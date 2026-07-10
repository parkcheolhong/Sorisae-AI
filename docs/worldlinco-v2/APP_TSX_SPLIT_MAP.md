# App.tsx 구조/seam 매핑 + 분리 계획

> 대상: `apps/mobile-nadotongryoksa/App.tsx` (**14,160줄**)
> 상태: **매핑 완료 / 구현 대기**. 모바일 god-file 분리는 디바이스 QA 동반 권장.

## 1. 매크로 구조 (라인 범위)

| 구간 | 라인 | 규모 | 성격 |
|---|---|---|---|
| **Imports** | 1–242 | ~242 | 이미 `src/features/*`·`src/components/*`·`src/screens/*`·`src/services/*` 다수 분리됨 |
| **모듈 헬퍼/상수/타입** | 243–1668 | ~1,425 | API 콜러·스토리지·딥링크 파서·오디오 재생·UI텍스트·색상 — **AppInner 바깥**(추출 친화적) |
| **`AppInner()`** | 1669–12120 | **~10,452** | 진짜 god-component. **useState/useRef 238개** |
| **`App()` 래퍼** | 12121–12127 | 7 | `<SafeAreaProvider><AppInner/></SafeAreaProvider>` |
| **`styles`** | 12129–14160 | **~2,032** | `StyleSheet.create`, 정적. 모듈 const(`C`,`GLOBAL_FONT_SCALE`)만 참조 |

## 2. 핵심 발견

- **AppInner state 238개**(useState/useRef): 섹션 간 상태 공유가 광범위 → **컴포넌트 단위 분해는 고위험**.
- 화면 전환은 단일 라우터가 아니라 **`activeRailSection: SectionRailKey | null`**(`chat`/`voip`/`song-mode`/`travel-booking`/home(front translation)) + 다수 모달 기반(L9154).
- 이미 "[기능 분리 Phase5.7]" 흔적(`SectionRailKey`/`SECTION_RAIL_ITEMS`/`buildSectionRailSelector` 분리, L303).
- 주요 풀스크린은 이미 외부 컴포넌트(`ChatRoomListScreen`/`ChatRoomScreen`/`SettingsScreen`/`FriendFolderScreen`/`FriendMapDiscoveryScreen`/`VoIPCallScreen`). AppInner은 **front translation surface + 각 섹션 패널 + 모달**을 인라인 렌더.

## 3. Seam 인벤토리 (위험도 등급)

### 🟢 LOW — 정적/순수, `tsc --noEmit`로 검증 가능 (디바이스 불필요)

| Seam | 현재 위치 | 타깃 | 비고 |
|---|---|---|---|
| **S1. styles** | 12129–14160 (~2,032) | `App.styles.ts` | StyleSheet 정적. `C`/`GLOBAL_FONT_SCALE` import. 단일 추출로 -2k줄 |
| **S2. 타입** | UserInfo/SignupPayload/UserProfileUpdatePayload/Voice*/SongFile*/Hybrid* 등 | `src/app/types.ts` | 순수 타입, 무위험 |
| **S3. 상수/UI텍스트** | UI_TEXT/getUiText/C/SECTION_TAB_COLORS/옵션배열(CATEGORY/RADIUS/VOICE_*) | `src/app/appConstants.ts` | 모듈 const, 무부작용 |
| **S4. 딥링크 파서** | parseAppEntryDeepLink(523)/parseIncomingVoipDeepLink(605) | `src/features/deeplink/` | 순수 함수 |

### 🟡 MEDIUM — 순수하지만 모듈 const(API_BASE 등) 의존, 호출부 다수

| Seam | 현재 위치 | 타깃 |
|---|---|---|
| **S5. Auth/Me API** | callLoginApi/callSignupApi/callSignup*Code/callMeApi/callUpdateMeApi (764–862) | `src/api/appAuthApi.ts` |
| **S6. 스토리지** | load/save/clearStoredAuthState, *ActiveVoipSession (863–957) | `src/services/authStorage.ts`·`voipSessionStorage.ts` |
| **S7. 예약/결제 API** | callNearbyPlacesApi/callBookingApi/call*Purchase*/call*Payment* (958–1087) | `src/api/appBookingApi.ts` |
| **S8. 송파일/보이스 API** | callCreateSongFileJob…callCreateVoicePreview (1234–1367) | `src/api/songVoiceApi.ts` |
| **S9. 오디오 재생** | playFaceTranslationOutput(1380)/stopFaceVoicePlayback(1368) | `src/features/face-conversation/facePlayback.ts` |
| **S10. 업데이트** | runApkInAppInstall(675)/checkForAppUpdate(704) | `src/features/app-update/` |

