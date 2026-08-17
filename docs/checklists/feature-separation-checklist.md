# ✅ 체크리스트: 모바일 앱 기능별 완전 분리

**작업명**: `App.tsx` 5개 기능 완전 분리 (대면통역 / 소리새AI+OCR / VOIP+채팅 / 일반전화+예약 / 노래번역)
**우선순위**: 🔴 P0 (현재 통증 — 기능 간 상호 침범)
**시작일**: 2026-06-23
**상태**: 진행중
**마스터 기술서**: [`../worldlinco-v2/FEATURE_SEPARATION_MASTER_SPEC.md`](../worldlinco-v2/FEATURE_SEPARATION_MASTER_SPEC.md)

---

## 핵심 불변 규칙 (모든 단계에서 검증)
- [x] **R1 단일 마이크 소유**: 한 시점에 마이크 캡처를 가진 기능은 단 하나. (voiceCaptureLease)
- [x] **R2 단일 TTS 소유**: 소리새 전용 TTS ref 분리 + 캡처 lease 로 재생 소유 단일화.
- [x] **R3 라우팅 스냅샷**: 소리새/대면 라우팅을 캡처 시작 시점 `mainSorisaeRouteRef` 로 고정.
- [x] **R4 전용 출력**: 소리새는 `sorisaeQaLog` 전용 — 대면 `inputText`/`resultText`/`engine` 미사용.

> ※ 디바이스 라이브 검증(육성/한일/소리새 무간섭/음량)은 build189·190 설치 후 수행.

---

## Phase 0 — 설계 문서
- [x] **0.1** 마스터 기술서 작성 `docs/worldlinco-v2/FEATURE_SEPARATION_MASTER_SPEC.md`
- [x] **0.2** ROADMAP / FILE_MAP / SERVICE_SEPARATION_DESIGN 백링크 등록
- [x] **0.3** 본 체크리스트 작성

## Phase 1 — 소리새↔대면통역 누수 차단 (최우선) — build189
- [x] **1.1** 소리새 라우팅 스냅샷(`mainSorisaeRouteRef`) — 캡처 타깃 분리 효과
- [x] **1.2** 소리새 출력은 `sorisaeQaLog` 전용 — 대면 `inputText`/`resultText`/`engine` setter 제거(자동 번역·자동 TTS 이펙트 누수 차단)
- [x] **1.3** 소리새 전용 TTS ref(`sorisaeVoicePlaybackSoundRef`) + 전용 `sorisaeSpeakingRef`
- [x] **1.4** 라우팅을 세그먼트 시작 시점 스냅샷으로 확정 (`isFaceGptMode` 라이브 ref 분기 제거)
- [x] **1.5** 소리새 창 open 시 `setAutoVoiceModeEnabled(false)` + 대면 캡처 정지 + 대면 TTS 정지
- [x] **1.6** 빌드/설치 (build189) — [ ] 라이브 검증(디바이스)

## Phase 2 — 음성엔진 중재 커널화 — build190
- [x] **2.1** `src/services/voiceCaptureLease.ts` 신규: `acquireVoiceCapture/releaseVoiceCapture/revokeCurrentVoiceCapture`
- [x] **2.2** `startVoiceInput` 단일 지점에서 lease 획득(face/sorisae/inter_call/song)
- [x] **2.3** `startVoiceInput` 경로/lease 판정 분리를 서비스로 완전 추출 + 라이브 ref 다중화 제거
  - 구현: `src/services/voiceCaptureLease.ts`에 `resolveVoiceCaptureLeaseFeature` / `shouldRouteMainSorisaeCapture` 추가
  - 적용: `src/features/sorisae/useVoiceCaptureLoop.ts`에서 inline route logic 제거 및 shared helper 호출
  - 검증: `npx jest src/__tests__/voiceCaptureLease.test.ts --runInBand` → 5/5 pass

