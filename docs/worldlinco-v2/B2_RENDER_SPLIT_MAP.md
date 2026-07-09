# App.tsx Phase B2 — 렌더 분리 사전 매핑 (읽기 전용 설계)

> 목적: `AppInner`의 state/effect 의존 그래프와 섹션레일별 렌더 서브트리 경계를 식별하고,
> 섹션을 `<XxxSection/>` 컴포넌트로 떼어내기 위한 **props 계약**을 설계한다.
> B1까지로 App.tsx는 **10,979줄**. B2는 stateful 영역이라 **tsc로 회귀를 못 잡고 디바이스 QA가 필수**.

## 0. 현재 해부 (B1 완료 시점)

| 항목 | 값 | 비고 |
|---|---|---|
| `AppInner` 시작 | L528 | 단일 거대 함수 컴포넌트 |
| `AppInner` return(JSX) 시작 | L8143 | 메인 `<ScrollView>` |
| `export default function App()` | L10981 | `AppInner`를 SafeArea/Provider로 감싸는 얇은 래퍼 |
| `useState` | ~150개 | L530–L1346 사이 집중 |
| `useRef` | ~50개 | 다수가 순환참조 회피용 late-bound 콜백 ref |
| `useEffect` | 63개 | |
| `useCallback`/`useMemo` 핸들러 | 다수 | 섹션 간 공유 |

**구조적 특징**: 무거운 로직은 이미 화면 컴포넌트로 추출됨 — 섹션 JSX는 대부분 "섹션 chrome + 위임 컴포넌트 wiring".
- `<ChatRoomListScreen>` (L8880), `<FriendMapDiscoveryScreen>` (L8870)
- `<VoIPCallScreen>` (L8944 활성통화 / L10172 프리뷰), `<VoipCallErrorBoundary>`
- `<TravelItineraryPanel>` (L9669)

## 1. 섹션 스위칭 모델

`activeRailSection: SectionRailKey | null` (L8013) 단일 상태에서 파생된 가시성 플래그가 렌더를 분기한다.

```
8015  isChatRailSectionVisible      = activeRailSection === 'chat'
8017  isVoipRailSectionVisible      = activeRailSection === 'voip' || hasPendingIncomingVoip
8018  isSongRailSectionVisible      = activeRailSection === 'song-mode'
8019  isTravelRailSectionVisible    = activeRailSection === 'travel-booking'
8106  isTranslateWorkspaceVisible   = isLoggedIn && activeRailSection === null
8027  isVoipRailLobbyVisible        = isVoipRailSectionVisible && showVoipTester && !voipCallInitResponse && !pendingIncomingVoipCall
8028  isVoipRailActiveCallVisible   = isVoipRailSectionVisible && !!voipCallInitResponse
```

전환 진입점: `handlePressSectionRail(key)` (하단 탭바 L10102~) + `setActiveRailSection(...)` 다수 호출처(딥링크/통화수락/공유 등 20+ 지점) → **이 오케스트레이션은 App에 잔류**.

## 2. 렌더 서브트리 경계 (메인 ScrollView 내부)

| 블록 | 라인(근사) | 가드 | 핵심 내용 / 위임 컴포넌트 |
|---|---|---|---|
| 번역 워크스페이스 | 8569–8795 | `isTranslateWorkspaceVisible` | 메인 번역 입력/결과/OCR/음성/대면통역 토글 |
| 채팅 허브 | 8795–8903 | `isChatRailSectionVisible` | 액션타일 + `FriendMapDiscoveryScreen` + `ChatRoomListScreen` |
| VoIP 잔류 배너 | 8905–8921 | `voipCallInitResponse && !isVoipRailSectionVisible` | 백그라운드 통화 복귀 배너 |
| VoIP 통화 호스트 | 8923–8958 | `voipCallInitResponse` | `VoipCallErrorBoundary` + `VoIPCallScreen`(활성) |
| VoIP 레일(로비/다이얼러) | 8960–9279 | `isVoipRailSectionVisible` | 다이얼러/테스터/수신 대기 |
| 노래 모드 | 9279–9526 | `isSongRailSectionVisible` | 송파일 업로드/자막/세그먼트 편집/내보내기 |
| 여행/예약 | 9526–10076 | `isTravelRailSectionVisible` | 카테고리/반경/`TravelItineraryPanel`/주변검색/지도/예약폼/결제 |
| 번역 워크스페이스(푸터) | 10077–10096 | `isTranslateWorkspaceVisible` | 앱정보/데이터출처 링크 |
| 하단 탭바 | 10100–10130 | 로그인&비통화 | `SECTION_RAIL_ITEMS` 탭 + 설정 |
| 소리새 FAB / 음성호출 칩 | 10132–10162 | 비통화 | 드래그 FAB + companion voice 토글 |
| 오버레이 모달군 | 10164–10970 | 각자 visible 상태 | VoIP 프리뷰, 데이터출처, 언어/국가 피커, 로그인 모달, 소리새 창 등 |

