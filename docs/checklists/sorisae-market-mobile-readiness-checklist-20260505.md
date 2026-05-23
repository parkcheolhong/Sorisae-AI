# Sorisae Market/Mobile Readiness Checklist (2026-05-05)

## 목적
- 소리새를 마켓 프로그램으로 운영 가능한 수준으로 고정한다.
- 모바일 APK 앱(서버 연동형)으로 구현 가능한 출고 기준을 명확히 한다.
- 각 항목은 실검증 2회 통과 후에만 완료됨으로 닫는다.

## 상태 규칙
- 보고 상태는 `구현됨`, `완료됨`, `실패`만 사용한다.
- 자동 검증 또는 운영 검증이 하나라도 실패하면 `완료됨`으로 보고하지 않는다.

## 게이트 항목

### 1) 슬롯별 입출력 계약 고정
- 상태: 구현됨
- 목표:
  - 슬롯별 요청/응답 JSON 스키마를 문서로 고정
  - 필수 필드/선택 필드/타입/기본값/에러 형식 정의
- 완료 기준:
  - 최소 6개 핵심 슬롯(voice_movie, detective_dashboard, integrated_dashboard, movie_server, master, shopping) 계약 문서화
  - `/api/marketplace/sorisae/dispatch` 실호출 2회에서 계약 위반 0건
- 증거 기록:
  - 검증 실행 1차: `docs/evidence/sorisae-dispatch-slot-io-validation-rounds-20260505.md` (Round 1, 6/6 slots, HTTP 200 + status=flask_server_ok)
  - 검증 실행 2차: `docs/evidence/sorisae-dispatch-slot-io-validation-rounds-20260505.md` (Round 2, 6/6 slots, HTTP 200 + status=flask_server_ok)
  - 비고: 계약 본문은 `docs/contracts/sorisae-dispatch-slot-io-contract-20260505.md`에 고정

### 2) 실패 코드 표준화
- 상태: 구현됨
- 목표:
  - 슬롯 실패 응답에 표준 코드(`error_code`, `error_message`, `retryable`, `source`) 적용
- 완료 기준:
  - 네트워크 실패/타임아웃/런타임 예외/입력 검증 실패를 구분해 일관된 코드 반환
  - 2회 실검증에서 동일 실패 조건에 동일 코드 재현
- 증거 기록:
  - 검증 실행 1차: `docs/evidence/sorisae-dispatch-failure-code-validation-rounds-20260505.md` (Round 1)
  - 검증 실행 2차: `docs/evidence/sorisae-dispatch-failure-code-validation-rounds-20260505.md` (Round 2)
  - 비고: 표준 정의는 `docs/contracts/sorisae-dispatch-failure-code-standard-20260505.md`에 고정

### 3) 1차 부하 테스트
- 상태: 구현됨
- 목표:
  - 마켓 호출 기준의 최소 동시성/응답시간/오류율 기초선 확보
- 완료 기준:
  - 핵심 슬롯 dispatch 대상으로 1차 부하 프로파일(요청 수, 동시성, p95, 오류율) 산출
  - 동일 조건 2회 재측정 결과 편차 허용 범위 내
- 증거 기록:
  - 검증 실행 1차: docs/evidence/sorisae-dispatch-loadtest-round1-final-20260505.json (180/180 성공, error_rate 0.0%, p95 89.654ms)
  - 검증 실행 2차: docs/evidence/sorisae-dispatch-loadtest-round2-final-20260505.json (180/180 성공, error_rate 0.0%, p95 83.434ms)
  - 비고: 원인/개선 분석은 docs/evidence/sorisae-dispatch-loadtest-analysis-20260505.md 참고

### 4) 보안 점검
- 상태: 구현됨
- 목표:
  - 인증/권한/CORS/입력 검증/민감정보 노출/에러 메시지 노출 범위 점검
- 완료 기준:
  - 비인가 요청 차단, 토큰 없는 호출 차단, 과도한 내부 예외 노출 제거 확인
  - 점검 시나리오 2회 반복 시 동일 통과
- 증거 기록:
  - 검증 실행 1차: `docs/evidence/sorisae-dispatch-security-gate4-round1-20260505.json` (7/7 pass, pass_rate 100.0%)
  - 검증 실행 2차: `docs/evidence/sorisae-dispatch-security-gate4-round2-20260505.json` (7/7 pass, pass_rate 100.0%)
  - 비고: 시나리오/판정 상세는 `docs/evidence/sorisae-dispatch-security-gate4-validation-rounds-20260505.md` 참고

### 5) 모바일 시나리오 실사용 테스트
- 상태: 구현됨
- 목표:
  - APK 앱(서버 연동형)에서 실제 사용자 흐름이 끊김 없이 동작하는지 확인
- 완료 기준:
  - 로그인 -> 기능 호출 -> 결과 확인 -> 재시도/오류 처리 흐름 검증
  - Android 실제 디바이스 또는 에뮬레이터에서 2회 반복 통과
- 증거 기록:
  - 검증 실행 1차:
  - 검증 실행 2차:
  - 비고:

## 최종 판정
- 현재 판정: 구현됨
- 완료됨 전제 조건:
  - 위 5개 항목의 증거 기록 2회씩 채워짐
  - 차단 항목 없음
