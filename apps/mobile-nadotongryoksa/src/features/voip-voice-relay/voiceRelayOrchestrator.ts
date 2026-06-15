import { VOICE_RELAY_FILE_SPEECH_RMS_DB } from './voiceRelayAudioMetrics';

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
    meterUnavailableFixedFlushMs: 5_400,
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
    ],
};

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
    return allowedCount / letterLike.length < 0.40;
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

    if (isLikelySilenceHallucination(params.transcript, params.sourceLang)) {
        return { reject: true, reason: 'remote_hallucination' };
    }

    if (
        params.captureTrust !== 'high'
        && isLikelySilenceHallucination(params.translatedText, params.targetLang)
    ) {
        return { reject: true, reason: 'remote_hallucination' };
    }

    return { reject: false };
}

const VOICE_RELAY_ECHO_GUARD_MS = 20_000;

function relayTextsSimilar(left: string, right: string): boolean {
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
    if (wordsA.length === 0 || wordsB.size === 0) {
        return false;
    }
    const overlap = wordsA.filter((word) => wordsB.has(word)).length;
    return overlap / wordsA.length >= 0.45;
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