## 3. State 클러스터 (도메인별 — 분리 시 colocation 후보)

| 클러스터 | 대표 상태 | 소비 섹션 | colocation 가능성 |
|---|---|---|---|
| **A. 번역 코어** | `fromLang`/`toLang`/`inputText`/`resultText`/`loading`/`ocr*`/`engine`/`gpsCountryCode`/`gpsRegionHint`/`lat`/`lon`/`langPickerFor` | 번역 워크스페이스 + (다수 공유: voip/travel가 fromLang/toLang 참조) | **공유** — App 잔류 |
| **B. 인증/프로필** | `token`/`userInfo`/`showLogin`/`authModalMode`/`login*`/`signup*`/`demoSession*`/`biometric*`/`profile*`/`myPurchases*` | 로그인 모달 + 내정보 모달 | 모달 단위 분리 후보(B3) |
| **C. 디버그** | `lastUiProbeEvent`/`railDebug*`/`authDebug*` | 플로팅 디버그 | 분리 용이(저위험) |
| **D. VoIP** | `voipCallInitResponse`/`pendingIncomingVoipCall`/`voipPhone`/`voipInit*`/`voipProfileGender`/`voipLocalLangOverride` + 통화 ref 20+ | VoIP 호스트/레일/배너 | **부분** — 통화 ref·재개 로직 App 잔류, 다이얼러 UI만 분리 |
| **E. 채팅** | `selectedChatRoom`/`chatRefreshKey`/`groupComposerSignal`/`chatShare*`/`shareTarget*`/`pendingChatShare`/`showFriendFolder`/`showFriendMapDiscovery` | 채팅 허브 | colocation 양호(위임 컴포넌트 多) |
| **F. 여행/예약** | `nearby*`/`radiusM`/`nearbyCategory`/`selected*PlaceId`/`booking*`/`checkin/out`/`guests`/`roomCount`/`pay*`/`purchaseResult`/`itinerarySeed*` | 여행/예약 | **colocation 최적** — 거의 독립 |
| **G. 노래** | `songMode*`/`songSubtitles`/`songFile*` | 노래 모드 | **colocation 최적** — 거의 독립 |
| **H. 음성/대면/자동릴레이** | `autoVoiceModeEnabled`/`isVoiceRecording`/`voiceStt*`/`interCall*`/`face*`(ref 多)/`autoRelayDelayMs` | 번역 워크스페이스(대면통역) | 고결합 — App 잔류 |
| **I. 소리새/Companion** | `sorisae*`/`companion*`/`aiDisplayName*` | FAB/음성호출/소리새 창 | 오버레이 단위 분리 후보(B3) |
| **J. UI/글로벌** | `settingsTabOpen`/`globalSettings`/`voipPreviewOpen`/`insets` | 탭바/모달/배경 | App 잔류 |

## 4. 섹션별 props 계약 설계 (제안)

원칙: **섹션 전용 상태는 컴포넌트 내부로 colocate**, **공유 상태(번역 코어·인증·activeRailSection)만 props로 주입**, **late-bound ref는 그대로 전달**.

### 4.1 `<TravelBookingSection/>` (1순위 — 최저결합)
```ts
type TravelBookingSectionProps = {
  visible: boolean;                 // isTravelRailSectionVisible
  apiBase: string;                  // API_BASE
  token: string;
  fromLang: LangCode; toLang: LangCode;     // 공유(번역코어)
  gpsCountryCode: string; gpsRegionHint: string;
  lat: string; lon: string;         // GPS 좌표(번역코어와 공유)
  onRequireLogin: (source: string) => void; // renderSectionConnectionCard 게이트
  registerSectionLayout: (key, y: number) => void; // railSectionOffsetRef wiring
};
```
- colocate(내부 이동): `nearby*`, `radiusM`, `nearbyCategory`, `selected*PlaceId`, `booking*`, `checkin/out`, `guests`, `roomCount`, `bookingNote`, `pay*`, `purchaseResult`, `payUrl`, `itinerarySeed*`, `bookingSelectionNotice` + 관련 핸들러(`handleSearchNearby`/`handleBooking`/`handlePay`) + `callNearbyPlacesApi`/`callBookingApi`/`callCreatePurchaseApi`/`callInitiatePaymentApi`(이미 appApiClient).
- 위임: `<TravelItineraryPanel>` 그대로.
- **잔류 의존**: `fromLang`/`toLang`/`lat`/`lon`은 번역코어와 공유 → props 주입(읽기). 변경 필요 없음.

