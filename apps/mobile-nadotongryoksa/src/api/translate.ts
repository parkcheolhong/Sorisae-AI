// WorldLinco 통번역 API 클라이언트
import Constants from 'expo-constants';

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
): Promise<VoiceTranslateResult> {
  const body: Record<string, string> = {
    audio_base64: audioBase64,
    from_lang: from,
    to_lang: to,
    language,
  };
  if (regionHint) {
    body.region_hint = regionHint;
  }
  const res = await fetch(`${BASE_URL}/api/llm/voice-translate`, {
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
  };
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
