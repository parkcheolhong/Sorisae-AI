# 감정 SER (E0) — 언어 무관 감정 베이스라인

설계([`EMOTION_EXPRESSIVE_DESIGN.md`](../../../docs/worldlinco-v2/EMOTION_EXPRESSIVE_DESIGN.md)) §5 **E0**.
음향 특징(텍스트 비의존 = **언어 무관**)으로 감정 차원(arousal/valence)·범주를 추정해
**통화 텔레메트리에 감정 라벨을 부착**한다.

> `COMM_V2_EMOTION_SER` env opt-in, 기본 **off → no-op**. **off-path 전용**(번역/통화 hot path
> 무접촉). 추정기는 **휴리스틱 베이스라인**(GPU/모델 불필요)이며, 향후 wav2vec2/HuBERT
> 미세조정 SER로 동일 인터페이스에서 교체한다(E0→실모델).

## 구성
| 파일 | 역할 |
|------|------|
| `config.py` | 플래그 + 설정(SER·register 신뢰도 임계·최소 샘플) |
| `models.py` | `EmotionLabel` · `AcousticFeatures` · `EmotionEstimate` |
| `features.py` | 순수 파이썬 음향 특징(RMS·ZCR·에너지 분산), int/float 자동 정규화 |
| `audio.py` | PCM16(RIFF 선택) → int 샘플 + **임의 오디오(mp3 등)→PCM16 ffmpeg 디코딩**(E2 out용, best-effort) |
| `estimator.py` | `EmotionEstimator` 인터페이스 + `AcousticHeuristicSER` 베이스라인 |
| `register.py` | **E1**: 감정 → MT register(존댓말/어휘·어조) 지시문(언어 인지) |
| `expressive_tts.py` | **E3**: 감정 → 표현형 운율(rate/pitch/volume) + Azure `mstts:express-as` SSML(전이 대신 재현) |
| `budget.py` | **E3**: TTS 지연 메트릭(`voice_tts_synth_seconds`) + P95 예산 서킷브레이커(초과 시 비표현형 폴백) |
| `integration.py` | 텔레메트리 부착 + **E1 register 힌트** + **E2 EMOTION_PROBE 생성** + **E3 표현형 운율 플랜** 진입점(best-effort, 완전 가드) |

## 추정 휴리스틱(베이스라인, 문서화된 근거)
- **arousal** ≈ 0.55·RMS + 0.30·에너지분산 + 0.15·ZCR (음향적으로 비교적 신뢰).
- **valence** 는 음향만으로 약함 → 0.5 중심 소폭 이동 proxy(불확실성 반영).
- **confidence** ≈ (중립 거리 + 샘플 충분성) × **에너지 존재 게이트**(무음=0).
- **오인식 안전망**: confidence < 임계(기본 0.35) → **중립 폴백**.
- 범주: (arousal, valence) 사분면 → ANGRY/HAPPY/SAD/CALM, 그 외 NEUTRAL.

## 환경변수
| 변수 | 기본 | 설명 |
|------|------|------|
| `COMM_V2_EMOTION_SER` | `false` | SER 텔레메트리 스위치 |
| `COMM_V2_EMOTION_SER_CONF` | `0.35` | 중립 폴백 신뢰도 임계 |
| `COMM_V2_EMOTION_SER_MIN_SAMPLES` | `1600` | 추정 최소 샘플(~100ms@16k) |
| `COMM_V2_EMOTION_REGISTER` | `false` | **E1** 감정→register 제어 스위치(SER과 독립 opt-in) |
| `COMM_V2_EMOTION_REGISTER_CONF` | `0.5` | register 지시문 최소 신뢰도(약신호 과조정 방지) |
| `COMM_V2_EMOTION_PROBE` | `false` | **E2** `VOIP_EMOTION_PROBE` 텔레메트리 emit 스위치(SER/register와 독립 opt-in) |
| `COMM_V2_EMOTION_EXPRESSIVE_TTS` | `false` | **E3** 표현형 TTS 운율 카나리 스위치(voice_gateway 배선) |
| `COMM_V2_EMOTION_EXPRESSIVE_TTS_CONF` | `0.55` | E3 표현형 적용 최소 신뢰도(미만=비표현형 폴백) |
| `COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS` | `2000` | E3 표현형 합성 지연 예산(롤링 P95 초과 시 자동 비표현형 폴백) |
| `COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES` | `5` | 서킷브레이커 발동 최소 표본 수 |

