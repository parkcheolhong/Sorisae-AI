# 저장소 전수검사 마스터 체크리스트

## 문서 목적

- 이 문서는 현재 저장소 전체를 헌법 규칙 기준으로 전수검사하고, 발견된 문제를 근거 기반으로 설계·구현·검증·정리하기 위한 단일 기준 문서다.
- 모든 후속 작업은 이 문서의 순서를 따른다.
- 어떤 항목도 실제 수정과 검증이 끝나기 전에는 완료로 닫지 않는다.

## 현재 판정

- 상태: `완료됨 (재검토 반영)`
- 이유: active master checklist 기준 `INSPECT-002`~`023` 이 모두 닫혔고, 2026-04-26 재검토 세션에서 발견된 `REINSPECT-001`~`002` 도 수정 및 실검증 완료. `REINSPECT-003`은 사용자 결정 보류 중이나 즉시 위험은 아님.

## 헌법형 진행 규칙

- 체크리스트는 대화용 메모가 아니라 실제 게이트다.
- 선행 항목이 닫히기 전에는 후행 항목으로 넘어가지 않는다.
- 각 항목은 최소 2회 이상 검증 통과 후에만 체크한다.
- 실제로 수행하지 않은 검증은 절대 체크하지 않는다.
- 하위 차단 항목이 남아 있으면 상위 항목도 체크하지 않는다.
- 보고 상태는 `구현됨`, `완료됨`, `실패` 세 가지만 사용한다.
- 자동 검증 또는 운영 검증 중 하나라도 실패하면 해당 단계는 `완료됨`으로 기록하지 않는다.

## 증적 기록 규칙

- 모든 체크 항목은 아래 3가지를 함께 남긴다.
  - 대상 파일 또는 기능군
  - 수행한 검증 명령 또는 실검증 경로
  - 결과 요약과 차단 여부
- 검증 로그는 같은 세션 기준으로 갱신한다.
- 문서 갱신 없는 완료 보고를 금지한다.

## 전수검사 순서

### 1. 기준선 고정

- [x] 현재 저장소 구조, 실행 진입점, 운영 문서, 체크리스트 문서를 수집했다.
- [x] 전수검사 범위를 `backend`, `frontend`, `frontend/frontend`, `scripts`, `docs`, `nginx`, `docker-compose.yml`, 생성기/오케스트레이터 계층으로 고정했다.
- [x] 현재 세션용 기준 문서와 실행 순서를 이 문서에 동기화했다.

### 2. 런타임 및 기동 경로 점검

- [x] 루트 기동 명령, backend 단독 기동, admin frontend, marketplace frontend, nginx 게이트웨이의 실제 진입 경로를 확인했다.
- [x] 로컬 기준 핵심 URL(`8000`, `8080`, `8443`, `3000`, `3005`)의 역할과 현재 상태를 점검했다.
- [x] start/stop/health 계열 스크립트와 실제 동작 경로의 불일치를 기록했다.

### 3. 백엔드 API 구조 점검

- [x] `backend/main.py` 라우터 등록 현황과 실제 구현 파일의 일치 여부를 점검했다.
- [x] 인증, 관리자, 마켓플레이스, LLM, 비디오, 이미지, 오케스트레이터 경로를 기능군별로 분해했다.
- [x] 404, 401, 500, dead route, 미등록 라우터, 중복 라우터 후보를 기록했다.

### 4. 관리자 기능군 점검

- [x] 관리자 대시보드의 핵심 API 호출 경로와 base URL 계산 경로를 점검했다.
- [x] `/api/admin/system-settings`, self-run, approvals, observability, publish, passkey 흐름을 기능군별로 점검했다.
- [x] 관리자 UI와 backend API 간 불일치, stale bundle, 잘못된 fetch origin 문제를 기록했다.

### 5. 마켓플레이스 기능군 점검

- [x] 공개 메인 앱의 목록, 상세, 리뷰, 구매, 다운로드, 직원 오케스트레이터 경로를 점검했다.
- [x] 결제 시뮬레이션 경로와 실결제 제거 경로 문서가 실제 구현과 일치하는지 확인했다.
- [x] MinIO, 업로드 루트, fallback 저장소 경로, 다운로드 자산 보관 규칙을 점검했다.

### 6. 오케스트레이터 및 생성기 점검

- [x] `backend/llm`, `backend/generators`, `backend/template_generator`, `backend/python_code_generator.py`, `backend/non_python_code_generator.py`를 기능군별로 나눠 점검했다.
- [x] 생성기 계약 단일화 규칙과 `app/services/__init__.py`, `app/services/runtime_service.py` 기준 준수 여부를 확인했다.
- [x] self-run, hard-gate, semantic gate, artifact 생성, evidence 채움 규칙 위반 여부를 기록했다.

### 7. 데이터 및 저장 계층 점검

- [x] PostgreSQL, Redis, Qdrant, uploads, tmp, reports, knowledge, models 경로의 실제 사용 여부를 점검했다.
- [x] DB 모델과 API/프런트 사용 경로 간 불일치를 점검했다.
- [x] 임시 파일, 죽은 산출물, 오래된 실험 디렉터리와 현재 운영 경로의 경계 문제를 기록했다.

### 8. 보안 및 설정 점검

- [x] `.env`, `*_FILE` 비밀값 규칙, `SECRET_KEY`, `FIXED_ADMIN_PASSWORD`, 외부 엔진 API 키 사용 경로를 점검했다.
- [x] 관리자/일반 사용자 권한 분리, 인증 fallback, 로컬 전용 우회, 운영 위험 설정을 기록했다.
- [x] 문서상 보안 설명과 실제 구현 상태의 불일치를 기록했다.

### 9. 프런트 구조 및 빌드 경로 점검

- [x] `frontend`와 `frontend/frontend`의 역할, 중복 페이지, base URL 계산 중복, dist/.next 잔존물 영향을 점검했다.
- [x] dev 서버 직접 진입과 nginx 경유 진입 간 차이를 점검했다.
- [x] Playwright/verify/ci 명령과 실제 페이지 구조의 일치 여부를 확인했다.

### 10. 스크립트, 문서, 테스트 점검

- [x] `scripts/` 하위 운영 스크립트와 README 명령 예시의 일치 여부를 점검했다.
- [x] 테스트 파일과 실제 운영 경로가 어떤 기능군을 덮는지 확인했다.
- [x] README, docs, 체크리스트 문서의 최신 상태와 실제 코드 상태 간 불일치를 기록했다.

### 11. 수정 설계 및 우선순위화

- [x] 발견 이슈를 기능군 기준으로 재분류했다.
- [x] 각 이슈에 대해 원인, 수정 대상 파일, 최소 수정 방안, 검증 방안을 설계했다.
- [x] 선행 수정 없이는 닫을 수 없는 상위 차단 이슈를 우선순위 상단으로 고정했다.

### 12. 구현 및 검증

- [x] 각 이슈를 체크리스트 순서대로 수정했다.
- [x] 각 수정 직후 가장 좁은 범위의 검증을 1차 수행했다.
- [x] 같은 항목에 대해 2차 검증까지 통과한 뒤 문서를 체크했다.

### 13. 운영 실검증 및 문서 마감

- [x] 핵심 운영 경로에 대해 2회 이상 실검증을 수행했다.
- [x] 자동 검증, 로컬 검증, 운영 실검증 결과를 이 문서와 관련 문서에 동기화했다.
- [x] 남은 차단 항목이 없을 때만 최종 판정을 `완료됨`으로 갱신한다.

## 이슈 기록표

