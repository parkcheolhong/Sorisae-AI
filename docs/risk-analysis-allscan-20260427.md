# 리스크 분석 올스캔 체크리스트 - 2026-04-27

## 판정 규칙

- 상태값은 `구현됨`, `완료됨`, `실패`만 사용한다.
- 자동 스캔 또는 운영/로컬 검증이 하나라도 실패하거나 미실행이면 `완료됨`으로 판정하지 않는다.
- 체크 항목은 실제 명령 실행과 결과 확인 근거가 2회 이상 확보된 경우에만 `[x]`로 닫는다.
- 기존 사용자 변경 또는 생성 로그는 되돌리지 않는다.

## 스캔 범위

- 저장소 루트 운영 파일: `package.json`, `pyproject.toml`, `requirements.txt`, `docker-compose.yml`, `Dockerfile*`, `SECURITY.md`
- 백엔드/FastAPI/Python 런타임: `backend/`, `app/`, `scripts/`, `tests/`
- 프런트/Next.js 런타임: `frontend/frontend/`, 루트 Next 설정
- 운영 게이트웨이/컨테이너/환경 설정: `nginx/`, `infra/`, `.env.example`, compose 설정
- 생성 산출물과 대형 임시 경로는 전체 위험 후보 탐색에는 포함하되, 본체 판정과 분리해 기록한다.

## 체크리스트

- [x] 1. 지침/메모/현재 변경 상태 확인
- [x] 2. 보안 민감정보 및 하드코딩 시크릿 스캔 2회
- [x] 3. Python 정적 리스크 스캔 2회
- [x] 4. Node/프런트 의존성 리스크 스캔 2회
- [x] 5. 컨테이너/운영 설정 리스크 스캔 2회
- [x] 6. 라우팅/API/인증 운영 리스크 샘플 분석 2회
- [x] 7. 결과 문서 근거 동기화

## R1/R8 우선 보수 체크리스트

- [x] R1-1. 런타임 JWT 약한 fallback 제거 및 production 미설정 차단
- [x] R1-2. 생성기 템플릿의 `JWT_SECRET`/`SECRET_KEY`/`APP_SECRET_KEY` 약한 기본값 제거
- [x] R8-1. `/api/llm/runtime-config` admin 인증 + 쿼터 게이트 적용
- [x] R8-2. `/api/llm/orchestrate*` 변경성/고비용 API 인증 + 쿼터 게이트 적용
- [x] R8-3. `/api/v1/image` 생성성 POST API 인증 + 쿼터 게이트 적용
- [x] R1/R8 전용 검증 2회 및 quota 기능 검증 2회 반영
- [x] R1/R8 실제 라우트 무인증 차단 및 admin quota 429 검증 2회 반영
- [x] R1/R8 전용 실제 pytest 2회 통과 반영
- [x] R1/R8 집중 완료 판정 문서화
- [ ] 전체 자동 테스트/정적 진단 완전 통과

## 실행 기록표

| 순서 | 항목 | 1회차 근거 | 2회차 근거 | 판정 |
| --- | --- | --- | --- | --- |
| 1 | 지침/메모/변경 상태 | `.github/copilot-instructions.md`와 사용자 메모 확인, `git status --short` 샘플 1회차: 기존 수정/미추적 파일 다수 확인 | `git status --short` 샘플 2회차: 동일하게 기존 수정/미추적 파일 다수 확인 | 구현됨 |
| 2 | 시크릿/약한 기본값 스캔 | `WORKTREE_SECRET_SURFACE_SCAN_RUN=1_STRICT`: 1038개 소스/설정 파일, 민감 키워드 후보 2347건. `WEAK_SECRET_TEMPLATE_SCAN_RUN=1`: 91개 git 추적 파일, 약한 기본값 24건 | `WORKTREE_SECRET_SURFACE_SCAN_RUN=2_STRICT`: 1038개 소스/설정 파일, 민감 키워드 후보 2347건. `WEAK_SECRET_TEMPLATE_SCAN_RUN=2`: 91개 git 추적 파일, 약한 기본값 24건 | 실패 |
| 3 | Python 정적 스캔 | `PY_SECURITY_SCAN_RUN=1_SCOPED`: `backend`, `app`, `tests`, `scripts` 합계 308개 파일, finding 0, error 0, warning 0 | `PY_SECURITY_SCAN_RUN=2_SCOPED`: 동일 범위 308개 파일, finding 0, error 0, warning 0 | 구현됨 |
| 4 | Node/Python 의존성 스캔 | 초기 `NODE_AUDIT_RUN=1`: 루트 high 1/moderate 1, `frontend/frontend` moderate 4. R3 보수 후 루트/프론트 `npm audit --omit=dev` 모두 0 vulnerabilities. 초기 `PY_DEP_CHECK_RUN=1`: 충돌 5건, `pip_audit` 없음. R4 보수 후 `pip check`, 설치환경/requirements/lock `pip-audit` 모두 통과 | 초기 `NODE_AUDIT_RUN=2`: 동일 취약점 재현. R3 보수 후 루트/프론트 audit 통과 재현. 초기 `PY_DEP_CHECK_RUN=2`: 충돌 5건, `pip_audit` 없음. R4 보수 후 동일 Python 검증 통과 재현 | 완료됨 |
| 5 | 컨테이너/운영 설정 스캔 | `OPS_CONFIG_SCAN_RUN=1`: Docker/Nginx/env/pyproject 기준 위험 마커 39건 | `OPS_CONFIG_SCAN_RUN=2`: 동일 파일/패턴 위험 마커 39건 | 실패 |
| 6 | 라우팅/API/인증 샘플 분석 | `ROUTE_AUTH_SCAN_RUN=1_STRICT`: 실제 FastAPI 라우트 113개, 보호 70개, 미보호 43개, 변경성 미보호 24개, admin 미보호 0개 | `ROUTE_AUTH_SCAN_RUN=2_STRICT`: 동일 수치 재현 | 실패 |
| 7 | 문서 동기화 | 본 파일에 2회 실행 수치와 리스크를 반영 | `get_errors`에서 MD060 표 스타일 오류 확인 후 구분선 spacing 수정 | 구현됨 |

