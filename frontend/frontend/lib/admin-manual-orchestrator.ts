export type AdminRouterStage = 'queued' | 'active' | 'review' | 'blocked' | 'completed';
export type AdminDurationDays = '1일' | '3일' | '10일';

export type AdminManualAction = {
    id: string;
    label: string;
    detail: string;
};

export type AdminManualStepState = {
    completed: boolean;
    note: string;
    doneActionIds: string[];
    routeStage: AdminRouterStage;
    durationDays: AdminDurationDays;
    attachmentLinks: string[];
    attachmentDraft: string;
    referenceUrl: string;
    startedAt: string;
    endedAt: string;
    updatedAt?: string;
    externalStageRunId?: string;
    externalStageStatus?: string;
    externalStageLabel?: string;
    externalStageTitle?: string;
    externalStageSummary?: string;
    externalStageUpdatedAt?: string;
};

export type AdminManualMeta = {
    domain: string;
    hostingLine: string;
};

export type AdminManualStepDefinition = {
    id: string;
    label: string;
    title: string;
    detail: string;
    flowId: string;
    stepId: string;
    action: string;
    mode: string;
    manualActions: AdminManualAction[];
};

export const ADMIN_MANUAL_ORCHESTRATOR_STEPS: AdminManualStepDefinition[] = [
    {
        id: 'ARCH-001', label: '1 구조 설계', title: '구조 설계 고정', detail: '프로젝트 구조 설계와 단계 책임을 먼저 확정합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-1', action: 'STRUCTURE_DESIGN', mode: 'full',
        manualActions: [
            { id: 'layout', label: '구조 설계 점검', detail: '레이어 분리와 단계 경계를 수동 확인합니다.' },
            { id: 'entry', label: '구조 기준 확인', detail: '실행 시작점과 기본 부팅 경로 기준을 검토합니다.' },
            { id: 'readme', label: '설계 문서 점검', detail: '초기 구조 문서와 필수 안내를 점검합니다.' },
        ],
    },
    {
        id: 'ARCH-002', label: '2 폴더/기초', title: '폴더 및 기초 구현', detail: '기본 폴더 구조와 기초 실행 파일을 점검합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-2', action: 'FOLDER_BOOTSTRAP', mode: 'full',
        manualActions: [
            { id: 'folder', label: '폴더 구조 검토', detail: '폴더와 엔트리 파일이 기초 기준에 맞는지 확인합니다.' },
            { id: 'entry', label: '기초 실행 확인', detail: '기본 부팅/빌드 가능한 상태인지 점검합니다.' },
            { id: 'scope', label: '기초 범위 기록', detail: '기초 구현에서 수동 변경 가능 범위를 기록합니다.' },
        ],
    },
    {
        id: 'ARCH-003', label: '3 골조 구현', title: '설계 반영 골조 구현', detail: '설계도가 실제 골조 코드에 반영됐는지 점검합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-3', action: 'SCAFFOLD_IMPLEMENT', mode: 'full',
        manualActions: [
            { id: 'skeleton', label: '골조 반영 점검', detail: '레이어 구조와 연결 골조를 확인합니다.' },
            { id: 'boundary', label: '레이어 경계 확인', detail: '설계와 실제 골조 경계가 어긋나지 않는지 비교합니다.' },
            { id: 'fields', label: '구현 범위 기록', detail: '골조 구현에서 수동 조정 가능한 범위를 기록합니다.' },
        ],
    },
    {
        id: 'ARCH-004', label: '4 핵심엔진', title: '핵심 엔진 구성', detail: '핵심 엔진과 모듈 책임을 수동 점검합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-4', action: 'ENGINE_BUILD', mode: 'full',
        manualActions: [
            { id: 'engine', label: '핵심 엔진 확인', detail: '핵심 엔진 모듈과 책임 분리를 점검합니다.' },
            { id: 'contract', label: '엔진 계약 검토', detail: '핵심 엔진 입출력 계약과 식별자를 확인합니다.' },
            { id: 'module', label: '모듈 경계 점검', detail: '엔진 내부 모듈 경계와 연결 규칙을 검토합니다.' },
        ],
    },
    {
        id: 'ARCH-0045', label: '4.5 Refiner/Fixer', title: 'Refiner/Fixer', detail: '핵심엔진 직후 로직 전에 구조 정리, 계약 보정, 자동 수정 안전고리를 점검합니다.', flowId: 'FLOW-001', stepId: 'ARCH-0045', action: 'REFINER_FIXER', mode: 'full',
        manualActions: [
            { id: 'cleanup', label: '구조 정리', detail: '중복 경로, 죽은 경로, 느슨한 책임을 정리합니다.' },
            { id: 'contract', label: '계약 보정', detail: '엔진 계약, import, safety gate 누락을 보정합니다.' },
            { id: 'fixer', label: '자동 수정 점검', detail: '로직 진입 전 자동 수정 안전고리가 작동하는지 검토합니다.' },
        ],
    },
    {
        id: 'ARCH-005', label: '5 로직', title: '로직(ID 식별)', detail: '핵심 로직과 ID 추적 규칙을 단계별로 확인합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-5', action: 'LOGIC_IDENTIFY', mode: 'full',
        manualActions: [
            { id: 'rule', label: '핵심 로직 검토', detail: '핵심 로직의 조건과 계산 규칙을 검토합니다.' },
            { id: 'id', label: 'ID 규칙 확인', detail: 'flow / step / action 식별자가 유지되는지 확인합니다.' },
            { id: 'errors', label: '예외 규칙 검토', detail: '실패 재현과 예외 흐름을 검토합니다.' },
        ],
    },
    {
        id: 'ARCH-006', label: '6 데이터', title: '데이터 계약 점검', detail: '입출력 스키마, mock/live 계약, 필드 변경 범위를 점검합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-6', action: 'DATA_BIND', mode: 'full',
        manualActions: [
            { id: 'schema', label: '스키마 점검', detail: '입출력 필드와 데이터 타입을 확인합니다.' },
            { id: 'adapter', label: '어댑터 계약 확인', detail: 'mock/live 공급자 계약을 비교합니다.' },
            { id: 'fields', label: '필드 변경 범위 기록', detail: '수동 변경 가능 필드를 메모에 남깁니다.' },
        ],
    },
    {
        id: 'ARCH-007', label: '7 서비스', title: '서비스 연결 점검', detail: '서비스 연결 순서와 상태 전이 규칙을 관리자 수동 버튼으로 확인합니다.', flowId: 'FLOW-003', stepId: 'FLOW-003-3', action: 'PORTFOLIO_UPDATE', mode: 'full',
        manualActions: [
            { id: 'flow', label: '연결 순서 확인', detail: '서비스 연결 순서와 의존 흐름을 점검합니다.' },
            { id: 'state', label: '상태 전이 검토', detail: '상태 전이 규칙과 누락 케이스를 확인합니다.' },
            { id: 'portfolio', label: '집계 규칙 점검', detail: '도메인 상태 반영 및 집계 규칙을 검토합니다.' },
        ],
    },
    {
        id: 'ARCH-008', label: '8 API', title: '요청/응답 점검', detail: 'API 계약과 오류 코드, 서비스 연결 경계를 확인합니다.', flowId: 'FLOW-002', stepId: 'FLOW-002-3', action: 'ORDER_SUBMIT', mode: 'full',
        manualActions: [
            { id: 'request', label: '요청 스키마 확인', detail: '요청 값 검증과 필수 필드를 점검합니다.' },
            { id: 'response', label: '응답 계약 확인', detail: '응답 형식과 추적 필드 노출을 확인합니다.' },
            { id: 'errors', label: '오류 코드 검토', detail: '오류 코드와 서비스 경계 준수 여부를 검토합니다.' },
        ],
    },
    {
        id: 'ARCH-009', label: '9 프론트', title: 'UI/운영 점검', detail: '프론트 표시, 로그, 운영 메모와 수동 수정 가능 범위를 확인합니다.', flowId: 'FLOW-001', stepId: 'FLOW-001-7', action: 'FRONT_OUTPUT', mode: 'full',
        manualActions: [
            { id: 'ui', label: 'UI 노출 확인', detail: '현재 단계와 결과 카드의 UI 노출을 점검합니다.' },
            { id: 'logs', label: '로그 표시 점검', detail: 'Flow/Step 로그 노출과 필터를 확인합니다.' },
            { id: 'ops', label: '운영 메모 기록', detail: '운영 시 유의사항과 수동 수정 범위를 메모합니다.' },
        ],
    },
];

