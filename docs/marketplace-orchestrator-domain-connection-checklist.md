# Marketplace Orchestrator / Domain Connection 체크리스트

## 검증 기준

- 실제 활성 경로에서 확인된 항목만 `[x]` 처리
- `/admin/llm` 에서 넘긴 handoff 가 `/marketplace/orchestrator` 실제 route 로 도달해야 통과 처리
- 운영/도메인 연결은 링크 선언이 아니라 실제 route 존재와 브라우저 진입으로 확인해야 통과 처리

## 1. 라우트 복구

- [x] 활성 `frontend/frontend/app/marketplace/orchestrator/page.tsx` 가 존재하고 Next app route 로 등록된다.
- [x] `/marketplace/orchestrator` 진입이 `[id]` 상세 페이지로 잘못 해석되지 않는다.

## 2. 오케스트레이터 연결

- [x] `/admin/llm` 의 full-page handoff 가 실제 orchestrator 화면으로 이동한다.
- [x] marketplace 메인/상세의 `오케스트레이터` 링크가 실제 주문 허브 화면을 연다.

## 3. 도메인/운영 경로

- [x] `docker-compose.yml` 의 `nginx` publish 포트 기본값이 인바운드 HTTP/HTTPS 80/443 과 일치한다.
- [x] `nginx/nginx.conf/nginx.conf` 의 `/marketplace/` 분기와 활성 프런트 route 가 서로 같은 경로 계약을 사용한다.
- [x] 브라우저에서 `/marketplace/orchestrator` 실진입 결과가 route mismatch 없이 렌더링된다.

## 4. 인증/마켓 데이터 복구

- [x] marketplace 고객 인증 계약이 활성 런타임에서 `POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me` 로 복구된다.
- [x] 활성 FastAPI 앱이 `/api/marketplace/*` router 를 실제 등록하고 도메인 ingress 에서 200 응답한다.
- [x] marketplace 메인 화면이 `/api/proxy?action=marketplace-*` 경로로 실제 데이터 응답을 다시 받는다.

## 5. UTF-8 인코딩 복구

- [x] 활성 backend 와 frontend proxy 가 JSON 응답에 `charset=utf-8` 을 명시한다.
- [x] 한글 payload 가 운영 도메인 응답에서 UTF-8 기준으로 그대로 읽힌다.

## 6. 보조 패널 API 정합성

- [x] `GET /api/marketplace/customer-orchestrate/logs/my` 가 활성 ORM/DB 스키마와 같은 필드 계약으로 200 응답한다.
- [x] `GET /api/marketplace/customer-orchestrate/retry-queue/my` 가 활성 ORM/DB 스키마와 같은 필드 계약으로 200 응답한다.
- [x] `GET /api/marketplace/customer-orchestrate/generated-programs/latest` 가 최근 생성 결과가 없는 경우에도 오케스트레이터 패널을 깨뜨리지 않는 응답 계약으로 정렬된다.
- [x] 고객 로그인 세션에서 실제 주문 실행 후 완료/로그/재시도/생성 결과 패널이 실데이터로 채워진다.

## 근거

- [x] `docker compose config`
 Result: `nginx` 서비스의 publish 포트가 `80->80`, `443->443` 로 해석됨.
- [x] `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
 Result: `devanalysis114-nginx` 가 `0.0.0.0:80->80`, `0.0.0.0:443->443` 로 실제 실행 중이며 `devanalysis114-backend` 도 함께 기동됨.
- [x] `curl.exe -I http://127.0.0.1/`
 Result: `HTTP/1.1 301 Moved Permanently`, `Location: https://127.0.0.1/` 로 80 포트 인입과 HTTPS 강제 전환 확인.
- [x] `curl.exe -k -I https://127.0.0.1/marketplace/orchestrator?product=code-generator-deployment-kit`
 Result: `HTTP/1.1 307 Temporary Redirect`, `location: /staff/login` 으로 `/marketplace/orchestrator` 가 더 이상 marketplace detail `[id]` 경로가 아니라 실제 orchestrator route 로 해석됨.
- [x] 브라우저 실검증 `https://127.0.0.1/marketplace/orchestrator?product=code-generator-deployment-kit`
 Result: TLS 경고 우회 후 `https://127.0.0.1/staff/login` 의 `직원 오케스트레이터 로그인` 화면까지 도달함. route mismatch 없이 인증 보호 경로로 연결됨.
- [x] `http://127.0.0.1:8000/api/auth/signup -> /api/auth/login -> /api/auth/me`
 Result: `marketplace.compat.20260423141555@example.com` 계정으로 회원가입/로그인/내정보 조회가 모두 성공했고 `tokenType=bearer`, `memberType=individual` 가 확인됨.
- [x] `docker compose up -d --build backend`
 Result: 활성 `app/main.py` 에 `backend.marketplace.router`, `backend.marketplace.stats_router` 등록을 반영한 뒤 backend 컨테이너를 재생성함.