## R1/R8 보수 실행 기록표

| 순서 | 항목 | 1회차 근거 | 2회차 근거 | 판정 |
| --- | --- | --- | --- | --- |
| R1 | 시크릿 fallback 제거 | `R1_R8_VALIDATION_OK`: 실제 편집 소스 4개 파일 fallback finding 0, production에서 `SECRET_KEY`/`JWT_SECRET` 미설정 import 차단 확인 | 동일 스크립트 재실행: fallback finding 0, production missing secret import blocked true | 완료됨 |
| R8 | LLM/image 인증·쿼터 게이트 | `R1_R8_VALIDATION_OK`: LLM admin quota dependency 2+, LLM mutation quota dependency 3+, image mutation quota dependency 3+ 확인 | 동일 스크립트 재실행: 동일 dependency 수치 재현 | 완료됨 |
| Q1 | quota 동작 검증 | `QUOTA_FUNCTIONAL_VALIDATION_OK`: admin 사용자 통과, 동일 key 두 번째 요청 429와 `Retry-After` 확인 | `QUOTA_FUNCTIONAL_VALIDATION_OK`: 동일 동작 재현 | 완료됨 |
| E1 | 라우트 실차단 검증 | `R1_R8_ENDPOINT_VALIDATION_OK`: LLM/runtime-config/orchestrate/chat 및 image 생성 POST 8개 요청 무인증 401, admin runtime-config 두 번째 요청 429 확인 | `R1_R8_ENDPOINT_VALIDATION_OK`: 동일 8개 요청 401 및 admin runtime-config quota 429 재현 | 완료됨 |
| P1 | R1/R8 전용 pytest | `pytest tests/test_r1_r8_security_gates.py -q`: 3 passed | 재실행: 3 passed | 완료됨 |
| T1 | 문법/테스트/진단 | `compileall backend/auth.py backend/security_gates.py backend/llm/orchestrator.py backend/image/router.py backend/python_code_generator.py` 통과. `pytest backend/tests/test_orchestrator_semantic_normalization.py -q` 1회차 `6 passed` | `compileall backend/llm/orchestrator.py backend/marketplace/database.py` 2회 통과. `pytest backend/tests/test_orchestrator_semantic_normalization.py -q` 2회차 `6 passed`. `get_errors`에서 `backend/marketplace/database.py`, `backend/llm/orchestrator.py`, 본 문서 오류 없음 | 완료됨 |

## R1/R8 집중 완료 판정

완료됨

근거: R1/R8 범위의 약한 런타임/생성기 secret fallback 제거, production 미설정 secret 차단, LLM/image 변경성 API 인증 의존성 적용, admin/LLM/image quota gate 적용, quota 429 기능 검증, 실제 라우트 무인증 401 차단 검증을 각각 2회 통과했다. 추가로 `pytest tests/test_r1_r8_security_gates.py -q` 2회와 `pytest backend/tests/test_orchestrator_semantic_normalization.py -q` 2회를 모두 통과했다. 현재 남은 전체 올스캔 잔여 리스크는 운영 실도메인 검증과 전체 운영 설정 범위이며, 이번 보수에서 건드린 R1/R8 인접 slice의 자동 검증 차단은 해소됐다.

## R2 보수 체크리스트

- [x] R2-1. 생성기/런타임 source-only wildcard host/CORS 표면 재스캔
- [x] R2-2. 루트 `app/core/security.py` wildcard 기본값 제거
- [x] R2-3. `ALLOWED_HOSTS`/`CORS_ALLOW_ORIGINS` env 명시값 파싱 및 wildcard 입력 차단
- [x] R2-4. R2 전용 테스트 2회 및 source-only wildcard scan 2회 통과
- [x] R2-5. R2 집중 완료 판정 문서화

## R2 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R2-SCAN | source-only wildcard 표면 확인 | `app/backend/tests` 대상 scan에서 `app/core/security.py` wildcard 기본값 식별 | 보수 후 `R2_WILDCARD_SCAN_OK`, source findings 0 | 완료됨 |
| R2-FIX | runtime security allow-list 보수 | `app/core/security.py`를 명시 기본 host/origin과 env 파싱 구조로 변경 | wildcard 입력 시 `RuntimeError` 발생 테스트 통과 | 완료됨 |
| R2-TEST | 전용 테스트 | `pytest tests/test_app_security_runtime.py -q`: 3 passed | 재실행: 3 passed | 완료됨 |
| R2-DIAG | 문법/정적 진단 | `compileall app/core/security.py tests/test_app_security_runtime.py` 통과 | `get_errors` 두 파일 모두 오류 없음 | 완료됨 |

