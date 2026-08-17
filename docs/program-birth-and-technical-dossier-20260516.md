# 프로그램 이력기술서 — WorldLinco / Nadotongryoksa / Sorisae 인증·콜백 기록

> **문서 성격:** 프로그램의 구조도(기획도면)부터 현재 상태까지의 이력기술서 SSOT
> **최종 갱신:** 2026-08-17
> **작성 원칙:** 기능 구현은 더 이상 추가하지 않고, 현재까지의 핵심 소스만 기준으로 이미 확인된 구조·진행·검증 결과를 날짜 순서대로 누적 기록한다.

---

## 0. 문서 목적과 고정 원칙

1. 본 문서는 현재까지 확인된 기능별 기록을 근거로 정리하는 프로그램 이력기술서이다.
2. 기능 구현이 아닌 기록 정리와 검증 근거 고정만 수행한다.
3. 완료된 작업은 다시 재작성하지 않고, 새 증적이 생기면 날짜별로만 뒤에 추가한다.
4. 현재 상태는 실기기 검증 기준으로 고정한다.
5. 소스 증적은 `evidence/` 아래의 검증 산출물과, 기능 닫기 체크리스트를 우선한다.
6. 기록의 1차 기준은 `App.tsx`, `socialLogin.ts`, `appDeepLinks.ts`, `appConstants.ts`, `MainActivity.kt`, `App.styles.ts` 이다.

---

## 1. 초기 구조도(기획도면)

### 1.1 기획 목표

1. 모바일 앱이 OAuth / passkey / social login 콜백을 실제 디바이스에서 수신한다.
2. 콜백 수신 이후 세션 복원과 UI 상태 전환이 한 번만 일어나도록 소비 가드를 둔다.
3. 재주입 또는 중복 딥링크가 들어오면 이미 소비된 entry로 판정해 다시 처리하지 않는다.
4. 실기기 로그와 증적 파일로만 PASS / FAIL 을 판정한다.

### 1.1.1 실제 코드 기준 앵커

1. 앱 시작과 콜백 소비는 [App.tsx](../apps/mobile-nadotongryoksa/App.tsx) 가 중심이다.
2. 콜백 URL 조립과 외부 로그인 시작은 [src/auth/socialLogin.ts](../apps/mobile-nadotongryoksa/src/auth/socialLogin.ts) 가 담당한다.
3. 앱 진입 인텐트 전달은 [MainActivity.kt](../mobile-nadotongryoksa/android/app/src/main/java/com/parkcheolhong/worldlinco/MainActivity.kt) 의 `onNewIntent` 가 담당한다.
4. 콜백/딥링크 문자열과 경로 상수는 [src/app/appConstants.ts](../apps/mobile-nadotongryoksa/src/app/appConstants.ts) 와 [src/app/appDeepLinks.ts](../apps/mobile-nadotongryoksa/src/app/appDeepLinks.ts) 에 분리되어 있다.
5. 화면 상태와 카드/패널 배치는 [App.styles.ts](../apps/mobile-nadotongryoksa/App.styles.ts) 가 고정한다.

### 1.1.2 핵심 소스 우선순위

1. 1차 원본: [App.tsx](../apps/mobile-nadotongryoksa/App.tsx)
2. 2차 원본: [src/auth/socialLogin.ts](../apps/mobile-nadotongryoksa/src/auth/socialLogin.ts)
3. 3차 원본: [src/app/appDeepLinks.ts](../apps/mobile-nadotongryoksa/src/app/appDeepLinks.ts)
4. 4차 원본: [src/app/appConstants.ts](../apps/mobile-nadotongryoksa/src/app/appConstants.ts)
5. 5차 원본: [MainActivity.kt](../mobile-nadotongryoksa/android/app/src/main/java/com/parkcheolhong/worldlinco/MainActivity.kt)
6. 6차 원본: [App.styles.ts](../apps/mobile-nadotongryoksa/App.styles.ts)

### 1.2 구조 단위