- [x] `http://127.0.0.1:8000/api/marketplace/projects`
 Result: `200 OK`, `total=6` 으로 seed 프로젝트 목록이 직접 조회됨.
- [x] `http://127.0.0.1:8000/api/marketplace/stats/overview`
 Result: `200 OK`, `projects=6`, `users=6` 으로 marketplace 통계가 직접 조회됨.
- [x] `https://metanova1004.com/api/marketplace/projects`
 Result: `200 OK`, 운영 도메인 ingress 를 통해 동일한 marketplace 목록이 직접 조회됨.
- [x] `https://metanova1004.com/api/proxy?action=marketplace-projects`
 Result: `200 OK`, frontend proxy 경유 목록 응답이 복구됨.
- [x] `https://metanova1004.com/api/proxy?action=marketplace-stats-overview`
 Result: `200 OK`, frontend proxy 경유 통계 응답이 복구됨.
- [x] 브라우저 네트워크 실검증 `https://metanova1004.com/marketplace`
 Result: `/api/proxy?action=marketplace-categories`, `/api/proxy?action=marketplace-projects`, `/api/proxy?action=marketplace-stats-overview`, `/api/proxy?action=marketplace-stats-revenue`, `/api/proxy?action=marketplace-stats-top-projects&limit=6` 가 모두 `200 OK` 로 재호출됨.
- [x] 브라우저 콘솔 실검증 `https://metanova1004.com/marketplace`
 Result: marketplace 재호출 이후 error level 콘솔 메시지가 남지 않음.
- [x] 브라우저 실검증 `https://metanova1004.com/marketplace -> 주문`
 Result: `https://metanova1004.com/marketplace/orchestrator` 로 실제 이동했고 `상품 주문 오케스트레이터` 화면이 렌더링되며 더 이상 `map is not a function` 크래시가 발생하지 않음. 완료/로그/재시도 패널은 빈 상태로 정상 노출됨.
- [x] 브라우저 실검증 `https://metanova1004.com/marketplace/1 -> 주문`
 Result: 상세 페이지 상단 `주문` 링크가 `https://metanova1004.com/marketplace/orchestrator` 로 실제 이동했고 `상품 주문 오케스트레이터` 주문 허브가 렌더링됨.
- [x] 브라우저 실검증 `https://metanova1004.com/admin/llm -> Full Page 오케스트레이터 열기`
 Result: `https://metanova1004.com/marketplace/orchestrator?product=code-generator-deployment-kit` 로 이동했고 `코드 생성기 배포 키트`, `운영형 생성기 실행`, `[관리자 수동 오케스트레이터 실행] ...` handoff payload 가 화면에 그대로 반영됨.
- [x] `http://127.0.0.1:8000/api/marketplace/projects`
 Result: `200 OK`, `Content-Type: application/json; charset=utf-8` 확인.
- [x] `https://metanova1004.com/api/marketplace/projects`
 Result: `200 OK`, `Content-Type: application/json; charset=utf-8` 확인.
- [x] `https://metanova1004.com/api/proxy?action=marketplace-projects`
 Result: `200 OK`, `Content-Type: application/json; charset=utf-8` 확인.
- [x] `http://127.0.0.1:8000/api/marketplace/customer-orchestrate/completions/my`, `logs/my`, `retry-queue/my`, `generated-programs/latest`
 Result: 인증된 고객 세션에서 `completions -> 200`, `logs -> 200`, `retry-queue -> 200`, `generated-programs/latest -> 200` 이 모두 확인됐고 `generated-programs/latest` 는 빈 결과에서도 summary object 형태를 유지했다.
- [x] 브라우저 실검증 `https://metanova1004.com/marketplace/orchestrator`
 Result: 로그인 세션 복원 후 `실프로그램 출고 요약`, `내 완료 이력`, `실행 로그` 패널이 빈 상태가 아니라 실제 값으로 렌더링됐다. 화면에는 `출력 경로`, `출고 ZIP`, `validation profile: python_fastapi`, `publish readiness: ready`, `shipping zip reproduction: pass`, 완료 이력 `project-scanner-starter / full · 시도 1`, 실행 로그 `고객 오케스트레이터 completion 자동 저장 / FLOW-001 / FLOW-001-4 / SAVE_COMPLETION / saved` 가 표시됐다.
- [x] 브라우저 재주문 실검증 `https://metanova1004.com/marketplace/orchestrator -> 주문하기`
 Result: `POST /api/marketplace/customer-orchestrate/stage-runs -> 200`, `POST /api/marketplace/customer-orchestrate/accepted -> 202`, `GET /api/marketplace/customer-orchestrate/progress/{run_id} -> 200`, `GET /api/marketplace/customer-orchestrate/stage-runs/{run_id} -> 200` 순서로 실제 호출됐고 더 이상 `404/500` 이 발생하지 않았다. 브라우저 콘솔 error level 메시지도 남지 않았으며 stage card 는 `1단계 · 구조 설계`, `active stage = running` 으로 전환됐다.