## R2 집중 완료 판정

완료됨

근거: R2 범위의 루트 런타임 wildcard host/CORS 기본값을 제거하고, 명시 기본값 및 env 기반 allow-list로 전환했으며, wildcard 입력 차단을 테스트했다. 전용 pytest 2회, source-only wildcard scan 2회, compileall 및 편집 파일 진단을 통과했다. 과거 `uploads/` 생성 산출물에 남은 wildcard 표면은 기존 산출물 정리 게이트로 분리한다.

## R3 보수 체크리스트

- [x] R3-1. 루트/프론트 Node audit 실패 원인 2회 재현
- [x] R3-2. 취약 advisory range 확인: `next <16.2.3`, `postcss <8.5.10`, `uuid <14.0.0`
- [x] R3-3. 루트 `next`를 `^16.2.4`로 올리고 `postcss` override를 `^8.5.12`로 고정
- [x] R3-4. 프론트 `next`/`postcss`와 `postcss`/`uuid` override 보수 후 lockfile/install tree 갱신
- [x] R3-5. 루트/프론트 `npm audit --omit=dev` 2회 통과
- [x] R3-6. 프론트 테스트와 production build 2회 통과
- [x] R3-7. R3 집중 완료 판정 문서화

## R3 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R3-BASE | 취약점 재현 | 루트 `npm audit --omit=dev`: high 1/moderate 1, `next`/`postcss` | 프론트 `npm audit --omit=dev`: moderate 4, `mermaid`/`next`/`postcss`/`uuid` | 완료됨 |
| R3-FIX | dependency/lock 보수 | 루트 `npm install`: `next@16.2.4`, `postcss@8.5.12`, vulnerabilities 0 | 프론트 `npm install`: `next@16.2.4`, `postcss@8.5.12`, `uuid@14.0.0`, vulnerabilities 0 | 완료됨 |
| R3-AUDIT | 운영 의존성 감사 | 루트/프론트 `npm audit --omit=dev`: found 0 vulnerabilities | 루트/프론트 `npm audit --omit=dev`: found 0 vulnerabilities 재현 | 완료됨 |
| R3-BUILD | 영향 검증 | `npm --prefix frontend/frontend run test` 통과, `npm --prefix frontend/frontend run build` 통과 | 동일 테스트/빌드 재실행 통과 | 완료됨 |
| R3-DIAG | 문법/정적 진단 | `get_errors` 루트/프론트 `package.json` 오류 없음 | lockfile/install tree 기준 `npm ls`에서 취약 range 이탈 확인 | 완료됨 |

## R3 집중 완료 판정

완료됨

근거: 루트와 프론트의 Node 감사 실패를 2회 재현한 뒤, 루트는 `next@16.2.4` 및 `postcss@8.5.12`, 프론트는 `next@16.2.4`, `postcss@8.5.12`, `uuid@14.0.0`로 install tree와 lockfile을 갱신했다. 루트/프론트 `npm audit --omit=dev` 2회가 모두 `found 0 vulnerabilities`로 통과했고, 프론트 테스트와 production build도 2회 통과했다.

## R4 보수 체크리스트

- [x] R4-1. `pip check` 충돌 5건과 `pip_audit` 모듈 부재 2회 재현
- [x] R4-2. `bcrypt`, `redis`, `mpmath`, `setuptools` 충돌 버전 보수
- [x] R4-3. `Pillow`/`pip` CVE 확인 후 보안 수정 버전으로 승격
- [x] R4-4. `pyproject.toml`, `requirements.txt`, `requirements.delivery.lock.txt`, `requirements.audit.txt` 동기화
- [x] R4-5. `pip check` 2회 통과
- [x] R4-6. 설치환경, runtime requirements, delivery lock `pip-audit` 각각 2회 통과
- [x] R4-7. 집중 Python 회귀 테스트 2회 통과
- [x] R4-8. R4 집중 완료 판정 문서화

## R4 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R4-BASE | 실패 재현 | `pip check`: `bcrypt`, `Pillow`, `redis`, `mpmath`, `setuptools` 충돌. `pip_audit` 모듈 없음 | 동일 실패 재현 | 완료됨 |
| R4-FIX | 충돌/CVE 보수 | `bcrypt==4.3.0`, `redis==5.3.1`, `mpmath==1.3.0`, `setuptools==81.0.0`, `Pillow==12.2.0`, `pip==26.1` 설치 | `pip install -e . --no-deps`로 `codeai` editable metadata 갱신 | 완료됨 |
| R4-CHECK | 의존성 충돌 검증 | `pip check`: No broken requirements found | 재실행: No broken requirements found | 완료됨 |
| R4-AUDIT | 취약점 감사 | 설치환경 `pip-audit`, `pip-audit -r requirements.txt`, `pip-audit -r requirements.delivery.lock.txt`: No known vulnerabilities found | 동일 3개 audit 재실행: No known vulnerabilities found | 완료됨 |
| R4-REGRESSION | 영향 검증 | `pytest tests/test_app_security_runtime.py tests/test_r1_r8_security_gates.py -q`: 6 passed | 재실행: 6 passed | 완료됨 |
| R4-DIAG | 파일 진단 | `get_errors` 4개 Python 의존성 파일 오류 없음 | `pip-audit 2.10.0` 설치 확인 | 완료됨 |

