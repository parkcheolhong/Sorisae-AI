// WorldLinco V.2 오케스트레이터 상관 ID(correlation id) 백본 — 클라이언트 SSOT.
//
// 모든 기능(VOIP 음성 릴레이 / 대면 통역 / 채팅 번역 / 마켓 TTS / OCR / 가사 등)이
// 단일 고유 ID로 [기능 ID 자동 매핑 → 셀프 서빙 → 전송(딜리버리) → 음성 발화] 전 구간을
// 자동으로 묶도록, 공통 ID 스킴을 한 곳에서 정의한다. 백엔드 `backend/llm/correlation.py` 와 정합.
//  - 기능 ID 자동 매핑: featureId 접두가 박힌 cid 발급/echo (스스로 자기 기능 ID에 매핑)
//  - 셀프 서빙: 번역 서비스가 동일 cid로 응답
//  - 전송(딜리버리): 릴레이/WS 채널이 동일 cid 전파
//  - 음성 발화: TTS 합성·재생이 동일 cid에 붙음
//
// ID 포맷: `{featureId}-{base36(epochMs)}-{rand6}`  예) `voip.voice_relay-l9x2k3-a3f9c2`
//  - featureId 가 접두로 박혀 어느 기능에서 왔는지 자가 식별된다(스스로 ID를 찾아 붙음).
//  - 시간 + 난수 조합으로 전역 충돌이 사실상 불가능하다.

export const FEATURE_IDS = {
    voipVoiceRelay: 'voip.voice_relay',
    faceInterpret: 'face.interpret',
    chatTranslate: 'chat.translate',
    voiceSynthesize: 'tts.synthesize',
    imageTranslate: 'ocr.image',
    songTranslate: 'song.translate',
    orchestrate: 'orchestrate.voice',
} as const;

export type FeatureId = (typeof FEATURE_IDS)[keyof typeof FEATURE_IDS];

const VALID_FEATURE_IDS: ReadonlySet<string> = new Set(Object.values(FEATURE_IDS));
const DEFAULT_FEATURE_ID: FeatureId = FEATURE_IDS.orchestrate;

const CORRELATION_RE = /^[a-zA-Z0-9._]{1,48}-[a-z0-9]{1,12}-[a-z0-9]{4,12}$/;
const MAX_LEN = 128;

let monotonicSalt = 0;

export function normalizeFeatureId(featureId: string | null | undefined): FeatureId {
    const candidate = String(featureId ?? '').trim();
    return (VALID_FEATURE_IDS.has(candidate) ? candidate : DEFAULT_FEATURE_ID) as FeatureId;
}

function rand6(): string {
    // crypto 미지원 환경(일부 RN)에서도 안전하게 동작하도록 Math.random 폴백.
    const base = Math.floor(Math.random() * 0xffffff).toString(36);
    monotonicSalt = (monotonicSalt + 1) % 0x1000;
    const salt = monotonicSalt.toString(36);
    return `${base}${salt}`.slice(0, 6).padStart(4, '0');
}

export function newCorrelationId(featureId?: string | null): string {
    const feature = normalizeFeatureId(featureId);
    const ts36 = Math.floor(Date.now()).toString(36);
    return `${feature}-${ts36}-${rand6()}`;
}

export function isValidCorrelationId(value: string | null | undefined): boolean {
    if (!value) {
        return false;
    }
    const text = String(value).trim();
    return text.length <= MAX_LEN && CORRELATION_RE.test(text);
}

export function featureOf(correlationId: string | null | undefined): FeatureId {
    if (!correlationId) {
        return DEFAULT_FEATURE_ID;
    }
    const head = String(correlationId).split('-', 1)[0];
    return normalizeFeatureId(head);
}

// 유효한 ID는 그대로(echo), 없거나 형식이 깨졌으면 새로 발급한다.
export function ensureCorrelationId(
    correlationId: string | null | undefined,
    featureId?: string | null,
): string {
    if (isValidCorrelationId(correlationId)) {
        return String(correlationId).trim();
    }
    return newCorrelationId(featureId ?? featureOf(correlationId));
}

// 콘텐츠 기반 결정적 ID — 송신측이 ID를 누락한 레거시 메시지의 dedup 상관용.
// (랜덤 폴백은 같은 발화의 재전송을 서로 다른 ID로 만들어 중복제거를 깨뜨리므로 금지.)
export function deterministicCorrelationId(
    featureId: string | null | undefined,
    seed: string,
): string {
    const feature = normalizeFeatureId(featureId);
    let hash = 5381;
    for (let i = 0; i < seed.length; i += 1) {
        hash = ((hash << 5) + hash + seed.charCodeAt(i)) >>> 0;
    }
    return `${feature}-d${hash.toString(36)}-0000`;
}
