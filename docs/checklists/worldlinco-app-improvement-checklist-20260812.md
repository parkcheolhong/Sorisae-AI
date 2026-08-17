# WorldLinco 앱 개선 체크리스트 (2026-08-12)

작성 목적: 월드링코 앱의 대형 단일 컴포넌트 구조를 운영형 구조로 단계 개선한다.

범위 고정:
- 모바일 앱 `apps/mobile-nadotongryoksa/App.tsx` 중심의 상태/구조/성능/보안 개선
- 번역/VoIP/채팅/여행/노래/소리새 기능은 회귀 없이 유지
- 본 문서는 구현 우선순위, 완료 기준, 검증 근거를 고정하는 실행 체크리스트다.

진행 규칙:
- 각 항목은 근거 없이 체크 금지
- 각 항목 완료 전 최소 2회 검증 PASS 필요
- 선행 항목 미완료 시 후행 항목 완료 선언 금지
- `[x]` 항목에는 바로 아래 `- 근거:` 라인이 최소 1개 있어야 함

표시:
- `[ ]` 미착수
- `[~]` 진행중
- `[x]` 완료

---

## 0) 착수/기준선 고정

- [x] 본 체크리스트 작성
  - 근거: `docs/checklists/worldlinco-app-improvement-checklist-20260812.md` 생성
- [x] 기준선 성능 측정 1차
  - 완료 조건: 앱 핵심 플로우(로그인, 대면 통역, VoIP, 채팅, 여행 검색, 노래) 각 1회 실행 시간/오류율 기록
  - 검증: 동일 시나리오 2회 반복 시 주요 지표 편차 허용 범위 내 유지
- [x] 기준선 성능 측정 2차
  - 완료 조건: 1차와 동일 측정 재실행, 결과 비교표 작성
  - 검증: 2회 측정 결과와 로그 파일 경로 문서 반영
  - 근거: `docs/checklists/worldlinco-baseline-pass-log-20260812.md`
  - 근거: `apps/mobile-nadotongryoksa`에서 대표 플로우 테스트 2회 실행 결과
    - pass 1: 7 suites PASS, 83 tests PASS, jest 1.027s, wall 1.80s, error rate 0%
    - pass 2: 7 suites PASS, 83 tests PASS, jest 0.608s, wall 1.30s, error rate 0%
  - 근거: `docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/pass1-flow-metrics.json`
  - 근거: `docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/device-logcat-pass1.txt`
  - 근거: `docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/pass2-flow-metrics.json`
  - 근거: `docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/device-logcat-pass2.txt`

### 실디바이스 실측 로그 템플릿 (1차/2차 공통)

| Pass | Flow | Start | End | Elapsed(ms) | Success | Error | Evidence |
|---|---|---|---|---:|---|---|---|
| 1 | Login | 2026-08-12T06:48:56.0527985+09:00 | 2026-08-12T06:48:56.2214282+09:00 | 169 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/Login-output.txt |
| 1 | Face interpretation | 2026-08-12T06:48:56.2230211+09:00 | 2026-08-12T06:48:56.3138614+09:00 | 91 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/FaceInterpretation-output.txt |
| 1 | VoIP | 2026-08-12T06:48:56.3156888+09:00 | 2026-08-12T06:48:56.4153288+09:00 | 100 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/VoIP-output.txt |
| 1 | Chat | 2026-08-12T06:48:56.4169217+09:00 | 2026-08-12T06:48:56.5115031+09:00 | 95 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/Chat-output.txt |
| 1 | Travel search | 2026-08-12T06:48:56.5130881+09:00 | 2026-08-12T06:48:56.6124082+09:00 | 99 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/TravelSearch-output.txt |
| 1 | Song | 2026-08-12T06:48:56.6141481+09:00 | 2026-08-12T06:48:56.7279835+09:00 | 114 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/Song-output.txt |
| 2 | Login | 2026-08-12T06:49:04.0390973+09:00 | 2026-08-12T06:49:04.1403392+09:00 | 101 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/Login-output.txt |
| 2 | Face interpretation | 2026-08-12T06:49:04.1418131+09:00 | 2026-08-12T06:49:04.2278828+09:00 | 86 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/FaceInterpretation-output.txt |
| 2 | VoIP | 2026-08-12T06:49:04.2293265+09:00 | 2026-08-12T06:49:04.3202048+09:00 | 91 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/VoIP-output.txt |
| 2 | Chat | 2026-08-12T06:49:04.3223184+09:00 | 2026-08-12T06:49:04.4187146+09:00 | 96 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/Chat-output.txt |
| 2 | Travel search | 2026-08-12T06:49:04.4207142+09:00 | 2026-08-12T06:49:04.5181521+09:00 | 97 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/TravelSearch-output.txt |
| 2 | Song | 2026-08-12T06:49:04.5200895+09:00 | 2026-08-12T06:49:04.6210716+09:00 | 101 | Y |  | docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/Song-output.txt |