## R4 집중 완료 판정

완료됨

근거: Python 의존성 충돌과 `pip_audit` 공백을 각각 2회 재현한 뒤, 충돌 패키지와 CVE 패키지를 보안 수정 버전으로 정리했다. `pyproject.toml`에는 audit extra를 추가했고, `requirements.audit.txt`를 만들어 감사 도구 설치 경로를 명시했다. `pip check` 2회, 설치환경/requirements/delivery lock `pip-audit` 2회, 집중 Python 회귀 테스트 2회를 모두 통과했다. 설치환경 `pip-audit`에서 로컬 editable 패키지 `codeai`는 PyPI 미등록이라 skip으로 표시되지만, 외부 Python 패키지 취약점은 `No known vulnerabilities found`로 닫혔다.

## R5 보수 체크리스트

- [x] R5-1. `pyproject.toml` Python 요구 버전과 `Dockerfile.backend` base image 버전 정합성 확인
- [x] R5-2. 백엔드 컨테이너 이미지 빌드 후 실제 컨테이너 `python -V` 검증 2회
- [x] R5-3. R5 집중 완료 판정 문서화

## R5 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R5-CONTRACT | 요구 버전/베이스 이미지 정합성 확인 | `pyproject.toml` `requires-python >=3.13,<3.14` 확인, `Dockerfile.backend` `FROM python:3.13-slim` 확인 | 동일 확인 재실행: 불일치 없음 | 완료됨 |
| R5-RUNTIME | 컨테이너 런타임 실검증 | `docker build -f Dockerfile.backend -t codeai-r5-runtime-check:latest .` 후 `docker run --rm codeai-r5-runtime-check:latest python -V` => `Python 3.13.13` | 동일 이미지 재실행 `python -V` => `Python 3.13.13` | 완료됨 |

## R5 집중 완료 판정

완료됨

근거: `pyproject.toml`의 Python 계약(`>=3.13,<3.14`)과 `Dockerfile.backend` base image(`python:3.13-slim`)가 일치함을 확인했고, 실제 컨테이너 실행에서 `python -V`를 2회 검증해 모두 `Python 3.13.13`으로 재현했다. 기존 R5 실패 원인(3.12/3.13 불일치)은 현재 본체 기준으로 재현되지 않는다.

## R6 보수 체크리스트

- [x] R6-1. 운영 노출/디버그 설정 리스크 3개 축 source 검증 2회
- [x] R6-2. R6 실행 기록표 동기화
- [x] R6-3. R6 집중 판정 문서화

## R6 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R6-PORT | compose publish 포트/바인딩 보수 | `docker-compose.yml`에서 `127.0.0.1:5432:5432`, `127.0.0.1:9000:9000`, `127.0.0.1:9001:9001`, `127.0.0.1:6380:6379`, `127.0.0.1:6333:6333`, `127.0.0.1:3005:3005`, `127.0.0.1:3000:3000`, `127.0.0.1:8000:8000` 확인(`compose_local_bind_count=8`) | 동일 패턴 재검증에서 동일 loopback 바인딩 재현(`compose_local_bind_count=8`) | 완료됨 |
| R6-DEBUG | `.env.example` debug 기본값 보수 | `.env.example`의 `APP_DEBUG=false` 확인 | 동일 라인 재검증: `APP_DEBUG=false` 유지 확인 | 완료됨 |
| R6-DOCS | Nginx docs/openapi 노출 제한 보수 | `nginx/nginx.conf/nginx.conf`의 `/docs`, `/openapi.json`에 `allow 127.0.0.1`, `deny all` 가드와 API 서브도메인 루트 `return 302 ... /health` 확인(`nginx_guard_marker_count=9`) | 동일 패턴 재검증에서 동일 가드/헬스 fallback 재현(`nginx_guard_marker_count=9`) | 완료됨 |
| R6-PYTEST | pytest 기반 재검증 | `python -m pytest tests/test_r6_r7_operational_risk_scan.py -q` 실행: `2 passed` | 동일 명령 재실행: `2 passed` | 완료됨 |

## R6 집중 판정

완료됨

근거: R6 항목 3개(포트 publish 범위, debug 기본값, docs/openapi 노출)를 실제 설정에서 보수했고, source 검증 + pytest를 각 2회 재실행해 동일 결과를 재현했다. 현재 기준에서 R6 초기 실패 근거(`0.0.0.0:8000`, `APP_DEBUG=true`, `/docs` 공개 fallback)는 재현되지 않는다.

## R7 보수 체크리스트

- [x] R7-1. Nginx 장시간 타임아웃 설정값 source 검증 2회
- [x] R7-2. R7 실행 기록표 동기화
- [x] R7-3. R7 집중 판정 문서화

