'use client';

import { hasSpeechSynthesisActivation, normalizeSpeechText } from '@/lib/admin-alert-speech';

const PREFERRED_KOREAN_VOICE_HINTS = [
    'sunhi online',
    'heami online',
    'injoon online',
    'yuna online',
    'google korean',
    'google ko',
    'microsoft sunhi',
    'microsoft heami',
    'microsoft injoon',
    'neural',
    'natural',
    'online',
    'sunhi',
    'heami',
    'injoon',
    'yuna',
];

const STAGE_NUMBER_WORDS: Record<string, string> = {
    '1': '일',
    '2': '이',
    '3': '삼',
    '4': '사',
    '5': '오',
    '6': '육',
    '7': '칠',
    '8': '팔',
    '9': '구',
    '10': '십',
};

let speechQueue: Promise<void> = Promise.resolve();
let speechQueueGeneration = 0;
let activeServerAudio: HTMLAudioElement | null = null;

const ORCHESTRATOR_TTS_ENDPOINT = '/api/llm/voice/synthesize';

function stripMarkdownForSpeech(text: string): string {
    return text
        .replace(/```[\s\S]*?```/g, ' ')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/^#{1,6}\s+/gm, '')
        .replace(/^\s*[-*]\s+/gm, '')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .replace(/[「」『』]/g, '')
        .replace(/###\s*[^\n]+/g, ' ')
        .replace(/[⚡⏳💡🧠📋✅❌🔧]/g, ' ')
        .replace(/[\u{1F300}-\u{1FAFF}]/gu, ' ')
        .replace(/\n{2,}/g, '. ')
        .replace(/\n/g, ', ');
}

function speakStageNumber(match: string, integerPart: string, decimalPart?: string): string {
    const whole = STAGE_NUMBER_WORDS[integerPart] || integerPart;
    if (decimalPart === '5') {
        return `${whole} 점 오`;
    }
    return whole;
}

export function humanizeOrchestratorSpeech(text: string): string {
    let normalized = normalizeSpeechText(stripMarkdownForSpeech(String(text || '').trim()));
    if (!normalized) {
        return '';
    }

    normalized = normalized
        .replace(/\bRedis\b/gi, '레디스')
        .replace(/\bAPI\b/gi, '에이피아이')
        .replace(/\bSTT\b/gi, '음성 인식')
        .replace(/\bTTS\b/gi, '음성 안내')
        .replace(/\bSSOT\b/gi, '단일 기준')
        .replace(/(\d+(?:\.\d+)?)\s*단계/g, (_, raw: string) => {
            const [integerPart, decimalPart] = raw.split('.');
            return `${speakStageNumber(raw, integerPart, decimalPart)} 단계`;
        })
        .replace(/진행할까요\?/g, '진행할까요?')
        .replace(/반영하고/g, '반영해서')
        .replace(/\.{2,}/g, '.')
        .replace(/\s+/g, ' ')
        .trim();

    return normalized;
}

export function summarizeForSpeech(text: string, maxLength = 420): string {
    const normalized = humanizeOrchestratorSpeech(text);
    if (!normalized) {
        return '';
    }
    if (normalized.length <= maxLength) {
        return normalized;
    }
    const clipped = normalized.slice(0, maxLength);
    const lastBreak = Math.max(clipped.lastIndexOf('. '), clipped.lastIndexOf(', '), clipped.lastIndexOf('? '));
    const safeCut = lastBreak > maxLength * 0.5 ? clipped.slice(0, lastBreak + 1) : `${clipped.trim()}.`;
    return `${safeCut.trim()} 나머지는 화면에서 이어서 확인해 주세요.`;
}

function splitSpeechSentences(text: string): string[] {
    return text
        .split(/(?<=[.?!…])\s+/)
        .map((part) => part.trim())
        .filter(Boolean);
}

function scoreKoreanVoice(voice: SpeechSynthesisVoice): number {
    const name = voice.name.toLowerCase();
    const lang = voice.lang.toLowerCase();
    let score = 0;
    if (lang.startsWith('ko')) {
        score += 10;
    }
    if (!voice.localService) {
        score += 3;
    }
    for (let index = 0; index < PREFERRED_KOREAN_VOICE_HINTS.length; index += 1) {
        if (name.includes(PREFERRED_KOREAN_VOICE_HINTS[index])) {
            score += 24 - index;
        }
    }
    if (name.includes('online') || name.includes('natural') || name.includes('neural')) {
        score += 6;
    }
    if (name.includes('desktop') || name.includes('mobile')) {
        score -= 2;
    }
    return score;
}

export function pickKoreanSpeechVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
    const koreanVoices = voices.filter((voice) => voice.lang.toLowerCase().startsWith('ko'));
    if (koreanVoices.length === 0) {
        return null;
    }
    return [...koreanVoices].sort((left, right) => scoreKoreanVoice(right) - scoreKoreanVoice(left))[0];
}

