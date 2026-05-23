'use client';

import { ADMIN_MANUAL_SECTION_ID_MAP } from '@/lib/admin-manual-orchestrator';

interface AdminManualSectionIdMapProps {
    selectedStepId: string;
}

export default function AdminManualSectionIdMap({ selectedStepId }: AdminManualSectionIdMapProps) {
    return (
        <div className="rounded-lg border border-blue-100 bg-white px-4 py-3 text-sm text-gray-700">
            <div className="flex items-center justify-between gap-3">
                <p className="font-semibold text-gray-900">섹션별 ID 조립 맵</p>
                <span className="text-[11px] text-gray-500">[Flow ID] + [Step ID] + [Action]</span>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                {ADMIN_MANUAL_SECTION_ID_MAP.map((section) => {
                    const active = section.architectureId === selectedStepId;
                    return (
                        <div key={section.sectionId} className={`space-y-1 rounded-lg border px-3 py-3 text-xs ${active ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-gray-50'}`}>
                            <p className="font-semibold text-gray-900">{section.sectionId} · {section.title}</p>
                            <p>arch/flow/step: {section.architectureId} / {section.flowId} / {section.stepId}</p>
                            <p>action: {section.action}</p>
                            <p>features: {section.featureSummary}</p>
                            <p className="break-all">assembly IDs: {section.assemblyIds.join(', ')}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
