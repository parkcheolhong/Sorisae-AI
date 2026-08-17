'use client';

import AdminManualActionsBlock from '@/components/admin/admin-manual-actions-block';
import AdminManualExternalStageStatus from '@/components/admin/admin-manual-external-stage-status';
import AdminManualMetaBlock from '@/components/admin/admin-manual-meta-block';
import AdminManualNotesBlock from '@/components/admin/admin-manual-notes-block';
import AdminManualRouteStageBlock from '@/components/admin/admin-manual-route-stage-block';
import AdminManualStepHeader from '@/components/admin/admin-manual-step-header';
import { buildAdminManualStepDetailSlices } from '@/components/admin/admin-manual-step-detail-slices';
import type {
    AdminManualOrchestratorWorkflowProps,
} from '@/components/admin/admin-manual-workflow-types';

interface AdminManualStepDetailCardProps {
    workflow: AdminManualOrchestratorWorkflowProps;
}

export default function AdminManualStepDetailCard({ workflow }: AdminManualStepDetailCardProps) {
    const { statusSlices, workflowSlices } = buildAdminManualStepDetailSlices(workflow);

    return (
        <div className="rounded-lg border border-blue-100 bg-white px-4 py-3 text-sm text-gray-700">
            <div>
                <AdminManualStepHeader selectedStep={statusSlices.header.selectedStep} />
                <AdminManualExternalStageStatus externalStage={statusSlices.externalStage} />
                <div className="mt-4 space-y-3">
                    <AdminManualRouteStageBlock routeStage={workflowSlices.routeStage} />
                    <AdminManualMetaBlock meta={workflowSlices.meta} />
                    <AdminManualActionsBlock actions={workflowSlices.actions} />
                    <AdminManualNotesBlock notes={workflowSlices.notes} />
                </div>
                <div className="mt-3">
                    <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-3 text-xs text-blue-800">이 단계는 관리자 오케스트레이터 내부에서 수동 점검, 메모, 완료 관리로 운영되며 고객 오케스트레이터와 같은 기능 축을 참고합니다.</div>
                </div>
            </div>
        </div>
    );
}
