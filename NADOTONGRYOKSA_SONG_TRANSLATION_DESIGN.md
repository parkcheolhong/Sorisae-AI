# FILE-ID: FILE-NADOTONGRYOKSA-SONG-TRANSLATION-DESIGN-MD
# SECTION-ID: SECTION-NADOTONGRYOKSA-SONG-TRANSLATION-DESIGN-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-BACKEND-JOB-ENGINE
# CHUNK-ID: CHUNK-NADOTONGRYOKSA-SONG-TRANSLATION-DESIGN-001

# 나도통역사 노래 파일 번역 자막 고급 설계

## 현재 상태

- 상태: 설계됨
- 작성일: 2026-05-08
- 대상 앱: `apps/mobile-nadotongryoksa`
- 대상 백엔드: `backend/mobile/song_translation`, `backend/main.py`
- 목표: 모바일에 다운로드된 타국 노래 파일을 업로드하고, 백엔드에서 원어 가사를 자동 감지/추출/번역하여 자국어 자막으로 편집하고 재생 싱크에 사용할 수 있게 한다.

## 제품 목표

나도통역사의 기존 노래 전용 모드는 마이크로 짧은 가사 구간을 캡처해 번역 자막을 누적하는 방식이다. 새 기능은 이 흐름을 고급 백엔드 처리형으로 확장한다.

사용자는 모바일에서 `mp3`, `m4a`, `wav`, `flac` 같은 노래 파일을 선택한다. 백엔드는 파일을 검증하고 작업 ID를 발급한 뒤, 음원 정규화, 가사 구간 추출, 언어 자동 감지, 세그먼트별 번역, 품질 점수 계산, 자막 타임라인 생성, 편집 저장, 내보내기까지 처리한다.

## 비범위

- 저작권이 있는 노래의 공개 배포용 번역 가사 생성은 지원 범위가 아니다.
- 1차 구현은 번역 자막/가사 편집 기능이며, 원곡을 자국어로 다시 부르는 음원 합성은 별도 고급 확장으로 둔다.
- 모바일 GPS는 언어 자동 감지에 사용하지 않는다. GPS는 공항, 호텔예약, 먹거리, 서비스 기능으로만 유지한다.

## 사용자 흐름

1. 모바일 노래 전용 모드에서 노래 파일 선택.
2. 목표 언어는 현재 번역 언어를 기본값으로 사용하고, 원어는 자동 감지로 둔다.
3. 파일 업로드 후 `job_id` 수신.
4. 모바일은 진행률을 1초에서 2초 간격으로 조회하거나 WebSocket으로 수신.
5. 백엔드는 가사 세그먼트와 번역 자막을 생성.
6. 모바일은 시간순 자막 타임라인을 표시.
7. 사용자는 세그먼트별 번역문을 직접 수정하거나 해당 구간만 재번역.
8. 결과를 앱 내부 JSON, SRT, VTT, LRC 형식으로 내보낸다.
9. 재생 위치에 맞춰 현재 번역 자막을 강조한다.

## 백엔드 파이프라인

```text
Upload
  -> File validation
  -> Job creation
  -> Audio normalization
  -> Vocal enhancement gate
  -> STT with timestamps
  -> Intermediate transcript/timeline artifact
  -> Language normalization
  -> Lyric cleanup
  -> Segment merge/split
  -> Segment translation
  -> Quality scoring
  -> Editable timeline save
  -> Export
```

## 음성 인식 후처리 성능 판단

음성을 먼저 STT로 인식하고, 그 결과를 타임스탬프 포함 텍스트/JSON 중간 산출물로 저장한 뒤, 편집부가 이 산출물을 읽어 가사 후처리를 수행하는 구조를 표준 경로로 둔다. 성능 병목은 파일 읽기/쓰기나 편집부 로딩이 아니라 STT와 번역 단계다. 3분 곡 기준 중간 산출물은 보통 수십 KB 수준이라 모바일 편집부에서 즉시 읽을 수 있다.

권장 중간 산출물은 단순 TXT 단독 파일이 아니라 `original`, `normalized`, `translated`, `start_ms`, `end_ms`, `confidence`, `detected_by`를 포함한 JSON 타임라인이다. TXT/SRT/VTT/LRC는 export 또는 사람이 검수하기 위한 파생 산출물로 유지한다.

## API 계약

### 작업 생성

```http
POST /api/mobile/song-translation/jobs
Content-Type: multipart/form-data
```

필드:

- `file`: 업로드할 노래 파일.
- `target_language`: 목표 언어. 기본값 `ko`.
- `source_language`: 기본값 `auto`.
- `quality`: `standard` 또는 `advanced`. 기본값 `advanced`.
- `mode`: 기본값 `subtitle`.

응답:

```json
{
  "job_id": "songjob_...",
  "status": "queued",
  "stage": "queued",
  "progress": 0,
  "source_language": "auto",
  "target_language": "ko"
}
```

### 작업 상태 조회

```http
GET /api/mobile/song-translation/jobs/{job_id}
```

응답:

```json
{
  "job_id": "songjob_...",
  "status": "processing",
  "stage": "transcribing",
  "progress": 58,
  "message": "가사 구간을 분석 중입니다.",
  "source_language": "en",
  "target_language": "ko",
  "quality_score": 0.88
}
```

### 자막 타임라인 조회

