# 설계 결정

측정값은 [measurements.md](measurements.md)에 따로 기록함. 이 문서는 결정과 그 이유만 다룸.

## 역할과 용어

| 이 프로젝트 | Zonal Architecture 용어 |
|---|---|
| 노트북의 `central` | Central Compute (HPC) |
| Jetson의 `zone_controller` (.11~.14) | Zone Controller ×4 = Zonal Gateway. 프로그램 안에서는 `ZoneController` 객체 하나가 4개 역할을 맡고 active zone을 공유함 |
| 브레드보드 LED·버튼, 카메라 | Zone에 연결된 센서·액추에이터 |

## 확정 (코드에 반영됨)

| 항목 | 결정 | 이유 |
|---|---|---|
| 상태 모델 | Jetson의 상태 전체는 `State(active_zone, signal, brake)` 값 하나. 바꾸는 규칙은 `core/state.py`의 `apply()`와 `select_next_zone()`뿐 | 허용 검사, Zone 전환, Safe State가 한 곳에 있고 하드웨어 없이 테스트됨 |
| 상태 소유 | `zone_controller/controller.py`의 `ZoneController`만 상태를 가짐 | Single Source of Truth. Central은 ACK로 받은 상태를 표시만 함 |
| 명령 형식 | 목표 상태 지정: `SET_SIGNAL OFF\|LEFT\|RIGHT\|HAZARD`, `SET_BRAKE true\|false` | 같은 명령을 다시 받아도 결과가 같음. 재시도·중복 수신에 안전하고 request_id로 중복을 거를 필요가 없음 |
| 토글 | 토글은 버튼 해석(`core/buttons.py`, Phase 2)에서만. 현재 상태를 보고 목표 상태 명령으로 바꿈 | 네트워크 명령은 항상 목표 상태 |
| Zone 전환 | 다음 Zone으로 넘어가면 signal OFF, brake OFF | 계획서 4.1 Safe Transition. 이전 Zone의 출력이 남지 않음 |
| 명령 대상 Zone | 수신 IP로 결정. 메시지에 zone 필드 없음 | payload와 IP가 어긋나는 상태가 생기지 않음 |
| 허용 규칙 | `core/zones.py`의 `ALLOWED_ACTIONS`: FRONT는 signal, REAR는 signal과 brake, LEFT/RIGHT는 없음 | 계획서 4.3. 규칙이 바뀌면 이 표만 고침 |
| ACK | 결과 상태와 명령 처리 후의 전체 상태(active_zone, signal, brake)를 담음. 거부돼도 현재 상태를 담음 | Central이 명령 하나로 결과와 현재 상태를 함께 확인 |
| 메시지 형식 | `core/protocol.py`만 메시지를 만들고 읽음 | 두 프로그램이 같은 함수를 써서 형식이 어긋나지 않음 |
| 동시성 | Jetson은 asyncio 단일 루프 | 상태를 바꾸는 actor가 하나라 lock이 필요 없음 |
| 실행 | 장치별 `bringup/*.sh` 하나. IP는 실행할 때마다 확인하고 없는 것만 추가 | 재부팅해도 다시 신경 쓸 필요 없음. NetworkManager 프로필은 건드리지 않음 |
| Python | 3.8 문법 (`ruff.toml`의 `target-version`) | Jetson이 3.8.10 (실측) |

## 잠정 (실측 후 확정)

| 항목 | 현재 값 | 바꿀 곳 |
|---|---|---|
| 전송 | TCP, JSON 한 줄당 메시지 1개 | `core/protocol.py` |
| Port | 5000 (모든 Zone IP 공통). Management는 5001 제안 | `core/protocol.py` `PORT` |
| 명령 연결 | 명령마다 새 TCP 연결. RTT는 연결 후 송신부터 ACK 수신까지 | `central/__main__.py` `send` |
| ZONE SELECT 입력 | GPIO 전까지는 Jetson 터미널의 Enter로 대신함 | `zone_controller/__main__.py` `on_stdin` |
| request_id | Central 콘솔 실행마다 1부터 증가 | `central/__main__.py` |
| 명령 로그 | Jetson stdout에 `COMMAND ip= zone= request_id= action= value= status= active= signal= brake=` | `zone_controller/net.py` |

## 미정

- **Management 채널(.10)**: 제안은 Jetson이 `STATE`(전체 상태) 메시지 하나만 보내는 것. 연결 직후, 상태가 바뀔 때, 주기적으로 보냄. 재동기화, ZONE_CHANGED 알림, Heartbeat를 메시지 하나로 처리함. 주기와 끊김 판정 시간은 미정
- **Zone 전환 지연 측정**: 데스크톱–Jetson 시험에서 PTP 전 시계 차이 약 47 ms 확인. 실제 전환 지연은 아직 미측정. 발표용 노트북에서 아래 두 방법 중 선택 필요
  - 측정 전후에 시각 질의로 차이를 재서 보정: 데스크톱 시험에서 추정 불확실성 약 ±0.3 ms, root 불필요
  - PTP 동기화: 시계 차이 추정값 +0.011 ms(±0.066 ms). 양쪽 `sudo`와 측정 중 NTP 끄기 필요. Jetson 하드웨어 모드와 `--tx_timestamp_timeout 100`으로 동작 확인. 명령은 [measurements.md](measurements.md) 참고
- Short/Long press 임계시간, 동시 입력 판정시간
- Brake를 누르는 동안만 켤지 토글할지. 상태 모델은 그대로이고 `core/buttons.py`의 판정만 달라짐
- 통신이 끊겼을 때의 GPIO Safe State
- 카메라 인터페이스와 송출 방식. 외부 패키지는 `zone_controller/camera.py`와 `central/video.py` 안에서만 import
- Jetson GPIO 핀맵, 입력 전압과 LED 전류 제한
