# 마켓플레이스 월구독 구현 준비 설계 v1

## 문서 목적

- 이 문서는 마켓플레이스 앱군을 모바일과 로컬PC에서 월구독으로 판매하기 위한 1단계 구현 준비 설계다.
- 현재 저장소의 기존 일회성 구매 구조를 보존하면서 월구독 구조를 병행 추가하는 방식을 고정한다.
- 본 문서는 DB 스키마 v1, 상태머신 모듈 경계, 웹훅/재처리 설계, 클라이언트 권한 게이트 명세를 포함한다.

## 현재 저장소 기준선

### 현재 이미 존재하는 구조

- `backend/marketplace/models.py` 에는 `Project`, `Purchase`, `DownloadToken` 중심의 일회성 구매 모델이 존재한다.
- `backend/marketplace/payment_service.py` 는 `Purchase` 레코드를 만들고 결제를 시뮬레이션한 뒤 `completed/refunded` 로 바꾸는 단건 결제 흐름이다.
- `frontend/frontend/lib/payment-service.ts` 도 단건 `purchase -> payment -> download token` 흐름에 맞춰져 있다.

### 현재 구조의 한계

- 월구독 개념이 없다.
- 결제 채널별 SKU/영수증/갱신 상태를 저장할 테이블이 없다.
- 모바일 스토어 영수증 검증과 PC 정기결제를 하나의 권한 상태로 합치는 계층이 없다.
- 기기 수 제한과 세션 회수 정책이 없다.

### v1 설계 원칙

- 기존 `Project/Purchase/DownloadToken` 은 유지한다.
- 월구독은 별도 테이블군으로 추가한다.
- 단건 구매와 월구독은 같은 마켓플레이스 안에서 공존시킨다.
- 권한 판정은 금액이 아니라 `plan_id` 와 `entitlement_key` 기준으로 수행한다.

## 도메인 모델 v1

### 1. 상품 계층

- `subscription_products`: 사용자가 무엇에 가입하는지 나타내는 상위 상품군
- `subscription_plans`: 권한 등급 정의
- `subscription_prices`: 채널/국가/통화별 실제 판매 가격
- `provider_sku_mappings`: Apple/Google/Stripe 와 내부 가격 ID 연결
- `subscription_product_projects`: 어떤 마켓플레이스 앱/프로젝트가 어떤 월구독 상품군에 포함되는지 매핑

### 2. 권한 계층

- `subscriptions`: 사용자의 현재 구독 계약 상태
- `subscription_entitlements`: 플랜별 권한 키 집합
- `device_sessions`: 동시 사용 기기 추적

### 3. 이벤트 계층

- `payment_events`: 결제사 원본 이벤트 저장
- `subscription_state_transitions`: 상태 전이 감사 로그
- `webhook_delivery_attempts`: 웹훅 처리 이력 및 재시도 추적

## DB 스키마 v1

아래는 현재 SQLAlchemy/관계형 구조에 맞춘 DDL 초안이다.