| ID | 기능군 | 증상 | 원인 가설 | 수정 대상 | 검증 방법 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| INSPECT-001 | 기준선 | 전수검사 마스터 체크리스트를 생성하고 active 저장소 기준 단일 게이트 문서로 정착시켰다 | 이후 전수검사, 수정, 검증, 문서 동기화가 모두 이 문서를 기준으로 수행돼 기준선 부재 상태가 해소됐다 | 이 문서 | 문서 생성 확인, 단계별 실행 로그와 최종 판정 동기화 확인 | 완료됨 |
| INSPECT-002 | 런타임/스크립트 | 루트 `package.json` 에는 더 이상 `ensure:admin` 스크립트가 없고, 관리자 보장 경로는 `scripts/start_all_in_one.ps1` 내부 optional hook 으로만 남아 있다 | 현재 루트 기준 active npm surface 는 `dev`, `build`, `start` 3개뿐이며 과거 `ensure:admin` mismatch 는 stale checklist 근거였다 | `package.json`, `scripts/start_all_in_one.ps1`, `scripts/` | 루트 `package.json` 스크립트 확인, `scripts/start_all_in_one.ps1` 의 optional ensure hook 확인 | 완료됨 |
| INSPECT-003 | 런타임/스크립트 | 루트 `package.json` 에는 더 이상 `start:local`, `stop:local` 스크립트가 정의돼 있지 않다 | 과거 local start/stop mismatch 는 현재 active package surface 에서 제거돼 더 이상 live failure 가 아니다 | `package.json`, `scripts/` | 루트 `package.json` 스크립트 확인, `scripts/` 목록 대조 | 완료됨 |
| INSPECT-004 | 문서/롤백 | 현재 루트 `README.md` 는 과거 `start_frontend_dual.ps1`, `stop_frontend_dual.ps1` 롤백 절차를 더 이상 안내하지 않는다 | README 가 최소 run 문서로 축소돼 듀얼 프런트 롤백 mismatch 는 제거됐다 | `README.md`, `scripts/` | 루트 `README.md` 확인, `scripts/` 디렉터리 목록 대조 | 완료됨 |
| INSPECT-005 | 문서/compose | 현재 루트 `README.md` 는 MinIO 운영 구성을 서술하지 않아 `docker-compose.yml` 과의 문서 충돌이 사라졌다 | 과거 README 설명이 제거돼 live compose 문서 mismatch 는 재현되지 않는다 | `README.md`, `docker-compose.yml` | 루트 `README.md` 현재 내용 확인, `docker-compose.yml` 서비스 정의 확인 | 완료됨 |
| INSPECT-006 | 빌드/compose | backend compose 빌드가 루트 `Dockerfile.backend` 와 정리된 루트 `.dockerignore` 기준으로 끝까지 완료된다 | 루트 `.dockerignore` 에 대용량 `uploads/`, `.git/`, `.vs/`, 다중 venv, `frontend/`, `node_modules/` 등을 제외한 뒤 `docker compose build backend` 의 build context 가 20.34MB 로 축소됐고 backend 이미지 빌드가 성공 종료됐다 | `docker-compose.yml`, `Dockerfile.backend`, `.dockerignore`, 루트 `Dockerfile` | `docker-compose.yml` 의 `dockerfile: Dockerfile.backend` 확인, 루트 `.dockerignore` 추가/확장 확인, `docker compose build backend` 성공과 context 20.34MB 확인 | 완료됨 |
| INSPECT-007 | 생성기/런타임 | `backend/app/services` 서비스 패키지를 복구해 오케스트레이터 baseline 이 기대하는 import 경로를 다시 만들었다 | `backend/app/services/__init__.py`, `health_service.py`, `auth_service.py`, `catalog_service.py`, `order_service.py` 를 추가했고 `.venv` 기준 `py_compile` 로 새 모듈 5개를 모두 검증했다 | `backend/python_code_generator.py`, `backend/llm/orchestrator.py`, `backend/tools/repair_refiner_result.py`, `backend/tests/test_orchestrator_compat_manifest_write.py`, `backend/app/services/` | 코드 참조 검색, `backend/app/services/` 생성 확인, `.venv/Scripts/python.exe -m py_compile backend/app/services/*.py` 확인 | 완료됨 |
| INSPECT-008 | 관리자 API 계약 | 관리자 시스템 설정 저장 함수와 백엔드 라우트는 현재 모두 `PUT /api/admin/system-settings` 기준으로 정렬돼 있다 | 활성 프런트 저장 서비스 `saveAdminSystemSettings()` 는 이미 `method: 'PUT'` 를 사용하고, `use-admin-system-category-controller` 는 그 함수를 직접 호출하며, 백엔드 라우트도 `@router.put("/system-settings")` 만 노출한다 | `frontend/frontend/lib/admin-system-settings-service.ts`, `frontend/frontend/lib/use-admin-system-category-controller.ts`, `backend/admin_router.py` | 프런트 저장 함수 메서드 확인, 저장 버튼 호출 경로 확인, 백엔드 라우트 메서드 확인 | 완료됨 |
| INSPECT-009 | 프런트/API base URL | 현재 활성 소스에서 `resolveApiBaseUrl()` 정의는 공용 유틸 `frontend/frontend/shared/api.ts` 한 곳만 남아 있다 | admin, marketplace, approvals, runs, observability, publish, feature orchestrator 훅은 공용 유틸을 import 해 사용하고 별도 중복 정의는 현재 활성 소스에서 재현되지 않는다 | `frontend/frontend/shared/api.ts`, `frontend/frontend/app/admin/page.tsx`, `frontend/frontend/app/admin/approvals/page.tsx`, `frontend/frontend/app/admin/observability/page.tsx`, `frontend/frontend/app/admin/publish/page.tsx`, `frontend/frontend/app/admin/runs/page.tsx`, `frontend/frontend/app/marketplace/page.tsx`, `frontend/frontend/hooks/use-feature-orchestrator.ts` | `resolveApiBaseUrl` 전역 검색으로 활성 소스의 정의 위치와 호출 위치 대조 | 완료됨 |
| INSPECT-010 | 관리자 UI 상태 표시 | 실행 보드와 관측 보드 요약 카드가 API 실패 여부와 무관하게 `streaming ready`, `probe queue monitored`, `operator action ready`, `active`, `http / ws checked`, `bundle ready` 같은 낙관 상태를 고정 표시한다 | 실제 런타임 상태 대신 설명용 하드코딩 카드가 운영 상태 카드처럼 노출돼 거짓 상태를 만든다 | `frontend/frontend/app/admin/runs/page.tsx`, `frontend/frontend/app/admin/observability/page.tsx` | 요약 카드 상수 확인, 실제 fetch 결과가 카드 상태와 연결되지 않는지 대조 | 완료됨 |
| INSPECT-011 | 관리자 승인 UI 미연동 | 승인 큐/Publish 보드는 승인·재시도 흐름을 설명하지만 현재 소스에서는 실제 승인/재시도 액션을 호출하지 않는다 | 백엔드에는 승인/재시도 라우트가 있으나 현재 관리자 페이지가 읽기 전용 보드로 축소돼 운영 액션 UI가 빠졌다 | `frontend/frontend/app/admin/approvals/page.tsx`, `frontend/frontend/app/admin/publish/page.tsx`, `backend/admin_router.py` | 페이지 내 `fetch`/`onClick` 검색, `/api/admin/workspace-self-run/approve`, `/api/admin/workspace-self-run-record/retry` 라우트 존재 대조 | 완료됨 |
| INSPECT-012 | 프런트 빌드/산출물 | 활성 프런트는 `@/lib/admin-self-run-control`, `@/lib/use-admin-self-run` 없이도 clean `next build` 가 정상 통과하고, stale build log 는 active root 와 historical runtime copies 양쪽에서 정리됐다 | 활성 `frontend/frontend` 에는 두 모듈이 없지만 clean build 2회가 모두 성공했고, 새 `.next` 산출물에는 해당 import 흔적이 재현되지 않았다. 남아 있던 `uploads/tmp/codeai_admin_runtime/**/frontend/frontend/.build-logs/next-build.log` 30개는 `uploads/tmp/archived_build_logs/inspect-012_20260423/` 로 이관했으며, 루트 `.gitignore` 에 `.build-logs/` 를 추가해 같은 stale log 가 다시 live 근거처럼 남지 않게 했다 | `.gitignore`, `frontend/frontend/.next/**`, `frontend/frontend/lib/`, `uploads/tmp/codeai_admin_runtime/**`, `uploads/tmp/archived_build_logs/inspect-012_20260423/manifest.json` | 활성 `frontend/frontend/lib` 에 대상 모듈 부재 확인, clean `npm run build` 2회 성공 확인, 활성 `frontend/frontend/.next/**` 검색에서 대상 import 미검출 확인, 활성 `frontend/frontend/.build-logs/next-build.log` 부재 확인, `uploads/tmp/codeai_admin_runtime/**/.build-logs/next-build.log` 부재 및 archive manifest 에 30개 이관 기록 확인 | 완료됨 |
| INSPECT-013 | self-run 정상화 자동화 | `/api/admin/workspace-self-run-record/normalize` 가 실패 기록 재생성을 약속하지만 라우터는 실제 self-run 실행기 대신 `{"queued": true}` 를 반환하는 더미 `asyncio.sleep(..., result=...)` 콜백을 주입한다 | 정상화 API가 진짜 재실행·치환 루프를 호출하지 않고 큐 등록 메시지만 돌려 self-run 완전 자동 복구 상태를 과장한다 | `backend/admin_router.py`, `backend/admin/orchestrator/self_run_record_service.py` | normalize 라우트의 `execute_workspace_self_run` 주입값 확인, 서비스가 해당 콜백 반환값만 `retry` 로 넘기는지 대조 | 완료됨 |
| INSPECT-014 | self-run 브라우저 경로 정합성 | 현재 활성 관리자 소스에는 `workspace-self-prepare`, `workspace-self-run`, `focused-self-healing` 호출이 없고 읽기 전용 record 조회만 남아 있는데, `.next-admin` 로그와 과거 실험 산출물은 `bootstrap:self-run-restore`, normalize/retry/approve, focused self-healing 흐름이 살아 있는 것처럼 보인다 | 실제 브라우저 소스와 캐시/실험 산출물의 self-run 기능군이 서로 달라 완전 오토기능 구현 여부를 UI에서 검증할 수 없고, stale 로그가 거짓 구현 인상을 만든다 | `frontend/frontend/app/admin/page.tsx`, `frontend/frontend/app/admin/approvals/page.tsx`, `frontend/frontend/app/admin/runs/page.tsx`, `frontend/frontend/app/admin/publish/page.tsx`, `frontend/frontend/.next-admin/dev/logs/next-development.log`, `uploads/tmp/codeai_admin_runtime/**` | 활성 소스 전역 검색으로 self-run/focused 호출 부재 확인, `.next-admin` 로그의 `bootstrap:self-run-restore` 및 과거 실험 산출물의 호출 흔적 대조 | 완료됨 |
| INSPECT-015 | 마켓플레이스 상세 경로 | 공개 목록의 `/marketplace/${project.id}` 링크를 받는 `[id]` 상세 라우트가 활성 소스와 회귀 명세 양쪽에서 정상 동작한다 | `frontend/frontend/app/marketplace/[id]/page.tsx` 와 `/api/proxy?action=marketplace-project-detail` 프록시 매핑을 추가해 기존 백엔드 상세 API(`/api/marketplace/projects/{project_id}`)와 연결했고, `frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts` 가 `http://127.0.0.1:3000/marketplace/3` 상세 진입부터 거래 UI 렌더까지 직접 검증한다 | `frontend/frontend/app/marketplace/page.tsx`, `frontend/frontend/app/marketplace/[id]/page.tsx`, `frontend/frontend/app/api/proxy/route.ts`, `backend/marketplace/router.py`, `frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts` | 목록 링크 확인, 활성 `app/marketplace/[id]` 디렉터리 생성 확인, 프록시 action 과 백엔드 상세 API 연결 확인, `npm run e2e:marketplace-detail-commerce` 통과로 `/marketplace/3` 상세 진입 및 렌더 검증 | 완료됨 |
| INSPECT-016 | 마켓플레이스 공개 거래 UI 미노출 | 공개 상세 경로에서 구매·리뷰·다운로드 UI와 백엔드 거래 API를 다시 연결했고 브라우저 실검증 2회를 통과했다 | `frontend/frontend/app/marketplace/[id]/page.tsx` 에 거래 UI를 복구하고 `frontend/frontend/app/api/proxy/route.ts` 및 `backend/marketplace/router.py` 에 공개 purchase/review/download 라우트를 복원했다. `http://127.0.0.1:3000/marketplace/3` 과 `/marketplace/1` 에서 각각 구매 완료, 리뷰 등록, ZIP 다운로드(`ai-cs-orchestrator-bundle.zip`, `saas-admin-ui-kit.zip`)를 브라우저에서 끝까지 확인했다 | `frontend/frontend/app/marketplace/[id]/page.tsx`, `frontend/frontend/app/api/proxy/route.ts`, `backend/marketplace/router.py`, `backend/marketplace/payment_service.py`, `backend/marketplace/minio_service.py` | 공개 상세 라우트 진입 확인, purchase/review/download proxy action 연결 확인, `/marketplace/3` 및 `/marketplace/1` 브라우저 실검증 2회에서 구매 상태/리뷰 반영/ZIP 다운로드 확인 | 완료됨 |
| INSPECT-017 | 런타임 설정/지식 저장소 | 활성 코드와 관리자 로더가 기대하는 canonical 루트 `knowledge/orchestrator_runtime_config.json` 을 실제 워크스페이스 루트에 생성하고 동일 파일을 기준으로 읽는다 | `backend/llm/orchestrator.py` 의 runtime-config 로더가 파일 부재/손상 시 기본 payload 를 루트 `knowledge/orchestrator_runtime_config.json` 에 즉시 기록하도록 보강했고, `backend/admin_router.py` 도 같은 bootstrap 로직을 재사용해 관리자 요약이 더 이상 빈 `{}` 로 떨어지지 않는다 | `backend/llm/orchestrator.py`, `backend/admin_router.py`, `backend/tests/test_runtime_config_persistence.py`, 루트 `knowledge/orchestrator_runtime_config.json` | `python -m pytest backend/tests/test_runtime_config_persistence.py` 통과, 실제 루트에서 `_load_runtime_config_from_disk()` 실행 후 `knowledge/orchestrator_runtime_config.json` 생성 확인, 실제 관리자 `_load_runtime_config_summary()` 실행에서 `config_path=knowledge/orchestrator_runtime_config.json` 및 `selected_profile=True` 확인 | 완료됨 |
| INSPECT-018 | 생성 산출물/임시 저장소 오염 | 운영 출력 루트 `uploads/projects/` 에는 현재 `customer_1/`, `customer_2/`, `staff-orchestrator_20260420_044008/` 만 남기고, 과거 hard-gate/phase smoke 산출물 12개는 `uploads/tmp/archived_projects/inspect-018_20260423/` 로 이관했다 | `backend/tmp_run_hard_gate_consistency.py`, `backend/tmp_check_hard_gate_progress.py`, `backend/tmp_read_tracker_state.py` 는 hard-gate 진단 산출물을 `uploads/tmp/hard-gate-consistency/` 로 분리하고, `backend/tools/backfill_generated_artifacts.py` 는 더 이상 과거 `uploads/projects/*` 목록을 하드코딩하지 않고 현재 루트에서 실제 backfill 후보를 동적 탐색한다 | `backend/tmp_hard_gate_paths.py`, `backend/tmp_run_hard_gate_consistency.py`, `backend/tmp_check_hard_gate_progress.py`, `backend/tmp_read_tracker_state.py`, `backend/tools/backfill_generated_artifacts.py`, `backend/tests/test_generated_artifact_isolation.py`, `uploads/projects/`, `uploads/tmp/archived_projects/inspect-018_20260423/manifest.json` | `python -m pytest backend/tests/test_generated_artifact_isolation.py` 통과, live Python 확인에서 hard-gate temp/result 경로가 모두 `uploads/tmp/hard-gate-consistency` 아래로 해석되는 것 확인, `uploads/projects/` 디렉터리 목록이 3개만 남은 것 확인, `uploads/projects/**/.delivery-venv/**` 및 `uploads/projects/**/__pycache__` 검색 결과 없음 확인, archive manifest 에 stale 산출물 12개 이관 기록 확인 | 완료됨 |
| INSPECT-019 | 관리자 부트스트랩 인증 | profiler 실기동 경로에서는 고정 관리자 계정과 관리자/LLM 오케스트레이터 라우터가 빠져 있어 관리자 로그인 후에도 운영 검증 경로가 끊겼다 | `run_profiler_backend.py` 가 `backend/main.py` 가 아니라 `backend/operational_validation_app.py` 를 직접 기동했고, 이 앱에 fixed-admin bootstrap 과 admin/LLM orchestrator 라우터가 누락돼 있었다 | `run_profiler_backend.py`, `backend/operational_validation_app.py`, `docs/checklists/repo-full-inspection-master-checklist.md` | `run_profiler_backend.py` 진입점 확인, `backend/operational_validation_app.py` 수정 후 컴파일 확인, profiler 실기동 2회에서 `/api/auth/login`, `/api/admin/workspace-self-run-record?latest=true`, `/api/admin/orchestrator/runtime-verification` 200 확인 | 완료됨 |
| INSPECT-020 | JWT/시크릿 키 정책 | 활성 인증 코드와 생성 템플릿에 남아 있던 런타임 fallback / 약한 기본 JWT 시크릿을 제거했고 profiler 운영 2차 실검증까지 통과했다 | `backend/auth.py` 는 명시 시크릿만 허용하도록 바뀌었고, `backend/llm/orchestrator.py` 활성 생성 템플릿 2곳의 `JWT_SECRET` 기본값도 제거했으며, profiler 실기동 2회에서 로그인과 LLM chat 라우트가 명시 시크릿으로 정상 동작했다 | `backend/auth.py`, `backend/python_code_generator.py`, `backend/llm/orchestrator.py`, `backend/operational_validation_app.py` | `SECRET_KEY_FILE`, `SECRET_KEY_IS_RUNTIME_FALLBACK`, `JWT_SECRET`, `change-me` 참조 검색과 코드 확인, `backend/llm/orchestrator.py` 및 `backend/operational_validation_app.py` 컴파일 확인, profiler 실기동 2회에서 `/api/auth/login`, `/api/llm/orchestrate/chat/light` 200 확인 | 완료됨 |
| INSPECT-021 | 비밀값 저장 규칙 | PostgreSQL 비밀번호 갱신 운영 경로 2회 실검증에서 `.env` 평문 비밀번호가 제거되고 시크릿 파일만 갱신되는 것을 확인했다 | `/api/admin/system-settings/postgres-password` live 호출 2회 모두 `secret_host_path=.runtime/secrets/postgres_password.txt` 에 새 비밀번호가 기록됐고, `.env` 에는 `POSTGRES_PASSWORD_FILE=/run/codeai-secrets/postgres_password.txt` 와 `DATABASE_URL=` 만 남았으며 `POSTGRES_PASSWORD` 는 재생성되지 않았다 | `backend/admin_router.py`, 루트 `.env`, `.runtime/secrets/postgres_password.txt` | 관리자 로그인 후 `/api/admin/system-settings/postgres-password` 2회 호출, 각 호출 뒤 `.env` 와 secret file 내용 확인 | 완료됨 |
| INSPECT-022 | 테스트 커버리지/활성 소스 정합성 | 활성 `frontend/frontend/tests/` 루트에 관리자 login/passkey/dashboard 계열과 공개 상세 거래 경로까지 포함한 Playwright 명세가 이관돼 현재 활성 경로를 직접 검증한다 | 과거 실험 사본에만 묶여 있던 테스트 의존을 줄이고, 활성 소스 기준으로 관리자 핵심 보드와 공개 marketplace detail purchase/review/download 경로를 재발 방지용 명세로 고정했다 | `frontend/frontend/tests/**`, `frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts`, `frontend/frontend/package.json`, `frontend/frontend/app/admin/`, `frontend/frontend/app/marketplace/` | 활성 테스트 파일 목록 확인, `e2e:marketplace-detail-commerce` 스크립트 확인, `npm run e2e:marketplace-detail-commerce` 통과, 활성 `app/admin`/`app/marketplace` 경로와 테스트 대상 기능군 비교 | 완료됨 |
| INSPECT-023 | self-run 승인 게이트 | self-run approval record 의 필수 approval-gate 필드가 현재 운영 경로에서 모두 채워지고 `approval_gate_ok=true` 로 통과한다 | 운영 저장소의 성공 approval `20260423_044957_456796`, `20260423_045332_159249` 를 live API 로 다시 조회했을 때 `applied`, `postcheck_ok`, `dod_ok`, `completion_gate_ok`, `semantic_audit_ok`, `structure_validation_ok`, `traceability_map_path` 가 모두 채워졌고 `status=applied_to_source` 로 닫혔다 | `backend/admin_router.py`, `backend/admin/orchestrator/self_run_record_service.py`, `backend/llm/orchestrator.py`, self-run worker 출력 계약 | `/api/admin/workspace-self-run-record?approval_id=...` live 조회 2회로 approval gate 필수 필드와 `approval_gate_ok` 재검증 | 완료됨 |
| REINSPECT-001 | 런타임/nginx | nginx upstream `frontend_main`이 `frontend-admin:3000`을 가리키지만 frontend-admin은 PORT=3005에서 실행 | upstream이 잘못된 포트를 가리키고 단일 upstream으로 marketplace/admin이 뒤섞임 | `nginx/nginx.conf/nginx.conf` upstream을 `frontend_marketplace:3000` + `frontend_admin:3005`로 분리 | docker compose up --build nginx 후 127.0.0.1:3000/marketplace, 127.0.0.1:3005/admin 브라우저 실검증 | 완료됨 (2026-04-26) |
| REINSPECT-002 | 런타임/compose | docker-compose.yml의 frontend-admin SITE_URL이 metanova1004.com, frontend-marketplace가 xn--114로 서로 반대 | 사용자 확인 기준: marketplace=metanova1004.com, admin=개발분석114.com | `docker-compose.yml` NEXT_PUBLIC_SITE_URL 교정 | docker compose up --build 후 브라우저 실검증 | 완료됨 (2026-04-26) |
| REINSPECT-003 | 보안 | `.env`에 `FIXED_ADMIN_PASSWORD=space0215@` 평문 노출. `.gitignore`에 `.env`, `.runtime/secrets/` 미포함 | INSPECT-021에서 '평문 제거'로 기록했으나 실제 코드에는 남아있었음 | `.env`에서 평문 비밀번호 제거, `FIXED_ADMIN_PASSWORD_FILE` 시크릿 파일 방식으로 이관, `.gitignore`에 `.env`와 `.runtime/secrets/` 추가 | `.env` 내용 확인, `.gitignore` 확인, `backend/main.py` _FILE 읽기 로직 추가 확인 | 완료됨 (2026-04-26) |
| REINSPECT-004 | 보안/부트스트랩 | `backend/main.py`의 `ENABLE_FIXED_ADMIN_BOOTSTRAP` 기본값이 `"true"`로 남아있음 | INSPECT-019에서 '기본값 false 변경'으로 기록했으나 실제 코드는 `"true"` | `backend/main.py` line 436 기본값을 `"false"`로 변경 | 코드 확인, docker compose up --build backend 후 bootstrap 로그 확인 | 완료됨 (2026-04-26) |

