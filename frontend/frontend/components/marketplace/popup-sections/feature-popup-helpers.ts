import type { FeaturePopupState, FeatureStreamConnection } from '@/hooks/use-feature-orchestrator';

export const POPUP_STATE_FLOW: FeaturePopupState[] = [
    'idle',
    'accepted',
    'preview_running',
    'preview_ready',
    'final_running',
    'quality_review',
    'completed',
];

const STATE_LABELS: Record<FeaturePopupState, string> = {
    idle: '대기',
    accepted: '요청 수락',
    preview_running: 'Preview 실행 중',
    preview_ready: 'Preview 완료',
    final_running: 'Final 실행 중',
    quality_review: '품질 검토 중',
    completed: '완료',
    completed_preview_only: 'Preview 전용 완료',
    failed: '실패',
};

export function stateLabel(state: FeaturePopupState): string {
    return STATE_LABELS[state] ?? state;
}

const CONNECTION_LABELS: Record<FeatureStreamConnection, string> = {
    idle: '대기',
    connecting: '연결 중',
    streaming: '스트리밍',
    completed: '완료',
    failed: '실패',
};

export function connectionLabel(connection: FeatureStreamConnection): string {
    return CONNECTION_LABELS[connection] ?? connection;
}

export function formatElapsed(seconds: number): string {
    const safe = Math.max(0, Math.round(seconds));
    if (safe < 60) {
        return `${safe}초`;
    }
    const minutes = Math.floor(safe / 60);
    const remainingSeconds = safe % 60;
    return remainingSeconds > 0 ? `${minutes}분 ${remainingSeconds}초` : `${minutes}분`;
}

const PROGRESS_WIDTH_CLASSES: Record<number, string> = {
    0: 'w-0',
    10: 'w-[10%]',
    20: 'w-[20%]',
    25: 'w-1/4',
    30: 'w-[30%]',
    33: 'w-1/3',
    40: 'w-[40%]',
    50: 'w-1/2',
    60: 'w-[60%]',
    66: 'w-2/3',
    70: 'w-[70%]',
    75: 'w-3/4',
    80: 'w-[80%]',
    90: 'w-[90%]',
    100: 'w-full',
};

export function progressWidthClass(percent: number): string {
    const clamped = Math.min(100, Math.max(0, Math.round(percent)));
    const nearest = Object.keys(PROGRESS_WIDTH_CLASSES)
        .map(Number)
        .reduce((prev, curr) => (Math.abs(curr - clamped) < Math.abs(prev - clamped) ? curr : prev), 0);
    return PROGRESS_WIDTH_CLASSES[nearest] ?? 'w-0';
}
