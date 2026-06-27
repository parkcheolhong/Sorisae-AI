# WorldLinco V.2 — 오케스트레이터 고유 ID 백본 (Correlation ID Backbone)

> 목표: **모든 기능**이 단일 고유 ID로 `기능 ID 자동 매핑 → 셀프 서빙 → 전송(딜리버리) → 음성 발화`
> 전 구간을 **스스로 자동 연결**한다. 각 단계가 자기 출처의 고유 ID를 찾아가 붙는다.
>
> 표준 4단계 용어(SSOT):
> | 단계 | 표준 용어 | 구현 |
> |---|---|---|
> | 1 | **기능 ID 자동 매핑** | featureId 접두 cid 발급/echo (STT 인식 결과가 자기 기능 ID에 매핑) |
> | 2 | **셀프 서빙** | 번역 서비스가 동일 cid로 응답 |
> | 3 | **전송(딜리버리)** | 릴레이/WS 채널이 동일 cid 전파 |
> | 4 | **음성 발화** | TTS 합성·재생이 동일 cid에 붙음 |

## 1. 단일 ID 스킴 (SSOT)

```
{feature_id}-{base36(epoch_ms)}-{rand6}
예) voip.voice_relay-mqm1w1y0-9cc6a7
```

- `feature_id` 접두로 **어느 기능에서 왔는지 자가 식별**된다.
- 시간 + 난수 조합으로 전역 충돌이 사실상 불가능.
- 클라이언트가 발급한 ID는 서버가 **그대로 echo**, 없거나 위조/오염 시 **서버가 재발급**.

### feature_id 레지스트리 (client ↔ backend 1:1 정합)

| feature_id | 기능 |
|---|---|
| `voip.voice_relay` | VOIP 통화 음성 릴레이 |
| `face.interpret` | 대면 통역(자동 감지) |
| `chat.translate` | 채팅/텍스트 번역 |
| `tts.synthesize` | 서버 뉴럴 TTS |
| `ocr.image` | 이미지 OCR 번역 |
| `song.translate` | 가사 번역 |
| `orchestrate.voice` | 오케스트레이터 음성 |

- 클라이언트 SSOT: `apps/mobile-nadotongryoksa/src/features/correlation/correlationId.ts`
- 백엔드 SSOT: `backend/llm/correlation.py`

## 2. 단계별 자동 연결 흐름

```
[캡처]  newCorrelationId(feature)  →  cid 발급
   │
[기능 ID 자동 매핑]  POST /api/llm/voice-translate {correlation_id, feature_id, utterance_id}
   │      ← 서버: ensure_correlation_id() echo, 로그 "[voice-translate] cid=... stt ..."
   │      → 응답 {correlation_id, utterance_id, seq_id, chunk_index}
   │
[셀프 서빙]  번역 단계 로그 "[voice-translate] cid=... translated ..."
   │
[전송(딜리버리)]  WS voice_translation {correlation_id, utterance_id, seq_id, chunk_index}
   │      → 수신측: message.correlation_id 이어받음(누락 시 콘텐츠 기반 결정적 ID)
   │
[음성 발화]  POST /api/llm/voice/synthesize {correlation_id, feature_id}
          ← 서버 로그 "[voice/synthesize] cid=... delivery=server_audio"
          → 재생 로그 PLAYBACK / PLAYBACK_DELIVERED {correlation_id}
```

## 3. 자가 상관(self-correlation) 불변식

1. **랜덤 폴백 금지**: 수신측이 ID 누락 메시지를 받으면 `remote-${seqId}` 같은 랜덤 ID를
   쓰지 않는다. 콘텐츠 기반 **결정적 ID**(`deterministicCorrelationId`)를 써서, 같은 발화의
   재전송이 동일 ID로 묶여 **중복제거·순서 상관이 유지**된다.
2. **재생 큐 정렬**: `VoiceRelayPlaybackQueue`는 `seqId → utteranceId → chunkIndex`로 정렬해
   순차 발화한다.
3. **하위호환**: 모든 ID 필드는 선택값. 구버전 클라이언트/서버는 무시하고 정상 동작하며,
   ID가 없으면 서버가 새로 발급해 echo 한다(무회귀).

## 4. 적용 범위 (이번 변경)

- 백엔드: `_MobileVoiceTranslateRequest`, `/voice-translate`, `VoiceSynthesizeRequest/Response`,
  `/voice/synthesize` — 수신·echo·단계별 `cid=` 로깅.
- 클라이언트 API: `voiceTranslate`, `synthesizeSpeech` — 송신·echo 수신.
- VOIP 릴레이: 캡처 세그먼트당 cid 발급 → 기능 ID 자동 매핑/셀프 서빙/전송(딜리버리)/음성 발화 일관 전파, 랜덤 폴백 제거.
- 대면 통역(App.tsx): 캡처당 cid 발급 → STT/발화 전파.

## 5. 운영 검증 방법

```powershell
# 백엔드 로그에서 한 발화의 전 구간을 동일 cid로 추적
docker logs devanalysis114-backend --since 5m | Select-String "cid="
# 단말 로그에서 재생 단계 cid 확인
adb -s <device> logcat -d | Select-String "PLAYBACK_DELIVERED"
```

동일 `cid`가 `stt → translated → synthesize → PLAYBACK_DELIVERED` 순으로 한 줄씩 찍히면
"스스로 고유 ID를 찾아 붙는" 자동 연결이 성립한 것이다.
