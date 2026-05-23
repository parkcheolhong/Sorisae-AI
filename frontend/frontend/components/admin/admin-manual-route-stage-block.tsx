'use client';

import { ADMIN_ROUTER_STAGE_LABELS, type AdminDurationDays, type AdminRouterStage } from '@/lib/admin-manual-orchestrator';
import type { AdminManualRouteStageBlockSlice } from '@/components/admin/admin-manual-orchestrator-types';

interface AdminManualRouteStageBlockProps {
    routeStage: AdminManualRouteStageBlockSlice;
}

export default function AdminManualRouteStageBlock({ routeStage }: AdminManualRouteStageBlockProps) {
    return (
        <div className="space-y-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold text-blue-900">관리자 전용 1~6단 라우터 상태머신</p>
                    <p className="mt-1 text-[11px] text-blue-700">현재 단계와 다음 단계를 수동으로 이동하고 상태를 명시적으로 전환합니다.</p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                    <button type="button" onClick={() => routeStage.onMoveStep('prev')} disabled={!routeStage.previousStep} className="rounded-md border border-blue-200 bg-white px-2 py-1 text-blue-800 disabled:opacity-40">이전 단계</button>
                    <button type="button" onClick={() => routeStage.onMoveStep('next')} disabled={!routeStage.nextStep} className="rounded-md border border-blue-200 bg-white px-2 py-1 text-blue-800 disabled:opacity-40">다음 단계</button>
                </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-md border border-blue-100 bg-white px-3 py-3">
                    <p className="text-xs text-gray-500">현재 라우터 상태</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {(Object.keys(ADMIN_ROUTER_STAGE_LABELS) as AdminRouterStage[]).map((stage) => {
                            const active = routeStage.selectedStepState.routeStage === stage;
                            return (
                                <button key={stage} type="button" onClick={() => routeStage.onUpdateRouteStage(routeStage.selectedStepId, stage)} className={`rounded-md border px-2 py-1 text-[11px] ${active ? 'border-blue-500 bg-blue-600 text-white' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'}`}>
                                    {ADMIN_ROUTER_STAGE_LABELS[stage]}
                                </button>
                            );
                        })}
                    </div>
                </div>
                <div className="rounded-md border border-blue-100 bg-white px-3 py-3">
                    <p className="text-xs text-gray-500">작업 기간 추적</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {(['1일', '3일', '10일'] as AdminDurationDays[]).map((duration) => (
                            <button key={duration} type="button" onClick={() => routeStage.onUpdateDuration(routeStage.selectedStepId, duration)} className={`rounded-md border px-2 py-1 text-[11px] ${routeStage.selectedStepState.durationDays === duration ? 'border-violet-500 bg-violet-600 text-white' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'}`}>
                                {duration}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
