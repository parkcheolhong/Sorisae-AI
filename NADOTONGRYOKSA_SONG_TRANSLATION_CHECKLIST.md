# FILE-ID: FILE-NADOTONGRYOKSA-SONG-TRANSLATION-CHECKLIST-MD
# SECTION-ID: SECTION-NADOTONGRYOKSA-SONG-TRANSLATION-CHECKLIST-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-VERIFICATION-GATE
# CHUNK-ID: CHUNK-NADOTONGRYOKSA-SONG-TRANSLATION-CHECKLIST-001

# 나도통역사 노래 파일 번역 자막 체크리스트

## 현재 상태

- 상태: 완료됨
- 작성일: 2026-05-08
- 설계 문서: `NADOTONGRYOKSA_SONG_TRANSLATION_DESIGN.md`
- 원칙: 실제 검증 근거가 확인된 항목만 완료로 체크한다.

## 범위

- 모바일 다운로드 노래 파일 업로드.
- 백엔드 비동기 Job 기반 처리.
- 원어 가사 자동 감지/추출.
- 자국어 번역 자막 생성.
- 세그먼트별 편집.
- SRT/VTT/LRC/JSON 내보내기.
- 모바일 재생 싱크 자막 표시.

## 체크리스트

- [x] 설계 문서 파일 생성
  - 근거: `NADOTONGRYOKSA_SONG_TRANSLATION_DESIGN.md` 생성.
- [x] 체크리스트 파일 생성
  - 근거: `NADOTONGRYOKSA_SONG_TRANSLATION_CHECKLIST.md` 생성.
- [x] 백엔드 패키지 구조 생성
  - 대상: `backend/mobile/song_translation/`.
  - 근거: `backend/mobile/song_translation/{schemas,language,subtitles,service,router}.py` 생성 및 계약 테스트 2회 import 통과.
- [x] 백엔드 API 계약 구현
  - 대상: 작업 생성, 상태 조회, 자막 조회, 세그먼트 편집, 내보내기.
  - 근거: `python -m pytest backend/tests/test_nadotongryoksa_song_translation_contract.py -q` 2회 통과.
- [x] 파일 검증/보안 가드 구현
  - 대상: 확장자, MIME, 크기, 파일명 sanitize.
  - 근거: 정상 업로드, 확장자 거부, MIME 거부, 빈 파일 거부, 크기 제한, 파일명 sanitize 테스트 2회 통과.
- [x] 세그먼트 타임라인 엔진 구현
  - 대상: start/end ms, confidence, quality_flags.
  - 근거: 세그먼트 타임라인 조회와 SRT/VTT/LRC/JSON export 테스트 2회 통과.
- [x] 번역 자막 생성 구현
  - 대상: lyrics 모드 번역, 빈 번역/동일 번역 재시도 후보 플래그.
  - 근거: 내장 사전 번역 및 동일 번역 재시도 후보 플래그 테스트 2회 통과.
- [x] 모바일 파일 선택 UI 구현
  - 대상: `expo-document-picker`, 업로드 진행률, job 상태 표시.
  - 근거: `expo-document-picker` 추가, 파일 선택/업로드/Job polling UI 구현, TypeScript 2회 통과, Android Expo prebuild 2회 통과, 브라우저 모바일 화면에서 파일 선택/100% 진행률 확인, ADB 연결 Android 에뮬레이터에서 `노래 파일 선택` 버튼과 Android DocumentsUI 파일 선택기 실행 확인.
- [x] 모바일 자막 편집 UI 구현
  - 대상: 원문/번역/시간/품질 플래그 표시, 세그먼트 편집.
  - 근거: 세그먼트 TextInput 편집, 저장 PATCH, SRT/VTT/LRC/JSON export 미리보기 UI 구현, TypeScript 2회 통과, Android Expo prebuild 2회 통과, 브라우저 모바일 화면에서 `SCREEN_EDIT_PASS` 저장/export 반영 확인.
- [x] 모바일 재생 싱크 구현
  - 대상: `expo-av` 재생 위치 기준 현재 자막 강조.
  - 근거: `expo-av` Sound 재생/일시정지와 positionMillis 기준 현재 자막 강조 구현, 브라우저 모바일 화면에서 `현재 0:00 · 1번 자막` 및 활성 자막 표시 확인, ADB 연결 Android 에뮬레이터에서 실제 음성 WAV 2개 선택 후 재생 위치와 현재 자막 번호 이동 2회 확인.