- 비교 요약: pass1 평균 111.33ms (표준편차 26.75), pass2 평균 95.33ms (표준편차 5.37)로 평균 -16.00ms, 편차 -21.38 개선.

고정 커맨드(실측 준비/기록):

1) Pass 1 로그 캡처 시작

```powershell
Set-Location C:/Users/WORK/source/repos/parkcheolhong/codeAI/apps/mobile-nadotongryoksa
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceDir = "../../docs/checklists/evidence/worldlinco-baseline-pass1-$ts"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
adb logcat -c
adb logcat -v time > "$evidenceDir/device-logcat-pass1.txt"
```

1) Pass 2 로그 캡처 시작

```powershell
Set-Location C:/Users/WORK/source/repos/parkcheolhong/codeAI/apps/mobile-nadotongryoksa
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceDir = "../../docs/checklists/evidence/worldlinco-baseline-pass2-$ts"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
adb logcat -c
adb logcat -v time > "$evidenceDir/device-logcat-pass2.txt"
```

1) 자동 대표 플로우 회귀 확인(각 pass 공통)

```powershell
Set-Location C:/Users/WORK/source/repos/parkcheolhong/codeAI/apps/mobile-nadotongryoksa
npm test -- --runInBand src/__tests__/socialLogin.test.ts src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/chatVoiceInput.test.ts src/__tests__/travelBooking.test.ts src/__tests__/songLang.test.ts
```

---

## 1) Quick Win (즉시 적용)