```http
GET /api/mobile/song-translation/jobs/{job_id}/subtitles
```

응답:

```json
{
  "job_id": "songjob_...",
  "source_language": "en",
  "target_language": "ko",
  "segments": [
    {
      "id": "seg_001",
      "index": 1,
      "start_ms": 12340,
      "end_ms": 16520,
      "original": "I still remember the night",
      "translated": "나는 아직도 그 밤을 기억해",
      "confidence": 0.91,
      "detected_by": "voice",
      "quality_flags": []
    }
  ]
}
```

### 세그먼트 편집

```http
PATCH /api/mobile/song-translation/jobs/{job_id}/segments/{segment_id}
Content-Type: application/json
```

요청:

```json
{
  "translated": "나는 아직도 그날 밤을 기억해"
}
```

### 내보내기

```http
GET /api/mobile/song-translation/jobs/{job_id}/export?format=srt
GET /api/mobile/song-translation/jobs/{job_id}/export?format=vtt
GET /api/mobile/song-translation/jobs/{job_id}/export?format=lrc
GET /api/mobile/song-translation/jobs/{job_id}/export?format=json
```

## 데이터 모델

```text
SongTranslationJob
- id
- user_id
- original_filename
- file_hash
- source_language
- target_language
- status
- stage
- progress
- duration_ms
- audio_storage_path
- created_at
- updated_at
- error_code
- error_message
- quality_score

SongLyricSegment
- id
- job_id
- index
- start_ms
- end_ms
- original_text
- normalized_text
- translated_text
- source_language
- target_language
- confidence
- detected_by
- edited_by_user
- quality_flags

SongExportArtifact
- id
- job_id
- format
- storage_path
- created_at
```

## 성능 기준

- 업로드 시작 응답: 2초 이내.
- 3분 곡 처리: GPU 서버 기준 60초 이내 목표.
- 5분 곡 처리: GPU 서버 기준 120초 이내 목표.
- CPU fallback: 5분 곡 6분 이내 허용.
- 파일 크기 1차 제한: 100MB.
- 서버 내부 표준 오디오: 16kHz mono wav.
- 진행률 갱신: 1초에서 2초 간격.
- 자막 렌더링 목표: 500개 세그먼트까지 모바일에서 안정 표시.
- 세그먼트 권장 길이: 1.2초에서 8초.
- 평균 STT confidence 목표: 0.80 이상.
- confidence 0.65 미만 구간은 편집 필요 플래그 표시.

## 품질 기준

- Whisper 감지 언어를 우선하고, 문자 패턴과 다수결로 보강한다.
- `en-US`, `english`, `English` 같은 감지값은 앱의 `LangCode`로 정규화한다.
- 간주, 무음, 비가사 노이즈 구간은 자막 생성에서 제외한다.
- 너무 긴 세그먼트는 분할하고 너무 짧은 세그먼트는 병합한다.
- 반복 후렴은 중복 후보로 표시한다.
- 빈 번역, 원문과 동일한 번역, 지나치게 짧은 번역은 재시도 대상으로 둔다.
- 사용자가 편집한 번역문은 STT 원본과 분리 저장한다.

## 보안 기준

- 허용 확장자: `mp3`, `m4a`, `wav`, `flac`.
- MIME 타입과 파일 시그니처를 함께 검증한다.
- 파일명은 저장 전에 sanitize한다.
- 업로드 크기 제한을 강제한다.
- 사용자별 job 접근 권한을 확인한다.
- 공개 URL은 기본 비활성화한다.
- 원본 파일은 보관 기간 정책을 둔다.
- 개인 처리/비공개 저장 기준을 기본값으로 한다.

## 모바일 설계

현재 `App.tsx`의 노래 전용 모드 카드에 다음 흐름을 추가한다.

```text
노래 전용 모드
- 마이크 캡처
- 노래 파일 선택
- 업로드 진행률
- 처리 단계 표시
- 원어/번역어 자동 감지 패널
- 자막 타임라인
- 세그먼트 편집
- 자막 내보내기
```

필요 의존성:

- `expo-document-picker`: 로컬 파일 선택.
- 기존 `expo-file-system`: 파일 URI 읽기와 업로드 준비.
- 기존 `expo-av`: 재생 위치 기반 자막 싱크.

## 구현 순서

1. 설계 문서와 체크리스트 생성.
2. 백엔드 `backend/mobile/song_translation` 패키지 생성.
3. API 스키마와 인메모리 Job 스토어 1차 구현.
4. 파일 검증, 세그먼트 정규화, 자막 export 유틸 구현.
5. FastAPI 라우터를 `backend/main.py`에 연결.
6. 백엔드 계약 테스트 2회 실행.
7. 모바일 파일 선택 API 클라이언트와 UI 추가.
8. 모바일 TypeScript/prebuild 2회 검증.
9. 운영 도메인 또는 로컬 실서버에서 업로드/조회/자막/export 2회 검증.

## 완료 게이트

완료됨으로 보고하려면 다음이 모두 필요하다.

- 설계 문서 생성 확인.
- 체크리스트 문서 생성 확인.
- 백엔드 계약 테스트 2회 통과.
- 모바일 TypeScript 검증 2회 통과.
- 실제 서버에서 업로드부터 자막 조회/export까지 2회 통과.
- 체크리스트 문서에 실제 근거 반영.
