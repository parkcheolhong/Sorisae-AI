import type { AdvisoryNextAction, SuggestedSelfRunPreview } from '@/lib/use-orchestrator-chat';
import type { SelfPrepareMode, SelfRunDirectiveScope, SelfRunDirectiveTemplate } from '@/lib/use-admin-self-run';

export const SELF_RUN_MODE_LABELS: Record<SelfPrepareMode, string> = {
    'self-diagnosis': '자가진단',
    'self-improvement': '자가개선',
    'self-expansion': '자가확장',
};

export const SELF_RUN_MODE_EXECUTION_MODE: Record<SelfPrepareMode, string> = {
    'self-diagnosis': 'review',
    'self-improvement': 'full',
    'self-expansion': 'full',
};

export const SELF_RUN_MODE_PIPELINES: Record<SelfPrepareMode, string[]> = {
    'self-diagnosis': ['reviewer'],
    'self-improvement': ['planner', 'coder', 'reviewer'],
    'self-expansion': ['planner', 'coder', 'reviewer'],
};

export const SELF_RUN_DIRECTIVE_TEMPLATES: Array<{
    value: SelfRunDirectiveTemplate;
    label: string;
    description: string;
    category: string;
    estimateBiasMinutes: number;
    resourceHint: string;
    recommendedMode: SelfPrepareMode;
    recommendedScope: SelfRunDirectiveScope;
}> = [
    { value: '', label: '기본 프리셋만 사용', description: '추가 주문 없이 현재 자가실행 프리셋만 적용합니다.', category: '기본', estimateBiasMinutes: 0, resourceHint: 'VRAM 낮음 / CPU 낮음', recommendedMode: 'self-diagnosis', recommendedScope: 'preset_default' },
    { value: 'debug_remediation_loop', label: '디버깅 기반 결함 교정', description: '결함 식별, 시스템 이해, 리스크 관리, 성능 최적화를 순차 적용해 corrective command로 되돌립니다.', category: '운영', estimateBiasMinutes: 9, resourceHint: 'VRAM 중간 / CPU 중간', recommendedMode: 'self-improvement', recommendedScope: 'targeted_implementation' },
    { value: 'video_ad_clarity', label: '영상 선명도', description: '해상감, 선명도, 디테일 개선 중심', category: '영상광고', estimateBiasMinutes: 6, resourceHint: 'VRAM 중간 / CPU 낮음', recommendedMode: 'self-improvement', recommendedScope: 'targeted_implementation' },
    { value: 'video_ad_conversion', label: '전환율 개선', description: '카피, CTA, 구매 흐름 개선 중심', category: '영상광고', estimateBiasMinutes: 8, resourceHint: 'VRAM 낮음 / CPU 중간', recommendedMode: 'self-expansion', recommendedScope: 'feature_expansion' },
    { value: 'video_ad_speed_optimization', label: '속도 최적화', description: '생성 시간과 병목 구간 단축 중심', category: '영상광고', estimateBiasMinutes: 4, resourceHint: 'VRAM 낮음 / CPU 낮음', recommendedMode: 'self-diagnosis', recommendedScope: 'diagnosis_only' },
    { value: 'video_ad_storytelling', label: '스토리텔링 강화', description: '훅, 장면 연결, 몰입감 강화 중심', category: '영상광고', estimateBiasMinutes: 7, resourceHint: 'VRAM 중간 / CPU 중간', recommendedMode: 'self-expansion', recommendedScope: 'feature_expansion' },
    { value: 'video_ad_quality_upgrade', label: '영상광고 품질 고도화', description: '선명도, 장면 완성도, 전달력 향상 중심', category: '영상광고', estimateBiasMinutes: 10, resourceHint: 'VRAM 중간~높음 / CPU 중간', recommendedMode: 'self-improvement', recommendedScope: 'modernization' },
    { value: 'video_ad_new_tech', label: '영상광고 신기술 도입', description: '생성형/렌더링/후처리 최신 기술 도입안 중심', category: '영상광고', estimateBiasMinutes: 12, resourceHint: 'VRAM 높음 / CPU 중간', recommendedMode: 'self-expansion', recommendedScope: 'modernization' },
    { value: 'admin_ops_efficiency', label: '관리자 운영 효율화', description: '반복 작업 절감, 운영 시간 단축 중심', category: '운영', estimateBiasMinutes: 5, resourceHint: 'VRAM 낮음 / CPU 낮음', recommendedMode: 'self-diagnosis', recommendedScope: 'diagnosis_only' },
    { value: 'marketplace_conversion', label: '마켓플레이스 전환 개선', description: '구매 흐름, 노출, 전환율 개선 중심', category: '서비스', estimateBiasMinutes: 8, resourceHint: 'VRAM 낮음 / CPU 중간', recommendedMode: 'self-expansion', recommendedScope: 'feature_expansion' },
    { value: 'llm_cost_latency', label: 'LLM 비용/지연 최적화', description: '응답 속도와 자원 점유 절감 중심', category: 'LLM', estimateBiasMinutes: 6, resourceHint: 'VRAM 낮음 / CPU 낮음', recommendedMode: 'self-diagnosis', recommendedScope: 'diagnosis_only' },
    { value: 'tower_crane_expansion', label: 'Tower Crane 확장 실험', description: 'capability 진단 + A/B/C 옵션 + 웹 리서치 기반 self-expansion full 실험', category: '운영', estimateBiasMinutes: 15, resourceHint: 'VRAM 중간~높음 / CPU 중간', recommendedMode: 'self-expansion', recommendedScope: 'feature_expansion' },
];