1. `App.tsx`
   - 앱 진입점.
   - `parseAppEntryDeepLink` 결과를 받아 auth / invite / sales / voip 분기를 처리한다.
   - `applyAuthenticatedSession` 으로 토큰과 사용자 정보를 세션에 반영한다.
   - `handleSocialAuthCallback` 에서 `PASSKEY_LOGIN_CALLBACK_SUCCESS` 와 `SOCIAL_LOGIN_CALLBACK_SUCCESS` 를 기록한다.
   - `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 로 중복 진입을 차단한다.
2. `socialLogin.ts`
   - social login hook 계열의 콜백 처리 진입부.
   - `SOCIAL_LOGIN_REDIRECT_URI = worldlingo://auth/callback` 를 고정한다.
   - provider start URL 을 `GET /api/auth/social/{provider}/start?redirect_uri=...` 형태로 만든다.
   - 실제 인증 시작은 `Linking.openURL` 로 호출된다.
3. `App.styles.ts`
   - 현재 화면 구조와 상태 허브 표현의 스타일 정의.
   - 기능 구현이 아니라 노출·가시성·레이아웃을 고정하는 UI 보조층이다.
   - `bottomTabBar`, `actionTileGrid`, `inlineAuthPanel`, `voipTabRow` 같은 상태 허브 배치가 여기서 유지된다.
4. `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED`
   - 중복 콜백 소비 방지용 런타임 가드 이벤트.
   - 동일 딥링크 재주입 시 다시 처리하지 않는 기준 이벤트이다.
5. `PASSKEY_LOGIN_CALLBACK_SUCCESS` / `SOCIAL_LOGIN_CALLBACK_SUCCESS`
   - 디바이스 실기기 검증에서 콜백 수신 및 세션 복원 성공을 나타내는 대표 이벤트이다.

### 1.2.1 진입 흐름 요약

1. Android `MainActivity.onNewIntent` 가 딥링크를 받는다.
2. `App.tsx` 가 `parseAppEntryDeepLink` 결과를 계산한다.
3. auth callback 이면 `handleSocialAuthCallback` 로 들어가 `callMeApi` 와 `applyAuthenticatedSession` 을 수행한다.
4. 성공 시 `PASSKEY_LOGIN_CALLBACK_SUCCESS` 또는 `SOCIAL_LOGIN_CALLBACK_SUCCESS` 가 남는다.
5. 동일 콜백이 다시 들어오면 `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 로 차단된다.

### 1.3 현재 구조 결론

1. 콜백 수신 경로는 실기기에서 확인되었다.
2. 세션 복원 경로는 로그상 `user_email` 복원으로 확인되었다.
3. 재주입 방지 경로는 `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 로 확인되었다.
4. 현재 이력은 구현 확장보다 증적 정리와 검증 고정이 우선이다.
5. 앞으로의 문서 갱신은 위 핵심 소스와 그에 대응하는 증적만 추가한다.

### 1.4 현재 화면 상태 기준

1. `App.styles.ts` 상의 탭/그리드/인라인 인증 패널 구조는 현재 상태 허브 배치의 바닥선이다.
2. 로그인 흐름은 화면을 별도 페이지로 분리하지 않고, 기존 hub 화면 내부의 login panel 과 auth state 로 처리된다.
3. 실기기 검증 시 `show_login=false` 상태가 유지되며, 인증 후 허브 전환이 확인되었다.

---

## 2. 기능 시리즈

### 시리즈 01. Social Login Hook / UI 연동

#### 2.1 기능명
- Social login hook / UI 연동

#### 2.2 기능 목적
- 버튼 또는 실행 경로에서 호출된 social login 결과를 앱 내부 상태와 로그로 동시에 남긴다.

#### 2.3 확인된 동작
- 콜백이 들어오면 `SOCIAL_LOGIN_CALLBACK_SUCCESS` 가 기록된다.
- 사용자 이메일이 복원되어 `user_email` 이 로그에 남는다.
- 화면 쪽에서는 로그인 완료 후 상태 허브가 닫힌 상태로 전환된다.

