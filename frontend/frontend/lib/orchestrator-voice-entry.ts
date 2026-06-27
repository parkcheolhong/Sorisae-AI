export const ORCHESTRATOR_VOICE_CONTEXT_TAGS = ['voice-stt', 'voice-entry'] as const;

export type OrchestratorVoiceSurface = 'admin' | 'marketplace';

const DISCUSS_MARKERS = [
    '아이디어',
    '제안',
    '검토',
    '협업',
    'redis',
    '캐시',
    '어떻게',
    '비교',
    '추천',
    '의견',
];

const EXECUTE_MARKERS = [
    '진행해',
    '진행 해',
    '시작해',
    '승인',
    '반영하고',
    '실행해',
    'go',
    'ok',
];

export function resolveVoiceSpeaker(surface: OrchestratorVoiceSurface): string {
    return surface === 'admin' ? '관리자(음성)' : '고객(음성)';
}

export function normalizeVoiceTranscript(transcript: string): string {
    return String(transcript || '').trim().replace(/\s+/g, ' ');
}

export function buildVoiceContextTags(extra: string[] = []): string[] {
    return [...ORCHESTRATOR_VOICE_CONTEXT_TAGS, ...extra.filter(Boolean)];
}

export function detectVoiceDiscussIntent(transcript: string): boolean {
    const normalized = normalizeVoiceTranscript(transcript).toLowerCase();
    if (!normalized) {
        return false;
    }
    if (normalized.startsWith('/ask') || normalized.startsWith('/search')) {
        return true;
    }
    return DISCUSS_MARKERS.some((marker) => normalized.includes(marker)) || normalized.includes('?');
}

export function detectVoiceExecuteIntent(transcript: string): boolean {
    const normalized = normalizeVoiceTranscript(transcript).toLowerCase();
    if (!normalized) {
        return false;
    }
    if (/\d+(\.\d+)?\s*단계\s*(진행|실행|시작)/.test(normalized)) {
        return true;
    }
    return EXECUTE_MARKERS.some((marker) => normalized.includes(marker));
}

export function enrichVoiceMessageForStage(
    transcript: string,
    options?: {
        stageNumber?: number | null;
        minDiscussStage?: number;
    },
): string {
    const normalized = normalizeVoiceTranscript(transcript);
    if (!normalized) {
        return normalized;
    }
    const stageNumber = options?.stageNumber ?? null;
    const minDiscussStage = options?.minDiscussStage ?? 4;
    const hasStagePrefix = /^\d+(\.\d+)?\s*단계/.test(normalized);
    const hasSlash = normalized.startsWith('/');

    if (
        stageNumber !== null
        && stageNumber >= minDiscussStage
        && detectVoiceDiscussIntent(normalized)
        && !hasStagePrefix
        && !hasSlash
    ) {
        return `${stageNumber}단계 ${normalized}`;
    }

    if (detectVoiceExecuteIntent(normalized) && stageNumber !== null && !hasStagePrefix && !hasSlash) {
        if (/^(진행해|승인|시작해|ok|go)$/i.test(normalized)) {
            return `${stageNumber}단계 진행해줘`;
        }
    }

    return normalized;
}

export function buildVoiceDecisionConfirmation(item: {
    title: string;
    stageNumber?: number | null;
}): string {
    const title = String(item.title || '').trim();
    const stageNumber = item.stageNumber ?? null;
    if (stageNumber) {
        const stageLabel = Number.isInteger(stageNumber)
            ? `${stageNumber}단계`
            : `${String(stageNumber).replace('.5', ' 점 오')}단계`;
        return `${stageLabel}에 ${title} 아이디어를 반영해서 진행할까요?`;
    }
    return `${title} 아이디어를 반영해서 진행할까요?`;
}

export function buildVoiceDiagnosticsPatch(surface: OrchestratorVoiceSurface): Record<string, unknown> {
    return {
        voice_entry: true,
        voice_speaker: resolveVoiceSpeaker(surface),
        voice_context_tags: [...ORCHESTRATOR_VOICE_CONTEXT_TAGS],
    };
}