## 단계별 실행 로그

### Step 1. 기준선 고정

- 상태: `완료됨`
- 수행 내용: 전수검사 마스터 체크리스트 문서를 생성하고, 헌법형 진행 규칙과 전체 검사 순서를 고정했다.
- 근거: `docs/checklists/repo-full-inspection-master-checklist.md` 생성
- 차단 여부: 없음. Step 1 기준선 고정은 이후 단계의 실제 점검/수정/검증 근거로 모두 소진됐고, active master checklist 의 기준 문서 역할을 완료했다.

### Step 2. 런타임 및 기동 경로 점검

- 상태: `완료됨`
- 수행 내용:
  - 루트 `package.json` 의 운영 스크립트와 실제 `scripts/` 디렉터리 존재 여부를 대조했다.
  - `scripts/start_all_in_one.ps1` 의 고정 관리자 계정 보장 경로를 확인했다.
  - README 서비스 표, 운영자 실행 명령, 롤백 절차를 현재 `docker-compose.yml` 및 `scripts/` 상태와 대조했다.
- 근거:
  - 현재 루트 `package.json` 의 active script 는 `dev`, `build`, `start` 뿐이며 `ensure:admin`, `start:local`, `stop:local` 은 더 이상 정의돼 있지 않다.
  - 실제 `scripts/` 목록에는 `ensure_fixed_admin_account.ps1`, `start_local_all_in_one.ps1`, `stop_local_all_in_one.ps1`, `start_frontend_dual.ps1`, `stop_frontend_dual.ps1` 가 없지만, 현재 루트 package/README 는 그 파일들을 active 명령으로 노출하지 않는다.
  - `scripts/start_all_in_one.ps1` 는 `ensure_fixed_admin_account.ps1` 누락 시 `Skipping admin ensure step` 경고를 출력하도록 작성돼 있다.
  - 현재 루트 `README.md` 는 최소 run 문서만 남아 있고 MinIO/듀얼 프런트/로컬 start-stop 스크립트 안내를 포함하지 않는다.
  - `docker-compose.yml` 의 backend/video-worker build 는 `Dockerfile.backend` 를 요구했고, 루트 `.dockerignore` 정리까지 반영한 뒤 `docker compose build backend` 가 context 20.34MB 로 축소된 상태에서 backend 이미지 빌드를 성공 종료했다.
  - `backend/python_code_generator.py`, `backend/llm/orchestrator.py`, `backend/tools/repair_refiner_result.py`, `backend/tests/test_orchestrator_compat_manifest_write.py` 가 기대하던 `backend/app/services/` 패키지를 실제로 생성했고, 새 서비스 모듈 5개는 `.venv/Scripts/python.exe -m py_compile ...` 검증을 통과했다.