#### 2.4 근거
- `evidence/apk-passkey-real-token-e2e-20260817-233215/verification-record.md`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/validation_summary.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/01_logcat.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/02_logcat.txt`

#### 2.5 현재 상태
- 완료됨.

---

### 시리즈 02. OAuth / Passkey 콜백 실기기 수신

#### 2.1 기능명
- OAuth / passkey 콜백 실제 디바이스 수신

#### 2.2 기능 목적
- 가짜 실행이 아니라 실제 디바이스 ADB 주입으로 콜백 딥링크를 수신했는지 증명한다.

#### 2.3 확인된 동작
- `MainActivity.onNewIntent` 경로로 `worldlingo://auth/callback?...` 전체가 전달되었다.
- runtime 로그에서 `PASSKEY_LOGIN_CALLBACK_SUCCESS` 가 기록되었다.
- runtime 로그에서 `SOCIAL_LOGIN_CALLBACK_SUCCESS` 가 기록되었다.
- `validation_summary.txt` 에서 round 1 / round 2 모두 PASS 로 확인되었다.

#### 2.4 근거
- `evidence/apk-passkey-real-token-e2e-20260817-233215/validation_summary.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/01_logcat.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/02_logcat.txt`

#### 2.5 현재 상태
- 완료됨.

---

### 시리즈 03. 중복 소비 가드 / 재주입 차단

#### 3.1 기능명
- APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED 가드

#### 3.2 기능 목적
- 같은 콜백을 다시 넣었을 때 이미 소비된 엔트리로 인식해 이중 처리하지 않는다.

#### 3.3 확인된 동작
- 첫 콜백 이후 동일 콜백 재주입 시 `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 가 기록되었다.
- round 1 / round 2 모두 재주입 후 같은 가드가 관측되었다.
- 중복 소비 차단과 콜백 성공이 서로 충돌하지 않고 함께 성립했다.

#### 3.4 근거
- `evidence/apk-passkey-real-token-e2e-20260817-233215/01_logcat.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/02_logcat.txt`
- `evidence/apk-passkey-real-token-e2e-20260817-233215/verification-record.md`

#### 3.5 현재 상태
- 완료됨.

---

## 3. 날짜별 진행 기록

### 2026-08-16

1. `docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md` 가 `상태: 완료됨` 으로 닫혔다.
2. 동일 조건 2회 연속 PASS 구조가 정리되었다.
3. 당시 기준으로 패스키 콜백 성공, Sorisae FAB 실이벤트, 2연속 PASS 판정이 모두 닫혔다.

#### 근거
- [Sorisae Passkey/FAB 통합 닫기 체크리스트](docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md)

---

### 2026-08-17

1. 실기기 `172.30.1.15:5555` 에서 OAuth callback deep link 를 실제 주입했다.
2. 초기 실행 `shell: rerun-passkey-callback-verifier` 는 더미 토큰 preflight 에서 `401` 로 중단되었다.
3. 같은 검증 스크립트를 실제 JWT 와 `-SkipTokenPreflight` 조건으로 다시 실행했다.
4. 검증 스크립트는 `PASS` 를 반환했다.
5. 증적 디렉터리 `evidence/apk-passkey-real-token-e2e-20260817-233215` 가 생성되었다.
6. `validation_summary.txt` 에서 round 1 / round 2 모두 PASS 로 정리되었다.
7. 로그에서 `PASSKEY_LOGIN_CALLBACK_SUCCESS`, `SOCIAL_LOGIN_CALLBACK_SUCCESS`, `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 가 확인되었다.

#### 근거
- [verification-record.md](../evidence/apk-passkey-real-token-e2e-20260817-233215/verification-record.md)
- [validation_summary.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/validation_summary.txt)
- [01_logcat.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/01_logcat.txt)
- [02_logcat.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/02_logcat.txt)

---

## 3.1 Build 331 APK 재현 계약 (2026-08-17 고정)

### 3.1.1 목적

1. 현재 프로그램과 연결된 실제 운영/검증 APK 기준선을 build 331로 고정한다.
2. 기술서만 읽고도 331 APK의 정확한 기준 바이너리, 소스 커밋, 원격 빌드 입력, 게시 매니페스트를 추적할 수 있게 한다.
3. 현재 작업트리의 332 드리프트를 331 재현 경로와 분리한다.

