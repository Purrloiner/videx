"""Command-line runner for local files, JPEG sequences, and videos."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .api import MockVisionClient
from .models import RecognitionConfig, RecognitionState
from .recognizer import ObjectRecognizer
from .sources import packet_from_file, packets_from_files, packets_from_video


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VIDEX 물체 인식 Python 검증 프로그램")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--images", nargs="+", help="시간순 JPEG 이미지 목록")
    source.add_argument("--video", help="테스트 동영상 경로")
    source.add_argument(
        "--manual-pair",
        nargs=2,
        metavar=("FRONT", "BACK"),
        help="앞면/뒷면 JPEG를 수동 확정하여 전체 파이프라인 검증",
    )
    parser.add_argument("--camera-id", default="local")
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--mock-product", default="테스트 제품 1L")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stable-seconds", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    config = RecognitionConfig(
        output_dir=args.output_dir,
        stable_duration=args.stable_seconds,
        phase_timeout=args.timeout,
    )
    recognizer = ObjectRecognizer(config, MockVisionClient(args.mock_product))
    recognizer.start_recognition(args.camera_id)
    try:
        if args.manual_pair:
            front, back = args.manual_pair
            recognizer.process_frame(
                packet_from_file(front, args.camera_id, "manual-front"), manual_capture=True
            )
            recognizer.process_frame(
                packet_from_file(back, args.camera_id, "manual-back"), manual_capture=True
            )
        else:
            packets = (
                packets_from_files(args.images, args.camera_id, args.fps)
                if args.images
                else packets_from_video(args.video, args.camera_id)
            )
            for packet in packets:
                recognizer.process_frame(packet)
                if recognizer.state in (RecognitionState.COMPLETED, RecognitionState.ERROR):
                    break
            if recognizer.state not in (RecognitionState.COMPLETED, RecognitionState.ERROR):
                # A finite file/video ending before capture completion is an input
                # failure; live transports should instead keep calling tick().
                recognizer.tick(recognizer.phase_started_at + args.timeout + 0.001)
    except (OSError, ValueError, RuntimeError) as exc:
        logging.error("입력 처리 실패: %s", exc)
        return 2
    state = recognizer.get_recognition_state()
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if recognizer.state is RecognitionState.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