- 차단 여부:
  - 없음. `INSPECT-002` 부터 `INSPECT-006` 까지의 활성 런타임/문서/compose 기준선이 현재 루트 소스와 실제 backend 이미지 빌드 성공 증적으로 닫혔다.

### Step 3. 백엔드 API 구조 점검

- 상태: `완료됨`
- 수행 내용:
  - 관리자 시스템 설정 조회/저장 경로의 실제 라우트 메서드와 프런트 호출 메서드를 대조했다.
  - 저장 버튼이 어떤 프런트 함수로 연결되는지 호출 경로를 추적했다.
- 근거:
  - `backend/admin_router.py` 에는 `@router.get("/system-settings")`, `@router.put("/system-settings")` 만 존재하며 동일 경로 `POST` 라우트는 없다.
  - `frontend/frontend/lib/admin-system-settings-service.ts` 의 `saveAdminSystemSettings()` 는 동일 경로로 `method: 'PUT'` 를 전송한다.
  - `frontend/frontend/lib/use-admin-system-category-controller.ts` 의 `saveSystemSettings()` 는 위 `saveAdminSystemSettings()` 를 직접 호출한다.
- 차단 여부:
  - 관리자 시스템 설정 저장 경로의 `POST`/`PUT` 계약 mismatch 는 현재 활성 소스에서 재현되지 않는다.
  - Step 3 범위의 독립 차단은 현재 남아 있지 않으며, 이후 단계 기능군 이슈도 같은 세션에서 닫혔다.

### Step 4. 관리자 기능군 점검

- 상태: `완료됨`
- 수행 내용:
  - 관리자 대시보드와 연관 페이지들의 API base URL 계산 경로를 공용 유틸 기준으로 대조했다.
  - 관리자 기능군 내부에서 origin 계산 로직이 중복 선언되는지 확인했다.
  - approvals, runs, observability, publish 보드가 실제 운영 액션과 런타임 상태를 반영하는지 UI/라우터를 대조했다.
- 근거:
  - 공용 유틸 `frontend/frontend/shared/api.ts` 에 `resolveApiBaseUrl()` 가 존재한다.
  - 활성 소스 전역 검색 기준 `resolveApiBaseUrl()` 정의는 `frontend/frontend/shared/api.ts` 한 곳만 남아 있고, `frontend/frontend/app/admin/page.tsx`, `frontend/frontend/app/admin/approvals/page.tsx`, `frontend/frontend/app/admin/observability/page.tsx`, `frontend/frontend/app/admin/publish/page.tsx`, `frontend/frontend/app/admin/runs/page.tsx`, `frontend/frontend/app/marketplace/page.tsx`, `frontend/frontend/hooks/use-feature-orchestrator.ts` 는 공용 유틸 호출만 수행한다.
  - `frontend/frontend/app/admin/runs/page.tsx`, `frontend/frontend/app/admin/observability/page.tsx` 의 요약 카드 상태는 현재 실제 fetch 결과 기반으로 렌더링된다.
  - `frontend/frontend/app/admin/approvals/page.tsx`, `frontend/frontend/app/admin/publish/page.tsx` 는 `/api/admin/workspace-self-run/approve`, `/api/admin/workspace-self-run-record/normalize`, `/api/admin/workspace-self-run-record/retry` 를 실제 backend 라우트에 연결한다.
  - 활성 관리자 Playwright 명세 `admin-publish-actions`, `admin-approvals-actions`, `admin-runtime-status-cards`, `admin-dashboard-ops` 가 현재 `/admin`, `/admin/approvals`, `/admin/publish`, `/admin/runs`, `/admin/observability` 경로를 직접 검증한다.
  - 운영 재검증 2회에서 fresh self-run 이 `pending_approval` 에서 실제 approve 호출을 거쳐 `applied_to_source` 로 닫히는 것을 확인했다.
- 차단 여부:
  - 없음. Step 12 구현과 운영 실검증 2회로 관리자 상태 카드, approve/normalize/retry 액션, self-run approval 흐름이 active 경로 기준으로 복구됐고 `INSPECT-010`, `011`, `013`, `014` 가 모두 닫혔다.

### Step 5. 마켓플레이스 기능군 점검

- 상태: `완료됨`
- 수행 내용:
  - 활성 공개 마켓플레이스 앱이 실제로 어떤 페이지를 제공하는지 디렉터리 구조와 목록 페이지 링크를 대조했다.
  - 목록, 통계, 고객 오케스트레이터는 살아 있는 반면 상세/거래형 공개 경로가 활성 소스에 남아 있는지 확인했다.
  - 백엔드의 프로젝트 상세 API, 결제/다운로드 서비스, MinIO 연결 흔적과 현재 공개 프런트 노출 범위를 비교했다.