async function loadSpeechVoices(): Promise<SpeechSynthesisVoice[]> {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
        return [];
    }
    const existing = window.speechSynthesis.getVoices();
    if (existing.length > 0) {
        return existing;
    }
    return await new Promise((resolve) => {
        let settled = false;
        const finish = () => {
            if (settled) {
                return;
            }
            settled = true;
            resolve(window.speechSynthesis.getVoices());
        };
        window.speechSynthesis.onvoiceschanged = finish;
        window.setTimeout(finish, 800);
    });
}

function speakSingleUtterance(
    text: string,
    voice: SpeechSynthesisVoice | null,
): Promise<void> {
    return new Promise((resolve) => {
        if (typeof window === 'undefined' || !window.speechSynthesis) {
            resolve();
            return;
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ko-KR';
        utterance.rate = 0.88;
        utterance.pitch = 0.96;
        utterance.volume = 1;
        if (voice) {
            utterance.voice = voice;
        }
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
    });
}

function delay(ms: number): Promise<void> {
    return new Promise((resolve) => {
        window.setTimeout(resolve, ms);
    });
}

function stopServerAudioPlayback(): void {
    if (!activeServerAudio) {
        return;
    }
    activeServerAudio.pause();
    activeServerAudio.src = '';
    activeServerAudio = null;
}

async function speakWithServerTts(text: string, generation: number): Promise<boolean> {
    try {
        const response = await fetch(ORCHESTRATOR_TTS_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
            cache: 'no-store',
        });
        if (!response.ok) {
            return false;
        }
        const payload = await response.json() as {
            tts_delivery?: string;
            audio_base64?: string | null;
            audio_format?: string | null;
        };
        if (
            generation !== speechQueueGeneration
            || payload.tts_delivery !== 'server_audio'
            || !payload.audio_base64
            || !String(payload.audio_format || '').startsWith('audio/')
        ) {
            return false;
        }

        const audio = new Audio(`data:${payload.audio_format};base64,${payload.audio_base64}`);
        activeServerAudio = audio;
        await new Promise<void>((resolve, reject) => {
            audio.onended = () => resolve();
            audio.onerror = () => reject(new Error('server tts playback failed'));
            void audio.play().catch(reject);
        });
        if (activeServerAudio === audio) {
            activeServerAudio = null;
        }
        return generation === speechQueueGeneration;
    } catch {
        return false;
    }
}

async function speakWithBrowserTts(text: string, generation: number): Promise<boolean> {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
        return false;
    }

    const voices = await loadSpeechVoices();
    const koreanVoice = pickKoreanSpeechVoice(voices);
    const sentences = splitSpeechSentences(text);

    for (const sentence of sentences) {
        if (generation !== speechQueueGeneration) {
            return false;
        }
        await speakSingleUtterance(sentence, koreanVoice);
        if (generation !== speechQueueGeneration) {
            return false;
        }
        await delay(140);
    }
    return true;
}

export async function speakOrchestratorReply(text: string): Promise<boolean> {
    const speechText = summarizeForSpeech(text);
    if (!speechText || typeof window === 'undefined' || !hasSpeechSynthesisActivation()) {
        return false;
    }

    const generation = speechQueueGeneration + 1;
    speechQueueGeneration = generation;
    stopServerAudioPlayback();
    window.speechSynthesis?.cancel();

    speechQueue = speechQueue.then(async () => {
        const spoke = await speakWithServerTts(speechText, generation);
        if (spoke || generation !== speechQueueGeneration) {
            return;
        }
        await speakWithBrowserTts(speechText, generation);
    });

    await speechQueue;
    return true;
}

export function speakOrchestratorReplySync(text: string): boolean {
    void speakOrchestratorReply(text);
    return true;
}

export function stopOrchestratorSpeech(): void {
    speechQueueGeneration += 1;
    stopServerAudioPlayback();
    if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
}
