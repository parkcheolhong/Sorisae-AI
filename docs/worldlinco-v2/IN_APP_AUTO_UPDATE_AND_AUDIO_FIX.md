# 인앱 자동 업데이트 + 음성 발화(재생) 회귀 수정 — 기술서

> 목적: 본 세션에서 추가/수정된 두 기능을 상세히 기술한다.
> 1. **인앱 자동 업데이트** — 마켓플레이스에 새 빌드를 올리면 설치된 단말이 스스로 감지하고
>    "업그레이드"를 누르면 앱 안에서 곧장 다운로드·설치까지 연결한다.
> 2. **음성 발화(TTS 재생) 회귀 수정** — expo-av → expo-audio 마이그레이션으로 인해 재생이
>    소리도 나기 전에 즉시 종료되던 버그를 공유 오디오 래퍼에서 근본 수정한다.
>
> 적용 버전: 자동 업데이트 = 1.0.91(build 143) 최초 도입 → 1.0.93(build 145) 포그라운드 재확인 추가.
> 재생 회귀 수정 = 1.0.92(build 144).

---

## A. 인앱 자동 업데이트 (마켓 → 단말 자동 업그레이드 연결)

### A.1 개요 / 동작 원칙

사이드로드(Play 스토어 외부, 마켓 직접 배포) 방식이므로 OTA(스토어 자동 갱신)가 없다.
따라서 앱이 **스스로 최신 빌드를 찾아가** 사용자에게 업그레이드를 제안하고, 동의 시
**브라우저로 빠지지 않고 앱 내부에서** APK 다운로드 → 시스템 설치 화면까지 연결한다.

핵심 흐름(4단계):

```
앱 실행/포그라운드 복귀
        │
        ▼
①  최신 메타 조회   GET /api/marketplace/latest-apk-metadata   (로그인 불필요)
        │
        ▼
②  버전 비교        versionCode(원격) > versionCode(설치본) ?
        │ (yes)
        ▼
③  업그레이드 팝업   "새 버전 v1.0.xx · build NNN 이(가) 준비되었습니다"
        │ ("업그레이드")
        ▼
④  다운로드+설치     GET /api/marketplace/latest.apk → 캐시 저장
                     → content:// URI 변환 → 시스템 패키지 설치기 인텐트
```

### A.2 백엔드 엔드포인트 (SSOT)

`backend/marketplace/router.py` — 둘 다 **인증 불필요**, 캐시 무효화 헤더 적용.

| 엔드포인트 | 메서드 | 반환 | 용도 |
|---|---|---|---|
| `/api/marketplace/latest-apk-metadata` | GET | `version_name`, `build_number`, `package`, `download_path`, `published_at`, `size_bytes`, `apk_filename` | 최신 버전 메타(업데이트 판정용) |
| `/api/marketplace/latest.apk` | GET | APK 바이너리(고정 URL, `application/vnd.android.package-archive`) | 최신 APK 다운로드 |

메타데이터의 소스는 발행 스크립트가 기록한 `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json`
(`_read_worldlinco_apk_manifest()`)이며, 매니페스트가 없으면 최신 mtime APK로 폴백한다.

> 운영/로컬 일관성: `https://metanova1004.com` 과 `http://127.0.0.1:8000` 이 동일 디렉터리를
> 서빙하므로, 발행 즉시 두 엔드포인트 모두 새 `build_number` 를 반환한다(실측 확인).

### A.3 클라이언트 모듈

#### `src/features/app-update/appUpdate.ts` (신규, 클라이언트 SSOT)

- `fetchLatestApkMetadata(apiBase)` → 메타 조회(no-cache). `build_number` 파싱.
- `isRemoteApkNewer(currentVersion, currentBuild, remote)` → **versionCode(빌드번호)를 1차 기준**으로
  최신 판정(단조 증가값이라 가장 신뢰 가능). 빌드번호가 같을 때만 semver(`x.y.z`)로 2차 비교.
- `downloadAndInstallLatestApk(apiBase, { onProgress })` → 다운로드 + 설치 인텐트.
  - `FileSystem.createDownloadResumable(...)` 로 `cacheDirectory/worldlinco-update-<ts>.apk` 저장(진행률 0~1 콜백).
  - 손상/빈 파일 가드(`size < 1024` 거부).
  - `FileSystem.getContentUriAsync(uri)` 로 **content:// URI** 변환(Android 7+ 설치기 접근 필수).
  - `IntentLauncher.startActivityAsync('android.intent.action.INSTALL_PACKAGE', { data, flags:1, type })`
    1차 시도 → 미해결 시 `ACTION_VIEW` 폴백. `flags:1` = `FLAG_GRANT_READ_URI_PERMISSION`.

#### `App.tsx` 통합