### 3.1.2 331의 최종 SSOT 체인

1. 정확한 게시 바이너리 SSOT는 [uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk](../uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk) 이다.
2. 위 바이너리의 고정값은 `SHA256=4DBEF5DC2B620D68F21841E731EAE8D2105FDCD3BF3464B8C4895E35B247F0E4`, `sizeBytes=127965746` 이다.
3. 게시 메타데이터 SSOT는 [uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json](../uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json) 이고, `versionCode=331`, `versionName=1.0.246`, `versionedFilename=nadotongryoksa-v1.0.246-build331-current.apk` 를 가리킨다.
4. 모바일 APK 기준선 SSOT는 [knowledge/worldlinco_apk_baseline.json](../knowledge/worldlinco_apk_baseline.json) 이고, 동일하게 `versionCode=331`, `versionName=1.0.246`, `probe_min_build=323` 으로 고정돼 있다.
5. 실제 EAS 원격 빌드 기준 소스 커밋은 `2494f4c6fe37ac794be7d292659d60f2d2d04864` 이다.
6. 해당 커밋의 `apps/mobile-nadotongryoksa/app.json` 은 `expo.version=1.0.246`, `expo.android.versionCode=331`, `package=com.parkcheolhong.worldlinco`, `runtimeVersion=1.0.76` 를 가진다.
7. 해당 커밋의 `apps/mobile-nadotongryoksa/eas.json` 은 `cli.appVersionSource=local` 이며, 모바일 331 빌드 입력은 루트 [eas.json](../eas.json) 이 아니라 앱 전용 `apps/mobile-nadotongryoksa/eas.json` 이다.
8. EAS 빌드 증적은 `build id=bd968eb2-9176-4060-8b34-4b2d5d10ca7d`, `appVersion=1.0.246`, `appBuildVersion=331`, `gitCommitHash=2494f4c6fe37ac794be7d292659d60f2d2d04864`, `completedAt=2026-08-12T19:03:46.217Z` 로 남아 있다.
9. 실기기 설치 증적은 [apps/mobile-nadotongryoksa/evidence/device-validation-20260813/run1_permissions_and_version.txt](../apps/mobile-nadotongryoksa/evidence/device-validation-20260813/run1_permissions_and_version.txt) 이고, `versionCode=331`, `versionName=1.0.246`, `targetSdk=36` 을 확인한다.

### 3.1.3 현재 드리프트 경고

1. 현재 작업트리의 [apps/mobile-nadotongryoksa/app.json](../apps/mobile-nadotongryoksa/app.json) 은 이미 `versionCode=332`, `versionName=1.0.247` 이다.
2. 현재 작업트리의 `apps/mobile-nadotongryoksa/android/app/build.gradle` 역시 `versionCode 332`, `versionName "1.0.247"` 로 올라가 있다.
3. 따라서 현재 체크아웃 상태에서 바로 빌드하면 331이 아니라 332 계열 APK가 생성된다.
4. 331 재현 문서에서 루트 [eas.json](../eas.json) 을 기준으로 삼으면 안 된다. 루트 설정은 `appVersionSource=remote` 로 바뀌어 있어 331 입력 체인과 다르다.

### 3.1.4 331 재현 방식의 구분

1. 정확히 같은 APK 바이트 재현 경로는 [uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk](../uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk) 을 기준 아티팩트로 사용하는 방법뿐이다.
2. 소스 기준 재현 경로는 `git checkout 2494f4c6fe37ac794be7d292659d60f2d2d04864` 후 `apps/mobile-nadotongryoksa/app.json` 과 `apps/mobile-nadotongryoksa/eas.json` 값을 검증하고 EAS 빌드를 다시 수행하는 방식이다.
3. 현재 저장된 원격 빌드 증적은 AAB 계열 `production` 빌드의 입력값과 완료 이력을 증명한다.
4. 현재 저장된 게시 APK는 마켓 배포용 exact-byte 기준선이며, 기술서에서 APK 100% 재현 기준은 이 preserved artifact 와 그 해시/바이트 수를 통과하는 것으로 정의한다.