## 사용
```python
from backend.communication.emotion import integration as ser

# E0 텔레메트리
tel = ser.estimate_as_telemetry(pcm_samples, sample_rate=16000)
# flag off → None / flag on → {"label","arousal","valence","confidence","source","at"}

# E1 register 힌트(PCM16 → 감정 → 존댓말/어조 지시문)
hint = ser.build_register_hint_from_pcm16(pcm16_bytes, target_lang="ko")
# COMM_V2_EMOTION_REGISTER off / 중립·저신뢰 → None

# E2 EMOTION_PROBE(원문 PCM16 + 출력 TTS bytes → src/out 감정 flat dict)
probe = ser.build_emotion_probe(src_pcm16_bytes, out_tts_bytes)
# COMM_V2_EMOTION_PROBE off / 한쪽 없음 → None
# on → {"src_arousal","src_valence","src_label","src_confidence","out_arousal","out_valence","out_label","out_confidence"}

# E3 표현형 TTS 운율 플랜(원문 PCM16 → 감정 → 운율 파라미터)
plan = ser.build_expressive_tts_plan_from_pcm16(src_pcm16_bytes, base_rate_pct=-6.0)
# COMM_V2_EMOTION_EXPRESSIVE_TTS off / 저신뢰·중립 → None
# on → ExpressiveTTSParams(rate="+12%", volume="+9%", pitch="+11Hz", style="angry", ...)
from backend.communication.emotion import to_edge_tts_kwargs, to_azure_ssml
edge_kwargs = to_edge_tts_kwargs(plan)          # {"rate","volume","pitch"} → edge_tts.Communicate
ssml = to_azure_ssml(text, plan, voice="ko-KR-SunHiNeural")  # 향후 Azure 표현형 보이스
```

## E1 — 감정 → register 제어 (배선 완료)
`llm/router.py` voice-translate(designated/VOIP 모드)에서 PCM16 릴레이 오디오 → 감정 추정 →
register 지시문을 **MT context_hint에 합성**(Session Core 맥락 힌트와 결합). flag off / 중립 /
저신뢰면 no-op → 기존 번역과 100% 동일. 음색 전이 없이 **어조·격식만 제어**(ko/ja 존댓말 일관성).
지시문 예: ANGRY(고각성·저정서) → "정중하고 차분한 존댓말로 완화해 번역".

## E2 — EMOTION_PROBE 텔레메트리 emission (배선 완료)
`llm/router.py` voice-translate(designated/VOIP, server_audio)에서 **원문 입력 PCM16**과
**합성된 TTS 오디오**(edge-tts `audio/mpeg` → ffmpeg PCM16 디코딩)의 감정을 추정해 응답 `emotion`
필드에 동봉(`COMM_V2_EMOTION_PROBE` off / TTS 없으면 `None`). 클라(`VoIPCallScreen.tsx`)가
`VOIP_EMOTION_PROBE`(`src/out_arousal·valence` 0..1)를 **로그캣에 emit** → 평가 하니스
(`eval/worldlinco/objective.py`)가 원문↔출력 감정 차원 거리로 **감정 보존도(E2)를 실데이터로 산출**.
off-path·best-effort·throw 금지 — 번역/통화 결과 불변.

