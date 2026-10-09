from __future__ import annotations

import unittest

from object_recognition.api import (
    PRODUCT_PROMPT,
    CachingVisionClient,
    HttpVisionClient,
    MockVisionClient,
    VisionApiError,
    parse_product_name,
)


class ApiTests(unittest.TestCase):
    def test_product_name_validation(self) -> None:
        self.assertEqual(parse_product_name('  "서울우유 나100% 1L"  '), "서울우유 나100% 1L")
        self.assertEqual(parse_product_name("인식 실패"), "인식 실패")
        for invalid in ("", "제품명: 우유", "첫 줄\n둘째 줄", '{"product_name":"우유"}'):
            with self.subTest(invalid=invalid), self.assertRaises(VisionApiError):
                parse_product_name(invalid)

    def test_cache_prevents_duplicate_calls(self) -> None:
        mock = MockVisionClient("서울우유 나100% 1L")
        client = CachingVisionClient(mock)
        self.assertEqual(client.recognize(b"jpeg"), "서울우유 나100% 1L")
        self.assertEqual(client.recognize(b"jpeg"), "서울우유 나100% 1L")
        self.assertEqual(mock.calls, 1)

    def test_http_payload_is_single_image_and_short_output(self) -> None:
        client = HttpVisionClient("https://example.invalid/vision", "future-model")
        payload = client.build_payload(b"jpeg")
        self.assertEqual(payload["max_tokens"], 48)
        content = payload["messages"][0]["content"]  # type: ignore[index]
        self.assertEqual(content[0]["text"], PRODUCT_PROMPT)
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
