# WorldLinco / 개발분석114 — 결함 보강 & 확장 플랜

> 작성: 2026-06-26 · 범위: 기능 정밀검증 후속 MEDIUM/LOW 보강 + 프로젝트 전반 보안·아키텍처 감사 + 확장 로드맵
> 본 문서는 "구석구석 완벽한 프로젝트 완성"을 위한 단일 실행 기준(SSOT)입니다.

---

## 0. 이번 세션에서 적용 완료한 보강 (코드 반영됨)

### 기능 결함 (MEDIUM/LOW) — 모두 적용 + 테스트 그린

| ID | 영역 | 결함 | 수정 | 파일 |
|----|------|------|------|------|
| m1 | 소리새 | 친구모드 TTS 실패가 정상 LLM 답변까지 500으로 폐기 | best-effort: 텍스트 반환 + 클라 온디바이스 TTS 폴백 | `backend/llm/voice_gateway.py` |
| m2 | 소리새 | `llm_connected` 가 '콜러블 구성 여부'만 보고(실제 실패와 무관) | 에이전트 결과 `metadata.llm_connected` 기반 도출 | `backend/orchestrator/autonomous/turn_controller.py` |
| m3 | 채팅 | 그룹 늦참여자 번역 폴백이 **죽은 코드**(그룹은 `translated_body=None` 강제 → 가드 항상 거짓) | "수신자 번역행 존재 + 비발신자"일 때 온더플라이 폴백(명시적요청 계약 유지) | `backend/marketplace/nadotongryoksa_chat_router.py` |
| m4 | 채팅 | hands-free 정지 desync + 수동→핸즈프리 전환 시 녹음 2중 경합 | 정지 SSOT(`stopHandsFree`), 자동듣기 OFF 시 실제 정지, 전환 시 `finalize()` await | `src/features/chat/useChatVoiceInput.ts` |
| m5 | 대면/통화 | 번역 실패 시 원문을 상대언어 음성으로 송출 / 에코가드 창 불일치(25s vs 20s) | 무번역 에코 차단 + `guardWindowMs` 주입으로 창 통일 | `App.tsx`, `src/features/voip-voice-relay/voiceRelayOrchestrator.ts` |
| m6 | VoIP | 수신 accept/reject `testID` 3중 중복(banner/rail/popup) | `-banner/-rail/-popup` 접미사로 유일화(`contains` 매칭 스크립트 호환) | `App.tsx` |
| m7 | 채팅 TTS | 2글자 코드(`ko`)·`toLowerCase()`로 로케일 깨짐 → 오발음/무음 | BCP-47 SSOT(`resolveVoipTtsLocale`) 경유 | `src/features/chat/screens/ChatRoomScreen.tsx` |

검증: 백엔드 `pytest` 채팅24 + 오케/대화/보이스 49 그린, 모바일 Jest **316/316** 그린.
빌드: **APK v1.0.190 build 242** 빌드·퍼블리시 완료.

### 보안 결함 — 안전·고가치 항목 즉시 적용

| ID | 심각도 | 결함 | 수정 | 파일:라인 |
|----|--------|------|------|-----------|
| s1 | **HIGH** | `end_voip_call` 소유자 미검증 → call_id만 알면 타인 통화 강제 종료(탈취/DoS) | 발신/착신 당사자만 종료 허용(accept 경로와 동일) | `nadotongryoksa_voip_router.py` `end_voip_call` |
| s2 | MED | `GET /calls/{id}` IDOR → 임의 통화의 전화번호·user_id·session_id 노출 | 통화 당사자만 조회 허용 | `nadotongryoksa_voip_router.py` `get_call_details` |
| s3 | MED | APK 다운로드 `current_user: Any = None`이 쿼리파라미터화 → `?current_user=1`로 401 우회 | 신원은 Bearer 토큰에서만 도출하는 옵션 의존성으로 교체 | `marketplace/router.py` `download_marketplace_apk` |
| s4 | MED | 문서화된 VoIP 쿼터가 live initiate에 미연결(푸시 스팸/방 고갈) | `require_voip_call_quota` 연결(20req/60s, 429+Retry-After) | `nadotongryoksa_voip_router.py` `initiate_voip_call` |

---

## 1. 남은 보안 권고 (다음 우선순위)