export const SELF_RUN_DIRECTIVE_SCOPES: Array<{ value: SelfRunDirectiveScope; label: string; description: string }> = [
    { value: 'preset_default', label: '프리셋 권장 범위', description: '현재 self-run 목적을 유지한 채 주문을 반영합니다.' },
    { value: 'diagnosis_only', label: '진단/설계 중심', description: '구현보다 분석과 설계안 정리에 집중합니다.' },
    { value: 'targeted_implementation', label: '지정 범위만 구현', description: '주문과 직접 관련된 부분만 좁게 수정합니다.' },
    { value: 'feature_expansion', label: '기능 확장 우선', description: '기존 개선과 신규 확장을 함께 다룹니다.' },
    { value: 'modernization', label: '구조 개선 포함', description: '필요하면 구조 재정리나 기술 교체안까지 포함합니다.' },
];

export const SELF_RUN_DIRECTIVE_EXAMPLES = [
    '영상광고 기능을 더 선명하게 만들고 최신 생성형 영상 후처리 기술 도입안을 같이 검토',
    '영상광고 주문 흐름은 유지하되 결과물 품질만 집중 개선',
    '관리자 자가진단 시간을 줄이도록 진단 범위만 최소화하고 병목 보고서 중심으로 정리',
];

export const getSelfRunDirectiveTemplateOption = (value?: string) => (
    SELF_RUN_DIRECTIVE_TEMPLATES.find((option) => option.value === (value || ''))
    || SELF_RUN_DIRECTIVE_TEMPLATES[0]
);

export const getSelfRunDirectiveScopeOption = (value?: string) => (
    SELF_RUN_DIRECTIVE_SCOPES.find((option) => option.value === value)
    || SELF_RUN_DIRECTIVE_SCOPES[0]
);

const formatMinuteRange = (minMinutes: number, maxMinutes: number) => (
    `약 ${Math.max(3, minMinutes)}-${Math.max(Math.max(3, minMinutes), maxMinutes)}분`
);

export const estimateSelfRunDuration = (
    requestedMode: SelfPrepareMode,
    directiveScope: SelfRunDirectiveScope,
    directiveTemplate: SelfRunDirectiveTemplate,
) => {
    const baseRanges: Record<SelfPrepareMode, [number, number]> = {
        'self-diagnosis': [8, 20],
        'self-improvement': [20, 45],
        'self-expansion': [10, 28],
    };
    const scopeAdjustments: Record<SelfRunDirectiveScope, [number, number]> = {
        preset_default: [0, 0],
        diagnosis_only: [-3, -6],
        targeted_implementation: [4, 8],
        feature_expansion: [6, 12],
        modernization: [8, 14],
    };
    const [baseMin, baseMax] = baseRanges[requestedMode];
    const [scopeMin, scopeMax] = scopeAdjustments[directiveScope];
    const templateBias = getSelfRunDirectiveTemplateOption(directiveTemplate).estimateBiasMinutes;
    return formatMinuteRange(baseMin + scopeMin + Math.floor(templateBias / 2), baseMax + scopeMax + templateBias);
};