## E3 — 표현형 TTS 운율 매핑 (카나리 배선 완료)
SeamlessExpressive 표현 보존은 **한국어 미지원** → SER(언어 무관 음향)로 감정을 추정해
**한국어 TTS 운율(rate·pitch·volume)·스타일로 "재현"**(전이 대신 재현, 설계 §3). arousal(각성,
비교적 신뢰)은 rate/volume/pitch 주신호, valence(약신호)는 pitch 소폭만. confidence < 임계 또는
중립이면 **비표현형 폴백**(기존 합성과 동일).

**배선**: `llm/router.py` voice-translate(designated/VOIP)에서 입력 PCM16 → `build_expressive_tts_plan_from_pcm16`
→ `voice_gateway._synthesize_tts(..., expressive=plan)` → `_synthesize_edge_tts` 가 edge-tts
`Communicate(rate/volume/pitch)` 로 적용. 운율 델타는 **제품 baseline 속도(`VOICE_EDGE_TTS_RATE`,
`edge_tts_base_rate_pct()`) 기준**으로 가산(감정 중립 ≈ 기존 속도). 향후 Azure 표현형 한국어
보이스는 `to_azure_ssml`(`mstts:express-as`)로 스타일까지 적용. **카나리 게이트
(`COMM_V2_EMOTION_EXPRESSIVE_TTS`, 기본 off → 기존과 100% 동일)**.

**지연 예산 모니터링 + 폴백([`budget.py`](budget.py)):** 합성 지연을 Prometheus
`voice_tts_synth_seconds{expressive}` 히스토그램으로 노출(Grafana "TTS synth latency p50/p95" 패널,
2s 임계선) 하고, **표현형 합성 롤링 P95 가 예산(`COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS`, 기본
2000ms) 초과 시 서킷브레이커**가 표현형을 자동 차단(비표현형 폴백) — 예산의 80% 이하로 회복되면
자동 복귀(히스테리시스). router 가 합성 전 `expressive_allowed()` 확인, 합성 후
`observe_tts_latency()` 기록. 설계 §6 "지연 예산 위반 시 비표현형 폴백" 구현.

## E0 범위·안전성
- **hot path 무배선**: E0는 텔레메트리 부착 능력만 제공. 라이브 오디오 hot path 직접 연결은
  E1 이후 플래그 하에 신중히. integration 함수는 예외를 흡수해 **절대 throw 하지 않는다**.
- **프라이버시**: 오디오 바이트 미보관(특징·라벨만). 학습 데이터화는 동의·익명화 후([`SECURITY_STRIDE_DESIGN.md`](../../../docs/worldlinco-v2/SECURITY_STRIDE_DESIGN.md)).

## 테스트
- [`backend/tests/test_communication_emotion_ser.py`](../../tests/test_communication_emotion_ser.py) — E0 베이스라인.
- [`backend/tests/test_communication_emotion_register.py`](../../tests/test_communication_emotion_register.py) — E1 register 제어.
- [`backend/tests/test_communication_emotion_probe.py`](../../tests/test_communication_emotion_probe.py) — **E2** EMOTION_PROBE
  (플래그 게이팅·RIFF 디코딩 숏컷·flat 4필드 보장·한쪽 누락 None·throw 금지).
- [`backend/tests/test_communication_emotion_expressive.py`](../../tests/test_communication_emotion_expressive.py) — **E3** 표현형 운율
  (신뢰도/중립 게이트·arousal→운율 단조성·라벨→스타일·SSML 이스케이프·integration 게이팅/throw 금지).
- [`backend/tests/test_voice_gateway_expressive_tts.py`](../../tests/test_voice_gateway_expressive_tts.py) — **E3 배선**
  (baseline rate 파싱·비표현형 기본값 유지·expressive→edge-tts `Communicate` rate/volume/pitch 전달).
- [`backend/tests/test_communication_emotion_budget.py`](../../tests/test_communication_emotion_budget.py) — **E3 예산**
  (기본 허용·표본부족 미발동·P95 초과 차단·히스테리시스 회복·비표현형 미반영·throw 금지).