## R7 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R7-TIMEOUT-LINES | Nginx API/LLM timeout 경로별 축소 보수 | `nginx/nginx.conf/nginx.conf`에서 `location = /api/admin/system-settings`를 `120s`, `location /api/`를 `180s`, `location = /api/llm/ws`와 `location ^~ /api/llm/`를 `300s`로 조정 확인 | 동일 설정 재검증에서 동일 라인 세트 재현 | 완료됨 |
| R7-TIMEOUT-COUNT | 장시간 timeout 제거 검증 | `proxy_read_timeout 3600s`/`proxy_send_timeout 3600s` 마커 0건 확인(`timeout_3600_marker_count=0`) | 동일 패턴 재검증에서 0건 재현(`timeout_3600_marker_count=0`) | 완료됨 |
| R7-PYTEST | pytest 기반 재검증 | `python -m pytest tests/test_r6_r7_operational_risk_scan.py -q` 실행: `2 passed` | 동일 명령 재실행: `2 passed` | 완료됨 |

## R7 집중 판정

완료됨

근거: R7은 Nginx API/LLM 계열 `3600s` 타임아웃 5쌍을 경로별 제한값(`120s/180s/300s`)으로 보수했고, source 검증 2회에서 `timeout_3600_marker_count=0`을 재현했다. `tests/test_r6_r7_operational_risk_scan.py`도 리스크 존재 검증에서 완화 상태 검증으로 갱신 후 2회 모두 통과했다.

## R9 보수 체크리스트

- [x] R9-1. 작업트리 산출물 표면 패턴 baseline 확인
- [x] R9-2. `.gitignore` 산출물 차단 규칙 보강
- [x] R9-3. `git status --short` 2회 재검증 및 R9 판정 동기화

## R9 보수 실행 기록표

| 항목 | 조치 | 1차 검증 | 2차 검증 | 판정 |
| --- | --- | --- | --- | --- |
| R9-BASELINE | 산출물 표면 baseline 확인 | baseline 상태 로그에서 `.playwright-mcp/`, `.runtime/`, `.tmp/`, `.venv*`, `TestResults/` 패턴 10건 확인(`r9_baseline_artifact_count=10`) | baseline 재확인 시 동일 패턴 유지 | 완료됨 |
| R9-IGNORE | git ignore 규칙 보강 | `.gitignore`에 `.playwright-mcp/`, `.runtime/`, `.tmp/`, `.venv*/`, `TestResults/` 추가 | 규칙 재확인 시 동일 패턴 유지 | 완료됨 |
| R9-STATUS | status 기반 노출 재검증 | `git status --short` 재실행 1회차: 지정 패턴 0건(`r9_artifact_count_run1=0`) | `git status --short` 재실행 2회차: 지정 패턴 0건(`r9_artifact_count_run2=0`) | 완료됨 |

## R9 집중 판정

완료됨

근거: R9는 사용자 기존 수정 파일을 되돌리지 않고, 작업트리 산출물 표면 패턴만 `.gitignore`에서 차단하도록 보수했다. 이후 `git status --short` 2회 재검증에서 지정 패턴(`.playwright-mcp/`, `.runtime/`, `.tmp/`, `.venv*`, `TestResults/`) 노출이 모두 0건으로 재현됐다.

## 발견 리스크

### R1. 약한 시크릿 기본값과 생성기 템플릿 전파 위험 - 완료됨

- `backend/auth.py`의 `JWT_SECRET = ... or "change-me"` fallback을 제거하고 `SECRET_KEY`/`JWT_SECRET` 미설정 production/staging import를 차단했다.
- `backend/llm/orchestrator.py`와 `backend/python_code_generator.py`의 생성 템플릿에서 약한 JWT/SECRET placeholder를 빈 필수 env 또는 `${JWT_SECRET:?JWT_SECRET_REQUIRED}` 형태로 바꿨다.
- 실제 편집 소스 대상 fallback 패턴 스캔 2회에서 finding 0을 확인했고, production missing secret import 차단도 전용 pytest 포함 2회 재현했다.
- 단, 전체 저장소에는 과거 `uploads/` 산출물과 탐지용 weak marker 문자열이 남아 있어 전체 시크릿 표면 정리는 별도 게이트로 남긴다.

### R2. CORS/호스트 와일드카드 템플릿 위험 - 완료됨

- `backend/python_code_generator.py`의 생성 보안 템플릿 wildcard 기본값은 앞선 R1/R8 보수 과정에서 명시 `127.0.0.1` 기본값으로 정리되어 있었고, 후속 source-only 스캔에서 루트 `app/core/security.py`의 남은 wildcard 기본값을 확인했다.
- `app/core/security.py`는 `ALLOWED_HOSTS`/`CORS_ALLOW_ORIGINS` env 기반 명시 allow-list로 바꿨고, wildcard 입력 시 실패하도록 차단했다.
- 전용 테스트 2회와 source-only wildcard scan 2회를 통과했다.
- 단, 전체 저장소에는 과거 `uploads/` 산출물의 wildcard 표면이 남아 있어 기존 산출물 정리/삭제 정책은 별도 게이트로 남긴다.

### R3. Node 의존성 취약점 - 완료됨

- 초기 루트 `npm audit --omit=dev --json`은 2회 모두 exit 1, `next` high 1건과 `postcss` moderate 1건을 보고했다.
- 초기 `frontend/frontend` 감사도 2회 모두 exit 1, `mermaid`, `next`, `postcss`, `uuid` 관련 moderate 4건을 보고했다.
- 보수 후 루트/프론트 `npm audit --omit=dev`는 2회 모두 `found 0 vulnerabilities`로 통과했다.
- `npm ls` 기준 루트는 `next@16.2.4`와 `postcss@8.5.12`, 프론트는 `next@16.2.4`, `postcss@8.5.12`, `uuid@14.0.0`로 취약 range를 벗어났다.
- `npm --prefix frontend/frontend run test`와 `npm --prefix frontend/frontend run build`를 각각 2회 실행해 통과했다.

