# 로그인/런타임 성능 진단 및 실검증 체크리스트 - 2026-05-08

## 범위
- 대상: 활성 백엔드 `backend/main.py` 기준 `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/admin/orchestrator/runtime-verification`, `GET /api/llm/runtime-config`
- 로컬 기준: `http://127.0.0.1:8000`
- 운영 기준: `https://metanova1004.com`
- 관리자 계정: 시크릿 파일 기반 고정 관리자 계정 사용. 비밀번호 값은 출력/기록하지 않음.

## 원인
- 로그인 자체는 정상 계정 기준 로컬 168~174ms로 병목이 아니었다.
- 활성 런타임 검증 라우터가 `build_runtime_verification_response()`에 필수 `mode` 인자를 넘기지 않아 dashboard/full 모두 500을 반환했다.
- 런타임 검증 서비스의 full 모드는 운영 evidence를 중복 수집해 불필요한 지연을 만들고 있었다.
- full 모드의 로컬 self-check 기본 포트가 활성 백엔드가 아닌 `8013`으로 남아 있었고, `.env`의 placeholder 도메인/포트(`validation.local`, `8001`)가 활성 컨테이너에서 닿지 않았다.
- WebSocket 검증기는 handshake 응답 뒤에 붙어 온 첫 프레임 바이트를 버려 간헐적으로 `timed out` 실패를 만들었다.

## 수정
- [x] `backend/admin_router.py`의 runtime-verification 요청 모델에 `mode: str = "dashboard"` 기본값 추가.
- [x] `backend/admin_router.py`에서 `build_runtime_verification_response()` 호출 시 `mode=payload.mode` 전달.
- [x] `backend/admin/orchestrator/runtime_verification_service.py` full 모드에서 operational evidence 중복 수집 제거.
- [x] 런타임 검증 로컬 API 기준 주소를 실제 reachable endpoint로 선택하도록 보정하고 기본 기준을 `127.0.0.1:8000`으로 복구.
- [x] placeholder 로컬 도메인에서는 frontend page target을 실제 backend API probe로 매핑.
- [x] `worker_log_path`가 비어 있는 상태는 traceback 실패가 아니라 skip/pass로 처리.
- [x] WebSocket handshake 이후 남은 buffered frame bytes를 보존해 간헐 timeout 제거.

## 자동 검증
- [x] 1차 컴파일: `docker exec devanalysis114-backend python -m py_compile /app/backend/admin_router.py /app/backend/admin/orchestrator/runtime_verification_service.py` 통과.
- [x] 2차 컴파일: WebSocket verifier 수정 후 동일 py_compile 통과.
- [x] 1차 테스트: `python -m pytest backend/tests/test_admin_project_root_service.py -q` -> `4 passed`.
- [x] 2차 테스트: WebSocket verifier 수정 후 동일 pytest -> `4 passed`.

## 로컬 실검증 2회

| 항목 | 1차 | 2차 | 판정 |
| --- | --- | --- | --- |
| 로그인 | `200`, `177ms`, token 발급 | `200`, `165ms`, token 발급 | 통과 |
| runtime dashboard | `200`, `35ms`, `FAILED=0`, `FINAL=passed` | `200`, `20ms`, `FAILED=0`, `FINAL=passed` | 통과 |
| runtime full | `200`, `6709ms`, `FAILED=0`, `FINAL=passed`, `OP_FAILED=0`, `OP_VERIFIED=5` | `200`, `6847ms`, `FAILED=0`, `FINAL=passed`, `OP_FAILED=0`, `OP_VERIFIED=5` | 통과 |
| LLM runtime-config | `200`, `15ms`, `7611 bytes` | `200`, `25ms`, `7611 bytes` | 통과 |

## 운영 실검증 2회

| 항목 | 1차 | 2차 | 판정 |
| --- | --- | --- | --- |
| 로그인 | `200`, `211ms`, token 발급 | `200`, `205ms`, token 발급 | 통과 |
| runtime dashboard | `200`, `21ms`, `FAILED=0`, `FINAL=passed` | `200`, `61ms`, `FAILED=0`, `FINAL=passed` | 통과 |
| runtime full | `200`, `7779ms`, `FAILED=0`, `FINAL=passed`, `OP_FAILED=0`, `OP_VERIFIED=5` | `200`, `7235ms`, `FAILED=0`, `FINAL=passed`, `OP_FAILED=0`, `OP_VERIFIED=5` | 통과 |
| LLM runtime-config | `200`, `20ms`, `7611 bytes` | `200`, `22ms`, `7611 bytes` | 통과 |

## 최종 체크리스트
- [x] 활성 라우트가 `backend/main.py` 기준임을 확인했다.
- [x] 정상 관리자 로그인 기준으로 기준 지연을 측정했다.
- [x] runtime-verification 500 원인을 코드 계약 누락으로 확인하고 수정했다.
- [x] full 런타임 검증의 중복 operational evidence 수집을 제거했다.
- [x] 로컬 self-check 주소/placeholder operational target 문제를 수정했다.
- [x] WebSocket operational 검증 간헐 timeout을 buffered frame 처리로 수정했다.
- [x] 로컬 자동 검증 2회 이상 통과했다.
- [x] 로컬 실 API 검증 2회 통과했다.
- [x] 운영 실 API 검증 2회 통과했다.

## 판정
- 상태: 완료됨
- 근거: 로컬/운영 모두 로그인, runtime dashboard, runtime full, LLM runtime-config가 2회씩 `200`으로 통과했고 runtime full의 `FINAL=passed`, `FAILED=0`, `OP_FAILED=0`, `OP_VERIFIED=5`가 확인됐다.
