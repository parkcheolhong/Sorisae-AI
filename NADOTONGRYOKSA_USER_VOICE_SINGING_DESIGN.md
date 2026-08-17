# FILE-ID: FILE-NADOTONGRYOKSA-USER-VOICE-SINGING-DESIGN-MD
# SECTION-ID: SECTION-NADOTONGRYOKSA-USER-VOICE-SINGING-DESIGN-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-USER-VOICE-SINGING-SAFE-PIPELINE
# CHUNK-ID: CHUNK-NADOTONGRYOKSA-USER-VOICE-SINGING-DESIGN-001

# 나도통역사 사용자 목소리 번역가사 음성 Preview 안전 설계

## 현재 상태

- 상태: 설계됨
- 작성일: 2026-05-08
- 선행 문서: `NADOTONGRYOKSA_SONG_TRANSLATION_DESIGN.md`
- 목표: 사용자가 본인 목소리로 동의한 경우에만 목소리 프로필을 만들고, 가사 번역 결과를 사용자 목소리 기반 개인 preview로 확인할 수 있게 한다.

## 제품 목표

기존 노래 파일 번역 자막 기능은 원어 가사 STT, 번역, 자막 편집, 재생 싱크까지 처리한다. 새 확장은 이 흐름 위에 사용자 본인 목소리 프로필, 동의 게이트, 안전한 번역가사 음성 preview를 단계적으로 추가한다.

1차 구현은 고급 가창 모델을 곧바로 운영에 여는 방식이 아니다. 먼저 사용자가 직접 녹음한 목소리 샘플로 번역 가사를 짧게 읽어 주는 TTS preview를 만들고, 권리와 동의 조건을 통과한 작업만 개인 저장 대상으로 승격한다.

## 제품 범위 고정

이 프로그램은 가사 번역 프로그램이다. 핵심 산출물은 원문 가사, 번역 가사, 타임스탬프 자막, 편집 가능한 JSON 타임라인이다. 사용자 목소리 기능은 번역 가사를 더 자연스럽게 확인하기 위한 개인 음성 preview 보조 기능이며, 기본 모드는 노래를 개사하거나 편곡해 배포용 음원으로 제작하는 프로그램이 아니다.

다만 기능을 영구 차단하지는 않는다. 공개 공유, 배포용 음원 export, 편곡/가창형 산출물은 `policy_locked` 상태로 두고, 사용자가 권리 확인과 책임 고지를 통과하거나 운영자가 승인한 경우에만 제한적으로 열 수 있는 확장 경로로 둔다.

## 헌법 규칙

- 원가수 또는 제3자의 목소리 복제는 명시적 허가 없이는 금지한다.
- 사용자 본인 목소리는 명시적 동의, 삭제 기능, 사용 이력 기록이 있을 때만 프로필화한다.
- 상용곡의 멜로디, 가사, 편곡, 반주는 사용자 목소리로 바꿔도 권리 문제가 사라지지 않는다.
- 공개 배포, 판매, 마켓플레이스 등록, 배포용 음원 export는 기본 비활성화 상태로 두고, 권리 확인/사용자 책임 고지/운영 정책 통과 시에만 별도 활성화한다.
- 권리 미확인 상용곡은 기본적으로 개인 preview 범위에 머물며, 사용자가 권리 보유 또는 허가를 선언하고 정책 게이트를 통과한 경우에만 저장/공유/export 후보로 승격한다.

## 비범위

- 권리 확인 없는 상용곡의 공개 배포용 번역 가창 음원 생성.
- 권리 확인 없는 노래 개사, 편곡, 배포용 커버 음원 제작.
- 원가수와 혼동될 수 있는 목소리 모방, 보이스 클론, 스타일 복제.
- 사용자가 업로드한 상용곡 보컬을 학습 데이터로 재사용하는 기능.
- 사용자 목소리 프로필을 다른 사용자나 마켓플레이스 상품에 공유하는 기능.

## 사용자 흐름

1. 사용자는 노래 전용 모드에서 `내 목소리로 번역가사 듣기`를 선택한다.
2. 앱은 목소리 사용 동의, 삭제 권리, 공개 배포 금지, 권리 확인 범위를 표시한다.
3. 사용자는 안내 문장을 20초에서 60초 정도 녹음한다.
4. 백엔드는 샘플 품질, 잡음, 길이, 본인 동의 체크를 검증한다.
5. 통과 시 사용자 계정에 묶인 `voice_profile_id`를 생성한다.
6. 노래 파일은 기존 STT/번역/자막 파이프라인을 먼저 통과한다.
7. 권리 게이트가 작업 모드를 결정한다.
8. 허가된 작업은 사용자 목소리 번역가사 preview, SRT/JSON, 편집 산출물을 생성한다.
9. 권리 미확인 작업은 개인 preview로 시작하고, 권리 확인/책임 고지/운영 정책 통과 시 외부 공유와 배포용 음원 export 후보로 승격할 수 있다.
10. 사용자는 언제든 음성 프로필과 관련 산출물을 삭제할 수 있다.

## 권리 게이트

```text
Audio intake
  -> Ownership declaration
  -> License mode classification
  -> Consent validation
  -> Export policy decision
```

라이선스 모드:

- `self_created`: 사용자가 직접 만든 곡. 번역 자막, 개인 preview, 사용자 선택 export 허용.
- `licensed`: 사용자가 라이선스를 보유한 곡. 증빙/체크 후 번역 자막, 개인 preview, 정책 범위 내 export 허용.
- `public_domain`: 공개 허용 또는 퍼블릭 도메인. 번역 자막, 개인 preview, 정책 범위 내 export 허용.
- `private_preview_unverified`: 권리 미확인 상용곡. 기본은 개인 preview이며, 권리 선언/책임 고지/운영 정책 통과 시 제한 export 후보로 승격.
- `policy_approved_distribution`: 운영자 또는 자동 정책 심사를 통과한 배포 가능 작업. 감사 로그와 사용자 책임 고지를 포함해 공유/export 활성화.

## 사용자 목소리 프로필

```text
Voice consent
  -> Voice sample recording
  -> Sample quality check
  -> Profile embedding generation
  -> Encrypted storage
  -> User-bound synthesis permission
  -> Delete/revoke path
```

프로필 필수 속성:

- `voice_profile_id`
- `user_id`
- `consent_version`
- `consent_accepted_at`
- `sample_duration_ms`
- `sample_quality_score`
- `storage_key`
- `encrypted`
- `status`
- `revoked_at`
- `last_used_at`

## 번역가사 음성 Preview 단계

```text
Translated lyric timeline
  -> Speech-safe line normalization
  -> User voice TTS preview
  -> Preview audio render
  -> Preview/export policy gate
```

1차 preview는 박자와 피치가 완벽한 최종 음원이 아니라, 사용자 목소리로 번역 가사를 읽어 주는 확인용 결과물로 둔다. 노래 개사, 편곡, 반주 믹싱, 배포용 mastering은 기본 기능에서 제외하되, 기능 코드는 정책 게이트 뒤에 확장 가능하도록 열어 둔다. 이후 고도화가 필요하면 번역 가사 이해를 중심으로 pitch guide, phoneme alignment, phrase duration fitting을 먼저 적용하고, 배포 목적 기능은 별도 권리 게이트를 통과한 경우에만 활성화한다.

## API 계약 초안

### 동의 생성

```http
POST /api/mobile/song-translation/voice-consents
Content-Type: application/json
```

```json
{
  "consent_version": "2026-05-voice-v1",
  "voice_owner": "self",
  "allow_private_preview": true,
  "allow_export_for_licensed_audio": true
}
```

### 목소리 프로필 생성

```http
POST /api/mobile/song-translation/voice-profiles
Content-Type: multipart/form-data
```

필드:

- `sample`: 사용자 본인 목소리 녹음 파일.
- `consent_id`: 동의 ID.
- `profile_label`: 사용자 지정 라벨.

### 번역가사 음성 preview 생성

```http
POST /api/mobile/song-translation/jobs/{job_id}/voice-preview
Content-Type: application/json
```

```json
{
  "voice_profile_id": "voice_...",
  "license_mode": "self_created",
  "preview_mode": "translated_lyric_voice",
  "output_scope": "private_preview",
  "rights_acknowledged": false
}
```

`output_scope` 값은 `private_preview`, `user_saved_preview`, `policy_review_export`, `policy_approved_export`로 나눈다. 기본값은 `private_preview`이며, 사용자가 책임 고지를 확인하고 권리 모드를 선언한 경우에만 다음 단계로 올라간다.

## 보안/프라이버시

- 목소리 샘플과 프로필은 계정 단위로 암호화 저장한다.
- 프로필 삭제 요청은 원본 샘플, 임베딩, preview 캐시까지 삭제해야 한다.
- 모든 preview 요청은 `voice_profile_id`, `consent_id`, `job_id`, `license_mode`, `output_scope`를 감사 로그에 남긴다.
- 권리 미확인 작업은 기본적으로 외부 URL, ZIP, marketplace export, 공개 공유, 배포용 음원 export를 보류한다. 단, `policy_approved_distribution`으로 승격된 작업은 감사 로그와 사용자 책임 고지를 남기고 활성화할 수 있다.
- 관리자 화면에는 권리 모드와 동의 상태를 명확히 표시한다.

## 단계별 구현

1. 문서/체크리스트 생성.
2. 동의/권리 게이트 스키마와 API 계약 추가.
3. 모바일 `내 목소리로 번역가사 듣기` UI와 동의 화면 추가.
4. 사용자 음성 샘플 업로드와 품질 검사 구현.
5. 안전한 voice profile 저장소와 삭제 경로 구현.
6. 기존 번역 타임라인을 입력으로 TTS 기반 번역가사 voice preview job 구현.
7. 배포용 음원 export와 공개 공유를 기본 보류하고, 권리 확인/책임 고지/운영 승인 후 열 수 있는 정책 게이트 구현.
8. 자체 제작 3분 이상 음원으로 운영 API 2회, Android 2회 검증.

## 성공 기준

- 동의 없는 음성 프로필 생성이 차단된다.
- 사용자 본인 목소리 프로필만 작업에 연결된다.
- 권리 미확인 상용곡은 개인 preview로 시작하고, 권리 확인/책임 고지/운영 정책 통과 시 공유와 배포용 음원 export 후보로 승격된다.
- 자체 제작 또는 라이선스 보유 음원은 번역 자막, 개인 preview, 정책 범위 내 export가 정상 동작한다.
- 사용자가 음성 프로필을 삭제하면 샘플, 프로필, 캐시 산출물이 모두 삭제된다.
- 3분 이상 자체 제작 음원 기준 운영 API와 Android 실기기 검증이 각각 2회 통과한다.