export const ADMIN_ROUTER_STAGE_LABELS: Record<AdminRouterStage, string> = {
    queued: '대기',
    active: '진행 중',
    review: '검토',
    blocked: '보류',
    completed: '완료',
};

export const ADMIN_MANUAL_SECTION_ID_MAP = ADMIN_MANUAL_ORCHESTRATOR_STEPS.map((step, index) => ({
    sectionId: `SEC-${String(index + 1).padStart(3, '0')}`,
    title: `${step.label} ${step.title}`,
    architectureId: step.id,
    flowId: step.flowId,
    stepId: step.stepId,
    action: step.action,
    assemblyIds: [step.id, step.flowId, step.stepId, step.action, ...step.manualActions.map((item) => `${step.id}:${item.id}`)],
    featureSummary: step.manualActions.map((item) => item.label).join(', '),
}));

export function createDefaultAdminManualStepState(): AdminManualStepState {
    return {
        completed: false,
        note: '',
        doneActionIds: [],
        routeStage: 'queued',
        durationDays: '1일',
        attachmentLinks: [],
        attachmentDraft: '',
        referenceUrl: '',
        startedAt: '',
        endedAt: '',
        externalStageRunId: '',
        externalStageStatus: '',
        externalStageLabel: '',
        externalStageTitle: '',
        externalStageSummary: '',
        externalStageUpdatedAt: '',
    };
}