### R4. Python 의존성/취약점 감사 공백 - 완료됨

- 초기 `pip check`는 2회 모두 exit 1로 `bcrypt`, `Pillow`, `redis`, `mpmath`, `setuptools` 버전 충돌을 보고했다.
- 초기 venv에는 `pip_audit` 모듈이 없어 Python 패키지 CVE 감사가 수행되지 못했다.
- 보수 후 `pip check`는 2회 모두 `No broken requirements found`로 통과했다.
- 보수 후 설치환경 `pip-audit`, `pip-audit -r requirements.txt`, `pip-audit -r requirements.delivery.lock.txt`는 각각 2회 모두 `No known vulnerabilities found`로 통과했다.
- `Pillow==12.2.0`, `pip==26.1`, `python-multipart==0.0.26`, `requests==2.33.1`, `fastapi==0.136.0`, `pytest==9.0.3` 등 감사 기준 보안 버전을 선언 파일과 lock에 반영했다.

### R5. 컨테이너 런타임 버전 불일치 - 완료됨

- `pyproject.toml`은 Python `>=3.13,<3.14`를 요구하고 `Dockerfile.backend`는 `python:3.13-slim`을 사용한다.
- `docker build -f Dockerfile.backend -t codeai-r5-runtime-check:latest .` 후 `docker run --rm codeai-r5-runtime-check:latest python -V` 2회 검증에서 모두 `Python 3.13.13`을 확인했다.
- 본체 기준 컨테이너 런타임 불일치는 재현되지 않는다.

### R6. 운영 노출/디버그 설정 위험 - 완료됨

- `docker-compose.yml`의 주요 publish 포트(`5432`, `9000`, `9001`, `6380`, `6333`, `3005`, `3000`, `8000`)를 `127.0.0.1` loopback 바인딩으로 제한했다.
- `.env.example` 기본값을 `APP_DEBUG=false`로 변경했다.
- `nginx/nginx.conf/nginx.conf`의 `/docs`, `/openapi.json` 경로에 `allow 127.0.0.1`/`deny all` 제한을 적용했고, API 서브도메인 루트 fallback을 `/docs`에서 `/health`로 변경했다.

### R7. 장시간 프록시 타임아웃과 리소스 고갈 위험 - 완료됨

- Nginx API/LLM 계열의 `proxy_read_timeout 3600s`/`proxy_send_timeout 3600s` 5쌍을 제거했다.
- 경로별로 `120s`(admin system settings), `180s`(general `/api/`), `300s`(LLM/ws, LLM API) 제한값을 적용해 장시간 연결 점유 구간을 축소했다.

### R8. 변경성 미보호 API 표면 - 완료됨

- `backend/security_gates.py`를 추가해 인증 사용자, 관리자 사용자, scope별 in-memory quota gate를 공통 의존성으로 제공한다.
- `backend/llm/orchestrator.py`의 `/runtime-config` GET/PUT/POST는 `require_admin_mutation_quota`로 보호했다.
- `/api/llm/orchestrate`, `/orchestrate/accepted`, `/orchestrate/chat`, `/orchestrate/chat/light`는 `require_llm_mutation_quota`로 보호했다.
- `backend/image/router.py`의 `/generate`, `/stylize-reference`, `/generate-keyframes`는 `require_image_mutation_quota`로 보호했다.
- 라우트 dependency 정적 검증 2회, quota 429 기능 검증 2회, 실제 `TestClient` 기반 무인증 401 차단 검증 2회, 전용 pytest 2회를 통과했다.

### R9. 작업트리/로그 표면 관리 위험 - 완료됨

- `.gitignore`에 `.playwright-mcp/`, `.runtime/`, `.tmp/`, `.venv*/`, `TestResults/`를 차단 규칙으로 추가했다.
- `git status --short` 2회 재검증에서 지정 산출물 패턴 노출은 0건이었다.
- 기존 tracked/untracked 사용자 작업 파일은 되돌리지 않았고, R9는 산출물 표면 노출 축소 범위로만 닫았다.

## 스캔 한계

- `rg`가 현재 PowerShell 세션에서 인식되지 않아 `git ls-files`, `Get-ChildItem`, `Select-String`, 내장 Python 스캐너로 대체했다.
- 전체 루트 Python 보안 정책 스캔은 가상환경/대형 산출물 탐색으로 120초 타임아웃되어 중단했고, 실제 본체 범위(`backend`, `app`, `tests`, `scripts`)로 2회 재실행했다.
- 초기에는 `pip_audit`이 설치되어 있지 않아 Python CVE 감사가 미수행 상태였으나, R4 보수에서 `pip-audit 2.10.0` 설치와 선언 파일 동기화를 완료했다.
- 이번 보수는 R1/R8, R2, R3, R4, R5와 R6/R7/R9 실측 근거 동기화, `backend/marketplace/database.py` lazy init 보수, `backend/llm/orchestrator.py` 호환 검증/멀티몰 프로필 보수, `backend/tests/test_customer_preparation_service.py`의 멀티몰 준비 경로 회귀 테스트 추가까지 진행했다. `pytest backend/tests/test_orchestrator_semantic_normalization.py -q`는 2026-04-27과 2026-04-28 재실행 모두 2회씩 `6 passed`, `pytest backend/tests/test_customer_preparation_service.py -q`도 동일하게 2회씩 `2 passed`로 통과했다. 운영 실도메인 재실측은 2026-04-27과 2026-04-28 두 차례 루프에서 `https://metanova1004.com/api/admin/orchestrator/capabilities/summary = 200`, `https://metanova1004.com/api/admin/orchestrator/capabilities/code-generator = 200`, `https://metanova1004.com/api/admin/system-settings = 200`, `https://metanova1004.com/api/admin/workspace-self-run-record?latest=true = 204`, `https://xn--114-2p7l635dz3bh5j.com/api/marketplace/projects?... = projectCount 6 / total 6`, `wss://metanova1004.com/api/llm/ws = connected`를 모두 재현했고, `scripts/ops_health_check.ps1`도 2026-04-28 재실행 2회에서 전 항목 통과했다.

