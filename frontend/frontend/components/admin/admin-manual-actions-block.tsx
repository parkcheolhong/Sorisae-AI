'use client';

import type { AdminManualActionsBlockSlice } from '@/components/admin/admin-manual-orchestrator-types';

interface AdminManualActionsBlockProps {
    actions: AdminManualActionsBlockSlice;
}

export default function AdminManualActionsBlock({ actions }: AdminManualActionsBlockProps) {
    return (
        <div>
            <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs font-semibold text-gray-700">수동 작업 버튼</p>
                <div className="flex flex-wrap gap-2 text-xs">
                    <button type="button" onClick={() => actions.onOpenAdminLlmBridge(actions.selectedStep, actions.selectedStepState)} className="rounded-md border border-indigo-300 bg-indigo-600 px-3 py-2 font-semibold text-white hover:bg-indigo-700">관리자 LLM로 실행</button>
                    <button
                        type="button"
                        onClick={() => actions.latestDedicatedOrder && actions.onOpenMarketplaceBridge(actions.latestDedicatedOrder, {
                            architectureId: actions.selectedStep.id,
                            flowId: actions.selectedStep.flowId,
                            stepId: actions.selectedStep.stepId,
                            action: actions.selectedStep.action,
                            bridgeNote: actions.selectedStepState.note || actions.selectedStep.detail,
                        })}
                        disabled={!actions.latestDedicatedOrder}
                        className={`rounded-md border px-3 py-2 font-semibold ${actions.latestDedicatedOrder ? 'border-sky-300 bg-sky-600 text-white hover:bg-sky-700' : 'border-gray-200 bg-gray-100 text-gray-400'}`}
                    >
                        마켓플레이스로 실행
                    </button>
                </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
                {actions.selectedStep.manualActions.map((manualAction) => {
                    const active = actions.selectedStepState.doneActionIds.includes(manualAction.id);
                    return (
                        <button key={manualAction.id} type="button" onClick={() => actions.onToggleManualAction(actions.selectedStep.id, manualAction.id)} className={`rounded-lg border px-3 py-2 text-xs ${active ? 'border-blue-500 bg-blue-50 text-blue-800' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'}`} title={manualAction.detail}>
                            {active ? '완료됨' : '실행 전'} · {manualAction.label}
                        </button>
                    );
                })}
            </div>
            <div className="mt-2 space-y-1 text-xs text-gray-600">
                {actions.selectedStep.manualActions.map((manualAction) => (
                    <p key={manualAction.id}>- {manualAction.label}: {manualAction.detail}</p>
                ))}
                <p className="pt-1 text-[11px] text-gray-500">선택된 trace `{actions.selectedStep.flowId} / {actions.selectedStep.stepId} / {actions.selectedStep.action}` 를 그대로 대상 오케스트레이터로 전달합니다.</p>
                {!actions.latestDedicatedOrder && <p className="text-[11px] text-amber-600">전용 광고 주문이 아직 없어 마켓플레이스 실행은 비활성화됩니다.</p>}
            </div>
        </div>
    );
}
