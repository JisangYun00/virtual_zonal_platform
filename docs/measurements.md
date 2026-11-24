# 실측 기록

- 측정한 값만 날짜별로 기록
- 추정은 따로 표시
- 발표용 요약은 Phase 4에서 정리

## 2026-11-24 — 장비 확인과 P0 실장비 시험

### 측정 환경

| 장치 | 내용 |
|---|---|
| Central 쪽 | 데스크톱 (Ubuntu 22.04), `enp8s0` Realtek r8169, `192.168.10.1/24`. 실제 시연은 노트북으로 바뀔 예정 |
| Jetson | **AGX Orin Developer Kit**, L4T R35.6.4 (JetPack 5.1.x), Ubuntu 20.04.6, kernel 5.10.216-tegra |
| Jetson Python | **3.8.10** |
| Jetson `eth0` | nvethernet, `192.168.10.10~14/24` (재부팅 전까지 유지 중). `wlan0`은 `192.168.0.9`로 인터넷 연결 |
| Jetson 라이브러리 | Jetson.GPIO 2.1.9 설치됨. 카메라 장치(`/dev/video*`) 없음 |
| 연결 | Ethernet 직결 |

### 연결성 (ICMP)

- 이전 확인: Desktop → `.10~.14` ping 10/10, 손실 0%, 평균 약 0.9 ms
- 이번 확인: `.10`에 20회, 평균 1.179 ms (min 0.830 / max 1.504 ms)

### 코드 테스트 (Jetson 실제 Python 3.8.10)

- `python3 -m unittest discover -s tests`: 당시 14개 모두 통과

### P0 실장비 시험: 통과

Jetson에서 `bringup/zone_controller.sh`(실제 모드), 데스크톱에서 `bringup/central.sh`로 명령을 보냄. 당시 명령 형식(`LEFT_TURN`, `BRAKE`) 기준.

| Active Zone | 명령 | 결과 |
|---|---|---|
| FRONT | FRONT(.11) 방향지시 | SUCCESS |
| FRONT | REAR(.12), LEFT(.13), RIGHT(.14) 방향지시 | REJECTED_INACTIVE_ZONE |
| FRONT | FRONT 브레이크 | REJECTED_NOT_ALLOWED |
| Enter 후 REAR | REAR 방향지시, REAR 브레이크 | SUCCESS |
| REAR | FRONT 방향지시 | REJECTED_INACTIVE_ZONE |

Jetson 로그에 명령마다 수신 IP, Zone, request_id, 명령, active_zone, 결과가 남음.

### P0 재시험 (목표 상태 명령 형식, 구조 정리 후): 통과

코드 테스트: Jetson Python 3.8.10에서 21개 모두 통과.

| Active Zone | 명령 | 결과와 응답 상태 |
|---|---|---|
| FRONT | FRONT `SET_SIGNAL HAZARD` 2회 | 두 번 모두 SUCCESS, signal=HAZARD. 반복해도 상태 같음 |
| FRONT | REAR(.12), LEFT(.13), RIGHT(.14) `SET_SIGNAL LEFT` | REJECTED_INACTIVE_ZONE, 상태 그대로 |
| FRONT | FRONT `SET_BRAKE ON` | REJECTED_NOT_ALLOWED |
| Enter 후 REAR | REAR `SET_SIGNAL LEFT`, `SET_BRAKE ON` 2회 | SUCCESS, signal=LEFT, brake=true. 반복해도 상태 같음 |
| REAR | FRONT `SET_SIGNAL RIGHT` | REJECTED_INACTIVE_ZONE |
| Enter 후 LEFT | LEFT `SET_SIGNAL LEFT` | REJECTED_NOT_ALLOWED, **signal=OFF, brake=false**. REAR의 출력이 전환과 함께 꺼짐 (Safe Transition) |

