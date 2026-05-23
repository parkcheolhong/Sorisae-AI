export function buildAdminGeneratorStatusSectionData(options: {
    activeGeneratorModal: string | null;
    generatorCapabilityStatusRows: Array<{
        id: string;
        title: string;
        state: string;
        summary: string;
        finalStage: string;
        metric: string;
    }>;
    effectiveCodeGenerationStrategy: string;
    effectivePipeline: string[];
    effectiveOrchestrationSpec: any;
    effectiveConversationAgents: {
        text: string;
        voice: string;
        question: string;
        research: string;
        action: string;
    };
    reasonerCoverageClassName: string;
    reasonerCoverageState: string;
    reasonerRequiredCoverage: number;
    requiredReasonerTargetCount: number;
    reasonerConversationCoverage: number;
}) {
    return {
        modalStatusLabel: options.activeGeneratorModal ? `${options.activeGeneratorModal} 열림` : '대기',
        generatorCapabilityStatusRows: options.generatorCapabilityStatusRows,
        effectiveCodeGenerationStrategy: options.effectiveCodeGenerationStrategy,
        effectivePipelineText: options.effectivePipeline.length > 0 ? options.effectivePipeline.join(' → ') : '실행 전 / 대기',
        specPipelineText: (options.effectiveOrchestrationSpec?.pipeline || []).join(' → ') || '-',
        effectiveConversationAgents: options.effectiveConversationAgents,
        reasonerCoverageClassName: options.reasonerCoverageClassName,
        reasonerCoverageState: options.reasonerCoverageState,
        reasonerCoverageSummary: `현재 운영 기준에서 음성과 조사 흐름은 reasoner 기본 연결입니다. 기본 커버리지는 ${options.reasonerRequiredCoverage}/${options.requiredReasonerTargetCount}, 확장 포함 전체 커버리지는 ${options.reasonerConversationCoverage}/5 입니다.`,
    };
}