### 4.2 `<SongModeSection/>` (2순위)
```ts
type SongModeSectionProps = {
  visible: boolean;                 // isSongRailSectionVisible
  apiBase: string; token: string; userInfo: UserInfo | null;
  fromLang: LangCode; toLang: LangCode;
  onRequireLogin: (source: string) => void;
  onRequirePurchase: () => void;    // 건당 결제 게이트(L3228~)
  registerSectionLayout: (key, y) => void;
};
```
- colocate: `songMode*`, `songSubtitles`, `songFile*` + `callCreateSongFileJob`/`callSongFileJobStatus`/`callSongFileTimeline`/`callPatchSongFileSegment`/`callExportSongFileTimeline`(이미 appMediaApi) + 폴링 effect.
- **주의**: 음성 라이브 모드(`songModeEnabled` 토글이 메인 번역 경로와 얽힘 — L7100~) 일부는 번역 워크스페이스와 공유. 경계 정밀 확인 필요.

### 4.3 `<ChatHubSection/>` (3순위)
```ts
type ChatHubSectionProps = {
  visible: boolean; apiBase: string; token: string; userInfo: UserInfo | null;
  voipProfileGender: VoipGenderOption;
  voipAutoCallVoiceId: string | null;
  onAutoCallConsumed: () => void;
  onOpenChatRoom: (room: ChatRoomSummary) => void;       // handleOpenChatRoom
  onStartFriendVoiceCall: (friend) => void;              // → VoIP 오케스트레이션(App)
  onFriendAccepted: (...) => void;                       // handleFriendAcceptedFromDiscovery
  chatRefreshKey: number; groupComposerSignal: number;
  showFriendFolder: boolean; showFriendMapDiscovery: boolean;
  onPressFriendEntry: (kind) => void;
  onOpenFriendMapFromFolder: () => void;
  onOpenContactsDirectory: () => void;
  onRequireLogin: (source) => void;
  registerSectionLayout: (key, y) => void;
};
```
- **잔류 의존**: 친구→음성통화 시작은 VoIP 오케스트레이션을 건드리므로 콜백으로만 위임. 채팅 상태 일부(`chatRefreshKey`/`groupComposerSignal`)는 다른 진입점(공유 메시지)에서도 set → App 잔류 + props 주입.

### 4.4 `<VoipDialerSection/>` (4순위 — 최고결합, 신중)
- 분리 대상은 **다이얼러/로비 UI만**(L8960–9279). **활성 통화 호스트(L8923–8958)·잔류 배너·수신 폴링·세션 재개·20+ ref 오케스트레이션은 App 잔류**.
```ts
type VoipDialerSectionProps = {
  visible: boolean;                  // isVoipRailLobbyVisible
  voipPhone: string; setVoipPhone: (v) => void;
  voipInitLoading: boolean; voipInitError: string; voipStatusMessage: string;
  voipProfileGender: VoipGenderOption;
  effectiveVoipSourceLang: LangCode; effectiveVoipTargetLang: LangCode;
  onStartCall: (...) => void;        // App 오케스트레이션 콜백
  onOpenPhoneDialer: () => void; onOpenContacts: () => void;
  onOpenLangModal: () => void;
  registerSectionLayout: (key, y) => void;
};
```

### 4.5 공통 헬퍼 props
- `registerSectionLayout(key, y)`: 현재 `railSectionOffsetRef.current[key] = y` + `scrollToRailSection` wiring(onLayout)을 콜백 1개로 추상화.
- `onRequireLogin(source)`: `renderSectionConnectionCard(...)`(L1115) 게이트를 콜백화(또는 공용 `<SectionLoginGate>` 컴포넌트로 별도 추출).

## 5. App에 반드시 잔류 (분리 금지/지연)

