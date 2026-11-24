# 진행 현황

기준일: 2026-11-24. 단계와 날짜는 프로젝트 계획서 7장 기준.

## 요약

- **뼈대 완성:** 노트북에서 보낸 명령을 Jetson이 Active Zone 기준으로 받아들이거나 거부하고, 처리 후 상태를 돌려줌
- **실제 장비 확인 완료:** Jetson과 Ethernet으로 연결해 P0 시험 통과
- **다음 순서:** GPIO·카메라 단위 확인 → 상태 동기화(Management 채널) → 버튼·LED → 대시보드 → 카메라 → 측정

## 한 것

### 1. 실행 구조

- 장치마다 실행 명령 하나
  - Jetson: `bringup/zone_controller.sh`
  - 노트북: `bringup/central.sh`
  - 하드웨어 없이 한 대에서 시험: 둘 다 `--local`
- 실행할 때마다 고정 IP를 확인하고 없는 것만 추가. 재부팅으로 IP가 사라져도 다시 설정할 필요 없음
- 폴더는 세 종류로 나눔

| 폴더 | 하는 일 |
|---|---|
| `core/` | 판단 규칙과 메시지 형식. 네트워크·GPIO 같은 입출력 없음 |
| `zone_controller/` | Jetson 프로그램 |
| `central/` | 노트북 프로그램 |

- 의존 방향 고정: `bringup/` → 두 프로그램 → `core/`. 어기면 테스트 실패

### 2. 동작

- **명령 형식:** 목표 상태를 지정하는 방식. 같은 명령을 여러 번 보내도 결과가 같음
  - `SET_SIGNAL OFF|LEFT|RIGHT|HAZARD`
  - `SET_BRAKE ON|OFF`
- **대상 Zone 판별:** 명령이 도착한 IP로 판별 (`.11` FRONT, `.12` REAR, `.13` LEFT, `.14` RIGHT)
- **허용 규칙:** FRONT는 방향지시등, REAR는 방향지시등과 브레이크, LEFT·RIGHT는 명령 없음
- **Zone 전환:** FRONT → REAR → LEFT → RIGHT 순환. 넘어갈 때 방향지시등과 브레이크를 끔
- **응답:** 결과(성공 또는 거부 이유)와 처리 후 전체 상태를 함께 보냄
- **Zone 전환 입력:** GPIO 연결 전까지 Jetson 터미널의 Enter로 대신함

### 3. 실제 장비 확인

| 항목 | 결과 |
|---|---|
| Jetson | AGX Orin, Ubuntu 20.04, Python 3.8.10, Jetson.GPIO 설치됨 |
| P0 시험 | 통과. 수용·거부, 같은 명령 반복, Zone 전환 시 출력 끄기 확인 |
| 명령 응답시간(RTT) | 300회씩 3번 측정. 평균 1.2~1.8 ms, P95 약 2 ms |
| 두 장치의 시계 차이 | 47 ms. 둘 다 NTP 동기화 상태인데도 어긋나 있음 |
| PTP | Jetson은 하드웨어 PTP 지원. 현재 데스크톱 NIC는 미지원 |
| 카메라 | 장치 인식 안 됨 (`/dev/video*` 없음) |

자세한 값과 측정 방법은 [measurements.md](measurements.md) 참고

### 4. 고친 문제

- Enter를 연달아 누르면 첫 번째만 처리되던 문제
  - 원인: 남은 입력이 Python 버퍼에 남아 다음 처리가 일어나지 않음
  - 수정: `os.read()`로 한 번에 읽고 Enter 수만큼 처리
  - 회귀 테스트 추가, Jetson에서 3회 연속 입력 확인

### 5. 검사

- 테스트 21개: Zone 규칙, 상태 규칙, 메시지, 의존 방향, 계획서 시나리오 A~D
- 실행: `python3 -m unittest discover -s tests -v`
- 이 PC(Python 3.10·3.8)와 Jetson(Python 3.8.10)에서 모두 통과

## 할 것

