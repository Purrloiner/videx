# ESP32-S3 USB 이미지 뷰어

`main/main.c`의 native USB CDC 출력(CAM2 헤더 + JPEG)을 수신하여
카메라 0(LEFT), 카메라 1(RIGHT)을 한 창에 표시합니다.
수신/디코딩은 별도 스레드에서 실행하고 화면에는 각 카메라의 최신 프레임을 표시합니다.
2초 이상 새 프레임이 없으면 마지막 영상에 STALE 표시가 나타납니다.
두 카메라의 영상은 시간 동기화된 쌍이 아닙니다.

## 설치

Python 3.9 이상, GUI가 있는 데스크톱 환경에서 실행하세요.

```bash
cd /home/wonyj/Desktop/videx/proxy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-viewer.txt
```

필요한 외부 라이브러리:

- `pyserial`: USB 시리얼 포트 수신
- `numpy`: JPEG 바이트와 이미지 배열 처리
- `opencv-python`: JPEG 디코딩과 화면 표시 (`opencv-python-headless`는 창 표시 불가)

## 연결 및 실행

1. ESP32-S3의 **native USB 포트**를 PC에 연결합니다. USB-to-UART 포트는 로그용입니다.
2. 같은 native USB 포트를 사용하는 시리얼 모니터를 종료합니다.
3. 포트를 확인하고 뷰어를 실행합니다.

```bash
python viewer.py --list-ports
python viewer.py --port /dev/ttyACM0
```

Windows에서는 `python viewer.py --port COM5`처럼 해당 포트를 지정합니다.
`Q`, `Esc`, 창 닫기 또는 `Ctrl+C`로 종료합니다.
USB 연결 오류가 발생하면 지정한 포트로 1초 간격으로 재접속합니다.
재연결 후 포트 이름이 바뀌면 새 포트를 지정하여 다시 실행하세요.
Linux에서 Permission denied가 발생하면 해당 장치의 시리얼 접근 권한을 확인하세요.
`--baudrate` 기본값은 115200이며 native USB 전송 속도를 제한하지 않습니다.

## 전송 형식

28바이트 little-endian 헤더 `struct.Struct("<IB3xIIHHQ")` 뒤에 JPEG가 옵니다.
필드 순서는 magic(0x324D4143, 바이트로 CAM2), camera_id, reserved(0인 3바이트),
frame_id, jpeg_size, width, height, timestamp_us입니다.
JPEG 최대 크기는 1 MiB, 가로/세로 최대값은 각각 2000입니다.
임의 크기로 나뉜 USB 읽기를 처리하고, 잘못된 헤더/JPEG 또는 미완성 프레임의
6초 제한 초과 시 CAM2를 다시 검색합니다. timestamp_us는 카메라별 로컬 시각입니다.