> 적용하면 규모 확장 전 반드시 닫아야 할 항목. 회귀 위험이 있어 별도 검토/테스트와 함께 진행 권장.

### HIGH — ✅ 마감 완료 (IP 키 레이트리밋 + 자원 캡)
> 모바일 클라가 이 경로들에 `Authorization` 헤더를 보내지 않으므로(앱 호환), 하드 인증 대신
> **클라이언트 IP 키 레이트리밋 + 자원 상한**으로 비용 증폭/DoS·브루트포스·폭탄을 1차 차단했다.
> (완전 인증 도입은 모바일 토큰 첨부 + APK 재배포가 동반되는 별도 작업으로 분리.)

1. **무인증 고비용 엔드포인트** — ✅
   - `GET /nearby` (`nadotongryoksa_lbs_router.py`): `require_lbs_search_quota`(IP 키, 기본 40/분) 적용. SerpApi/Overpass 팬아웃 비용 증폭 차단. `radius_m`은 기존 500km 상한 유지(전세계 검색 기능 보존).
   - `POST /api/mobile/image-translation` (`mobile/image_translation/router.py`): `require_public_image_quota`(IP 키, 기본 12/분) + 청크 단위 **8MB 업로드 상한**(전체 메모리 적재 방지, 초과 시 413) + **제네릭 500**(예외 본문 비노출, 상세는 서버 로그). RapidOCR 연산 DoS 차단.
2. **OTP 발송·로그인 레이트리밋** — ✅ (`auth_router.py`)
   - `POST /login`: `require_login_quota`(IP 키, 기본 10/분) — 크리덴셜 스터핑/bcrypt 무한호출 차단.
   - `POST /signup/request-code`, `POST /recovery/start`: `require_otp_send_quota`(IP 키, 기본 5/분) — SMS·메일 폭탄 차단.
   - 게이트 정의: `backend/security_gates.py` (`_LBS_SEARCH_QUOTA`/`_PUBLIC_IMAGE_QUOTA`/`_AUTH_LOGIN_QUOTA`/`_AUTH_OTP_QUOTA`, 모두 env로 조정·`0`이면 비활성). 회귀 테스트: `backend/tests/test_public_rate_limit_gates.py`(7건 그린).
   - 잔여(후속): per-계정(이메일/전화) 재발송 쿨다운 — 분산 IP 공격 대비 2차 방어선.

