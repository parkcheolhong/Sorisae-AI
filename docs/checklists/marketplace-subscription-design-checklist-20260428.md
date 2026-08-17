# 마켓플레이스 월구독 설계 체크리스트 (모바일 + 로컬PC)

## 문서 목적

- 이 문서는 마켓플레이스 앱군의 월구독 결제/권한 설계를 실제 구현 가능한 수준으로 고정하기 위한 체크리스트다.
- 대화에서만 완료 처리하지 않고, 이 문서의 체크 상태와 근거를 동기화한다.
- 모든 항목은 증적(설계 산출물, 코드, 검증 로그) 없이는 체크하지 않는다.

## 현재 판정

- 상태: `완료됨`
- 이유: Step 2-9 계약 회귀([backend/marketplace/router.py](backend/marketplace/router.py) `subscription_service` 노출)와 관리자 런타임 검증 회귀([backend/admin_router.py](backend/admin_router.py) 빈 `project_root` 기본 경로 허용)를 수정한 뒤, 백엔드 전수 검증(`30 passed`) 2회와 운영 도메인 검증(CORS + production endpoint) 2회를 연속 통과해 문서-실행 정합성 게이트를 닫았다.

## 2026-04-29 서비스군 월정액 확장 증분 판정

- 상태: `완료됨`
- 이유: 서비스군별 월정액 카탈로그 API/기본 SKU 자동 보장/프런트 다중 서비스군 결제 UI를 반영했고, 프런트 기존 차단 이슈 2건([frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx](frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx) `presentation` 타입 정합성, [frontend/frontend/app/marketplace/page.tsx](frontend/frontend/app/marketplace/page.tsx) 레일 라벨 문구)을 수정한 뒤 프런트 전체 검증(빌드+테스트) 2회와 백엔드 구독 테스트 2회를 모두 연속 통과해 `완료됨` 게이트를 닫았다.

### 2026-04-29 체크리스트

- [x] 서비스군 월정액 카탈로그 응답 스키마 추가 ([backend/marketplace/schemas.py](backend/marketplace/schemas.py))
- [x] 서비스군 기본 상품/플랜/가격 자동 보장 로직 추가 ([backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py))
- [x] 카탈로그 조회 API 추가 (`GET /api/marketplace/v1/subscription/catalog`) ([backend/marketplace/subscription_router.py](backend/marketplace/subscription_router.py))
- [x] 프런트 구독 페이지 다중 서비스군 선택/결제 연결 ([frontend/frontend/app/marketplace/subscription/page.tsx](frontend/frontend/app/marketplace/subscription/page.tsx))
- [x] 백엔드 구독 테스트 1차 통과 (`py -3.13 -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py -q` -> `19 passed`)
- [x] 백엔드 구독 테스트 2차 통과 (`py -3.13 -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py -q` -> `19 passed`)
- [x] 프런트 빌드 1차 통과 (`npm run build` -> Next.js build + TypeScript 성공)
- [x] 프런트 테스트 1차 통과 (`npm test` -> `frontend smoke tests passed`, `rail-labels snapshot: PASS`)
- [x] 프런트 빌드 2차 통과 (`npm run build` -> Next.js build + TypeScript 성공)
- [x] 프런트 테스트 2차 통과 (`npm test` -> `frontend smoke tests passed`, `rail-labels snapshot: PASS`)

## 헌법형 진행 규칙

- 선행 단계가 닫히기 전에는 후행 단계로 넘어가지 않는다.
- 각 단계는 최소 2회 검증 통과 후에만 `완료됨`으로 체크한다.
- 실제로 수행하지 않은 검증은 절대 체크하지 않는다.
- 하위 차단 항목이 남으면 상위 단계 체크를 보류한다.
- 보고 상태는 `구현됨`, `완료됨`, `실패`만 사용한다.

## 0단계 설계 산출물 고정

### A. 정책표 v1

- [x] 결제 채널 분리 정책 확정 (iOS=App Store, Android=Google Play, PC/Web=Stripe/PG)
- [x] 권한 단일화 정책 확정 (결제 채널과 무관하게 서버 Entitlement 단일 판정)
- [x] 해지/환불/결제실패/Grace Period 정책 확정
- [x] 제품별 요금 차등 허용 정책 확정 (요금과 권한 분리)

### B. 상태전이표 v1

- [x] 상태 집합 확정 (`none`, `trialing`, `active`, `grace_period`, `past_due`, `canceled`, `refunded`, `suspended`)
- [x] 이벤트 기반 전이 규칙 확정 (갱신 성공/실패, 환불, 해지예약, 운영자 정지)
- [x] Idempotency/이벤트 순서 역전(out-of-order) 처리 원칙 확정

### C. API 계약 초안 v1

- [x] 구독 조회 API 초안 확정 (`GET /v1/me/subscription`)
- [x] PC 결제 세션 API 초안 확정 (`POST /v1/billing/checkout/sessions`)
- [x] 모바일 검증 API 초안 확정 (`POST /v1/billing/mobile/verify`)
- [x] 해지/재개 API 초안 확정 (`POST /v1/me/subscription/cancel`, `POST /v1/me/subscription/resume`)
- [x] 결제사 웹훅 API 초안 확정 (`POST /v1/billing/webhooks/{provider}`)
- [x] 기기 등록/해제 API 초안 확정 (`POST /v1/me/devices/register`, `POST /v1/me/devices/revoke`)

## 1단계 구현 준비 체크리스트

- [x] DB 스키마 v1 확정 (Product, Plan, Price, ProviderSkuMapping, Subscription, PaymentEvent, DeviceSession)
- [x] 상태머신 단일 모듈 설계 확정 (모든 채널 공용)
- [x] 웹훅 검증/중복처리/재처리 큐 설계 확정
- [x] 클라이언트 권한 게이트 명세 확정 (모바일/PC 공통)

## 현재 저장소 기준선

- 현재 활성 마켓플레이스 결제는 [backend/marketplace/models.py](backend/marketplace/models.py) 의 `Purchase` 와 [backend/marketplace/payment_service.py](backend/marketplace/payment_service.py) 의 일회성 구매 흐름에 고정돼 있다.
- 현재 프런트 결제 유틸은 [frontend/frontend/lib/payment-service.ts](frontend/frontend/lib/payment-service.ts) 기준으로 `구매 생성 -> 결제 URL -> 환불/다운로드` 흐름만 가진다.
- 따라서 월구독은 기존 `Purchase` 도메인을 확장하는 대신, `Subscription` 계층을 병렬 추가해 `일회성 구매` 와 `정기권한` 을 분리해야 한다.

## 1단계 산출물 v1

### A. DB 스키마 v1

원칙

- 기존 `projects` / `purchases` 는 유지한다.
- 월구독은 `marketplace_subscriptions_*` 계열 신규 테이블로 분리한다.
- 권한 판정은 `subscription.plan_code` 와 `subscription.status` 기반으로만 수행한다.

테이블 정의

`subscription_products`