- `checkForAppUpdate()` 재작성:
  - `ENABLE_IN_APP_UPDATE_PROMPT` 게이트(아래 A.6), `VERSION_IGNORE_KEY`(영구 비활성) 확인.
  - 메타 직접 조회 → `isRemoteApkBuildNewer` 판정.
  - 같은 빌드를 "나중에"로 누른 경우 `VERSION_SNOOZE_BUILD_KEY` 로 재알림 억제(더 새 빌드면 다시 알림).
  - 신규 빌드면 `Alert` 로 "업그레이드/나중에" 제시. "업그레이드" → `runApkInAppInstall()`(진행률 토스트 포함).
- 트리거:
  - **앱 시작 시**(mount useEffect) 1회.
  - **포그라운드 복귀 시**(`AppState 'active'`) 재확인, 30초 쓰로틀. → *1.0.93에서 추가.*
    마켓에 올린 뒤 앱을 새로 켜지 않아도 앱으로 돌아오면 스스로 감지한다.

### A.4 권한 / 매니페스트

`android/app/src/main/AndroidManifest.xml` + `app.json`:

- `android.permission.REQUEST_INSTALL_PACKAGES` — 외부 출처 APK 설치 트리거.
- 패키지 가시성 쿼리(Android 11+/targetSdk 36):
  ```xml
  <queries>
    <intent><action android:name="android.intent.action.INSTALL_PACKAGE"/></intent>
    <intent>
      <action android:name="android.intent.action.VIEW"/>
      <data android:mimeType="application/vnd.android.package-archive"/>
    </intent>
  </queries>
  ```
- 네이티브 모듈: `expo-intent-launcher ~56.0.4`(expo 자동링크). content:// 는 expo-file-system 의 FileProvider 사용.

### A.5 사용자 경험 / "Google Play 프로텍트" 단계

설치 직전 **"Google Play 프로텍트 / 검색 중…"** 팝업은 사이드로드 APK에 대한 구글의 정상 검사다.
검사 후 **설치** 버튼으로 진행한다. 최초 1회는 "출처를 알 수 없는 앱 설치 허용"을 요구할 수 있다.

### A.6 활성화 플래그 (회귀 원인 + 수정)

- (회귀) 과거: `ENABLE_IN_APP_UPDATE_PROMPT = (RELEASE_CHANNEL === 'production')`.
  빌드 스크립트가 `EXPO_PUBLIC_RELEASE_CHANNEL` 를 설정하지 않아 **프롬프트가 항상 비활성**이었다.
- (수정) 현재: 기본 활성, `EXPO_PUBLIC_DISABLE_UPDATE_PROMPT=1` 로만 비활성.

### A.7 버전 게이팅(중요한 제약)

인앱 업데이터 코드는 **1.0.91(build 143)부터** 존재한다. 그 이전 빌드(≤1.0.90)에는 업데이터가
사실상 없으므로 자동 팝업이 뜨지 않는다. → 각 단말은 **최초 1회 수동으로 1.0.91+ 설치**가 필요하며,
그 이후부터 모든 신규 빌드가 자동 연결된다. (WiFi/USB든 LTE든 네트워크와 무관하게 동일 — 단말의
설치 버전만이 조건이다.)

---

## B. 음성 발화(TTS 재생) 회귀 수정 — expo-av → expo-audio

### B.1 증상

VoIP·대면 양쪽에서 STT/MT/TTS는 정상이고 앱 로그에는 `played`(server_audio)로 찍히는데
**실제로는 소리가 안 났다.** 양쪽 폰 동시 무음.

### B.2 프로파일링으로 좁힌 근거(추측 배제)

단말(SM-G973N, 1.0.91) 실측:

| 검사 | 결과 | 판정 |
|---|---|---|
| 백엔드 `/api/llm/voice/synthesize` | `audio/mpeg` 23,040자 정상 반환 | ✅ 서버 정상 |
| STREAM_MUSIC / STREAM_VOICE_CALL | speaker 15/15·8/8, **뮤트 아님** | ✅ 음량 정상 |
| 재생 시점 모드 / 트랙 | NORMAL, `usage=USAGE_MEDIA`, `setVolume(1.0)` | ✅ 라우팅 정상 |
| **타이밍** | `segment_response`→`played` = **0.6초** | ❌ 2초 mp3가 즉시 "완료" |

→ 음량·라우팅·서버 전부 정상인데 **재생이 즉시 종료**되어 소리가 안 난 것.

### B.3 근본 원인

앱은 expo-av 제거 후 **expo-audio 를 감싼 compat 래퍼**(`src/compat/expoAvAudio.ts`)로 재생한다.
expo-audio 는 소스를 **비동기 로드**하므로, 재생 시작 *전* 에 `isLoaded:false`(로딩 중) 상태가 먼저 흐른다.
그런데 호출부(VoIP `playVoiceRelayOutput`, 대면 `playFaceTranslationOutput`)는 expo-av 관례대로
`isLoaded === false` 를 **"재생 종료"로 오인** → Promise 즉시 resolve → 곧장 `stop/unload` →
**소리가 나기 전에 끊김**. 두 경로가 동일 래퍼를 공유하므로 양쪽 모두 무음이었다.

