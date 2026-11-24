# virtual_zonal_platform

Ethernet 기반 Virtual Zonal Architecture 테스트베드. 단일 Jetson에 4개의 논리적 Zone Controller(FRONT/REAR/LEFT/RIGHT)를 두고, 노트북(Central)이 Ethernet으로 Zone별 명령을 보냄.

Python 3.8 이상, 표준 라이브러리만 사용. 설치 없이 이 레포를 받아 바로 실행함.

| 문서 | 내용 |
|---|---|
| [docs/progress.md](docs/progress.md) | 한 것과 할 것 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 협업 규칙 |
| [docs/design.md](docs/design.md) | 설계 결정과 이유 |
| [docs/measurements.md](docs/measurements.md) | 날짜별 실측값 |

## 실행

같은 레포를 두 장치에 받고, 장치마다 bringup 명령 하나로 켬.

```bash
git clone https://github.com/JisangYun00/virtual_zonal_platform.git
cd virtual_zonal_platform

# Jetson: IP .10~.14 확인 (없으면 sudo로 추가) → Zone Controller 실행. 이 터미널의 Enter = ZONE SELECT
bringup/zone_controller.sh                 # 기본 인터페이스 eth0, 다르면 --iface <name>

# 노트북: IP .1 확인 → Jetson ping → Central 콘솔 실행
bringup/central.sh --iface <name>          # 인터페이스 이름은 ip -br link로 확인
```

하드웨어 없이 한 대에서 시험할 때는 둘 다 `--local`을 붙임 (127.0.0.x 사용).

```text
$ bringup/central.sh --local
FRONT SET_SIGNAL LEFT
{"action": "SET_SIGNAL", "active_zone": "FRONT", "brake": false, "request_id": 1, "rtt_ms": 0.35, "signal": "LEFT", "status": "SUCCESS", "value": "LEFT", "zone": "FRONT"}
REAR SET_BRAKE ON
{"action": "SET_BRAKE", "active_zone": "FRONT", "brake": false, "request_id": 2, "rtt_ms": 0.16, "signal": "LEFT", "status": "REJECTED_INACTIVE_ZONE", "value": "ON", "zone": "REAR"}
```

한 번만 보낼 때: `echo "REAR SET_BRAKE ON" | bringup/central.sh --local`

전체 검사 (규칙, 메시지, import 경계, bringup으로 띄운 시나리오 A~D):

```bash
python3 -m unittest discover -s tests -v
```

## 동작 약속

- **명령은 목표 상태를 지정함.** `SET_SIGNAL OFF|LEFT|RIGHT|HAZARD`, `SET_BRAKE ON|OFF`. 같은 명령을 여러 번 보내도 결과가 같음.
- **명령 대상 Zone은 명령이 도착한 IP 주소로 결정함.** 메시지에 zone 필드가 없음.
- **허용 규칙:** FRONT는 SET_SIGNAL, REAR는 SET_SIGNAL과 SET_BRAKE, LEFT/RIGHT는 Zone Indicator만 있으므로 명령 없음.
- **Zone 전환(ZONE SELECT):** FRONT → REAR → LEFT → RIGHT 순환. 넘어갈 때 signal과 brake를 끔.
- **응답:** Zone Controller는 모든 명령에 ACK로 답함. ACK에는 결과(`SUCCESS`, `REJECTED_INACTIVE_ZONE`, `REJECTED_NOT_ALLOWED`)와 처리 후의 전체 상태가 들어 있음. 이름이 ACK여도 거부일 수 있음. 형식이 잘못된 메시지에는 `ERROR`로 답하고 연결은 유지함.
- **Central 콘솔:** 한 줄에 `ZONE ACTION VALUE` 하나를 읽음 (대소문자 무관). ACK는 stdout에 JSON 한 줄로, 잘못된 입력이나 연결 실패는 stderr에 쓰고 다음 줄을 계속 처리함. 입력이 끝나면 exit 0.
- **RTT:** 명령 송신부터 ACK 수신까지. TCP 연결 시간은 포함하지 않음.

## 구조