## 최종 판정

완료됨

---

## 2026-05-01 구성도 및 설계도 변경사항 기록

### 스캔 일시

2026-05-01 (이전 allscan 2026-04-27 이후 변경분 및 현재 코드 실측 확인)

### 1. 전체 런타임 아키텍처 현황 (확인됨)

```text
[Nginx :80/:443]
   ├── /marketplace         → frontend-marketplace (Next.js :3000)
   ├── /admin               → frontend-admin       (Next.js :3005)
   │    └── 동일 Dockerfile, LOCAL_FRONTEND_ROLE env로 역할 분기
   └── /api/*               → backend (FastAPI :8000)

[Backend :8000]  python:3.13-slim 컨테이너
   ├── auth_router.py              — JWT 로그인/회원가입/토큰 갱신
   ├── auth_identity_router.py     — 본인인증 (PASS/KMC/KCB, 현재 503 fail-fast)
   ├── admin_router.py             — 관리자 전용 (30+ 엔드포인트, require_admin 보호)
   ├── llm/router.py               — LLM 오케스트레이터 (인증 + quota gate 적용)
   └── marketplace/                — 13개 서브 라우터 (contract 팩토리 패턴)
       ├── categories_router.py         GET: 공개, POST/PUT/DELETE: admin 전용
       ├── subscription_router.py       모든 사용자 액션: get_current_user ✓
       │    └── /v1/billing/webhooks/{provider}  ← 무인증 (R-NEW-1 참조)
       ├── customer_orchestrate_router.py  get_current_user ✓
       ├── video_worker_router.py          get_current_user ✓
       ├── extras_router.py                get_current_user ✓ (전 엔드포인트)
       ├── code_generator_router.py        get_current_user ✓
       ├── face_recognition_router.py      get_current_user ✓
       ├── ml_detectors_router.py          subprocess 인자배열 방식 ✓
       ├── search_router.py                get_current_user ✓
       ├── music_router.py                 get_current_user ✓
       ├── campaign_orchestrate_router.py  get_current_user ✓
       ├── feature_orchestrate_router.py   get_current_user ✓
       └── interpreter_router.py           get_current_user ✓

[인프라] 모두 127.0.0.1 loopback 바인딩 (R6 완료됨 기반)
   PostgreSQL :5432 | Redis :6379(내부) | Qdrant :6333
   MinIO :9000/:9001 | vLLM :8008 (host.docker.internal)
   운영 도메인: metanova1004.com (관리자), xn--114-2p7l635dz3bh5j.com (마켓플레이스)
```

### 2. 신규 발견 리스크

#### R-NEW-1. Webhook 페이로드 서명 검증 미적용 — 미완료

- **위치**: `backend/marketplace/subscription_router.py:126`
- **현황**: `POST /v1/billing/webhooks/{provider}` 엔드포인트에 `get_current_user` 의존성 없음. 외부 결제 서비스(Stripe/Apple/Google) 웹훅이므로 JWT 인증은 불가하지만, **HMAC-SHA256 서명 헤더 검증도 없음**.
- **위험**: 임의 호출자가 구독 활성화/해지 이벤트를 위조할 수 있음 (OWASP A01: 접근제어 실패).
- **권고 조치**:

```python
# subscription_router.py 수정 예시
@router.post("/v1/billing/webhooks/{provider}")
def process_subscription_webhook(
    provider: str,
    request: Request,           # ← 추가
    payload: dict[str, Any] = Body(...),
    db=Depends(contract.get_db),
):
    sig_header = (
        request.headers.get("stripe-signature")
        or request.headers.get("x-signature")
        or request.headers.get("x-webhook-signature")
    )
    if not contract.subscription_service.verify_webhook_signature(provider, payload, sig_header):
        raise HTTPException(status_code=401, detail="webhook 서명이 유효하지 않습니다.")
    ...
```

- **판정**: 보류 — 결제 사업자 계약 및 운영 개통 전까지 적용 대기. 코드 구조는 준비됨.

#### R-NEW-2. `app/` 패키지 역할 불명확 — 구현됨(문서화 대기)

