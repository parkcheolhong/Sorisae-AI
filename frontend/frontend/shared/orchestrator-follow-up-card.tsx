'use client';

import * as React from 'react';

export type SharedFollowUpRecommendation = {
    id: string;
    label: string;
    detail: string;
};

export type SharedFollowUpMetric = {
    label: string;
    value: string;
    tone?: 'neutral' | 'good' | 'warning';
};

export type SharedFollowUpScoreAxisId =
    | 'severity'
    | 'recency'
    | 'approval_risk'
    | 'hard_gate_impact'
    | 'operational_risk'
    | 'self_run_priority';

export type SharedFollowUpScoreAxis = {
    id: SharedFollowUpScoreAxisId;
    label: string;
    score: number;
    detail: string;
    tone?: 'neutral' | 'good' | 'warning';
};

export type SharedFollowUpTrendPoint = {
    label: string;
    value: number;
};

interface SharedOrchestratorFollowUpCardProps {
    tone: 'customer' | 'admin';
    title: string;
    summary: string;
    scoreLabel: string;
    scoreValue: number;
    scoreAxes?: SharedFollowUpScoreAxis[];
    recommendations: SharedFollowUpRecommendation[];
    metrics?: SharedFollowUpMetric[];
    trendPoints?: SharedFollowUpTrendPoint[];
    actionLabel?: string;
    actionBusyLabel?: string;
    actionDisabled?: boolean;
    onAction?: () => void;
}

const toneClasses = {
    customer: {
        shell: 'border-[#25304a] bg-[#0f1523]',
        accent: 'text-[#58c9ff]',
        badge: 'border-[#58c9ff] bg-[rgba(88,201,255,0.12)] text-[#9ee7ff]',
    },
    admin: {
        shell: 'border-[#30363d] bg-[#0d1117]',
        accent: 'text-[#79c0ff]',
        badge: 'border-[#1f6feb] bg-[rgba(31,111,235,0.16)] text-[#9ecbff]',
    },
} as const;

const metricToneClassName = (tone: SharedFollowUpMetric['tone']) => {
    if (tone === 'good') return 'text-[#3fb950]';
    if (tone === 'warning') return 'text-[#f2cc60]';
    return 'text-[#c9d1d9]';
};

