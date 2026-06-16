'use client';

import { hasSpeechSynthesisActivation, normalizeSpeechText } from '@/lib/admin-alert-speech';

const PREFERRED_KOREAN_VOICE_HINTS = [
    'heami',
    'injoon',
    'sunhi',
    'yuna',
    'google ko',
    'google korean',
    'microsoft ko',
    'naver',
    'neural',
];

function stripMarkdownForSpeech(text: string): string {
    return text
        .replace(/```[\s\S]*?```/g, ' 코드 블록 생략. ')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/^#{1,6}\s+/gm, '')
        .replace(/^\s*[-*]\s+/gm, '')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .replace(/\n{2,}/g, '. ')
        .replace(/\n/g, ', ');
}

export function summarizeForSpeech(text: string, maxLength = 520): string {
    const normalized = normalizeSpeechText(stripMarkdownForSpeech(String(text || '').trim()));
    if (!normalized) {
        return '';
    }
    if (normalized.length <= maxLength) {
        return normalized;
    }
    const clipped = normalized.slice(0, maxLength);
    const lastBreak = Math.max(clipped.lastIndexOf('. '), clipped.lastIndexOf(', '));
    const safeCut = lastBreak > maxLength * 0.55 ? clipped.slice(0, lastBreak + 1) : `${clipped.trim()}…`;
    return `${safeCut.trim()} 이하 생략.`;
}

function scoreKoreanVoice(voice: SpeechSynthesisVoice): number {
    const name = voice.name.toLowerCase();
    const lang = voice.lang.toLowerCase();
    let score = 0;
    if (lang.startsWith('ko')) {
        score += 10;
    }
    if (voice.localService) {
        score += 2;
    }
    for (let index = 0; index < PREFERRED_KOREAN_VOICE_HINTS.length; index += 1) {
        if (name.includes(PREFERRED_KOREAN_VOICE_HINTS[index])) {
            score += 20 - index;
        }
    }
    if (name.includes('online') || name.includes('natural') || name.includes('neural')) {
        score += 4;
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
        window.setTimeout(finish, 300);
    });
}

export async function speakOrchestratorReply(text: string): Promise<boolean> {
    const speechText = summarizeForSpeech(text);
    if (!speechText || typeof window === 'undefined' || !window.speechSynthesis || !hasSpeechSynthesisActivation()) {
        return false;
    }

    const voices = await loadSpeechVoices();
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.lang = 'ko-KR';
    utterance.rate = 0.94;
    utterance.pitch = 1;
    utterance.volume = 1;
    const koreanVoice = pickKoreanSpeechVoice(voices);
    if (koreanVoice) {
        utterance.voice = koreanVoice;
    }

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    return true;
}

export function speakOrchestratorReplySync(text: string): boolean {
    void speakOrchestratorReply(text);
    return true;
}
