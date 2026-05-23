'use client';

import { ADMIN_MANUAL_ORCHESTRATOR_STEPS } from '@/lib/admin-manual-orchestrator';

interface AdminManualStepStripProps {
    selectedStepId: string;
    selectedStepCompleted: boolean;
    completedStepCount: number;
    onSelectedStepIdChange: (value: string) => void;
}

export default function AdminManualStepStrip({
    selectedStepId,
    selectedStepCompleted,
    completedStepCount,
    onSelectedStepIdChange,
}: AdminManualStepStripProps) {
    return (
        <>
            <div>
                <p className="text-sm font-semibold text-blue-900">관리자 수동 10단 버튼 라인</p>
                <p className="mt-1 text-xs text-blue-700">관리자 오케스트레이터는 고객 오케스트레이터와 같은 9단계+4.5 Refiner/Fixer 기능 축을 보되, 단계별 수동 조작과 분석 누적을 목적으로 유지합니다.</p>
                <p className="mt-2 text-xs text-blue-800">완료 단계: {completedStepCount} / {ADMIN_MANUAL_ORCHESTRATOR_STEPS.length}</p>
            </div>
            <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-9">
                {ADMIN_MANUAL_ORCHESTRATOR_STEPS.map((step) => {
                    const selected = selectedStepId === step.id;
                    const completed = selected ? selectedStepCompleted : false;
                    return (
                        <div key={step.id} className={`rounded-lg border px-3 py-3 text-left text-xs ${selected ? 'border-blue-500 bg-white text-blue-900 shadow-sm' : 'border-blue-100 bg-white text-gray-700 bg-white'}`}>
                            <button type="button" onClick={() => onSelectedStepIdChange(step.id)} className="w-full text-left">
                                <div className="flex items-center justify-between gap-2">
                                    <p className="font-semibold">{step.id}</p>
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] ${completed ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{completed ? '완료' : '대기'}</span>
                                </div>
                                <p className="mt-1">{step.label}</p>
                            </button>
                            <p className="mt-2 text-[11px] text-blue-700">{step.title}</p>
                        </div>
                    );
                })}
            </div>
        </>
    );
}