export default function SharedOrchestratorFollowUpCard({
    tone,
    title,
    summary,
    scoreLabel,
    scoreValue,
    scoreAxes = [],
    recommendations,
    metrics = [],
    trendPoints = [],
    actionLabel,
    actionBusyLabel = '실행 중...',
    actionDisabled,
    onAction,
}: SharedOrchestratorFollowUpCardProps) {
    const palette = toneClasses[tone];
    const normalizedScore = Math.max(0, Math.min(100, Math.round(scoreValue)));
    const maxTrendValue = Math.max(1, ...trendPoints.map((point) => point.value));
    const metricTonePriority = (tone: SharedFollowUpMetric['tone']) => {
        if (tone === 'warning') return 0;
        if (tone === 'neutral') return 1;
        return 2;
    };
    const sortedMetrics = [...metrics].sort((left, right) => {
        const toneDiff = metricTonePriority(left.tone) - metricTonePriority(right.tone);
        if (toneDiff !== 0) {
            return toneDiff;
        }
        return left.label.localeCompare(right.label, 'ko');
    });
    const criticalMetrics = sortedMetrics.filter((metric) => metric.tone === 'warning');
    const supplementalMetrics = sortedMetrics.filter((metric) => metric.tone !== 'warning');
    const sortedAxes = [...scoreAxes].sort((left, right) => right.score - left.score || left.label.localeCompare(right.label, 'ko'));
    const [showSupplementalMetrics, setShowSupplementalMetrics] = React.useState(false);
    return (
        <div className={`rounded-[24px] border p-5 ${palette.shell}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className={`text-sm font-semibold uppercase tracking-[0.18em] ${palette.accent}`}>{title}</p>
                    <p className="mt-2 text-sm text-[#c9d1d9]">{summary}</p>
                </div>
                <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${palette.badge}`}>
                    {scoreLabel} {normalizedScore}점
                </div>
            </div>
            {sortedAxes.length > 0 && (
                <div className="mt-4 rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3">
                    <div className="mb-3 flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-[#e6edf3]">공통 score axis</p>
                        <span className="text-[11px] text-[#8b949e]">severity / recency / approval / hard gate / operational / self-run</span>
                    </div>
                    <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                        {sortedAxes.map((axis) => (
                            <div key={axis.id} className="rounded-xl border border-[#30363d] bg-[#0b0f14] px-3 py-3">
                                <div className="flex items-center justify-between gap-2">
                                    <p className="text-[11px] text-[#8b949e]">{axis.label}</p>
                                    <span className={`text-sm font-semibold ${metricToneClassName(axis.tone)}`}>{Math.max(0, Math.min(100, Math.round(axis.score)))}점</span>
                                </div>
                                <p className="mt-1 text-xs text-[#c9d1d9] whitespace-pre-wrap">{axis.detail}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            {sortedMetrics.length > 0 && (
                <div className="mt-4 space-y-3">
                    <div>
                        <div className="mb-2 flex items-center justify-between gap-3">
                            <p className="text-xs font-semibold text-[#e6edf3]">핵심 경고</p>
                            <span className="text-[11px] text-[#8b949e]">{criticalMetrics.length}건</span>
                        </div>
                        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                            {(criticalMetrics.length > 0 ? criticalMetrics : sortedMetrics.slice(0, 4)).map((metric) => (
                                <div key={`${metric.label}-${metric.value}`} className="rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3">
                                    <p className="text-[11px] text-[#8b949e]">{metric.label}</p>
                                    <p className={`mt-1 text-sm font-semibold ${metricToneClassName(metric.tone)}`}>{metric.value}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                    {supplementalMetrics.length > 0 && (
                        <div>
                            <div className="mb-2 flex items-center justify-between gap-3">
                                <p className="text-xs font-semibold text-[#e6edf3]">기타 지표</p>
                                <button
                                    type="button"
                                    onClick={() => setShowSupplementalMetrics((previous) => !previous)}
                                    className="rounded-lg border border-[#30363d] bg-[#11161d] px-3 py-1 text-[11px] font-semibold text-[#c9d1d9]"
                                >
                                    {showSupplementalMetrics ? '접기' : '펼치기'}
                                </button>
                            </div>
                            {showSupplementalMetrics && (
                                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                                    {supplementalMetrics.map((metric) => (
                                        <div key={`${metric.label}-${metric.value}`} className="rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3">
                                            <p className="text-[11px] text-[#8b949e]">{metric.label}</p>
                                            <p className={`mt-1 text-sm font-semibold ${metricToneClassName(metric.tone)}`}>{metric.value}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
            {trendPoints.length > 0 && (
                <div className="mt-4 rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3">
                    <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-[#e6edf3]">before/after 추세 그래프</p>
                        <p className="text-[11px] text-[#8b949e]">누적 모델 고도화 전까지 실시간 비교 추세를 표시합니다.</p>
                    </div>
                    <div className="mt-3 flex items-end gap-3">
                        {trendPoints.map((point) => (
                            <div key={`${point.label}-${point.value}`} className="flex-1 text-center">
                                <div className="flex h-24 items-end justify-center rounded-lg border border-[#30363d] bg-[#0b0f14] px-2 py-2">
                                    <div
                                        className="w-full rounded-t-md bg-[#58a6ff]"
                                        style={{ height: `${Math.max(8, Math.round((point.value / maxTrendValue) * 88))}%` }}
                                    />
                                </div>
                                <p className="mt-2 text-[11px] text-[#8b949e]">{point.label}</p>
                                <p className="text-xs font-semibold text-[#e6edf3]">{point.value}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            <div className="mt-4 space-y-2">
                {recommendations.length > 0 ? recommendations.map((item) => (
                    <div key={item.id} className="rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3">
                        <p className="text-xs font-semibold text-[#e6edf3]">{item.label}</p>
                        <p className="mt-1 text-xs text-[#c9d1d9] whitespace-pre-wrap">{item.detail}</p>
                    </div>
                )) : (
                    <div className="rounded-xl border border-[#30363d] bg-[#11161d] px-3 py-3 text-xs text-[#8b949e]">
                        후속 제안이 아직 없습니다.
                    </div>
                )}
            </div>
            {onAction && actionLabel && (
                <div className="mt-4">
                    <button
                        type="button"
                        onClick={onAction}
                        disabled={Boolean(actionDisabled)}
                        className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${actionDisabled ? 'bg-[#21262d]' : 'bg-[#238636]'}`}
                    >
                        {actionDisabled ? actionBusyLabel : actionLabel}
                    </button>
                </div>
            )}
        </div>
    );
}