### 지금 바로

- [ ] 첫 커밋과 push (remote: `JisangYun00/virtual_zonal_platform`)

### Phase 1 남은 항목 (11/24~11/27): 하드웨어 단위 확인

계획서 9장 체크리스트 중 남은 항목

- [ ] GPIO LED 1개 켜고 끄기
- [ ] GPIO 버튼 1개 입력 감지
- [ ] 카메라 연결 및 영상 획득

### Phase 2 (11/28~12/1): 핵심 모듈

| 할 일 | 넣을 위치 | 완료 기준 |
|---|---|---|
| Management 채널: Jetson이 전체 상태(`STATE`)를 연결 직후·변경 시·주기적으로 전송 | 메시지는 `core/protocol.py`, 서버는 `zone_controller/net.py` | 노트북에서 Enter 전환이 바로 보임 |
| 버튼 판정: debounce, 짧게·길게 누름, 동시 입력, 버튼 토글을 목표 상태로 변환 | `core/buttons.py` | 시각을 인자로 주는 테스트 통과 |
| LED 출력값: Zone 표시등 1개만 켜기, 방향지시등 1.5 Hz 점멸, 브레이크 | `core/state.py`의 `leds(state, now)` | 시각별 LED 7개 값 테스트 통과 |
| GPIO 입출력과 핀 표 | `zone_controller/gpio.py` | 실제 버튼으로 Zone 전환, LED 점등 |
| 노트북 상태 화면 | `central/dashboard.py`. 이때 전송 함수를 `central/client.py`로 분리 | 현재 Zone과 조명 상태 표시 |

### Phase 3 (12/2~12/4): 통합

- [ ] 통신 끊김 감지, 재연결 후 상태 다시 받기 (시나리오 D 완성)
- [ ] 후방 카메라: `zone_controller/camera.py`, `central/video.py`
  - 외부 패키지는 이 두 파일에서만 사용
  - REAR에서만 전송, 다른 Zone으로 넘어가면 중지
- [ ] 버튼·LED·대시보드·카메라를 함께 켠 통합 시험

### Phase 4 (12/5~12/7): 검증과 발표 준비

- [ ] 측정 기록: `central/metrics.py`가 `output/`에 저장
- [ ] Zone 전환 지연 측정 방법 확정. 두 장치의 시계가 47 ms 어긋나 있어 둘 중 하나 필요

| 방법 | 오차 | 필요한 것 |
|---|---|---|
| 측정 전후에 시계 차이를 재서 보정 | ±0.3 ms (실측) | 없음 |
| PTP 동기화 | 수십 µs (추정) | 노트북 sudo, 측정 중 NTP 끄기 |

- [ ] 반복 시험: 정상, 비활성 Zone 명령, 통신 끊김
- [ ] 발표용 요약: 평균, 최대, P95

## 구현 전에 정할 값

- 버튼을 짧게·길게 누름으로 나누는 기준 시간, 동시 입력으로 보는 시간 차
- 브레이크를 누르는 동안만 켤지, 누를 때마다 켜고 끌지
- 통신이 끊겼을 때 LED를 끌지, 유지할지
- 카메라 영상 전송 방식
- Jetson 핀 배치, 버튼 입력 전압, LED 전류 제한
- 상태 전송 주기와 끊김 판정 시간

## 알려진 위험

- **시나리오 테스트가 멈출 수 있음:** Jetson 출력을 한 줄씩 기다리는 구조라, 기대한 줄이 오지 않으면 실패하지 않고 멈춤
- **RTT 차이 원인 미확인:** 3회차가 1·2회차보다 평균 약 0.55 ms 빠름. 원인 조사 안 함
- **IP 숫자가 두 곳에 있음:** `core/zones.py`와 `scripts/setup_network.sh`. 바꿀 때 함께 수정 필요
- **실제 시연 노트북 미확인:** 지금까지 시험은 데스크톱으로 진행. 노트북의 네트워크 인터페이스 이름과 PTP 지원 여부 확인 필요