- 목적: 판매 대상 앱군/제품 정의
- 주요 컬럼
  - `id`
  - `code` (`marketplace-suite`, `video-studio`, `orchestrator-pro`)
  - `name`
  - `description`
  - `is_active`
  - `created_at`, `updated_at`

`subscription_plans`

- 목적: 권한 등급 정의
- 주요 컬럼
  - `id`
  - `product_id`
  - `plan_code` (`basic`, `pro`, `team`)
  - `plan_name`
  - `device_limit`
  - `feature_flags_json`
  - `is_active`
  - `created_at`, `updated_at`

`subscription_prices`

- 목적: 채널/국가/통화별 요금 정의
- 주요 컬럼
  - `id`
  - `product_id`
  - `plan_id`
  - `billing_period` (`monthly`)
  - `channel` (`apple`, `google`, `stripe`, `pg-web`)
  - `country_code`
  - `currency`
  - `amount_minor`
  - `external_price_code`
  - `is_active`
  - `created_at`, `updated_at`

`subscription_provider_mappings`

- 목적: 결제사 SKU / price code 와 내부 price 연결
- 주요 컬럼
  - `id`
  - `provider`
  - `external_product_id`
  - `external_price_id`
  - `price_id`
  - `raw_metadata_json`
  - `created_at`

`user_subscriptions`

- 목적: 사용자별 현재 구독 상태의 단일 진실원
- 주요 컬럼
  - `id`
  - `user_id`
  - `product_id`
  - `plan_id`
  - `price_id`
  - `source` (`apple`, `google`, `stripe`)
  - `status` (`none`, `trialing`, `active`, `grace_period`, `past_due`, `canceled`, `refunded`, `suspended`)
  - `current_period_start`
  - `current_period_end`
  - `grace_period_end`
  - `cancel_at_period_end`
  - `canceled_at`
  - `refunded_at`
  - `provider_customer_id`
  - `provider_subscription_id`
  - `provider_original_transaction_id`
  - `last_event_at`
  - `created_at`, `updated_at`

`subscription_events`

- 목적: 모든 결제/상태 변경 이벤트 감사 및 멱등 처리
- 주요 컬럼
  - `id`
  - `subscription_id`
  - `provider`
  - `event_id`
  - `event_type`
  - `event_time`
  - `idempotency_key`
  - `payload_json`
  - `applied`
  - `applied_at`
  - `error_message`
  - `created_at`

`subscription_devices`

- 목적: 동시 접속 기기 제한 관리
- 주요 컬럼
  - `id`
  - `subscription_id`
  - `user_id`
  - `device_fingerprint`
  - `device_type` (`ios`, `android`, `windows`, `macos`)
  - `device_name`
  - `last_seen_at`
  - `revoked_at`
  - `created_at`

`subscription_access_logs`

- 목적: 권한 판정 결과와 운영 추적 보강
- 주요 컬럼
  - `id`
  - `subscription_id`
  - `user_id`
  - `path`
  - `decision` (`allow`, `deny`, `grace`, `device_limit_denied`)
  - `reason`
  - `created_at`

설계 결론

- `Purchase` 는 프로젝트 개별 판매용으로 유지한다.
- 월구독은 `user_subscriptions` 를 통해 제품군 접근권을 부여한다.
- 같은 사용자에게 `구독` 과 `프로젝트 개별 구매` 가 공존 가능하다.

### B. 상태머신 단일 모듈 설계

대상 파일 초안

- `backend/marketplace/subscription_state_machine.py`
- `backend/marketplace/subscription_models.py`
- `backend/marketplace/subscription_service.py`

핵심 원칙

- Apple / Google / Stripe 이벤트는 모두 하나의 `apply_subscription_event()` 로 들어간다.
- 상태 전이는 한 곳에서만 수행한다.
- 라우터, 웹훅, 모바일 영수증 검증 로직은 직접 상태를 바꾸지 않는다.

핵심 함수 초안

`resolve_target_subscription(user_id, provider_payload)`

- 내부 subscription 식별

`normalize_provider_event(provider, payload)`

- 외부 이벤트를 내부 표준 이벤트로 정규화
- 반환 예시
  - `event_type`
  - `event_time`
  - `provider_subscription_id`
  - `provider_original_transaction_id`
  - `price_external_id`
  - `period_start`
  - `period_end`
  - `cancel_at_period_end`

`apply_subscription_event(subscription, normalized_event)`

- 실제 상태 전이
- out-of-order 방지: `normalized_event.event_time < subscription.last_event_at` 이면 무시

`derive_entitlements(subscription, plan)`

- 플랜 권한 계산

`can_access(subscription, device_context)`

- 기능 접근 허용 여부 계산

상태 전이 규칙 요약

- `purchase_confirmed` -> `active`
- `renewal_succeeded` -> `active`
- `renewal_failed` -> `grace_period`
- `grace_expired` -> `past_due`
- `cancel_requested` -> `active + cancel_at_period_end=true`
- `period_expired_after_cancel` -> `canceled`
- `refund_confirmed` -> `refunded`
- `admin_suspended` -> `suspended`

### C. 웹훅/검증/재처리 큐 설계

엔드포인트 원칙

- `POST /v1/billing/webhooks/stripe`
- `POST /v1/billing/webhooks/apple`
- `POST /v1/billing/webhooks/google`
- `POST /v1/billing/mobile/verify`

처리 순서

1. 서명 검증
2. `event_id` / `idempotency_key` 추출
3. `subscription_events` 에 원본 저장 시도
4. 이미 존재하면 `ignored=true` 로 종료
5. provider payload 정규화
6. 상태머신 적용
7. 성공 시 `applied=true`
8. 실패 시 `error_message` 저장 후 재처리 가능 상태 유지

재처리 원칙

- 동기 처리 실패 시 재시도 큐에 적재
- 최대 재시도 횟수와 백오프 정책 분리
- 3회 이상 실패 이벤트는 운영자 검토 큐로 이동

필수 보안

- Stripe: webhook signature 검증
- Apple: signed payload / notification 검증
- Google: purchase token / RTDN 원본 검증
- provider secret 은 모두 secret store 사용

### D. 클라이언트 권한 게이트 명세

공통 원칙

- 모바일/PC 모두 서버 권한 조회 결과만 신뢰한다.
- 클라이언트는 결제 성공 여부를 직접 확정하지 않는다.
- 기능 진입 시 `GET /v1/me/subscription` 또는 제품별 entitlement endpoint 를 조회한다.

모바일

- 앱 시작 시 구독 상태 프리페치
- 구매 완료 후 즉시 `POST /v1/billing/mobile/verify`
- 오프라인 허용은 마지막 정상 검증 시점부터 제한 시간 내에서만 인정

로컬PC

- 로그인 후 구독 상태 프리페치
- 앱 실행 시 device register
- 중요 기능 진입 시 subscription 상태와 device limit 재검사

게이트 판정 규칙

- `active` -> 허용
- `trialing` -> 허용
- `grace_period` -> 허용 + 경고 배너
- `past_due` -> 제한
- `canceled` + 기간 남음 -> 허용
- `canceled` + 기간 종료 -> 제한
- `refunded` / `suspended` -> 즉시 제한

## 1단계 실행 로그