발견하고 고친 버그: Enter를 연달아 보내면 첫 번째만 처리됨. 원인은 `sys.stdin.readline()`이 나머지를 Python 버퍼에 담아 두어 OS가 다시 '읽을 것 있음'을 알리지 않은 것. `os.read()`로 바꾼 뒤 Jetson에서 Enter 3회를 한 번에 보내 3회 모두 전환되는 것을 확인함. 회귀 테스트 `test_a_zone_select_presses_arriving_together_all_count` 추가.

### 명령 RTT (같은 명령 300회, 명령마다 새 TCP 연결, 연결 시간 제외)

- 총 3회 측정. 1회차만 이전 명령 형식
- 2회차는 위 버그로 Zone이 RIGHT에 머물러 300회 모두 REJECTED_INACTIVE_ZONE. 단, 수신 → 판단 → ACK 경로는 같아 시간 값은 유효

| 회차 | 명령 | 성공 | 평균 | 중앙값 | P95 | P99 | 최소 | 최대 (첫 명령) |
|---|---|---|---|---|---|---|---|---|
| 1 | `REAR HAZARD` (이전 형식) | 300/300 | 1.753 | 1.898 | 2.205 | 2.705 | 0.818 | 6.521 ms |
| 2 | `REAR SET_SIGNAL HAZARD` (Zone=RIGHT) | 0/300 (모두 거부) | 1.788 | 1.974 | 2.237 | 2.411 | 0.879 | 6.911 ms |
| 3 | `REAR SET_SIGNAL HAZARD` | 300/300 | 1.207 | 1.131 | 1.940 | 2.121 | 0.381 | 3.082 ms |

- 3회차가 1·2회차보다 평균 약 0.55 ms 낮음
- 원인 미조사. 반복 측정 횟수와 조건을 정할 때 다시 확인

1회차 상세:

| 항목 | 값 |
|---|---|
| 성공 | 300/300 |
| 평균 / 중앙값 | 1.753 / 1.898 ms |
| P95 / P99 | 2.205 / 2.705 ms |
| 최소 / 최대 | 0.818 / 6.521 ms (최대는 첫 명령) |

해석 (추정, 미조사): 직결 기가비트의 ICMP 1.18 ms는 높은 편이라 NIC 절전이나 interrupt coalescing을 의심. 명령 RTT와 ping의 차이 약 0.7 ms는 Python 처리와 로그 출력 몫으로 보임.

### 시간 동기화

| 항목 | 결과 |
|---|---|
| Jetson PTP 하드웨어 | **지원**. `ethtool -T eth0`: `PTP Hardware Clock: 0`, 하드웨어 송수신 타임스탬프 |
| Jetson PHC 시각 | 1970년 값. 시스템 시계와 무관하게 돎 (하드웨어 모드로 쓰려면 `phc2sys` 필요) |
| Jetson linuxptp | 1.9.2 설치함. `ptp4l -i eth0 -H`가 `/dev/ptp0`를 잡고 오류 없이 시작 |
| 데스크톱 PTP 하드웨어 | **없음** (r8169, software 타임스탬프만) |
| 양쪽 PTP 동기화 | 미실시. 데스크톱 `sudo` 필요 |
| **현재 시계 차이** | **Jetson − 데스크톱 = +47.015 ms (±0.313 ms)**. 양쪽 모두 NTP "동기화됨" 상태에서 측정 |

시계 차이 측정 방법: Jetson `192.168.10.10:5999`에 UDP로 `time.time()`을 돌려주는 임시 서버를 띄우고, 데스크톱에서 200회 질의해 RTT가 가장 짧은 샘플로 `offset = t_jetson − (t_send + t_recv) / 2`를 계산. 오차는 그 RTT의 절반.

결론: 두 장치의 타임스탬프를 그대로 비교하면 47 ms가 섞임. Zone 전환 지연을 재려면 시계 차이 보정이나 PTP 동기화가 필요함 (`docs/design.md` 미정 항목).
