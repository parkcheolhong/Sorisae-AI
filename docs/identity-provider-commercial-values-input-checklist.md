# PASS / KMC / KCB 상용값 입력 체크리스트

## 목적

- 관리자 대시보드 **전역 .env 설정 패널** → **PASS / KMC / KCB 상용 운영 게이트**에서 입력할 **운영값(env)** 을 공급사별로 정리합니다.
- 계약·약관 기준은 `docs/identity-provider-commercial-terms-checklist.md`, 기술 payload 계약은 `docs/identity-provider-integration-contract.md`를 함께 참고하세요.

---

## 0. 입력 전 공통 준비

| # | 항목 | 확인 | 비고 |
|---|------|------|------|
| 0-1 | 운영 도메인 확정 | [ ] | 예: `metanova1004.com` → `.env`의 `ADMIN_DOMAIN`, `MARKETPLACE_API_DOMAIN` |
| 0-2 | HTTPS / nginx 라우팅 | [ ] | callback은 **HTTPS 공개 URL** 이어야 함 |
| 0-3 | 백엔드 API 기준 주소 | [ ] | `LOCAL_API_BASE_URL=http://127.0.0.1:8000` (로컬) / 운영은 gateway origin |
| 0-4 | `.env` 저장 경로 | [ ] | Docker: `/app/.env` (호스트 `./.env` 마운트) |
| 0-5 | 공급사 계약 완료 | [ ] | **운영 client id / secret / endpoint** 발급 |
| 0-6 | 공급사 콘솔 callback 등록 권한 | [ ] | 아래 callback URL을 **공급사 포털에 동일하게 등록** |

### 공급사에 등록할 callback URL (고정 형식)

| 공급사 | callback URL |
|--------|----------------|
| PASS | `https://{ADMIN_DOMAIN}/api/auth/identity/providers/pass/callback` |
| KMC | `https://{ADMIN_DOMAIN}/api/auth/identity/providers/kmc/callback` |
| KCB | `https://{ADMIN_DOMAIN}/api/auth/identity/providers/kcb/callback` |

`{ADMIN_DOMAIN}` 예: `metanova1004.com`

---

## 1. 활성 공급사 선택 (1개)

| env 키 | 입력값 | 확인 |
|--------|--------|------|
| `IDENTITY_PROVIDER` | `pass` **또는** `kmc` **또는** `kcb` | [ ] |

- 실제 본인확인 **시작·완료에 사용할 1개**만 선택합니다.
- 나머지 공급사 env도 미리 채워 두면 전환 시 `.env`만 바꿔 재기동 가능합니다.

---

## 2. PASS 상용값 입력

### 2-1. env 키 (관리자 패널 → 본인확인 공급사 운영값 섹션)

| env 키 | 공급사에서 받을 값 | 입력 | 패널 상태 |
|--------|-------------------|------|-----------|
| `PASS_IDENTITY_ENDPOINT` | PASS 본인확인 **시작 URL 전체** | [ ] | endpoint |
| `PASS_CLIENT_ID` | PASS 운영 **client id** | [ ] | request mapping |
| `PASS_CLIENT_SECRET` | PASS 운영 **secret** | [ ] | request mapping |
| `PASS_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/pass/callback` | [ ] | complete mapping |

### 2-2. 입력 시 주의

- [ ] URL에 `example`, `dummy`, `placeholder`, `test-secret` 등 **placeholder 문자열 금지** (백엔드가 상용 거부)
- [ ] `PASS_IDENTITY_ENDPOINT`는 **경로까지 포함한 전체 URL** (trailing slash 불일치 주의)
- [ ] `PASS_CLIENT_SECRET` 저장 후 패널에서 **마스킹**되는지 확인
- [ ] PASS 포털에 callback URL **문자 단위 동일** 등록

### 2-3. PASS 패널 게이트 (저장 후)

