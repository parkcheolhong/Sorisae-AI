# Mobile Stock AI Command Log

## Session Command History

- npx eas-cli --help
- npx eas-cli project --help
- npx eas-cli project:info --help
- npx eas-cli project:init --help

## Validation Commands

- npm install
- npm run typecheck
- npx expo config --json
- npx eas-cli --version

## Latest Verified Runs

- npm run eas:project:ensure:dry
  - result: success
  - output: placeholder 오염 없이 real projectId만 dry-run 출력 (쓰기 없음)
- npm run typecheck
  - result: success
  - output: TypeScript 오류 없음
- npx expo config --json
  - result: success
  - output: owner/updates/runtimeVersion/maxStopLossPercent/eas.projectId 반영 확인
- node scripts/validate-production-submit-gate.mjs (run #1)
  - result: success
  - output:
    - GATE_PASS: version format ok (1.0.0)
    - GATE_PASS: changelog contains current version (1.0.0)
    - GATE_PASS: approval marker found
    - GATE_PASS: production submit pre-check completed
- node scripts/validate-production-submit-gate.mjs (run #2)
  - result: success
  - output:
    - GATE_PASS: version format ok (1.0.0)
    - GATE_PASS: changelog contains current version (1.0.0)
    - GATE_PASS: approval marker found
    - GATE_PASS: production submit pre-check completed
- npm run release:dry-run:production-submit (run #1)
  - result: success
  - output:
    - DRY_RUN_PASS: submit.production profile exists
    - DRY_RUN_PASS: production submit gate passed
    - DRY_RUN_PASS: submit help contains required flags: --platform, --profile, --latest, --non-interactive
    - DRY_RUN_PASS: validated command shape: npx eas-cli submit --platform android --profile production --latest --non-interactive
    - DRY_RUN_PASS: production submit dry-run checks completed
- npm run release:dry-run:production-submit (run #2)
  - result: success
  - output:
    - DRY_RUN_PASS: submit.production profile exists
    - DRY_RUN_PASS: production submit gate passed
    - DRY_RUN_PASS: submit help contains required flags: --platform, --profile, --latest, --non-interactive
    - DRY_RUN_PASS: validated command shape: npx eas-cli submit --platform android --profile production --latest --non-interactive
    - DRY_RUN_PASS: production submit dry-run checks completed

## Staging Build Run (Actual)

- npx eas-cli build --non-interactive --platform android --profile staging
  - result: failed
  - output: Experience with id '00000000-0000-4000-8000-000000000000' does not exist.
  - note: 실제 EAS 프로젝트 ID 연결 후 재시도 필요
- npx eas-cli build --platform android --profile staging
  - result: blocked (resolved)
  - output:
    - dynamic app config에서 extra.eas.projectId 자동 반영 불가
    - expo-updates 동적 설정 필요
- npx eas-cli build --platform android --profile staging
  - result: in progress
  - output:
    - remote Android keystore 생성 완료
    - project compress 완료
    - EAS 업로드 진행 중
- npx eas-cli build --non-interactive --platform android --profile staging (EAS_NO_VCS=1)
  - result: failed (post-upload remote build failed)
  - output:
    - compress 완료 (1.7 GB)
    - Uploaded to EAS 완료
    - Computed project fingerprint 완료
    - build URL: <https://expo.dev/accounts/parkcheolhong/projects/stock-ai-mobile/builds/555a372a-5696-4fce-be98-98d2d1d23cf9>
    - 최종 상태: ERRORED
    - 원인: EAGER_BUNDLE 단계에서 `expo-asset` 패키지 누락
    - 에러: Error: The required package `expo-asset` cannot be found
- fix 적용
  - command: npx expo install expo-asset
  - config: app.config.ts plugins에 "expo-asset" 추가
- npx eas-cli build --non-interactive --platform android --profile staging (retry after expo-asset fix)
  - result: failed (post-upload remote build failed again)
  - output:
    - compress 완료 (1.7 GB)
    - EAS 업로드 진행 중
    - latest build id: 5885abc2-1041-4922-b715-8e711351ebe9
    - build URL: <https://expo.dev/accounts/parkcheolhong/projects/stock-ai-mobile/builds/5885abc2-1041-4922-b715-8e711351ebe9>
    - latest status: ERRORED
    - error code: EAS_BUILD_UNKNOWN_GRADLE_ERROR
    - error: Gradle build failed with unknown error (Run gradlew phase)
- 대응
  - 동일 지점 반복 실패(업로드 이후 원격 빌드 단계 실패)로 판단
  - 모바일 전용 경량 worktree 전환 후 재시도 실행
- npx eas-cli build --non-interactive --platform android --profile staging (lightweight worktree retry)
  - result: failed (post-upload remote build failed)
  - output:
    - worktree: c:/Users/WORK/source/repos/parkcheolhong/codeAI_mobile_lite
    - Uploaded to EAS 완료
    - Computed project fingerprint 완료
    - build URL: <https://expo.dev/accounts/parkcheolhong/projects/stock-ai-mobile/builds/22191376-58ff-4e78-a477-016f9a86b513>
    - 최종 상태: ERRORED
    - error code: EAS_BUILD_UNKNOWN_GRADLE_ERROR
    - root cause: :expo-modules-core:compileReleaseKotlin 단계에서 Compose Compiler 1.5.15가 Kotlin 1.9.25를 요구하나 빌드는 Kotlin 1.9.24 사용
    - log evidence: "This version (1.5.15) of the Compose Compiler requires Kotlin version 1.9.25 but you appear to be using Kotlin version 1.9.24"
- fix 적용 (Kotlin mismatch)
  - command: npx expo install expo-build-properties
  - config: app.config.ts plugins에 expo-build-properties 추가 및 android.kotlinVersion=1.9.25 명시
- npx eas-cli build --non-interactive --platform android --profile staging (retry after Kotlin fix)
  - result: failed (post-upload remote build failed)
  - output:
    - worktree: c:/Users/WORK/source/repos/parkcheolhong/codeAI_mobile_lite
    - Uploaded to EAS 완료
    - Computed project fingerprint 완료
    - build URL: <https://expo.dev/accounts/parkcheolhong/projects/stock-ai-mobile/builds/dc569363-48c0-4994-8212-da1b9cacb2e4>
    - 최종 상태: ERRORED
    - error code: EAS_BUILD_UNKNOWN_GRADLE_ERROR
    - note: lightweight 복사 경로의 READ_APP_CONFIG에 expo-build-properties가 누락되어 Kotlin 고정치가 미적용됨 (plugins: expo-asset only)
- npx eas-cli build --non-interactive --platform android --profile staging (main workspace retry after Kotlin fix)
  - result: success
  - output:
    - workspace: c:/Users/WORK/source/repos/parkcheolhong/codeAI/apps/mobile-stock-ai
    - Compressed project files 완료 (1.7 GB)
    - Uploaded to EAS 완료
    - Computed project fingerprint 완료
    - build URL: <https://expo.dev/accounts/parkcheolhong/projects/stock-ai-mobile/builds/45b49aa0-bacd-40a3-a0c0-2efead2d66ff>
    - 최종 상태: FINISHED
    - artifact (apk): <https://expo.dev/artifacts/eas/9BeJtd8LrPYjbQar26PXGK.apk>
    - completedAt: 2026-04-28T02:40:38.466Z
    - metrics: buildQueueTime=38335ms, buildDuration=323559ms

## Production Submit Gate Run

- approval 문서 갱신: APPROVED: YES 반영 완료
- gate 검증 2회 통과 완료
- submit dry-run 검증 2회 통과 완료

## Notes

- EAS project linking automation script는 --dry-run 옵션으로 로컬에서 인증 없이 흐름 검증 가능
- 손절 하드게이트 임계값은 EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT로 외부화됨

## Checklist Execution Run (2026-04-28)

- Production submit (pre-check)
  - command: npm run release:dry-run:production-submit
  - result: success
  - output:
    - DRY_RUN_PASS: submit.production profile exists
    - DRY_RUN_PASS: production submit gate passed
    - DRY_RUN_PASS: validated command shape
- Production submit (actual attempt #1)
  - command: npx eas-cli submit --platform android --profile production --latest --non-interactive
  - result: failed
  - output:
    - Couldn't find any builds for this project on EAS servers (latest selector failed)
- Production submit (actual attempt #2)
  - command: npx eas-cli submit --platform android --profile production --id 45b49aa0-bacd-40a3-a0c0-2efead2d66ff --non-interactive
  - result: failed
  - output:
    - Google Service Account Keys cannot be set up in --non-interactive mode
- Production submit (interactive attempt)
  - command: npx eas-cli submit --platform android --profile production --id 45b49aa0-bacd-40a3-a0c0-2efead2d66ff
  - result: blocked
  - prompt:
    - Path to Google Service Account file required

- APK 설치/기기 검증 준비
  - command: adb devices
  - result: failed
  - output:
    - adb command not found (Android platform-tools 미설치)
  - command: adb.exe 자동 탐색 (**/adb.exe 및 일반 SDK 경로)
  - result: failed
  - output:
    - adb.exe 발견되지 않음

- 통합/API 검증 (run #1, backend not running)
  - target endpoints:
    - POST /api/llm/voice/orchestrate
    - GET /api/marketplace/metrics/summary
    - GET /api/marketplace/ml-detectors/status
  - result: failed
  - output:
    - Unable to connect to remote server (127.0.0.1:3010)

- 운영/통합 검증 환경 기동
  - task: dev-marketplace-port3010
  - output:
    - Next.js dev server ready on <http://127.0.0.1:3010>
    - TcpTestSucceeded=True for 127.0.0.1:3010

- 통합/API 검증 (run #2 after service start)
  - POST /api/llm/voice/orchestrate: status=200
  - GET /api/marketplace/metrics/summary: status=200
  - GET /api/marketplace/ml-detectors/status: status=ERR
  - ml-detectors error body:
    - MARKETPLACE_ML_STATUS_EXTERNAL_BACKEND_REQUIRED
    - 외부 ML 검출기 백엔드 URL 미설정으로 차단

- 통합/API 검증 (run #3 after service start, recheck)
  - POST /api/llm/voice/orchestrate: status=200
  - GET /api/marketplace/metrics/summary: status=200
  - GET /api/marketplace/ml-detectors/status: status=ERR
  - result: partial pass (2/3 endpoint success, 1/3 external backend missing)

## Checklist Execution Continuation (2026-04-28)

- Build 상태 재검증
  - command: npx eas-cli build:view 45b49aa0-bacd-40a3-a0c0-2efead2d66ff --json
  - result: success
  - output:
    - status: FINISHED
    - artifact: <https://expo.dev/artifacts/eas/9BeJtd8LrPYjbQar26PXGK.apk>

- Android platform-tools(adb) 자동 설치
  - command: winget install --id Google.PlatformTools -e --accept-package-agreements --accept-source-agreements
  - result: success
  - output:
    - package: Google.PlatformTools 37.0.0
    - adb/fastboot alias 추가 완료

- adb 실행 검증 (절대경로 실행)
  - command: C:/Users/WORK/AppData/Local/Microsoft/WinGet/Packages/Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe/platform-tools/adb.exe version
  - result: success
  - output:
    - Android Debug Bridge version 1.0.41
    - Version 37.0.0-14910828

- 기기 연결 검증
  - command: C:/Users/WORK/AppData/Local/Microsoft/WinGet/Packages/Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe/platform-tools/adb.exe devices
  - result: blocked
  - output:
    - List of devices attached
    - (연결된 실기기/에뮬레이터 없음)

- APK 로컬 아티팩트 준비
  - command: Invoke-WebRequest -Uri <https://expo.dev/artifacts/eas/9BeJtd8LrPYjbQar26PXGK.apk> -OutFile apps/mobile-stock-ai/artifacts/stock-ai-staging-latest.apk
  - result: success
  - output:
    - file: apps/mobile-stock-ai/artifacts/stock-ai-staging-latest.apk
    - size: 64,538,708 bytes

## Marketplace ZIP Download Fix (2026-04-28)

- issue reproduction
  - command: GET /api/marketplace/download-product?product=stock-ai-autotrader
  - result: failed (HTTP 500)
  - root cause #1:
    - route implementation used external `zip` CLI
    - Windows/runtime environment had no `zip` binary (`ZIP_COMMAND_MISSING`)
  - root cause #2:
    - first dependency install was applied to a different workspace path
    - active Next.js app (`codeAI/frontend/frontend`) could not resolve `jszip`

- fix applied
  - file: frontend/frontend/app/api/marketplace/download-product/route.ts
  - change:
    - removed `execSync(zip ...)` shell dependency
    - implemented in-process ZIP generation via `jszip`
    - added project-root fallback discovery logic for `intraday_lgbm_live`
  - dependency:
    - installed `jszip` into `codeAI/frontend/frontend/package.json`

- verification
  - command: curl -I "<http://127.0.0.1:3010/api/marketplace/download-product?product=stock-ai-autotrader>"
  - result: success (HTTP 200)
  - headers:
    - content-type: application/zip
    - content-disposition: attachment; filename="intraday_lgbm_live.zip"
    - content-length: 2070

## Marketplace ZIP Revalidation (2026-04-28, follow-up)

- endpoint validation (run #1)
  - command: Invoke-WebRequest "<http://127.0.0.1:3010/api/marketplace/download-product?product=stock-ai-autotrader>"
  - result: success (HTTP 200)
  - headers:
    - content-type: application/zip
    - content-disposition: attachment; filename="intraday_lgbm_live.zip"
    - content-length: 2070

- endpoint validation (run #2)
  - command: Invoke-WebRequest "<http://127.0.0.1:3010/api/marketplace/download-product?product=stock-ai-autotrader>"
  - result: success (HTTP 200)
  - headers:
    - content-type: application/zip
    - content-disposition: attachment; filename="intraday_lgbm_live.zip"
    - content-length: 2070

- gateway path check (local nginx)
  - command: curl -I "<http://127.0.0.1:8080/api/marketplace/download-product?product=stock-ai-autotrader>"
  - result: blocked
  - output:
    - connection refused (port 8080 listener not active)
  - note:
    - direct app route on port 3010 is healthy; gateway stack must be started separately for 8080/8443 verification