```sql
create table subscription_products (
    id integer primary key generated always as identity,
    code varchar(100) not null unique,
    name varchar(200) not null,
    description text,
    product_family varchar(100) not null,
    billing_type varchar(30) not null default 'subscription',
    is_active boolean not null default true,
    created_at timestamp not null default current_timestamp,
    updated_at timestamp not null default current_timestamp
);

create table subscription_plans (
    id integer primary key generated always as identity,
    product_id integer not null references subscription_products(id),
    code varchar(100) not null unique,
    name varchar(100) not null,
    billing_period varchar(20) not null default 'monthly',
    device_limit integer not null default 2,
    grace_days integer not null default 3,
    trial_days integer not null default 0,
    entitlement_version varchar(20) not null default 'v1',
    is_active boolean not null default true,
    created_at timestamp not null default current_timestamp,
    updated_at timestamp not null default current_timestamp
);

create table subscription_entitlements (
    id integer primary key generated always as identity,
    plan_id integer not null references subscription_plans(id),
    entitlement_key varchar(150) not null,
    entitlement_value varchar(150),
    created_at timestamp not null default current_timestamp,
    unique(plan_id, entitlement_key)
);

create table subscription_prices (
    id integer primary key generated always as identity,
    plan_id integer not null references subscription_plans(id),
    channel varchar(30) not null,
    provider varchar(30) not null,
    country_code varchar(2),
    currency varchar(10) not null,
    unit_amount numeric(12,2) not null,
    tax_mode varchar(20) not null default 'provider_managed',
    is_active boolean not null default true,
    effective_from timestamp,
    effective_to timestamp,
    created_at timestamp not null default current_timestamp,
    updated_at timestamp not null default current_timestamp
);

create table provider_sku_mappings (
    id integer primary key generated always as identity,
    price_id integer not null references subscription_prices(id),
    provider varchar(30) not null,
    external_product_id varchar(150) not null,
    external_price_id varchar(150),
    external_offer_id varchar(150),
    environment varchar(20) not null default 'production',
    is_active boolean not null default true,
    created_at timestamp not null default current_timestamp,
    unique(provider, external_product_id, coalesce(external_price_id, ''))
);

create table subscription_product_projects (
    id integer primary key generated always as identity,
    subscription_product_id integer not null references subscription_products(id),
    project_id integer not null references projects(id),
    created_at timestamp not null default current_timestamp,
    unique(subscription_product_id, project_id)
);

create table subscriptions (
    id integer primary key generated always as identity,
    user_id integer not null references users(id),
    product_id integer not null references subscription_products(id),
    plan_id integer not null references subscription_plans(id),
    price_id integer references subscription_prices(id),
    status varchar(30) not null,
    source varchar(30) not null,
    external_customer_id varchar(150),
    external_subscription_id varchar(150),
    original_transaction_id varchar(255),
    latest_transaction_id varchar(255),
    purchase_token_hash varchar(255),
    period_start timestamp,
    period_end timestamp,
    grace_until timestamp,
    trial_until timestamp,
    cancel_at_period_end boolean not null default false,
    canceled_at timestamp,
    refunded_at timestamp,
    suspended_at timestamp,
    last_verified_at timestamp,
    created_at timestamp not null default current_timestamp,
    updated_at timestamp not null default current_timestamp
);

create table payment_events (
    id integer primary key generated always as identity,
    provider varchar(30) not null,
    event_id varchar(255) not null,
    event_type varchar(100) not null,
    subscription_id integer references subscriptions(id),
    user_id integer references users(id),
    payload_json text not null,
    signature_valid boolean,
    idempotency_key varchar(255),
    event_created_at timestamp,
    received_at timestamp not null default current_timestamp,
    processed_at timestamp,
    processing_status varchar(30) not null default 'received',
    processing_error text,
    unique(provider, event_id)
);

create table subscription_state_transitions (
    id integer primary key generated always as identity,
    subscription_id integer not null references subscriptions(id),
    from_status varchar(30),
    to_status varchar(30) not null,
    reason_code varchar(50) not null,
    event_id integer references payment_events(id),
    actor_type varchar(30) not null default 'system',
    actor_id varchar(100),
    note text,
    created_at timestamp not null default current_timestamp
);

create table webhook_delivery_attempts (
    id integer primary key generated always as identity,
    provider varchar(30) not null,
    event_id varchar(255) not null,
    delivery_key varchar(255),
    http_status integer,
    attempt_number integer not null default 1,
    result varchar(30) not null,
    error_message text,
    created_at timestamp not null default current_timestamp
);

create table device_sessions (
    id integer primary key generated always as identity,
    user_id integer not null references users(id),
    subscription_id integer references subscriptions(id),
    device_id varchar(255) not null,
    device_type varchar(30) not null,
    platform varchar(30) not null,
    app_version varchar(50),
    os_version varchar(50),
    last_ip varchar(100),
    last_seen_at timestamp not null default current_timestamp,
    revoked_at timestamp,
    created_at timestamp not null default current_timestamp,
    unique(user_id, device_id)
);
```

## SQLAlchemy 적용 원칙

