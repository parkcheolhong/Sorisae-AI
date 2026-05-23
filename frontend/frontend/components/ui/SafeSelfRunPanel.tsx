'use client';

import React from 'react';

interface SafeSelfRunPanelProps {
    selfRunStage: string;
    activeSelfRunStageMeta: {
        label: string;
        badgeClassName: string;
        selectedButtonClassName: string;
        buttonClassName: string;
        detailClassName: string;
        panelClassName: string;
        helperTitle: string;
        helperDescription: string;
    };
    selfRunStageOptions: Array<{ value: string; label: string; description: string }>;
    continueInPlace: boolean;
    onSelectStage: (stage: string) => void;
    onToggleContinueInPlace: (value: boolean) => void;
    getSelfRunStageMeta: (stage?: string) => {
        selectedButtonClassName: string;
        buttonClassName: string;
        detailClassName: string;
    };
}

export default function SafeSelfRunPanel({
    selfRunStage,
    activeSelfRunStageMeta,
    selfRunStageOptions,
    continueInPlace,
    onSelectStage,
    onToggleContinueInPlace,
    getSelfRunStageMeta,
}: SafeSelfRunPanelProps) {
    return (
        <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
            <div className="mb-3">
                <label className="mb-1.5 block text-xs text-[#8b949e]">실행 제어</label>
                <div className="rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-3">
                    <p className="text-sm text-[#8b949e]">
                        self-run 단계는 여기서 직접 고를 수 있고, 아래 통합 챗봇 통로에서 수동/반자동 실험 요청으로 이어집니다.
                    </p>
                    <p className="mt-2 text-xs text-[#e3b341]">
                        내부 승인과 반영 완료는 1차 검증 상태이며, 최종 통과는 사용자가 오케스트레이터에서 직접 실험 후 인정합니다.
                    </p>
                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                                <p className="text-xs font-semibold text-[#79c0ff]">self-run 단계 선택</p>
                                <p className="mt-1 text-[11px] text-[#8b949e]">버튼 색상으로 단계 성격을 구분합니다. 특히 `regression-check`는 기존 개선 후 회귀 여부만 따로 확인할 때 사용합니다.</p>
                            </div>
                            <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${activeSelfRunStageMeta.badgeClassName}`}>
                                현재 {activeSelfRunStageMeta.label}
                            </span>
                        </div>
                        <div className="mt-3 grid gap-2 md:grid-cols-3">
                            {selfRunStageOptions.map((option) => {
                                const selected = selfRunStage === option.value;
                                const optionMeta = getSelfRunStageMeta(option.value);
                                const optionLabel = option.value === 'regression-check' && selected
                                    ? '회귀 확인 집중'
                                    : option.label;
                                const optionDescription = option.value === 'regression-check' && selected
                                    ? '이전 개선이 다시 깨졌는지 바로 재검증합니다.'
                                    : option.description;
                                return (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => onSelectStage(option.value)}
                                        className={`rounded-lg border px-3 py-3 text-left transition-colors ${selected ? optionMeta.selectedButtonClassName : optionMeta.buttonClassName}`}
                                    >
                                        <div className="text-sm font-semibold">{optionLabel}</div>
                                        <p className={`mt-1 text-[11px] ${selected ? optionMeta.detailClassName : 'text-[#8b949e]'}`}>{optionDescription}</p>
                                    </button>
                                );
                            })}
                        </div>
                        <div className={`mt-3 rounded-lg border p-3 ${activeSelfRunStageMeta.panelClassName}`}>
                            <p className="text-xs font-semibold text-[#e6edf3]">{activeSelfRunStageMeta.helperTitle}</p>
                            <p className={`mt-1 text-[11px] ${activeSelfRunStageMeta.detailClassName}`}>{activeSelfRunStageMeta.helperDescription}</p>
                        </div>
                    </div>
                    <label className="mt-3 flex items-center gap-2 text-xs text-[#e6edf3]">
                        <input
                            type="checkbox"
                            checked={continueInPlace}
                            onChange={(e) => onToggleContinueInPlace(e.target.checked)}
                        />
                        현재 작업 폴더 계속 사용
                    </label>
                </div>
            </div>
        </div>
    );
}