- [x] 재주문 완료 근거 재확인 `http://127.0.0.1:8000/api/marketplace/customer-orchestrate/completions/my`, `logs/my`, `generated-programs/latest` + 브라우저 패널
 Result: 최신 재주문 산출물이 `output_dir=/app/uploads/projects/customer_7/runs/project-scanner-starter_20260423_064349_743820`, `shipment.zip`, `validation profile: python_fastapi`, `publish readiness: ready`, `shipping zip reproduction: pass` 로 갱신됐고 API 기준 `completionCount=2`, `logCount=2`, `approval_history_count=2` 가 확인됐다. 같은 시점에 브라우저 패널도 완료 이력 2건, 실행 로그 2건, 최신 출고 요약을 실제 값으로 렌더링했다.

## 7. 현재 세션 재검증 (마켓플레이스 CORB/CSP 전용)

- [x] 브라우저 콘솔 실검증 1차 (Playwright Chromium, headless)
 Result: `reports/browser-console-marketplace-corb-csp-pass1.json` 기준 `matchedCount=0`.
 스캔 URL: `https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace/orchestrator`, `https://xn--114-2p7l635dz3bh5j.com/marketplace`, `https://xn--114-2p7l635dz3bh5j.com/marketplace/orchestrator`
- [x] 브라우저 콘솔 실검증 2차 (동일 시나리오 재검증)
 Result: `reports/browser-console-marketplace-corb-csp-pass2.json` 기준 `matchedCount=0`.
 스캔 URL: 1차와 동일.

## 8. 현재 세션 미수행 항목

- [ ] 섹션 1~6 전체를 같은 시점/같은 조건으로 재실행해 체크 상태를 다시 확정

## 9. 추가 실검증 (운영 도메인, 현재 턴)

- [x] 운영 도메인 marketplace 페이지가 참조하는 `/_next/static/chunks/*.js` 응답이 실제 JavaScript MIME 으로 반환된다.
 Result: `https://metanova1004.com/marketplace` HTML 에서 추출한 chunk 10건 모두 `200 application/javascript; charset=UTF-8` 확인.
- [x] 브라우저 콘솔에서 CSP/eval/chunk 관련 에러 키워드 재검증
 Result: Playwright headless 재검증(`https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace/orchestrator`) 결과 `matchedCount=0`.
- [x] 운영 응답 헤더에 강제 CSP 헤더가 삽입되지 않았는지 확인
 Result: `https://metanova1004.com/marketplace` 응답 헤더 `Content-Security-Policy=<none>`.

## 10. 관리자 대시보드 보고 이슈 대응 (CORS + CSP/eval, 현재 턴)

- [x] `xn--` 호스트의 `/marketplace` 경로가 cross-origin 302 리다이렉트 없이 same-origin 200 으로 정규화됐다.
 Result: `nginx/nginx.conf/nginx.conf` 에서 `server_name localhost xn--114-2p7l635dz3bh5j.com` 블록의 `location = /marketplace`, `location ^~ /marketplace/`를 `return 302` 에서 `proxy_pass http://frontend_marketplace`로 변경 후 `nginx -t`, `nginx -s reload` 성공.
- [x] 헤더/리다이렉트 실검증 1차
 Result: `https://xn--114-2p7l635dz3bh5j.com/marketplace`, `https://xn--114-2p7l635dz3bh5j.com/marketplace?_rsc=17qrm`, `https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace?_rsc=17qrm` 모두 `HTTP/1.1 200 OK`, `Location=<none>`.
- [x] 헤더/리다이렉트 실검증 2차 (동일 시나리오 재검증)
 Result: 1차와 동일하게 4개 URL 모두 `HTTP/1.1 200 OK`, `Location=<none>`.
- [x] `/marketplace/orchestrator?_rsc=17qrm` 헤더/리다이렉트 실검증 1차
 Result: `https://xn--114-2p7l635dz3bh5j.com/marketplace/orchestrator?_rsc=17qrm`, `https://metanova1004.com/marketplace/orchestrator?_rsc=17qrm` 모두 `HTTP/1.1 200 OK`, `Location=<none>`.
- [x] `/marketplace/orchestrator?_rsc=17qrm` 헤더/리다이렉트 실검증 2차 (동일 시나리오 재검증)
 Result: 1차와 동일하게 2개 URL 모두 `HTTP/1.1 200 OK`, `Location=<none>`.
