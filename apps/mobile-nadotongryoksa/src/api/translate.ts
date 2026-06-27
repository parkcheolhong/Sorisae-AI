// WorldLinco 통번역 API 클라이언트
import Constants from 'expo-constants';
import { FEATURE_IDS, ensureCorrelationId } from '../features/correlation/correlationId';

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  'http://10.0.2.2:8000';

export interface TranslateResult {
  translated: string;
  from: string;
  to: string;
  engine: string;
  offline: boolean;
}

export interface VoiceTranslateResult extends TranslateResult {
  original_text: string;
  detected_language?: string;
  audio_url?: string;
  audio_base64?: string;
  audio_format?: string;
  tts_delivery?: 'server_audio' | 'device_speech';
  stt_trust?: 'high' | 'low' | string;
  stt_avg_logprob?: number | null;
  // V.2 ID 백본 — 서버가 echo 한 상관 ID(기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화 자동 연결).
  correlation_id?: string;
  // V.2 감정 E2 — 서버가 추정한 원문↔출력(TTS) 감정(arousal/valence 0..1). 클라가 VOIP_EMOTION_PROBE 로그캣 emit → 평가 하니스가 보존도 산출.
  emotion?: EmotionProbe;
}

export interface EmotionProbe {
  src_arousal: number;
  src_valence: number;
  src_label?: string;
  src_confidence?: number;
  out_arousal: number;
  out_valence: number;
  out_label?: string;
  out_confidence?: number;
}

export type TranslateServiceMode = 'default' | 'lyrics';

export interface TranslateOptions {
  serviceMode?: TranslateServiceMode;
  regionHint?: string;
}

export interface ImageTranslateResult extends TranslateResult {
  original_text: string;
  file_name: string;
  content_type: string;
  line_count: number;
}

// 오프라인 폴력 사전 (24개 언어 주요 표현 포함)
// 키 형식: "from:to:text"
const OFFLINE_DICT: Record<string, string> = {
  // 한국어 → 영어
  'ko:en:안녕하세요': 'Hello',
  'ko:en:감사합니다': 'Thank you',
  'ko:en:도와주세요': 'Please help me',
  'ko:en:얼마입니까': 'How much is it?',
  'ko:en:병원이 어디인가요': 'Where is the hospital?',
  'ko:en:화장실이 어디인가요': 'Where is the restroom?',
  'ko:en:택시 불러주세요': 'Please call a taxi',
  'ko:en:경찰을 불러주세요': 'Please call the police',
  // 한국어 → 중국어
  'ko:zh:안녕하세요': '你好',
  'ko:zh:감사합니다': '谢谢',
  'ko:zh:도와주세요': '请帮帮我',
  'ko:zh:얼마입니까': '多少錢？',
  'ko:zh:병원이 어디인가요': '医院在哪里？',
  // 한국어 → 일본어
  'ko:ja:안녕하세요': 'こんにちは',
  'ko:ja:감사합니다': 'ありがとう',
  'ko:ja:도와주세요': '助けてください',
  'ko:ja:얼마입니까': 'いくらですか？',
  // 영어 → 한국어
  'en:ko:Hello': '안녕하세요',
  'en:ko:Thank you': '감사합니다',
  'en:ko:Please help me': '도와주세요',
  'en:ko:How much is it?': '얼마입니까?',
  'en:ko:Where is the hospital?': '병원이 어디인가요?',
  // 중국어 → 한국어
  'zh:ko:你好': '안녕하세요',
  'zh:ko:谢谢': '감사합니다',
  'zh:ko:请帮帮我': '도와주세요',
  // 일본어 → 한국어
  'ja:ko:こんにちは': '안녕하세요',
  'ja:ko:ありがとう': '감사합니다',
  // 비엣남 → 한국어
  'vi:ko:Xin chào': '안녕하세요',
  'vi:ko:Cảm ơn': '감사합니다',
  // 태국어 → 한국어
  'th:ko:สวัสดี': '안녕하세요',
  'th:ko:ขอบคุณ': '감사합니다',
};

const SPECIALIZED_GLOSSARY: Record<string, string> = {
  // 일본어 -> 한국어 자주 쓰는 생활/여행 표현 보정
  'ja:ko:チェックイン': '체크인',
  'ja:ko:チェックアウト': '체크아웃',
  'ja:ko:空港': '공항',
  'ja:ko:駅': '역',
  'ja:ko:病院': '병원',
  // 중국어 -> 한국어
  'zh:ko:机场': '공항',
  'zh:ko:酒店': '호텔',
  'zh:ko:医院': '병원',
  // 영어 -> 한국어
  'en:ko:check-in': '체크인',
  'en:ko:check-out': '체크아웃',
  'en:ko:boarding gate': '탑승구',
};

const LYRIC_METADATA_PATTERNS = [/\[[^\]]*\]/g, /\([^\)]*\)/g, /[♪♫♬]+/g];

