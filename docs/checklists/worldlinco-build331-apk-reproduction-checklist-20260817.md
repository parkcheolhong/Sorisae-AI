# WorldLinco Build 331 APK 재현 체크리스트

상태: 완료됨

목적:
- 현재 프로그램에 연결된 build 331 APK의 exact-byte 기준선, 소스 커밋, 원격 빌드 입력, 게시 매니페스트를 한 문서에서 닫는다.
- 기술서만으로 331 APK를 다시 찾고, 현재 332 드리프트와 분리해 재현 경로를 고정한다.

## 1. 게시 APK 기준선

- [x] exact-byte 기준 APK 파일이 저장소에 보존되어 있다.
- 근거: `uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk` 존재 확인.
- [x] exact-byte 기준 APK의 SHA256 이 고정되어 있다.
- 근거: `SHA256=4DBEF5DC2B620D68F21841E731EAE8D2105FDCD3BF3464B8C4895E35B247F0E4`.
- [x] exact-byte 기준 APK의 바이트 수가 고정되어 있다.
- 근거: `sizeBytes=127965746`.

## 2. 게시 메타데이터 정합성

- [x] 게시 manifest 가 build 331 을 가리킨다.
- 근거: `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json` 에 `versionCode=331`.
- [x] 게시 manifest 가 versionName 1.0.246 을 가리킨다.
- 근거: 동일 manifest 에 `versionName=1.0.246`.
- [x] 게시 manifest 의 versioned filename 이 exact-byte APK 파일명과 일치한다.
- 근거: `versionedFilename=nadotongryoksa-v1.0.246-build331-current.apk`.
- [x] 모바일 APK baseline SSOT 가 같은 버전을 가리킨다.
- 근거: `knowledge/worldlinco_apk_baseline.json` 에 `versionCode=331`, `versionName=1.0.246`, `probe_min_build=323`.

## 3. 소스 커밋과 빌드 입력

- [x] 실제 EAS build 331 의 소스 커밋이 특정돼 있다.
- 근거: EAS build view `gitCommitHash=2494f4c6fe37ac794be7d292659d60f2d2d04864`.
- [x] 해당 커밋의 앱 설정이 build 331 을 가리킨다.
- 근거: `git show 2494f4c6fe37ac794be7d292659d60f2d2d04864:apps/mobile-nadotongryoksa/app.json` 결과 `expo.version=1.0.246`, `expo.android.versionCode=331`.
- [x] 해당 커밋의 모바일 EAS 설정이 local app version source 를 사용한다.
- 근거: `git show 2494f4c6fe37ac794be7d292659d60f2d2d04864:apps/mobile-nadotongryoksa/eas.json` 결과 `cli.appVersionSource=local`.
- [x] 원격 빌드 증적이 build 331 을 기록한다.
- 근거: `docs/checklists/evidence/eas-build-watch-20260813_042324/last-build-view.json` 에 `appVersion=1.0.246`, `appBuildVersion=331`, `build id=bd968eb2-9176-4060-8b34-4b2d5d10ca7d`.

## 4. 실기기 설치 증적

- [x] 실기기 설치 상태가 build 331 을 확인한다.
- 근거: `apps/mobile-nadotongryoksa/evidence/device-validation-20260813/run1_permissions_and_version.txt` 에 `versionCode=331`, `versionName=1.0.246`, `targetSdk=36`.

## 5. 드리프트 차단 규칙

- [x] 현재 작업트리의 모바일 소스가 이미 332 로 올라간 사실을 확인했다.
- 근거: `apps/mobile-nadotongryoksa/app.json` 현재값 `versionCode=332`, `versionName=1.0.247`.
- [x] 현재 네이티브 Gradle 값도 332 로 올라간 사실을 확인했다.
- 근거: `apps/mobile-nadotongryoksa/android/app/build.gradle` 현재값 `versionCode 332`, `versionName "1.0.247"`.
- [x] 루트 EAS 설정은 331 재현 기준이 아님을 확인했다.
- 근거: 루트 `eas.json` 현재값 `cli.appVersionSource=remote`; 모바일 331 기준은 앱 전용 `apps/mobile-nadotongryoksa/eas.json`.

## 6. 재현 결론

- [x] exact-byte 331 APK 재현 기준은 저장소 보존 아티팩트와 해시/바이트 수로 닫혔다.
- 근거: 섹션 1, 2 통과.
- [x] source-lineage 331 재현 기준은 커밋 `2494f4c6fe37ac794be7d292659d60f2d2d04864` 와 앱 전용 EAS/app 설정으로 닫혔다.
- 근거: 섹션 3 통과.
- [x] 기술서에 332 드리프트 차단 규칙과 331 재현 절차를 반영했다.
- 근거: `docs/program-birth-and-technical-dossier-20260516.md` 3.1절.
- [x] 새 리허설 증적 디렉터리를 추가로 만들었다.
- 근거: `docs/checklists/evidence/build331-rehearsal-20260818-003405/` 생성 및 `rehearsal-summary.md`, `apk_hash.txt`, `device_dumpsys.txt` 확인.