### 🔴 HIGH — AppInner 내부, 상태 238개 공유. **디바이스 QA 필수**

| Seam | 전략 |
|---|---|
| **S11. 섹션 패널** (song-mode/travel-booking/voip dock/chat) | **컴포넌트 분리보다 커스텀 훅 우선**: 응집 state 슬라이스를 `useSongFileController`/`useVoicePreviewController`/`useBookingController` 로 추출(렌더 트리 유지, 줄 수 감소) |
| **S12. Auth 모달/폼** | 11700+ 인라인 → 훅(`useAuthFormController`) + presentational 컴포넌트 |
| **S13. front translation surface** | 핵심 통역 루프. 가장 위험 — 최후순위 |

## 4. 단계별 계획 (제안)

- **Phase A (🟢 LOW, 즉시·tsc 검증)**: S1 styles → `App.styles.ts`. 단일 최대 효과(-2k줄), 무위험. 이어 S2/S3/S4.
  - ✅ **S1 + 테마 완료**: `C`/`SECTION_TAB_COLORS` → `src/app/appTheme.ts`, styles(2,031줄) → `App.styles.ts`(`C` import). App.tsx **14,160 → 12,106(-2,054)**. 검증: baseline `tsc --noEmit` 클린 → 추출 후도 클린(error 0), lint 0.
  - ✅ **S3 선행(appConstants) 완료**: 브랜딩/버전/스토리지키/딥링크경로/플래그/OCR디버그 상수 **27개** → `src/app/appConstants.ts`(`expo-constants`+`worldlincoBrand` import). 타입 의존이 있는 옵션배열(`CATEGORY_OPTIONS`/`VOIP_GENDER_OPTIONS`/`VOICE_*_OPTIONS`)은 S2 이후로 유보. App.tsx **12,106 → 12,059(-47)**. 검증: `tsc --noEmit` 클린(error 0), lint 0.
  - ✅ **S3 본체(UI_TEXT/getUiText) 완료**: 다국어 사전 `UI_TEXT` + `getUiText`(99줄) → `src/app/appUiText.ts`(`APP_FOOTER_BRAND(_KO)`←appConstants, `SUPPORTED_LANGUAGE_COUNT`←languageCatalog import). `UI_TEXT`는 getUiText 내부에서만 쓰여 App.tsx는 `getUiText`만 import. App.tsx **12,059 → 11,989(-70)**. 검증: `tsc --noEmit` 클린(error 0), lint 0.
  - ✅ **S2(타입) 완료**: 최상위 도메인 타입 22개(`VoipParticipantProfile`/`UserInfo`/`SignupPayload`/`AppEntryDeepLinkTarget`/`HybridGpsResult`/`SongFile*`/`Voice*` 등) → `src/app/appTypes.ts`(타입 전용 모듈). 외부 의존: `SectionRailKey`←sectionRegistry, `HybridGpsMode`←hybridGps, `LangCode`←languageCatalog. 내부 상호참조(`SongFileTimeline`→`SongFileTimelineSegment`, `VoicePreviewResponse`→`VoiceOutputScope`)는 라인 순서 보존으로 해소. App.tsx는 `import type { ... }`로 일괄 재import(전부 사용 중 — tsc unused 0). 코드 사이 산재한 22개 선언 개별 제거(161줄) + 이중 공백 18곳 정규화. App.tsx **11,989 → 11,811(-178)**. 검증: `tsc --noEmit` 클린(error 0), lint 0.
  - ✅ **S3 잔여(옵션 배열) 완료**: 타입 분리 후 의존 해소된 도메인 옵션 배열 5개(`CATEGORY_OPTIONS`/`RADIUS_OPTIONS`/`VOIP_GENDER_OPTIONS`/`VOICE_LICENSE_OPTIONS`/`VOICE_OUTPUT_SCOPE_OPTIONS`) → `src/app/appConstants.ts` append. 타입 import 추가: `SearchCategory`←travel-booking/types, `VoipGenderOption`←profileFormatters, `VoiceLicenseMode`/`VoiceOutputScope`←appTypes. App.tsx 기존 appConstants import에 5개 추가. 33줄 제거 + 공백 2곳 정규화. App.tsx **11,811 → 11,804(-7, 순수 33줄은 import 35줄로 상쇄)**. 검증: `tsc --noEmit` 클린(error 0), lint 0.
  - ✅ **S4(딥링크 파서) 완료**: 순수 함수 `parseAppEntryDeepLink`/`parseIncomingVoipDeepLink`(2개 사이의 무관 상수/주석은 App.tsx 잔류) → `src/app/appDeepLinks.ts`(신규). 의존: `AppEntryDeepLinkTarget`←appTypes, `CallInitResponse`(type)←voipCallClient, `parseSectionRailKey`←sectionRegistry, `getDefaultVoipTurnServers`/`normalizeTurnServers`←voipSignaling, 링크 경로 상수 5개←appConstants. App.tsx는 두 함수 import만 추가(잔존 import는 다른 호출처서 계속 사용 — tsc unused 0). App.tsx **11,804 → 11,698(-106)**. 검증: `tsc --noEmit` 클린(error 0), lint 0. **→ Phase A(LOW 위험·tsc 검증 가능) 종료.**
