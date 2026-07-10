# WorldLinco — 기능별 완전 분리 마스터 기술서 (모바일 앱)

> **목적:** 모바일 앱 `apps/mobile-nadotongryoksa/App.tsx`(≈13,610줄 모놀리스)에 한 몸으로 얽혀 있는 **5개 기능**을, 어제까지 동작하던 기능(육성 통화·한일 통역 통화)을 깨지 않는 **안전한 점진 단계**로 **완전 분리**하기 위한 SSOT.
> **상위 문서:** [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md) · [`FILE_MAP.md`](FILE_MAP.md) · [`SERVICE_SEPARATION_DESIGN.md`](SERVICE_SEPARATION_DESIGN.md)
> **연동 문서:** [`SORISAE_TRAVEL_PARTNER_API_MASTER_TECH_SPEC.md`](SORISAE_TRAVEL_PARTNER_API_MASTER_TECH_SPEC.md)
> **연계 체크리스트:** [`../checklists/feature-separation-checklist.md`](../checklists/feature-separation-checklist.md)
> **원칙(고정):** V2 Strangler Fig — `POST /api/llm/voice-translate` · `voip-voice-relay/*` **hot path 계약 동결**. 분리는 클라이언트 상위 경계(소유권·라우팅·모듈)만 추가한다.

---

## 0. 5개 기능 정의 (사장님 확정 경계)

| # | 기능 모듈 | 범위 |
|---|-----------|------|
| 1 | **대면 통역** | 한 기기·한 마이크에서 두 사람이 번갈아 말하는 양방향 자동 통역 |
| 2 | **소리새AI + OCR** | 관광 특화 대화형 AI(친구챗) + 이미지/카메라(현재 OCR) 인식 |
| 3 | **VOIP + 채팅** | WebRTC 통역 통화 + 텍스트 채팅 (이미 `src/features`·`src/screens` 분리됨) |
| 4 | **일반전화 + 예약** | PSTN 다이얼/통역 + 여행 예약·결제 |
| 5 | **노래 번역** | 음원/마이크 가사 통역, 보이스 클론, 자막 export |

> **불변 규칙(사장님 지시):** 사용자는 한 화면에서 **한 번에 한 기능만** 사용한다. 따라서 **한 시점에 마이크·스피커(TTS) 소유자는 단 하나**여야 하며, 두 기능이 동시에 청취/발화해서는 안 된다.

---

## 1. 현재 결합 구조 (근본 원인 — 실측 확인)

`App.tsx` 단일 컴포넌트가 모든 기능을 `activeRailSection` 하나로 조건부 렌더링한다(내비게이션 라이브러리 없음).

```text
            ┌──────────────────────────────────────────────┐
            │  startVoiceInput / stopVoiceInput (≈8147–9050)│  ← 단일 마이크 캡처
            │  라이브 ref 분기:                              │
            │   sorisaeWindowOpenRef / songModeEnabled /     │
            │   voiceInputTargetRef('main'|'inter_call')     │
            └──────────────────────────────────────────────┘
   대면통역        소리새AI        일반전화(inter)      노래
      │              │                │               │
      └─ 공유: faceSpeakingRef(반이중) · faceVoicePlaybackSoundRef(TTS) ·
               inputText/resultText/engine(출력 UI) · scheduleFaceConversationRestart(재시작 루프)
```

**핵심 결함:**
- 대면통역과 소리새AI를 구분하는 유일한 기준이 **처리 시점에 비동기로 읽는 boolean ref**(`sorisaeWindowOpenRef.current`, `App.tsx:8587`)다.
- 세그먼트가 캡처된 뒤 처리되기 전에 창이 열리거나 닫히면(`App.tsx:9145`/`9154`) 발화가 **반대 경로로 라우팅**되어, 소리새 발화가 대면통역으로 통역·발성된다(레이스).
- 두 기능이 **같은 출력 상태**(`setResultText`/`setInputText`/`setEngine`)에 쓰므로, 라우팅이 맞아도 소리새 답변이 대면통역 결과창에 표시된다(시각적 누수).
- 반이중 플래그 `faceSpeakingRef`가 **전역 1개**라, 한 기능이 발성 중이면 다른 기능 캡처도 함께 막힌다.

---

## 2. 목표 아키텍처 — 단일-활성 기능 + 공용 커널

```text
┌──────────────────────────────────────────────────────────────┐
│  FeatureShell (단일-활성 라우터)                                │
│   activeFeature: 'face'|'sorisae'|'voip-chat'|'phone-book'|'song'│
│   기능 전환 시 이전 기능 quiesce(마이크/TTS/타이머/소켓 정리)      │
└──────────────────────────────────────────────────────────────┘
        │            │            │            │           │
        ▼            ▼            ▼            ▼           ▼
   [대면통역]   [소리새+OCR]  [VOIP+채팅]  [일반전화+예약]  [노래]
        │            │            │            │           │
        └──── acquire/release ────┴──── acquire/release ───┘
                          │
          ┌───────────────┴────────────────────────────┐
          │            공용 커널 (소유권 단일화)          │
          │  VoiceCaptureService  : 마이크 단일 소유 lease │
          │  AudioPlaybackService : 스피커/TTS 단일 소유   │
          │  Auth/Language/API_BASE Context               │
          │  worldlincoPushHandler (전역)                 │
          │  FeatureLog (기능별 태그 스트림)               │
          └───────────────────────────────────────────────┘
```

### 2-1. 단일-활성 계약 (불변)
1. `VoiceCaptureService.acquire(featureId)` 는 **한 시점에 한 기능**만 보유한다. 다른 기능이 `acquire` 하면 직전 소유자는 **자동 `release`**(녹음 중지, 재시작 타이머 해제, 반이중 플래그 리셋).
2. **라우팅 결정은 세그먼트 시작 시점에 스냅샷**으로 확정한다(어느 엔드포인트·어느 출력 sink). 처리 시점에 라이브 ref를 다시 읽지 않는다 → 레이스 제거.
3. 각 기능은 **자기 전용 출력 상태 + 전용 TTS sound ref + 전용 speakingRef** 를 가진다. 기능 간 공유 금지.
4. `AudioPlaybackService` 도 동일 — 한 시점에 한 기능만 TTS 재생을 소유. 새 소유자 acquire 시 직전 재생 stop.

### 2-2. 공용으로 유지할 것 (복제 금지)
- 백엔드 Voice Pipeline hot path(`voice-translate`, `voip-voice-relay/*`) — 계약 불변(채널 프로파일은 [`SERVICE_SEPARATION_DESIGN.md`](SERVICE_SEPARATION_DESIGN.md) §6 참조).
- `worldlincoPushHandler`(FCM), `API_BASE`, Auth/Language Context, 튜닝 SSOT [`../../knowledge/worldlinco_tuning_config.json`](../../knowledge/worldlinco_tuning_config.json).

---

## 3. 기능별 소유 자원 명세 (분리 후)

