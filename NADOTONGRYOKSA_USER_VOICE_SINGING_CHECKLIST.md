<!-- FILE-ID: FILE-NADOTONGRYOKSA-USER-VOICE-SINGING-CHECKLIST-MD -->
<!-- SECTION-ID: SECTION-NADOTONGRYOKSA-USER-VOICE-SINGING-CHECKLIST-MAIN -->
<!-- FEATURE-ID: FEATURE-NADOTONGRYOKSA-USER-VOICE-SINGING-VERIFICATION-GATE -->
<!-- CHUNK-ID: CHUNK-NADOTONGRYOKSA-USER-VOICE-SINGING-CHECKLIST-001 -->

# 나도통역사 사용자 목소리 번역가사 음성 Preview 체크리스트

## 현재 상태

- 상태: 백엔드/모바일 UI/운영 API/Android 전체 조작 검증 2회 통과, 고급 가창/배포 안전 경계 계약 테스트 2회 통과
- 작성일: 2026-05-08
- 설계 문서: `NADOTONGRYOKSA_USER_VOICE_SINGING_DESIGN.md`
- 선행 기능: `NADOTONGRYOKSA_SONG_TRANSLATION_DESIGN.md`
- 원칙: 실제 검증 근거가 확인된 항목만 완료로 체크한다.
- 범위 고정: 이 기능은 가사 번역 프로그램의 개인 음성 preview 확장이 기본이며, 공유/export/편곡형 산출물은 권리 확인과 정책 승인 후 열리는 확장 경로로 둔다.

## 범위

- 사용자 본인 목소리 사용 동의.
- 음성 샘플 녹음/업로드.
- 목소리 프로필 생성, 암호화 저장, 삭제.
- 권리 모드 분류와 export 정책 게이트.
- 번역 가사 타임라인 기반 사용자 목소리 TTS preview.
- 공개 공유와 배포용 음원 export의 정책 게이트 관리.
- Android 모바일 UI와 운영 API 실검증.

## 체크리스트

- [x] 사용자 목소리 번역가사 음성 preview 설계 문서 생성
  - 근거: `NADOTONGRYOKSA_USER_VOICE_SINGING_DESIGN.md` 생성.
- [x] 사용자 목소리 번역가사 음성 preview 체크리스트 파일 생성
  - 근거: `NADOTONGRYOKSA_USER_VOICE_SINGING_CHECKLIST.md` 생성.
- [x] 가사 번역 프로그램 범위 고정
  - 근거: 설계 문서에 핵심 산출물을 원문/번역 가사, 자막, JSON 타임라인으로 고정하고 공유/export/편곡형 산출물은 정책 승인 후 열리는 확장 경로로 명시.
- [x] 동의 게이트 API 계약 구현
  - 대상: `POST /api/mobile/song-translation/voice-consents`.
  - 통과 기준: 동의 없는 voice profile 생성 차단 테스트 2회 통과.
  - 근거: `backend/tests/test_nadotongryoksa_song_translation_contract.py` 2회 통과, 운영 도메인 consent/profile/preview 2회 통과.
- [x] 권리 게이트 정책 구현
  - 대상: `self_created`, `licensed`, `public_domain`, `private_preview_unverified`, `policy_approved_distribution`.
  - 통과 기준: 기본 private preview, 사용자 권리 선언, 책임 고지, 운영 승인 후 export 후보 승격 테스트 2회 통과.
  - 근거: 운영 1차 `policy_approved_export/allowed`, 운영 2차 `private_preview/review_required` 통과.
- [x] 사용자 음성 샘플 업로드 구현
  - 대상: 음성 샘플 기본 길이/품질 추정, MIME, 확장자, 파일 크기, 무음/손상 샘플 거부.
  - 통과 기준: 정상 샘플과 실패 샘플 계약 테스트 2회 통과.
  - 근거: 정상 샘플 profile 생성, 무음 샘플 거부, 운영 voice profile 생성 2회 통과.
- [x] 목소리 프로필 저장/삭제 구현
  - 대상: `voice_profile_id`, 암호화 샘플 저장, 삭제/철회, 삭제 후 profile 접근 차단.
  - 통과 기준: 삭제 후 암호화 샘플 파일 제거와 profile 조회 불가 검증 2회 통과.
  - 근거: 암호화 샘플 파일 생성/삭제 후 profile 조회 404 계약 테스트 2회 통과.
- [x] 모바일 `내 목소리로 번역가사 듣기` UI 구현
  - 대상: 동의 화면, 샘플 녹음/업로드, 프로필 상태, 삭제 버튼.
  - 통과 기준: TypeScript 2회, Android 화면 검증 2회 통과.
  - 근거: `npm run typecheck` 2회 통과, Android UI dump 2회에서 `내 목소리 번역가사 preview`, `샘플 녹음`, `샘플 파일 업로드`, `권리 모드` 확인.
