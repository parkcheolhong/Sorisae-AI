# Platform Start/Stop/Health Recovery Checklist

## Scope
- 대상:
  - `package.json`
  - `docker-compose.yml`
  - `scripts/start_backend_stack.ps1`
  - `scripts/stop_backend_stack.ps1`
  - `scripts/start_all_in_one.ps1`
  - `scripts/stop_all_in_one.ps1`
  - `scripts/ops_health_check.ps1`
  - `nginx/nginx.conf/nginx.conf`

## Checklist
- [x] 현재 루트의 platform start/stop/health 스크립트 누락 상태를 확인한다.
- [x] 현재 `docker-compose.yml` 실구성과 README 설명 불일치를 확인한다.
- [x] UI 미기동 원인이 nginx SSL 인증서 누락임을 재현한다.
- [x] 로컬 인증서 누락 원인을 확인하고 복구 전략을 고정한다.
- [x] `start_all_in_one.ps1`를 현재 compose 실구성 기준으로 복구한다.
- [x] `stop_all_in_one.ps1`를 현재 compose 실구성 기준으로 복구한다.
- [x] `ops_health_check.ps1`를 현재 compose 실구성 기준으로 복구한다.
- [x] 전체 시작(`npm run start:platform`)을 2회 검증해 통과한다.
- [x] 헬스체크(`npm run health:platform`)를 2회 검증해 통과한다.
- [x] 전체 중지(`npm run stop:platform`)을 2회 검증해 통과한다.
- [x] 브라우저 UI 진입 URL을 실사용 로컬 게이트웨이(`http://127.0.0.1:8080`) 기준으로 2회 검증해 통과한다.

## Verification Log
- 확인 1: `npm run start:platform` 실행 시 `scripts/start_all_in_one.ps1` 파일이 루트에 없어 즉시 실패함.
- 확인 2: 루트 `scripts`에는 `start_backend_stack.ps1`, `stop_backend_stack.ps1`만 있고 `start_all_in_one.ps1`, `stop_all_in_one.ps1`, `ops_health_check.ps1`, `ensure_fixed_admin_account.ps1`는 없음.
- 확인 3: 현재 `docker-compose.yml` 서비스는 `postgres`, `redis`, `qdrant`, `minio`, `backend`, `video-worker`, `frontend-admin`, `nginx`이며 README의 `frontend-marketplace` 설명과 불일치함.
- 확인 4: `backend`는 `0.0.0.0:8000:8000`으로 노출되고 실제 `http://127.0.0.1:8000/health` 응답이 확인됨.
- 확인 5: `frontend-admin` 컨테이너는 실행 중이나 `nginx`는 `/etc/nginx/local-certs/fullchain.pem`, `/etc/nginx/local-certs/privkey.pem` 누락으로 시작 실패함.
- 확인 6: `nginx/nginx.conf/nginx.conf`는 `ssl_certificate /etc/nginx/local-certs/fullchain.pem;`, `ssl_certificate_key /etc/nginx/local-certs/privkey.pem;`를 강제함.
- 확인 7: 호스트에서 `openssl.exe`는 현재 사용 불가(`OPENSSL_MISSING`) 상태임.
- 확인 8: `certbot/logs/letsencrypt.log`에는 `Successfully received certificate.` 기록이 남아 있어 인증서 발급 자체는 성공했으며, 누락 원인은 루트 작업본 `certbot/local-certs`에 산출물이 반영되지 않은 상태로 확인됨.
- 확인 9: 과거 산출물(`uploads/tmp/codeai_admin_runtime/admin_self_experiments/codeAI_20260419_175028/certbot/local-certs`)의 `fullchain.pem`, `privkey.pem`를 루트 `certbot/local-certs`로 복원한 뒤 `docker compose up -d nginx` 재실행과 `http://127.0.0.1:8080/health` 기준 `HTTP 200` 응답을 확인함.
- 확인 10: 현재 compose 실구성 기준으로 `scripts/start_all_in_one.ps1`, `scripts/stop_all_in_one.ps1`, `scripts/ops_health_check.ps1`를 새로 복구했고, 인증서 복원 우선 + self-signed fallback 전략과 compose 실서비스 선택 기동/중지 로직을 반영함.
- 확인 11: 과거 산출물(`uploads/tmp/codeai_admin_runtime/admin_self_experiments/codeAI_20260419_175028/backend`) 기준으로 현재 루트 backend에서 빠진 Python 파일을 패키지 단위로 복원해 `video-worker` import tree를 닫았고, `docker compose rm -f -s video-worker` 후 clean recreate 기준 `video-worker`가 `Up` 상태로 회복됨.
- 확인 12: `npm run start:platform`를 2회 실행해 backend/nginx readiness와 UI 자동 오픈 경로까지 통과함. 이후 브라우저 자동 오픈 기본 경로는 인증서/외부 도메인 오탐을 피하기 위해 `http://127.0.0.1:8080/marketplace`, `http://127.0.0.1:8080/admin`으로 고정함.
- 확인 13: `npm run health:platform`를 2회 실행해 `postgres`, `redis`, `qdrant`, `minio`, `backend`, `video-worker`, `frontend-admin`, `nginx` 전부 `Passed`, backend `/health`·`/docs`·`/openapi.json`, nginx `http/https /health`, UI 검증은 `http://127.0.0.1:8080` 실사용 게이트웨이 기준으로 정리함.
- 확인 14: `npm run stop:platform`를 2회 실행해 `frontend-admin`, `nginx`, `video-worker`, `backend`, `postgres`, `redis`, `qdrant`, `minio` 중지 흐름이 모두 정상 종료됨.

## Notes
- 체크는 실제 수정 및 재검증 근거가 확인된 뒤에만 반영한다.
- 인증서 복구 전략은 1) 기존 산출물/기존 certbot 인증서 복원 우선, 2) 복원 불가 시 self-signed 재생성 fallback 순서로 고정한다.
- 로컬 체감 진입 URL은 인증서 CN/외부 DNS 오탐을 피하기 위해 `http://127.0.0.1:8080/marketplace`, `http://127.0.0.1:8080/admin`을 우선 사용한다.
- README, package.json, compose, start/stop/health 스크립트는 동일한 현재 실구성 기준으로 맞춰야 한다.
