'use client';

type OrchestratorVoiceMicButtonProps = {
    listening?: boolean;
    disabled?: boolean;
    onClick: () => void;
    compact?: boolean;
    testId?: string;
};

export default function OrchestratorVoiceMicButton({
    listening = false,
    disabled = false,
    onClick,
    compact = false,
    testId = 'orchestrator-voice-input',
}: OrchestratorVoiceMicButtonProps) {
    return (
        <button
            type="button"
            disabled={disabled}
            onClick={onClick}
            aria-pressed={listening}
            aria-label={listening ? '음성 입력 중지' : '음성 지시 시작'}
            data-testid={testId}
            className={`inline-flex items-center justify-center gap-2 rounded-xl border font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                compact ? 'px-3 py-2 text-xs' : 'px-4 py-2.5 text-sm'
            } ${
                listening
                    ? 'border-rose-500/70 bg-rose-950/40 text-rose-100 shadow-[0_0_0_1px_rgba(244,63,94,0.35)]'
                    : 'border-emerald-500/70 bg-emerald-950/30 text-emerald-100 shadow-[0_0_0_1px_rgba(16,185,129,0.25)] hover:bg-emerald-900/40'
            }`}
        >
            <span
                aria-hidden
                className={`inline-flex h-7 w-7 items-center justify-center rounded-full ${
                    listening ? 'bg-rose-500/25 text-base' : 'bg-emerald-500/20 text-base'
                }`}
            >
                🎤
            </span>
            <span>{listening ? '듣는 중… 탭하면 중지' : '음성 지시'}</span>
        </button>
    );
}
