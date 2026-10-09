# VIDEX 물체 인식 Python 모듈

## 설치

`app` 디렉터리에서 아래 명령을 실행한다.

```powershell
python -m pip install -r requirements.txt
```

## 실행

실제 Vision API를 호출하지 않고 Mock 제품명으로 앞면/뒷면 병합 전체 흐름을 확인한다.

```powershell
python -m object_recognition --manual-pair front.jpg back.jpg --mock-product "테스트 제품 1L" --verbose
```

시간순 JPEG 프레임 또는 동영상 자동 선별도 지원한다.

```powershell
python -m object_recognition --images frames\*.jpg --fps 10 --verbose
python -m object_recognition --video sample.mp4 --verbose
```

PowerShell은 프로그램에 wildcard를 자동 확장하지 않으므로 `--images`에는 실제 파일 경로 목록을
전달해야 한다. 테스트는 다음 명령으로 실행한다.

```powershell
python -m unittest discover -s tests -v
```

출력은 기본적으로 `app/test_output/`에 `*_front.jpg`, `*_back.jpg`,
`*_merged.jpg`로 저장된다. `--output-dir`로 변경할 수 있다.

## 실제 연결 전 확인할 정보

- ESP32 프레임 전송 방식(HTTP/WebSocket/USB 등)과 JPEG 메시지 경계
- 카메라 ID, 프레임 ID, 촬영 타임스탬프 필드 형식
- 실제 카메라의 FPS, 해상도, 회전 방향
- 대회에서 허용된 Vision API와 중계 서버의 요청/응답 규격
- 실제 영상으로 보정할 안정성, 회전 차이, 선명도, 밝기 임계값

`HttpVisionClient`는 미래의 승인된 OpenAI 호환 중계 서버를 위한 격리된 구현이며 기본 CLI에서는
사용하거나 호출하지 않는다. 키는 코드가 아니라 `VIDEX_VISION_API_KEY` 환경변수에서만 읽는다.