| 기능 | 캡처 타깃(featureId) | 출력 상태 | TTS sound ref | speakingRef | 라우팅 엔드포인트 |
|------|----------------------|-----------|---------------|-------------|-------------------|
| 대면통역 | `face` | `faceInputText`/`faceResultText` | `faceTtsSoundRef` | `faceSpeakingRef` | `/api/llm/face/voice-translate` (mode=bilingual) |
| 소리새AI | `sorisae` | `sorisaeInputText`/`sorisaeResultText`(+QA log) | `sorisaeTtsSoundRef` | `sorisaeSpeakingRef` | `/api/llm/voice/friend-chat` |
| VOIP | `voip` | VoIPCallScreen 내부 | VoIPCallScreen 내부 | relay turn controller | `voip-voice-relay/*` |
| 일반전화 | `inter_call` | `interCallLog` | (PSTN 경로) | inter-call gate | `/api/llm/voice/orchestrate` 등 |
| 노래 | `song` | `songSubtitles` | (재생 분리) | n/a | `/api/llm/voice/orchestrate` |

> Phase 1에서는 위 표 중 **대면통역·소리새**의 분리만 우선 적용한다(현재 통증). 나머지는 Phase 2~5에서 커널 추출과 함께 정식 분리.

---

## 4. 단계별 실행 (각 단계 = 빌드·설치·검증 후 다음)

### Phase 0 — 설계 문서 (본 문서 + 체크리스트)
- 본 마스터 기술서 + [`../checklists/feature-separation-checklist.md`](../checklists/feature-separation-checklist.md).

### Phase 1 — 소리새↔대면통역 누수 즉시 차단 (최우선)
- 소리새 전용 캡처 타깃/출력 상태/TTS ref/`sorisaeSpeakingRef` 도입.
- 라우팅을 **세그먼트 시작 시점 스냅샷**으로 확정(`isFaceGptMode` 라이브 ref 분기 제거).
- 소리새 창 open 시 `setAutoVoiceModeEnabled(false)`로 대면 캡처를 확실히 중지(현재 `App.tsx:9153` 효과는 stop만 하고 플래그 미해제).
- 대상: `App.tsx` 8584–8780, 9112–9162, 3170–3210.

### Phase 2 — 음성엔진 중재 커널화
- `src/services/voiceCaptureService.ts`(신규): `acquire(featureId)/release()`, 세그먼트→소유 기능 핸들러 디스패치. 라이브 ref 다중화 제거.

### Phase 3 — `useCallModeController` 분리
- `useVoipState` / `useInterCallState` 로 분할 → VOIP+채팅과 일반전화+예약 독립.

### Phase 4 — 단일-활성 FeatureShell
- 비활성 기능 정지(quiesce): 마이크/TTS/타이머/소켓 정리. 동시 마운트·동시 청취 제거.

### Phase 5 — 인라인 기능 모듈 추출
- `src/features/face-interpretation/`, `src/features/sorisae/`(+OCR), `src/features/song/`, `src/features/travel-booking/`.

### Phase 6 — 터미널/로그 분리
- 기능별 로그 태그 스트림([`../../apps/mobile-nadotongryoksa/src/features/correlation/correlationId.ts`](../../apps/mobile-nadotongryoksa/src/features/correlation/correlationId.ts) `FEATURE_IDS`) + logcat/백엔드 로그 분리 스크립트 + 프로세스 분리 옵션.

---

## 5. 안전장치 / 회귀 방지

- 각 Phase는 독립 배포 가능하게 쪼갠다. Phase 1 단독으로도 소리새 누수 해소.
- 매 Phase 후 회귀 검증(체크리스트):
  - (a) 육성(동일언어) 통화, (b) 한↔일 통역 통화, (c) 소리새 대화가 대면통역에 안 샘, (d) 음량.
- 튜닝값은 코드가 아니라 [`../../knowledge/worldlinco_tuning_config.json`](../../knowledge/worldlinco_tuning_config.json) 유지.

---

## 6. 미해결 확인 항목

- **"이미지 카메라 인식":** 현재 코드는 실시간 카메라 캡처 없음 — `DocumentPicker` 기반 OCR(`handlePickImageOcr`)만 존재. 라이브 카메라 캡처 신규 추가 여부는 분리 작업 후 별도 기능 확장으로 처리 권장(사장님 확인 필요).

---

## 7. Phase 5.6 — 순수 모듈/유틸 분리 진행 기록 (2026-06-24)

> **방식(안전 원칙):** Phase 5의 대규모 JSX/상태 추출은 디바이스 검증을 동반하므로, 그 전에 **순수(부수효과 없는) 도메인/유틸 로직**을 먼저 모듈로 분리한다. 매 단계 = 추출 → 회귀 단위테스트 → JS 번들 게이트(`expo export:embed`) → 린트 0. App.tsx의 타입/JSX/핸들러 사용처는 import 배선으로만 해소한다(동작 불변).

| 단계 | 신규 모듈 | 분리 심볼 | 회귀테스트 |
|------|-----------|-----------|-----------|
| **5.6a** | (정리) `src/features/app-update/appUpdate.ts` 로 단일화 | App.tsx 죽은 중복 버전 헬퍼(`parseVersionTriplet`/`parseBuildNumber`/`compareSemanticVersions`/문자열 `isRemoteApkNewer`/`resolveLatestApkMetadataUrl` + 고아 상수 `LATEST_APK_METADATA_PATH`) 제거 | — |
| **5.6b** | `src/features/monetization/monetization.ts` | `MonetizationPlanKey`/`MonetizationPlanConfig`/`MONETIZATION_PLAN_CONFIG`/`PREMIUM_PURCHASE_STATUSES`/`isPurchaseSettled`/`resolvePlanKeyFromPurchase`/`collectOwnedPlanKeys` | +9 |
| **5.6c** | `src/features/profile/profileFormatters.ts` | `resolveCountryFlag`/`resolveLocaleCountryCode`/`resolveLanguageLabel` + 성별 라벨 `formatVoipGenderLabel`/`formatDiscoveryGenderLabel`/`resolveDiscoveryGenderFromProfile` + 타입 `VoipGenderOption` | +8 |
| **5.6d** | `src/features/call-mode/callModeHelpers.ts` | `TERMINAL_VOIP_STATUSES`/`normalizeCallModeCandidate`/`resolveCallModeFromPayload`/`formatUnifiedCallModeText`/`formatUnifiedTranslationStatus`/`isTerminalVoipStatus` + 타입 `TranslationStatusRoute`/`TranslationStatusPhase` | +10 |
| **5.6e** | `src/features/country/{countryLanguage,countryCatalog,regionHints}.ts` | (영향 정밀 매핑 후 의존순 B→A→C) B: `COUNTRY_LANG_MAP`/`resolveLangFromCountry` · A: `SIGNUP_COUNTRY_OPTIONS`/`SignupCountryCode`/`SIGNUP_COUNTRY_OPTION_CODES`/`COUNTRY_NAME_MAP`/`isSupportedSignupCountryCode`/`normalizeSignupCountryCode`/`resolveSignupCountryFromLang`/`resolveCountryName` · C: `GPS_REGION_COORDINATE_FALLBACKS`/`DIALECT_REGION_HINT_KEYWORDS`/`resolveGpsDialectRegionHint`/`resolveGpsCoordinateFallback`/`resolveRegionHintForSourceLanguage` | +17 (4/7/6) |
| **5.6f** | `src/features/shared/textFormat.ts` | `formatStatusText`/`extractApiErrorMessage`/`summarizeAuthToken` | +9 |
| **5.6g** | `src/features/voip/voipSignaling.ts` | `buildVoiceId`/`buildVoipTopic`/`buildVoipWebSocketUrl`/`getDefaultVoipTurnServers`/`normalizeTurnServers` | +7 |

