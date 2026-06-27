import { VOICE_RELAY_FILE_SPEECH_RMS_DB } from './voiceRelayAudioMetrics';

// NOTE: fallback 값은 SSOT(worldlinco_tuning_config.json voip)와 정합 유지.
// (G1 정합) maxSegmentMs=12000·silenceFlushMs=1500 은 SSOT(vad_max_segment_ms·vad_silence_flush_ms)와
// 동일하게 두어, 원격 fetch 실패/콜드스타트 시에도 calibrated 정상값(자연 장문 8~12s 수용)과 일치시킨다.
// (이전 7000 폴백은 튜닝 미로드 구간에서 장문장을 7s 에 강제 flush → '중간 음성 사망 후 분할'을 유발했다.)
export const VOICE_RELAY_VAD_DEFAULTS = {
    /** Minimum capture window before any flush/send (prevents ultra-short STT clips). */
    minSegmentMs: 2_200,
    maxSegmentMs: 12_000,
    /** Pause after last speech before ending an utterance (natural phrase boundary). */
    silenceFlushMs: 1_500,
    shortSpeechThresholdMs: 3_000,
    speechMeterMinDb: -52,
    meterPollMs: 180,
    /** Android dead-meter safety cap; phrase boundary uses file-RMS VAD first. */
    meterUnavailableFixedFlushMs: 4_000,
    /** Poll partial recording file every N meter ticks when Android metering is dead. */
    meterUnavailableFilePollEvery: 5,
} as const;

export function resolveVoiceRelayFixedFlushDelayMs(
    meterUnavailable: boolean,
    config: typeof VOICE_RELAY_VAD_DEFAULTS = VOICE_RELAY_VAD_DEFAULTS,
): number {
    if (meterUnavailable) {
        return config.meterUnavailableFixedFlushMs;
    }
    return config.maxSegmentMs;
}

export const VOICE_RELAY_SILENCE_PEAK_DB = -159;

const SILENCE_HALLUCINATION_PATTERNS: Record<string, RegExp[]> = {
    en: [
        /^hello\.?$/i,
        /^hi\.?$/i,
        /^hey\.?$/i,
        /^you\.?$/i,
        /^thank you\.?$/i,
        /^thanks\.?$/i,
        /^ok(?:ay)?\.?$/i,
        /^bye\.?$/i,
        /^um+\.?$/i,
        /^uh+\.?$/i,
        /^hmm+\.?$/i,
        /^the\.?$/i,
        /^a\.?$/i,
        /^i\.?$/i,
    ],
    ko: [
        /^안녕(?:하세요|히)?\.?$/,
        /^너\.?$/,
        /^음+\.?$/,
        /^어+\.?$/,
        // Whisper 가 무음/잡음 구간에서 흔히 뱉는 "정중한 마무리" 환각 (유튜브 아웃트로 계열).
        /^시청\s*해?\s*주셔서\s*감사합니다[.!?]*$/,
        /^시청\s*해?\s*주셔서\s*감사해요[.!?]*$/,
        /^감사합니다[.!?]*$/,
        /^감사해요[.!?]*$/,
        /^구독(?:과)?\s*좋아요.*부탁.*$/,
        /^구독.*부탁(?:드립니다|합니다)[.!?]*$/,
        // 근접무음에서 반복 생성돼 상대에게 중복 발화되던 메타 단어 환각("통역 문장"→"翻訳文").
        /^통역\s*문장[.!?]*$/,
    ],
    ja: [
        // 일본어 Whisper 무음 환각 1순위: "ご視聴ありがとうございました" 계열 (유튜브 아웃트로).
        /^ご視聴\s*(?:ありがとうございました|ありがとうございます|ありがとう)[。.!?]*$/u,
        /^ありがとうございました[。.!?]*$/u,
        /^ありがとうございます[。.!?]*$/u,
        /^チャンネル登録\s*(?:を)?\s*(?:よろしく)?\s*お願いします[。.!?]*$/u,
        /^(?:では|それでは)?\s*また(?:ね)?[。.!?]*$/u,
        /^(?:お)?やすみ(?:なさい)?[。.!?]*$/u,
        /^バイバイ[。.!?]*$/u,
        /^はい[。.!?]*$/u,
        /^えー?と+[。.!?]*$/u,
        /^あの+[。.!?]*$/u,
        /^ん+[。.!?]*$/u,
    ],
};