- [x] 번역 타임라인 기반 voice preview job 구현
  - 대상: 기존 song translation job의 JSON 타임라인 입력, 사용자 voice profile 연결, 개인 preview 산출물 생성.
  - 통과 기준: 자체 제작 3분 이상 음원으로 preview job 2회 completed 검증.
  - 근거: 운영 도메인 3분 음원 A/B에서 voice preview 2회 생성, `duration_ms=199840/184500`, `segment_count=30/30`.
- [x] 안전 export 정책 구현
  - 대상: 번역 자막/JSON은 정책 범위 안에서 허용, 공개 공유와 배포용 음원 export는 권리 확인/책임 고지/운영 승인 후 활성화.
  - 통과 기준: 기본 보류/승격/허용 케이스 운영 API 2회 통과.
  - 근거: 운영 1차 승인 export 허용, 운영 2차 권리 미확인 export 요청 private preview 보류.
- [x] 운영 API 실검증
  - 대상: 동의, 프로필, preview, export policy.
  - 통과 기준: `https://metanova1004.com/api/mobile/song-translation` 기준 2회 통과.
  - 근거: `songjob_79686f565cef4f53`, `songjob_a60d0240fa794842` 운영 API 완료.
- [x] Android 실기기/에뮬레이터 실검증
  - 대상: 동의 UI, 샘플 업로드, preview 재생, 삭제.
  - 통과 기준: Android DocumentsUI/녹음/재생 화면 증거 2회 확보.
  - 근거: Round 1 실제 `샘플 녹음` 시작/종료 후 업로드, preview 생성/듣기, 삭제 통과. Round 2 Android DocumentsUI 샘플 파일 업로드, preview 생성/듣기, 삭제 통과.
- [x] 고급 가창/배포 안전 경계 계약 테스트 고정
  - 대상: pitch/emotion/final mastering, 노래 개사/편곡/커버 음원, 마켓플레이스 export, 원가수/제3자 목소리 복제 요청.
  - 통과 기준: 번역가사 확인용 `translated_lyric_voice` 외 preview mode 거부, `marketplace_export` 범위 거부, `voice_owner=self` 외 동의 거부, 운영 승인 ID 없는 배포 export는 review required로 하향.
  - 근거: `backend/tests/test_nadotongryoksa_song_translation_contract.py` 9개 계약 테스트 2회 통과.

## 검증 기록

| 순서 | 명령/방법 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 문서 파일 생성 | 통과 | 설계/체크리스트 파일 생성 |
| 2 | 가사 번역 프로그램 범위 보정 | 통과 | 공유/export/편곡형 산출물은 정책 승인 후 열리는 확장 경로로 명시 |
| 3 | 백엔드 계약 테스트 1차 | 통과 | `8 passed in 0.56s` |
| 4 | 백엔드 계약 테스트 2차 | 통과 | `8 passed in 0.39s` |
| 5 | 모바일 TypeScript 1차 | 통과 | `npm run typecheck` |
| 6 | 모바일 TypeScript 2차 | 통과 | `npm run typecheck` |
| 7 | Android UI 화면 1차 | 통과 | `nado_voice_ui_1_scrolled.xml`에서 샘플/권리/preview 컨트롤 확인 |
| 8 | Android UI 화면 2차 | 통과 | `nado_voice_ui_2_panel.xml`에서 샘플/권리/preview 컨트롤 확인 |
| 9 | 운영 API 1차 | 통과 | `songjob_79686f565cef4f53`, `voicepreview_f8278b8a54dd429f`, `policy_approved_export/allowed` |
| 10 | 운영 API 2차 | 통과 | `songjob_a60d0240fa794842`, `voicepreview_57d45e91ef0e4d0a`, `private_preview/review_required` |
| 11 | Android 전체 조작 1차 | 통과 | `round1_recording_started.xml`, `round1_profile_ready.xml`, `round1_preview_ready.xml`, `round1_preview_listen_tapped.xml`, `round1_profile_deleted.xml` |
| 12 | Android 전체 조작 2차 | 통과 | `round2_upload_picker.xml`, `round2_profile_ready.xml`, `round2_preview_ready.xml`, `round2_preview_listen_tapped.xml`, `round2_profile_deleted.xml` |
| 13 | 안전 경계 계약 테스트 1차 | 통과 | `9 passed in 0.52s` |
| 14 | 안전 경계 계약 테스트 2차 | 통과 | `9 passed in 0.37s` |

## 정책 게이트 고정 규칙

- 실제 고급 가창 모델의 pitch/emotion/final mastering은 1차 preview 이후에도 가사 번역 확인 범위 안에서만 검토한다.
- 노래 개사, 편곡, 배포용 커버 음원 제작은 기본 기능이 아니며 정책 승인형 확장 경로로 둔다.
- 권리 확인 없는 상용곡의 공개 배포, 판매, 마켓플레이스 등록은 기본 보류한다.
- 원가수 또는 제3자의 목소리 복제는 명시적 허가 전까지 지원하지 않는다.
