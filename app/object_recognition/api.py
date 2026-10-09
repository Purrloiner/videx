"""Replaceable Vision API clients. Network access is opt-in and disabled by CLI."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


PRODUCT_PROMPT = (
    "이미지에 있는 제품의 정확한 제품명만 출력하세요. 브랜드와 용량이 제품명에 포함되어 "
    "있다면 유지하세요. 설명이나 다른 문장은 출력하지 마세요. 식별할 수 없다면 "
    "'인식 실패'만 출력하세요."
)


class VisionApiError(RuntimeError):
    pass


class VisionClient(Protocol):
    def recognize(self, jpeg_bytes: bytes) -> str:
        """Return one validated product-name string or '인식 실패'."""


def parse_product_name(raw: str) -> str:
    """Strictly accept a single short plain-text product name."""

    if not isinstance(raw, str):
        raise VisionApiError("Vision API 응답이 문자열이 아닙니다.")
    value = raw.strip().strip("\"'").strip()
    if value == "인식 실패":
        return value
    if not value or len(value) > 100:
        raise VisionApiError("제품명이 비어 있거나 너무 깁니다.")
    if "\n" in value or "\r" in value:
        raise VisionApiError("제품명 외의 여러 줄 응답을 받았습니다.")
    if value.startswith(("{", "[", "```", "#", "- ")):
        raise VisionApiError("제품명 형식이 아닌 응답을 받았습니다.")
    if re.search(r"(?i)^(product_name|제품명)\s*[:=]", value):
        raise VisionApiError("설명 필드가 포함된 응답을 받았습니다.")
    return value


@dataclass
class MockVisionClient:
    product_name: str = "테스트 제품 1L"
    calls: int = 0

    def recognize(self, jpeg_bytes: bytes) -> str:
        if not jpeg_bytes:
            raise VisionApiError("빈 이미지입니다.")
        self.calls += 1
        return parse_product_name(self.product_name)


class CachingVisionClient:
    """Prevent duplicate billable calls for identical merged JPEG payloads."""

    def __init__(self, inner: VisionClient) -> None:
        self.inner = inner
        self._cache: dict[str, str] = {}

    def recognize(self, jpeg_bytes: bytes) -> str:
        digest = hashlib.sha256(jpeg_bytes).hexdigest()
        if digest not in self._cache:
            self._cache[digest] = parse_product_name(self.inner.recognize(jpeg_bytes))
        return self._cache[digest]


class HttpVisionClient:
    """Minimal OpenAI-compatible JSON transport for a future approved endpoint.

    This class never runs unless an application explicitly instantiates and calls it.
    The API contract is isolated here because the final provider is not decided.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key_env: str = "VIDEX_VISION_API_KEY",
        timeout: float = 20.0,
        max_output_tokens: int = 48,
    ) -> None:
        if not endpoint.lower().startswith("https://"):
            raise ValueError("Vision API endpoint must use HTTPS")
        self.endpoint = endpoint
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens

    def build_payload(self, jpeg_bytes: bytes) -> dict[str, object]:
        encoded = base64.b64encode(jpeg_bytes).decode("ascii")
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PRODUCT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ],
                }
            ],
            "max_tokens": self.max_output_tokens,
        }

    def recognize(self, jpeg_bytes: bytes) -> str:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise VisionApiError(f"환경변수 {self.api_key_env}가 설정되지 않았습니다.")
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self.build_payload(jpeg_bytes)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            raw = payload["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exc:
            raise VisionApiError("Vision API 요청 또는 응답 처리에 실패했습니다.") from exc
        return parse_product_name(raw)