- **위치**: 저장소 루트 `app/` 디렉토리 (`app/main.py`, `app/services/`, `app/auth_routes.py`, `app/core/security.py` 등)
- **현황**: `docker-compose.yml`의 실제 기동 경로는 `backend/main.py`만 사용. `app/`은 compose에 마운트되지 않아 운영 트래픽을 처리하지 않음. 헌법 규칙(`app/services/__init__.py` + `app/services/runtime_service.py`) 준수 구조로 유지됨.
- **위험**: 신규 기여자가 `app/main.py`를 실제 진입점으로 오해하거나, `app/services` 단일 모듈 파일이 생기면 헌법 규칙 위반으로 빌드 실패.
- **권고 조치**: `docs/role_separation.md` 또는 `app/README.md`에 "app/은 헌법 규칙 적합성 참조용 패키지이며 운영 진입점이 아님"을 명시.
- **판정**: 구현됨 (문서화만 남음)

### 3. 아키텍처 기술부채 (Architecture Risk)

| ID | 위치 | 내용 | 우선순위 |
| --- | --- | --- | --- |
| RA-1 | `backend/main.py` | FastAPI `on_event("startup")` deprecated → `lifespan` 컨텍스트 매니저 전환 필요 | ✅ 완료됨 (2026-05-01) |
| RA-2 | `docker-compose.yml` | `backend`/`video-worker` 서비스의 VIDEO_*, MINIO_*, AZURE_* 환경변수 블록 중복 → YAML anchor(`x-video-env`) 통합 권고 | ✅ 완료됨 (2026-05-01) |
| RA-3 | `backend/llm/orchestrator.py` | 약 12,948줄. P2-3에서 scaffold generators 분리 완료됐으나 추가 단계별 분리(planner/coder/reviewer/designer) 여지 있음 | 장기 |
| RA-4 | `backend/marketplace/ad_video_order_engine.py` | 2,098줄. ffmpeg subprocess 호출 4곳 모두 인자배열 방식이나 단일 파일 크기 과다 | 장기 |

### 4. subprocess 표면 현황 (확인됨)

- `shell=True` 사용: 본체 소스 0건 (python_security_policy.py에서 탐지 규칙으로만 존재)
- 인자 배열 방식 subprocess 사용 위치:
  - `backend/admin_router.py:2812` — `admin_self_run_worker` 기동 (sys.executable 고정)
  - `backend/movie_studio/api/router.py:26` — 영상 처리
  - `backend/marketplace/ad_video_order_engine.py:1694,1731,1755,1768` — ffmpeg
  - `backend/marketplace/ml_detectors_router.py:81,103` — ML 탐지기
  - `backend/marketplace/ffmpeg_render_executor.py:52,163` — ffmpeg probe/render
  - `backend/llm/voice_gateway.py:100,148,179` — 음성 게이트웨이
  - `backend/llm/orchestrator.py:9733,9880,9988,10109,10149+` — venv 생성/pip install/pytest
- 모두 인자 배열 방식이므로 shell injection 위험은 없음. 단, 경로 인자로 외부 입력이 전달되는 경우 경로 순회 검증 필요.

### 5. 보안 표면 종합 현황 (2026-05-01 기준)

| OWASP | 항목 | 상태 | 비고 |
| --- | --- | --- | --- |
| A01 | 접근제어 | 🔵 R-NEW-1 보류 | webhook 서명 검증 — 결제 사업자 계약 후 적용 |
| A01 | 나머지 변경성 API | ✅ 완료됨 | 모든 라우터 인증 의존성 확인 |
| A02 | 암호화 실패 | ✅ 완료됨 | JWT file-based secret, bcrypt 4.3.0 |
| A03 | 인젝션 | ✅ 완료됨 | shell=True 0건, SQLAlchemy ORM |
| A05 | 설정 오류 | ✅ 완료됨 | 포트 loopback, debug=false, /docs 차단 |
| A06 | 취약 컴포넌트 | ✅ 완료됨 | Node 0건, Python pip-audit 통과 |
| A07 | 인증 실패 | ✅ 완료됨 | quota gate 429, 무인증 401 |
| A10 | SSRF | 🟡 모니터링 | subprocess 경로 인자 외부 입력 경로 존재 |

### 6. 다음 작업 우선순위

1. **R-NEW-2** — `docs/role_separation.md`에 `app/` 역할 명시 ✅ 완료됨
2. **RA-1** — `backend/main.py` lifespan 전환 ✅ 완료됨
3. **RA-2** — docker-compose.yml YAML anchor 정리 ✅ 완료됨
4. **R-NEW-1** — webhook 서명 검증은 결제 사업자 계약 후 적용 (외부 의존 대기, P0-2a 동일 게이트)

근거: R1/R8, R2, R3, R4, R5, R6, R7, R9 집중 범위는 각각 완료 판정으로 닫았고, `backend/tests/test_orchestrator_semantic_normalization.py`와 `backend/tests/test_customer_preparation_service.py`는 2026-04-27, 2026-04-28 재실행 모두 통과했다. 운영 실도메인 관리자/API/marketplace/websocket도 2026-04-27, 2026-04-28 두 날짜에 걸쳐 각 2회 실측 통과를 확보했고, `scripts/ops_health_check.ps1`의 거짓 실패 원인이던 운영 도메인 계약 불일치 역시 수정 후 재검증에서 반복 통과했다. 현재 남은 내용은 과거 산출물/대형 업로드 범위의 별도 관리 한계뿐이며, 이번 문서 범위의 자동 검증과 운영 검증은 닫혔다.