- `activeRailSection` 상태 + `handlePressSectionRail` + 20+ `setActiveRailSection` 오케스트레이션.
- VoIP 통화 생명주기: `voipCallInitResponse`/`pendingIncomingVoipCall` + presence/audit 소켓 ref + 수신 폴링·세션 재개·딥링크 라우팅 effect.
- late-bound 콜백 ref(순환참조 회피): `handleLogoutRef`/`stopVoiceInputRef`/`scheduleFaceConversationRestartRef`/`wakeCompanionVoiceCallNowRef`/`activeRailSectionRef`.
- 번역 코어 상태(다수 섹션이 읽음) + 대면통역/자동음성(클러스터 H, 고결합).
- 전역 Text/TextInput 몽키패치, Firebase 부트스트랩, 배경/탭바/FAB.

## 6. 분리 순서 · 리스크 · QA 매핑

| 순서 | 컴포넌트 | 결합도 | 주 리스크 | 디바이스 QA 시나리오 |
|---|---|---|---|---|
| 1 | `TravelBookingSection` ✅(패스스루 추출 완료, tsc 그린) | 실측 높음 | inter-call 카드 중첩(클러스터 H) · GPS 좌표/음성seed 공유 | 여행→주변검색→지도→예약폼→결제 (+일반통화 모드) |
| 2 | `SongModeSection` ✅(패스스루 추출 완료, tsc 그린·jest 316) | 낮음 | 라이브 송모드와 번역경로 경계 | 노래모드→파일업로드→자막→세그먼트편집→내보내기 |
| 3 | `ChatHubSection` ✅(패스스루 추출 완료, tsc 그린·jest 316) | 중간 | 친구→통화 콜백, 공유 메시지 진입 | 채팅→방목록→그룹→친구찾기→번역공유→친구통화 |
| 4 | `VoipDialerSection` | 높음 | 통화 ref 오케스트레이션 누수 | 다이얼러→발신→수신→백그라운드복귀→종료 |
| (B3) | `LoginModal`/`MyInfoModal`/`SorisaeWindow`/피커 모달군 | 중간 | 인증 상태 전파 | 로그인/회원가입/프로필/소리새 호출 |

**공통 회귀(매 분리 후 필수)**: 로그인 → 번역 → 섹션전환(chat/voip/song/travel) → 통화 → 송파일.

### 분리 절차(섹션 1개당)
1. 섹션 전용 state/handler/effect를 `src/features/<section>/<Section>.tsx`로 colocate 이동.
2. 공유 상태·콜백은 props 주입(위 계약).
3. `tsc --noEmit` 그린 + `npm run test`(스모크).
4. **Android 빌드 + 디바이스 수동 회귀**(해당 시나리오 + 공통 회귀).
5. 통과 시 커밋. 실패 시 즉시 롤백(섹션 단위라 격리됨).

## 7. 권장
- B2는 **섹션 1개 = 1 PR/커밋 = 1 디바이스 QA 패스**로 진행(되돌리기 용이).
- 1순위 `TravelBookingSection`을 파일럿으로 절차/계약을 검증한 뒤 동일 패턴 반복.
- 모달군(B3)은 렌더 분리와 독립적이므로 B2 이후 별도 트랙.

## 8. 파일럿 실행 결과 — `TravelBookingSection` (완료)

정밀 매핑에서 본 문서 §3·§4.1의 "최저결합 + colocation" 가정과 **다른 실제 결합**이 드러나, 안전을 위해 **패스스루(passthrough) 추출**로 진행했다(사용자 승인).

**발견된 결합(가정과 차이):**
- inter-call("예약 섹션 일반 통화 모드") 카드가 여행 블록 안에 **물리적으로 중첩**(`여행 예약 레일` View 내부) → 클러스터 H(음성/자동릴레이) 소속, App effect(L7658/7681/7745/7783)와 고결합.
- `lat`/`lon`은 GPS 자동감지 effect(L6206–6207)가 set → 공유 상태.
- `itinerarySeedQuery`는 음성 전사 경로(L7020)에서 set → 공유 상태.

**채택 방식(패스스루):**
- 여행 JSX 전체(inter-call 카드 포함, 내부 546줄)를 `src/features/travel-booking/TravelBookingSection.tsx`로 **바이트 동일** 이동.
- **상태 소유권 불변** — 모든 참조값을 props(75개)로 주입. → 리렌더/타이밍/동작 변화 0.
- 모듈 레벨 의존(styles·C·CATEGORY/RADIUS_OPTIONS·SUPPORTED_LANGUAGE_COUNT·API_BASE·formatDistance·formatAutoRelayDelayLabel·TravelItineraryPanel·RN 프리미티브)은 새 파일에서 직접 import.