## Phase 3 — `useCallModeController` 분리 — 완료
- [x] **3.1** `useVoipState` 추출 (VOIP 상태)
- [x] **3.2** `useInterCallState` 추출 (일반전화 상태)
- [x] **3.3** 컨트롤러는 두 훅을 compose — 공개 API/소비부(App.tsx) 불변

## Phase 4 — 단일-활성 FeatureShell — build190
- [x] **4.1** 레일(기능) 변경 시 단일-활성 enforcement 효과(`activeRailSection` watch)
- [x] **4.2** 기능 전환 시 직전 음성 기능 quiesce(`revokeCurrentVoiceCapture` → 마이크 정지)
- [x] **4.3** 명시적 FeatureShell 정리 단계: `FeatureQuiesceHandlers.cleanup` 추가 + quiesce 순서에 generic cleanup 적용
  - 구현: `src/features/isolation/fourFeatureRuntime.ts`에 `cleanup` 훅 추가, 전환 시 `stopCapture -> stopPlayback -> cleanup -> release` 순서 보장
  - 검증: `cd 'C:\Users\WORK\source\repos\parkcheolhong\codeAI\apps\mobile-nadotongryoksa'; npx jest src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts --runInBand --json --outputFile=jest-fourfeature.json` → `numPassedTests: 7`, `numFailedTests: 0`

## Phase 5 — 인라인 기능 모듈 추출 (단계적 — 디바이스 검증 동반)
- [x] **5.3a** `src/features/song/songText.ts` — 순수 가사/시간 헬퍼 추출(첫 안전 단계)
- [x] **5.2a** `src/features/sorisae/sorisaeEcho.ts` — 자기에코 판정 순수 헬퍼(`normalizeEchoText`/`echoOverlapRatio`) 추출(안전 단계)
- [x] **5.4a** `src/features/travel-booking/{types.ts,travelBooking.ts}` — 순수 헬퍼/타입(`buildNearbyMapHtml`·`escapeMapLabel`·`formatDistance`·`todayPlus` + `NearbyPlace`/`BookingResponse`/`SearchCategory`) 추출(안전 단계)
  - 부수 픽스: `buildNearbyMapHtml` WebView 스크립트에 build35 베이스라인부터 오삽입돼 있던 JSX 3줄(`accessibilityRole`/`accessibilityLabel`/`testID`, `item` 미정의) 제거 → 근처 지도 마커 렌더 손상 수정.
- [x] **5.1a** `src/features/face-interpretation/faceConversationTiming.ts` — 대면통역 전용 타이밍 상수(`FACE_CONVERSATION_RESTART_MS`/`PLAYBACK_CAP_MS`/`PERMISSION_RETRY_MS`/`ECHO_GUARD_MS`/`SPOKEN_HISTORY`/`PLAYBACK_DRAIN_MS` + `FACE_OUTPUT_ECHO_GUARD_MS`) 추출(순수 상수, 안전 단계).
  - 부수 정리: App.tsx 로컬 중복이던 공용 음성릴레이 헬퍼 `normalizeRelayText`(orchestrator와 동일 로직)·`formatAutoRelayDelayLabel`(신규 export)을 `src/features/voip-voice-relay/voiceRelayOrchestrator.ts` 로 통합(대면/VOIP/일반전화/자동번역 공유 SSOT) → App.tsx 중복 정의 제거.
  - 검증: 회귀 단위테스트 +4(faceConversationTiming 2 + voiceRelayOrchestrator 2; 소스 jest 137 통과), JS 번들 게이트 843 모듈 OK.