**누적:** 신규 회귀 단위테스트 **+60**(소스 jest 197 통과; `dist/*` 2건은 기존 Babel 변환 이슈로 무관). App.tsx ≈13,610 → ≈12,800줄로 축소. 의존 그래프상 country 클러스터는 `resolveLangFromCountry`(B)를 토대로 A·C가 의존 → **B 선분리로 순환 import 차단**.

**App.tsx 의도적 잔류:** `SignupSelectionModal`(국가 무관 모달 상태), `buildInstantDemoCredentials`/`parseIncomingVoipDeepLink`(차기 단계 후보).

### 7-2. Phase 5.7 — 섹션 레일 단일 레지스트리(SSOT) + 고유 ID 자동 넘버링/자동 연결 (2026-06-24)

> **요구:** "기능 섹션별 고유ID 넘버링 오토 매핑 + 전체 시스템 레일 하나까지도 오토 연결." 기존에 **5곳에 흩어져** 있던 레일 정의를 한 곳으로 모아 나머지를 전부 파생한다.

| 신규 모듈 | 통합/파생 심볼 | 회귀테스트 |
|-----------|----------------|-----------|
| `src/features/navigation/sectionRegistry.ts` | **SSOT** `SECTION_RAIL_SOURCE`(편집 지점 1곳) → 파생: `SectionRailKey` 유니온 · `SECTION_RAIL_DEFS`(자동 `numericId`) · `SECTION_RAIL_ITEMS` · `buildSectionRailSelector` · `parseSectionRailKey`(key+alias 자동 색인) · 신규 `sectionNumericId`/`sectionByNumericId`/`sectionDefByKey`/`featureIdForSection` | +10 |

- **자동 넘버링:** 정의 순서 = 고유 `numericId`(1부터). chat=1·voip=2·song-mode=3·travel-booking=4. 항목 추가/재배치 시 자동 재매핑, 전역 고유 보장.
- **자동 연결:** 레일 1개 추가 = `SECTION_RAIL_SOURCE` 항목 1개 추가만으로 타입·렌더 아이템·셀렉터·딥링크 파서·correlation `featureId`(chat→`chat.translate`, voip→`voip.voice_relay`, song-mode→`song.translate`, travel-booking→`orchestrate.voice`)가 전부 자동 연결(수기 중복 0).
- App.tsx 측 `SectionRailKey`/`SECTION_RAIL_ITEMS`/`buildSectionRailSelector`/`parseSectionRailKey` 로컬 정의 제거 → import 배선으로 해소(동작 불변, 셀렉터/별칭/라벨/아이콘 동일). 번들 게이트(`expo export:embed`, 691 modules) OK, 린트 0.

### 7-3. Phase 5.8 — 소리새 AI: 관광특화 → 진화형 멀티도메인 동반자 친구 (2026-06-24)

> **요구:** "소리새AI를 진화형 AI로 확장 — 관광 특화 외 멀티 AI, 성격·습관·모든 것을 인지하고 함께하는 친구." 기존엔 친구 페르소나가 **관광 가이드 정체성에 강결합**돼 있고 **세션을 넘는 기억이 없었다**(매 대화 백지).

**설계 원칙(안전·프라이버시 우선):**
- **프라이버시 SSOT = 온디바이스.** 성격·습관·관심·기억할 사실은 단말(AsyncStorage)에만 저장. 서버에는 요청 시 **압축 페르소나 브리프 문자열만** 시스템 컨텍스트로 주입하고 **저장하지 않음**(PII 서버 영속화 0).
- **무회귀·additive.** 기존 친구챗 경로/관광 A/B 파일럿을 깨지 않도록 페르소나 프롬프트는 관광 전문성을 유지한 채 멀티도메인 framing 만 **추가**. `persona_brief` 는 옵션 필드(없으면 기존 동작 그대로). 턴 관측은 **쓰기 전용**(응답에 영향 0).

| 영역 | 신규/변경 | 내용 | 테스트 |
|------|-----------|------|-------|
| 클라 도메인 | `src/features/sorisae/companionDomains.ts` | 멀티도메인 SSOT 레지스트리(일상친구/여행/지식·하우투/생활비서/감정지지) + 키워드 인텐트 분류기. sectionRegistry 와 동일 **자동 넘버링(numericId)·자동 연결**. 각 도메인 `personaHint` 파생 | +13 |
| 클라 기억 | `src/features/sorisae/companionMemory.ts` | 진화형 페르소나 순수 모델: `observeTurn`(말투/관심/도메인습관/자기개방 사실 누적, immutable) · `buildPersonaBrief`(압축 영문 1문단, 최소 턴 게이트) · `resolveTone`/`topInterests`/`topDomains` | +9 |
| 클라 영속 | `src/features/sorisae/companionPersonaStore.ts` | 온디바이스 영속(AsyncStorage) 래퍼 `load/save/recordTurn/resetPersona` + `revivePersona`(손상/구버전 방어) | (revive 포함) |
| 백엔드 | `backend/llm/voice_gateway.py` | `_friend_system_prompt` 멀티도메인 동반자 framing **추가**(관광 유지) · `_build_friend_messages`(테스트 가능 추출) + `persona_brief` 시스템 주입(상한 `PERSONA_BRIEF_MAX_LEN`) · `FriendChatRequest.persona_brief` 옵션 필드 | +5(pytest) |
| 라이브 배선 | `App.tsx` | 마운트 시 페르소나 로드 → 친구챗 페이로드에 `persona_brief` 주입(빈 값 시 생략) → 응답 성공 후 `recordTurn`(쓰기 전용) 으로 진화 | — |

- **자동 연결:** 도메인 1개 추가 = `COMPANION_DOMAIN_SOURCE` 항목 1개로 타입·numericId·분류기·페르소나 힌트 자동 연결(수기 중복 0).
- **진화 흐름:** 매 친구 대화 턴 → `observeTurn`(온디바이스 누적) → 다음 요청 시 `buildPersonaBrief` 주입 → 서버가 "오래된 친구처럼" 맥락 반영. 누적 턴 `< PERSONA_BRIEF_MIN_TURNS(3)` 이면 브리프 미주입(초반 노이즈 방지).
- 게이트: 신규 jess +22(도메인13/기억9) + sorisaeEcho 회귀 동반 · pytest +5 · 번들(`expo export:embed`, 854 modules) OK · 린트 0.
- **후속(디바이스 검증 동반):** 호칭/“나를 잊어줘(resetPersona)” UI, 관심·습관 기반 능동 제안(리마인더 발화), 도메인별 톤 전환 라이브 튜닝. 모두 온디바이스 SSOT 유지.