- **Phase B1 (컴포넌트 외부 비-React 함수 — tsc 검증 가능 마지막 안전 구간)**
  - 매핑: `AppInner`(1240행) 이전 모듈 레벨 선언 전수 조사 → 순수/부수효과 함수(훅 미사용) vs React 결합(잔류) 분류.
  - ✅ **G3 영속화** → `src/app/appStorage.ts`: AsyncStorage 인증/VoIP 세션 영속화 + 세션 술어 8개(`load/save/clearStoredAuthState`, `load/save/clearStoredActiveVoipSession`, `is(Stored|Runtime)AcceptedCalleeVoipSession`). 의존: AsyncStorage, `AUTH_STORAGE_KEY`/`ACTIVE_VOIP_CALL_STORAGE_KEY`←appConstants, `UserInfo`/`StoredActiveVoipSession`←appTypes, `SectionRailKey`←sectionRegistry.
  - ✅ **G1 REST API** → `src/app/appApiClient.ts`: 인증/마켓/여행/VoIP 콜 제어 13개(`requestEndVoipCall`, `fetchVoipCallResumeSnapshot`, `callLoginApi`, `callSignupApi`, `callSignupRequestCodeApi`, `callSignupConfirmApi`, `callMeApi`, `callUpdateMeApi`, `callNearbyPlacesApi`, `callBookingApi`, `callCreatePurchaseApi`, `callInitiatePaymentApi`, `callMyPurchasesApi`). 의존: `API_BASE`, `extractApiErrorMessage`, `resolveWorldLincoProjectId`, 다수 타입.
  - ✅ **G2 미디어 API** → `src/app/appMediaApi.ts`: 노래/음성 미디어 API + 공용 fetch 헬퍼 11개(`delay`, `parseApiResponse`, `callCreateSongFileJob`, `callSongFileJobStatus`, `callSongFileTimeline`, `callPatchSongFileSegment`, `callExportSongFileTimeline`, `callCreateVoiceConsent`, `callCreateVoiceProfile`, `callDeleteVoiceProfile`, `callCreateVoicePreview`). 의존: `DocumentPicker`, `API_BASE`, `LangCode`, SongFile/Voice 타입.
  - 처리: 함수 465줄 제거 + 공백 32곳 정규화. App.tsx에는 **잔존 참조되는 이름만** import(unused 방지). App.tsx **11,698 → 11,205(-493)**. 검증: `tsc --noEmit` 클린(error 0), lint 0.
  - ✅ **G4 업데이트 컨트롤러** → `src/app/appUpdateController.ts`: `runApkInAppInstall`/`checkForAppUpdate`(Alert/Toast 부수효과). 의존: `Alert`/`Platform`/`ToastAndroid`←react-native, AsyncStorage, `fetchLatestApkMetadata`/`isRemoteApkNewer`/`downloadAndInstallLatestApk`←app-update, 버전 상수←appConstants.
  - ✅ **G5 순수 헬퍼** → `src/app/appHelpers.ts`: `buildInstantDemoCredentials`(←`DEMO_SESSION_EMAIL_DOMAIN`)/`resolveVoipRemoteLanguageHint`(←`isSupportedLangCode`/`LangCode`).
  - ✅ **G6 대면통역 오디오** → `src/app/appFaceVoicePlayback.ts`: `stopFaceVoicePlayback`/`playFaceTranslationOutput`(서버 뉴럴 TTS→디바이스 TTS 폴백, ref를 인자로 수령). 의존: `React`(type)/`Speech`/`FileSystem`/`Audio`/`synthesizeSpeech`/`normalizeSpeakText`/`inferTtsLanguage`/`LANGS`/`FEATURE_IDS`/`API_BASE`.
  - 처리: 함수 257줄 제거 + 공백 5곳 정규화. 잔존 참조 이름만 import. App.tsx **11,205 → 10,979(-226)**. 검증: `tsc --noEmit` 클린(error 0), lint 0. **→ Phase B1 종료.**
  - **잔류 확정(B1 대상 아님)**: `translateChildrenDeep`+Text/TextInput 몽키패치 IIFE(React 결합), Firebase 부트스트랩(`ensureFirebaseDefaultApp`/`voipMessagingAdapter` — import-시 초기화 순서 민감), 에셋 require(`SKY_BG`/`LOGIN_MASCOT`), 도메인 타이밍/경로 상수(`AUTO_RELAY_*`/`TRANSLATION_REQUEST_TIMEOUT_MS`/`GPS_*`/`SONG_FILE_JOB_*`/`PENDING_INCOMING_RING_MAX_MS`/`GLOBAL_FONT_SCALE` — 필요 시 appConstants로 이관 가능하나 헬퍼 아님).
  - **다음: Phase B2 (렌더 분리) — 디바이스 QA 동반 필수.**