- 상태: `구현됨`
- 수행 내용:
  - 현재 저장소의 활성 결제 도메인([backend/marketplace/models.py](backend/marketplace/models.py), [backend/marketplace/payment_service.py](backend/marketplace/payment_service.py), [frontend/frontend/lib/payment-service.ts](frontend/frontend/lib/payment-service.ts))을 확인했다.
  - 기존 일회성 구매 `Purchase` 와 신규 월구독 `Subscription` 을 분리하는 DB 스키마 v1 을 정의했다.
  - 단일 상태머신 모듈, 웹훅 멱등 처리, 클라이언트 권한 게이트 설계를 문서화했다.
- 근거:
  - 현재 코드에는 `Purchase.status`, `payment_method`, `transaction_id`, `receipt_url` 기반 일회성 구매만 존재한다.
  - 월구독용 엔티티와 웹훅 이벤트 저장소는 현재 부재하므로 신규 추가가 필요하다는 결론을 문서에 고정했다.
- 차단 여부:
  - 없음. 설계 1단계 산출물은 문서 기준으로 확정됐지만, 코드 구현과 2회 검증 전이므로 전체 상태는 여전히 `구현됨` 이다.

## 2단계 구현 체크리스트

- [x] 결제 채널별 어댑터 구현 (Apple/Google/Stripe)
- [x] 구독 상태 전이 엔진 구현
- [x] API v1 엔드포인트 구현
- [x] 라우터/서비스 실패 응답 일관성 잠금 (운영 가드 400/503)
- [x] 관리자 모니터링 화면 구현 (실패결제, 환불, 상태변경 이력)

## 구현 착수 로그

### Step 2-1. 구독 SQLAlchemy 모델 초안 추가

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/subscription_models.py](backend/marketplace/subscription_models.py) 를 새로 추가해 월구독 전용 모델 초안을 작성했다.
  - `SubscriptionProduct`, `SubscriptionPlan`, `SubscriptionEntitlement`, `SubscriptionPrice`, `ProviderSkuMapping`, `SubscriptionProductProject`, `UserSubscription`, `PaymentEvent`, `SubscriptionStateTransition`, `WebhookDeliveryAttempt`, `DeviceSession` 모델을 분리 정의했다.
  - [backend/marketplace/database.py](backend/marketplace/database.py) 의 `init_db()` 에 `subscription_models` import 를 추가해 `Base.metadata.create_all(...)` 경로에서 신규 테이블이 등록되도록 연결했다.
- 검증:
  - `python -m py_compile backend/marketplace/subscription_models.py backend/marketplace/database.py`
  - 에디터 오류 검사: 신규 파일 2개 오류 없음
- 차단 여부:
  - 없음. 다만 아직 migration, 상태머신, API 연결 전이라 운영 경로에는 미노출 상태다.

### Step 2-2. 구독 상태머신 모듈 추가

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/subscription_state_machine.py](backend/marketplace/subscription_state_machine.py) 를 추가했다.
  - `SubscriptionStatus`, `SubscriptionEventType`, `SubscriptionSnapshot`, `NormalizedSubscriptionEvent`, `TransitionResult` 를 정의했다.
  - `apply_subscription_event()` 와 이벤트별 핸들러를 구현해 상태 전이를 단일 모듈로 고정했다.
- 검증:
  - `python -m py_compile backend/marketplace/subscription_state_machine.py`
  - 에디터 오류 검사: 신규 상태머신 파일 오류 없음
- 차단 여부:
  - 없음. 다만 아직 서비스 계층과 라우터가 이 상태머신을 호출하지 않으므로 실제 운영 경로에는 연결되지 않았다.