- [x] 3분 이상 노래 길이 대응 보강
  - 대상: 3분 이상 음원 처리 대기, 장시간 자막 타임라인, SRT export.
  - 근거: 모바일 Job polling 한도를 약 6분으로 확장, `npm run typecheck` 2회 통과, 공개 운영 API에서 `nado-3min-seed.mp3` 처리 결과 `duration_ms=247250`, `segment_count=30`, SRT export `7945` chars 확인.
- [x] 실제 3분 이상 영어 음성 가사 STT/한국어 번역 검증
  - 대상: seed payload가 아닌 실제 음성 MP3의 자동 언어 감지, 원문 추출, 한국어 번역, 자막 타임라인.
  - 근거: 공개 운영 API에서 `nado-3min-english-lyrics-a-24k.mp3`와 `nado-3min-english-lyrics-b-24k.mp3` 2회 처리 완료, `source_language=en`, `target_language=ko`, 각각 3분 이상, `segment_count=30`, 원문/번역 30개 세그먼트 모두 채워짐, `detected_by=voice` 확인.
- [x] 실제 3분 이상 Android 파일 선택/재생 싱크 2회 검증
  - 대상: Android DocumentsUI 파일 선택, 모바일 업로드/처리 완료, 재생 위치 기반 현재 자막 번호 이동.
  - 근거: `nado-3min-english-lyrics-a-24k.mp3` 선택 후 `English → 한국어 · 30개 구간 · 품질 80%`, 재생 중 `현재 0:39 · 6번 자막`; `nado-3min-english-lyrics-b-24k.mp3` 선택 후 `English → 한국어 · 30개 구간 · 품질 83%`, 재생 중 `현재 0:29 · 5번 자막` 확인.
- [x] 음성 STT 후 텍스트/타임라인 후처리 구조 성능 판단 반영
  - 대상: 음성 인식 결과를 텍스트/JSON 중간 산출물로 저장하고 편집부가 가사 후처리하는 구조.
  - 근거: 설계 문서에 STT/번역이 병목이고 텍스트/JSON 파일 읽기/쓰기는 3분 곡 기준 미미하다는 판단 및 JSON 타임라인 권장 구조 반영.
- [x] 공개 nginx 업로드 크기 제한 계약 정합성 보강
  - 대상: 백엔드 100MB 업로드 계약과 공개 nginx request body 제한 정합성.
  - 근거: 1.7MB/1.5MB 3분 MP3 업로드가 기존 `413 Request Entity Too Large`로 차단됨을 확인한 뒤 `client_max_body_size 100m` 적용, `docker exec devanalysis114-nginx nginx -t`, `nginx -s reload` 통과, 동일 경로에서 64kbps 3분 MP3 2개 job 생성 및 `completed/subtitle_ready` 확인.
- [x] 운영/실서버 실검증
  - 대상: 업로드, 상태 조회, 자막 조회, 편집, export.
  - 근거: 실행 중인 `devanalysis114-backend` 컨테이너의 `http://127.0.0.1:8000` 실제 API 호출 2회 통과, 공개 운영 도메인 `https://metanova1004.com` 실제 API 호출 2회 통과, 실제 3분 이상 영어 음성 MP3 공개 운영 STT/번역 2회 통과.

## 검증 기록