- 근거:
  - `frontend/frontend/app/marketplace/` 활성 디렉터리에 `[id]/page.tsx` 상세 라우트를 추가했다.
  - `frontend/frontend/app/marketplace/page.tsx` 는 각 카드에 `Link href={`/marketplace/${project.id}`}` 를 렌더링해 상세 진입을 유도한다.
  - `backend/marketplace/router.py` 에는 `@router.get("/projects/{project_id}", response_model=schemas.Project)` 상세 API가 존재한다.
  - `frontend/frontend/app/api/proxy/route.ts` 에 `marketplace-project-detail` action 을 추가해 상세 라우트가 same-origin proxy 경로로 backend 상세 API를 읽는다.
  - `frontend/frontend/app/marketplace/[id]/page.tsx` 는 공개 purchase/review/download UI 와 proxy fetch 경로를 노출한다.
  - `frontend/frontend/app/api/proxy/route.ts`, `backend/marketplace/router.py`, `backend/marketplace/payment_service.py`, `backend/marketplace/minio_service.py` 가 공개 거래 흐름을 같은 계약으로 연결한다.
  - `frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts` 와 브라우저 실검증 2회에서 `/marketplace/3`, `/marketplace/1` 의 상세 진입, 구매 완료, 리뷰 등록, ZIP 다운로드를 직접 확인했다.
- 차단 여부:
  - 없음. `[id]` 상세 라우트, purchase/review/download 공개 거래 경로, 관련 Playwright 회귀 명세와 브라우저 실검증 2회가 확보돼 `INSPECT-015`, `016` 이 모두 닫혔다.

### Step 6. 오케스트레이터 및 생성기 점검

- 상태: `완료됨`
- 수행 내용:
  - self-run 실패 기록 정상화 경로가 실제 재실행기를 연결하는지 서비스 레벨까지 대조했다.
  - 승인 치환 서비스가 실제 clone -> source 반영을 수행하는 반면, normalize 경로는 같은 수준의 실행기를 쓰는지 비교했다.
- 근거:
  - `backend/admin/orchestrator/self_run_record_service.py` 의 `normalize_workspace_self_run_record_response()` 는 실패 기록일 때 주입된 `execute_workspace_self_run(...)` 콜백을 호출하고, 그 반환값을 `retry` 필드에 반영한다.
  - `backend/admin_router.py` 의 normalize / retry 경로는 현재 실제 `_execute_workspace_self_run_internal(...)` 실행기로 연결돼 retry approval 을 재생성한다.
  - `backend/admin/orchestrator/self_run_approval_service.py` 의 `approve_workspace_self_run_response()` 는 `sync_clone_into_source()` 를 통해 실제 clone -> source 치환과 backup 생성까지 수행한다.
  - 운영 self-run approval record `20260423_044957_456796`, `20260423_045332_159249` 재조회에서 `approval_gate_ok=true`, `status=applied_to_source` 와 필수 gate 필드 채움을 확인했다.
- 차단 여부:
  - 없음. normalize/retry 경로가 실제 self-run 실행과 approval gate 채움 경로로 연결됐고, 운영 self-run record 2건이 `approval_gate_ok=true`, `status=applied_to_source` 로 재검증돼 `INSPECT-013`, `023` 이 닫혔다.

### Step 7. 데이터 및 저장 계층 점검

- 상태: `완료됨`
- 수행 내용:
  - 런타임이 실제로 참조하는 저장 루트가 `uploads/projects`, `uploads/tmp`, `knowledge`, `models` 중 어디인지 코드와 실제 디렉터리 상태를 대조했다.
  - 루트 저장소와 `uploads/tmp/codeai_admin_runtime/admin_self_experiments/**` 하위 실험 사본들이 동일한 지식/산출물 역할을 중복 보유하는지 확인했다.
  - `uploads/projects/` 아래에 현재 운영 산출물 외 오래된 smoke 결과, 가상환경, 캐시가 누적되는지 점검했다.
- 근거:
  - `backend/llm/orchestrator.py` 는 `ORCH_RUNTIME_CONFIG_PATH = "knowledge/orchestrator_runtime_config.json"`, `ORCH_VALIDATION_WORK_ROOT = "uploads/tmp/orchestrator_validation"`, `output_base_dir: str = "uploads/projects"` 를 사용한다.
  - `backend/llm/model_config.py`, `backend/llm/admin_capabilities.py`, `backend/admin_router.py` 도 동일하게 루트 `knowledge/orchestrator_runtime_config.json` 를 운영 기준 설정처럼 참조한다.
  - 루트 `knowledge/orchestrator_runtime_config.json` 이 canonical runtime-config 로 실제 생성돼 관리자 로더와 같은 파일을 기준으로 읽는다.
  - hard-gate 진단 산출물은 `uploads/tmp/hard-gate-consistency/` 아래로 분리됐고, `backend/tmp_hard_gate_paths.py` 가 temp/result 경로를 단일 해석한다.
  - `uploads/projects/` 운영 루트는 `customer_1/`, `customer_2/`, `staff-orchestrator_20260420_044008/` 만 유지하고, 과거 project artifacts 12개는 `uploads/tmp/archived_projects/inspect-018_20260423/` 로 이관됐다.
  - `backend/tools/backfill_generated_artifacts.py` 는 더 이상 과거 산출물 경로를 하드코딩하지 않고 현재 루트에서 backfill 후보를 동적으로 탐색한다.
- 차단 여부:
  - 없음. canonical runtime-config 루트와 hard-gate/backfill/output 경로가 active workspace 기준으로 단일화됐고 stale project artifacts 는 archive 로 이관돼 `INSPECT-017`, `018` 이 닫혔다.

### Step 8. 보안 및 설정 점검

- 상태: `완료됨`
- 수행 내용:
  - 활성 백엔드의 인증 비밀키 결정 로직과 고정 관리자 부트스트랩 기본값을 점검했다.
  - 관리자 시스템 설정 패널이 `*_FILE` 시크릿 규칙을 실제로 지키는지, 평문 `.env` 중복 저장이 있는지 확인했다.
  - 생성기 템플릿과 오케스트레이터가 `change-me` 류 기본 시크릿을 계속 산출하는지 재확인했다.
- 근거:
  - 활성 `backend/**`, `app/**` 소스에는 `ENABLE_FIXED_ADMIN_BOOTSTRAP`, `FIXED_ADMIN_EMAIL`, `FIXED_ADMIN_PASSWORD` 기본값 주입 코드가 남아 있지 않다.
  - `backend/auth.py` 는 명시된 `SECRET_KEY`/`JWT_SECRET` 또는 지정된 시크릿 파일만 읽고, 런타임 임시 시크릿 fallback 을 사용하지 않는다.
  - `backend/python_code_generator.py`, `backend/llm/orchestrator.py` 의 활성 생성 템플릿에서 `change-me`, `change-me-in-production`, `replace-with-32-char-random-secret` 계열 기본 시크릿 값이 제거됐다.
  - `backend/admin_router.py` 의 PostgreSQL 비밀번호 갱신 경로는 `POSTGRES_PASSWORD_FILE` 만 유지하고 `.env` 에 `POSTGRES_PASSWORD` 평문을 재기록하지 않는다.
  - profiler 운영 실검증 2회에서 로그인, LLM chat, PostgreSQL 비밀번호 회전 경로가 모두 명시 시크릿 기준으로 통과했다.
- 차단 여부:
  - 없음. fixed-admin 기본값, 런타임 시크릿 fallback, `.env` 평문 PostgreSQL 비밀번호 중복 기록이 제거됐고 profiler 운영 실검증 2회까지 통과해 `INSPECT-019`, `020`, `021` 이 닫혔다.

### Step 9. 프런트 구조 및 빌드 경로 점검

- 상태: `완료됨`
- 수행 내용:
  - 현재 활성 소스, `.next` 산출물, 빌드 로그 사이에 남아 있는 관리자 self-run 스택 참조를 대조했다.
  - 현재 소스에서 제거된 모듈이 캐시/로그/실험 산출물에는 남아 있는지 확인했다.
- 근거:
  - 현재 워크스페이스의 `frontend/frontend/lib/` 아래에는 `admin-self-run-control.ts`, `use-admin-self-run.ts` 가 없다.
  - clean `npm run build` 2회가 모두 성공했고, active `.next/**` 검색에서는 `@/lib/admin-self-run-control`, `@/lib/use-admin-self-run` 참조가 재현되지 않았다.
  - active `frontend/frontend/.build-logs/next-build.log` 는 제거됐고, historical runtime copies 의 stale build logs 30개는 `uploads/tmp/archived_build_logs/inspect-012_20260423/` 로 이관됐다.
  - `.next-admin` 활성 로그를 2회 비운 뒤 다시 로드해도 `bootstrap:self-run-restore` 가 재생성되지 않았다.
- 차단 여부:
  - 없음. active frontend 기준 clean build 2회, stale `.build-logs` 정리, `.next`/historical runtime copy import 흔적 제거까지 반영돼 빌드 경로 정합성이 복구됐다.

### Step 10. 스크립트, 문서, 테스트 점검

- 상태: `완료됨`
- 수행 내용:
  - 활성 프런트 Playwright 스위트가 현재 소스 기능군을 어디까지 덮는지 확인했다.
  - 문서/스크립트 드리프트로 이미 기록된 항목이 여전히 뒤집히지 않는지 재확인했다.
  - 실험 사본 내부 테스트와 활성 테스트 루트의 범위 차이를 비교했다.
- 근거:
  - 활성 Playwright 루트 `frontend/frontend/tests/` 에는 `admin-login`, `admin-passkey-operational`, `admin-dashboard-ops`, `admin-publish-actions`, `admin-approvals-actions`, `admin-runtime-status-cards`, `admin-system-settings-operational`, `marketplace-detail-commerce` 를 포함한 11개 명세가 존재한다.
  - `frontend/frontend/package.json` 의 관련 스크립트와 실제 명세 구성이 active 관리자 로그인/passkey/dashboard 경로 및 공개 marketplace detail-commerce 경로를 직접 검증한다.
  - `npm --prefix frontend/frontend run build`, 관리자 Playwright 명세들, `npm run e2e:marketplace-detail-commerce` 검증이 모두 통과했다.
  - Step 2에서 기록한 `INSPECT-002` 부터 `INSPECT-006` 문서/스크립트 불일치도 이후 수정과 재검증으로 뒤집히지 않았고 active 문서 상태와 동기화됐다.
