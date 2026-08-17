# 본인확인 공급사 기술 연동 계약서

## 목적

- `PASS`, `KMC`, `KCB` 본인확인 공급사에 대한 요청/응답/callback 기술 계약을 고정합니다.
- 관리자 대시보드 운영값과 백엔드 provider 코드가 동일 계약을 따르도록 기준 문서로 사용합니다.

---

## 공통 구조

### 시작 요청 필수 운영값

| 항목 | 설명 |
|---|---|
| endpoint | 공급사 본인확인 시작 URL |
| client_id | 계약 후 발급된 운영 client id |
| client_secret | 계약 후 발급된 운영 secret |
| callback_url | 공급사 결과를 다시 받을 백엔드 callback URL |

### 시작 요청 공통 payload

| 필드 | 타입 | 설명 |
|---|---|---|
| client_id | string | 공급사 운영 client id |
| client_secret | string | 공급사 운영 secret |
| callback_url | string | 공급사 callback URL |
| session_token | string | 내부 추적 세션 토큰 |
| scope | string | 현재 `admin` |
| purpose | string | 현재 `password_reset` |
| user_hint | string | 관리자 이메일 |

### complete payload 공통 필수 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| provider | string | `pass` / `kmc` / `kcb` |
| verified | boolean | 공급사 인증 성공 여부 |
| ci | string | CI 원문 |
| di | string | DI 원문 |
| phone | string | 본인확인 휴대전화 |
| name | string | 실명 |
| birth | string | 생년월일 `yyyyMMdd` |

---

## PASS

### 운영값 키

| 키 | 설명 |
|---|---|
| PASS_IDENTITY_ENDPOINT | PASS 상용 시작 URL |
| PASS_CLIENT_ID | PASS 운영 client id |
| PASS_CLIENT_SECRET | PASS 운영 secret |
| PASS_CALLBACK_URL | PASS callback URL |

### 요청 명세

`query` 또는 공급사 요구 방식(form/body)에 아래 필드를 동일 의미로 전달합니다.

| 필드 | 설명 |
|---|---|
| client_id | PASS 계약 client id |
| client_secret | PASS 계약 secret |
| callback_url | PASS 결과 callback |
| session_token | 내부 세션 연계값 |
| scope | `admin` |
| purpose | `password_reset` |
| user_hint | 관리자 이메일 |

### callback 명세

| 필드 | 설명 |
|---|---|
| provider | `pass` |
| verified | 인증 성공 여부 |
| ci | CI |
| di | DI |
| phone | 휴대전화 |
| name | 이름 |
| birth | 생년월일 |

---

## KMC

### 운영값 키

| 키 | 설명 |
|---|---|
| KMC_IDENTITY_ENDPOINT | KMC 상용 시작 URL |
| KMC_CLIENT_ID | KMC 운영 client id |
| KMC_CLIENT_SECRET | KMC 운영 secret |
| KMC_CALLBACK_URL | KMC callback URL |

### 요청 명세

PASS와 동일 의미 필드를 유지하되 공급사 요구 포맷에 맞게 래핑합니다.

### callback 명세

| 필드 | 설명 |
|---|---|
| provider | `kmc` |
| verified | 인증 성공 여부 |
| ci | CI |
| di | DI |
| phone | 휴대전화 |
| name | 이름 |
| birth | 생년월일 |

---

## KCB

### 운영값 키

| 키 | 설명 |
|---|---|
| KCB_IDENTITY_ENDPOINT | KCB 상용 시작 URL |
| KCB_CLIENT_ID | KCB 운영 client id |
| KCB_CLIENT_SECRET | KCB 운영 secret |
| KCB_CALLBACK_URL | KCB callback URL |

### 요청 명세

PASS/KMC와 동일 의미 필드를 유지하되 KCB 요구 포맷에 맞게 전달합니다.

### callback 명세

| 필드 | 설명 |
|---|---|
| provider | `kcb` |
| verified | 인증 성공 여부 |
| ci | CI |
| di | DI |
| phone | 휴대전화 |
| name | 이름 |
| birth | 생년월일 |

---

## 관리자 대시보드 연계

- 경로: `/admin/llm`
- 기능:
  - 운영값 직접 입력
  - 기본값 가이드 문구 표시
  - provider별 request/complete 준비 여부 카드 표시
  - 저장 후 즉시 상태 재검증

---

## 사업자 유형별 계약 가능성

### 개인사업자

- 계약 가능성이 있음
- 보통 요구 서류:
  - 사업자등록증
  - 서비스 URL
  - 개인정보처리방침
  - 이용약관
  - 정산 정보

### 법인사업자

- 가장 일반적인 계약 주체
- 보통 요구 항목:
  - 법인 사업자등록증
  - 담당자/보안 담당 정보
  - 서비스 설명서
  - 정산/세금계산서 정보

### 자연인 개인

- 상용 계약이 어려운 경우가 많음
- 테스트/개발은 가능하나 운영 전환은 제한될 수 있음

---

## 관련 문서

- **상용값(env) 입력 체크리스트**: `docs/identity-provider-commercial-values-input-checklist.md`
- 상용화 계약·약관 기준: `docs/identity-provider-commercial-terms-checklist.md`
- 운영 전환 패키지: `docs/identity-provider-operations-transition-package.md`
- 사업자 유형 가이드: `docs/identity-provider-business-type-guide.md`