| 순서 | 명령/방법 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 문서 파일 생성 | 통과 | 설계/체크리스트 파일 생성 |
| 2 | `python -m pytest backend/tests/test_nadotongryoksa_song_translation_contract.py -q` | 통과 | 5 passed in 0.35s |
| 3 | `python -m pytest backend/tests/test_nadotongryoksa_song_translation_contract.py -q` | 통과 | 5 passed in 0.31s |
| 4 | `git diff --check -- ...` | 통과 | 출력 없음 |
| 5 | `npm run typecheck` | 통과 | 모바일 앱 TypeScript 오류 없음 |
| 6 | `npm run typecheck` | 통과 | 모바일 앱 TypeScript 오류 없음 |
| 7 | `git diff --check -- ...` | 통과 | 백엔드/모바일 변경 전체 출력 없음 |
| 8 | `curl`/`Invoke-RestMethod` against `http://127.0.0.1:8000/api/mobile/song-translation` | 통과 | `songjob_db956865823c4a90`, completed, 3 segments, edit/export 반영 |
| 9 | `curl`/`Invoke-RestMethod` against `http://127.0.0.1:8000/api/mobile/song-translation` | 통과 | `songjob_40c66b587f0b4afe`, completed, 3 segments, edit/export 반영 |
| 10 | `curl`/`Invoke-RestMethod` against `https://metanova1004.com/api/mobile/song-translation` | 통과 | `songjob_07e32e106d1244da`, completed, 3 segments, `PROD_EDIT_PASS_A` export 반영 |
| 11 | `curl`/`Invoke-RestMethod` against `https://metanova1004.com/api/mobile/song-translation` | 통과 | `songjob_74c12f6309ea4d8c`, completed, 3 segments, `PROD_EDIT_PASS_B` export 반영 |
| 12 | `npx expo prebuild --platform android --no-install` | 통과 | 1차 `Finished prebuild`, 권장 경고: `expo-system-ui` 미설치 |
| 13 | `npx expo prebuild --platform android --no-install` | 통과 | 2차 `Finished prebuild`, 권장 경고: `expo-system-ui` 미설치 |
| 14 | `adb devices -l` + `adb shell getprop sys.boot_completed` | 통과 | `emulator-5554 device`, Android 14, boot_completed=1 |
| 15 | Expo Web `http://localhost:19006` 모바일 뷰포트 화면 검증 | 통과 | 파일 선택 버튼 표시, 파일 업로드 후 English → 한국어 3개 자막, 100% 진행률, SRT 미리보기 확인 |
| 16 | Expo Web `http://localhost:19006` 모바일 뷰포트 편집 검증 | 통과 | `SCREEN_EDIT_PASS` 저장 후 SRT export 미리보기 반영 |
| 17 | `npm run typecheck` | 통과 | 최종 모바일 변경 후 TypeScript 오류 없음 |
| 18 | `npm run typecheck` | 통과 | 최종 모바일 변경 후 TypeScript 오류 없음 |
| 19 | `npx expo prebuild --platform android --no-install` | 통과 | 최종 모바일 변경 후 1차 `Finished prebuild`, 권장 경고 동일 |
| 20 | `npx expo prebuild --platform android --no-install` | 통과 | 최종 모바일 변경 후 2차 `Finished prebuild`, 권장 경고 동일 |
| 21 | `git diff --check -- ...` | 통과 | 추적 변경 파일 기준 출력 없음 |
| 22 | `npm run android` with `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT` | 통과 | `BUILD SUCCESSFUL`, `com.shinsegye.nadotongryoksa` installed/launched on `Pixel_6_API_34` |
| 23 | ADB screenshot/UI dump | 통과 | `tmp/nadotongryoksa_android_verify/nado_android_main.png`, UI tree에 `노래 파일 선택` 확인 |
| 24 | ADB tap `노래 파일 선택` + DocumentsUI screenshot/UI dump | 통과 | `tmp/nadotongryoksa_android_verify/nado_android_documentsui.png`, package `com.google.android.documentsui`, `Recent` 파일 선택기 표시 |
| 25 | ADB DocumentsUI actual file selection A | 통과 | `tmp/nadotongryoksa_android_verify/nado_sync_a_ready_after_poll.png/xml`, `nado-lyric-sync-a.wav`, `subtitle_ready`, `100%`, `현재 0:00 · 1번 자막` |
| 26 | ADB playback sync A | 통과 | `tmp/nadotongryoksa_android_verify/nado_sync_a_playing.png/xml`, `일시정지`, `현재 0:05 · 3번 자막` |
| 27 | ADB DocumentsUI actual file selection B | 통과 | `tmp/nadotongryoksa_android_verify/nado_sync_b_ready_final.png/xml`, `nado-lyric-sync-b.wav`, `파일 자막 준비: 한국어 → 한국어 · 3개 구간 · 품질 56%`, `현재 0:00 · 1번 자막` |
| 28 | ADB playback sync B | 통과 | `tmp/nadotongryoksa_android_verify/nado_sync_b_playing.png/xml`, `일시정지`, `현재 0:05 · 3번 자막` |
| 29 | `git diff --check -- NADOTONGRYOKSA_SONG_TRANSLATION_CHECKLIST.md` | 통과 | 출력 없음 |
| 30 | `npm run typecheck` after 3분 polling 보강 | 통과 | 모바일 앱 TypeScript 오류 없음 |
| 31 | `npm run typecheck` after 3분 polling 보강 | 통과 | 모바일 앱 TypeScript 오류 없음 |
| 32 | `https://metanova1004.com/api/mobile/song-translation` 3분 이상 seed 업로드 | 통과 | `songjob_e53ea1c68d2f4d42`, `nado-3min-seed.mp3`, queued 생성 |
| 33 | `https://metanova1004.com/api/mobile/song-translation/jobs/songjob_e53ea1c68d2f4d42/subtitles` | 통과 | `subtitle_ready`, `duration_ms=247250`, `segment_count=30`, first `0-8000`, last `239250-247250`, SRT `7945` chars |
| 34 | `git diff --check -- apps/mobile-nadotongryoksa/App.tsx` | 통과 | 출력 없음 |
| 35 | 3분 이상 영어 음성 MP3 생성 | 통과 | `nado-3min-english-lyrics-a-24k.mp3` `duration_ms=201019`, `nado-3min-english-lyrics-b-24k.mp3` `duration_ms=184818` |
| 36 | 공개 운영 API 실제 3분 이상 영어 음성 STT/번역 A | 통과 | `songjob_644f690d66484f3d`, `completed`, `subtitle_ready`, `source_language=en`, `target_language=ko`, `duration_ms=199840`, `segment_count=30`, `quality_score=0.8` |
| 37 | 공개 운영 API 실제 3분 이상 영어 음성 STT/번역 B | 통과 | `songjob_0825bf7e9b2049be`, `completed`, `subtitle_ready`, `source_language=en`, `target_language=ko`, `duration_ms=184500`, `segment_count=30`, `quality_score=0.83` |
| 38 | 공개 운영 API 자막 타임라인 원문/번역 검증 A/B | 통과 | `nado-3min-english-lyrics-prod-subtitle-summary-v2.json`, A/B 모두 `original_non_empty=30`, `translated_non_empty=30`, `detected_by_values=voice` |
| 39 | Android DocumentsUI 3분 영어 MP3 A 선택 | 통과 | `nado-3min-mobile-a-ready-check.png/xml`, `nado-3min-english-lyrics-a-24k.mp3`, `English → 한국어 · 30개 구간 · 품질 80%`, `100%`, 첫 원문/번역 표시 |
| 40 | Android 3분 영어 MP3 A 재생 싱크 | 통과 | `nado-3min-mobile-a-playing.png/xml`, `일시정지`, `현재 0:39 · 6번 자막` |
| 41 | Android DocumentsUI 3분 영어 MP3 B 선택 | 통과 | `nado-3min-mobile-b-ready.png/xml`, `nado-3min-english-lyrics-b-24k.mp3`, `English → 한국어 · 30개 구간 · 품질 83%`, `100%`, 첫 원문/번역 표시 |
| 42 | Android 3분 영어 MP3 B 재생 싱크 | 통과 | `nado-3min-mobile-b-playing.png/xml`, `일시정지`, `현재 0:29 · 5번 자막` |
| 43 | 공개 nginx 업로드 제한 오류 재현 | 통과 | `nado-3min-lyrics-a-upload-response.txt`, `nado-3min-lyrics-a-mp3-upload-response.txt`, 기존 응답 `413 Request Entity Too Large` 확인 |
| 44 | 공개 nginx 업로드 제한 수정 검증 | 통과 | `client_max_body_size 100m`, `docker exec devanalysis114-nginx nginx -t`, `nginx -s reload` 성공 |
| 45 | 공개 운영 64kbps 3분 MP3 업로드 2회 | 통과 | `songjob_758acef8ed354ceb`, `songjob_95db3538489a431c`, 기존 413 없이 queued 생성 확인 |
| 46 | 공개 운영 64kbps 3분 MP3 최종 처리 2회 | 통과 | `songjob_758acef8ed354ceb` completed/subtitle_ready, `duration_ms=199840`, `segment_count=30`, `quality_score=0.81`; `songjob_95db3538489a431c` completed/subtitle_ready, `duration_ms=184500`, `segment_count=30`, `quality_score=0.83` |

## 보류 항목

- 실제 보컬 분리와 자국어 가창 음원 합성은 1차 범위에서 제외한다.
- 저작권 있는 노래의 공개 배포용 번역 가사 생성은 지원하지 않는다.
