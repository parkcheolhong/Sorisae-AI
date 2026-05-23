'use client';

import type { AdminManualStepDefinition } from '@/lib/admin-manual-orchestrator';

interface AdminManualStepHeaderProps {
    selectedStep: Pick<AdminManualStepDefinition, 'id' | 'title' | 'detail' | 'flowId' | 'stepId' | 'action'>;
}

export default function AdminManualStepHeader({ selectedStep }: AdminManualStepHeaderProps) {
    return (
        <>
            <p className="font-semibold text-gray-900">{selectedStep.id} · {selectedStep.title}</p>
            <p className="mt-1 text-xs text-gray-600">{selectedStep.detail}</p>
            <p className="mt-2 text-xs text-blue-700">preset: {selectedStep.flowId} / {selectedStep.stepId} / {selectedStep.action}</p>
        </>
    );
}