### MEDIUM
3. ~~`download_marketplace_feature_delivery_asset` (`router.py`) 무인증 → run_id만 알면 산출물 다운로드.~~ — ✅ **마감**: 이 플로우는 프론트가 익명 `<a href>` 로 다운로드(인증 헤더 첨부 불가)하고 run_id 는 `token_urlsafe(18)`(144bit) 비추측 토큰이라 열거 위험은 이미 낮음. 실질 취약점인 **임의 파일 노출**을 차단 — ① run_id 토큰 화이트리스트(`_FEATURE_RUN_ID_RE`)로 경로 트래버설/LFI 차단, ② 제공 파일을 산출물 루트(`gettempdir()/codeai-marketplace-*`)로 confine(`_assert_delivery_path_confined`, 메타데이터 path 변조 방어). 테스트: `test_feature_delivery_path_confinement.py`(12건). (완전 인증은 모바일/href 클라 변경 동반 별도 작업.)
4. ~~비만료 admin 토큰 + 세션검사 fail-open → 유출 토큰 영구화.~~ — ✅ **마감**: ① `_should_issue_non_expiring_admin_token` 가 prod/staging 에서는 `ALLOW_NON_EXPIRING_ADMIN_TOKENS` 가 켜져 있어도 **하드 오프**(만료 토큰 발급) + 경고 로그 — 유출 admin 토큰 영구화 방지. ② 세션검사 DB 조회 실패 시 `_lookup_active_session`→`(None, True)` 신호로 **admin/superuser 는 fail-closed(503)**, 일반 사용자는 가용성 우선 fail-open 유지(`auth.py`). 테스트: `test_auth_router_security.py`(prod 하드오프 + 조회실패 신호). *잔여(후속): 단기토큰+리프레시 토큰 도입, Redis 캐시 검증.*
5. ~~비밀번호 재설정/변경이 기존 세션 무효화 안 함.~~ — ✅ **마감**: `reset_password_via_recovery`·`change_user_password` 양쪽에서 비밀번호 갱신 후 **활성 sid 회전**(`set_active_session(uid, token_urlsafe(24))`) → 기존 발급 토큰(다른 sid)은 다음 요청부터 401. 응답 `must_relogin=True` 계약과 일치. 기존 단일세션 메커니즘 재사용(저위험). 회귀: `test_user_password_recovery.py`/`test_admin_recovery_otp.py` 그린.
6. ~~WS/SSE의 `?token=`이 nginx 액세스 로그에 평문 노출.~~ — ✅ **마감**: nginx `log_format scrubbed` 신설 — 요청라인을 `$request`(쿼리 포함) 대신 `$request_method $uri $server_protocol`(쿼리 제거)로 기록해 `?token=` 등 민감 파라미터가 액세스 로그에 남지 않게 함(`nginx.conf`, `nginx -t` 통과). **추가 마감(2차 배치)**: 백엔드 전 WS 엔드포인트가 `Sec-WebSocket-Protocol: bearer, <jwt>` 를 우선 수용(`auth.resolve_ws_token` SSOT, accept 시 subprotocol echo)하고 미전환 클라는 `?token=` 폴백 — VoIP presence/signaling, orchestrator `/ws`·진행 WS, customer-orchestrate WS 모두 적용(`ws_channel.connect(subprotocol=)`). 테스트: `test_ws_token_auth.py`(6건). *잔여(클라 동반): 모바일/웹 WS 클라를 subprotocol 전송으로 전환 + APK 재배포(백엔드는 무중단 준비 완료).*
7. ~~nginx 보안 헤더 부재 + 엣지 limit_req 부재.~~ — ✅ **마감**: ① `http` 레벨 공통 보안 헤더(`X-Content-Type-Options:nosniff`, `X-Frame-Options:SAMEORIGIN`, `Referrer-Policy:strict-origin-when-cross-origin`, `HSTS`) + add_header 상속이 끊기는 admin/marketplace 셸 블록에는 동일 헤더 별도 부여. ② `limit_req_zone`(20r/s) + `^~ /api/auth/` 전용 location 에 `limit_req burst=40 nodelay`(429)로 로그인/OTP 무차별 대입 엣지 차단(앱단 쿼터 보완). **추가 마감(2차 배치)**: ③ 일반 API 표면 거친 플러드 실드 `general_edge_limit`(50r/s, burst 100, 정적/_next·WS 제외) `/api/` 적용. ④ CSP 는 Next.js nonce 미들웨어(`frontend/frontend/middleware.ts`)로 도입 — `CSP_MODE` env 로 `off`(기본·무중단)/`report`/`enforce` 단계 전환, nonce+strict-dynamic, connect/img/script-src env 확장. 운영은 `report` 로 위반 수집 후 `enforce` 승급. `nginx -t` 통과. *잔여(클라 동반): `report` 리포트 검토 후 `enforce` 승급.*

### per-계정 2차 방어선 — ✅ 마감
- OTP/복구 코드 **대상(이메일/전화) 단위 재발송 쿨다운 + 시간당 상한** (`contact_verification.py` `_enforce_target_send_quota`, `ResendCooldownError`→429+Retry-After). 분산 IP 가 한 피해자에게 코드 폭탄 발송하는 것을 차단(IP 키 레이트리밋의 보완). env 조정: `OTP_RESEND_COOLDOWN_SEC`(기본 60), `OTP_MAX_SENDS_PER_TARGET`(기본 5)/`OTP_TARGET_SEND_WINDOW_SEC`(기본 3600). 테스트: `test_otp_resend_cooldown.py`(5건).