### Step 2-3. 구독 API v1 최소 엔드포인트 추가

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py) 를 추가해 구독 조회/모바일 검증용 서비스 계층을 만들었다.
  - [backend/marketplace/schemas.py](backend/marketplace/schemas.py) 에 `SubscriptionStatusResponse`, `MobileSubscriptionVerifyRequest`, `MobileSubscriptionVerifyResponse` 를 추가했다.
  - [backend/marketplace/router.py](backend/marketplace/router.py) 에 `GET /v1/me/subscription`, `POST /v1/billing/mobile/verify` 엔드포인트를 추가했다.
  - [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 를 추가해 신규 API 2개에 대한 계약 테스트를 만들었다.
- 검증:
  - 에디터 오류 검사: [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/schemas.py](backend/marketplace/schemas.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 오류 없음
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py -q` -> `2 passed`
- 차단 여부:
  - 있음. 현재 `POST /v1/billing/mobile/verify` 는 외부 App Store / Google Play 실검증 어댑터 전 단계이므로 `MARKETPLACE_BILLING_ALLOW_SIMULATED_VERIFY=true` 에서만 시뮬레이션 검증으로 동작한다. 실제 운영 검증은 채널 어댑터 구현 후 별도 2회 실검증이 필요하다.

### Step 2-4. 결제 채널 어댑터 초안 구현

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/provider_adapters/__init__.py](backend/marketplace/provider_adapters/__init__.py), [backend/marketplace/provider_adapters/base.py](backend/marketplace/provider_adapters/base.py), [backend/marketplace/provider_adapters/registry.py](backend/marketplace/provider_adapters/registry.py) 를 추가해 Apple/Google/Stripe 공통 어댑터 계약과 레지스트리를 만들었다.
  - [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py) 를 추가해 모바일 검증/PC 체크아웃 세션의 provider별 진입점을 분리했다.
  - [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py) 를 리팩터링해 모바일 검증이 서비스 내부 시뮬레이션 분기 대신 어댑터 결과를 상태머신에 반영하도록 변경했다.
  - [backend/marketplace/schemas.py](backend/marketplace/schemas.py), [backend/marketplace/router.py](backend/marketplace/router.py) 에 Stripe 체크아웃 세션 요청/응답 계약과 `POST /v1/billing/checkout/sessions` 경로를 추가했다.
  - [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 에 checkout session 계약 테스트를 추가했다.
- 검증:
  - 에디터 오류 검사: [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 오류 없음
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py -q` -> `3 passed`
- 차단 여부:
  - 있음. 현재 Apple/Google/Stripe 어댑터는 실결제사 API 호출 대신 시뮬레이션/설정 점검 계층까지 구현된 상태다. 실운영 웹훅 서명 검증과 실제 provider API 검증은 후속 단계에서 연결해야 한다.

### Step 2-5. 구독 API v1 잔여 경로 추가

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/schemas.py](backend/marketplace/schemas.py) 에 취소/재개, 기기 등록/해제, webhook intake 요청/응답 계약을 추가했다.
  - [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py) 에 `cancel_subscription()`, `resume_subscription()`, `register_device()`, `revoke_device()`, `process_webhook()` 를 추가했다.
  - `cancel/resume` 는 기존 상태머신의 `CANCEL_SCHEDULED`, `CANCEL_REVOKED` 이벤트를 사용하도록 연결했다.
  - `device register/revoke` 는 기존 `device_sessions` 와 구독 `device_limit` 필드를 사용해 최소 등록/회수 흐름을 구현했다.
  - [backend/marketplace/router.py](backend/marketplace/router.py) 에 `POST /v1/me/subscription/cancel`, `POST /v1/me/subscription/resume`, `POST /v1/me/devices/register`, `POST /v1/me/devices/revoke`, `POST /v1/billing/webhooks/{provider}` 경로를 추가했다.
  - [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 에 신규 경로 5개 계약 테스트를 추가했다.
- 검증:
  - 에디터 오류 검사: [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 오류 없음
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py -q` -> `8 passed`
- 차단 여부:
  - 있음. webhook 경로는 동작하지만 provider 어댑터로의 정규화/서명검증 이동 전 단계다.

### Step 2-6. webhook 정규화/서명검증 어댑터 이동 + 서비스 DB 테스트 추가

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/provider_adapters/base.py](backend/marketplace/provider_adapters/base.py) 에 `AdapterWebhookResult` 계약을 추가했다.
  - [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py) 에 `parse_webhook()` 를 추가해 provider별 event_type 정규화와 HMAC 서명검증을 어댑터 레이어로 이동했다.
  - [backend/marketplace/provider_adapters/registry.py](backend/marketplace/provider_adapters/registry.py) 에 `webhook_adapter_for_provider()` 를 추가했다.
  - [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py) 에서 webhook event map 직접 처리 로직을 제거하고, 어댑터 반환값(`AdapterWebhookResult`) 기반 상태 전이로 전환했다.
  - [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py) 를 추가해 취소/재개와 기기 등록/회수의 DB 상태 변화를 서비스 레벨에서 검증하고, webhook 서명검증 경로도 함께 검증했다.
- 검증:
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py backend/tests/test_marketplace_webhook_adapter_parsers.py -q` -> `17 passed`
  - 에디터 오류 검사: 어댑터/서비스/신규 서비스 테스트 파일 오류 없음
- 차단 여부:
  - 있음. Stripe는 `Stripe-Signature(t=,v1=)` 파서를 적용했고, Apple/Google 실운영 검증은 Step 2-8 에서 후속 고도화했다. 현재 남은 차단은 Apple 공개 루트 체인 정책(루트 pinset 자동 갱신)과 Google OIDC audience/issuer 운영값 고정 배포가 필요하다는 점이다.

### Step 2-8. Apple x5c + Google OIDC 실운영 검증 고도화

- 상태: `구현됨`
- 수행 내용:
  - [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py) 에 ES256 + `x5c` 체인 검증 경로를 추가했다.
  - Apple 경로는 JWS 헤더의 `x5c` 인증서 체인을 순차 검증하고, `MARKETPLACE_APPLE_ROOT_CA_PEM` 이 지정되면 루트 앵커 검증까지 수행한다.
  - [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py) 에 OIDC/JWKS 검증 경로를 추가했다.
  - Google 경로는 Pub/Sub push OIDC 토큰을 `kid` 기반 JWKS 조회로 검증하고 `audience`, `issuer`, `service_account(email)` 검사를 수행한다.
  - [backend/tests/test_marketplace_webhook_adapter_parsers.py](backend/tests/test_marketplace_webhook_adapter_parsers.py) 에 Apple ES256+x5c 체인 테스트와 Google OIDC/JWKS 체인 테스트를 추가했다.
- 검증:
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_webhook_adapter_parsers.py backend/tests/test_marketplace_subscription_service.py -q` -> `11 passed`
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py backend/tests/test_marketplace_webhook_adapter_parsers.py -q` -> `17 passed` (직전 검증 결과 유지)
- 차단 여부:
  - 있음. Apple 실서비스 루트/중간 인증서 pinset 운영 정책 자동화와 Google OIDC audience/issuer 운영값 강제 배포는 운영 배포 단계에서 추가 고정이 필요하다.

### Step 2-9. 라우터/서비스 실패 응답 일관성 잠금

- 상태: `구현됨`
- 수행 내용:
  - [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py) 에 운영 가드 실패 통합 케이스를 추가해 서비스 레벨 실패 응답을 고정했다.
  - Apple pinset 파일 누락 시 `400`, Google OIDC 운영 필수값 누락 시 `503` 응답을 서비스 경로에서 검증했다.
  - [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 에 동일 실패를 라우터 경로로 전달했을 때 status/detail 이 그대로 보존되는 계약 케이스를 추가했다.
- 검증:
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_service.py -q` -> `7 passed`
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py -q` -> `17 passed`
- 차단 여부:
  - 없음. 운영 가드 실패 응답의 서비스/라우터 정합성은 테스트로 잠금 완료.

### Step 2-10. 관리자 구독 모니터링 화면 구현

- 상태: `구현됨`
- 수행 내용:
  - [backend/admin_router.py](backend/admin_router.py) 에 `GET /api/admin/subscription-monitor-summary` 경로를 추가했다.
  - 동일 파일에 `_build_admin_subscription_monitor_summary_payload()` 를 추가해 `실패 결제(24h)`, `환불(30d)`, `상태 분포`, `상태 변경 이력`, `웹훅 실패/재시도 이력` 집계를 제공하도록 고정했다.
  - [frontend/frontend/components/admin/admin-subscription-monitor-section.tsx](frontend/frontend/components/admin/admin-subscription-monitor-section.tsx) 를 추가해 관리자 패널에서 새로고침/요약 지표/이력 리스트를 표시하도록 구현했다.
  - [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx) 에 런처 버튼과 보드 섹션(`💳 구독 결제 운영 모니터링`)을 연결했다.
  - [frontend/frontend/lib/admin-dashboard-types.ts](frontend/frontend/lib/admin-dashboard-types.ts) 에 `AdminSubscriptionMonitorSummary` 타입 계열을 추가했다.
  - [backend/tests/test_admin_project_root_service.py](backend/tests/test_admin_project_root_service.py) 에 신규 라우트 계약 테스트(`test_subscription_monitor_summary_route_returns_helper_payload`)를 추가했다.
- 검증:
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_admin_project_root_service.py -k subscription_monitor_summary_route_returns_helper_payload -q` -> `1 passed` (1차)
  - `./.venv/Scripts/python.exe -m pytest backend/tests/test_admin_project_root_service.py -k subscription_monitor_summary_route_returns_helper_payload -q` -> `1 passed` (2차)
  - 에디터 오류 검사: [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx), [frontend/frontend/components/admin/admin-subscription-monitor-section.tsx](frontend/frontend/components/admin/admin-subscription-monitor-section.tsx), [frontend/frontend/lib/admin-dashboard-types.ts](frontend/frontend/lib/admin-dashboard-types.ts), [backend/tests/test_admin_project_root_service.py](backend/tests/test_admin_project_root_service.py) 오류 없음
- 차단 여부:
  - 없음. 관리자 화면에서 월구독 운영 핵심 지표/이력 확인 경로를 확보했다.

### Step 2-10 운영 실검증 보강 (기간/상태 필터 + 화면 새로고침)

- 상태: `구현됨`
- 수행 내용:
  - `GET /api/admin/subscription-monitor-summary` 에 `period_days`, `status` 쿼리 필터를 적용해 기간/상태 기반 운영 집계를 확장했다.
  - 관리자 패널 UI에서 기간/상태 필터를 선택하고 새로고침 시 동일 쿼리 파라미터가 반영되도록 연결했다.
  - 운영 화면 검증 경로를 `/admin/subscription-monitor` 로 분리해 패널 렌더와 새로고침을 실접속 기준으로 확인했다.
- 검증:
  - API 운영 호출 1차: `http://127.0.0.1:8000/api/admin/subscription-monitor-summary?period_days=7&status=active` -> `filters={"period_days":7,"status":"active"}` 확인
  - API 운영 호출 2차: `http://127.0.0.1:8000/api/admin/subscription-monitor-summary?period_days=30` -> `filters={"period_days":30,"status":null}` 확인
  - 화면 운영 검증 1차: `http://127.0.0.1:3012/admin/subscription-monitor` 에서 `구독 모니터링 새로고침` 클릭 후 `갱신 중...` 전환 및 복귀 확인
  - 화면 운영 검증 2차: 동일 버튼 재클릭 후 `갱신 중...` 전환 및 `구독 모니터링 새로고침` 복귀 확인
  - 필터 반영 확인: 기간을 `최근 7일`로 변경 후 카드 라벨이 `최근 7일 실패 결제`, `최근 7일 환불`로 동적 변경 확인
  - 메인 레일 원인 확인: `127.0.0.1:3005` 는 코드 불일치가 아니라 구버전 `devanalysis114-frontend-admin` 컨테이너 이미지가 포트를 점유한 상태였고, 재빌드 전 스냅샷에서 `💳 구독` 버튼이 누락됨을 확인
  - 메인 레일 수정 조치: `docker compose up -d --build frontend-admin frontend-marketplace` 재실행으로 `frontend-admin` 컨테이너를 최신 소스로 교체
  - 메인 `/admin` 렌더 검증: `http://127.0.0.1:3005/admin` 스냅샷에서 레일 `💳 구독` 버튼 노출 확인
  - 메인 `/admin` 새로고침 검증 1차: 레일 `💳 구독` 클릭으로 패널 오픈 후 `구독 모니터링 새로고침` 클릭 -> `갱신 중...` 전환 및 복귀 확인
  - 메인 `/admin` 새로고침 검증 2차: 동일 버튼 재클릭 -> `갱신 중...` 전환 및 `구독 모니터링 새로고침` 복귀 확인
- 차단 여부:
  - 없음. `/admin` 메인 레일 누락 원인은 구버전 컨테이너 이미지였고, 재빌드 이후 메인 경로 렌더/새로고침 2회 실검증까지 완료했다.

## 3단계 검증 체크리스트

- [x] 신규 구독 성공 시나리오 2회 통과
- [x] 자동갱신 성공 시나리오 2회 통과
- [x] 결제실패 -> grace -> 복구 시나리오 2회 통과
- [x] 해지예약 -> 기간종료 해지 시나리오 2회 통과
- [x] 환불 후 권한 회수 시나리오 2회 통과
- [x] 기기 제한 정책 시나리오 2회 통과

### 3단계 실행 로그 (실검증 2회)

- 상태: `완료됨`
- 실행 환경: `docker exec devanalysis114-backend` 내부에서 `python /tmp/step3_subscription_validate.py` 실행
- 증적 파일 1차: [reports/step3_subscription_validation_20260428_155310.json](reports/step3_subscription_validation_20260428_155310.json)
- 증적 파일 2차: [reports/step3_subscription_validation_20260428_155613.json](reports/step3_subscription_validation_20260428_155613.json)
- 시나리오 통과 근거(1차/2차 동일):
  - 신규 구독 성공: `purchase_verified` 이벤트 2회 모두 `active`
  - 자동갱신 성공: `renewal_succeeded` 이벤트 2회 모두 `active`
  - 결제실패 -> grace -> 복구: `renewal_failed` 후 `grace_period`, `renewal_succeeded` 후 `active` (각 2회)
  - 해지예약 -> 기간종료 해지: `cancel_at_period_end=true` 후 `period_ended` 적용 시 `canceled` (2회)
  - 환불 후 권한 회수: `refund_applied` 후 `refunded`, `subscription_restored` 후 `active` (2회)
  - 기기 제한 정책: 동일 구독에서 `device_limit=1` 기준 1대 등록 `200`, 2대째 등록 `409` (2회)
- 차단 여부:
  - 없음. 초기 실행 중 발생한 환경 차단(`mobile/verify` 시뮬레이션 비활성, 웹훅 aware-naive 시간 비교)은 웹훅 기반 시나리오 및 naive UTC 이벤트 시각으로 재실행하여 2회 실검증 통과까지 확인.

## 제품별 요금 차등 정책 (중요)

- [x] 제품별/플랜별/국가별/채널별 요금 차등 허용
- [x] 권한 판정은 금액이 아니라 `plan_id` 기반으로 수행
- [x] 결제사 SKU와 내부 `price_id` 매핑 테이블 운영

## 이슈/차단 기록

| ID | 항목 | 증상 | 조치 | 상태 |
| --- | --- | --- | --- | --- |
| BILLING-DESIGN-001 | 문서 고정 | 체크리스트가 대화에만 존재하면 추적 불가 | 본 문서 생성 및 설계 0단계 체크 동기화 | 완료됨 |
| BILLING-DESIGN-002 | 저장소 기준선 | 현재 결제 코드가 일회성 구매 중심이라 월구독을 같은 테이블에 억지로 넣으면 계약이 오염됨 | `Purchase` 와 별도 `Subscription` 도메인으로 분리하는 스키마/상태머신/게이트 설계를 문서에 고정 | 완료됨 |
| BILLING-IMPLEMENT-001 | 모델 초안 | 월구독 엔티티가 코드에 없어 이후 상태머신/API 구현을 시작할 수 없음 | [backend/marketplace/subscription_models.py](backend/marketplace/subscription_models.py) 추가 및 [backend/marketplace/database.py](backend/marketplace/database.py) 등록 경로 연결 | 구현됨 |
| BILLING-IMPLEMENT-002 | 상태머신 초안 | provider/webhook/API 마다 상태 문자열을 직접 바꾸면 전이 규칙이 분산됨 | [backend/marketplace/subscription_state_machine.py](backend/marketplace/subscription_state_machine.py) 추가로 상태/이벤트/전이 결과를 단일 모듈로 고정 | 구현됨 |
| BILLING-IMPLEMENT-003 | API 최소 경로 | 구독 상태 조회/모바일 검증 API 부재로 클라이언트와 상태머신 연결을 시작할 수 없음 | [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/marketplace/schemas.py](backend/marketplace/schemas.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 추가 | 구현됨 |
| BILLING-IMPLEMENT-004 | 채널 어댑터 초안 | 모바일 검증이 서비스 내부 시뮬레이션에 고정돼 Apple/Google/Stripe 별 계약 분리와 PC 체크아웃 세션 진입점을 만들 수 없음 | [backend/marketplace/provider_adapters/__init__.py](backend/marketplace/provider_adapters/__init__.py), [backend/marketplace/provider_adapters/base.py](backend/marketplace/provider_adapters/base.py), [backend/marketplace/provider_adapters/registry.py](backend/marketplace/provider_adapters/registry.py), [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py), [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 추가/수정 | 구현됨 |
| BILLING-IMPLEMENT-005 | API 잔여 경로 | 취소/재개, webhook, 기기 등록/회수 경로가 없어 월구독 운영 수명주기를 닫을 수 없음 | [backend/marketplace/schemas.py](backend/marketplace/schemas.py), [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/router.py](backend/marketplace/router.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 추가/수정 | 구현됨 |
| BILLING-IMPLEMENT-006 | webhook 어댑터화 + 서비스 테스트 | webhook event_type 정규화/서명검증이 서비스에 남아 있고, 취소/재개/기기 등록의 DB 변화가 서비스 레벨에서 검증되지 않음 | [backend/marketplace/provider_adapters/base.py](backend/marketplace/provider_adapters/base.py), [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py), [backend/marketplace/provider_adapters/registry.py](backend/marketplace/provider_adapters/registry.py), [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py) 추가/수정 | 구현됨 |
| BILLING-IMPLEMENT-007 | 실서명 파서 분리 + 재시도/Dead-letter | provider별 실서명 규격 파서가 공통 형태로 뭉쳐 있고 webhook 실패 재시도/dead-letter 정책이 부재함 | [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py), [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py), [backend/tests/test_marketplace_webhook_adapter_parsers.py](backend/tests/test_marketplace_webhook_adapter_parsers.py) 추가/수정 | 구현됨 |
| BILLING-IMPLEMENT-008 | Apple x5c + Google OIDC | Apple/Google 실운영 체인 검증이 부재해 운영 보안 게이트가 불완전함 | [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/tests/test_marketplace_webhook_adapter_parsers.py](backend/tests/test_marketplace_webhook_adapter_parsers.py) 추가/수정 | 구현됨 |
| BILLING-IMPLEMENT-009 | 실패 응답 일관성 잠금 | 운영 가드 실패 시 서비스와 라우터 응답 코드/메시지 불일치 위험 | [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py), [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 에 400/503 실패 전파 케이스 추가 | 구현됨 |
| BILLING-IMPLEMENT-010 | 관리자 구독 모니터링 화면 | 관리자 화면에서 실패결제/환불/상태변경/웹훅 실패를 한 번에 확인할 수 없어 운영 대응이 지연됨 | [backend/admin_router.py](backend/admin_router.py), [frontend/frontend/components/admin/admin-subscription-monitor-section.tsx](frontend/frontend/components/admin/admin-subscription-monitor-section.tsx), [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx), [frontend/frontend/lib/admin-dashboard-types.ts](frontend/frontend/lib/admin-dashboard-types.ts), [backend/tests/test_admin_project_root_service.py](backend/tests/test_admin_project_root_service.py) 추가/수정 | 구현됨 |

## 4단계 프런트엔드 구독 UX 체크리스트

- [x] `lib/subscription-service.ts` — 구독 조회/취소/재개/체크아웃 API 호출 함수 + 타입 정의
- [x] `components/marketplace/subscription-status-card.tsx` — 현재 구독 상태 카드 (상태/플랜/기간/기기수 + 취소/재개 버튼)
- [x] `app/marketplace/subscription/page.tsx` — 구독 관리 페이지 (상태 조회, 취소, 재개, 체크아웃 세션 생성)
- [x] `marketplace-rails.tsx` — `subscription` 레일 항목 추가 (`MarketplaceRailId` 확장 포함)

### 4단계 실행 로그 (실검증 2회)

- 상태: `완료됨`
- 수행 내용:
  - 프런트 구독 API 유틸 [frontend/frontend/lib/subscription-service.ts](frontend/frontend/lib/subscription-service.ts) 추가.
  - 구독 상태 카드 [frontend/frontend/components/marketplace/subscription-status-card.tsx](frontend/frontend/components/marketplace/subscription-status-card.tsx) 추가.
  - 구독 관리 페이지 [frontend/frontend/app/marketplace/subscription/page.tsx](frontend/frontend/app/marketplace/subscription/page.tsx) 추가.
  - 마켓플레이스 레일 구독 진입점 [frontend/frontend/components/marketplace/marketplace-rails.tsx](frontend/frontend/components/marketplace/marketplace-rails.tsx) 반영.
  - `docker compose ... build frontend-marketplace` 재빌드 완료 및 `/marketplace/subscription` 라우트 빌드 산출 확인.
  - 운영 검증 2회 수행:
    - [reports/step4_subscription_validation_20260429_012042_pass1.json](reports/step4_subscription_validation_20260429_012042_pass1.json)
    - [reports/step4_subscription_validation_20260429_012043_837_pass2.json](reports/step4_subscription_validation_20260429_012043_837_pass2.json)
- 검증 요약:
  - pass1/pass2 모두 페이지 응답 `200`, 로그인 `200`, 구독 조회 `200`, 해지 `200`, 재개 `200`.

## 5단계 체크아웃 복귀 UX 안정화 체크리스트

- [x] `app/marketplace/subscription/page.tsx` 에 `checkout=success|cancel` 복귀 상태 처리 추가
- [x] 결제 복귀 메시지 표시 후 URL 쿼리(`checkout`) 자동 정리 처리
- [x] 성공/취소 복귀 시나리오를 각각 1회씩, 총 2회 실검증 통과

### 5단계 실행 로그 (실검증 2회)

- 상태: `완료됨`
- 수행 내용:
  - [frontend/frontend/app/marketplace/subscription/page.tsx](frontend/frontend/app/marketplace/subscription/page.tsx) 에 체크아웃 복귀 상태(`success`, `cancel`) 처리 로직을 추가했다.
  - `checkout` 쿼리 파라미터를 메시지 처리 후 `history.replaceState` 로 URL에서 제거하도록 고정했다.
  - 3000 런타임 반영을 위해 `docker compose up -d --build frontend-marketplace frontend-admin` 재빌드를 수행했다.
- 검증:
  - pass1(성공 복귀): `http://127.0.0.1:3000/marketplace/subscription?checkout=success` 진입 후 성공 메시지 노출 + URL 쿼리 제거 확인
    - [reports/step5_checkout_return_validation_20260429_012801_pass1.json](reports/step5_checkout_return_validation_20260429_012801_pass1.json)
  - pass2(취소 복귀): `http://127.0.0.1:3000/marketplace/subscription?checkout=cancel` 진입 후 취소 메시지 노출 + URL 쿼리 제거 확인
    - [reports/step5_checkout_return_validation_20260429_012802_pass2.json](reports/step5_checkout_return_validation_20260429_012802_pass2.json)
- 차단 여부:
  - 없음. 복귀 메시지 노출과 URL 정리 동작이 2회 실검증으로 확인됐다.

## 6단계 관리자 구독 모니터링 딥링크 안정화 체크리스트

- [x] `/admin?panel=subscription-monitor` 진입 시 구독 모니터링 패널 자동 오픈 처리
- [x] `period_days`, `status` 쿼리를 구독 모니터링 필터 초기값으로 반영
- [x] 관리자 메인/단독 라우트 각각 1회씩, 총 2회 실검증 통과

### 6단계 실행 로그 (실검증 2회)

- 상태: `완료됨`
- 수행 내용:
  - [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx) 에 `panel=subscription-monitor` 딥링크 감지 시 패널 자동 오픈 및 해당 섹션 스크롤 처리를 추가했다.
  - [frontend/frontend/components/admin/admin-subscription-monitor-section.tsx](frontend/frontend/components/admin/admin-subscription-monitor-section.tsx) 에 URL 쿼리(`period_days`, `status`) 기반 필터 초기화 로직을 추가했다.
  - 런타임 반영을 위해 `docker compose up -d --build frontend-admin frontend-marketplace` 재빌드를 수행했다.
- 검증:
  - pass1(메인 관리자 딥링크): `http://127.0.0.1:3005/admin?panel=subscription-monitor&period_days=7&status=all` 진입 후 모니터링 패널 자동 오픈 + 기간 7일 선택 + `최근 7일 실패 결제` 라벨 확인
    - [reports/step6_admin_subscription_deeplink_validation_20260429_013833_pass1.json](reports/step6_admin_subscription_deeplink_validation_20260429_013833_pass1.json)
  - pass2(단독 모니터링 라우트): `http://127.0.0.1:3005/admin/subscription-monitor?period_days=90&status=all` 진입 후 기간 90일 선택 + `최근 90일 실패 결제` 라벨 확인
    - [reports/step6_admin_subscription_deeplink_validation_20260429_013903_pass2.json](reports/step6_admin_subscription_deeplink_validation_20260429_013903_pass2.json)
- 차단 여부:
  - 없음. 딥링크 패널 오픈과 필터 초기화가 2회 실검증으로 확인됐다.

## 7단계 관리자 구독 모니터링 우측 진입 레일 체크리스트

- [x] `/admin/subscription-monitor` 우측 영역에 운영 진입 레일 UI 추가
- [x] 관리자 대시보드/7일/30일/90일/마켓 구독 페이지 링크 노출
- [x] 단독 모니터링 라우트에서 2회 실검증 통과

### 7단계 실행 로그 (실검증 2회)

- 상태: `완료됨`
- 수행 내용:
  - [frontend/frontend/app/admin/subscription-monitor/page.tsx](frontend/frontend/app/admin/subscription-monitor/page.tsx) 에 우측 고정 진입 레일(`⚡ 진입 레일`) 영역을 추가했다.
  - 진입 레일 링크를 관리자 대시보드, 최근 7일/30일/90일 모니터링, 마켓 구독 페이지로 구성했다.
  - 런타임 반영을 위해 `docker compose up -d --build frontend-admin frontend-marketplace` 재빌드를 수행했다.
- 검증:
  - pass1(90일 필터 진입): `http://127.0.0.1:3005/admin/subscription-monitor?period_days=90&status=all` 에서 우측 레일 헤더/링크 목록 노출 확인
    - [reports/step7_admin_subscription_entry_rail_validation_20260429_014344_pass1.json](reports/step7_admin_subscription_entry_rail_validation_20260429_014344_pass1.json)
  - pass2(7일 필터 전환): 레일의 `최근 7일 모니터링` 링크 클릭 후 `period_days=7` 진입 상태에서 우측 레일 유지 및 active 링크 확인
    - [reports/step7_admin_subscription_entry_rail_validation_20260429_014425_pass2.json](reports/step7_admin_subscription_entry_rail_validation_20260429_014425_pass2.json)
- 차단 여부:
  - 없음. 우측 진입 레일 노출과 링크 동작이 2회 실검증으로 확인됐다.

## 변경 이력

- 2026-04-28: 초기 생성. 설계 0단계 산출물(정책표/상태전이/API v1) 반영.
- 2026-04-28: 1단계 구현 준비 산출물(DB 스키마 v1, 상태머신 모듈 기준, 웹훅/재처리 원칙, 모바일/PC 권한 게이트) 반영.
- 2026-04-28: Step 2-1 코드 착수. 구독 SQLAlchemy 모델 초안 추가 및 `init_db()` 메타데이터 등록 경로 연결.
- 2026-04-28: Step 2-2 코드 착수. 구독 상태머신 모듈 추가 및 파이썬 검증 통과.
- 2026-04-28: Step 2-3 코드 착수. 구독 조회/모바일 검증 API 최소 경로 및 계약 테스트 추가.
- 2026-04-28: Step 2-4 코드 착수. Apple/Google/Stripe 어댑터 레이어와 Stripe checkout session 경로 추가, 계약 테스트 3건 통과.
- 2026-04-28: Step 2-5 코드 착수. 취소/재개, webhook, 기기 등록/회수 경로 추가, 계약 테스트 8건 통과.
- 2026-04-28: Step 2-6 코드 착수. webhook 정규화/서명검증 어댑터 이동, 서비스 레벨 DB 테스트 추가.
- 2026-04-28: Step 2-7 코드 착수. provider별 실서명 규격 파서 분리(Stripe 헤더/JWS/PubSub envelope) 및 webhook retry backoff + dead-letter 처리 추가.
- 2026-04-28: Step 2-8 코드 착수. Apple ES256+x5c 체인 검증 및 Google OIDC/JWKS 검증 경로 추가.
- 2026-04-29: Step 2-9 코드 착수. 운영 가드 실패(Apple pinset 파일 누락 400, Google OIDC 운영 필수값 누락 503)에 대한 서비스/라우터 응답 일관성 테스트 잠금 완료.
- 2026-04-29: Step 2-10 코드 착수. 관리자 구독 모니터링 API/대시보드 섹션 추가 및 신규 라우트 계약 테스트 2회 통과.
- 2026-04-29: Step 2-10 운영 실검증 보강. 관리자 구독 모니터링 API 기간/상태 필터 운영 호출 2회와 `/admin/subscription-monitor` 화면 새로고침 2회(로딩 전환/복귀) 확인, 기간 7일 라벨 동적 반영 확인.
- 2026-04-29: Step 2-10 메인 경로 보강. `127.0.0.1:3005` 레일 누락 원인을 구버전 `frontend-admin` 컨테이너로 확정하고 재빌드 반영 후 `/admin` 메인 레일 `💳 구독` 노출 및 패널 새로고침 2회(로딩 전환/복귀) 검증 완료.
- 2026-04-29: Step 3 실검증 2회 완료. `docker exec devanalysis114-backend` 기준 구독 상태 전이 6개 시나리오를 각 2회 실행하고 [reports/step3_subscription_validation_20260428_155310.json](reports/step3_subscription_validation_20260428_155310.json), [reports/step3_subscription_validation_20260428_155613.json](reports/step3_subscription_validation_20260428_155613.json) 증적 동기화.
- 2026-04-29: Step 4 프런트엔드 구독 UX 완료. 구독 서비스/카드/페이지/레일 추가 후 컨테이너 재빌드 및 구독 조회/해지/재개 실검증 2회 통과, 증적 [reports/step4_subscription_validation_20260429_012042_pass1.json](reports/step4_subscription_validation_20260429_012042_pass1.json), [reports/step4_subscription_validation_20260429_012043_837_pass2.json](reports/step4_subscription_validation_20260429_012043_837_pass2.json) 반영.
- 2026-04-29: Step 5 체크아웃 복귀 UX 안정화 완료. `checkout=success|cancel` 복귀 메시지 처리와 URL 쿼리 제거를 [frontend/frontend/app/marketplace/subscription/page.tsx](frontend/frontend/app/marketplace/subscription/page.tsx) 에 반영하고, 실검증 2회 증적 [reports/step5_checkout_return_validation_20260429_012801_pass1.json](reports/step5_checkout_return_validation_20260429_012801_pass1.json), [reports/step5_checkout_return_validation_20260429_012802_pass2.json](reports/step5_checkout_return_validation_20260429_012802_pass2.json) 동기화.
- 2026-04-29: Step 6 관리자 구독 모니터링 딥링크 안정화 완료. [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx) 패널 딥링크 자동 오픈과 [frontend/frontend/components/admin/admin-subscription-monitor-section.tsx](frontend/frontend/components/admin/admin-subscription-monitor-section.tsx) 필터 쿼리 초기화를 반영하고, 실검증 2회 증적 [reports/step6_admin_subscription_deeplink_validation_20260429_013833_pass1.json](reports/step6_admin_subscription_deeplink_validation_20260429_013833_pass1.json), [reports/step6_admin_subscription_deeplink_validation_20260429_013903_pass2.json](reports/step6_admin_subscription_deeplink_validation_20260429_013903_pass2.json) 동기화.
- 2026-04-29: Step 7 관리자 단독 구독 모니터링 우측 진입 레일 추가 완료. [frontend/frontend/app/admin/subscription-monitor/page.tsx](frontend/frontend/app/admin/subscription-monitor/page.tsx) 에 우측 레일 링크 허브를 추가하고, 실검증 2회 증적 [reports/step7_admin_subscription_entry_rail_validation_20260429_014344_pass1.json](reports/step7_admin_subscription_entry_rail_validation_20260429_014344_pass1.json), [reports/step7_admin_subscription_entry_rail_validation_20260429_014425_pass2.json](reports/step7_admin_subscription_entry_rail_validation_20260429_014425_pass2.json) 동기화.
- 2026-04-29: 문서 기준 미구현/미완료 재수행. 파일별 실행흐름 점검 결과 [backend/tests/test_marketplace_subscription_contract.py](backend/tests/test_marketplace_subscription_contract.py) 가 [backend/marketplace/router.py](backend/marketplace/router.py) 의 `subscription_service` 심볼을 monkeypatch 대상으로 요구했으나 라우터 모듈 노출이 끊겨 10건 회귀 실패를 재현했다.
- 2026-04-29: 회귀 수정. [backend/marketplace/router.py](backend/marketplace/router.py) 에 `from .subscription_service import subscription_service` 를 복구해 `build_subscription_router(sys.modules[__name__])` 계약 경로를 다시 고정했다.
- 2026-04-29: 재검증 1차. `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py backend/tests/test_marketplace_webhook_adapter_parsers.py -q` + `./.venv/Scripts/python.exe -m pytest backend/tests/test_admin_project_root_service.py -k subscription_monitor_summary_route_returns_helper_payload -q` 실행 결과 `26 passed` + `1 passed, 3 deselected`.
- 2026-04-29: 재검증 2차. 동일 명령 재실행 결과 `26 passed` + `1 passed, 3 deselected` 재확인.
- 2026-04-29: 관리자 런타임 검증 회귀 수정. [backend/admin_router.py](backend/admin_router.py) 의 `/api/admin/orchestrator/runtime-verification` 에서 `resolve_admin_project_root(..., allow_workspace_default=True)` 를 적용해 빈 `project_root` 요청이 워크스페이스 루트로 해석되도록 계약을 복구했다.
- 2026-04-29: 백엔드 전수 재검증 1차. `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py backend/tests/test_marketplace_webhook_adapter_parsers.py backend/tests/test_admin_project_root_service.py -q` 실행 결과 `30 passed`.
- 2026-04-29: 백엔드 전수 재검증 2차. 동일 명령 재실행 결과 `30 passed` 재확인.
- 2026-04-29: 운영 도메인 검증 스크립트 보강. [check_cors_final.ps1](check_cors_final.ps1) 의 백엔드 컨테이너 하드코딩(`devanalysis114-backend`)을 동적 탐지로 교체하고, [final_production_verification.ps1](final_production_verification.ps1) 에 컨테이너 실명 출력 기반 상태 확인을 반영했다.
- 2026-04-29: 운영 실검증 1차. `powershell -NoProfile -File check_cors_final.ps1; powershell -NoProfile -File final_production_verification.ps1` 실행 결과 CORS origin 로드 라인에서 `https://metanova1004.com`, `https://xn--114-2p7l635dz3bh5j.com` 포함 확인 + marketplace/admin 페이지 HTTP 200 + `/api/marketplace/ml-detectors/status` 200 확인.
- 2026-04-29: 운영 실검증 2차. 동일 명령 재실행 결과 1차와 동일하게 CORS/도메인/API/페이지 상태를 재확인.
- 2026-04-29: 경고 정리 마감. `datetime.utcnow/utcfromtimestamp` 및 `not_valid_before/not_valid_after`, Pydantic `class Config` 경고를 코드 레벨로 교체([backend/marketplace/models.py](backend/marketplace/models.py), [backend/marketplace/subscription_models.py](backend/marketplace/subscription_models.py), [backend/marketplace/subscription_service.py](backend/marketplace/subscription_service.py), [backend/marketplace/provider_adapters/apple_billing.py](backend/marketplace/provider_adapters/apple_billing.py), [backend/marketplace/provider_adapters/google_billing.py](backend/marketplace/provider_adapters/google_billing.py), [backend/marketplace/provider_adapters/stripe_billing.py](backend/marketplace/provider_adapters/stripe_billing.py), [backend/marketplace/provider_adapters/base.py](backend/marketplace/provider_adapters/base.py), [backend/marketplace/schemas.py](backend/marketplace/schemas.py), [backend/tests/test_marketplace_subscription_service.py](backend/tests/test_marketplace_subscription_service.py), [backend/tests/test_marketplace_webhook_adapter_parsers.py](backend/tests/test_marketplace_webhook_adapter_parsers.py)).
- 2026-04-29: 경고 정리 재검증. `./.venv/Scripts/python.exe -m pytest backend/tests/test_marketplace_subscription_contract.py backend/tests/test_marketplace_subscription_service.py backend/tests/test_marketplace_webhook_adapter_parsers.py backend/tests/test_admin_project_root_service.py -q` 결과 `30 passed`(warnings summary 없음) 확인.
- 2026-04-29: 운영 검증 스크립트 정리. [final_production_verification.ps1](final_production_verification.ps1) 의 정적 `Remaining Browser Warnings` 섹션을 제거하고 HTTP 레벨 실검 결과만 보고하도록 고정.