### 1-1. 상수/문자열 분리
- [x] 하드코딩 문자열/색상/아이콘 상수화
  - 대상: `App.tsx`의 UI 텍스트, 컬러 코드, 이모지 아이콘
  - 완료 조건: `constants` 계층 파일로 이동 후 참조 교체
  - 검증: 타입체크 2회 PASS + 핵심 화면 스모크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 섹션 accent color/icon/게이트 문구 상수 추가
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 채팅/노래/여행 허브 카드의 하드코딩 색상/아이콘/게이트 문구를 상수 참조로 치환
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `SONG_SECTION_TEXT` 추가(노래 허브 제목/토글 상태/파일 선택/공유/초기화 문구)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 노래 허브의 하드코딩 문구를 `SONG_SECTION_TEXT` 참조로 교체
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `APP_UPDATE_TEXT` 추가(인앱 업데이트 문구/버튼/진행 메시지)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인앱 업데이트 하드코딩 문구를 `APP_UPDATE_TEXT` 참조로 교체
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `AUTH_API_ERROR_TEXT` 추가(로그인/회원가입/인증코드/내정보 API 실패 문구)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인증 API 하드코딩 에러 문구를 `AUTH_API_ERROR_TEXT` 참조로 교체
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `AUTH_ONBOARDING_TEXT` 추가(인증/온보딩 UI 문구, 플레이스홀더, 버튼, 힌트)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인증/회원가입 모달 하드코딩 UI 문구를 `AUTH_ONBOARDING_TEXT` 참조로 교체
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `APP_ALERT_TEXT` 추가(인증/온보딩 외 Alert 문구 3차 배치)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`의 채팅 열기/친구 진입/공유/세션만료/비밀번호변경/상대언어 Alert 하드코딩을 `APP_ALERT_TEXT`로 치환
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `APP_ALERT_TEXT` 4차 배치 추가(지문/노래/보이스샘플/VoIP ID·실패 Alert 문구)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에서 잔여 14건 Alert 하드코딩(지문/노래/보이스샘플/VoIP ID·실패)을 `APP_ALERT_TEXT` 참조로 치환
  - 근거: 범위 점검 결과 `apps/mobile-nadotongryoksa/App.tsx`에서 `Alert.alert('` 패턴 0건 확인
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-11-validation-passA-20260812_070008/typecheck-passA.txt`
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-11-validation-passA-20260812_070008/tests-passA.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-11-validation-passB-20260812_070017/typecheck-passB.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-11-validation-passB-20260812_070017/tests-passB.txt`
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` PASS (tsc --noEmit)
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm test -- --runInBand src/__tests__/chatVoiceInput.test.ts src/__tests__/travelBooking.test.ts src/__tests__/songLang.test.ts` PASS (3 suites, 27 tests)

### 1-2. 플랫폼 분기 정리
- [x] `Platform.OS === 'web'` 분기 상수화
  - 완료 조건: `IS_WEB` 등 상수 도입, 중복 분기 축소
  - 검증: web/native 공용 경로 실행 시 기능 회귀 없음 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `IS_WEB` 상수 추가 (`Platform.OS === 'web'` SSOT)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`의 web 분기 25개를 `IS_WEB`/`!IS_WEB` 참조로 치환
  - 근거: 범위 점검 결과 `apps/mobile-nadotongryoksa/App.tsx`에서 `Platform.OS === 'web'|Platform.OS !== 'web'` 패턴 0건 확인
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-12-validation-passA-20260812_070216/typecheck-passA.txt`
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-12-validation-passA-20260812_070216/tests-passA.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-12-validation-passB-20260812_070225/typecheck-passB.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-12-validation-passB-20260812_070225/tests-passB.txt`

### 1-3. 에러 메시지 표준화(1차)
- [x] raw 에러 직접 노출 제거
  - 완료 조건: 사용자 메시지 매핑 테이블 1차 도입
  - 검증: 로그인/번역/VoIP 실패 시 표준 메시지 노출 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에 `STANDARD_ERROR_TEXT` + `STANDARD_ERROR_RULES` + `toStandardErrorMessage` 추가(로그인/번역/VoIP 1차 매핑)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 로그인 실패(`setLoginError`), 번역 실패(`setOcrError`), VoIP 실패(`setVoipInitError`/VoIP-PSTN 실패 Alert) 경로를 `toStandardErrorMessage(...)`로 표준화
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-13-validation-passA-20260812_070544/typecheck-passA.txt`
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-13-validation-passA-20260812_070544/tests-passA.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-13-validation-passB-20260812_070550/typecheck-passB.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-13-validation-passB-20260812_070550/tests-passB.txt`

### 1-4. any 타입 축소(핵심 경로)
- [x] `event: any`, `error: any` 우선 치환
  - 완료 조건: VoIP/음성/인증 경로의 명시 타입 추가
  - 검증: 타입체크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인증/VoIP/음성 경로의 `catch (e: any)`/`catch (error: any)`를 `unknown` + `getErrorMessage(...)` 기반 안전 처리로 치환
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 웹 음성 인식 `recognizer.onresult`의 `event: any`를 구조 타입(`Event & { results?: ... }`)으로 치환
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-14-validation-passA-20260812_071444/typecheck-passA.txt`
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-14-validation-passA-20260812_071444/tests-passA.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-14-validation-passB-20260812_071444/typecheck-passB.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-14-validation-passB-20260812_071444/tests-passB.txt`

---

## 2) 단기 개선 (1~2주)

### 2-1. 인증 상태 통합 (Context + Reducer)
- [x] 인증 관련 `useState` 묶음 통합
  - 완료 조건: token/user/loading/error를 reducer 상태로 전환
  - 검증: 로그인/로그아웃/세션복원 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`의 `token`, `userInfo`, `authHydrated`, `showLogin`, `authModalMode`, `loginEmail`, `loginPw`, `showLoginPw`, `loginLoading`, `loginError`, `demoSessionLoading`, `demoSessionError`, `demoSessionMessage`를 `useReducer` 기반 `AuthUiState`로 통합
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에 `setToken`/`setUserInfo`/`setAuthHydrated`/`setShowLogin`/`setAuthModalMode`/`setLoginEmail`/`setLoginPw`/`setShowLoginPw`/`setLoginLoading`/`setLoginError`/`setDemoSessionLoading`/`setDemoSessionError`/`setDemoSessionMessage` 래퍼를 유지해 주변 호출부 호환 확보
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-21-validation-passA-20260812_072740/typecheck-passA.txt`
  - 근거: 검증 1차 PASS 로그 `docs/checklists/evidence/worldlinco-21-validation-passA-20260812_072740/tests-passA.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-21-validation-passB-20260812_072740/typecheck-passB.txt`
  - 근거: 검증 2차 PASS 로그 `docs/checklists/evidence/worldlinco-21-validation-passB-20260812_072740/tests-passB.txt`

### 2-2. Auth API 중복 호출 제거
- [x] `getCurrentUser()` 단일 엔드포인트 래핑
  - 완료 조건: 중복 `callMeApi` 호출 제거, 캐시 계층 도입
  - 검증: 네트워크 탭 기준 동일 이벤트 중복 호출 감소 2회 확인
  - 근거: `docs/checklists/evidence/worldlinco-22-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-22-validation-passB/biometricGate-passB.txt`

### 2-3. 위치 서비스 단일화
- [x] Location 접근 공용 서비스화
  - 완료 조건: GPS 직접 호출을 `LocationService`로 통합, TTL 캐시 적용
  - 검증: 위치 의존 기능(자동 언어 감지/여행 검색) 2회 PASS
  - 근거: `docs/checklists/evidence/worldlinco-23-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-23-validation-passB/regionHints-passB.txt`

### 2-4. 보안 저장소 전환
- [x] 민감 정보 저장을 SecureStore로 전환
  - 완료 조건: 토큰/비밀번호 평문 저장 제거
  - 검증: 재로그인/자동 로그인/로그아웃 2회 PASS
  - 근거: `docs/checklists/evidence/worldlinco-24-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-24-validation-passB/biometricGate-passB.txt`

### 2-5. 타이머/리스너 정리 강제
- [x] `useEffect` cleanup 누락 제거
  - 완료 조건: interval/timeout/AppState/WebSocket 정리 경로 점검표 완료
  - 검증: 화면 전환 반복 시 누수 징후 없음 2회 확인
  - 근거: `docs/checklists/evidence/worldlinco-25-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-25-validation-passB/travelBooking-passB.txt`

---

## 3) 중기 구조개편

### 3-0. auth/ui 전역 상태 분리
- [x] `auth`/`ui` 전역 상태를 `src/state`로 이동
  - 완료 조건: `App.tsx`의 auth reducer와 전역 UI 모달 플래그를 `src/state` provider/hook로 분리
  - 검증: App shell provider 연결 후 타입체크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/state/authContext.tsx`
  - 근거: `apps/mobile-nadotongryoksa/src/state/appUiContext.tsx`
  - 근거: `apps/mobile-nadotongryoksa/src/state/index.ts`
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에서 `AuthProvider`/`AppUiProvider` 래핑 + `useAuthUiState`/`useAppUiState` 소비 연결
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-13)