export function hasAdminManualStepProgressEvidence(value?: Partial<AdminManualStepState> | null): boolean {
    return Boolean(
        (value?.doneActionIds && value.doneActionIds.length > 0)
        || String(value?.note || '').trim()
        || String(value?.referenceUrl || '').trim()
        || (value?.attachmentLinks && value.attachmentLinks.length > 0)
        || String(value?.startedAt || '').trim()
        || String(value?.endedAt || '').trim()
        || (value?.routeStage && value.routeStage !== 'queued'),
    );
}

export function normalizeAdminManualStepState(value?: Partial<AdminManualStepState> | null): AdminManualStepState {
    const defaults = createDefaultAdminManualStepState();
    const normalizedRouteStage = value?.routeStage === 'completed' && !hasAdminManualStepProgressEvidence(value)
        ? 'queued'
        : (value?.routeStage || defaults.routeStage);
    const completed = Boolean(value?.completed) && hasAdminManualStepProgressEvidence(value) && normalizedRouteStage !== 'queued';
    return {
        ...defaults,
        ...value,
        routeStage: normalizedRouteStage,
        completed,
        doneActionIds: Array.isArray(value?.doneActionIds) ? value.doneActionIds : defaults.doneActionIds,
        attachmentLinks: Array.isArray(value?.attachmentLinks) ? value.attachmentLinks : defaults.attachmentLinks,
        externalStageRunId: String(value?.externalStageRunId || ''),
        externalStageStatus: String(value?.externalStageStatus || ''),
        externalStageLabel: String(value?.externalStageLabel || ''),
        externalStageTitle: String(value?.externalStageTitle || ''),
        externalStageSummary: String(value?.externalStageSummary || ''),
        externalStageUpdatedAt: String(value?.externalStageUpdatedAt || ''),
    };
}

export function assertAdminManualOrchestratorContract() {
    if (ADMIN_MANUAL_ORCHESTRATOR_STEPS.length !== 10) {
        throw new Error(`admin manual orchestrator contract 누락: 4.5단계 포함 10개 단계 고정 순서 위반 (${ADMIN_MANUAL_ORCHESTRATOR_STEPS.length})`);
    }
    const sample = createDefaultAdminManualStepState();
    if (!sample.routeStage || !sample.durationDays) {
        throw new Error('admin manual orchestrator contract 누락: 기본 step state 핵심 필드 필요');
    }
}
