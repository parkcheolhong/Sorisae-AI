/**
 * Shared relay text guards.
 */

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
        /^시청\s*해?\s*주셔서\s*감사합니다[.!?]*$/,
        /^시청\s*해?\s*주셔서\s*감사해요[.!?]*$/,
        /^감사합니다[.!?]*$/,
        /^감사해요[.!?]*$/,
        /^구독(?:과)?\s*좋아요.*부탁.*$/,
        /^구독.*부탁(?:드립니다|합니다)[.!?]*$/,
        /^통역\s*문장[.!?]*$/,
    ],
    ja: [
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

const GLOBAL_OUTRO_HALLUCINATION_PATTERNS: RegExp[] = [
    /\btakk\s+for\s+at/i,
    /\btack\s+f[öo]r\s+att\s+du\s+tittade\b/i,
    /\btak\s+fordi\s+du\s+s[åa]\s+med\b/i,
    /thank you for watching/i,
    /thanks for watching/i,
    /please\s+(?:like|subscribe)/i,
    /don'?t forget to subscribe/i,
    /subscribe to (?:my|the|our) channel/i,
    /vielen dank f[üu]rs zuschauen/i,
    /danke f[üu]rs zuschauen/i,
    /merci d'avoir regard[ée]/i,
    /gracias por ver/i,
    /ご視聴.*ありがとう/u,
    /시청\s*해?\s*주셔서\s*감사/u,
    /amara\.org/i,
    /\bteksting\s+av\b/i,
    /\bundertekst(?:er|et|ing)?\b/i,
    /\btekstet\s+av\b/i,
    /\boversatt\s+av\b/i,
    /\boversettelse\b/i,
    /\bundertextning\b/i,
    /\bunterti?tel/i,
    /\bsous-?titr/i,
    /\bsottotitoli\b/i,
    /\bsubt[ií]tulos?\b/i,
    /\blegendas?\b/i,
    /\bsubtitles?\s+by\b/i,
    /\bcaptions?\s+by\b/i,
    /\btranscription\s+by\b/i,
    /\bsubtitled\s+by\b/i,
    /字幕/u,
    /\b(?:my|the|our)\s+channel\b/i,
    /\bwelcome back to\b/i,
    /\bthis video\b/i,
    /\bin (?:today'?s|this) video\b/i,
    /\blike and subscribe\b/i,
    /\bhit the (?:like|bell)\b/i,
    /\btoday i(?:'|’)?(?:ll| will| am going to| am gonna)?\s+show you\b/i,
    /\bin this tutorial\b/i,
];

const VOICE_RELAY_ECHO_GUARD_MS = 20_000;

const WHISPER_NOISE_SCRIPT_PATTERNS: RegExp[] = [
    /[\u10A0-\u10FF]/u,
    /[\u0530-\u058F]/u,
    /[\u1200-\u137F]/u,
    /[\u2C00-\u2C5F]/u,
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

const WELSH_HALLUCINATION = /\b(?:rwy'n|rwyf|ddweud|dweud)\b/iu;

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

export function formatAutoRelayDelayLabel(ms: number): string {
    return Number.isInteger(ms / 1000) ? `${ms / 1000}초` : `${(ms / 1000).toFixed(1)}초`;
}

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

    return { reject: false };
}

export function normalizeRelayText(value: string): string {
    return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

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
    return relayBigramDice(a, b) >= 0.55;
}

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
    guardWindowMs?: number;
}): { echo: boolean; reason?: string } {
    const nowMs = params.nowMs ?? Date.now();
    const guardWindowMs = typeof params.guardWindowMs === 'number' && params.guardWindowMs > 0
        ? params.guardWindowMs
        : VOICE_RELAY_ECHO_GUARD_MS;
    const within = (sentAtMs?: number) => (
        typeof sentAtMs === 'number'
        && sentAtMs > 0
        && nowMs - sentAtMs < guardWindowMs
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

export function isLikelySilenceHallucination(transcript: string, sourceLang: string): boolean {
    const normalized = normalizeRelayText(transcript);
    if (!normalized) {
        return true;
    }

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