- [ ] **5.1** `src/features/face-interpretation/` (상태/JSX/핸들러)
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 신규로 얼굴 통역 시작/종료 토글 핸들러를 feature layer 로 이동
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 에서 auto voice 종료 경로를 `stopFaceConversationAutoVoiceMode` 로 추가 분리
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 에서 companion voice call 해제 경로를 `disarmCompanionVoiceCallForFaceConversation` 으로 추가 분리
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 에서 시작 활성화 경로를 `startFaceConversationSession` 으로 추가 분리
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 에서 faceConversationTexts 조립을 `buildFaceConversationTexts` 로 추가 분리
  - 진행: `src/features/face-interpretation/faceConversationController.ts` 에서 controller deps 조립을 `buildFaceConversationControllerDeps` 로 추가 분리
  - 진행(2026-08-16): `useFaceConversationAutoVoiceGuards` 추가로 대면통역 auto voice guard useEffect 3개(동일언어 차단/워크스페이스 이탈 시 종료/활성화 시 자동 시작)를 App.tsx 인라인에서 feature 모듈로 이동
  - 진행(2026-08-16): `src/features/face-interpretation/FaceInterpretationScreen.tsx` 신규로 대면통역 화면 JSX 블록(모달/언어필/피어·내 텍스트/마이크 토글/하단 탭)을 분리하고 `App.tsx` 인라인 모달 블록을 컴포넌트 호출로 교체
  - 진행: App.tsx 에서 face conversation controller deps 객체를 지역 변수로 묶어 호출부 연결부 축소
  - 검증: `src/__tests__/faceConversationController.test.ts` 8/8 pass
  - [x] 자동시작/자동종료 분리 증적 닫힘(미니 러너): `scripts/collect_face_start_stop_evidence.ps1` (`face-start-stop-v2`) 기준 1차 PASS. 근거: 1차 요약 산출물.
  - [x] full capture 실패 원인 중 언어피커 미개방 해소: `scripts/collect_face_capture_evidence.ps1` 탭 셀렉터 안정화 1회(가시 bounds 우선 + 단일 재시도) 후 2차 재검증에서 `langPickerOpened=true`, `peerLangSelected=true` 확인. 근거: 2차 요약 산출물.
  - [ ] full capture FACE trace 수집 미해결: 동일 근거에서 `hasStartSignal=false`, `hasNetworkSignal=false`로 PASS 미충족(`pass=false`).
- [ ] **5.2** `src/features/sorisae/` (+OCR) 잔여(상태/JSX/핸들러; OCR 파싱은 서버측 — App.tsx에 순수 추출 대상 없음)
- [x] **5.5a (선행)** 공용 언어 모듈 분리 `src/features/language/languageCatalog.ts` — `LANGS`/`LangCode`/`SUPPORTED_LANGUAGE_COUNT`/`getLangLabelText`/`isSupportedLangCode`/`WHISPER_LANG_MAP`/`normalizeDetectedLangCode`/`inferSpeechLangCode`/`resolveAutoTargetLang` (대면/소리새/노래/VOIP/일반전화 공유 SSOT, 순수)
- [x] **5.5b (선행)** 공용 발화(TTS) 텍스트 모듈 분리 `src/features/tts/ttsText.ts` — `normalizeSpeakText`/`inferTtsLanguage`(로케일 교정은 scriptLangResolver/voipLanguageLocales 위임, 순수)
- [x] **5.3b** `src/features/song/songLang.ts` — `normalizeSongFileLang`/`resolveSongFileTargetLang` 추출(공용 언어 모듈 의존 → 순환 import 해소)
- [x] **5.T** 추출 순수 모듈 회귀 가드 단위 테스트 추가 — `__tests__/{languageCatalog,songLang,sorisaeEcho,travelBooking,ttsText}.test.ts` (신규 41 케이스, 지도 오삽입 JSX 회귀가드 포함; 전체 jest 133 통과)
- [x] **5.6a** 인앱 업데이트 SSOT 정리 — App.tsx 로컬 중복 버전 헬퍼(`parseVersionTriplet`/`parseBuildNumber`/`compareSemanticVersions`/문자열 인자 `isRemoteApkNewer`/`resolveLatestApkMetadataUrl` + 고아 상수 `LATEST_APK_METADATA_PATH`) 제거 — 실제 경로는 `src/features/app-update/appUpdate.ts`(메타데이터 기반 `isRemoteApkNewer`)로 단일화돼 있었고 로컬본은 호출처 0건(죽은 중복). 번들 게이트 842 모듈 OK, 린트 0.
- [x] **5.6b** 수익화(결제/구독) 도메인 분리 `src/features/monetization/monetization.ts` — `MonetizationPlanKey`/`MonetizationPlanConfig`/`MONETIZATION_PLAN_CONFIG`/`PREMIUM_PURCHASE_STATUSES`/`isPurchaseSettled`/`resolvePlanKeyFromPurchase`/`collectOwnedPlanKeys` 추출(순수, SSOT). App.tsx는 `MONETIZATION_PLAN_CONFIG`·`collectOwnedPlanKeys`·타입만 import, 나머지 3개는 모듈 내부 캡슐화. 검증: 단위테스트 +9(`__tests__/monetization.test.ts`) 통과, 번들 게이트 OK, 린트 0.
- [x] **5.6c** 프로필 표시용 포매터 분리 `src/features/profile/profileFormatters.ts` — `resolveCountryFlag`/`resolveLocaleCountryCode`/`resolveLanguageLabel`(LANGS 의존) + 성별 라벨 `formatVoipGenderLabel`/`formatDiscoveryGenderLabel`/`resolveDiscoveryGenderFromProfile` + 타입 `VoipGenderOption` 추출(순수). 검증: 단위테스트 +8(`__tests__/profileFormatters.test.ts`) 통과, 번들 게이트 OK, 린트 0.
  - 잔류(후속 country 모듈 단계): `resolveCountryName`/`COUNTRY_NAME_MAP` 은 `SIGNUP_COUNTRY_OPTIONS`/`SignupCountryCode`/`resolveLangFromCountry` 클러스터(타입·JSX·핸들러 수십 곳)와 강결합 → 빅뱅 방지 위해 별도 단계로 분리 예정.
