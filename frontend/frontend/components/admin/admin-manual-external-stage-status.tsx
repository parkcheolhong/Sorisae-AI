'use client';

import type { AdminManualExternalStageStatusSlice } from '@/components/admin/admin-manual-orchestrator-types';

interface AdminManualExternalStageStatusProps {
    externalStage: AdminManualExternalStageStatusSlice;
}

export default function AdminManualExternalStageStatus({ externalStage }: AdminManualExternalStageStatusProps) {
    if (externalStage.selectedStepId !== 'ARCH-0045' || !externalStage.selectedStepState.externalStageRunId) {
        return null;
    }

    return (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-xs text-emerald-900">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">운영 Refiner/Fixer 카드 상태</p>
                <span className={`rounded-full px-2 py-0.5 ${externalStage.selectedStepState.externalStageStatus === 'passed' ? 'bg-emerald-100 text-emerald-700' : externalStage.selectedStepState.externalStageStatus === 'failed' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>
                    {externalStage.selectedStepState.externalStageStatus || 'pending'}
                </span>
            </div>
            <p className="mt-2 text-[11px] text-emerald-800">{externalStage.selectedStepState.externalStageLabel || '4.5단계'} · {externalStage.selectedStepState.externalStageTitle || 'Refiner/Fixer'}</p>
            <p className="mt-1 text-[11px] text-emerald-700">{externalStage.selectedStepState.externalStageSummary || '핵심엔진 직후 로직 전에 구조 정리, 계약 보정, 자동 수정 안전고리를 점검합니다.'}</p>
            <p className="mt-2 break-all text-[11px] text-emerald-700">run_id: {externalStage.selectedStepState.externalStageRunId}</p>
            {externalStage.selectedStepState.externalStageUpdatedAt && (
                <p className="mt-1 text-[11px] text-emerald-700">최근 동기화: {new Date(externalStage.selectedStepState.externalStageUpdatedAt).toLocaleString('ko-KR', { hour12: false })}</p>
            )}
        </div>
    );
}