- **Phase B2 (🔴 렌더 분리, 디바이스 QA 동반)**: 설계는 `B2_RENDER_SPLIT_MAP.md`.
  - ✅ **B2-1 `TravelBookingSection` 완료(패스스루)**: 여행/예약 섹션 JSX 전체(inter-call 카드 중첩 포함, 내부 546줄)를 `src/features/travel-booking/TravelBookingSection.tsx`로 **바이트 동일** 이동. 정밀 매핑에서 inter-call(클러스터 H) 중첩 + `lat`/`lon`(GPS) · `itinerarySeedQuery`(음성) 공유가 드러나, 안전을 위해 **상태 소유권 불변(패스스루) + props 75개 주입** 방식 채택(동작 변화 0). 모듈 의존은 새 파일 직접 import. App.tsx **11,238 → 10,516(-722)**. 검증: `tsc --noEmit` 클린(props 전수 + noUnusedLocals 통과), lint 0. **디바이스 QA 대기**(여행→주변검색→지도→예약폼→결제 +일반통화).
  - *S2(타입)*: ~22개 타입을 `src/app/appTypes.ts` 로. 독립적이나 교차 타입(`LangCode`/`SectionRailKey`/`SearchCategory`/`CallInitResponse`) import 필요, 22개 지점 개별 이동.
- **Phase B (🟡 MEDIUM)**: S5–S10. 모듈 헬퍼를 `src/api`·`src/services`·`src/features` 로 이동, App.tsx는 import. 각 이동 후 `tsc --noEmit` + 스모크.
- **Phase C (🔴 HIGH, 디바이스 QA)**: S11–S13. **훅 추출 우선**(컴포넌트 분해 지양)으로 238 state를 슬라이스화. 각 슬라이스마다 디바이스 회귀(로그인/통역/예약/통화/송파일).

예상 효과: Phase A+B 만으로 App.tsx **~14.1k → ~10k**(styles 2k + 헬퍼 1.4k 제거), AppInner 자체는 Phase C에서 점진 축소.

## 5. 검증 전략

- **정적**: `cd apps/mobile-nadotongryoksa && npx tsc --noEmit` (각 단계 후).
- **스모크**: 기존 mobile `npm run test` 해당 시.
- **디바이스(Phase C)**: 로그인→통역→섹션레일(chat/voip/song/travel) 전환→통화→송파일 시나리오 수동 회귀.

## 6. 리스크

| 리스크 | 완화 |
|---|---|
| styles 동적 참조 누락 | 추출 후 `tsc` + `C`/`GLOBAL_FONT_SCALE` import 확인 |
| 헬퍼가 AppInner 클로저 참조(실은 모듈레벨이라 없음) | 모두 AppInner 바깥(243–1668) → 클로저 의존 0, 안전 |
| 훅 추출 시 effect 의존성/순서 변화 | 슬라이스 단위로 작게, deps 보존, 디바이스 회귀 |
| 238 state 상호참조 | Phase C 전 state 의존 그래프 별도 매핑 선행 |