- [x] **5.6d** 콜모드/통번역 상태 순수 헬퍼 분리 `src/features/call-mode/callModeHelpers.ts` — `TERMINAL_VOIP_STATUSES`/`normalizeCallModeCandidate`/`resolveCallModeFromPayload`/`formatUnifiedCallModeText`/`formatUnifiedTranslationStatus`/`isTerminalVoipStatus` + 타입 `TranslationStatusRoute`/`TranslationStatusPhase` 추출(순수; `CallMode`/`CallInitResponse` 타입 의존). `SECTION_RAIL_ITEMS`/`buildSectionRailSelector`(네비 관심사)는 App.tsx 잔류. 검증: 단위테스트 +10(`__tests__/callModeHelpers.test.ts`) 통과, 번들 게이트 OK, 린트 0.
- [x] **5.6e** country 클러스터 단계 분리 `src/features/country/*` — 영향 정밀 매핑 후 의존순(B→A→C) 단계 추출:
  - **5.6e-1(B)** `countryLanguage.ts` — `COUNTRY_LANG_MAP`/`resolveLangFromCountry`(LangCode 의존). +4 테스트.
  - **5.6e-2(A)** `countryCatalog.ts` — `SIGNUP_COUNTRY_OPTIONS`/`SignupCountryCode`/`SIGNUP_COUNTRY_OPTION_CODES`/`COUNTRY_NAME_MAP`/`isSupportedSignupCountryCode`/`normalizeSignupCountryCode`/`resolveSignupCountryFromLang`/`resolveCountryName`(B 위임). +7 테스트.
  - **5.6e-3(C)** `regionHints.ts` — `GPS_REGION_COORDINATE_FALLBACKS`/`DIALECT_REGION_HINT_KEYWORDS`/`resolveGpsDialectRegionHint`(expo-location 타입)/`resolveGpsCoordinateFallback`/`resolveRegionHintForSourceLanguage`(B 위임). +6 테스트.
  - App.tsx 잔류: `SignupSelectionModal` 타입(국가 무관), `SECTION_RAIL_ITEMS`/`buildSectionRailSelector`. 각 단계 번들 게이트 OK, 린트 0.
