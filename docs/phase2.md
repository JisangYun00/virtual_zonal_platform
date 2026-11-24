# Phase 2 추가 모듈 — 팀 코드 호환 패치

- 기준 저장소: `JisangYun00/virtual_zonal_platform`, 2026-11-24 공개 `main` 기준
- 기존 `core/state.py` 상태 변경 규칙, `core/protocol.py` 명령 프로토콜은 변경하지 않음
- `controller.py` 변경: 상태 변경 후 관찰자 콜백만 실행. 거부·중복 명령에서는 STATE Push를 발생시키지 않음
- Management: Jetson `.10:5001` TCP 상태 구독, 접속 즉시 전체 상태 전송, 상태 변경 즉시 전송, 1초마다 Heartbeat 스냅샷. 별도 물리 인터페이스를 의미하지 않음
- GPIO: 설치 시 비활성, BOARD 핀 검증 JSON을 명시적으로 제공해야 활성. 임의 핀 할당 금지
- LED: 1.5Hz, 50% duty. 7개 출력은 실험용 논리 신호이며 부품 배치에 따라 변동 가능
- Buttons: 50ms debounce, 700ms Long Press, 120ms Chord 구간은 프로젝트 의사결정 전 임시값
- Brake Chord: 두 버튼을 함께 누른 동안만 ON. 실제 동작 규칙은 팀 협의 전 임시값
- REAR Camera: `.10:8080/frame.jpg` JPEG snapshot polling. FLIR Blackfly S 실제 연동은 미검증. 실습 Lab 10의 PySpin 획득 및 Release 패턴 사용
- Laptop Dashboard: Tkinter 십자가 Zone 강조, active Zone·signal·brake·event 로그, 기존 Zone IP TCP 명령 전송. 카메라는 별도 viewer 창
- 테스트 범위: 추가 테스트 16개(재구성된 팀 핵심 인터페이스 fixture 사용), 관리 상태 변경 간단 E2E 실행. 기존 GitHub 저장소의 전체 21개 테스트는 직접 실행하지 못했음

## 통합 시 주의

`bringup/zone_controller.sh`가 Management `.10:5001`을 기본으로 함께 연다. 같은 포트를 쓰는 다른 프로그램이 있다면 시작 실패함. `--camera`를 지정한 경우에는 `.10:8080`도 연다. 방화벽과 장치 간 통신 여부 확인.

영상은 실습용 격리망에서만 송신할 것. Management와 JPEG HTTP에는 인증/암호화가 없으므로 공용망에 그대로 노출하지 않음.

## PR 규칙

`main` 직접 Push 금지. 브랜치 `feat/phase2-management-gpio-camera` 생성, 적용·전체 테스트 확인 후 PR 작성. `core/`/`bringup/` 변경으로 상대방 승인 필요.
