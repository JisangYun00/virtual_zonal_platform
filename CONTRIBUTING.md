# 협업 규칙

사용법은 [README](README.md), 코드를 올릴 때 지킬 규칙은 이 문서 참고

## 1. 담당

| 폴더 | 담당 |
|---|---|
| `zone_controller/` | 정준홍 |
| `central/` | 윤지상 |
| `core/`, `bringup/`, `scripts/`, `tests/`, `docs/` | 공동 |

## 2. 브랜치

- `main`과 짧은 작업 브랜치만 사용
- 작업 브랜치는 `main`에서 만들고 `main`으로 병합
- 이름 형식: `<종류>/<주제>`
  - 예: `feat/gpio-buttons`, `bugfix/zone-select-debounce`
  - `<주제>`: 바꾸는 내용을 짧게. 영문 소문자 kebab-case
  - 사람 이름과 날짜는 넣지 않음
- `<종류>`는 아래 다섯 가지만 사용. 새 단어 만들지 않음

| 종류 | 용도 |
|---|---|
| `feat` | 기능 추가 |
| `bugfix` | 잘못된 동작 수정 |
| `refactor` | 동작은 그대로 두고 구조·이름만 정리 |
| `docs` | 문서만 수정 |
| `chore` | 스크립트, `.gitignore`, 설정 등 그 밖의 유지보수 |

## 3. 병합

- `main`에 직접 push 금지. PR로만 병합
- PR 전 필수: `python3 -m unittest discover -s tests -v` 통과
- PR 본문에 적을 것
  - 무엇을 왜 바꿨는지
  - 실제로 돌려 본 것. 예: "unittest 통과", "Jetson에서 bringup 실행, REAR SET_BRAKE ON → SUCCESS"
- 리뷰 조건은 바꾼 위치에 따라 다름

| 바꾼 위치 | 병합 조건 |
|---|---|
| `core/`, `bringup/`, `tests/test_architecture.py` | 상대방 승인 필수. 두 프로그램 사이의 약속이 바뀌는 곳 |
| 자기 담당 폴더 안에서만 | 테스트 통과 시 본인이 병합 |

- 병합 방식: squash merge. 병합한 작업 브랜치는 바로 삭제
- 병합 커밋 제목: `[MERGE] main <- <브랜치>`
  - 예: `[MERGE] main <- feat/gpio-buttons`
- `main`은 언제든 시연 가능한 상태 유지

## 4. 폴더 규칙

| 폴더 | 규칙 |
|---|---|
| `bringup/` | 사용자 진입점. 장치마다 스크립트 하나. 장치에 새 프로세스나 준비 단계가 생기면 그 장치의 스크립트에 추가. 스크립트는 시작할 때 레포 최상위로 이동 |
| `core/` | 판단 규칙과 메시지 형식만. 소켓, GPIO, 파일, 프로세스, 시계 사용 금지. 시각이 필요하면 인자로 받음. 상태를 바꾸는 규칙은 `core/state.py`에만 둠 |
| `zone_controller/`, `central/` | 장치 프로그램. `__main__.py`는 부품 연결만 하고 판단은 `core/`에 맡김. 두 폴더는 서로 import 금지 |
| `scripts/` | bringup이 부르는 보조 도구. 직접 실행해도 됨 |
| `docs/` | `design.md`: 결정과 이유. `measurements.md`: 날짜별 실측값. `progress.md`: 한 것과 할 것. 추정은 추정이라고 표시 |
| `output/` | 측정 원본 로그. 커밋 금지 (`.gitignore`에 포함) |

- `core/`·`zone_controller/`·`central/` 사이의 import 규칙은 `tests/test_architecture.py`가 자동 검사

## 5. 코드 규칙

- **메시지:** `core/protocol.py`로만 만들고 읽음. 메시지 형식을 바꾸는 PR은 두 프로그램과 테스트를 같은 PR에서 함께 수정
- **명령:** 목표 상태를 지정 (`SET_SIGNAL LEFT`, `SET_BRAKE ON`). 켜고 끄기를 번갈아 하는 토글은 버튼 해석에서만 사용
- **장치 값:** 정한 사람이 한 곳에만 적고, 코드는 읽기만 함
  - IP: `core/zones.py`. `scripts/setup_network.sh`에도 같은 숫자가 있어 함께 수정
  - GPIO 핀: 배선을 정한 사람이 `zone_controller/gpio.py` 맨 위 표에 기록
- **외부 패키지:** 카메라 파일(`zone_controller/camera.py`, `central/video.py`)에서만 사용. 나머지 코드와 테스트는 설치 없이 실행 가능해야 함
- **Python 3.8 문법:** Jetson이 3.8.10. 타입 힌트에 `list[...]`를 쓰려면 파일 맨 위에 `from __future__ import annotations` 추가
- **경로:** 개인 PC의 절대 경로(`/home/...`) 커밋 금지
- **언어:** 코드와 주석은 영어. README와 `docs/`는 한국어, 개조식, 명사형 끝맺음(~함, ~임)

## 6. 이름 규칙

| 대상 | 규칙 | 예 |
|---|---|---|
| 폴더 | 역할을 나타내는 명사. 장치 이름 사용 안 함 | `zone_controller`, `central` |
| bringup 스크립트 | 실행할 패키지와 같은 이름 | `bringup/central.sh` ↔ `central/` |
| 모듈 | 책임지는 대상 하나를 명사로 | `controller`, `net`, `gpio`, `state` |
| 클래스 | 상태를 가진 것만 클래스로. 값은 `Enum`이나 `NamedTuple` | `ZoneController`, `State`, `Ack` |
| 함수 | 판단 함수는 결과를 돌려줌. 입출력 함수는 동사 | `apply()`, `next_zone()`, `send()`, `listen()` |
| 메시지 함수 | 만들기는 메시지 이름, 읽기는 `parse_` + 메시지 이름 | `ack()`, `parse_ack()` |
| 상수 표 | `<키>_<값>` 형식 대문자 | `ZONE_HOST`, `ALLOWED_ACTIONS` |
| 로그 | `EVENT key=value ...` | `COMMAND ip=... status=...`, `ZONE_CHANGED FRONT -> REAR` |
| 테스트 | `test_<모듈>.py`. 시나리오는 계획서 기호를 붙임 | `test_state.py`, `test_c_inactive_zone_command_...` |