- [x] **5.6f** 공용 텍스트/API 유틸 분리 `src/features/shared/textFormat.ts` — `formatStatusText`(템플릿 치환)/`extractApiErrorMessage`(서버 에러 메시지 추출)/`summarizeAuthToken`(로그-안전 토큰 요약) 추출(특정 기능 무관 순수 유틸). 검증: 단위테스트 +9(`__tests__/textFormat.test.ts`) 통과, 번들 게이트 OK, 린트 0.
- [x] **5.6g** VoIP 식별자/URL/TURN 순수 유틸 분리 `src/features/voip/voipSignaling.ts` — `buildVoiceId`/`buildVoipTopic`/`buildVoipWebSocketUrl`/`getDefaultVoipTurnServers`/`normalizeTurnServers`(TURNServer 타입 의존) 추출. 검증: 단위테스트 +7(`__tests__/voipSignaling.test.ts`) 통과, 번들 게이트 OK, 린트 0.
- [x] **5.7** 섹션 레일 SSOT 레지스트리 `src/features/navigation/sectionRegistry.ts` — 5곳 흩어진 정의(타입/`SECTION_RAIL_ITEMS`/셀렉터/딥링크 파서/correlation featureId)를 단일 배열 SSOT 로 통합 → **고유ID 자동 넘버링(numericId)** + 타입·아이템·셀렉터·파서·featureId **자동 연결**(레일 1개 추가 = 전 시스템 자동 연결). 검증: 단위테스트 +10(`__tests__/sectionRegistry.test.ts`), 번들 게이트 691모듈 OK, 린트 0.
- [x] **5.8** 소리새 AI 진화형 멀티도메인 동반자 — 관광특화→멀티 AI 친구(성격·습관·기억 인지). `src/features/sorisae/companionDomains.ts`(멀티도메인 SSOT+분류기, 자동 넘버링) · `companionMemory.ts`(온디바이스 진화형 기억 순수 모델: `observeTurn`/`buildPersonaBrief`) · `companionPersonaStore.ts`(AsyncStorage 영속). 백엔드 `voice_gateway.py` 멀티도메인 페르소나 framing 추가 + `persona_brief` 시스템 주입(additive, `FriendChatRequest.persona_brief`). App.tsx 무회귀 배선(브리프 주입 + 쓰기전용 `recordTurn`). **프라이버시: 온디바이스 SSOT, 서버 영속화 0.** 검증: jest +22, pytest +5(`test_voice_gateway_companion_persona.py`), 번들 854모듈 OK, 린트 0.
  - [x] 인접 슬라이스 분리 묶음 완료: `sorisaeConversationController`/`sorisaeWakeController`/`sorisaeWindowController`/`sorisaeDormantWatchdog`/`companionVoiceCallController` + wake/window/open-button 후속 분리까지 반영.
  - [x] 인접 슬라이스 단위테스트 통합 PASS: `sorisaeConversationController` 3/3, `sorisaeWakeController` 2/2, `sorisaeWindowController` 2/2, `sorisaeDormantWatchdog` 1/1, `companionVoiceCallController` 4/4, `sorisaeOpenButton` 1/1.