// 언어 무관 유튜브 아웃트로/자막 크레딧 환각. Whisper 가 무음·메아리 구간에서 강제 디코딩 언어와
// 무관하게 흔히 뱉는 정형 문구(스칸디나비아·독·불·서 포함). STT 가 'no/sv/da' 등으로 오탐지해도
// sourceLang 별 사전을 통과하던 문제(예: "Takk for att du så med." → 영어로 통역·발화)를 막는다.
const GLOBAL_OUTRO_HALLUCINATION_PATTERNS: RegExp[] = [
    /\btakk\s+for\s+at/i, // no: "takk for at(t) du så / takk for ating med" 환청 변형 전부
    /\btack\s+f[öo]r\s+att\s+du\s+tittade\b/i, // sv: "tack för att du tittade"
    /\btak\s+fordi\s+du\s+s[åa]\s+med\b/i, // da: "tak fordi du så med"
    /thank you for watching/i,
    /thanks for watching/i,
    /please\s+(?:like|subscribe)/i,
    /don'?t forget to subscribe/i,
    /subscribe to (?:my|the|our) channel/i,
    /vielen dank f[üu]rs zuschauen/i, // de
    /danke f[üu]rs zuschauen/i, // de
    /merci d'avoir regard[ée]/i, // fr
    /gracias por ver/i, // es
    /ご視聴.*ありがとう/u,
    /시청\s*해?\s*주셔서\s*감사/u,
    /amara\.org/i,
    // 자막/번역 크레딧 환각(무음·메아리 구간에서 매우 흔함, 이름과 함께 생성).
    // 예: "Teksting av Nicolai Winther", "Undertekster av ...". 통역 경로로 흘러
    // 발화되던 핵심 누수 케이스. 일반 여행 대화엔 등장하지 않는 메타 문구만 차단.
    /\bteksting\s+av\b/i, // no: subtitling by
    /\bundertekst(?:er|et|ing)?\b/i, // no/da: subtitles
    /\btekstet\s+av\b/i, // no: texted by
    /\boversatt\s+av\b/i, // no: translated by
    /\boversettelse\b/i, // no: translation
    /\bundertextning\b/i, // sv: subtitling
    /\bunterti?tel/i, // de: subtitles
    /\bsous-?titr/i, // fr: subtitles/subtitling
    /\bsottotitoli\b/i, // it
    /\bsubt[ií]tulos?\b/i, // es
    /\blegendas?\b/i, // pt: subtitles
    /\bsubtitles?\s+by\b/i,
    /\bcaptions?\s+by\b/i,
    /\btranscription\s+by\b/i,
    /\bsubtitled\s+by\b/i,
    /字幕/u, // ja/zh: subtitles
    // 유튜브 인트로/채널 환각(무음 구간에서 흔함). 통역/여행 대화엔 절대 등장하지 않는 고유 토큰만.
    // 예: "Hello everyone, welcome back to my channel, today I will show you ..."
    /\b(?:my|the|our)\s+channel\b/i,
    /\bwelcome back to\b/i,
    /\bthis video\b/i,
    /\bin (?:today'?s|this) video\b/i,
    /\blike and subscribe\b/i,
    /\bhit the (?:like|bell)\b/i,
    /\btoday i(?:'|’)?(?:ll| will| am going to| am gonna)?\s+show you\b/i,
    /\bin this tutorial\b/i,
];

export function normalizeRelayText(value: string): string {
    return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

const WHISPER_NOISE_SCRIPT_PATTERNS: RegExp[] = [
    /[\u10A0-\u10FF]/u, // Georgian
    /[\u0530-\u058F]/u, // Armenian
    /[\u1200-\u137F]/u, // Ethiopic
    /[\u2C00-\u2C5F]/u, // Glagolitic
];

const RELAY_LANG_CHAR_CHECKS: Record<string, RegExp> = {
    ko: /[\uAC00-\uD7A3\u3131-\u318E]/u,
    en: /[A-Za-z]/,
    ja: /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/u,
    zh: /[\u4E00-\u9FFF]/u,
    vi: /[\u00C0-\u024FA-Za-z\u1E00-\u1EFF]/u,
    th: /[\u0E00-\u0E7F]/u,
    ar: /[\u0600-\u06FF]/u,
    ru: /[\u0400-\u04FF]/u,
};

const RELAY_NEUTRAL_CHAR = /[\s\d.,!?;:'"()[\]{}<>/\\|@#$%^&*+=~`\-—…·]/u;

function normalizeRelayLangCode(lang: string): string {
    return String(lang || '').trim().toLowerCase().split('-')[0];
}

function charMatchesRelayLangs(char: string, langs: string[]): boolean {
    if (RELAY_NEUTRAL_CHAR.test(char)) {
        return true;
    }
    return langs.some((lang) => {
        const pattern = RELAY_LANG_CHAR_CHECKS[lang];
        return pattern ? pattern.test(char) : /[A-Za-z\u00C0-\u024F]/.test(char);
    });
}

const WELSH_HALLUCINATION = /\b(?:rwy'n|rwyf|ddweud|dweud)\b/iu;

function containsUnexpectedNoiseScript(text: string, expectedLangs: string[]): boolean {
    const langs = new Set(expectedLangs.map(normalizeRelayLangCode).filter(Boolean));
    if (langs.has('ka') || langs.has('hy') || langs.has('am') || langs.has('cy')) {
        return false;
    }
    if (WELSH_HALLUCINATION.test(text)) {
        return true;
    }
    return WHISPER_NOISE_SCRIPT_PATTERNS.some((pattern) => pattern.test(text));
}

/** Rejects Whisper noise hallucinations (Georgian spam, mojibake, script mismatch). */
export function isLikelyGibberishRelayTranscript(
    transcript: string,
    expectedLangs: string[],
): boolean {
    const trimmed = String(transcript || '').trim();
    if (!trimmed) {
        return true;
    }
    if (/\uFFFD/u.test(trimmed)) {
        return true;
    }

    const langs = [...new Set(
        expectedLangs
            .map(normalizeRelayLangCode)
            .filter(Boolean),
    )];
    if (containsUnexpectedNoiseScript(trimmed, langs)) {
        return true;
    }

    const compact = trimmed.replace(/[\s\d.,!?;:'"()[\]{}<>/\\|@#$%^&*+=~`\-—…·]/gu, '');
    if (!compact) {
        return true;
    }
    if (/(.)\1{3,}/u.test(compact)) {
        return true;
    }

    const letterLike = [...compact].filter((char) => !RELAY_NEUTRAL_CHAR.test(char));
    if (letterLike.length === 0) {
        return true;
    }

    const allowedCount = letterLike.filter((char) => charMatchesRelayLangs(char, langs)).length;
    // (G4 정합) 백엔드 _is_likely_gibberish_relay_transcript 와 동일 임계(0.35).
    // 클라가 0.40 으로 더 엄격하면 백엔드는 통과시킬 혼합/자연 발화를 선차단할 수 있어,
    // 백엔드가 최종 게이트이므로 클라를 0.35 로 완화해 오차단(false reject)만 줄인다.
    return allowedCount / letterLike.length < 0.35;
}

export function shouldRejectRemoteVoiceRelayPlayback(params: {
    captureTrust?: string | null;
    transcript: string;
    translatedText: string;
    sourceLang: string;
    targetLang: string;
    langScope: string[];
}): { reject: boolean; reason?: string } {
    if (params.captureTrust === 'low') {
        return { reject: true, reason: 'low_capture_trust' };
    }

    const langScope = params.langScope;
    if (isLikelyGibberishRelayTranscript(params.transcript, langScope)) {
        return { reject: true, reason: 'gibberish_transcript' };
    }
    if (isLikelyGibberishRelayTranscript(params.translatedText, langScope)) {
        return { reject: true, reason: 'gibberish_translation' };
    }
    if (
        isLikelyRepetitionHallucination(params.transcript)
        || isLikelyRepetitionHallucination(params.translatedText)
    ) {
        return { reject: true, reason: 'repetition_hallucination' };
    }

    // NOTE: 무음 인사말 환각 필터(isLikelySilenceHallucination)는 원격 재생 경로에서
    // 제거한다. 원격 메시지는 발신측 VAD+STT 를 이미 통과해 전송된 "실제 발화"이고,
    // "안녕하세요/おはよう/hello/thank you" 같은 인사말은 대화의 핵심이라 반드시
    // 들려야 한다. (이전에는 번역문이 ko '안녕하세요'에 매칭되어 수신측이 재생을
    // 스킵 → 듣는 사람에게 안 들리는 버그가 발생했다.) 실제 위험(지비리시/반복/
    // 명시적 low capture_trust)은 위에서 계속 차단한다. 무음 환각 차단은 발신측
    // 로컬 캡처 경로에서 담당한다.

    return { reject: false };
}

const VOICE_RELAY_ECHO_GUARD_MS = 20_000;

// 문자 바이그램 집합(공백 제거) — 공백을 쓰지 않는 CJK(일본어/중국어/한국어)에서도
// 유사도를 측정하기 위해 단어가 아닌 인접 문자쌍으로 비교한다.
function relayCharBigrams(value: string): string[] {
    const compact = value.replace(/\s+/g, '');
    if (compact.length < 2) {
        return compact ? [compact] : [];
    }
    const grams: string[] = [];
    for (let i = 0; i < compact.length - 1; i += 1) {
        grams.push(compact.slice(i, i + 2));
    }
    return grams;
}

// Sørensen–Dice 계수(0~1). 같은 문장이 STT로 미세하게 다르게 받아써져도(에코 잔향)
// 높은 값을 돌려줘 언어 비의존으로 에코를 잡는다.
function relayBigramDice(a: string, b: string): number {
    const ga = relayCharBigrams(a);
    const gb = relayCharBigrams(b);
    if (ga.length === 0 || gb.length === 0) {
        return 0;
    }
    const counts = new Map<string, number>();
    for (const gram of gb) {
        counts.set(gram, (counts.get(gram) ?? 0) + 1);
    }
    let intersection = 0;
    for (const gram of ga) {
        const remaining = counts.get(gram) ?? 0;
        if (remaining > 0) {
            intersection += 1;
            counts.set(gram, remaining - 1);
        }
    }
    return (2 * intersection) / (ga.length + gb.length);
}

export function relayTextsSimilar(left: string, right: string): boolean {
    const a = normalizeRelayText(left);
    const b = normalizeRelayText(right);
    if (!a || !b) {
        return false;
    }
    if (a === b || a.includes(b) || b.includes(a)) {
        return true;
    }
    const wordsA = a.split(' ').filter((word) => word.length > 2);
    const wordsB = new Set(b.split(' ').filter((word) => word.length > 2));
    if (wordsA.length > 0 && wordsB.size > 0) {
        const overlap = wordsA.filter((word) => wordsB.has(word)).length;
        if (overlap / wordsA.length >= 0.45) {
            return true;
        }
    }
    // 공백 기반 단어 비교가 무력한 CJK/연속 스크립트 대비 문자 바이그램 유사도로 보강.
    // 0.55 이상이면 동일 발화의 재인식(에코)으로 간주한다(서로 다른 사람의 발화는
    // 통상 0.3 미만이라 정상 응답을 막지 않는다).
    return relayBigramDice(a, b) >= 0.55;
}

/** Blocks callee TTS echo and caller playback echo of recent relay text. */
export function isLikelyVoiceRelayEcho(params: {
    transcript: string;
    translatedText: string;
    nowMs?: number;
    recentLocalTranslated?: string;
    recentLocalSentAtMs?: number;
    recentRemotePlaybackTranslated?: string;
    recentRemotePlaybackAtMs?: number;
    recentRemoteTranscript?: string;
    recentRemoteAtMs?: number;
}): { echo: boolean; reason?: string } {
    const nowMs = params.nowMs ?? Date.now();
    const within = (sentAtMs?: number) => (
        typeof sentAtMs === 'number'
        && sentAtMs > 0
        && nowMs - sentAtMs < VOICE_RELAY_ECHO_GUARD_MS
    );

    if (within(params.recentLocalSentAtMs) && params.recentLocalTranslated) {
        if (
            relayTextsSimilar(params.transcript, params.recentLocalTranslated)
            || relayTextsSimilar(params.translatedText, params.recentLocalTranslated)
        ) {
            return { echo: true, reason: 'local_relay_echo' };
        }
    }

    if (within(params.recentRemotePlaybackAtMs) && params.recentRemotePlaybackTranslated) {
        if (
            relayTextsSimilar(params.transcript, params.recentRemotePlaybackTranslated)
            || relayTextsSimilar(params.translatedText, params.recentRemotePlaybackTranslated)
        ) {
            return { echo: true, reason: 'playback_pickup_echo' };
        }
    }

    if (within(params.recentRemoteAtMs) && params.recentRemoteTranscript) {
        if (
            relayTextsSimilar(params.transcript, params.recentRemoteTranscript)
            || relayTextsSimilar(params.translatedText, params.recentRemoteTranscript)
        ) {
            return { echo: true, reason: 'remote_transcript_echo' };
        }
    }

    return { echo: false };
}

export function isVoiceRelaySilenceCapture(
    meterUnavailable: boolean,
    peakMeterDb: number,
    hasSpeech: boolean,
): boolean {
    return meterUnavailable && peakMeterDb <= VOICE_RELAY_SILENCE_PEAK_DB && !hasSpeech;
}

function countLeadingInlinePhraseRepeats(words: string[], minRepeat: number): number {
    if (words.length < minRepeat * 2) {
        return 0;
    }

    const maxUnitLen = Math.min(12, Math.floor(words.length / minRepeat));
    for (let unitLen = 1; unitLen <= maxUnitLen; unitLen += 1) {
        const unitNorm = normalizeRelayText(words.slice(0, unitLen).join(' '));
        if (!unitNorm || unitNorm.length < 2) {
            continue;
        }

        let repeats = 1;
        for (let index = unitLen; index + unitLen <= words.length; index += unitLen) {
            const chunkNorm = normalizeRelayText(words.slice(index, index + unitLen).join(' '));
            if (chunkNorm !== unitNorm) {
                break;
            }
            repeats += 1;
        }

        const coveredWords = repeats * unitLen;
        if (repeats >= minRepeat && coveredWords >= Math.ceil(words.length * 0.75)) {
            return repeats;
        }
    }

    return 0;
}

export function collapseRepeatedRelayPhrases(text: string, minRepeat = 3): string {
    const trimmed = text.trim().replace(/\s+/g, ' ');
    if (!trimmed) {
        return '';
    }

    const sentenceParts = trimmed
        .split(/\.\s+/)
        .map((part) => part.trim().replace(/[.!?。]+$/g, ''))
        .filter(Boolean);
    if (sentenceParts.length >= minRepeat) {
        const firstNorm = normalizeRelayText(sentenceParts[0]);
        if (sentenceParts.every((part) => normalizeRelayText(part) === firstNorm)) {
            return sentenceParts[0];
        }
    }

    const commaParts = trimmed.split(/,\s+/).map((part) => part.trim()).filter(Boolean);
    if (commaParts.length >= minRepeat) {
        const firstNorm = normalizeRelayText(commaParts[0]);
        if (commaParts.every((part) => normalizeRelayText(part) === firstNorm)) {
            return commaParts[0];
        }
    }

    const words = trimmed.split(' ').filter(Boolean);
    const maxUnitLen = Math.min(12, Math.floor(words.length / minRepeat));
    for (let unitLen = 1; unitLen <= maxUnitLen; unitLen += 1) {
        const unitNorm = normalizeRelayText(words.slice(0, unitLen).join(' '));
        if (!unitNorm) {
            continue;
        }

        let repeats = 1;
        for (let index = unitLen; index + unitLen <= words.length; index += unitLen) {
            const chunkNorm = normalizeRelayText(words.slice(index, index + unitLen).join(' '));
            if (chunkNorm !== unitNorm) {
                break;
            }
            repeats += 1;
        }

        if (repeats >= minRepeat && repeats * unitLen === words.length) {
            return words.slice(0, unitLen).join(' ');
        }
    }

    return trimmed;
}

/** Whisper on looped TTS/remote audio often emits the same phrase dozens of times in one segment. */
export function isLikelyRepetitionHallucination(text: string): boolean {
    const trimmed = String(text || '').trim().replace(/\s+/g, ' ');
    if (!trimmed) {
        return false;
    }

    const words = trimmed.split(' ').filter(Boolean);
    if (countLeadingInlinePhraseRepeats(words, 4) >= 4) {
        return true;
    }

    if (trimmed.length > 80) {
        const collapsed = collapseRepeatedRelayPhrases(trimmed);
        if (collapsed.length > 0 && collapsed.length <= trimmed.length * 0.35) {
            return true;
        }
    }

    if (words.length >= 24) {
        const uniqueWords = new Set(words.map((word) => normalizeRelayText(word)).filter(Boolean));
        if (uniqueWords.size <= Math.max(3, Math.floor(words.length * 0.15))) {
            return true;
        }
    }

    return false;
}

export const VOICE_RELAY_MAX_SPEAK_CHARS = 240;

export function isLikelySilenceHallucination(transcript: string, sourceLang: string): boolean {
    const normalized = normalizeRelayText(transcript);
    if (!normalized) {
        return true;
    }

    // 언어 무관 아웃트로/자막 환각 우선 차단(STT 언어 오탐지로 sourceLang 사전을 우회하던 경우 대비).
    if (GLOBAL_OUTRO_HALLUCINATION_PATTERNS.some((pattern) => pattern.test(normalized))) {
        return true;
    }

    const lang = String(sourceLang || '').trim().toLowerCase().split('-')[0] || 'en';
    const patterns = SILENCE_HALLUCINATION_PATTERNS[lang] ?? SILENCE_HALLUCINATION_PATTERNS.en;
    if (patterns.some((pattern) => pattern.test(normalized))) {
        return true;
    }

    if (lang === 'en' && normalized.length <= 3) {
        return true;
    }

    if (lang === 'ko' && normalized.length <= 1) {
        return true;
    }

    if (lang === 'ja' && normalized.length <= 1) {
        return true;
    }

    return false;
}

export type VoiceRelayFlushReason = 'silence' | 'max_duration' | 'manual';

export type VoiceRelaySegmentDecision =
    | { action: 'continue' }
    | { action: 'flush'; reason: VoiceRelayFlushReason; isFinal: boolean };

export type VoiceRelaySegmentState = {
    segmentStartedAtMs: number;
    lastSpeechAtMs: number | null;
    hasSpeech: boolean;
    chunkIndex: number;
};

export function createVoiceRelayUtteranceId(callId: string, nowMs: number = Date.now()): string {
    const safeCallId = String(callId || 'call').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 48);
    return `${safeCallId}-${nowMs}`;
}

export function createInitialVoiceRelaySegmentState(nowMs: number, chunkIndex = 0): VoiceRelaySegmentState {
    return {
        segmentStartedAtMs: nowMs,
        lastSpeechAtMs: null,
        hasSpeech: false,
        chunkIndex,
    };
}

export function updateVoiceRelaySegmentSpeechState(
    state: VoiceRelaySegmentState,
    currentMeterDb: number,
    nowMs: number,
    speechMeterMinDb: number = VOICE_RELAY_VAD_DEFAULTS.speechMeterMinDb,
): VoiceRelaySegmentState {
    if (currentMeterDb < speechMeterMinDb) {
        return state;
    }

    return {
        ...state,
        hasSpeech: true,
        lastSpeechAtMs: nowMs,
    };
}

/** File-RMS fallback for Android devices where expo-audio metering stays at -160. */
export function updateVoiceRelaySegmentSpeechStateFromFileRms(
    state: VoiceRelaySegmentState,
    fileRmsDb: number | null,
    nowMs: number,
    speechRmsDb: number = VOICE_RELAY_FILE_SPEECH_RMS_DB,
): VoiceRelaySegmentState {
    if (fileRmsDb === null || fileRmsDb < speechRmsDb) {
        return state;
    }

    return {
        ...state,
        hasSpeech: true,
        lastSpeechAtMs: nowMs,
    };
}

export function evaluateVoiceRelaySegmentDecision(
    state: VoiceRelaySegmentState,
    nowMs: number,
    currentMeterDb: number,
    config: typeof VOICE_RELAY_VAD_DEFAULTS = VOICE_RELAY_VAD_DEFAULTS,
): VoiceRelaySegmentDecision {
    const durationMs = nowMs - state.segmentStartedAtMs;
    const speechNow = currentMeterDb >= config.speechMeterMinDb;

    if (durationMs >= config.maxSegmentMs) {
        if (state.hasSpeech || speechNow) {
            return { action: 'flush', reason: 'max_duration', isFinal: false };
        }
        return { action: 'continue' };
    }

    if (!state.hasSpeech && !speechNow) {
        return { action: 'continue' };
    }

    if (speechNow) {
        return { action: 'continue' };
    }

    const lastSpeechAt = state.lastSpeechAtMs ?? state.segmentStartedAtMs;
    const silenceMs = nowMs - lastSpeechAt;

    if (state.hasSpeech && silenceMs >= config.silenceFlushMs && durationMs >= config.minSegmentMs) {
        return { action: 'flush', reason: 'silence', isFinal: true };
    }

    return { action: 'continue' };
}

export function nextVoiceRelaySegmentStateAfterFlush(
    state: VoiceRelaySegmentState,
    isFinal: boolean,
    nowMs: number,
): VoiceRelaySegmentState {
    if (isFinal) {
        return createInitialVoiceRelaySegmentState(nowMs, 0);
    }

    return createInitialVoiceRelaySegmentState(nowMs, state.chunkIndex + 1);
}