### 7-4. Phase 5.9 — 동반자 능력 확장: 언어쌍 교습·정직 계약·메모리 명령·능동 제안 (2026-06-24)

> **요구:** (1) 수신 채팅 읽어주기, (2) 부재중→채팅/VoIP 연결, (3) 50개국 언어쌍 교습 센스, (4) 최신·주식·상식 다각 답변, (5) **반드시 정직 — 거짓 안내 절대 금지(특히 국가별 위험지역·관습·예절)**, (6) 후속(resetPersona/호칭/능동 제안). 이 중 **순수·additive(무회귀)** 항목을 구현하고, **라이브 음성/VoIP 경로** 항목은 디바이스 검증 단계로 분리.

| 영역 | 신규/변경 | 내용 | 테스트 |
|------|-----------|------|-------|
| 멀티도메인 | `companionDomains.ts` | `language-tutor` 도메인 추가(자동 넘버링 #6) + `knowledge` 에 주식/최신/뉴스/날씨/환율/상식 키워드 보강. 초범용 토큰(how/what/어떻게) 충돌 제거로 분류 정밀도↑ | +2 |
| 언어쌍 교습 | `companionLanguageTutor.ts` | `detectLanguageTutorIntent` · `resolveTargetLanguageFromText`(50개국 LANGS 별칭/이름/코드 해석, `normalizeDetectedLangCode` 재사용) · `buildLanguagePair`/`buildLanguagePairLabel`(지정 언어↔물어본 언어) | +9 |
| 메모리 명령/능동 | `companionCommands.ts` | `parseCompanionCommand`("나를 잊어줘"→reset, "~라고 불러줘/call me"→set_name; 결정적, LLM 불필요) · `buildProactiveSuggestion`(습관/관심 기반 한 마디, 근거 약하면 null) | +6 |
| 백엔드(정직) | `voice_gateway.py` `_friend_system_prompt` | **HONESTY CONTRACT(최우선)** 추가: 거짓/날조 절대 금지, 불확실하면 솔직히 말하고 출처 안내; 주식/시세/뉴스/날씨 등 라이브 수치는 검증 데이터 있을 때만 단정, 없으면 공식 출처로; **국가별 위험지역·법·관습·예절·금기는 정확/신중, 추측 금지**. + **LANGUAGE TUTOR**(언어쌍+발음+뉘앙스) instruction. 모두 additive(관광/기존 동작 유지) | +3(pytest) |
| 라이브 배선 | `App.tsx` | 친구챗 처리에 `parseCompanionCommand` 배선(온디바이스 reset/호칭 즉시 반영, 서버 미저장) + 명령 턴은 관심사 누적 제외(무회귀) | — |

- 게이트: jest **+17**(도메인2/튜터9/명령6) · pytest **+3** · 번들(`expo export:embed`, 856 modules) OK · 린트 0.
- **정직 계약(사장님 최우선 원칙)** 은 페르소나 시스템 프롬프트 최상위 규칙으로 박혀, 위험지역·관습·예절·시세/최신 정보에서 **확신형 오답을 금지**하고 불확실성을 명시하도록 강제한다.

#### 7-4-1. 디바이스 검증 동반(라이브 경로) — 단계화(미구현, 다음 단계)
- **수신 채팅 읽어주기(TTS):** 채팅 수신 핸들러 + 오디오 재생 경로 변경 → 2단말/포그라운드·백그라운드 검증 필요. 순수 사전판정 헬퍼(읽을지 여부/낭독 텍스트 정리)부터 분리 권장.
- **부재중 전화 → 채팅/VoIP 연결:** VoIP 시그널링/콜 상태 경로(현재 S10 단방향 이슈 영역) 결합 → 라이브 2단말 검증 필수. 부재중 이벤트 모델 + 콜백/딥링크 재연결을 순수 모델로 먼저 설계.
- **실시간 주식/시세 피드:** 정직 계약상 "검증 데이터 없으면 수치 단정 금지"가 우선 적용 중. 실 수치 제공은 별도 금융 데이터 소스(API 키/라이선스) 연동이 필요한 백엔드 그라운딩 확장 과제.

### 7-5. Phase 5.10 — 가입 필수 "나의 AI 이름" + 소리새 AI → "OOOO AI" 자동 치환 + 수신 채팅 읽어주기 (2026-06-24)

> **요구:** (1) 회원가입 조건에 **나의 AI 이름 등록 필수** → 기존 "소리새 AI" 를 사용자 지정 "OOOO AI" 로 **자동 변경**, (2) **사용자 명령 시 수신 채팅 읽어주기**부터 디바이스 검증과 함께 진행.

| 영역 | 신규/변경 | 내용 | 테스트 |
|------|-----------|------|-------|
| AI 이름 SSOT | `src/features/sorisae/companionIdentity.ts` | `normalizeAiName`(트림/공백압축/제어문자/길이상한20) · `isValidAiName`(가입 필수 검증) · `resolveAiDisplayName`(→ "OOOO AI", AI/에이아이 접미 중복 방지, 무효 시 기본 "소리새 AI") · AsyncStorage 영속(`load/saveAiName`, `loadAiDisplayName`) | +10 |
| 낭독 순수층 | `src/features/sorisae/companionChatReadAloud.ts` | `sanitizeChatTextForSpeech`(URL/코드블록/마크다운 제거·길이상한220) · `shouldReadAloudIncoming`(토글ON+수신+낭독가능 판정) · 토글 영속(`load/saveChatReadAloudEnabled`) | +14 |
| 가입 배선 | `App.tsx` | `signupAiName` 상태 + `handleSignupRequestCode` 필수 검증 + 확인 성공 시 `saveAiName`/`setAiDisplayName`. 가입 폼에 "나의 AI 이름(필수)" 입력 + 실시간 미리보기 힌트 | — |
| 표시명 치환 | `App.tsx` | `aiDisplayName` 상태(마운트 시 `loadAiDisplayName` 복원) 로 소리새 AI 창 제목/대화 토글/상태 메시지/알림 **전구간 자동 치환** | — |
| 수신 낭독 배선 | `ChatRoomScreen.tsx` | 헤더 "🔈 읽어주기" 토글(영속) + 수신 이벤트 훅에서 `shouldReadAloudIncoming` 판정 후 `expo-speech` 발화(뷰어 번역본 우선·`viewer_translation.target_lang` 언어 추정·방 이탈/비활성 시 `Speech.stop`) | — |

- **AI 이름은 계정 식별** 이라 별도 키(`worldlinco_companion_ai_name_v1`)에 저장 — "나를 잊어줘(resetPersona)" 메모리 초기화로는 지워지지 않는다(페르소나 기억과 분리).
- **수신 채팅 읽어주기는 사용자 명령(토글)** 일 때만 동작하며 기본 OFF. 순수 판정/정리 헬퍼는 단위테스트로 고정하고, 실제 발화(expo-speech)·실시간 수신 경로는 **2단말 디바이스 검증 단계**로 둔다.
- 게이트: jest **+24**(identity10/read-aloud14) · 번들(`expo export`, **858 modules**) OK · 린트 0 · tsc 신규파일 에러 0(기존 tsconfig `--module`/expo-av 잔존 에러는 무관).

#### 7-5-1. 디바이스 검증 항목(수신 채팅 읽어주기)
- 2단말 1:1/그룹 방에서 상대 메시지 수신 시 토글 ON 상태에서 음성 낭독되는지(번역본 우선·언어 일치).
- 포그라운드/백그라운드 전환·방 이탈 시 낭독 정지(`Speech.stop`) 정상 동작.
- 토글 OFF 시 낭독 미발생 + 기존 수신음(playMessageTone) 회귀 없음.

### 7-6. Phase 5.11 — 채팅 마이크/텍스트 겸용 입력 + 연락처 연동(채팅/VoIP/일반통화) + SNS 연동 채팅 (2026-06-24)

> **요구:** (1) 채팅 **입력 방식을 마이크/텍스트 겸용**, (2) **모바일 연락처를 채팅/VoIP/일반통화에 연동**(VoIP·일반통화는 기존 동작 → 채팅 시작 보강), (3) **SNS 연동 채팅**(카카오톡/라인 등으로 초대·공유). 사장님 확정: 마이크는 STT→**입력칸 채움 후 확인 전송**, SNS는 **OS 공유 시트 초대/공유**(외부 SDK·OAuth 불요).

| 영역 | 신규/변경 | 내용 | 테스트 |
|------|-----------|------|-------|
| 마이크 입력 순수층 | `src/features/chat/chatVoiceInput.ts` | `resolveVoiceSttLangs`(from=auto·to 폴백 ko) · `cleanVoiceTranscript`(공백/제어문자 정리) · `mergeTranscriptIntoDraft`(초안+STT 결합) · `isVoiceAudioLongEnough`(MIN 800) | +11 |
| 마이크 입력 훅 | `src/features/chat/useChatVoiceInput.ts` | 토글 녹음(`Audio.Recording`) → base64(`FileSystem`) → 서버 STT(`voiceTranslate.original_text`) → `onTranscript`. 권한/오디오모드/언마운트 정지 가드 | — |
| 전화키 SSOT 분리 | `src/services/phoneKey.ts` | `normalizePhoneKey`(끝 9자리 매칭 키)를 **react-native 비의존 순수 모듈**로 분리 → `deviceContacts.ts` 재export(기존 import 호환) · 단위테스트 가능 | — |
| 연락처↔친구 매칭 | `src/features/contacts/contactFriendMatch.ts` | `buildFriendPhoneIndex`(앱 사용자 친구만·번호 정규화) · `matchFriendByPhones` · `resolveContactChatAction`(매칭=채팅 / 미가입=초대) | +6 |
| SNS 공유 SSOT | `src/features/sns-share/snsShare.ts` | `buildChatInviteMessage`/`buildInstallUrl`(=`${apiBase}/api/marketplace/latest.apk`)/`buildChatDeepLink`(`worldlingo://chat/…`)/`composeShareText` 순수 + `shareChatInvite`(RN `Share` **지연 import**로 jest 변환 제외 회피) | +6 |
| 채팅 입력 배선 | `ChatRoomScreen.tsx` | 작성칸에 🎙️ 음성 버튼(idle/recording/transcribing) + 오류 표시. STT 결과를 `mergeTranscriptIntoDraft` 로 입력칸에 합쳐 채움(확인 후 전송) | — |
| SNS 초대 배선 | `ChatRoomScreen.tsx` | 헤더 "📨 SNS 초대" → `shareChatInvite`(방 딥링크/설치 URL) | — |
| 연락처 액션 배선 | `App.tsx` | OS 연락처 피커 선택 후 액션 선택(💬 채팅/초대 · 📞 일반통화). 채팅은 번호→친구 매칭 시 `createDirectChatRoom` 으로 방 열기, 미가입은 `shareChatInvite` 초대. 피커 안내 문구를 "연락처 연동(채팅·VoIP·일반통화)" 으로 갱신 | — |

- **재사용 원칙:** 음성 인식은 신규 STT 엔드포인트 없이 기존 `voiceTranslate`(audio_base64) 의 `original_text` 만 사용(번역 결과 미사용). VoIP/일반통화 연락처 연동은 기존 흐름 유지하고 **채팅 진입만 추가** → hot path 무변경.
- **jest 변환 경계:** 이 프로젝트 jest 는 `transformIgnorePatterns=node_modules` 라 모듈 최상단 `import 'react-native'` 가 있으면 순수 헬퍼 테스트가 깨진다. 그래서 (a) `normalizePhoneKey` 를 RN 비의존 `phoneKey.ts` 로 분리, (b) `snsShare` 의 `Share` 는 호출 시점 동적 import 로 처리.
- 게이트: jest **+23**(voice11/sns6/match6, 전체 35스위트·283테스트 통과) · 번들(`expo export`, **863 modules**) OK · 린트 0.

#### 7-6-1. 디바이스 검증 항목
- 채팅 🎙️ 버튼: 녹음→정지→입력칸에 인식 텍스트 채움(확인 후 전송), 권한 거부/짧은 녹음 오류 표시.
- 연락처 피커: 연락처 선택 → 채팅(친구면 방 열림)/초대(미가입 시 공유 시트)/일반통화(번호 채움) 분기.
- 채팅방 "📨 SNS 초대": OS 공유 시트(카카오톡/라인/문자)로 초대 메시지+링크 전송.

### 7-7. Phase 5.12 — 마이크 STT 작동불능 수정 + 단말 전화번호부 전체 디렉터리 + SNS 앱 홍보 (2026-06-24)

> **사장님 피드백:** (1) 채팅 마이크가 **실음성에서 인식 안 됨(작동 불능)**, (2) 연락처 연동은 피커 액션이 아니라 **사용자 휴대폰에 저장된 연락처 전체와 연동**(일반전화 통역/VoIP/채팅), (3) **프로그램(앱) 홍보를 SNS로** 하는 방법.

| 영역 | 신규/변경 | 내용 |
|------|-----------|------|
| 마이크 STT 근본수정 | `chatVoiceInput.resolveVoiceSttLangs` · `useChatVoiceInput` | 채팅 STT가 `from_lang:'auto'`+designated 로 호출돼 서버가 `detected_from_lang=from_lang='auto'` 로 고정→'auto' 번역/gibberish 판정에서 422·오류로 **throw** 하던 것이 작동불능 원인. 채팅 입력 화자는 **로컬 사용자**이므로 from 을 사용자 지정 언어로 **고정(designated)**, 양쪽 언어를 알면 bilingual(face). 녹음 16kHz/모노/32k 로 검증경로와 정합. 실패 시 서버 메시지(≤60자) 그대로 노출 + `[CHAT_VOICE_STT_FAIL]` 로그 |
| 연락처 디렉터리 | `src/features/contacts/ContactsDirectoryModal.tsx` (신규) | `loadDeviceContacts` 로 단말 저장 연락처 **전체**를 검색 가능한 목록(FlatList)으로 렌더. 각 행 [📞 통역통화 / 📡 VoIP / 💬 채팅·초대] 3액션 + "앱 친구" 배지. VoIP/채팅은 번호↔친구 매칭(`matchFriendByPhones`) 시만 활성, 미가입은 채팅이 초대로 폴백. 하단 "📣 앱 홍보 공유" |
| 연락처 액션 배선 | `App.tsx` | `handleRegularCallContact`(번호 채움→`startPstnAssistDialFlow` 다이얼+자동 통역), `handleVoipCallContact`(`handleStartFriendVoiceCall`), `handleChatContact`(`createDirectChatRoom`/`shareChatInvite`). 예약 레일 진입 버튼을 "📇 연락처 연동(전화/VoIP/채팅)" → 디렉터리 모달로 교체 |
| expo SDK 56 버그수정 | `src/services/deviceContacts.ts` | 메인 `expo-contacts` 의 `getContactsAsync` 가 **deprecated→throw** 라 연락처 0건이던 것을 `expo-contacts/legacy` import 로 교정. 권한 폴백(`getPermissionsAsync`) + `[DEVICE_CONTACTS]` 텔레메트리 추가 |
| SNS 앱 홍보 | `src/features/sns-share/snsShare.ts` | `buildAppPromotionMessage`(가치 카피·추천인) + `shareAppPromotion`(설치 URL 포함 OS 공유 시트). 외부 SDK/광고계정 없이 카카오톡·라인·SNS·문자로 즉시 전파 |

- **게이트:** jest **285 통과**(신규 chatVoiceInput +5·snsProm +2 포함) · 린트 0 · gradle assembleRelease build198 OK(번들 게이트 통과).
- **실기기 검증(R83W70QY11H, build198):** 앱 정상 실행 · 연락처 디렉터리 **1137명 로드**(raw 1250→usable 1137, 권한 granted) · 통역통화/VoIP(미가입 비활성)/초대 3액션 + 앱 홍보 공유 버튼 렌더 확인. **마이크 실음성 STT 는 사용자 수용 테스트 통과**(사장님: "마이크 실음성 아주 잘되고 있습니다").

### 7-8. Phase 6.1 — tsc/잔재테스트 전수 정리 + 소리새 AI 음성 호출형(웨이크워드·3분 자동 종료) + 소리새 심볼 앱 아이콘 (2026-06-24)

> **사장님 요청:** (1) `tsc` 오류·실패 테스트 스위트 **모두 수정**, (2) 소리새 AI를 **음성 호출형**으로 — 로그인 상태에서 이름을 부르면 깨어나 대화하고 **3분 무응답이면 자동 종료**, (3) **소리새 아이콘을 월드링코 심볼**(앱 아이콘)로 사용.

| 영역 | 신규/변경 | 내용 |
|------|-----------|------|
| 잔재 테스트 정리 | `src/__tests__/dist/*.js` 삭제 · `package.json` jest · `tsconfig.json` | 컴파일 잔재 `dist/AppSignupProfile.test.js`·`FriendMapDiscoveryScreen.test.js`(소스 없음, `__assign` 변수 참조로 mock 실패) 2스위트 삭제 + `testPathIgnorePatterns:['/node_modules/','/dist/']` · tsconfig `exclude:['**/dist/**','**/*.test.js']` 로 재발 차단 |
| tsc 오류 근본수정 | `tsconfig.json` · `package.json`(typescript ~5.3.3→**~5.8.3**) | TS6046 근본원인 = expo base 가 `module:"preserve"`(TS5.4+ 전용)인데 5.3.3 핀 → `--module` 거부·dynamic import(TS1323) 연쇄. TS 5.8.3 업그레이드 + `module:"esnext"` 명시로 **전수 해소** |
| Audio 타입 정합 | `faceConversationVadController.ts` · `VoIPCallScreen.tsx` · `voipToneService.ts` | 값(const `Audio`)을 타입 위치(`Audio.Recording/Sound/RecordingOptions`)로 쓰던 것을 compat 의 타입 export(`AudioRecording`·`AudioSound`·`RecordingOptions`)로 교정. VAD 설정 타입을 `VoiceRelayVadConfig` 인터페이스로 느슨화(literal `as const` 강제 제거), `status.metering` `number\|undefined`→`-160` 폴백, `getInfoAsync` 의 폐기된 `{size}` 옵션 제거, `expoAvAudio` web 옵션 기본값, NetInfo details 경계 캐스팅 |
| 음성 호출형 순수층 | `src/features/sorisae/companionVoiceCall.ts` (신규) | 상태기계(off/dormant/awake) SSOT: `matchCompanionWakeWord`(이름 코어+"소리새"+별칭, 공백/구두점 무시) · `arm/disarm/wake/sleep` · `markActivity` · `shouldSleep`(3분=`COMPANION_VOICE_CALL_IDLE_MS` 180000) · `onTranscript`. RN/타이머/오디오 비의존 |
| 음성 호출형 배선 | `App.tsx` | "📞 음성 호출 대기" 토글(로그인·비통화 시 노출). dormant 동안 통역 캡처를 **조용한 웨이크워드 스캐너**로 재사용(전사 통역/표시/발화 없이 호명만 감시) → 감지 시 소리새 창 열고 gpt 대화 모드로 듣기 이어감. awake 매 턴 활동시각 갱신, 15s 주기 검사로 3분 무응답 시 창 닫고 dormant 복귀(다시 부르면 깨어남) |
| 소리새 앱 아이콘 | `assets/icon.png`·`adaptive-icon.png` + `android/.../mipmap-*/ic_launcher*.png` | 플레이스홀더(단색 원)였던 아이콘을 **소리새(소리=음성파형에서 날아오르는 새)** 심볼로 교체(네이비 #0b0f16·시안 #58c9ff). 1024² 정사각 크롭 후 5개 density 의 launcher/round/foreground mipmap 재생성(어댑티브 안전영역 준수). 원본은 `assets/legacy-icon-backup/` 백업(복구 가능) |

- **게이트:** jest **36스위트·302테스트 통과**(신규 companionVoiceCall **+15**) · **tsc --noEmit 0 오류** · 린트 0 · gradle assembleRelease **build200 OK**.
- **실기기 검증(R83W70QY11H, build200):** 새 소리새 아이콘 빌드/설치 OK(런처 mipmap 시안 새 렌더 확인) · "📞 음성 호출 대기 켜기"→"🔔 부르면 깨어나요"(armed)·Conversation ON·Listening 전환 OK · armed 상태에서 **번역 출력 없이 조용히 대기**(입력/결과칸 비어 있음=주변대화 통역 미노출) 확인. **실음성 호명→깨우기·3분 자동 종료는 사용자 수용 테스트 대기**(상태기계 15테스트로 회귀 차단).

### 7-9. Phase 6.2 — 대면 통역 언어 감지 조사 + VoIP 음성 속도·볼륨 사용자 패턴 자동 튜닝 (2026-06-24)

> **사장님 보고/요청:** (1) 대면 통역에서 "언어 감지를 못한다"·"음성감지 감도 저하·양방향이 부자연스럽게 연결", (2) **VoIP 통화 음성 속도·볼륨을 사용자 패턴에 맞춰 자동 감지·조절하는 런타임 튜닝** 구현 가능 여부.

| 영역 | 신규/변경 | 내용 |
|------|-----------|------|
| 대면 언어 감지 조사 | (조사) `backend/llm/router.py` `_transcribe_bilingual_voice_audio`/`_resolve_bilingual_route` · 단말 logcat | 실기기 logcat·화면으로 **감지 정상 동작 확인**: `segment_response ok=true bilingual=true stt_trust=high from="ja" to="ko"` (일본어 발화→`わかりまして本当にですよ`→`알겠습니다 정말이에요`). Phase6.1 의 metering `-160` 폴백은 **meter-dead 폴백 경로**(활성 경로는 silero native capture)라 회귀 아님. 양방향 부자연스러움은 에코가드(outputLangEcho/substringEcho·25s/5s 창)의 보수적 차단 영향으로 추정 → 자동 튜닝의 발화패턴 학습으로 점진 완화 |
| 음성 속도·볼륨 자동튜닝 순수층 | `src/features/voip-voice-relay/voiceRuntimeAutoTuning.ts` (신규) | SSOT 순수 상태기계: 매 STT 턴의 `(발화길이ms·전사글자수·피크dB)`로 사용자 **말속도(글자/초)·발성음량 EMA** 학습 → 통역 TTS `ttsRate[0.85~1.25]`·`ttsVolume[0.7~1.0]` 환산. 빠른발화→rate↑/느린발화→rate↓, 큰발화(시끄러운 환경 보정)→volume↑. 워밍업(2표본)·환각 cps 컷·meter 불가 시 볼륨학습 제외·`repeatRequested` 시 일회성 속도↓·볼륨↑. 직렬화로 통화 간 영속. RN/오디오/스토리지 비의존 |
| 자동튜닝 배선 | `VoIPCallScreen.tsx` | 마운트 시 `AsyncStorage(@worldlinco/voip/runtime-tuning/v1)` 하이드레이트, 신뢰도 높은 유효 턴마다 `recordVoiceTuningObservation`(공백제거 글자수·snapshot 발화길이/피크dB/meter가용) 학습+1.5s 디바운스 영속화, 통역 재생에 적용 — 서버 합성 오디오(expo-av Sound)는 **볼륨**, 디바이스 TTS(`Speech.speak`)는 **rate+volume** 자동값. `[VOIP_RUNTIME_TUNING]` 텔레메트리 |

- **게이트:** jest **37스위트·316테스트 통과**(신규 voiceRuntimeAutoTuning **+14**) · **tsc --noEmit 0 오류** · 린트 0 · gradle assembleRelease **build201 OK**.
- **실기기 검증(R83W70QY11H, build201):** v1.0.149/build201 빌드·설치·실행 OK(크래시 0) · GPS 자동 언어 감지 정상(국가 KR→추천 한국어) · 대면 통역 감지 화면 정상(日本語→한국어). 자동튜닝은 다자 통화 다턴 누적으로 발현(단말 1대 단독 풀검증 불가) → **순수모듈 14테스트로 회귀 차단**, 통화 시 `[VOIP_RUNTIME_TUNING]` 로그로 실측 가능.

### 7-10. Phase 6.3 — 소리새 홈 음성 대기 안정화 + 최신 번들 반영 판독 규칙 (2026-07-03)

> **범위:** 소리새 홈 전용 음성 대기, 긴 질문 절단, 홈 자동 음성 호출 대기(`auto_arm`)의 런타임 반영 여부.  
> **대상 단말 실측:** `SM_T225N` (`R83W70QY11H`) · 설치 패키지 `com.parkcheolhong.worldlinco` · `versionName=1.0.236` · `versionCode=299`.

#### 7-10-1. 실측 증상과 근본 원인

- **긴 질문이 중간에서 잘림**  
홈 소리새 Q&A가 대면 통역 공용 `face_conversation` 경계값을 그대로 사용했다. 런타임 튜닝이 공격적일 때(`silence_flush_ms≈900`, `min_segment_ms≈1600`, `restart_ms≈120`) 짧은 숨 고르기만으로 세그먼트가 잘렸다.

- **심볼 파장이 중간에 흔들리거나 끊겨 보임**  
`SorisaeVoiceWaveOrb` 가 `wavePaused` 토글마다 애니메이션 루프를 `stop/reset/start` 했다. 답변 재생 전후 상태가 바뀔 때 오브가 리셋되며 체감상 깜박임/끊김으로 보였다.

- **홈 자동 음성 호출 대기(`auto_arm`) 미반영**  
코드 상수는 `true` 였지만, 단말 logcat 에서는 지속적으로 `COMPANION_VOICE_CALL armable_eval ... auto_arm:false` 만 관측됐다. 같은 로그에서 `companion_arm_suspended:false`, `voip_session_active:false`, `has_user:true` 였으므로 조건 미충족이 아니라 **최신 JS 번들이 단말에 반영되지 않은 상태**로 판정했다. 이를 식별하기 위해 `App.tsx` 에 `home_auto_arm_config` 시작 로그를 추가했다. 이 로그가 보이지 않으면 최신 번들이 아님을 의미한다.

#### 7-10-2. 적용한 수정

| 영역 | 수정 | 파일 |
|------|------|------|
| 홈 Q&A VAD | 소리새 전용 경계 해석기 추가 (`silence>=1700`, `min>=3200`, `max>=14000`) | `src/services/worldlincoTuningConfig.ts` |
| VAD 컨트롤러 | 세션별 VAD 설정 주입 허용 | `src/features/face-conversation/faceConversationVadController.ts` |
| 소리새 캡처 | 홈 경로만 긴 경계 사용 + 최소 세그먼트 상향 | `src/features/sorisae/useVoiceCaptureLoop.ts`, `src/features/sorisae/sorisaeCaptureSegment.ts` |
| 파장 UI | pause 시 루프 재생성 제거, 시각 강도만 감쇠 | `src/features/sorisae/SorisaeVoiceWaveOrb.tsx` |
| 홈 auto-arm 확인성 | 모바일 런타임 기준 플래그 + `home_auto_arm_config` 로그 추가 | `App.tsx` |

#### 7-10-3. 2026-07-03 ADB 실측 결과

**질문 절단 경로:** 해결 쪽으로 판정.

실기기 질문 로그에서 아래 순서를 반복 관측했다.

```text
FACE_CONVERSATION meter_unavailable
→ file_growth_speech / file_rms_speech
→ vad_flush reason=max_duration
→ silero_native_capture duration_ms≈9280~9420
→ segment_response ok=true stt_trust=high route="sorisae"
```

대표 전사 예시:

- `북제주가 그렇게 좋은 데구나 그럼 북제주에 그 뭐야 그 돼지가 유명한`
- `제주도를 갔으면 흑돼지를 먹어야지 왜 한우를 먹어 아니 대한민국 사람들은 맨 한우만 그렇게 주워 먹나봐`
- `공부를 좀 많이 하는구나 참 똑똑해졌네 ...`

판정:

- 이전처럼 문장 중간에서 짧게 잘리는 현상은 재현되지 않았다.
- 현재 단말은 자연 무음 종료보다 **`max_duration` 종료**가 우세하다. 따라서 긴 질문은 안정적이지만, 매우 긴 자유발화에서는 향후 `max_segment_ms` 조정 여지가 남는다.

**홈 auto-arm 경로:** 1차 실측에서는 미반영이었으나, 최신 release APK 재설치 후 해결 확인.

실측 로그:

```text
COMPANION_VOICE_CALL armable_eval
  auto_arm:false
  has_user:true
  sorisae_window_open:false|true
  voip_session_active:false
  companion_arm_suspended:false
```

1차 stale 번들 상태에서는 새 패치의 식별 로그 `home_auto_arm_config` 가 관측되지 않았다.

판정:

- 초기 판정은 홈 자동대기 로직 자체의 조건 실패가 아니라, **단말이 최신 JS 번들을 아직 사용하지 않음** 이었다.
- 같은 `versionName/versionCode` 여도 JS bundle 이 stale 일 수 있으므로, **버전 문자열만으로 최신 패치 반영 여부를 판정하지 않는다**.
- 최신 release APK 재설치 후에는 아래 로그가 확인됐다.

```text
COMPANION_VOICE_CALL home_auto_arm_config runtime_enabled:true source_flag:true platform:android
COMPANION_VOICE_CALL armable_eval armable:true auto_arm:true has_user:true armed:true
```

- 따라서 home auto-arm 패치 자체는 정상이며, 이후 문제는 stale bundle 여부부터 먼저 배제해야 한다.

#### 7-10-4. 최신 번들 반영 여부 30초 확인 절차 (최단)

1. 단말에서 앱을 완전히 종료한다.
1. 아래 명령으로 로그를 초기화하고 앱을 다시 띄운다.

```powershell
adb -s R83W70QY11H logcat -c
adb -s R83W70QY11H shell am force-stop com.parkcheolhong.worldlinco
adb -s R83W70QY11H shell am start -n com.parkcheolhong.worldlinco/com.parkcheolhong.worldlinco.MainActivity
adb -s R83W70QY11H logcat -d -v time ReactNativeJS:V OnDeviceKws:V *:S |
  Select-String -Pattern 'home_auto_arm_config|COMPANION_VOICE_CALL|WORLDLINGCO_TUNING'
```

1. **PASS 기준**  
`home_auto_arm_config` 가 보이고, `runtime_enabled:true` 가 보이고, 로그인 후 `armable_eval ... auto_arm:true` 가 보인다.

1. **FAIL 기준**  
`home_auto_arm_config` 가 없거나 `armable_eval ... auto_arm:false` 만 반복되면, 원인은 VAD가 아니라 **stale bundle / 재배포 미반영**이다.

#### 7-10-5. 다음 단계 게이트

다음 단계인 **VoIP 통화 품질 정밀 튜닝**은 아래 조건이 모두 만족될 때 시작한다.

1. `home_auto_arm_config` 가 단말에서 확인된다.
2. `armable_eval ... auto_arm:true` 가 확인된다.
3. 소리새 홈 긴 질문 1회에서 `segment_response ok:true` 와 정상 답변이 확인된다.

이 세 조건 전에는 VoIP 품질보다 **배포 반영/런타임 판독**을 우선한다. 그렇지 않으면 다른 기능을 튜닝할 때도 stale bundle 때문에 오판하게 된다.

### 7-1. VoIP S10 단방향(발신자 무음) 조사 — 보류 결론
- 2폰 라이브에서 **S10(발신)만 업링크가 디지털 무음 수준**(`caller→callee` frames~30k·voiced~46·segs~2·mean_rms~98)으로 STT 세그먼트 미형성. TAB(수신)→S10 방향은 정상(서버 STT 게인 정규화로 rms→1800 부스트 + `interpret emit ja→ko`).
- 스피커폰/이어폰/블루투스 라우팅 변경 모두 동일 → 라우팅(AEC) 단독 문제가 아니라 **S10 단말의 WebRTC 마이크 캡처 자체** 이슈로 추정.
- 조치: 서버 `backend/voip/media_bridge.py` uplink STT 게인 정규화 추가(유지, 타 단말에 유효). 클라이언트 마이크 제약(`echoCancellation/noiseSuppression/autoGainControl=false`) 실험 빌드는 S10 무음 변화 없어 회귀 위험으로 **원복**.
- 언어 표기(TAB 국가=한국·언어=일본)는 정상이며 무관함을 확인. 후속으로 S10 단말 오디오 소스/마이크 HW 레벨 단독 조사 필요.

---

*작성: 2026-06-23 · 갱신: 2026-06-24(§7 Phase 5.6 순수 모듈 분리 + §7-1 VoIP S10 조사 + §7-2 Phase 5.7 섹션 레일 SSOT/고유ID 자동 넘버링·자동 연결 + §7-3 Phase 5.8 소리새 AI 진화형 멀티도메인 동반자 + §7-4 Phase 5.9 언어쌍 교습·정직 계약·메모리 명령·능동 제안 + §7-5 Phase 5.10 가입 필수 AI 이름·표시명 자동 치환·수신 채팅 읽어주기 + §7-6 Phase 5.11 채팅 마이크/텍스트 겸용·연락처 연동·SNS 연동 채팅 + §7-7 Phase 5.12 마이크 STT 작동불능 수정·단말 전화번호부 전체 디렉터리·SNS 앱 홍보 + §7-8 Phase 6.1 tsc/잔재테스트 전수 정리·소리새 AI 음성 호출형(웨이크워드·3분 자동 종료)·소리새 심볼 앱 아이콘 + §7-9 Phase 6.2 대면 언어감지 조사·VoIP 음성 속도/볼륨 사용자패턴 자동 튜닝) · 전략 A+B(점진→완전분리) · 터미널 A+B(로그+프로세스) · 단일-활성 계약 확정.*