- [x] **5.9** 동반자 능력 확장 — 언어쌍 교습·정직 계약·메모리 명령·능동 제안. `companionDomains`(language-tutor 도메인 + knowledge 주식/최신 보강) · `companionLanguageTutor.ts`(50개국 교습 인텐트/타겟언어 해석/언어쌍, +9) · `companionCommands.ts`(`parseCompanionCommand` reset/호칭 + `buildProactiveSuggestion`, +6). 백엔드 `_friend_system_prompt` **정직 계약(거짓안내 금지·위험지역·법·관습·예절·주식/시세/최신 라이브 수치 검증 필수)** + 언어쌍 교습 instruction(additive, +3 pytest). App.tsx 명령 배선(온디바이스 reset/호칭, 무회귀). 검증: jest +17, pytest +3, 번들 856모듈 OK, 린트 0.
- [x] **5.10** 가입 필수 "나의 AI 이름" 등록 + 소리새 AI → "OOOO AI" 자동 치환 + 수신 채팅 읽어주기(토글). `src/features/sorisae/companionIdentity.ts`(AI 이름 SSOT: `normalizeAiName`/`isValidAiName`/`resolveAiDisplayName`/AsyncStorage 영속, +10) · `companionChatReadAloud.ts`(낭독 정리/판정 + 토글 영속, +14). App.tsx 가입 폼 필수 필드(`signupAiName` 검증/JSX/확인 시 `saveAiName`) + `aiDisplayName` 상태로 소리새 AI 표시명 전구간 자동 치환(창 제목/토글/상태/알림). ChatRoomScreen 헤더 "읽어주기" 토글 + 수신 훅 `expo-speech` 배선(뷰어 번역본 우선·언어 추정·방 이탈 시 정지). **AI 이름은 계정 식별이라 "나를 잊어줘" 메모리 초기화로 지워지지 않음.** 검증: jest +24, 번들 858모듈 OK, 린트 0.
  - [x] **5.10 수신 채팅 읽어주기(구현 완료, 디바이스 검증 대기):** 토글 ON 시 상대 메시지 음성 낭독(expo-speech). 2단말 실수신 검증 필요.
  - [ ] **5.9/5.10-라이브 잔여(디바이스 검증 동반):** 부재중 전화→채팅/VoIP 재연결 · 실시간 주식/시세 피드(금융 데이터 소스 연동) — 라이브 VoIP/외부 API 경로라 2단말 검증 후 단계 진행.
- [x] **5.11** 채팅 마이크/텍스트 겸용 + 연락처 연동(채팅/VoIP/일반통화) + SNS 연동 채팅. `src/features/chat/chatVoiceInput.ts`(STT 언어쌍/정리/초안결합, +11) + `useChatVoiceInput.ts`(녹음→`voiceTranslate.original_text`→입력칸 채움) · `src/services/phoneKey.ts`(normalizePhoneKey RN비의존 분리, deviceContacts 재export) · `src/features/contacts/contactFriendMatch.ts`(연락처↔친구 매칭=채팅/미가입=초대, +6) · `src/features/sns-share/snsShare.ts`(초대 메시지/설치URL/딥링크 + OS Share, +6). ChatRoomScreen 🎙️ 음성 버튼(확인 후 전송)+"📨 SNS 초대" 헤더. App.tsx 연락처 피커 선택 후 채팅/초대·일반통화 분기. 검증: jest +23(전체 35스위트/283), 번들 863모듈 OK, 린트 0.
  - [x] **5.11 구현 완료(디바이스 검증 대기):** 🎙️ 녹음→인식→입력칸 채움 · 연락처→채팅/초대 분기 · OS 공유 시트 초대 — 실기기 2단말 검증 필요.
- [x] **5.12** 마이크 STT 버그 수정 + 단말 전화번호부 전체 디렉터리 + SNS 앱 홍보. (1) **마이크 STT 작동불능 수정**: 채팅 STT가 `from_lang:'auto'`+designated 로 호출돼 서버가 'auto'를 화자언어로 고정→번역/판정 실패(throw)하던 근본원인 제거. `chatVoiceInput.resolveVoiceSttLangs(selfLang, counterpartLang)`가 **화자(로컬 사용자) 지정 언어로 from 고정**(designated) 또는 양쪽 알면 bilingual(face) 로 분기. 녹음 16kHz 모노로 검증경로와 정합. (2) **연락처 디렉터리**(`src/features/contacts/ContactsDirectoryModal.tsx`): `loadDeviceContacts` 로 휴대폰 저장 연락처 전체를 검색 가능한 목록으로 + 각 행 [📞 통역통화 / 📡 VoIP(친구만) / 💬 채팅·초대] 3액션. App.tsx `handleRegularCallContact`(PSTN 다이얼+통역)·`handleVoipCallContact`(친구 보이스톡)·`handleChatContact`(채팅방/초대) 연결, 예약 레일 진입 버튼 교체. (3) **`deviceContacts.ts` expo SDK 56 버그 수정**: `getContactsAsync` deprecated→throw 였음, `expo-contacts/legacy` import 로 교정. (4) **SNS 앱 홍보**: `snsShare.buildAppPromotionMessage`/`shareAppPromotion` + 디렉터리 하단 "📣 앱 홍보 공유" 버튼. 검증: jest 285 통과(신규 포함), 린트 0, build198 실기기 — **연락처 1137명 로드·3액션·홍보버튼 렌더 확인**.
  - [x] **5.12 디바이스 검증 완료:** 연락처 1137명 로드(raw 1250→usable 1137)·통역통화/VoIP(미가입 비활성)/초대 3액션·앱 홍보 공유 버튼 렌더(build198, R83W70QY11H).
  - [x] **5.12 사용자 수용 완료:** 채팅 마이크 **실음성** STT 입력칸 채움 — 사장님 "마이크 실음성 아주 잘되고 있습니다".