### 3.1.5 기술서 기반 331 재현 절차

1. exact-byte 재현이 목표면 먼저 [uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk](../uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk) 의 `SHA256` 과 `sizeBytes` 를 위 고정값과 대조한다.
2. 게시 상태 검증은 [uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json](../uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json) 과 [knowledge/worldlinco_apk_baseline.json](../knowledge/worldlinco_apk_baseline.json) 이 모두 331/1.0.246 로 일치하는지 확인한다.
3. 소스 재현이 목표면 반드시 `git checkout 2494f4c6fe37ac794be7d292659d60f2d2d04864` 로 내려가서 당시 `apps/mobile-nadotongryoksa/app.json` 과 `apps/mobile-nadotongryoksa/eas.json` 을 기준으로 삼는다.
4. 현재 작업트리의 332 파일을 기준으로 331 재현을 시도하면 실패로 판정한다.
5. 실기기 기준 최종 확인은 [apps/mobile-nadotongryoksa/evidence/device-validation-20260813/run1_permissions_and_version.txt](../apps/mobile-nadotongryoksa/evidence/device-validation-20260813/run1_permissions_and_version.txt) 처럼 `versionCode=331`, `versionName=1.0.246` 가 설치 상태에서 다시 확인될 때만 통과로 본다.
6. 331 재현 체크리스트와 근거 묶음은 [docs/checklists/worldlinco-build331-apk-reproduction-checklist-20260817.md](checklists/worldlinco-build331-apk-reproduction-checklist-20260817.md) 에 고정한다.

### 3.1.6 운영 런북(명령 단위)

1. exact-byte 아티팩트 해시 확인:

```powershell
Get-FileHash -Algorithm SHA256 uploads\marketplace_local\apk\nadotongryoksa-v1.0.246-build331-current.apk
```

- 게시 매니페스트 확인:

```powershell
Get-Content uploads\marketplace_local\apk\nadotongryoksa-v1.manifest.json -Raw
```

- build 331 소스 커밋 lineage 확인:

```powershell
git show 2494f4c6fe37ac794be7d292659d60f2d2d04864 --stat --no-patch
git show 2494f4c6fe37ac794be7d292659d60f2d2d04864:apps/mobile-nadotongryoksa/app.json
git show 2494f4c6fe37ac794be7d292659d60f2d2d04864:apps/mobile-nadotongryoksa/eas.json
```

- 실기기 설치 상태 확인:

```powershell
adb -s 172.30.1.15:5555 shell dumpsys package com.parkcheolhong.worldlinco
```

- 새 리허설 증적 폴더 생성:

```powershell
$runDir = "docs\checklists\evidence\build331-rehearsal-20260818-003405"
New-Item -ItemType Directory -Force -Path $runDir
```

- 리허설 증적에는 `git_commit.txt`, `app_json_331.txt`, `eas_json_331.txt`, `apk_hash.txt`, `apk_size.txt`, `manifest.json`, `device_dumpsys.txt`, `rehearsal-summary.md` 를 남긴다.

---

## 4. 현재 고정 상태

1. 기능 구현은 현재 상태에서 종료한다.
2. 앞으로는 기능 추가가 아니라 기록 누적만 수행한다.
3. 오늘 확인한 실기기 증적은 현재 프로그램 상태의 기준선으로 고정한다.
4. 중복 소비 가드와 콜백 수신 경로는 현재 검증 결과를 기준으로 동결한다.

### 현재 판정
- 콜백 수신: 완료됨
- 세션 복원: 완료됨
- 중복 소비 가드: 완료됨
- 추가 기능 구현: 없음

---

## 5. 증적 묶음 인덱스

1. [verification-record.md](../evidence/apk-passkey-real-token-e2e-20260817-233215/verification-record.md)
2. [validation_summary.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/validation_summary.txt)
3. [01_logcat.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/01_logcat.txt)
4. [02_logcat.txt](../evidence/apk-passkey-real-token-e2e-20260817-233215/02_logcat.txt)
5. [Sorisae Passkey/FAB 통합 닫기 체크리스트](docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md)