### B.4 수정 (`src/compat/expoAvAudio.ts`, 공유 1곳)

`Sound`에 `hasLoaded`/`shouldPlayRequested` 상태를 두고, `createAsync` 리스너와
`setOnPlaybackStatusUpdate` 양쪽에서:

- **한 번이라도 `isLoaded:true` 가 된 뒤(또는 `didJustFinish`)에만** 종료성 상태를 호출부에 전달.
  로드 전의 `isLoaded:false` 는 "종료"가 아니라 "로딩 중"이므로 무시한다.
- 로드 완료 시 재생을 **한 번 더 보장**(`play()` 가 로딩 전 호출되어 무시된 경우 대비).
- 완료 판정은 expo-audio 정식 필드 `didJustFinish` 로 일원화(타입 확인 완료).

> 호출부(App.tsx / VoIPCallScreen.tsx)는 수정하지 않는다 — 공유 래퍼 1곳 수정으로 VoIP·대면 동시 해결.

### B.5 VoIP 재생 라우팅 보강(부가)

`VoIPCallScreen.tsx` 의 `playVoiceRelayOutput` 재생 직전:
- `playThroughEarpieceAndroid: false`(통역폰=탁자 가정, 항상 라우드스피커)
- `setVoipSpeakerphone(true)` + `enableVoipAudio(true, true)` 로 라우드스피커 + 통화음량 최대화.
  근거: MODE_IN_COMMUNICATION 구간에서 미디어가 이어피스로 라우팅되는 단말 특성 상쇄.

---

## C. 검증 / 운영

### C.1 발행

```powershell
powershell -ExecutionPolicy Bypass -File scripts/publish_worldlinco_apk.ps1
```
→ `nadotongryoksa-v1.apk`(canonical), `…-vX.Y.Z-buildN-current.apk`, `nadotongryoksa-v1.manifest.json` 갱신.

### C.2 자동 업데이트 동작 확인(실측)

```powershell
# 1) 메타가 새 빌드를 반영하는지(운영/로컬 동일해야 함)
Invoke-WebRequest https://metanova1004.com/api/marketplace/latest-apk-metadata -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/api/marketplace/latest-apk-metadata -UseBasicParsing

# 2) 단말 콜드 재시작 → 업데이터가 감지·설치기까지 연결되는지(스크린샷)
adb -s <device> shell am force-stop com.parkcheolhong.worldlinco
adb -s <device> shell monkey -p com.parkcheolhong.worldlinco -c android.intent.category.LAUNCHER 1
adb -s <device> shell screencap -p /sdcard/u.png; adb -s <device> pull /sdcard/u.png
```
설치 버전 확인: `adb -s <device> shell dumpsys package com.parkcheolhong.worldlinco | findstr versionName`

### C.3 재생(발화) 동작 확인

VoIP 통화 중 logcat 마커: `VOIP_VOICE_RELAY_PLAYBACK`(pending) → `VOIP_VOICE_RELAY_PLAYBACK_DELIVERED`.
정상 시 `played` 까지의 간격이 실제 오디오 길이(약 2초±)에 비례해야 한다(0.x초 즉시 완료면 회귀).

---

## D. 변경 파일 요약

| 파일 | 변경 |
|---|---|
| `src/features/app-update/appUpdate.ts` | 신규 — 메타 조회/다운로드/설치 인텐트 SSOT |
| `App.tsx` | `checkForAppUpdate` 재작성, 시작+포그라운드 재확인, 프롬프트 항상 활성 |
| `src/compat/expoAvAudio.ts` | 재생 즉시 종료 회귀 수정(로딩 중 isLoaded:false 무시 + 재생 보장) |
| `src/screens/VoIPCallScreen.tsx` | VoIP 재생 직전 라우드스피커 강제 + 통화음량 최대화 |
| `android/app/src/main/AndroidManifest.xml`, `app.json` | `REQUEST_INSTALL_PACKAGES` + 설치 인텐트 가시성 쿼리 |
| `package.json` | `expo-intent-launcher ~56.0.4` 추가 |

## E. 버전 이력

| 버전 | build | 핵심 |
|---|---|---|
| 1.0.91 | 143 | 인앱 자동 업데이트 최초 도입(프롬프트 활성화 포함) |
| 1.0.92 | 144 | 재생 즉시 종료 회귀 수정(공유 오디오 래퍼) |
| 1.0.93 | 145 | 포그라운드 복귀 시 자동 업데이트 재확인 |
