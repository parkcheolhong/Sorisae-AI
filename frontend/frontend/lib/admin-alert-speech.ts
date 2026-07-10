import type { OrchestratorCapabilitySummaryCard } from '@/lib/admin-dashboard-types';

export interface AdminAlertSpeechItem {
    id: string;
    level: 'warning' | 'critical';
    title: string;
    message: string;
    action: string;
}

export function normalizeSpeechText(text: string) {
    return text
        .replace(/·/g, ', ')
        .replace(/=/g, ' ')
        .replace(/\//g, ' 중 ')
        .replace(/\s+/g, ' ')
        .trim();
}

export function buildCapabilitySpeechReason(card: OrchestratorCapabilitySummaryCard) {
    if (card.id === 'project-scanner') {
        return `프로젝트 스캐너. ${normalizeSpeechText(card.metric)}. ${normalizeSpeechText(card.detail || '')}`;
    }
    if (card.id === 'code-generator') {
        return `코드 생성 기준 미달. ${normalizeSpeechText(card.metric)}. ${normalizeSpeechText(card.detail || '')}`;
    }
    if (card.id === 'self-healing-engine') {
        return `자가 복구 경고. ${normalizeSpeechText(card.detail || card.metric)}`;
    }
    return `${card.title}. ${normalizeSpeechText(card.metric)}. ${normalizeSpeechText(card.detail || '')}`;
}

export function buildAdminAlertSpeech(
    opsAlerts: AdminAlertSpeechItem[],
    problemCards: OrchestratorCapabilitySummaryCard[],
) {
    const spokenParts: string[] = [];

    const topAlerts = opsAlerts.slice(0, 2);
    for (const alert of topAlerts) {
        spokenParts.push(
            `${alert.level === 'critical' ? '치명 경고' : '주의 경고'}. ` +
            `${normalizeSpeechText(alert.title)}. ` +
            `${normalizeSpeechText(alert.message)}. ` +
            `개선 방안. ${normalizeSpeechText(alert.action)}`
        );
    }

    const topProblem = problemCards[0];
    if (topProblem) {
        spokenParts.push(buildCapabilitySpeechReason(topProblem));
    }

    const secondaryProblem = problemCards[1];
    if (secondaryProblem) {
        spokenParts.push(`추가 경고. ${buildCapabilitySpeechReason(secondaryProblem)}`);
    }

    if (spokenParts.length === 0) {
        return '';
    }
    return `관리자 경고 알림입니다. ${spokenParts.join('. ')}. 상세 조치는 관리자 오케스트레이터 제어에서 확인하세요.`;
}

export function hasSpeechSynthesisActivation() {
    if (typeof navigator === 'undefined') {
        return false;
    }
    const userActivation = navigator.userActivation;
    if (!userActivation) {
        return true;
    }
    return Boolean(userActivation.isActive || userActivation.hasBeenActive);
}

export function speakAdminAlert(text: string) {
    if (!text || typeof window === 'undefined' || !window.speechSynthesis || !hasSpeechSynthesisActivation()) {
        return false;
    }
    void import('@/lib/orchestrator-speech').then(({ speakOrchestratorReply }) => speakOrchestratorReply(text));
    return true;
}

export function assertAdminAlertSpeechContract() {
    const sample = buildAdminAlertSpeech([
        { id: 'sample', level: 'warning', title: '제목', message: '메시지', action: '조치' },
    ], []);
    if (!sample.includes('관리자 경고 알림입니다.')) {
        throw new Error('admin alert speech contract 누락: 기본 음성 조립 문구 필요');
    }
}
