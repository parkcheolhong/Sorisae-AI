'use client';

import * as React from 'react';

import OrchestratorStageCardPanel from '@shared/orchestrator-stage-card-panel';
import AdminManualOrchestratorLinks from '@/components/admin/admin-manual-orchestrator-links';
import AdminManualPrinciples from '@/components/admin/admin-manual-principles';
import AdminManualSectionIdMap from '@/components/admin/admin-manual-section-id-map';
import AdminManualStepDetailCard from '@/components/admin/admin-manual-step-detail-card';
import AdminManualStepStrip from '@/components/admin/admin-manual-step-strip';
import { buildAdminManualOrchestratorSectionSlices } from '@/components/admin/admin-manual-orchestrator-section-slices';
import AdminAdProductionPanel from '@/components/admin/admin-ad-production-panel';
import type {
    AdminManualOrchestratorProductionPanelProps,
    AdminManualOrchestratorStageCardProps,
} from '@/components/admin/admin-manual-orchestrator-types';
import type { AdminManualOrchestratorWorkflowProps } from '@/components/admin/admin-manual-workflow-types';

export interface AdminManualOrchestratorSectionProps {
    stageCard: AdminManualOrchestratorStageCardProps;
    workflow: AdminManualOrchestratorWorkflowProps;
    productionPanel: AdminManualOrchestratorProductionPanelProps;
}

export default function AdminManualOrchestratorSection({ stageCard, workflow, productionPanel }: AdminManualOrchestratorSectionProps) {
    const sectionSlices = buildAdminManualOrchestratorSectionSlices(workflow, productionPanel);

    return (
        <>
            <OrchestratorStageCardPanel
                tone="admin"
                title="관리자 공용 단계 카드 오케스트레이터"
                description="고객 오케스트레이터와 동일한 공용 StageCardPanel을 관리자 화면에도 고정 연결했습니다. ARCH-0045 Refiner/Fixer와 운영 stage run 상태를 같은 카드 구조로 봅니다."
                stageRun={stageCard.stageRun}
                stageNoteDraft={stageCard.stageNoteDraft}
                onStageNoteDraftChange={stageCard.onStageNoteDraftChange}
                substepChecks={stageCard.stageSubstepChecks}
                onSubstepChecksChange={stageCard.onStageSubstepChecksChange}
                revisionNote={stageCard.stageRevisionNote}
                onRevisionNoteChange={stageCard.onStageRevisionNoteChange}
                stageUpdateLoading={stageCard.stageUpdateLoading}
                onMarkPassed={() => stageCard.onUpdateStageStatus('passed')}
                onMarkManualCorrection={() => stageCard.onUpdateStageStatus('manual_correction')}
                onMarkFailed={() => stageCard.onUpdateStageStatus('failed')}
                onRefresh={stageCard.onRefreshStageRun}
                ideaPresets={[
                    '핵심엔진 직후 구조 정리 규칙을 추가',
                    'Refiner/Fixer에서 import/계약 누락을 먼저 보정',
                    '운영 API 실검증 결과를 다음 카드 진입 조건으로 고정',
                ]}
                onApplyIdeaPreset={(preset) => stageCard.onStageRevisionNoteChange([stageCard.stageRevisionNote, preset].filter(Boolean).join('\n'))}
                onRunOperationalVerification={stageCard.onRefreshStageRun}
                operationalVerificationLabel="관리자 stage run + 운영 API 새로고침"
                commandRules={[
                    '관리자 화면도 공용 카드 패널 기준으로 /pass /fix /fail /verify 명령 체계를 유지합니다.',
                    'ARCH-0045 Refiner/Fixer는 로직 전 구조 정리/계약 보정/자동 수정 안전고리 단계로 고정합니다.',
                    '관리자 협업 대화는 /ask /search /news /revise /resume 명령으로 중간 설계 변경과 조사 대화를 같이 진행합니다.',
                    'stage run 상태와 수동 메모를 같이 기록해 관리자/고객 추적을 동일 구조로 맞춥니다.',
                ]}
            />
            <AdminManualOrchestratorLinks />
            <div className="mb-4 space-y-3 rounded-xl border border-blue-100 bg-blue-50 p-4">
                <AdminManualStepStrip {...sectionSlices.stepStrip} />
                <AdminManualStepDetailCard workflow={workflow} />
                <AdminManualSectionIdMap {...sectionSlices.sectionIdMap} />
                <AdminAdProductionPanel {...sectionSlices.productionPanel} />
            </div>
            <AdminManualPrinciples />
        </>
    );
}