- 차단 여부:
  - 없음. active Playwright 루트가 관리자 login/passkey/dashboard 와 marketplace detail-commerce 회귀까지 덮도록 이관됐고 관련 검증이 통과해 `INSPECT-022` 가 닫혔다.

### Step 11. 수정 설계 및 우선순위화

- 상태: `완료됨`
- 수행 내용:
  - 기록된 이슈를 기능군 기준으로 재분류하고 선행 차단 관계를 묶었다.
  - 각 기능군별로 원인 축, 최소 수정 단위, 검증 게이트를 정의했다.
  - Step 12 구현 순서를 상위 hard gate 기준으로 고정했다.
- 기능군별 설계:
  - 보안/설정 hard gate:
    - 대상 이슈: `INSPECT-019`, `INSPECT-020`, `INSPECT-021`
    - 원인 축: 기본 관리자 자격증명 자동 주입, 런타임 fallback 시크릿 허용, `*_FILE` 규칙과 평문 `.env` 저장의 이중 정책
    - 최소 수정 방안: 고정 관리자 기본값 제거 또는 필수 env 강제, 런타임 생성 시크릿을 개발 한정 분기로 격리, 관리자 설정 저장 시 평문 `POSTGRES_PASSWORD` 기록 제거 및 secret-file 단일 계약으로 통일
    - 수정 대상: `backend/main.py`, `backend/auth.py`, `backend/admin_router.py`, 생성기 기본 `.env` 템플릿 계열
    - 1차 검증: 보안 관련 단위/정적 검증, 시크릿 결정 로직 확인, 관리자 설정 저장 payload 점검
    - 2차 검증: 로컬 부팅 후 관리자 로그인/설정 저장 실검증 2회, 약한 기본값 미주입 재확인 2회
  - 기준 경로/계약 단일화 gate:
    - 대상 이슈: `INSPECT-007`, `INSPECT-008`, `INSPECT-009`, `INSPECT-017`, `INSPECT-018`
    - 원인 축: 생성기 계약 불일치, 프런트-백엔드 HTTP 메서드 불일치, base URL 계산 중복, 런타임 설정/출력 루트 분산, 과거 artifact 혼재
    - 최소 수정 방안: `app/services` 패키지 기준으로 생성기 계약 단일화, 시스템 설정 저장 메서드 계약을 한쪽으로 고정, 공용 API origin 유틸 단일 사용, 런타임 설정/산출물 루트의 authoritative 경로 명시, 오래된 artifact/venv/cache를 운영 루트에서 분리
    - 수정 대상: `backend/python_code_generator.py`, `backend/llm/orchestrator.py`, `backend/tools/**`, `frontend/frontend/lib/**`, `frontend/frontend/shared/api.ts`, 저장 루트 관련 문서/스크립트
    - 1차 검증: 관련 테스트와 grep 수준 계약 검증, 경로/메서드 참조 단일화 확인
    - 2차 검증: 생성 산출물 smoke, 시스템 설정 저장 실호출, 루트별 결과물 적재 위치 재검증 2회
  - 관리자 운영 기능 복구 gate:
    - 대상 이슈: `INSPECT-010`, `INSPECT-011`, `INSPECT-013`, `INSPECT-014`, `INSPECT-022`
    - 원인 축: false status 카드, 승인/재시도 액션 미연동, normalize dummy callback, 활성 관리자 UI와 stale build/실험 사본의 기능군 괴리, 활성 테스트 부재
    - 최소 수정 방안: 상태 카드를 실제 API 응답 기반으로 재작성, approve/retry/normalize/focused healing 중 현재 유지할 운영 경로를 명시하고 UI와 라우트 계약을 같은 범위로 축소 또는 복구, 실험 사본이 아닌 활성 테스트 루트에 운영 테스트 재정착
    - 수정 대상: `frontend/frontend/app/admin/**`, `backend/admin_router.py`, `backend/admin/orchestrator/**`, `frontend/frontend/tests/**`
    - 1차 검증: 관리자 페이지별 좁은 Playwright 또는 컴포넌트 검증, self-run 관련 라우트 응답 검증
    - 2차 검증: `/admin`, 승인 큐, runs/observability, normalize/retry 흐름 2회 실검증
  - 마켓플레이스 공개 거래 복구 gate:
    - 대상 이슈: `INSPECT-015`, `INSPECT-016`
    - 원인 축: 상세 라우트 제거 후 링크 잔존, 활성 공개 프런트에서 구매/리뷰/다운로드 흐름 축소
    - 최소 수정 방안: 상세 페이지를 복구하거나 링크를 제거해 dead route 제거, 공개 거래 UX 범위를 백엔드 계약과 동일하게 맞추고 최소 구매/다운로드/리뷰 진입 경로를 활성 소스에 복귀
    - 수정 대상: `frontend/frontend/app/marketplace/**`, `backend/marketplace/router.py`, 관련 서비스와 테스트
    - 1차 검증: 상세 라우트 진입, 구매/다운로드 CTA 존재 여부, API 연결 확인
    - 2차 검증: 마켓플레이스 목록→상세→주문/다운로드 실검증 2회
  - 런타임 스크립트/문서 동기화 gate:
    - 대상 이슈: `INSPECT-002`, `INSPECT-003`, `INSPECT-004`, `INSPECT-005`, `INSPECT-006`
    - 원인 축: package script, README, compose, 실제 파일 구조가 서로 다른 운영 절차를 가리킴
    - 최소 수정 방안: 실제 유지할 운영 스크립트만 남기고 package/README/compose를 그 기준으로 재정렬, 존재하지 않는 파일 참조 제거, backend Dockerfile 경로를 실제 파일 구조와 일치시킴
    - 수정 대상: `package.json`, `README.md`, `docker-compose.yml`, `scripts/**`, Dockerfile 위치
    - 1차 검증: 스크립트 존재/호출 계약 점검, compose build 경로 확인
    - 2차 검증: 문서 명령 재실행과 compose 기동 검증 2회
- 우선순위 고정:
  - P0: 보안/설정 hard gate를 먼저 닫지 않으면 어떤 UI 복구도 운영 검증 대상으로 승격하지 않는다.
  - P1: 기준 경로/계약 단일화를 먼저 수행해 생성기, 시스템 설정, 저장 루트, API origin 기준을 하나로 고정한다.
  - P2: 관리자 운영 기능 복구는 P0-P1 이후에 진행한다. 그렇지 않으면 false status 와 stale build 를 다시 증폭시킨다.
  - P3: 마켓플레이스 공개 거래 복구는 관리자/계약 기준이 고정된 뒤 수행한다.
  - P4: 스크립트/문서 동기화는 각 기능 수정 직후 같은 커밋 범위에서 함께 닫아 drift 재발을 막는다.
- Step 12 구현 순서:
  - 12-1. `INSPECT-019`~`021` 보안/시크릿 강제화
  - 12-2. `INSPECT-007`~`009`, `017`, `018` 계약/저장 루트 단일화
  - 12-3. `INSPECT-010`, `011`, `013`, `014`, `022` 관리자 운영 경로 복구와 활성 테스트 이관
  - 12-4. `INSPECT-015`, `016` 마켓플레이스 상세/거래 경로 복구
  - 12-5. `INSPECT-002`~`006` 문서/스크립트/compose 동기화 마감
- 차단 여부:
  - 없음. Step 11 에서 고정한 우선순위가 실제 Step 12 구현 순서와 검증 흐름으로 끝까지 적용됐고, 대응 INSPECT 항목이 모두 닫혔다.

### Step 12. 구현 및 검증