- [x] **6.1(기능)** tsc/테스트 정리 + 소리새 음성호출형 + 앱 아이콘 교체 완료.
  - [x] 구현/검증 요약: `companionVoiceCall.ts` 상태기계 도입, TS/오디오 타입 정합화, 아이콘 자산 교체, jest 36/302 + tsc/lint + build200 실기기 확인 완료.
  - [ ] 사용자 수용 잔여: 실음성 호명 깨우기 + 3분 무응답 자동종료는 사용자 확인 대기.
- [x] **6.2(기능)** 대면 감지 조사 + VoIP 런타임 음성 튜닝 도입 완료.
  - [x] 구현/검증 요약: `voiceRuntimeAutoTuning.ts` + `VoIPCallScreen.tsx` 배선, jest 37/316 + tsc/lint + build201 실기기(크래시 0, GPS/대면 감지 정상) 확인.
  - [ ] 사용자 수용 잔여: 다자 통화 다턴 누적 상황에서 `[VOIP_RUNTIME_TUNING]` 실측 확인 필요.
- [~] **5.3** `src/features/song/` 잔여(상태/JSX/핸들러) — **JSX 패스스루 추출 완료**: `src/features/song/SongModeSection.tsx`(노래 레일 244줄 → 컴포넌트, props 48개, 상태 소유권 App 잔류 → 동작 불변). `tsc` 0·린트 0·jest 37스위트/316 통과, App.tsx 10,516→10,324줄. 잔여: 노래 전용 state/effect colocate(후속·디바이스 검증 동반) + 디바이스 회귀(노래모드→파일→자막→세그먼트편집→내보내기).
  - [x] 인접 슬라이스 분리 묶음 완료: `songFilePlaybackController.ts`에 로드/재생토글/세그먼트편집/선택초기화/타임라인내보내기/선택결과반영/워크스페이스초기화까지 단계 분리 완료.
  - [x] 회귀 근거: `src/__tests__/songFilePlaybackController.test.ts` 최종 7/7 pass.
- [ ] **5.4** `src/features/travel-booking/` 잔여(상태/JSX/핸들러; travel-itinerary 통합)
  - [x] 인접 슬라이스 분리 완료: `travelBookingController.ts`에 주변검색(start/success/fail) + 예약요청 lifecycle(start/success/fail/finally) 분리.
  - [x] 회귀 근거: `src/__tests__/travelBookingController.test.ts` 4/4 pass.
  - [ ] 잔여: travel-itinerary 통합 및 디바이스 실검증은 후속.
- [x] **5.5** 공용은 Context/서비스로 주입(API_BASE/Language/Auth) — 언어 SSOT는 5.5a로 선분리 완료.
  - [x] 구현 치환 완료: `AppRuntimeProvider/useAppRuntime` 도입 + `AppInner` auth/UI/profile 상태 바인딩 + `API_BASE` 참조 주입형 전환(`App.tsx` helper 포함).
  - [x] 증적 갱신 완료: API 증적(`evidence/marketplace-formal-signup-feature-e2e-20260816-d0rerun.json`) 유지, D0 스모크 최종 통과(`evidence/device-d0-smoke-20260816-220106/summary.json`) 확인.
  - [x] 상태: 5.5 닫힘 조건 충족 유지(코드 치환 + API/서버 증적 + D0 통과 증적).