### 후속 트랙(2차 배치) — ✅ 적용 + 테스트 그린
- **[LOW] CORS 운영 강화** (`main.py` `_build_cors_origin_regex`/`_build_cors_origins`): `APP_ENV` 가 prod/staging 이면 dev 전용 출처(localhost/LAN 10·172·192/`.local`/`host.docker.internal`) 와 **임의 서브도메인 와일드카드**(`([a-z0-9-]+\.)?domain`)를 제거하고 등록 도메인 **정확 일치**만 허용 — `allow_credentials=True` 와 결합 시 크리덴셜 동반 교차출처 노출 표면 축소(dev 는 기존 편의 유지).
- **[LOW] 보안 경로 broad-except 관측성** (`auth.py` `verify_password`): bcrypt 는 불일치 시 예외 없이 False 를 반환하므로 except 도달 = 해시 손상/형식오류 신호. 조용히 삼키지 않고 경고 로그(인증은 안전 실패 유지).
- **[LOW] 다중 워커 인메모리 상태 가드레일** (`main.py` `_warn_if_multiworker_inmemory_state`): `WEB_CONCURRENCY`/`UVICORN_WORKERS`/`GUNICORN_WORKERS`>1 감지 시 기동 경고 — 레이트리밋/OTP세션/발급토큰/FCM 이 프로세스-로컬이라 워커 수만큼 헐거워짐을 명시(Redis 백킹 또는 단일워커+엣지 limit_req 권고).
- **[#4] 단일세션 검사 Redis 캐시** (`auth.py` `_session_cache_*`): 인증 요청마다 `user_active_sessions` 를 조회하던 것을 짧은 TTL(`SESSION_CACHE_TTL_SEC` 기본 30s) Redis 캐시로 단축. `UserActiveSession` 은 `set_active_session` 으로만 변경(로그아웃/삭제 경로 없음)되므로 거기서 **write-through** → 캐시가 항상 권위값과 일치(스테일 무효화 불필요), Redis 미연결 시 DB 폴백(fail-open). 테스트: `test_session_cache.py`(5건).
- **[ARCH] Alembic 베이스라인 도입** (`alembic.ini`·`alembic/env.py`·`alembic/versions/...0001_baseline`): URL/메타데이터를 앱 SSOT(`marketplace/database.py`)에서 가져와 전체 모델 등록 → autogenerate 기반 확보. 베이스라인 upgrade=메타데이터 `create_all`(멱등). 신규 DB `upgrade head`, **기존 운영 DB `stamp 0001_baseline`**(재생성 금지). 오프라인 SQL 생성 검증(전체 테이블 CREATE 확인). 부팅 `create_all`/`ALTER` 는 무중단 유지, 향후 변경은 Alembic 으로 규율.

### 잘 보호된 부분(검증됨)
SECRET_KEY prod 강제·약한키 하드페일, HS256+exp·bcrypt, passkey 서버검증, SQLAlchemy(주입 없음), 코드젠 validator는 `py_compile`만(실행 없음), APK 경로탐색 방어, SSRF 표면 제약(Literal+bounded float), 채팅 권한 일관.

---

## 2. 아키텍처 / 기술부채 (확장 전 4대 병목)

1. **두 개의 god-file** — `App.tsx` ~14.1k, `backend/llm/orchestrator.py` (분리 전 ~13.3k). 반복속도·테스트성 저하. → orchestrator는 router/stage엔진/템플릿뱅크로 분리, App.tsx 는 `src/features/*` 로 분리.
   - ✅ **1차 분리(템플릿 뱅크)**: 코드젠 템플릿 빌더 10개(7 빌더 + 3 resolver, ~4.9k줄)를 `backend/llm/orchestrator_templates.py` 로 byte-정확 이관(AST `end_lineno` 기반). 외부 의존은 `json`+typing 뿐이라 **순환 import 없음**. orchestrator.py 에서 동일 이름 재-import → 공개 API 무변경. `datetime.utcnow` 동결 템플릿 23개 **바이트 보존**(orchestrator.py 잔여 0). orchestrator.py **13.3k→8.4k(-37%)**. 검증: 베이스라인 27건 + 라우터마운트/런타임설정 5건 그린, 공개 심볼 import 전수 확인.
   - ✅ **2차 분리(검증기/semantic-gate)**: 산출물 정적 검증 + semantic-gate 함수 11개(~669줄)를 `backend/llm/orchestrator_validators.py` 로 byte-정확 이관. 외부 의존은 typing + `orchestrator_scaffold_generators._strip_generated_id_headers` 뿐(순환 없음). 재-import 로 공개 API 무변경. orchestrator.py **8.4k→7.7k**. 검증: 베이스라인 27건 + 라우터마운트 3건 그린, 공개 심볼 import 확인.
   - ✅ **3차 분리(실행-검증기/라이브 통합엔진)**: venv·pip·compileall·pytest·FastAPI 스탠드얼론 부팅+HTTP 프로브·도메인 통합 테스트 엔진·shipping zip 재현 검증 등 `_run_*` 10개(~780줄)를 `backend/llm/orchestrator_runtime_validation.py` 로 byte-정확 이관. AST 사전 의존성 분석으로 결합도 확인: 외부 의존은 **표준 라이브러리뿐**(`subprocess/httpx/zipfile/socket/...`) + 클러스터 전용 헬퍼 `_log_integration_validation_phase`·상수 `ORCH_VALIDATION_WORK_ROOT`(둘 다 클러스터 외 미사용 → 함께 이관, **순환 import 없음**). 재-import 로 공개 API 무변경. orchestrator.py **7.7k→7.0k(-47% 누적)**. 검증: 베이스라인 27건 + 보안게이트 3건 그린, `__module__`/상수 재노출 확인, lint clean.
   - ✅ **4차 분리(고객주문 프로파일 + 도메인계약/통합테스트/stage 빌더)**: `_build_customer_order_profile`(도메인 프로파일 추론 카탈로그) + 도메인계약/통합테스트플랜/개선루프/Refiner·Fixer stage/패키징감사 빌더 8개 + 헬퍼 `_unique_sequence`·`_has_mojibake_text` = 함수 10개(~559줄)를 `backend/llm/orchestrator_order_profile.py` 로 byte-정확 이관. AST 분석: 외부 의존은 **typing + `re`뿐** + 클러스터 전용 상수 `ORCH_REFINER_FIXER_STAGE`(클러스터 외 미사용 → AST 구간으로 byte-정확 함께 이관, **순환 import 없음**). 재-import 로 공개 API 무변경. orchestrator.py **7.0k→6.4k(-52% 누적)**. 검증: 베이스라인 27건 + 보안게이트 3건 그린, `__module__`/상수 재노출/`_unique_sequence` 동작 확인, lint clean.
   - ✅ **5차 분리(핵심 실행 루프 ②중간 스테이지)**: `_run_orchestration_core` 의 prepare↔finalize 사이 인라인 스테이지(b-brain 생성·manifest·semantic gate·packaging audit·통합/프레임워크/외부 검증·completion judge·seed/aux 아티팩트, ~240줄)를 `backend/orchestrator/customer/validation_stages_service.py` 의 `run_customer_validation_stages` 로 **byte-동일 이동**. 기존 customer 서비스(prepare/finalize/assemble)와 동일하게 **orchestrator 미-import + DI(키워드 43개: 함수16/상수14/입력13, 원본과 동일 이름)** → 본문 편집 0, 순환 없음. 반환 18키 번들. `_run_orchestration_core` 402→~80줄(prepare→stages→finalize→assemble 와이어링). orchestrator.py **6.4k→6.27k(-53% 누적)**. 검증: AST 자유이름 미해소 **0**(NameError 불가), baseline 30 + 고객 orchestrate 컨트랙트 10 그린, lint clean.
   - *잔여: App.tsx 분리(디바이스 테스트 동반 단독 세션 권장).*
2. ~~**마이그레이션 부재(Alembic 없음)**~~ — ✅ **베이스라인 도입**: Alembic 스캐폴드(`alembic.ini`/`env.py`/`0001_baseline`) + 앱 SSOT URL/메타데이터 연동. 기존 DB 는 `stamp`, 신규는 `upgrade`. *잔여: 부팅 `ALTER TABLE`(`database.py`) 점진 제거 → Alembic 단일화(다중 레플리카 전제).*
3. ~~**요청마다 단일세션 검사 2 DB 세션/2 쿼리, 캐시 없음**~~ — ✅ **마감**: Redis 짧은 TTL 캐시 + `set_active_session` write-through(`auth.py` `_session_cache_*`, `SESSION_CACHE_TTL_SEC` 기본 30s, fail-open). 테스트 `test_session_cache.py`.
4. **수익 플로우의 스텁/임시상태** — 예약은 정적 서울 8곳만(`create_booking`), live는 `booking_supported=False`; 결제 `MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT=true` 기본; FCM `device_registrations` 인프로세스 딕셔너리.

기타: 라우터 마운트 `try/except`가 전부 삼킴 → 라우터 하나 깨져도 `/health`는 ok(가시성 함정). 의존성 SSOT 분산(requirements 31개·package.json 11개, pyproject와 불일치, mobile React19/TS5.8 vs web React18/TS6.0). i18n 이중전략(백엔드 정적 24언어 dict vs 모바일 런타임 MT).

---

## 3. 확장 로드맵 (3 호라이즌, 현존 파일 기준)

### Horizon 1 — 퀵윈(주 단위, 현존 자산 디리스크)
- [x] 단일세션 검사 Redis 캐시화 (`auth.py` `_session_cache_*`) — ✅ 적용(write-through·fail-open, `test_session_cache.py`)
- [x] **백엔드 CI 게이트** 신설: `.github/workflows/backend-security-gate.yml` — Python 3.13 + `requirements.txt` 설치, `compileall`(backend/app/tests) + 보안·계약 스위트(R1~R8 게이트, IP 레이트리밋, signup/recovery OTP, image-translation, LBS) PR 게이트. 외부 서비스 없이 SQLite+목으로 결정적 실행, 문서화된 제외목록(`test_orchestrator_operational_evidence_targets.py`) 명시. (로컬 3.13 검증 93건 그린)
- [ ] import 깨진 `test_orchestrator_operational_evidence_targets.py` 수정/삭제 + 상시 실패 2건 정리(그린 베이스라인)
- [ ] 라우터 마운트 실패를 `/api/health`에 노출
- [ ] 의존성 SSOT 통일(pyproject→requirements 생성, numpy/boto3/requests 상한, googletrans/rapidocr 교체 검토)
- [ ] SerpApi 일일 예산 카운터(Redis)로 LBS 비용 가드 (`nadotongryoksa_lbs_router.py:315`)
- [x] **§1 HIGH 보안 3종 마감**(LBS/이미지번역 IP 레이트리밋+자원캡, OTP/로그인 레이트리밋)

### Horizon 2 — 중기(1~2분기, 프로덕션화)
- [~] Alembic 도입(베이스라인 ✅) + 부팅 `ALTER TABLE` 제거(다중 레플리카 전제, 잔여)
- [ ] **실 OTA 예약 연동**: `BookingProvider` 인터페이스(Booking/Expedia/Agoda/Amadeus) + 예약 테이블 + 웹훅 정산
- [ ] 결제 하드닝: 시뮬레이션 체크아웃 prod off, 웹훅 서명 강제, 멱등키
- [ ] 푸시 알림: device-token을 DB+Redis로 이전(재시작·레플리카 생존) → VoIP 수신 푸시 확장 기반
- [ ] `App.tsx`/`VoIPCallScreen.tsx` 분해 시작 + 컴포넌트 테스트
- [ ] 멀티레플리카 워커 토폴로지: API 컨테이너 `ENABLE_AD_ORDER_WORKER_BOOTSTRAP=false`, 전용 워커만

### Horizon 3 — 전략(스케일·신규 수익)
- [ ] 멀티리전: 스키마 부팅변경(#H2-1)·인프로세스 상태(#H2-4,6)·캐시 통계 제거 후 리전 샤딩, CORS/도메인 env화(`main.py:715-786`)
- [ ] 소리새 AI 제품화: 7 Flask 슬롯 + brain을 단일 게이트웨이 + 안정 API 계약 + per-tenant 쿼터(`security_gates.py` 재사용)로 통합 → 미터링 판매
- [ ] orchestrator 12.8k 리팩터(router/stage/template) — 11단계 파이프라인 반복속도 개선
- [ ] 관측성 티어: 구조적 JSON 로깅 + correlation-id, prod OTEL, Prometheus→TSDB, DB풀포화·큐깊이 SLO 알림

---

**Bottom line.** 기능 MEDIUM/LOW 7종 + 안전 보안 4종(HIGH 1 포함)은 적용 완료(테스트 그린, b242 배포). "완벽한 프로덕션"까지의 핵심은 집중되어 있다: ① god-file 2종, ② 실 마이그레이션, ③ 요청당 DB 세션검사, ④ 스텁 예약·시뮬 결제·임시 푸시 레지스트리. Horizon 1부터 닫으면 나머지가 풀린다.