```text
bringup/              장치별 실행 명령. 사용자는 항상 여기서 시작
  zone_controller.sh    Jetson: 네트워크 확인 → python3 -m zone_controller
  central.sh            노트북: 네트워크 확인 → python3 -m central
core/                 판단 규칙과 메시지 형식. I/O 없음, 두 프로그램이 import
  zones.py              용어와 고정 표: Zone, Signal, Action, Status, 허용 표, IP 표
  state.py              State, apply(), select_next_zone(): 상태를 바꾸는 유일한 규칙
  protocol.py           모든 메시지의 생성과 파싱 (command/ack/error, parse_*)
zone_controller/      Jetson 프로그램 (정준홍)
  __main__.py           조립: 인자, controller 생성, 네트워크와 입력 연결
  controller.py         ZoneController: 상태 단일 소유. 모든 입력이 여기로 들어옴
  net.py                Zone 주소별 TCP 서버: 바이트 ↔ protocol ↔ controller
central/              노트북 프로그램 (윤지상)
  __main__.py           콘솔: 입력 → 전송 → ACK + RTT 출력
scripts/setup_network.sh  없는 IP만 추가 (bringup이 호출)
tests/                test_<모듈>.py, 경계 검사, 시나리오 A~D (test_scenarios.py)
docs/                 design.md (결정), measurements.md (실측)
```

의존 방향은 `bringup/` → `zone_controller/`, `central/` → `core/` 한쪽으로만 흐름. `tests/test_architecture.py`가 검사함.

- `core/`는 I/O 모듈을 import하지 않음
- `zone_controller/`와 `central/`은 서로 import하지 않음

## 명령 하나의 흐름

```text
central/__main__.py        "REAR SET_BRAKE ON" 입력 → command() 생성 → 전송, RTT 시작
  ═══ TCP 192.168.10.12:5000 ═══
zone_controller/net.py     수신 IP로 Zone 판별 (.12 = REAR), parse_command()
zone_controller/controller.py   request(REAR, SET_BRAKE, True)
core/state.py              apply(state, REAR, SET_BRAKE, True) → (새 state, Status)
zone_controller/net.py     COMMAND 로그, ack(status, state) 응답
  ═══
central/__main__.py        parse_ack(), RTT 끝, JSON 한 줄 출력
```

## 코드 읽는 순서

1. 이 README: 정체, 실행법, 동작 약속
2. `tests/test_scenarios.py`: 계획서 시나리오 A~D가 실제로 어떻게 동작하는지
3. `core/zones.py` → `core/state.py` → `core/protocol.py`: 용어, 규칙, 메시지
4. `bringup/zone_controller.sh` → `zone_controller/__main__.py` → `net.py` → `controller.py`: Jetson 쪽
5. `bringup/central.sh` → `central/__main__.py`: 노트북 쪽
6. `tests/test_architecture.py`, `docs/design.md`: 경계와 결정 이유

## 다음에 넣을 위치

| 기능 | 위치 | 연결 방식 |
|---|---|---|
| 버튼 판정 (debounce, short/long, 동시 입력, 토글 → 목표 상태) | `core/buttons.py` | 시간을 인자로 받는 순수 함수. 결과를 `controller.request()`나 `select_next()`로 넘김 |
| LED 출력값 (Zone Indicator 1개, 1.5 Hz 점멸, Brake) | `core/state.py`에 `leds(state, now)` 추가 | 상태와 시각만으로 계산 |
| GPIO 입출력, 핀 표 | `zone_controller/gpio.py` | `__main__.py`가 연결. controller는 gpio를 import하지 않음 |
| Management 채널 (STATE push) | 메시지는 `core/protocol.py`, 서버는 `zone_controller/net.py` | |
| 후방 카메라 | `zone_controller/camera.py`, `central/video.py` | 외부 패키지는 이 두 파일에서만 import |
| 대시보드, 측정 로그 | `central/dashboard.py`, `central/metrics.py`. 이때 `send()`를 `central/client.py`로 분리 | 콘솔과 같은 `send()`를 씀 |