**검증:** `tsc --noEmit` 그린(75개 props 전수 + `noUnusedLocals`로 미사용 0 확인), 린트 0. App.tsx **11,238 → 10,516줄**(−722).

**후속(QA 통과 후 선택):** inter-call 카드를 별도 위치/컴포넌트로 들어낸 뒤 여행 전용 state를 colocate하면 props 수를 크게 줄일 수 있음(현 패스스루는 안전·동작불변 우선). 2~4순위 섹션은 colocation 가능성을 개별 재실측 후 진행.

## 9. 순서 2 실행 결과 — `SongModeSection` (완료)

travel 파일럿과 동일한 **패스스루 추출**로 진행(상태 소유권 App 잔류, JSX 바이트 동일 이동).

- 추출 범위: 노래 모드 레일 JSX 전체(`isSongRailSectionVisible` 가드 내부 `<View>` 244줄) → `src/features/song/SongModeSection.tsx`.
- props 계약: **48개**(공유/노래·보이스 전용 상태·핸들러·setter 전수 주입). 가드(`isSongRailSectionVisible`)·`setActiveRailSection` 오케스트레이션은 App 잔류.
- 모듈 의존(새 파일 직접 import): `styles`·`MONETIZATION_PLAN_CONFIG`/`MonetizationPlanKey`·`VOICE_LICENSE_OPTIONS`/`VOICE_OUTPUT_SCOPE_OPTIONS`·`resolveSongFileTargetLang`/`normalizeSongFileLang`·`formatSongFileTime`·`LangCode`·`SectionRailKey`·노래/보이스 타입(appTypes)·RN 프리미티브.
- **주의 해소**: §4.2의 "라이브 송모드 ↔ 번역경로 경계" 우려는 패스스루로 자동 회피 — `songModeEnabled` 토글 effect/핸들러는 모두 App에 잔류, 섹션은 렌더만 위임하므로 라이브 경로 변화 0.
- 검증: `tsc --noEmit` 0(48 props 전수 + `noUnusedLocals`), 린트 0, jest 37스위트/316 통과. App.tsx **10,516 → 10,324줄**(−192).
- **디바이스 QA(대기)**: 노래모드→파일업로드→자막→세그먼트편집→내보내기 + 공통 회귀(로그인→번역→섹션전환→통화→송파일). 빌드/설치는 프로덕션 앱 교체가 필요해 별도 타이밍.

## 10. 순서 3 실행 결과 — `ChatHubSection` (완료)

travel·song과 동일한 **패스스루 추출**(상태 소유권 App 잔류, JSX 바이트 동일 이동).

- 추출 범위: 채팅+친구 허브 레일 JSX 전체(`isChatRailSectionVisible` 가드 내부 `<View>` 107줄) → `src/features/chat/ChatHubSection.tsx`.
- props 계약: **23개**. 친구→통화 시작(`handleStartFriendVoiceCall`)·친구 수락(`handleFriendAcceptedFromDiscovery`)·방 열기(`handleOpenChatRoom`)는 §4.3 설계대로 **콜백 위임**(VoIP/공유 오케스트레이션은 App 잔류). 로그인 게이트 카드는 `renderSectionConnectionCard` **render-prop**으로 주입(내부에서 demoSession 상태 다수 클로저 → App 잔류 필수).
- 모듈 의존(새 파일 직접 import): `styles`·`API_BASE`·`UserInfo`·`SectionRailKey`·`resolveDiscoveryGenderFromProfile`/`VoipGenderOption`·`ChatRoomListScreen`·`ChatRoomSummary`·`FriendMapDiscoveryScreen`·`Friend`/`AcceptedFriendActionPayload`·RN 프리미티브.
- 검증: `tsc --noEmit` 0(23 props + `noUnusedLocals`), 린트 0, jest 37스위트/316 통과. App.tsx **10,324 → 10,242줄**(−82).
- **디바이스 QA(대기)**: 채팅→방목록→그룹→친구찾기→번역공유→친구통화 + 공통 회귀. travel·song과 함께 일괄 검증.

> 누적: B2 순서 1·2·3(`Travel`/`Song`/`ChatHub`) 패스스루 추출 완료. App.tsx **11,238 → 10,242줄**(−996). 남은 순서 4 `VoipDialerSection`(최고결합 — 통화 ref 오케스트레이션 누수 위험, 신중).