| 카드 항목 | 기대값 |
|-----------|--------|
| request mapping | **ready** (endpoint + client id + secret 모두 유효) |
| complete mapping | **ready** (callback URL 설정됨) |
| 환경 키 표시 | `PASS_IDENTITY_ENDPOINT, PASS_CLIENT_ID, PASS_CLIENT_SECRET, PASS_CALLBACK_URL` |

---

## 3. KMC 상용값 입력

### 3-1. env 키

| env 키 | 공급사에서 받을 값 | 입력 | 패널 상태 |
|--------|-------------------|------|-----------|
| `KMC_IDENTITY_ENDPOINT` | KMC 본인확인 **시작 URL 전체** | [ ] | endpoint |
| `KMC_CLIENT_ID` | KMC 운영 **client id** | [ ] | request mapping |
| `KMC_CLIENT_SECRET` | KMC 운영 **secret** | [ ] | request mapping |
| `KMC_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/kmc/callback` | [ ] | complete mapping |

### 3-2. 입력 시 주의

- [ ] KMC 계약서의 **서비스 코드 / CP 코드**가 client id와 매핑되는지 담당자 확인
- [ ] KMC 포털 callback 등록 (운영/검수 환경 구분)
- [ ] placeholder 값 사용 금지 (PASS와 동일 규칙)

### 3-3. KMC 패널 게이트

| 카드 항목 | 기대값 |
|-----------|--------|
| request mapping | **ready** |
| complete mapping | **ready** |
| 환경 키 | `KMC_IDENTITY_ENDPOINT, KMC_CLIENT_ID, KMC_CLIENT_SECRET, KMC_CALLBACK_URL` |

---

## 4. KCB 상용값 입력

### 4-1. env 키

| env 키 | 공급사에서 받을 값 | 입력 | 패널 상태 |
|--------|-------------------|------|-----------|
| `KCB_IDENTITY_ENDPOINT` | KCB 본인확인 **시작 URL 전체** | [ ] | endpoint |
| `KCB_CLIENT_ID` | KCB 운영 **client id** | [ ] | request mapping |
| `KCB_CLIENT_SECRET` | KCB 운영 **secret** | [ ] | request mapping |
| `KCB_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/kcb/callback` | [ ] | complete mapping |

### 4-2. 입력 시 주의

- [ ] KCB OkCert/본인확인 연동 가이드의 **운영 endpoint**와 일치하는지 확인
- [ ] callback URL 공급사 등록 + 방화벽/IP 허용 목록(필요 시)
- [ ] placeholder 값 사용 금지

### 4-3. KCB 패널 게이트

| 카드 항목 | 기대값 |
|-----------|--------|
| request mapping | **ready** |
| complete mapping | **ready** |
| 환경 키 | `KCB_IDENTITY_ENDPOINT, KCB_CLIENT_ID, KCB_CLIENT_SECRET, KCB_CALLBACK_URL` |

---

## 5. 관리자 대시보드 입력 순서 (Windows / Docker)

1. [ ] `/admin` 로그인
2. [ ] **전역 .env 설정 패널** → **설정 새로고침**
3. [ ] **연동 정밀 검사** 7/7 확인 (API · Swagger · 문서 등)
4. [ ] **본인확인 공급사 운영값** 섹션 **펼치기**
5. [ ] 위 표의 env 키 순서대로 입력
6. [ ] **`.env 저장`** 클릭
7. [ ] **PASS / KMC / KCB 상용 운영 게이트** 카드에서 request/complete **ready** 확인
8. [ ] (필요 시) backend Docker 재기동: `docker compose up -d backend`

### 빈 callback만 있을 때

- [ ] **빈 값 보강** 버튼 → `KMC_CALLBACK_URL`, `KCB_CALLBACK_URL` 등 권장값 자동 채움
- [ ] endpoint / client id / secret은 **공급사 발급값**으로 수동 입력 필수

---

## 6. 저장 후 기술 검증