- 기존 `backend/marketplace/models.py` 에 월구독 모델을 추가하거나, 더 안전하게는 `backend/marketplace/subscription_models.py` 로 분리한다.
- 권장: `subscription_models.py` 분리 후 초기화 루틴에서 metadata 등록.
- 이유: 기존 단건 구매 모델의 변경 리스크를 줄이고, 월구독 도메인을 독립적으로 테스트하기 쉽다.

## 상태머신 단일 모듈 설계

### 모듈 경계

권장 파일 구조

- `backend/marketplace/subscription_state_machine.py`
- `backend/marketplace/subscription_service.py`
- `backend/marketplace/subscription_repository.py`
- `backend/marketplace/provider_adapters/apple_billing.py`
- `backend/marketplace/provider_adapters/google_billing.py`
- `backend/marketplace/provider_adapters/stripe_billing.py`

### 역할 분리

- `subscription_state_machine.py`
  - 입력: 현재 상태, 이벤트 타입, 이벤트 시각, 부가 데이터
  - 출력: 다음 상태, 부수효과 명세, 감사 사유 코드
  - 외부 API 호출 금지

- `subscription_service.py`
  - 상태머신 호출
  - DB 저장
  - 권한 계산
  - 기기 제한 적용

- `provider_adapters/*`
  - 영수증/토큰 검증
  - 웹훅 서명 검증
  - 제공자 이벤트를 내부 공통 이벤트로 변환

### 내부 공통 이벤트 타입

- `PURCHASE_VERIFIED`
- `RENEWAL_SUCCEEDED`
- `RENEWAL_FAILED`
- `GRACE_EXPIRED`
- `CANCEL_SCHEDULED`
- `CANCEL_REVOKED`
- `PERIOD_ENDED`
- `REFUND_APPLIED`
- `SUBSCRIPTION_SUSPENDED`
- `SUBSCRIPTION_RESTORED`

### 상태 전이 원칙

- 상태 전이는 오직 상태머신 모듈만 수행한다.
- API 핸들러, 웹훅 핸들러, 배치 잡이 직접 상태 문자열을 수정하지 않는다.
- 지연 도착 이벤트는 `event_created_at` 과 현재 `updated_at` 비교 후 무시 여부를 판정한다.
- 동일 `provider + event_id` 는 1회만 적용한다.

## 웹훅/중복처리/재처리 큐 설계

### 수신 흐름

1. 웹훅 수신
2. 서명 검증
3. `payment_events` 에 원본 이벤트 저장
4. `(provider, event_id)` 중복 여부 확인
5. 내부 공통 이벤트로 변환
6. 상태머신 실행
7. `subscription_state_transitions` 기록
8. 결과 응답

### 실패 처리 규칙

- 서명 실패: 401, 이벤트 저장 가능하나 `signature_valid=false`
- 일시 장애(DB/API): 5xx 반환, 재시도 허용
- 중복 이벤트: 200 + `ignored=true`
- 처리 중 예외: `payment_events.processing_status='failed'` 저장 후 재처리 대상 적재

### 재처리 큐 기준

- 초기 v1: DB 기반 재처리 테이블/플래그로 운영 가능
- 확장 v2: Redis queue 또는 Celery/RQ 전환

### 재처리 대상 조건

- `processing_status='failed'`
- `signature_valid=true`
- 운영자 재처리 승인 또는 자동 재시도 정책 만족

## 클라이언트 권한 게이트 명세

### 공통 원칙

- 모바일/PC 모두 권한의 진실원은 `GET /v1/me/subscription`
- 결제 성공 직후에도 UI는 반드시 서버 재조회 후 잠금 해제
- 금액/채널 정보로 권한을 열지 않는다

### 모바일 앱

- 앱 시작 시 구독 상태 조회
- 구매 후 `POST /v1/billing/mobile/verify`
- 검증 성공 후 다시 `GET /v1/me/subscription`
- 로컬 캐시는 최대 6시간까지만 허용
- 6시간 초과 시 온라인 검증 실패하면 유예 UI 표시

### 로컬PC 앱

- 로그인 후 즉시 구독 상태 조회
- 결제 버튼 클릭 시 외부 체크아웃 세션 생성
- 복귀 후 `GET /v1/me/subscription` 재조회
- 앱 실행 시 device 등록 또는 heartbeat 수행