- [x] 브라우저 콘솔 실검증 1차 (admin+marketplace 포함)
 Result: Playwright headless(`https://xn--114-2p7l635dz3bh5j.com/admin`, `https://xn--114-2p7l635dz3bh5j.com/marketplace`, `https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace/orchestrator`)에서 CSP/eval/CORS 패턴 `matchedCount=0`.
- [x] 브라우저 콘솔 실검증 2차 (동일 시나리오 재검증)
 Result: CSP/eval/CORS 전용 필터 기준 `matchedCount=0`.
 Note: 중간 1회 실행에서 `GET .../marketplace/video?_rsc=... :: net::ERR_ABORTED` 1건이 있었으나 CSP/CORS 패턴이 아닌 이동 중 중단 요청으로 분류했고, 동일 시나리오를 CSP/CORS 전용 필터로 재실행해 `0건` 재확인.
- [x] CSP/eval 미해결 경고 재진단 (현재 턴)
 Result: 운영 URL(`https://xn--114-2p7l635dz3bh5j.com/admin`, `https://xn--114-2p7l635dz3bh5j.com/marketplace`, `https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace/orchestrator`) 응답 헤더에서 `Content-Security-Policy`, `Content-Security-Policy-Report-Only` 모두 미주입 확인. Playwright 진단(`reports/console_dump_tmp.js`)에서도 `securitypolicyviolation` 이벤트/콘솔의 CSP-eval 관련 매치가 `matchedCount=0`으로 재현되지 않음.
- [x] Stylesheet URL 실검증 (현재 턴)
 Result: 페이지가 참조한 `/_next/static/chunks/0~zt4ftbzdr7j.css` 를 양 도메인(`xn--114-2p7l635dz3bh5j.com`, `metanova1004.com`)에서 직접 조회한 결과 모두 `HTTP/1.1 200 OK`, `Content-Type: text/css; charset=UTF-8`, `Cache-Control: public, max-age=31536000, immutable` 확인.
- [x] 브라우저 레벨 재진단 (admin + marketplace, 현재 턴)
 Result: Playwright headless에서 admin/marketplace/orchestrator를 순회한 결과 CSS 요청 `0~zt4ftbzdr7j.css` 는 모두 `status=200`, `text/css` 로 수신됨. `CSP/unsafe-eval/script-src` 및 `securitypolicyviolation` 매치는 `0건`. 실패 요청은 라우트 전환 중 발생한 `_rsc` fetch `net::ERR_ABORTED` 3건만 관측됨.
- [x] 시크릿(확장 비활성) 기준 자동 재검증 2회 (현재 턴)
 Result: Playwright에서 `--incognito`, `--disable-extensions` 인자로 clean context를 강제한 2회 실행 결과, `https://xn--114-2p7l635dz3bh5j.com/admin`, `https://xn--114-2p7l635dz3bh5j.com/marketplace`, `https://metanova1004.com/marketplace`, `https://metanova1004.com/marketplace/orchestrator` 순회 시 `0~zt4ftbzdr7j.css` 는 라운드별 전부 `200 text/css` 수신. `securitypolicyviolation`/`CSP eval` 매치 `0건`. 실패는 페이지 전환 과정의 `_rsc` fetch `ERR_ABORTED`만 관측.

## 11. Chrome Issues 패널 잔존 이슈 최소 재현/정리 절차

- [x] 최소 절차 문서화 (현재 턴)
 Result: 아래 6단계로 잔존 이슈를 정리하고 동일 증상을 재확인한다.

 1) Chrome에서 대상 도메인 탭을 모두 닫고 새 시크릿 창을 연다.
 2) 확장 영향을 제거하기 위해 `chrome://extensions`에서 "Allow in Incognito"가 켜진 확장이 있으면 임시 해제한다.
 3) DevTools를 열고 `Network` 탭에서 `Disable cache`를 켠 뒤 새로고침한다.
 4) 같은 DevTools 세션에서 `Issues` 패널 우상단 `Clear issues`를 수행한 뒤 대상 URL 4개(admin/marketplace/orchestrator)를 순서대로 재접속한다.
 5) `Network`에서 `0~zt4ftbzdr7j.css` 요청의 `Status=200`, `Content-Type=text/css`를 확인하고, `Console`에서 `CSP`, `unsafe-eval`, `script-src` 키워드 에러 유무를 확인한다.
 6) 남는 항목이 있으면 항목 상세의 `Source`(extension id, document URL, blocked URI)를 기록해 서버 이슈/브라우저 로컬 이슈를 분리 판정한다.

## 현재 판정

- 상태: **구현됨**
- 이유: 이번 세션에서 실제로 다시 검증한 범위는 섹션 7(CORB/CSP 전용 2회)이며, 해당 범위는 두 번 모두 `matchedCount=0` 으로 확인됐다. 다만 섹션 1~6 전체를 같은 시점에 재검증하지 않았으므로 전체 항목을 다시 `완료됨` 으로 닫지는 않았다.