> Phase 5의 대규모 JSX/상태 추출은 13,610줄 모놀리스 특성상 **빅뱅 금지** — 기능별로 한 번에 하나씩,
> 매 추출 후 디바이스 회귀 검증을 거쳐 진행한다(승인된 플랜의 per-phase 검증 원칙).
> **[보류] VoIP S10 단방향(발신자 무음) 이슈** — 2폰 라이브에서 S10(발신, beyond1lteks)만 업링크가
> 디지털 무음 수준(`caller→callee` frames~30k, voiced~46, segs~2, mean_rms~98)으로 STT 세그먼트가
> 형성되지 않음. TAB(수신)→S10 방향은 정상(서버 STT 정규화로 rms→1800 부스트 + `interpret emit ja→ko`).
> 스피커폰/이어폰/블루투스 모두 동일 → 라우팅(AEC)만의 문제가 아니라 **S10 클라이언트 마이크 캡처 자체** 이슈로 추정.
> 시도: 서버 `media_bridge` uplink STT 게인 정규화(유지, 타 단말에 유효) + S10 마이크 제약
> `echoCancellation/noiseSuppression/autoGainControl=false` 실험 빌드 설치 → S10 무음 변화 없음 → 회귀 위험으로 **원복**.
> 결론: 서버측으로는 해결 불가. 후속으로 S10 단말의 WebRTC 오디오 소스/마이크 HW 레벨 단독 조사 필요(언어 표기·번역 경로는 정상으로 확인됨, 무관).

## Phase 7 — 오디오 세션 격리 CRITICAL (2026-07-09, build316 감사)
- [x] **7.x 요약** 오디오 세션 격리 핵심(7.1~7.5) 반영 완료: `voipSessionGuard`, `prepareForVoipSession`, PSTN lifecycle, `useAppVoiceCaptureLoop` 브리지, `song-mode` 레지스트리 정리.
- [x] 근거 문서: [`feature-separation-audio-isolation-audit-20260709.md`](./feature-separation-audio-isolation-audit-20260709.md)
- [ ] **7.6 잔여** 디바이스 재검증(대면 TTS + VoIP UI 회귀 패치 후) 대기.

## Phase 6 — 터미널/로그 분리 — 완료
- [x] **6.x(운영 로그 분리) 요약 완료**: 로그 태그/correlation 규칙, logcat/backend tail 스크립트, 프로세스 분리 문서화까지 닫힘.
- [x] 근거: `scripts/logs/tail_feature_logcat.ps1`, `scripts/logs/tail_feature_backend.ps1`, `scripts/logs/README.md`.

---

## 회귀 수용 기준 (매 Phase 후 필수)
- [x] **A. 육성(동일언어) 통화** 정상 — 회귀 코어 2라운드 PASS 유지
- [x] **B. 한↔일 통역 통화** 양방향 전달 정상 — 통역/VoIP 오케스트레이터 스위트 2라운드 PASS 유지
- [x] **C. 소리새 대화가 대면통역 결과창/음성으로 새지 않음**
- [x] **D. 음량** 회귀 없음
- [x] **E. 빌드/설치 후 크래시 0건**

근거(2026-08-16):
- `evidence/feature-separation-checklist-close-20260816-202529/summary.json` (회귀 코어 2연속 PASS 집계)
- `evidence/full-functional-validation-20260816-194753/summary.json` (기능별 종합 검증 집계)
- `evidence/feature-separation-checklist-close-20260816-202529/crash_scan.txt` (NO_CRASH_SIGNATURE_FOUND)
- 상세 라운드 로그(`mobile_core_round*.log`, `round*/mobile_core_tests.log`)는 상기 요약 산출물의 원본 증적로 보관.

---

*작성: 2026-06-23 · 전략 A+B · 단일-활성 계약.*