### 기능 잠금 규칙

예시 entitlement key

- `marketplace.app_family.stock_ai.use`
- `marketplace.app_family.stock_ai.export_hd`
- `marketplace.app_family.voice_auto_apply.use`
- `marketplace.device_limit.override`

판정 방식

- 구독 상태가 `active` 또는 `grace_period` 인가
- 해당 entitlement key 가 plan 에 포함되는가
- 기기 제한을 초과하지 않았는가

## API v1와 저장소 구조 매핑

### 기존 구조 유지

- 기존 단건 구매 API는 유지
- 기존 다운로드 토큰 흐름 유지

### 신규 월구독 API 추가

- `GET /v1/me/subscription`
- `POST /v1/billing/checkout/sessions`
- `POST /v1/billing/mobile/verify`
- `POST /v1/me/subscription/cancel`
- `POST /v1/me/subscription/resume`
- `POST /v1/billing/webhooks/stripe`
- `POST /v1/billing/webhooks/apple`
- `POST /v1/billing/webhooks/google`
- `POST /v1/me/devices/register`
- `POST /v1/me/devices/revoke`

### 현재 저장소 적용 포인트

- 기존 `backend/marketplace/payment_service.py` 는 단건 결제 서비스로 유지
- 신규 `backend/marketplace/subscription_service.py` 를 별도 추가
- 프런트 기존 `frontend/frontend/lib/payment-service.ts` 는 단건 결제 전용으로 유지
- 신규 `frontend/frontend/lib/subscription-service.ts` 를 추가해 월구독 상태 조회/구매/검증 분리

## 제품별 차등 요금 처리 기준

제품별 요금이 달라도 문제없다. 오히려 아래와 같이 설계해야 한다.

- 같은 상품군이라도 채널별 가격 다름 허용
- 같은 플랜이라도 국가별 가격 다름 허용
- 프로모션 가격과 정가 공존 허용
- 권한은 `subscription_plans` 와 `subscription_entitlements` 로만 판정
- 실제 과금 금액은 `subscription_prices` 와 `provider_sku_mappings` 가 담당

예시

- `stock-ai-suite` 상품군
- `basic-monthly`, `pro-monthly` 플랜
- iOS KRW 가격, Android KRW 가격, PC USD/KRW 가격 각각 별도 저장
- 그러나 `pro-monthly` 권한 집합은 동일하게 유지

## 구현 순서 v1

### Step 1. 모델 추가

- `subscription_models.py` 추가
- migration 작성
- metadata 등록

### Step 2. 상태머신 추가

- 내부 공통 이벤트 enum
- 상태 전이 함수
- 감사 로그 기록 함수

### Step 3. 채널 어댑터 추가

- Stripe 체크아웃 세션
- Apple receipt 검증
- Google purchase token 검증

### Step 4. API 추가

- 구독 조회
- 모바일 검증
- 취소/재개
- 웹훅
- 기기 등록/해제

### Step 5. 프런트 게이트 추가

- 월구독 상태 조회 유틸
- 기능 잠금 컴포넌트
- 모바일/PC 결제 후 재조회 흐름 연결

## 차단 리스크

- 기존 `users` 테이블과 인증 계층이 여러 곳에서 재사용되므로 월구독 모델은 사용자 외래키만 공유하고 나머지 필드는 독립 유지해야 한다.
- 기존 `Purchase` 는 단건 결제 흐름과 다운로드 권한에 이미 사용 중이므로 월구독 상태를 억지로 합치면 회귀 위험이 크다.
- 모바일 스토어 정책 차이 때문에 웹 결제와 동일 UX를 기대하면 안 된다. UX는 달라도 서버 권한 상태는 같아야 한다.

## 완료 판정 기준

1단계 구현 준비 완료는 아래가 모두 충족될 때만 인정한다.

- DB 스키마 v1 문서화 완료
- 상태머신 모듈 경계 문서화 완료
- 웹훅/재처리 설계 문서화 완료
- 클라이언트 권한 게이트 문서화 완료
- 체크리스트 파일 동기화 완료