| # | 검증 | 방법 | Pass |
|---|------|------|------|
| 6-1 | env 파일 반영 | 패널 `ENV 경로` 확인, 저장 후 새로고침 시 값 유지 | [ ] |
| 6-2 | placeholder 거부 | `service.pass.example`, `dummy-secret` 등 입력 시 request mapping **pending** 유지 | [ ] |
| 6-3 | Swagger callback 경로 | `GET/POST .../api/auth/identity/providers/{pass\|kmc\|kcb}/callback` 존재 | [ ] |
| 6-4 | 계약 문서 viewer | `/admin/docs-viewer?path=docs/identity-provider-integration-contract.md` 열림 | [ ] |
| 6-5 | 실제 시작 흐름 | 관리자 비밀번호 재설정/본인확인 UI에서 redirect 발생 | [ ] |
| 6-6 | complete payload | `ci`, `di`, `phone`, `name`, `birth`, `verified` 수신 (계약서 § complete) | [ ] |

---

## 7. 공급사별 계약 시 받아야 할 정보 (체크리스트)

입력 전 공급사 담당자에게 아래를 **문서/메일로 수령**했는지 확인하세요.

### PASS

- [ ] 운영 시작 URL (full URL)
- [ ] Client ID
- [ ] Client Secret (1회 표시 시 안전 저장)
- [ ] callback 등록 완료 스크린샷 또는 확인 메일
- [ ] 검수/운영 환경 구분 (staging URL이 있으면 별도 기록)

### KMC

- [ ] 운영 시작 URL
- [ ] Client ID (CP 코드 등)
- [ ] Client Secret
- [ ] callback 등록 완료 확인
- [ ] IP 허용 / VPN 요구사항

### KCB

- [ ] 운영 시작 URL
- [ ] Client ID
- [ ] Client Secret
- [ ] callback 등록 완료 확인
- [ ] OkCert/연동 매뉴얼 버전

---

## 8. 현재 프로젝트 기본값 (참고)

| 항목 | 현재 `.env` 기준 |
|------|------------------|
| `IDENTITY_PROVIDER` | `pass` |
| `ADMIN_DOMAIN` | `metanova1004.com` |
| `PASS_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/pass/callback` |
| `KMC_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/kmc/callback` |
| `KCB_CALLBACK_URL` | `https://metanova1004.com/api/auth/identity/providers/kcb/callback` |
| PASS endpoint (미상용) | `https://service.pass.example/identity/start` → **교체 필요** |
| PASS secret (미상용) | `dummy-secret` → **교체 필요** |

---

## 9. 상용 전환 완료 정의

아래 **모두** 체크되면 해당 공급사 상용값 입력 완료로 봅니다.

- [ ] §2~4 해당 공급사 env 4개 모두 실계약값
- [ ] 공급사 포털 callback 등록 완료
- [ ] 관리자 패널 카드 **request/complete 정상**
- [ ] `IDENTITY_PROVIDER`가 사용할 공급사로 설정
- [ ] `.env 저장` + (필요 시) backend 재기동
- [ ] §6 기술 검증 6-5, 6-6 실환경 1회 성공
- [ ] 약관 `/terms`, 개인정보 `/privacy` 공개 URL 운영 중

---

## 10. 관련 문서 (관리자 docs-viewer)

| 문서 | 경로 |
|------|------|
| **상용값 입력 (본 문서)** | `docs/identity-provider-commercial-values-input-checklist.md` |
| 기술 연동 계약 | `docs/identity-provider-integration-contract.md` |
| 계약·약관 기준 | `docs/identity-provider-commercial-terms-checklist.md` |
| 운영 전환 패키지 | `docs/identity-provider-operations-transition-package.md` |
| 사업자 유형 가이드 | `docs/identity-provider-business-type-guide.md` |

관리자 topnav: **PASS 문서** / **계약 기준** / 패널 내 **이용약관·개인정보** 링크에서 바로 열 수 있습니다.