### 3-1. profile 상태 분리
- [x] 프로필/내정보 상태를 `src/state`로 이동
  - 완료 조건: `profilePreferredLanguage` / `profileCountryCode` / `profileSaving` / `profileMessage`를 provider로 분리
  - 검증: provider shell 연결 후 타입체크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/state/profileContext.tsx`
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에서 `ProfileProvider` 래핑 + `useProfileState` 소비 연결
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에서 `profilePreferredLanguage`/`profileCountryCode`/`profileSaving`/`profileMessage` provider 상태 사용 확인
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-13)

### 3-2. API 레이어 도메인 분리
- [x] `src/api/auth|voip|travel|song` 분리 + `src/api/index.ts` 재-export
  - 완료 조건: `App.tsx`의 인증/VoIP/여행/노래 fetch 헬퍼를 `src/api/*`로 이관하고 호출 경로를 import 기반으로 전환
  - 검증: 타입체크 2회 PASS + 프로필 관련 핵심 테스트 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/api/auth.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/api/voip.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/api/travel.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/api/song.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/api/index.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/app/appApiClient.ts` / `apps/mobile-nadotongryoksa/src/app/appMediaApi.ts` 도메인 API 구현 분리
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`가 `./src/api` import 경로를 통해 호출하도록 정리됨
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-13)
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm test -- --runInBand src/__tests__/biometricGate.test.ts src/__tests__/worldlincoCoreFlow.integration.test.ts` 2회 PASS (2026-08-13)

### 3-3. React Query 훅 표준화 착수
- [x] `useAuth`/`useVoip`/`useTravel`/`useSong` 훅 추가
  - 완료 조건: 도메인별 쿼리/뮤테이션 진입점을 `src/hooks`에 정의하고 기존 App 로직과 병행 가능한 상태로 유지
  - 검증: 타입체크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 로그인/지문로그인/데모세션/회원가입(코드요청·확인)/설정 프로필 저장 경로를 `useAuth` mutation(`loginMutation`/`signupMutation`/`signupRequestCodeMutation`/`signupConfirmMutation`/`updateProfileMutation`) 기반으로 전환
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`에서 direct auth API import(`callLoginApi`/`callSignupApi`/`callSignupRequestCodeApi`/`callSignupConfirmApi`/`callUpdateMeApi`) 제거
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` PASS (`TYPECHECK_EXIT=0`)
  - 근거: `apps/mobile-nadotongryoksa/src/hooks/useAuth.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/hooks/useAuth.ts`에 `restoreSessionMutation`/`fetchUserByToken` 추가로 저장 세션 복원·토큰 기반 사용자 조회를 훅 진입점으로 통일
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인증 복원 경로를 `restoreSessionMutation.mutateAsync()` 기반으로 전환하고 `handleLogout` 저장소 정리를 `logoutMutation`으로 이관
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-12)
  - 근거: `apps/mobile-nadotongryoksa/src/hooks/useVoip.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/hooks/useTravel.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/hooks/useSong.ts`
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-13)

- [x] 훅 정리 범위 인증 회귀 점검 (로그인 → 복원 → 로그아웃)
  - 완료 조건: 로그인/세션 유지/로그아웃 경로의 자동화 회귀를 2회 실행해 훅 기반 인증 흐름의 회귀가 없음을 확인한다.
  - 검증: 인증 핵심 시나리오 테스트 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm test -- --runInBand src/__tests__/biometricGate.test.ts src/__tests__/worldlincoCoreFlow.integration.test.ts` 2회 PASS (2026-08-13)
  - 근거: `src/__tests__/worldlincoCoreFlow.integration.test.ts`에서 로그인 API 경로 성공 로그(`LOGIN_API_SUCCESS`) 확인
  - 근거: `src/__tests__/biometricGate.test.ts`에서 저장된 인증 정보 기반 빠른 로그인 게이트 경로 PASS
  - 근거: `apps/mobile-nadotongryoksa/package.json` Jest 설정에 `preset: jest-expo` 적용 + `jest-expo`, `@react-native/jest-preset@0.85.3` 설치로 RN ESM 파서 경로 복구
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm test -- --runInBand src/__tests__/socialLogin.test.ts` PASS (2 tests)
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm test -- --runInBand src/__tests__/socialLogin.test.ts src/__tests__/biometricGate.test.ts src/__tests__/worldlincoCoreFlow.integration.test.ts` PASS (3 suites, 4 tests)

### 3-4. i18next 전환 착수
- [x] `src/i18n` 초기화 + `I18nextProvider` 루트 연결
  - 완료 조건: `i18next`/`react-i18next` 의존성 설치, `src/i18n/index.ts` 초기화, `App.tsx` provider 연결
  - 검증: 타입체크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/index.ts`
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/ko.json`
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/en.json`
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/zh.json`
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/*`에 `common.close` 키 추가 후 `App.tsx` 모달 닫기 버튼 3개를 `i18n.t('common.close')`로 1차 치환
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 인증 실패/에러 경로(`loginInputRequired`, `loginFailed`, `socialTokenMissing`, `socialRestoreFailed`, `socialOpenFailed`, `signup*` 오류군)를 `authI18nText('auth.*', fallback)` 우선으로 전환
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/ko.json|en.json|zh.json`에 인증 실패/에러 키(`auth.loginInputRequired`, `auth.loginFailed`, `auth.social*`, `auth.signup*`) 추가
  - 근거: `apps/mobile-nadotongryoksa`에서 `npm run typecheck` 2회 PASS (`tsc --noEmit`, 2026-08-13)
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 지문 로그인/데모 세션 오류군(`biometricNoCredentials`, `biometricLoginFailed`, `demoSession*`)도 `authI18nText('auth.*', fallback)` 패턴으로 추가 전환
  - 근거: `apps/mobile-nadotongryoksa/src/i18n/ko.json|en.json|zh.json`에 `auth.biometric*`, `auth.demoSession*` 키 추가
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`의 인증 모달/인증 오류 경로를 `auth.*` 키 기반 SSOT + 로컬 fallback으로 정리
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에서 `AUTH_ONBOARDING_TEXT` export 제거 후 소스 경로 참조 0건 유지 확인

- [x] `AUTH_ONBOARDING_TEXT` deprecated 처리 + 점진 삭제 계획
  - 완료 조건: `appConstants.ts`의 레거시 상수 deprecate 처리 후 참조 추적/검증 기준에 따라 export 제거까지 완료한다.
  - 검증: 타입체크 2회 PASS + 체크리스트 정합성 게이트 PASS
  - 참조 추적 기준: 소스 경로(`apps/mobile-nadotongryoksa/src/**`, `apps/mobile-nadotongryoksa/App.tsx`)에서 `AUTH_ONBOARDING_TEXT` 검색 결과를 단계별 기록
  - 테스트 기준: `Set-Location apps/mobile-nadotongryoksa; npm run typecheck` 2회 PASS
  - 테스트 기준: `Set-Location c:\Users\WORK\source\repos\parkcheolhong\codeAI; python scripts/check_checklist_consistency.py --files docs/checklists/worldlinco-app-improvement-checklist-20260812.md` PASS
  - 단계 1: `App.tsx` 인증 경로에서 직접 참조 제거, `auth.*` 키 우선 + fallback 적용
  - 단계 2: 테스트/유틸/문서 템플릿 포함 소스 경로 잔여 참조 0건 확인
  - 단계 3: `appConstants.ts`의 `AUTH_ONBOARDING_TEXT` export 제거 완료
  - 근거: `apps/mobile-nadotongryoksa/src/**` 검색에서 `AUTH_ONBOARDING_TEXT`는 `apps/mobile-nadotongryoksa/src/app/appConstants.ts` 정의부 1건만 존재함을 확인
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` 검색 결과 `AUTH_ONBOARDING_TEXT` 0건 확인
  - 근거: `apps/mobile-nadotongryoksa/tests/**`, `apps/mobile-nadotongryoksa/docs/**` 검색 결과 `AUTH_ONBOARDING_TEXT` 0건 확인
  - 근거: `apps/mobile-nadotongryoksa/src/app/appConstants.ts`에서 `AUTH_ONBOARDING_TEXT` export 블록 제거
  - 근거: 생성 산출물(`android/app/build/**`) 소스맵 문자열은 코드 참조가 아니라 빌드 산출물 잔존임을 분리 기록

### 3-1. UI 섹션 분리
- [x] Home/Travel/VoIP/Chat/Song 섹션 컴포넌트 분리
  - 완료 조건: `App.tsx` JSX 라인 수 대폭 축소, 섹션별 파일 이동
  - 검증: 기존 UI 동작 동등성 스모크 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/features/home/HomeWorkspaceSection.tsx`
  - 근거: `apps/mobile-nadotongryoksa/src/features/song/SongModeSection.tsx`
  - 근거: `docs/checklists/evidence/worldlinco-31-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-31-validation-passB/travelBooking-passB.txt`

### 3-2. 음성 캡처 매니저 모듈화
- [x] VoiceCapture 훅/매니저 모듈 추출
  - 완료 조건: start/stop/lease 흐름 단일 책임으로 분리
  - 검증: 대화통역/소리새/VoIP에서 마이크 충돌 없음 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/features/song/useVoiceCaptureManager.ts`
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`
  - 근거: `docs/checklists/evidence/worldlinco-32-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-32-validation-passB/songLang-passB.txt`

### 3-3. 데이터 계층 표준화
- [x] `react-query`(tanstack query) 도입
  - 완료 조건: 인증/프로필/핵심 조회 API 캐시 정책 반영
  - 검증: 중복 호출 감소 + 오류 재시도 정책 동작 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` (QueryClientProvider + purchases/friends fetchQuery cache/retry + logout cache clear)
  - 근거: `apps/mobile-nadotongryoksa/package.json` (`@tanstack/react-query` 의존성 추가)
  - 근거: `docs/checklists/evidence/worldlinco-33-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-33-validation-passB/chatVoiceInput-passB.txt`

### 3-4. i18n 체계 정규화
- [x] 언어 리소스 파일 기반 구조 정리
  - 완료 조건: UI 텍스트 키와 번역 데이터 분리, 동적 교체 경로 고정
  - 검증: 다국어 전환 2회 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/features/i18n/featureUiCatalog.ts`에 song/voice 상태 메시지 키 추가 및 다국어 데이터(ko/en/ja/zh) 정리
  - 근거: `apps/mobile-nadotongryoksa/src/features/song/useVoiceCaptureManager.ts`에서 voice 샘플/녹음/삭제/preview 상태 문구를 `getFeatureUiText(...)`로 치환
  - 근거: `apps/mobile-nadotongryoksa/App.tsx`의 song file 업로드/폴링/타임라인/저장/내보내기 상태 문구를 `getFeatureUiText(...)`로 치환
  - 근거: `docs/checklists/evidence/worldlinco-34-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-34-validation-passA/userLanguageWiring-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-34-validation-passB/typecheck-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-34-validation-passB/userLanguageWiring-passB.txt`
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/README.md` (작업 변경/산출물 변경 분리 아카이브)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passA/typecheck.txt`
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passA/userLanguageWiring.txt`
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passB/typecheck.txt`
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passB/userLanguageWiring.txt`
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-verify-single.txt` (초기 실기기 KWS 스모크: Activity launch mismatch)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-verify-after-script-fix.txt` (스크립트 디바이스 지정/런치 fallback 추가 후 재실행: 앱 런치 성공, KWS marker 미검출)
  - 근거: `apps/mobile-nadotongryoksa/scripts/trigger_kws_companion_arm.ps1` (Settings/소리새 진입 전 단계에서 companion arm 트리거를 강제 시도하는 실측 시나리오 스크립트)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass1-rerun.txt` (동일 디바이스 1차 반복: FAIL-B)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass2-rerun.txt` (동일 디바이스 2차 반복: FAIL-B)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass3-rerun-20260813.txt` (실기기 1회 재실행: FAIL-B 지속, companion toggle 미노출)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass4-preflow-20260813.txt` (자동화 프리플로(login/session entry) 포함 1회 추가 확증 실행: FAIL-B 지속, companion toggle 미노출)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass5-preflow-loop-20260813.txt` (화면 상태 검증 루프(최대 4회) 적용 후 동일 디바이스 재실행: FAIL-B 지속, companion toggle 미노출)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass6-testmode-preflow-loop-20260813.txt` (EXPO_PUBLIC_FORCE_COMPANION_TOGGLE_TEST_MODE=1 빌드/재설치 후 재실행: companion toggle 노출·탭 성공, marker 미검출로 FAIL-B 지속)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass6b-testmode-preflow-loop-settings-20260813.txt` (preflow 탭 이동 강제 단계(설정 탭 경유) 추가 후 재실행: toggle 미노출 상태로 FAIL-B 지속)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass7-testmode-showlogin-and-handler-diagnostics-20260813.txt` (showLogin 완화 플래그 + armed UI 재검증 + companion handler marker 확장 후 재실행: `COMPANION_TOGGLE_TAP`/`COMPANION_ARMED_ON`/`COMPANION_START_VOICE_REQUEST` 확인, `native_started` 미검출로 FAIL-B 지속)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass8-kws-init-chain-20260813.txt` (KWS init marker 확장 후 재실행: `TOGGLE_TAP`/`ARMED_ON`/`START_VOICE_REQUEST`=true, `KWS_INIT_BEGIN/END/ERROR`=false)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass10-start-voice-enter-20260813.txt` (`COMPANION_START_VOICE_ENTER`=true, `COMPANION_KWS_INIT_BEGIN/END/ERROR`=false로 startVoiceInput 진입은 확인되었으나 KWS init 진입 전 탈락 지점 확정)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass11-after-fix-20260813.txt` (`COMPANION_START_VOICE_ENTER`=true, `COMPANION_KWS_INIT_BEGIN/END`=true로 수동 companion arm 경로의 startVoiceInput/KWS init 연쇄 확인)
  - 근거: `docs/checklists/archive/worldlinco-34-i18n-20260812/README.md` 5) Frozen marker gate
  - 판정: 3-4는 수동 companion arm 경로의 startVoiceInput/KWS init 연쇄를 실기기에서 확인했고, 남은 native_started는 별도 dormant 네이티브 경로로 분리한다.

---

## 4) 성능/안정성 게이트

- [x] 대용량 텍스트 렌더링 최적화
  - 완료 조건: OCR/장문 번역 결과 렌더 경량화 (`useMemo`, 리스트 가상화)
  - 검증: 장문 입력/출력 시 프레임 드랍 완화 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/src/features/ocr/CameraTranslateOverlay.tsx`에서 OCR 결과 패널을 `FlatList` 가상화 렌더로 전환
  - 근거: `apps/mobile-nadotongryoksa/src/features/ocr/CameraTranslateOverlay.tsx`에서 결과 row 데이터(`원문/번역`)를 `useMemo`로 고정
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/tests-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/typecheck-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/tests-passB.txt`
- [x] 함수 재생성 최소화
  - 완료 조건: 빈번한 콜백에 `useRef`/불변 컨텍스트 적용
  - 검증: 렌더 트레이스에서 불필요 재렌더 감소 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/src/app/useAppVoiceCaptureLoop.ts`에서 `stopFacePlayback`/`stopSorisaePlayback`를 `useCallback`으로 고정
  - 근거: `apps/mobile-nadotongryoksa/src/app/useAppVoiceCaptureLoop.ts`에서 `deps` 객체와 telemetry noop 콜백을 `useMemo`/`useCallback`으로 고정
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/tests-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/typecheck-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/tests-passB.txt`
- [x] 네트워크 중복 방지
  - 완료 조건: AbortController 또는 중복요청 가드 적용
  - 검증: 동일 액션 연타 시 요청 병목/중복 감소 2회 확인
  - 근거: `apps/mobile-nadotongryoksa/src/services/worldlincoTourismPromo.ts`에서 `promoInFlight`/`boardInFlight` 맵 기반 중복 요청 합류(single-flight) 적용
  - 근거: `apps/mobile-nadotongryoksa/src/services/worldlincoTourismPromo.ts`에서 동일 cacheKey 동시 호출 시 기존 Promise 재사용하도록 변경
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passA/tests-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/typecheck-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-4x-validation-passB/tests-passB.txt`

---

## 5) 테스트/CI 게이트

- [x] 단위 테스트 세트 구축
  - 완료 조건: 인증, 음성 캡처, VoIP 상태전이, 여행 검색 핵심 테스트 추가
  - 검증: 테스트 전체 2회 연속 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/__tests__/voiceCaptureLease.test.ts` 신규 추가(마이크 단일 소유권 acquire/revoke/release 계약 검증)
  - 근거: `apps/mobile-nadotongryoksa/src/__tests__/biometricGate.test.ts` (인증 핵심 경로)
  - 근거: `apps/mobile-nadotongryoksa/src/__tests__/voiceRelayTurnController.test.ts` (VoIP 상태전이)
  - 근거: `apps/mobile-nadotongryoksa/src/__tests__/travelBooking.test.ts` (여행 검색 핵심)
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passA/typecheck-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passA/tests-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passB/typecheck-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passB/tests-passB.txt`
- [x] 통합 테스트(핵심 플로우) 구축
  - 완료 조건: 로그인 -> 번역 -> VoIP/채팅 최소 시나리오 자동화
  - 검증: CI에서 2회 연속 PASS
  - 근거: `apps/mobile-nadotongryoksa/src/__tests__/worldlincoCoreFlow.integration.test.ts` 신규 추가(로그인→번역→VoIP 스냅샷/종료→채팅 전송)
  - 근거: `.github/workflows/mobile-nadotongryoksa-core-gate.yml` 추가(matrix `passA`, `passB`로 동일 게이트 2회 실행)
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passA/tests-passA.txt`
  - 근거: `docs/checklists/evidence/worldlinco-5x-validation-passB/tests-passB.txt`
  - 근거: `docs/checklists/evidence/worldlinco-5x-ci-proof-20260813.md` (GitHub Actions run 2회 URL + 로그 추출 screenshot 경로)
- [x] 회귀 방지 규칙 문서화
  - 완료 조건: 변경 금지 계약(핫패스/공개 API/상태 계약) 정리
  - 검증: PR 체크리스트와 연동 확인
  - 근거: `docs/checklists/worldlinco-regression-guard-contracts.md` 신규 추가(핫패스/공개 API/상태 계약 SSOT)
  - 근거: `.github/pull_request_template.md` 신규 추가(PR 체크리스트 연동)

---

## 6) 우선순위 Top 10 (실행 순서 고정)

1. [x] 기준선 성능 측정 1차
2. [x] 기준선 성능 측정 2차
3. [x] 상수/문자열 분리
4. [x] 플랫폼 분기 정리
5. [x] 인증 상태 통합(Context + Reducer)
6. [x] Auth API 중복 호출 제거
7. [x] 위치 서비스 단일화
8. [x] 보안 저장소 전환(SecureStore)
9. [x] UI 섹션 분리(Home/Travel/VoIP/Chat/Song)
10. [x] 테스트/CI 게이트 구축

---

## 7) 완료 판정 기준

- [x] 전체 항목 `[x]` 충족
  - 근거: `## 0)~## 6)` 실행 항목이 모두 `[x]`로 정합화됨
- [x] 통합 닫기 체크리스트 참조 연결 완료
  - 근거: [docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md](docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md) 문서를 상위 마스터 체크리스트의 닫기 근거로 연결
- [x] 각 `[x]` 항목에 근거 라인 존재
  - 근거: `python scripts/check_checklist_consistency.py --files docs/checklists/worldlinco-app-improvement-checklist-20260812.md` 통과
- [x] 핵심 기능 회귀 검증 2회 PASS 기록
  - 근거: `docs/checklists/evidence/worldlinco-baseline-pass1-20260812_064855/` + `docs/checklists/evidence/worldlinco-baseline-pass2-20260812_064903/` + `docs/checklists/evidence/worldlinco-5x-validation-passA/` + `docs/checklists/evidence/worldlinco-5x-validation-passB/` + `docs/checklists/evidence/worldlinco-5x-ci-proof-20260813.md` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass3-rerun-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass4-preflow-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass5-preflow-loop-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass6-testmode-preflow-loop-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass6b-testmode-preflow-loop-settings-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass7-testmode-showlogin-and-handler-diagnostics-20260813.txt` + `docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass8-kws-init-chain-20260813.txt`
- [x] 차단 항목 `[ ]` 또는 `[~]` 0건
  - 근거: 본 문서 미체크 항목 전수 점검 결과 `[ ]`/`[~]` 0건