export const buildSelfRunPreview = (
    requestedMode: SelfPrepareMode,
    directiveScope: SelfRunDirectiveScope,
    directiveTemplate: SelfRunDirectiveTemplate,
) => {
    const templateOption = getSelfRunDirectiveTemplateOption(directiveTemplate);
    const scopeOption = getSelfRunDirectiveScopeOption(directiveScope);
    return {
        title: SELF_RUN_MODE_LABELS[requestedMode],
        executionMode: SELF_RUN_MODE_EXECUTION_MODE[requestedMode],
        estimatedDuration: estimateSelfRunDuration(requestedMode, directiveScope, directiveTemplate),
        pipeline: SELF_RUN_MODE_PIPELINES[requestedMode],
        resourceHint: templateOption.resourceHint,
        recommendedMode: SELF_RUN_MODE_LABELS[templateOption.recommendedMode],
        recommendedScope: getSelfRunDirectiveScopeOption(templateOption.recommendedScope).label,
        note: `${templateOption.label} · ${scopeOption.label}`,
    };
};

export interface SelfRunComparisonResultLike {
    requested_mode?: string;
    execution_mode?: string;
    directive_template?: string;
    directive_scope?: string;
    directive_request?: string;
    status: string;
    executed_task?: string;
    diff_summary: {
        added_files: string[];
        modified_files: string[];
        deleted_files: string[];
        total_changed_files: number;
    };
    orchestration_result?: {
        mode?: string;
        pipeline?: string[];
    } | null;
}

export const buildSelfRunComparisonRows = (result: SelfRunComparisonResultLike) => {
    const templateOption = getSelfRunDirectiveTemplateOption(result.directive_template);
    const scopeOption = getSelfRunDirectiveScopeOption(result.directive_scope);
    const actualPipeline = result.orchestration_result?.pipeline?.length
        ? result.orchestration_result.pipeline.join(' -> ')
        : '-';
    const requestedPipeline = (['self-diagnosis', 'self-improvement', 'self-expansion'] as SelfPrepareMode[])
        .includes((result.requested_mode || '') as SelfPrepareMode)
        ? SELF_RUN_MODE_PIPELINES[result.requested_mode as SelfPrepareMode].join(' -> ')
        : '-';
    const promptReflected = result.directive_request
        ? (result.executed_task || '').includes(result.directive_request)
        : false;

    return [
        {
            label: '실행 경로',
            requested: `${result.requested_mode || '-'} / ${result.execution_mode || '-'}`,
            actual: `${result.orchestration_result?.mode || result.execution_mode || '-'} / ${actualPipeline}`,
            note: `예상 파이프라인: ${requestedPipeline}`,
        },
        {
            label: '주문 템플릿',
            requested: templateOption.label,
            actual: result.directive_template || '기본 프리셋만 사용',
            note: templateOption.description,
        },
        {
            label: '실행 범위',
            requested: scopeOption.label,
            actual: actualPipeline,
            note: scopeOption.description,
        },
        {
            label: '자유 주문 반영',
            requested: result.directive_request || '-',
            actual: promptReflected ? '실행 프롬프트에 반영됨' : '직접 주문 없음 또는 미검출',
            note: promptReflected ? 'executed_task 내부 주문 문장 확인' : '결과 리포트와 변경 파일을 함께 확인 필요',
        },
        {
            label: '산출물 변화',
            requested: '주문 목표에 맞는 변경/계획 생성',
            actual: `${result.diff_summary.total_changed_files}개 파일 변화, 상태 ${result.status}`,
            note: `추가 ${result.diff_summary.added_files.length} / 수정 ${result.diff_summary.modified_files.length} / 삭제 ${result.diff_summary.deleted_files.length}`,
        },
    ];
};

export const resolveSelfRunDirectiveScopeForActionType = (actionType: string): SelfRunDirectiveScope => (
    actionType === 'self-improvement' ? 'targeted_implementation' : 'feature_expansion'
);

export const resolveGeneratorSelfRunDirectiveScope = (presetId: SelfPrepareMode): SelfRunDirectiveScope => (
    presetId === 'self-expansion' ? 'feature_expansion' : 'targeted_implementation'
);

export const buildSuggestedSelfRunPreview = (options: {
    action: AdvisoryNextAction;
    directiveTemplate: SelfRunDirectiveTemplate;
    directiveRequest: string;
}): SuggestedSelfRunPreview => ({
    action: options.action,
    requestedMode: options.action.action_type === 'self-improvement' ? 'self-improvement' : 'self-expansion',
    directiveTemplate: options.directiveTemplate,
    directiveScope: resolveSelfRunDirectiveScopeForActionType(options.action.action_type),
    directiveRequest: options.directiveRequest,
});