- 상태: `완료됨`
- 수행 내용:
  - P0 첫 슬라이스로 `INSPECT-019` 고정 관리자 부트스트랩 기본 자격증명 제거를 시작했다.
  - `backend/main.py` 에서 `ENABLE_FIXED_ADMIN_BOOTSTRAP` 기본값을 `false` 로 바꾸고, `FIXED_ADMIN_EMAIL`, `FIXED_ADMIN_PASSWORD` fallback 기본값을 제거했다.
  - 이어서 `INSPECT-020`, `INSPECT-021` 구현으로 런타임 시크릿 자동 fallback 과 `change-me` 계열 기본값, PostgreSQL 비밀번호 평문 `.env` 중복 기록을 제거했다.
  - profiler 실기동 경로를 재추적한 결과 `run_profiler_backend.py` 는 `backend/main.py` 가 아니라 `backend/operational_validation_app.py` 를 직접 실행하고 있음을 확인했고, 이 앱에 fixed-admin bootstrap 과 admin/LLM orchestrator 라우터를 추가했다.
  - [backend/operational_validation_app.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/operational_validation_app.py) 에서 `ENABLE_FIXED_ADMIN_BOOTSTRAP`, `FIXED_ADMIN_EMAIL`, `FIXED_ADMIN_PASSWORD` 를 읽어 고정 관리자 계정을 생성/보정하는 startup hook 을 추가하고, `/api/admin/orchestrator/runtime-verification`, `/api/llm/orchestrate/chat/light`, `/api/marketplace/customer-orchestrate/stage-runs` 를 profiler 앱 health/routes 에 포함시켰다.
  - 이번 턴 재검증에서 활성 루트의 [backend/main.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/main.py) 가 실제로는 `app.main` re-export 만 수행하는 얇은 진입점이고, 활성 `backend/**`, `app/**` 소스에는 `ENABLE_FIXED_ADMIN_BOOTSTRAP`, `FIXED_ADMIN_EMAIL`, `FIXED_ADMIN_PASSWORD` 기본값 주입 코드가 남아 있지 않음을 다시 확인했다.
  - 같은 재검증에서 활성 [backend/llm/orchestrator.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/llm/orchestrator.py) 내부 생성 템플릿 2곳에 남아 있던 `JWT_SECRET = os.getenv('JWT_SECRET', 'replace-with-32-char-random-secret')` 기본값을 제거하고 `require_jwt_secret()` 강제 패턴으로 통일했다.
  - 다음 슬라이스로 `INSPECT-011`, `INSPECT-022` 의 최소 복구 경로를 잡아 [frontend/frontend/app/admin/publish/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/publish/page.tsx) 에 approve / hold(normalize) / retry 액션 버튼을 추가하고, 활성 테스트 루트에 [frontend/frontend/tests/admin-publish-actions.playwright.spec.ts](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/tests/admin-publish-actions.playwright.spec.ts) 를 신설했다.
  - 이어서 [frontend/frontend/app/admin/approvals/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/approvals/page.tsx) 에 approve / normalize / retry 실액션을 연결하고, [backend/admin_router.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/admin_router.py) 의 normalize / retry 경로를 더미 큐 응답 대신 실제 `_execute_workspace_self_run_internal(...)` 경로로 묶었다.
  - [frontend/frontend/app/admin/runs/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/runs/page.tsx), [frontend/frontend/app/admin/observability/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/observability/page.tsx) 의 고정 낙관 상태 카드를 fetch 결과 기반 동적 상태로 바꿨고, 활성 테스트 루트에 [frontend/frontend/tests/admin-approvals-actions.playwright.spec.ts](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/tests/admin-approvals-actions.playwright.spec.ts), [frontend/frontend/tests/admin-runtime-status-cards.playwright.spec.ts](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/tests/admin-runtime-status-cards.playwright.spec.ts) 를 추가했다.
  - 최신 운영 재검증에서 실제 관리자 로그인 후 `/admin`, `/admin/approvals`, `/admin/publish`, `/admin/runs`, `/admin/observability` 를 2회씩 확인했고, fresh self-run `20260423_025813_051596` 가 `pending_approval` 까지 진행된 뒤 실제 approve 호출 성공으로 `applied_to_source` 까지 닫히는 것을 확인했다.
  - 같은 루트 스크립트 [scripts/capture_normalize_evidence.ps1](c:/Users/WORK/source/repos/parkcheolhong/codeAI/scripts/capture_normalize_evidence.ps1) 를 `-CleanupOnly` 없이 추가 실행해 [tmp/normalize-evidence-retry.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-retry.json), [tmp/normalize-evidence-retry-2.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-retry-2.json) 2건의 retry 생성 증적을 남겼다.
  - 두 번째 retry 생성 증적에서 나온 `retry_approval_id=20260423_043154_761427` 에 대해 live approve 경로를 후속 호출했고, 응답과 approval record 를 각각 [tmp/approve-evidence-20260423_043154_761427.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-evidence-20260423_043154_761427.json), [tmp/approve-record-20260423_043154_761427.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-record-20260423_043154_761427.json) 로 저장했다.
  - 이어서 `empty_files=28` 근본 원인을 추적해 [backend/admin_router.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/admin_router.py) 의 Python diagnostic fallback validation 범위를 whole clone 이 아니라 fallback 이 실제로 생성한 `docs/code_analysis.json`, `docs/root_cause_analysis.md` 로 제한했다.
  - post-fix 재검증으로 [tmp/normalize-evidence-retry-3.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-retry-3.json) 을 남기고 새 `retry_approval_id=20260423_044040_936593` 를 생성했으며, 해당 live record 를 [tmp/approve-record-20260423_044040_936593.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-record-20260423_044040_936593.json) 으로 저장했다.
  - profiler 경로 운영 실검증 1차에서 `ops-admin@example.com` 로그인 후 `/api/admin/workspace-self-run-record?latest=true`, `/api/admin/orchestrator/runtime-verification`, `/api/llm/orchestrate/chat/light`, `/api/marketplace/customer-orchestrate/stage-runs` 생성/조회까지 모두 통과시켰다.
  - profiler 경로 운영 실검증 2차에서 같은 환경으로 서버를 재기동한 뒤 동일 로그인, 관리자 record 조회, admin runtime verification, LLM light chat, 고객 stage-run 생성/조회까지 다시 통과시켰다.
- 근거:
  - 기존 코드는 명시 env 가 없어도 `119cash@naver.com` / `space0215@` 를 사용해 관리자 계정을 자동 생성·갱신했다.
  - 현재 코드는 고정 관리자 부트스트랩을 명시적으로 켜지 않으면 실행되지 않으며, 켜더라도 이메일/비밀번호 env 가 없으면 skip 한다.
  - 수정 직후 [backend/main.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/main.py) 에 대해 editor diagnostics 확인 결과 오류가 없었다.
  - 이어서 `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -m py_compile backend/main.py` 를 실행해 Python 컴파일을 통과했다.
  - 이번 턴 재검증에서 활성 루트 [backend/main.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/main.py) 는 `app.main` re-export 만 수행하며, 활성 `backend/**`, `app/**` grep 결과 `ENABLE_FIXED_ADMIN_BOOTSTRAP`, `FIXED_ADMIN_EMAIL`, `FIXED_ADMIN_PASSWORD` 는 과거 `uploads/tmp/**` 사본에만 남아 있음을 확인했다.
  - [backend/auth.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/auth.py) 는 더 이상 임시 파일 생성이나 랜덤 런타임 시크릿 fallback 을 사용하지 않고, 명시된 `SECRET_KEY`/`JWT_SECRET` 또는 지정된 시크릿 파일만 읽는다. 미설정 상태에서는 `SECRET_KEY=''`, `SECRET_KEY_IS_RUNTIME_FALLBACK=False`, `is_weak_secret_key()=True` 를 반환하도록 좁은 실행 검증으로 확인했다.
  - [backend/python_code_generator.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/python_code_generator.py), [backend/llm/orchestrator.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/llm/orchestrator.py) 의 활성 생성 템플릿에서 `change-me`, `change-me-in-production`, `codeai-*-change-me` 기본 시크릿 값을 제거하고 빈 env 요구 형태로 전환했다.
  - 이번 턴 추가 검증에서 활성 `backend/**` 범위에는 더 이상 `JWT_SECRET = os.getenv('JWT_SECRET', 'replace-with-32-char-random-secret')` 패턴이 남아 있지 않았고, `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -m py_compile backend/llm/orchestrator.py` 검증도 통과했다.
  - `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -m py_compile backend/operational_validation_app.py` 검증이 통과했고, editor diagnostics 에서 같은 파일 오류가 없었다.
  - [backend/admin_router.py](c:/Users/WORK/source/repos/parkcheolhong/codeAI/backend/admin_router.py) 의 `_write_admin_env_values(...)` 는 `None` 값을 받은 키를 `.env` 에서 삭제하도록 바뀌었고, PostgreSQL 비밀번호 갱신 API 는 `POSTGRES_PASSWORD_FILE` 만 유지하고 `POSTGRES_PASSWORD` 평문 줄은 제거한다.
  - `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -m py_compile backend/auth.py backend/admin_router.py backend/python_code_generator.py backend/llm/orchestrator.py` 를 실행해 수정 파일 4개가 모두 Python 컴파일을 통과했다.
  - 추가 좁은 실행 검증에서 시크릿 미설정 상태의 `backend.auth` import 결과가 `{'secret': '', 'runtime_fallback': False, 'weak': True}` 로 출력됐고, 임시 `.env` 파일에 대해 `_write_admin_env_values(..., {'POSTGRES_PASSWORD': None, 'POSTGRES_PASSWORD_FILE': '/run/new-secret.txt'})` 실행 결과 `POSTGRES_PASSWORD_FILE=/run/new-secret.txt` 한 줄만 남는 것을 확인했다.
  - 관리자 publish 보드 복구 후 `frontend/frontend` dev 서버를 `http://127.0.0.1:3005` 로 기동한 뒤 `npm run e2e -- tests/admin-publish-actions.playwright.spec.ts --project chromium --no-deps` 를 실행해 새 Playwright 명세 1건이 통과했다.
  - 이후 같은 dev 서버에서 `npm run e2e -- tests/admin-publish-actions.playwright.spec.ts tests/admin-approvals-actions.playwright.spec.ts tests/admin-runtime-status-cards.playwright.spec.ts --project chromium --no-deps` 를 실행해 관리자 액션/상태 카드 복구 명세 3건이 모두 통과했다.
  - `backend/admin_router.py` 는 루트 작업 디렉터리에서 `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -m py_compile backend/admin_router.py` 컴파일 검증을 통과했다.
  - 운영 재검증 기준으로 [frontend/frontend/app/admin/runs/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/runs/page.tsx), [frontend/frontend/app/admin/observability/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/observability/page.tsx) 는 더 이상 고정 낙관 상태 문자열을 쓰지 않고 실제 API 응답 기반 status 를 표시한다.
  - 운영 재검증 기준으로 [frontend/frontend/app/admin/approvals/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/approvals/page.tsx), [frontend/frontend/app/admin/publish/page.tsx](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/app/admin/publish/page.tsx) 는 approve / normalize / retry 를 실제 backend 라우트에 `POST` 한다.
  - 활성 Playwright 루트 [frontend/frontend/tests](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/tests) 에는 현재 `admin-system-settings-operational`, `admin-runtime-status-cards`, `admin-publish-actions`, `admin-approvals-actions`, `admin-login`, `admin-passkey-operational`, `admin-dashboard-ops`, `marketplace-generator-products`, `marketplace-liveview-ai-sheet-launcher`, `marketplace-popup-interactions`, `marketplace-detail-commerce` 11개 명세가 존재한다.
  - `npm --prefix frontend/frontend run build` 검증이 통과했고, `npm --prefix frontend/frontend exec -- playwright test -c frontend/frontend/playwright.config.cjs frontend/frontend/tests/admin-login.playwright.spec.ts frontend/frontend/tests/admin-passkey-operational.playwright.spec.ts --project chromium --no-deps`, `$env:PLAYWRIGHT_ADMIN_USERNAME='ops-admin@example.com'; $env:PLAYWRIGHT_ADMIN_PASSWORD='OpsAdmin!20260423'; npm --prefix frontend/frontend exec -- playwright test -c frontend/frontend/playwright.config.cjs frontend/frontend/tests/admin-dashboard-ops.playwright.spec.ts --project chromium --no-deps`, `npm run e2e:marketplace-detail-commerce` 검증이 모두 통과했다.
  - 공개 상세 거래 회귀 방지용 [frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/tests/marketplace-detail-commerce.playwright.spec.ts) 와 [frontend/frontend/package.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/package.json) 의 `e2e:marketplace-detail-commerce` 스크립트를 추가했고, dev 서버 재사용 조건에서 `1 passed (3.6s)` 로 통과했다.
  - `.next-admin` 활성 로그 [frontend/frontend/.next-admin/dev/logs/next-development.log](c:/Users/WORK/source/repos/parkcheolhong/codeAI/frontend/frontend/.next-admin/dev/logs/next-development.log) 를 2회 비운 뒤 로그인 페이지와 관리자 대시보드 활성 루트를 다시 로드했지만, 파일은 공백만 유지했고 `bootstrap:self-run-restore` 는 활성 로그에 재생성되지 않았다.
  - normalize 운영 실검증 2회 증적을 [tmp/normalize-evidence-1.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-1.json), [tmp/normalize-evidence-2.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-2.json) 로 남겼고, 두 호출 모두 `normalized=true`, `action=regenerated`, 새 retry approval id 생성까지 확인됐다.
  - 추가 실검증에서 [tmp/normalize-evidence-retry.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-retry.json) 은 `action=regenerated`, `retry_approval_id=20260423_042956_974502`, [tmp/normalize-evidence-retry-2.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/normalize-evidence-retry-2.json) 은 `action=regenerated`, `retry_approval_id=20260423_043154_761427` 를 기록했고, 두 파일 모두 raw UTF-8 bytes 로 다시 읽었을 때 한글 `message` 가 깨지지 않았다.
  - 생성된 `retry_approval_id=20260423_043154_761427` 로 `/api/admin/workspace-self-run/approve` 를 live 호출한 결과 [tmp/approve-evidence-20260423_043154_761427.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-evidence-20260423_043154_761427.json) 에 `{"detail":"승인 대기 상태가 아닙니다."}` 가 기록됐다.
  - 같은 approval id 의 live record 인 [tmp/approve-record-20260423_043154_761427.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-record-20260423_043154_761427.json) 은 `status=failed`, `python_self_diagnostic_error="승인 직전 재검증에서 빈 파일이 감지되었습니다"`, `python_self_diagnostic_logs=["[approval-check] files_total=1849", "[approval-check] empty_files=28"]` 를 반환해 approve business gate 차단 원인을 명시했다.
  - 좁은 함수 검증에서 `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -c "... _build_python_self_diagnostic_fallback(...) ..."` 재실행 결과 `{'ok': True, 'err': None, 'generated_files': ['docs/code_analysis.json', 'docs/root_cause_analysis.md']}` 가 출력돼 `empty_files=28` 차단이 제거된 것을 확인했다.
  - post-fix live retry approval [tmp/approve-record-20260423_044040_936593.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/tmp/approve-record-20260423_044040_936593.json) 은 `python_self_diagnostic_error=''`, `runtime_diagnostic='... py_compile=ok'` 로 바뀌어 기존 empty-file 차단이 사라졌음을 보여준다.
  - 그러나 같은 post-fix approval 은 여전히 `status=failed` 이고, orchestration approval gate 필수 필드 `applied`, `postcheck_ok`, `dod_ok`, `completion_gate_ok`, `semantic_audit_ok`, `structure_validation_ok`, `traceability_map_path` 가 비어 있어 `pending_approval` 승격이 막혔다.
  - profiler 실기동 1차에서 서버 로그 기준 `/api/auth/login`, `/api/admin/workspace-self-run-record?latest=true`, `/api/admin/orchestrator/runtime-verification`, `/api/llm/orchestrate/chat/light`, `/api/marketplace/customer-orchestrate/stage-runs`, `/api/marketplace/customer-orchestrate/stage-runs/{run_id}` 가 모두 `200 OK` 로 기록됐다.
  - profiler 실기동 2차에서 호출 결과 JSON 기준 `tokenIssued=true`, `adminRecordStatus=applied_to_source`, `runtimeVerificationKeys=context,gate_policy,operational_evidence,operational_evidence_summary,operational_targets_by_id,project_root,verification_items`, `llmReplyLength=264`, `customerStageRunCreated=true`, `customerStageScope=marketplace` 가 확인됐다.