function normalizeText(text: string, serviceMode: TranslateServiceMode): string {
  let normalized = text;
  if (serviceMode === 'lyrics') {
    for (const pattern of LYRIC_METADATA_PATTERNS) {
      normalized = normalized.replace(pattern, ' ');
    }
    normalized = normalized.replace(/\s*\/\s*/g, ' ');
  }
  return normalized.replace(/\s+/g, ' ').trim();
}

function applySpecializedGlossary(
  input: string,
  from: string,
  to: string,
  serviceMode: TranslateServiceMode,
): string {
  let output = input;
  for (const [key, replacement] of Object.entries(SPECIALIZED_GLOSSARY)) {
    const [src, dst, term] = key.split(':');
    if (src !== from || dst !== to || !term) continue;
    output = output.replaceAll(term, replacement);
  }
  if (serviceMode === 'lyrics') {
    for (const pattern of LYRIC_METADATA_PATTERNS) {
      output = output.replace(pattern, ' ');
    }
    output = output.replace(/\s+/g, ' ').trim();
  }
  return output;
}

async function requestTranslate(
  text: string,
  from: string,
  to: string,
  signal: AbortSignal,
  regionHint?: string,
): Promise<{ translated: string; engine: string }> {
  const body: Record<string, string> = { text, from_lang: from, to_lang: to };
  if (regionHint) {
    body.region_hint = regionHint;
  }
  const res = await fetch(`${BASE_URL}/api/llm/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return {
    translated: String(data.translated ?? data.result ?? text),
    engine: String(data.engine ?? 'nado'),
  };
}

export async function translateText(
  text: string,
  from: string,
  to: string,
  timeoutMs = 8000,
  options: TranslateOptions = {},
): Promise<TranslateResult> {
  const serviceMode = options.serviceMode ?? 'default';
  const normalizedText = normalizeText(text, serviceMode);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    // 1차 요청 실패 시 1회 재시도해서 순간 네트워크 흔들림에 강하게 처리
    let translated: string;
    let engine: string;
    try {
      const first = await requestTranslate(normalizedText, from, to, controller.signal, options.regionHint);
      translated = first.translated;
      engine = first.engine;
    } catch {
      const second = await requestTranslate(normalizedText, from, to, controller.signal, options.regionHint);
      translated = second.translated;
      engine = second.engine;
    }

    const refined = applySpecializedGlossary(translated, from, to, serviceMode);
    return {
      translated: refined,
      from,
      to,
      engine,
      offline: false,
    };
  } catch {
    // 오프라인 폴백
    const dictKey = `${from}:${to}:${normalizedText}`;
    const offlineResult = OFFLINE_DICT[dictKey];
    return {
      translated: offlineResult ?? normalizedText,
      from,
      to,
      engine: 'offline',
      offline: true,
    };
  } finally {
    clearTimeout(timer);
  }
}

export interface VoiceTranslateOptions {
  regionHint?: string;
  language?: string;
}

export async function voiceTranslate(
  audioBase64: string,
  from: string,
  to: string,
  regionHint?: string,
  language: string = 'auto',
  options: {
    deviceTts?: boolean;
    mode?: 'designated' | 'bilingual';
    langA?: string;
    langB?: string;
    // V.2 ID 백본 — 캡처 시점 고유 ID를 전 구간에 전파한다.
    correlationId?: string;
    featureId?: string;
    utteranceId?: string;
    seqId?: number;
    chunkIndex?: number;
    // V.2 Session Core(선택) — 통화/세션 단위 언어쌍·맥락 기억용. 서버는 미지정 시 no-op.
    sessionId?: string;
  } = {},
): Promise<VoiceTranslateResult> {
  const featureId = options.featureId
    ?? (options.mode === 'bilingual' ? FEATURE_IDS.faceInterpret : FEATURE_IDS.voipVoiceRelay);
  const correlationId = ensureCorrelationId(options.correlationId, featureId);
  const body: Record<string, string | boolean | number> = {
    audio_base64: audioBase64,
    from_lang: from,
    to_lang: to,
    language,
    device_tts: options.deviceTts !== false,
    // 채널 모드 명시(V.2 Delivery 채널 경계). 기본값은 지정 언어(designated).
    mode: options.mode ?? 'designated',
    correlation_id: correlationId,
    feature_id: featureId,
  };
  if (options.utteranceId) {
    body.utterance_id = options.utteranceId;
  }
  if (typeof options.seqId === 'number' && Number.isFinite(options.seqId)) {
    body.seq_id = options.seqId;
  }
  if (typeof options.chunkIndex === 'number' && Number.isFinite(options.chunkIndex)) {
    body.chunk_index = options.chunkIndex;
  }
  if (options.sessionId) {
    body.session_id = options.sessionId;
  }
  // bilingual 모드는 언어 쌍(lang_a/lang_b)으로 서버가 화자 언어를 자동 감지·방향 결정한다.
  if (options.langA) {
    body.lang_a = options.langA;
  }
  if (options.langB) {
    body.lang_b = options.langB;
  }
  if (regionHint) {
    body.region_hint = regionHint;
  }
  // 채널 분리(V.2) — VoIP(designated)와 대면(bilingual)은 서로 다른 백엔드 라우트를 사용한다.
  // 한 채널의 요청 계약/검증 변경이 다른 채널 요청을 깨뜨리지 못하도록 격리한다(코어 로직은 서버에서 공유).
  const voiceEndpoint =
    options.mode === 'bilingual'
      ? `${BASE_URL}/api/llm/face/voice-translate`
      : `${BASE_URL}/api/llm/voip/voice-translate`;
  const res = await fetch(voiceEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const message = typeof payload.detail === 'string' ? payload.detail : `HTTP ${res.status}`;
    throw new Error(message);
  }
  const data = await res.json();
  return {
    original_text: data.original_text ?? '',
    translated: data.translated ?? '',
    from: data.from ?? from,
    to: data.to ?? to,
    engine: data.engine ?? 'nado-voice',
    offline: false,
    detected_language: data.detected_language ?? data.from,
    audio_url: data.audio_url,
    audio_base64: data.audio_base64,
    audio_format: data.audio_format,
    tts_delivery: data.tts_delivery,
    stt_trust: data.stt_trust,
    stt_avg_logprob: typeof data.stt_avg_logprob === 'number' ? data.stt_avg_logprob : null,
    correlation_id: typeof data.correlation_id === 'string' ? data.correlation_id : correlationId,
    emotion:
      data.emotion &&
      typeof data.emotion.src_arousal === 'number' &&
      typeof data.emotion.out_arousal === 'number'
        ? (data.emotion as EmotionProbe)
        : undefined,
  };
}

export interface SynthesizeResult {
  audioBase64?: string;
  audioFormat?: string;
  ttsDelivery: 'server_audio' | 'device_speech';
  correlationId?: string;
}

// 서버 뉴럴 TTS 합성(Edge neural). 통역 수신측이 번역문을 대상 언어 네이티브 보이스로
// 받기 위해 호출한다 — 단말 음성팩 의존을 제거해 50개국 일관 발음·자연스러운 톤을 보장.
// 실패/미지원 시 null 또는 device_speech 를 반환하여 호출측이 디바이스 TTS로 폴백한다.
export async function synthesizeSpeech(
  text: string,
  targetLang?: string,
  baseUrl: string = BASE_URL,
  // 기본 12초 — 대면/VOIP 공통 SSOT. 6초에선 edge-tts 콜드스타트/네트워크 지연 시
  // 단말 TTS(붙여 읽기)로 폴백되어 발화 품질이 떨어졌다(대면·VOIP 모두 동일하게 정합).
  timeoutMs = 12000,
  // V.2 ID 백본 — 발화 단계가 출처 상관 ID에 스스로 붙도록 전달/echo.
  correlation?: { correlationId?: string; featureId?: string },
): Promise<SynthesizeResult | null> {
  const trimmed = (text || '').trim();
  if (!trimmed) return null;
  const featureId = correlation?.featureId ?? FEATURE_IDS.voiceSynthesize;
  const correlationId = ensureCorrelationId(correlation?.correlationId, featureId);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl}/api/llm/voice/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: trimmed,
        target_lang: targetLang,
        correlation_id: correlationId,
        feature_id: featureId,
      }),
      signal: controller.signal,
    });
    if (!res.ok) return null;
    const data = await res.json();
    const echoedId = typeof data.correlation_id === 'string' ? data.correlation_id : correlationId;
    const fmt = typeof data.audio_format === 'string' ? data.audio_format : undefined;
    const b64 = typeof data.audio_base64 === 'string' ? data.audio_base64 : undefined;
    if (!b64 || !fmt || !fmt.startsWith('audio/')) {
      return { ttsDelivery: 'device_speech', correlationId: echoedId };
    }
    return { audioBase64: b64, audioFormat: fmt, ttsDelivery: 'server_audio', correlationId: echoedId };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function translateImage(
  asset: { uri: string; name?: string | null; mimeType?: string | null },
  from: string,
  to: string,
  regionHint?: string,
): Promise<ImageTranslateResult> {
  const formData = new FormData();
  const fileName = asset.name || `ocr-${Date.now()}.jpg`;
  const mimeType = asset.mimeType || 'image/jpeg';
  formData.append('file', { uri: asset.uri, name: fileName, type: mimeType } as unknown as Blob);
  formData.append('source_language', from);
  formData.append('target_language', to);
  if (regionHint) {
    formData.append('region_hint', regionHint);
  }

  const res = await fetch(`${BASE_URL}/api/mobile/image-translation`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const message = typeof payload.detail === 'string' ? payload.detail : `HTTP ${res.status}`;
    throw new Error(message);
  }
  const data = await res.json();
  return {
    original_text: String(data.original_text ?? ''),
    translated: String(data.translated ?? ''),
    from: String(data.source_language ?? from),
    to: String(data.target_language ?? to),
    engine: String(data.engine ?? 'rapidocr+nado'),
    offline: Boolean(data.offline),
    file_name: String(data.file_name ?? fileName),
    content_type: String(data.content_type ?? mimeType),
    line_count: Number(data.line_count ?? 0),
  };
}