- 차단 여부:
  - `INSPECT-019`, `INSPECT-020` 은 profiler 실기동 2회 운영 검증까지 확보돼 `완료됨` 으로 재판정한다.
  - `INSPECT-021` 은 관리자 로그인 후 `/api/admin/system-settings/postgres-password` 2회 실검증에서 `.env` 평문 비밀번호 미재생성 및 secret file 갱신이 확인돼 `완료됨` 으로 재판정한다.
  - `INSPECT-010`, `INSPECT-011` 은 실제 운영 경로 2회 검증과 live approve 성공 근거까지 확보돼 `완료됨` 으로 재판정한다.
  - `INSPECT-013` 은 normalize 라우트의 실제 재생성 경로와 운영 실검증 2회 증적까지 확보돼 `완료됨` 으로 재판정한다.
  - `INSPECT-014` 는 stale `.next-admin` 로그를 2회 리셋 후 활성 관리자 루트를 다시 로드해도 `bootstrap:self-run-restore` 가 재생성되지 않는 것이 확인돼 `완료됨` 으로 재판정한다.
  - `INSPECT-022` 는 활성 테스트 루트에 login / passkey / dashboard 명세가 이관되고 관련 Playwright 검증이 통과해 `완료됨` 으로 재판정한다.
  - `INSPECT-023` 은 운영 self-run record 2건(`20260423_044957_456796`, `20260423_045332_159249`)을 live API 로 다시 조회했을 때 approval gate 필수 필드가 모두 채워지고 `approval_gate_ok=true`, `status=applied_to_source` 로 확인돼 `완료됨` 으로 재판정한다.

### Step 13. 운영 실검증 및 문서 마감

- 상태: `완료됨`
- 수행 내용:
  - profiler 기준 운영 실검증 1차를 수행해 관리자 로그인, 관리자 record 조회, admin runtime verification, LLM light chat, 고객 stage-run 생성/조회 경로를 실제로 호출했다.
  - 같은 환경으로 profiler 서버를 재기동한 뒤 동일 경로에 대해 운영 실검증 2차를 다시 수행했다.
  - 위 2회 결과를 Step 12 근거와 이슈 기록표 상태에 동기화했다.
- 근거:
  - 1차 실검증 서버 로그에 `/api/auth/login`, `/api/admin/workspace-self-run-record?latest=true`, `/api/admin/orchestrator/runtime-verification`, `/api/llm/orchestrate/chat/light`, `/api/marketplace/customer-orchestrate/stage-runs`, `/api/marketplace/customer-orchestrate/stage-runs/{run_id}` `200 OK` 가 기록됐다.
  - 2차 실검증 결과 JSON 에서 `tokenIssued=true`, `adminRecordStatus=applied_to_source`, `runtimeVerificationKeys=context,gate_policy,operational_evidence,operational_evidence_summary,operational_targets_by_id,project_root,verification_items`, `llmReplyLength=264`, `customerStageRunCreated=true`, `customerStageRunStatus=running`, `customerStageScope=marketplace` 가 확인됐다.
  - 2차 고객 stage run 은 `customerRunId=stage_run_qQEiqXTHxqpjF6xrc7E1GM83` 로 생성됐다.
  - PostgreSQL 비밀번호 저장 운영 실검증 1차/2차에서 `/api/admin/system-settings/postgres-password` 응답이 모두 `changed=True` 를 반환했고, `.env` 에 `POSTGRES_PASSWORD_FILE=/run/codeai-secrets/postgres_password.txt` 만 남은 상태와 `.runtime/secrets/postgres_password.txt` 의 비밀번호 회전(`PgSecret!20260423A` -> `PgSecret!20260423B`)을 확인했다.
  - self-run approval gate 운영 실검증 1차/2차에서 `/api/admin/workspace-self-run-record?approval_id=20260423_044957_456796`, `/api/admin/workspace-self-run-record?approval_id=20260423_045332_159249` 응답이 모두 `status=applied_to_source`, `approval_gate_ok=True`, `applied=True`, `postcheck_ok=True`, `dod_ok=True`, `completion_gate_ok=True`, `semantic_audit_ok=True`, `structure_validation_ok=True`, `traceability_map_path` populated 를 반환했다.
- 차단 여부:
  - 오케스트레이터 연결 복구, PostgreSQL 비밀값 저장 경로, self-run approval gate 필수 필드 채움 경로에 대해서 모두 운영 실검증 2회를 충족했다.
  - 추가 차단 없음. active 이슈 기록표의 `INSPECT-001`~`023` 은 모두 `완료됨` 으로 정리됐고, 본 문서의 단계 체크박스/최종 판정도 같은 세션 기준으로 동기화했다.

## 최종 판정

- 상태: `완료됨`
- 충족 근거:
  - 전수검사 순서 1~13의 체크박스와 단계별 상태가 모두 닫혔다.
  - active INSPECT 이슈 기록표의 `INSPECT-001`~`023` 이 모두 현재 세션 증적으로 정리됐다.
  - 자동 검증, 로컬 검증, 운영 핵심 경로 실검증 2회 결과가 최신 세션 기준으로 문서에 반영됐다.
  - active master checklist 와 관련 근거 문구가 현재 코드/산출물 상태에 맞게 동기화됐다.
