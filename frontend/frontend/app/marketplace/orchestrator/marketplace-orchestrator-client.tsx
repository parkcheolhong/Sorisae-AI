'use client';

import * as React from 'react';
import { resolveApiBaseUrl } from '@shared/api';
import OrchestratorStageCardPanel, { type SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';
import SharedOrchestratorFollowUpCard from '@shared/orchestrator-follow-up-card';
import { buildFollowUpPriorityScore } from '@shared/orchestrator-follow-up-history';
import { MarketplaceLeftRail, MarketplaceRightRail, type MarketplaceEngineRail } from '@/components/marketplace/marketplace-rails';
import {
    MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY,
    type MarketplaceOrchestratorBridgePayload,
} from '@/lib/admin-orchestrator-bridge';
import { getAdminToken } from '@/lib/admin-session';

type ConversationMessage = {
    role: string;
    content: string;
    speaker?: string | null;
    timestamp?: string | null;
    step_title?: string | null;
};

type Product = {
    id: string;
    title: string;
    category: string;
    price: string;
    summary: string;
    highlights: string[];
};

type CustomerOrchestrateResult = {
    requested_by?: { id: number; email: string };
    result?: {
        final_output?: string;
        output_dir?: string | null;
        completion_summary?: string | null;
        failure_summary?: string | null;
        apply_error?: string | null;
        postcheck_error?: string | null;
        stage_run?: SharedOrchestratorStageRun;
    };
};

type CompletionItem = {
    id: number;
    project_name: string;
    mode: string;
    attempts: number;
    output_dir?: string | null;
    gate_passed: boolean;
    created_at?: string;
};

type FeatureLogItem = {
    id: number;
    status: string;
    message: string;
    flow_id?: string | null;
    step_id?: string | null;
    action?: string | null;
    created_at?: string;
};

type RetryQueueItem = {
    id: number;
    queue_name: string;
    status: string;
    last_error?: string | null;
    attempt_count?: number;
    updated_at?: string;
};

type RetryReplayResponse = {
    id?: number;
    status?: string;
    attempt_count?: number;
    last_error?: string | null;
};

type MarketplaceSlotRow = {
    slot: number;
    engine_id?: string;
    engine_name_ko?: string;
    file?: string | null;
    category?: string;
    priority?: string;
    slot_status?: string;
    source?: string;
    usage_description_ko?: string;
    experiment_template_ko?: string;
    market_status?: string;
    is_official?: boolean;
};

type SlotExperimentResult = {
    status: string;
    experiment_type?: string;
    message?: string;
    error?: string;
    output_preview?: unknown;
    callable?: string | null;
};

const CATEGORY_USAGE_GUIDE: Record<string, string> = {
    interpreter: '요구사항 번역/정리, 다국어 문맥 변환',
    voice: '음성 명령 인식, 실시간 입력 처리',
    music: '감정 기반 생성/편곡, 출력 콘텐츠 생성',
    iot: '디바이스 제어, 센서 상태 수집',
    simulation: '가상 시나리오 실험, 경제/운영 검증',
    security: '보안 이벤트 분석, 위험도 평가/관제',
    general: '복합 유틸리티/보조 처리',
};

function getCategoryUsageLabel(category?: string): string {
    const key = String(category || 'general').trim().toLowerCase();
    return CATEGORY_USAGE_GUIDE[key] || CATEGORY_USAGE_GUIDE.general;
}

function getCategoryOutputExample(category?: string): string {
    const key = String(category || 'general').trim().toLowerCase();
    if (key === 'interpreter') return '{"translated_text":"Hello, the meeting starts at 10 AM."}';
    if (key === 'voice') return '{"recognized_text":"거실 조명을 켜줘","confidence":0.94}';
    if (key === 'music') return '{"track_id":"mus_2026_01","mood":"calm","duration_sec":120}';
    if (key === 'iot') return '{"device_id":"living-room-light","state":"on"}';
    if (key === 'simulation') return '{"scenario":"weekend-promo","users":120,"result":"stable"}';
    if (key === 'security') return '{"scan_result":"clean","risk_score":0.05}';
    return '{"status":"ok"}';
}
function isOfficialSlot(row?: MarketplaceSlotRow): boolean {
    if (!row) return false;
    if (row.is_official) return true;
    const market = String(row.market_status || '').trim().toLowerCase();
    return market === 'official';
}

type EngineDetail = {
    description: string;
    input: string;
    output: string;
    upstream: string;
    downstream: string;
    programs: string[];
};

const CATEGORY_DETAIL: Record<string, EngineDetail> = {
    interpreter: {
        description: '텍스트나 음성을 다국어로 번역·변환합니다. 한국어 ↔ 영어·중국어·동남아어 실시간 문맥 번역을 처리합니다.',
        input: '원문 텍스트, 언어 코드, 문맥 메타데이터',
        output: '번역 텍스트, 신뢰도 점수, 언어 감지 결과',
        upstream: '음성 인식(voice) → 텍스트 추출 후 입력',
        downstream: '음악(music) 감정 분석 또는 보안(security) 분류로 전달',
        programs: [
            '실시간 회의 동시통역 시스템',
            '다국어 고객 응대 챗봇',
            '해외 계약서 번역 자동화 파이프라인',
        ],
    },
    voice: {
        description: '마이크 입력 또는 오디오 파일에서 음성을 인식하고 텍스트로 변환합니다. 명령어 파싱 및 의도 분류까지 처리합니다.',
        input: '오디오 스트림, WAV/MP3 파일, PCM 바이트',
        output: '인식 텍스트, 신뢰도, 감지된 명령 의도',
        upstream: '마이크·IoT 센서 입력 또는 직접 오디오 파일',
        downstream: '번역(interpreter) 또는 IoT 제어 명령으로 전달',
        programs: [
            '음성 명령 스마트홈 제어 시스템',
            '회의록 자동 생성기',
            '고객 콜센터 음성 분석 파이프라인',
        ],
    },
    music: {
        description: '감정 상태나 텍스트 입력을 기반으로 음악·멜로디·가사를 자동 생성합니다. 분위기·장르·BPM을 파라미터로 제어할 수 있습니다.',
        input: '감정 레이블, 분위기 설명 텍스트, 장르 코드',
        output: '트랙 메타데이터, 멜로디 코드, 가사 초안',
        upstream: '번역(interpreter) 또는 음성(voice) 감정 분석 결과',
        downstream: '시뮬레이션(simulation) 콘텐츠 배포 검증으로 전달',
        programs: [
            '감정 기반 배경음악 자동 생성 서비스',
            '스트리밍 플랫폼 개인화 추천 시스템',
            '게임 이벤트 연동 실시간 OST 생성기',
        ],
    },
    iot: {
        description: '스마트홈·공장·센서 장치를 제어하고 상태를 수집합니다. MQTT·HTTP 프로토콜로 다수 디바이스를 동시 관리합니다.',
        input: '장치 ID, 명령 코드, 센서 임계값 설정',
        output: '장치 상태, 응답 코드, 센서 로그',
        upstream: '음성(voice) 명령 파싱 또는 보안(security) 이벤트 트리거',
        downstream: '시뮬레이션(simulation) 또는 뇌(brain) 의사결정 엔진으로 전달',
        programs: [
            '스마트홈 자동화 통합 플랫폼',
            '공장 설비 원격 모니터링 시스템',
            '에너지 절감 자동 제어 파이프라인',
        ],
    },
    simulation: {
        description: '가상 시나리오에서 경제·게임·운영 상황을 수치로 시뮬레이션합니다. 다양한 변수를 바꿔가며 최적 전략을 도출합니다.',
        input: '시나리오 파라미터, 초기 조건, 반복 횟수',
        output: '시뮬레이션 결과 통계, 최적값, 위험 지표',
        upstream: 'IoT 센서(iot) 데이터 또는 금융(finance) 예측값',
        downstream: '보안(security) 위험 평가 또는 뇌(brain) 전략 결정으로 전달',
        programs: [
            '게임 경제 밸런싱 자동화 도구',
            '투자 포트폴리오 시뮬레이터',
            '물류 최적화 가상 검증 플랫폼',
        ],
    },
    security: {
        description: '네트워크·시스템 이벤트를 분석해 위협을 탐지하고 위험도를 평가합니다. 보안 로그를 실시간으로 파싱해 대응 명령을 생성합니다.',
        input: '보안 이벤트 로그, IP·사용자 ID, 심각도 레이블',
        output: '위험도 점수, 대응 명령, 보안 상태 요약',
        upstream: 'IoT(iot) 디바이스 이상 감지 또는 뇌(brain) 의사결정 요청',
        downstream: '시뮬레이션(simulation) 위험 시나리오 또는 파이프라인 최종 보고로 전달',
        programs: [
            '실시간 사이버 위협 탐지 대시보드',
            '스마트홈 침입 감지 자동 대응 시스템',
            '보안 감사 자동화 파이프라인',
        ],
    },
    brain: {
        description: 'AI 의사결정·추론 엔진으로, 복잡한 상황을 분석하고 전략을 자동 수립합니다. 멀티 에이전트 협업을 조율하는 핵심 두뇌 역할을 합니다.',
        input: '상황 데이터, 이전 결정 이력, 목표 목록',
        output: '우선순위 결정, 실행 계획, 신뢰도 점수',
        upstream: '모든 카테고리 엔진의 분석 결과를 통합 입력',
        downstream: '보안(security)·IoT(iot)·파이프라인 최종 실행으로 전달',
        programs: [
            '멀티 에이전트 자율 의사결정 시스템',
            '복합 조건 기반 자동화 워크플로',
            'AI 지휘관 기반 시뮬레이션 플랫폼',
        ],
    },
    finance: {
        description: '주식·투자 데이터를 분석해 수익 예측과 포트폴리오 최적화를 수행합니다. 실시간 시장 데이터를 기반으로 투자 의사결정을 지원합니다.',
        input: '종목 코드, 과거 가격 데이터, 경제 지표',
        output: '수익률 예측, 매수·매도 신호, 위험 지표',
        upstream: '시뮬레이션(simulation) 파라미터 또는 뇌(brain) 전략 요청',
        downstream: '보안(security) 이상거래 감지 또는 파이프라인 보고로 전달',
        programs: [
            '자동 주식 매매 신호 생성기',
            'AI 기반 포트폴리오 리밸런싱 시스템',
            '투자 리스크 자동 경보 대시보드',
        ],
    },
    general: {
        description: '복합 처리 유틸리티 엔진으로 다양한 입력을 가공·변환합니다. 다른 엔진의 보조 역할이나 전처리·후처리 단계에 활용됩니다.',
        input: '임의 형식 텍스트, JSON, 바이너리 데이터',
        output: '정제된 데이터, 요약, 변환 결과',
        upstream: '모든 카테고리 엔진 앞단 전처리로 연결 가능',
        downstream: '모든 카테고리 엔진 뒤단 후처리로 연결 가능',
        programs: [
            '범용 데이터 전처리 파이프라인',
            '로그 수집·정제 자동화 도구',
            '멀티포맷 데이터 변환기',
        ],
    },
};

function getEngineDetail(category?: string): EngineDetail {
    const key = String(category || 'general').trim().toLowerCase();
    return CATEGORY_DETAIL[key] || CATEGORY_DETAIL.general;
}

function getProgramFormationDescription(blocks: Array<{ slot: number; category: string; label: string }>): string {
    if (blocks.length === 0) return '';
    if (blocks.length === 1) {
        const b = blocks[0];
        return `슬롯 ${b.slot} [${b.label}] 단독 실행 — ${getCategoryUsageLabel(b.category)} 기능을 수행합니다.`;
    }
    const chain = blocks.map((b) => `${b.label}(${b.category})`).join(' → ');
    const cats = [...new Set(blocks.map((b) => b.category.toLowerCase()))];
    let summary = '';
    if (cats.includes('voice') && cats.includes('interpreter')) {
        summary = '음성 인식 후 다국어 번역';
    } else if (cats.includes('interpreter') && cats.includes('music')) {
        summary = '번역 텍스트 기반 감정 음악 생성';
    } else if (cats.includes('iot') && cats.includes('security')) {
        summary = 'IoT 장치 모니터링 + 보안 위협 분석';
    } else if (cats.includes('simulation') && cats.includes('finance')) {
        summary = '투자 시뮬레이션 및 수익 예측';
    } else if (cats.includes('brain')) {
        summary = 'AI 두뇌 중심의 복합 의사결정';
    } else if (cats.includes('voice') && cats.includes('iot')) {
        summary = '음성 명령 기반 IoT 자동 제어';
    } else {
        summary = cats.map((c) => getCategoryUsageLabel(c)).join(' + ');
    }
    return `[${summary}] 파이프라인 — ${chain}`;
}

function toListPayload<T>(payload: unknown): T[] {
    if (Array.isArray(payload)) {
        return payload as T[];
    }
    if (payload && typeof payload === 'object' && Array.isArray((payload as { items?: unknown }).items)) {
        return (payload as { items: T[] }).items;
    }
    return [];
}

type GeneratedProgramSummary = {
    output_dir?: string | null;
    output_archive_path?: string | null;
    delivery_gate_blocked: boolean;
    delivery_gate_message?: string | null;
    publish_ready: boolean;
    publish_targets: string[];
    shipping_zip_ok: boolean;
    validation_profile?: string | null;
    required_tests: string[];
    priority_average_score?: number;
    priority_peak_score?: number;
    priority_latest_score?: number;
    priority_previous_score?: number | null;
    priority_momentum?: number;
    priority_cumulative_score?: number;
    approval_history_count?: number;
    stage_run_status?: string | null;
    hard_gate_failed_stages?: string[];
};

type Props = {
    selectedProduct: Product;
    initialProjectName: string;
    initialTaskDraft: string;
    sourceProjectTitle?: string | null;
};

const CUSTOMER_TOKEN_KEY = 'customer_token';

type CustomerMemberType = 'individual' | 'sole_proprietor' | 'corporation';

const MEMBER_TYPE_LABELS: Record<CustomerMemberType, string> = {
    individual: '개인',
    sole_proprietor: '개인사업자',
    corporation: '법인사업자',
};

type ReverseQuestionMode = 'implementation' | 'pass_review' | 'feature_innovation';

type ConversationTonePreset = 'auto' | 'free_talk' | 'concise' | 'execution';

type ReverseQuestionModeConfig = {
    id: ReverseQuestionMode;
    label: string;
    description: string;
    tag: string;
};

const REVERSE_QUESTION_MODE_CONFIGS: ReverseQuestionModeConfig[] = [
    {
        id: 'implementation',
        label: '구현 역질문',
        description: '현재 구현 조건과 막힌 지점을 짚어 역질문합니다.',
        tag: 'reverse-question-implementation',
    },
    {
        id: 'pass_review',
        label: '통과 역질문',
        description: '검증/통과 기준을 먼저 확인하는 역질문을 생성합니다.',
        tag: 'reverse-question-pass',
    },
    {
        id: 'feature_innovation',
        label: '기능추가/신기술 역질문',
        description: '신기술 도입 포인트와 기능확장 가설을 질문합니다.',
        tag: 'reverse-question-innovation',
    },
];

function getReverseQuestionModeConfig(mode: ReverseQuestionMode): ReverseQuestionModeConfig {
    return REVERSE_QUESTION_MODE_CONFIGS.find((item) => item.id === mode) || REVERSE_QUESTION_MODE_CONFIGS[0];
}

const CUSTOMER_TONE_PRESET_CONFIGS: Array<{
    id: ConversationTonePreset;
    label: string;
    description: string;
    conversationMode: string;
    responseStyle: string;
    tag: string;
}> = [
        {
            id: 'auto',
            label: '자동질문',
            description: '오케스트레이터가 먼저 3종을 물어보고 스타일을 확정합니다.',
            conversationMode: 'auto',
            responseStyle: 'balanced',
            tag: 'tone-auto',
        },
        {
            id: 'free_talk',
            label: '자유대화',
            description: '친구처럼 자연스럽게 묻고 답합니다.',
            conversationMode: 'free',
            responseStyle: 'free_talk',
            tag: 'tone-free-talk',
        },
        {
            id: 'concise',
            label: '간결',
            description: '핵심만 빠르게 요약해 답합니다.',
            conversationMode: 'free',
            responseStyle: 'concise',
            tag: 'tone-concise',
        },
        {
            id: 'execution',
            label: '실행형',
            description: '실행 단계 중심으로 바로 안내합니다.',
            conversationMode: 'directive_fixed',
            responseStyle: 'execution',
            tag: 'tone-execution',
        },
    ];

function getCustomerTonePresetConfig(preset: ConversationTonePreset) {
    return CUSTOMER_TONE_PRESET_CONFIGS.find((item) => item.id === preset) || CUSTOMER_TONE_PRESET_CONFIGS[0];
}

function buildTask(product: Product, userPrompt: string, projectName: string) {
    return [
        `[상품 주문 오케스트레이터]`,
        `- 상품 ID: ${product.id}`,
        `- 상품명: ${product.title}`,
        `- 카테고리: ${product.category}`,
        `- 가격: ${product.price}`,
        `- 프로젝트명: ${projectName}`,
        `- 핵심 포인트: ${product.highlights.join(', ')}`,
        '',
        '[고객 요청]',
        userPrompt.trim(),
    ].join('\n');
}

export default function MarketplaceOrchestratorClient({
    selectedProduct,
    initialProjectName,
    initialTaskDraft,
    sourceProjectTitle,
}: Props) {
    const apiBaseUrl = React.useMemo(() => resolveApiBaseUrl(), []);
    const [token, setToken] = React.useState('');
    const [me, setMe] = React.useState<{ email: string; username: string; full_name?: string | null; member_type?: string; business_name?: string | null; business_registration_number?: string | null; representative_name?: string | null } | null>(null);
    const [authMode, setAuthMode] = React.useState<'login' | 'signup'>('login');
    const [email, setEmail] = React.useState('');
    const [username, setUsername] = React.useState('');
    const [fullName, setFullName] = React.useState('');
    const [memberType, setMemberType] = React.useState<CustomerMemberType>('individual');
    const [businessName, setBusinessName] = React.useState('');
    const [businessRegistrationNumber, setBusinessRegistrationNumber] = React.useState('');
    const [representativeName, setRepresentativeName] = React.useState('');
    const [password, setPassword] = React.useState('');
    const [authLoading, setAuthLoading] = React.useState(false);
    const [authMessage, setAuthMessage] = React.useState('');
    const [projectName, setProjectName] = React.useState(initialProjectName);
    const [taskDraft, setTaskDraft] = React.useState(initialTaskDraft);
    const [runId, setRunId] = React.useState('');
    const [stageRun, setStageRun] = React.useState<SharedOrchestratorStageRun | null>(null);
    const [stageNoteDraft, setStageNoteDraft] = React.useState('');
    const [stageRevisionNote, setStageRevisionNote] = React.useState('');
    const [stageSubstepChecks, setStageSubstepChecks] = React.useState<Record<string, boolean>>({});
    const [stageLoading, setStageLoading] = React.useState(false);
    const [submitLoading, setSubmitLoading] = React.useState(false);
    const [resultText, setResultText] = React.useState('');
    const [errorText, setErrorText] = React.useState('');
    const [logs, setLogs] = React.useState<FeatureLogItem[]>([]);
    const [completions, setCompletions] = React.useState<CompletionItem[]>([]);
    const [retryQueue, setRetryQueue] = React.useState<RetryQueueItem[]>([]);
    const [generatedProgramSummary, setGeneratedProgramSummary] = React.useState<GeneratedProgramSummary | null>(null);
    const [conversation, setConversation] = React.useState<ConversationMessage[]>([]);
    const [chatInput, setChatInput] = React.useState('');
    const [chatLoading, setChatLoading] = React.useState(false);
    const [engineRails, setEngineRails] = React.useState<MarketplaceEngineRail[] | undefined>(undefined);
    const [engineSlots, setEngineSlots] = React.useState<MarketplaceSlotRow[]>([]);
    const [selectedEngineRailId, setSelectedEngineRailId] = React.useState<string>('RAIL-01');
    const [conversationTonePreset] = React.useState<ConversationTonePreset>('auto');
    const [reverseQuestionMode, setReverseQuestionMode] = React.useState<ReverseQuestionMode>('implementation');
    const [compactUi, setCompactUi] = React.useState(true);
    const terminalFocusedView = false;

    const authHeaders = React.useMemo(() => (
        token ? { Authorization: `Bearer ${token}` } : undefined
    ), [token]);

    const activeStage = React.useMemo(
        () => (stageRun?.stages || []).find((stage) => stage.id === stageRun?.current_stage_id) || null,
        [stageRun],
    );
    const customerFollowUpScore = React.useMemo(() => {
        const completionPenalty = generatedProgramSummary?.publish_ready ? 5 : 75;
        const gatePenalty = generatedProgramSummary?.delivery_gate_blocked ? 85 : 10;
        const retryPenalty = Math.min(100, retryQueue.length * 20);
        const activePenalty = activeStage?.status === 'failed' ? 90 : activeStage?.status === 'manual_correction' ? 60 : 15;
        return buildFollowUpPriorityScore({
            severity: completionPenalty,
            recency: activePenalty,
            approvalRisk: Math.min(100, (generatedProgramSummary?.approval_history_count ?? 0) * 25),
            hardGateImpact: gatePenalty,
            operationalRisk: retryPenalty,
            selfRunPriority: (generatedProgramSummary?.stage_run_status === 'failed' || generatedProgramSummary?.stage_run_status === 'manual_correction') ? 80 : 20,
        });
    }, [activeStage?.status, generatedProgramSummary?.delivery_gate_blocked, generatedProgramSummary?.publish_ready, retryQueue.length]);
    const customerFollowUpRecommendations = React.useMemo(() => {
        const items: Array<{ id: string; label: string; detail: string }> = [];
        if (generatedProgramSummary?.delivery_gate_message) {
            items.push({ id: 'delivery-gate', label: '출고 게이트 보정', detail: generatedProgramSummary.delivery_gate_message });
        }
        if (activeStage) {
            items.push({ id: 'active-stage', label: '현재 카드 우선 처리', detail: `${activeStage.label} · ${activeStage.title} 상태=${activeStage.status}` });
        }
        if (retryQueue.length > 0) {
            items.push({ id: 'retry-queue', label: '재시도 큐 정리', detail: `재시도 대기 ${retryQueue.length}건을 먼저 정리하세요.` });
        }
        if (generatedProgramSummary?.required_tests?.length) {
            items.push({ id: 'required-tests', label: '필수 검증 유지', detail: `required tests: ${generatedProgramSummary.required_tests.join(', ')}` });
        }
        return items.slice(0, 4);
    }, [activeStage, generatedProgramSummary?.delivery_gate_message, generatedProgramSummary?.required_tests, retryQueue.length]);
    const customerHistoryStats = {
        averageScore: generatedProgramSummary?.priority_average_score ?? customerFollowUpScore.weighted,
        peakScore: generatedProgramSummary?.priority_peak_score ?? customerFollowUpScore.weighted,
        latestScore: generatedProgramSummary?.priority_latest_score ?? customerFollowUpScore.weighted,
        previousScore: generatedProgramSummary?.priority_previous_score ?? null,
        momentum: generatedProgramSummary?.priority_momentum ?? 0,
        cumulativeScore: generatedProgramSummary?.priority_cumulative_score ?? customerFollowUpScore.weighted,
    };
    const safeCompletions = React.useMemo(() => toListPayload<CompletionItem>(completions), [completions]);
    const safeLogs = React.useMemo(() => toListPayload<FeatureLogItem>(logs), [logs]);
    const safeRetryQueue = React.useMemo(() => toListPayload<RetryQueueItem>(retryQueue), [retryQueue]);
    const reverseQuestionModeConfig = React.useMemo(
        () => getReverseQuestionModeConfig(reverseQuestionMode),
        [reverseQuestionMode],
    );
    const conversationTonePresetConfig = React.useMemo(
        () => getCustomerTonePresetConfig(conversationTonePreset),
        [conversationTonePreset],
    );
    const selectedEngineRail = React.useMemo(
        () => (engineRails || []).find((rail) => rail.rail_id === selectedEngineRailId) || null,
        [engineRails, selectedEngineRailId],
    );
    const selectedEngineSlotRows = React.useMemo(() => {
        if (!selectedEngineRail) {
            return [];
        }
        return engineSlots.filter((row) => row.slot >= selectedEngineRail.slot_start && row.slot <= selectedEngineRail.slot_end);
    }, [engineSlots, selectedEngineRail]);

    const [slotLaunchResults, setSlotLaunchResults] = React.useState<Record<number, { status: string; message?: string; error?: string }>>({});
    const [slotLaunchLoading, setSlotLaunchLoading] = React.useState<Record<number, boolean>>({});
    const [slotExperimentInputs, setSlotExperimentInputs] = React.useState<Record<number, string>>({});
    const [slotExperimentResults, setSlotExperimentResults] = React.useState<Record<number, SlotExperimentResult>>({});
    const [slotExperimentLoading, setSlotExperimentLoading] = React.useState<Record<number, boolean>>({});
    const [focusedSlotNumber, setFocusedSlotNumber] = React.useState<number | null>(null);
    const [expandedSlotNumber, setExpandedSlotNumber] = React.useState<number | null>(null);
    const [smokeRateByRail, setSmokeRateByRail] = React.useState<Record<string, number>>({});
    const [pipelineRateByRail, setPipelineRateByRail] = React.useState<Record<string, number>>({});
    const [hoveredTubeSlot, setHoveredTubeSlot] = React.useState<{
        slot: number;
        railId: string;
        engineName: string;
        category: string;
        inputExample: string;
        outputExample: string;
    } | null>(null);
    const slotCardRefs = React.useRef<Record<number, HTMLDivElement | null>>({});

    const tubeRails = React.useMemo(() => {
        return (engineRails || []).map((rail) => {
            const slots = engineSlots
                .filter((slot) => slot.slot >= rail.slot_start && slot.slot <= rail.slot_end)
                .sort((a, b) => a.slot - b.slot);
            return {
                rail,
                slots,
                summary: Array.from(new Set(slots.map((slot) => (slot.category || 'general').toLowerCase()))).slice(0, 4),
            };
        });
    }, [engineRails, engineSlots]);

    const railIdBySlot = React.useMemo(() => {
        const mapping: Record<number, string> = {};
        for (const railInfo of tubeRails) {
            for (const slot of railInfo.slots) {
                mapping[slot.slot] = railInfo.rail.rail_id;
            }
        }
        return mapping;
    }, [tubeRails]);

    const railLiveRates = React.useMemo(() => {
        const rates: Record<string, { smoke: number | null; experiment: number | null; pipeline: number | null }> = {};

        for (const railInfo of tubeRails) {
            const railId = railInfo.rail.rail_id;
            const slotNumbers = railInfo.slots.map((slot) => slot.slot);

            const experimentDone = slotNumbers
                .map((slot) => slotExperimentResults[slot])
                .filter((result) => result && result.status !== 'running') as SlotExperimentResult[];
            const experimentPassed = experimentDone.filter((result) => result.status === 'ok').length;
            const experimentRate = experimentDone.length > 0 ? Math.round((experimentPassed / experimentDone.length) * 100) : null;

            rates[railId] = {
                smoke: smokeRateByRail[railId] ?? null,
                experiment: experimentRate,
                pipeline: pipelineRateByRail[railId] ?? null,
            };
        }

        return rates;
    }, [pipelineRateByRail, slotExperimentResults, smokeRateByRail, tubeRails]);

    React.useEffect(() => {
        if (!focusedSlotNumber) return;
        const isVisibleInRail = selectedEngineSlotRows.some((row) => row.slot === focusedSlotNumber);
        if (!isVisibleInRail) return;
        const target = slotCardRefs.current[focusedSlotNumber];
        if (!target) return;
        const timer = window.setTimeout(() => {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 90);
        return () => window.clearTimeout(timer);
    }, [focusedSlotNumber, selectedEngineSlotRows]);

    React.useEffect(() => {
        if (selectedEngineSlotRows.length === 0) {
            setExpandedSlotNumber(null);
            return;
        }
        // Keep one card expanded by default so users immediately see what each engine does.
        if (!selectedEngineSlotRows.some((row) => row.slot === expandedSlotNumber)) {
            setExpandedSlotNumber(selectedEngineSlotRows[0].slot);
        }
    }, [selectedEngineSlotRows, expandedSlotNumber]);

    const launchSlot = React.useCallback(async (row: MarketplaceSlotRow) => {
        if (!authHeaders) {
            setErrorText('로그인 후 엔진을 실행할 수 있습니다.');
            return;
        }
        setSlotLaunchLoading((prev) => ({ ...prev, [row.slot]: true }));
        setSlotLaunchResults((prev) => ({ ...prev, [row.slot]: { status: 'running' } }));
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/engine/launch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({ slot: row.slot, engine_id: row.engine_id, file: row.file, dry_run: true }),
            });
            const payload = await response.json().catch(() => null) as { status?: string; message?: string; error?: string } | null;
            if (!response.ok) {
                setSlotLaunchResults((prev) => ({ ...prev, [row.slot]: { status: 'error', error: (payload as any)?.detail || 'API 오류' } }));
            } else {
                setSlotLaunchResults((prev) => ({ ...prev, [row.slot]: { status: payload?.status || 'ok', message: payload?.message, error: payload?.error } }));
            }
        } catch (err: any) {
            setSlotLaunchResults((prev) => ({ ...prev, [row.slot]: { status: 'error', error: err?.message || '네트워크 오류' } }));
        } finally {
            setSlotLaunchLoading((prev) => ({ ...prev, [row.slot]: false }));
        }
    }, [apiBaseUrl, authHeaders]);

    const runSlotExperiment = React.useCallback(async (row: MarketplaceSlotRow) => {
        if (!authHeaders) {
            setErrorText('로그인 후 엔진 실험을 실행할 수 있습니다.');
            return;
        }

        const defaultTemplate = row.experiment_template_ko || row.usage_description_ko || row.engine_name_ko || '';
        const typedInput = slotExperimentInputs[row.slot];
        const experimentInput = (typedInput ?? defaultTemplate).trim();
        if (typedInput == null && defaultTemplate) {
            setSlotExperimentInputs((prev) => ({ ...prev, [row.slot]: defaultTemplate }));
        }
        setSlotExperimentLoading((prev) => ({ ...prev, [row.slot]: true }));
        setSlotExperimentResults((prev) => ({ ...prev, [row.slot]: { status: 'running', message: '실험 실행 중' } }));

        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/engine/experiment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({
                    slot: row.slot,
                    engine_id: row.engine_id,
                    file: row.file,
                    category: row.category,
                    experiment_input: experimentInput,
                    timeout_sec: 8.0,
                }),
            });
            const payload = await response.json().catch(() => null) as SlotExperimentResult | null;
            if (!response.ok) {
                setSlotExperimentResults((prev) => ({
                    ...prev,
                    [row.slot]: { status: 'error', error: (payload as any)?.detail || '실험 API 오류' },
                }));
            } else {
                setSlotExperimentResults((prev) => ({
                    ...prev,
                    [row.slot]: {
                        status: payload?.status || 'ok',
                        experiment_type: payload?.experiment_type,
                        message: payload?.message,
                        error: payload?.error,
                        output_preview: payload?.output_preview,
                        callable: payload?.callable || null,
                    },
                }));
            }
        } catch (err: any) {
            setSlotExperimentResults((prev) => ({
                ...prev,
                [row.slot]: { status: 'error', error: err?.message || '실험 네트워크 오류' },
            }));
        } finally {
            setSlotExperimentLoading((prev) => ({ ...prev, [row.slot]: false }));
        }
    }, [apiBaseUrl, authHeaders, slotExperimentInputs]);

    const [smokeTestResult, setSmokeTestResult] = React.useState<{ rail_id?: string; passed?: number; failed?: number; pass_rate_pct?: number; results?: Array<{ slot: number; status: string; file?: string | null; error?: string | null }> } | null>(null);
    const [smokeTestLoading, setSmokeTestLoading] = React.useState(false);

    // ── 레일 대표 슬롯 데모 (R1~R6) ───────────────────────────────────
    type RailDemoEntry = {
        rail_id: string;
        slot: number;
        category: string;
        engine_name_ko: string;
        experiment_template_ko: string;
        result: { status: string; experiment_type?: string; output_preview?: unknown; error?: string };
        passed: boolean;
    };
    const [railDemoResult, setRailDemoResult] = React.useState<{
        passed: number; failed: number; total: number; pass_rate_pct: number;
        demo_results: RailDemoEntry[];
    } | null>(null);
    const [railDemoLoading, setRailDemoLoading] = React.useState(false);

    const runRailDemo = React.useCallback(async () => {
        if (!authHeaders) { setErrorText('로그인 후 실행할 수 있습니다.'); return; }
        setRailDemoLoading(true);
        setRailDemoResult(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/engine/rail-demo`, {
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                cache: 'no-store',
            });
            const payload = await response.json().catch(() => null);
            if (!response.ok) { setErrorText((payload as any)?.detail || 'Rail demo API 오류'); }
            else { setRailDemoResult(payload); }
        } catch (err: any) {
            setErrorText(err?.message || 'Rail demo 네트워크 오류');
        } finally {
            setRailDemoLoading(false);
        }
    }, [apiBaseUrl, authHeaders]);

    // ── 파이프라인 빌더 ──────────────────────────────────────────────────
    type PipelineBlock = { slot: number; category: string; label: string; template_override: string };
    type PipelineBlockResult = {
        slot: number; category: string; label: string; status: string;
        experiment_type?: string; output_preview?: unknown; error?: string;
    };
    type PipelineResult = {
        status: string; pipeline_id: string; mode: string; user_command: string;
        block_count: number; passed_blocks: number; failed_blocks: number;
        block_results: PipelineBlockResult[]; final_output: string;
    };
    const [pipelineCommand, setPipelineCommand] = React.useState('');
    const [pipelineMode, setPipelineMode] = React.useState<'sequential' | 'parallel'>('sequential');
    const [pipelineBlocks, setPipelineBlocks] = React.useState<PipelineBlock[]>([]);
    const [pipelineResult, setPipelineResult] = React.useState<PipelineResult | null>(null);
    const [pipelineLoading, setPipelineLoading] = React.useState(false);
    const [pipelineBlockInput, setPipelineBlockInput] = React.useState('');

    const addPipelineBlock = React.useCallback(() => {
        const slotNum = parseInt(pipelineBlockInput.trim(), 10);
        if (isNaN(slotNum) || slotNum < 1 || slotNum > 120) return;
        const meta = engineSlots.find((r) => r.slot === slotNum);
        const block: PipelineBlock = {
            slot: slotNum,
            category: meta?.category || 'general',
            label: meta?.engine_name_ko || `슬롯 ${slotNum}`,
            template_override: meta?.experiment_template_ko || '',
        };
        setPipelineBlocks((prev) => [...prev.filter((b) => b.slot !== slotNum), block]);
        setPipelineBlockInput('');
    }, [engineSlots, pipelineBlockInput]);

    const removePipelineBlock = React.useCallback((slot: number) => {
        setPipelineBlocks((prev) => prev.filter((b) => b.slot !== slot));
    }, []);

    const runPipeline = React.useCallback(async () => {
        if (!authHeaders) { setErrorText('로그인 후 파이프라인을 실행할 수 있습니다.'); return; }
        if (pipelineBlocks.length === 0) { setErrorText('파이프라인 블럭을 1개 이상 추가하세요.'); return; }
        setPipelineLoading(true);
        setPipelineResult(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/engine/pipeline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({
                    user_command: pipelineCommand || '120엔진 파이프라인 실행',
                    engine_blocks: pipelineBlocks.map((b) => ({
                        slot: b.slot,
                        category: b.category,
                        label: b.label,
                        template_override: b.template_override || undefined,
                    })),
                    mode: pipelineMode,
                    timeout_sec: 10.0,
                }),
            });
            const payload = await response.json().catch(() => null) as PipelineResult | null;
            if (!response.ok) { setErrorText((payload as any)?.detail || '파이프라인 API 오류'); }
            else if (payload) {
                setPipelineResult(payload);
                const grouped: Record<string, { total: number; passed: number }> = {};
                for (const result of payload.block_results || []) {
                    const railId = railIdBySlot[result.slot] || '';
                    if (!railId) continue;
                    if (!grouped[railId]) grouped[railId] = { total: 0, passed: 0 };
                    grouped[railId].total += 1;
                    if (result.status === 'ok') grouped[railId].passed += 1;
                }
                setPipelineRateByRail((prev) => {
                    const next = { ...prev };
                    for (const [railId, stat] of Object.entries(grouped)) {
                        next[railId] = stat.total > 0 ? Math.round((stat.passed / stat.total) * 100) : 0;
                    }
                    return next;
                });
            }
        } catch (err: any) {
            setErrorText(err?.message || '파이프라인 네트워크 오류');
        } finally {
            setPipelineLoading(false);
        }
    }, [apiBaseUrl, authHeaders, pipelineBlocks, pipelineCommand, pipelineMode, railIdBySlot]);

    const runRailSmokeTest = React.useCallback(async (railId: string) => {
        if (!authHeaders) {
            setErrorText('로그인 후 smoke test를 실행할 수 있습니다.');
            return;
        }
        setSmokeTestLoading(true);
        setSmokeTestResult(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/engine/smoke-test/${encodeURIComponent(railId)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({ dry_run: true, timeout_per_slot: 5.0 }),
            });
            const payload = await response.json().catch(() => null);
            if (!response.ok) {
                setErrorText((payload as any)?.detail || 'Smoke test API 오류');
            } else {
                setSmokeTestResult(payload);
                const railKey = String((payload as any)?.rail_id || railId || '').trim();
                const rate = Number((payload as any)?.pass_rate_pct);
                if (railKey) {
                    setSmokeRateByRail((prev) => ({ ...prev, [railKey]: Number.isFinite(rate) ? rate : 0 }));
                }
            }
        } catch (err: any) {
            setErrorText(err?.message || 'Smoke test 네트워크 오류');
        } finally {
            setSmokeTestLoading(false);
        }
    }, [apiBaseUrl, authHeaders]);

    React.useEffect(() => {
        if (terminalFocusedView && !compactUi) {
            setCompactUi(true);
        }
    }, [compactUi, terminalFocusedView]);

    const refreshStageRun = React.useCallback(async (targetRunId?: string) => {
        const effectiveRunId = targetRunId || runId;
        if (!effectiveRunId || !authHeaders) return;
        const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs/${encodeURIComponent(effectiveRunId)}`, {
            headers: authHeaders,
            cache: 'no-store',
        });
        if (!response.ok) {
            return;
        }
        const payload = await response.json();
        setStageRun(payload);
    }, [apiBaseUrl, authHeaders, runId]);

    const loadMyInfo = React.useCallback(async (targetToken: string) => {
        const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
            headers: { Authorization: `Bearer ${targetToken}` },
            cache: 'no-store',
        });
        if (!response.ok) {
            throw new Error('내 정보를 불러오지 못했습니다.');
        }
        const payload = await response.json();
        setMe(payload);
    }, [apiBaseUrl]);

    const loadHistory = React.useCallback(async (targetToken?: string) => {
        const effectiveToken = targetToken || token;
        if (!effectiveToken) return;
        const headers = { Authorization: `Bearer ${effectiveToken}` };
        const [completionResponse, logResponse, retryResponse] = await Promise.all([
            fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/completions/my`, { headers, cache: 'no-store' }),
            fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/logs/my`, { headers, cache: 'no-store' }),
            fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/retry-queue/my`, { headers, cache: 'no-store' }),
        ]);
        if (completionResponse.ok) {
            setCompletions(toListPayload<CompletionItem>(await completionResponse.json()));
        }
        if (logResponse.ok) {
            setLogs(toListPayload<FeatureLogItem>(await logResponse.json()));
        }
        if (retryResponse.ok) {
            setRetryQueue(toListPayload<RetryQueueItem>(await retryResponse.json()));
        }
        const generatedProgramResponse = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/generated-programs/latest`, { headers, cache: 'no-store' });
        if (generatedProgramResponse.ok) {
            setGeneratedProgramSummary(await generatedProgramResponse.json());
        }
    }, [apiBaseUrl, token]);

    const replayRetryQueueItem = React.useCallback(async (queueItemId: number) => {
        if (!authHeaders) {
            setErrorText('로그인 후 재시도 큐를 다시 실행할 수 있습니다.');
            return;
        }
        setErrorText('');
        setResultText('');
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/retry-queue/my/${queueItemId}/replay`, {
                method: 'POST',
                headers: authHeaders,
            });
            const payload = await response.json().catch(() => null) as RetryReplayResponse | null;
            if (!response.ok) {
                throw new Error((payload as { detail?: string } | null)?.detail || '재시도 큐 재실행에 실패했습니다.');
            }
            setResultText(`재시도 큐 ${queueItemId}번을 다시 실행했습니다.${payload?.attempt_count != null ? ` (시도 ${payload.attempt_count})` : ''}`);
            await loadHistory();
        } catch (error: any) {
            setErrorText(error?.message || '재시도 큐 재실행 중 오류가 발생했습니다.');
        }
    }, [apiBaseUrl, authHeaders, loadHistory]);

    React.useEffect(() => {
        if (typeof window === 'undefined') return;
        const customerToken = localStorage.getItem(CUSTOMER_TOKEN_KEY) || '';
        const savedToken = customerToken || getAdminToken() || '';
        if (!savedToken) return;
        setToken(savedToken);
        loadMyInfo(savedToken).catch(() => {
            // customer token이 깨진 경우에만 제거하고, admin_token은 건드리지 않는다.
            if (customerToken && customerToken === savedToken) {
                localStorage.removeItem(CUSTOMER_TOKEN_KEY);
            }
            setToken('');
            setMe(null);
        });
        loadHistory(savedToken).catch(() => { });
    }, [loadHistory, loadMyInfo]);

    React.useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        const params = new URLSearchParams(window.location.search);
        const rail = (params.get('rail') || '').trim().toUpperCase();
        if (rail.startsWith('RAIL-')) {
            setSelectedEngineRailId(rail);
        }
    }, []);

    const handleSelectEngineRail = React.useCallback((railId: string) => {
        const normalizedRailId = String(railId || '').trim().toUpperCase();
        if (!normalizedRailId.startsWith('RAIL-')) {
            return;
        }
        setSelectedEngineRailId(normalizedRailId);
        if (typeof window !== 'undefined') {
            const url = new URL(window.location.href);
            url.searchParams.set('rail', normalizedRailId);
            window.history.replaceState({}, '', url.toString());
        }
    }, []);

    React.useEffect(() => {
        if (!authHeaders) {
            setEngineRails([]);
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/api/marketplace/extras/catalog`, {
                    headers: authHeaders,
                    cache: 'no-store',
                });
                if (!response.ok) {
                    if (!cancelled) {
                        setEngineRails([]);
                    }
                    return;
                }
                const payload = await response.json().catch(() => null) as {
                    slot_rails?: MarketplaceEngineRail[];
                    slot_checklist?: {
                        slot_rails?: MarketplaceEngineRail[];
                        slots?: MarketplaceSlotRow[];
                    };
                } | null;
                const rails = Array.isArray(payload?.slot_rails)
                    ? payload?.slot_rails
                    : Array.isArray(payload?.slot_checklist?.slot_rails)
                        ? payload?.slot_checklist?.slot_rails
                        : [];
                const slots = Array.isArray(payload?.slot_checklist?.slots)
                    ? payload.slot_checklist.slots
                    : [];
                if (!cancelled) {
                    setEngineRails(rails.slice(0, 6));
                    setEngineSlots(slots);
                    const hasSelectedRail = rails.some((rail) => rail.rail_id === selectedEngineRailId);
                    if (!hasSelectedRail && rails.length > 0) {
                        setSelectedEngineRailId(rails[0].rail_id);
                    }
                }
            } catch {
                if (!cancelled) {
                    setEngineRails([]);
                    setEngineSlots([]);
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl, authHeaders, selectedEngineRailId]);

    React.useEffect(() => {
        if (typeof window === 'undefined') return;
        try {
            const raw = localStorage.getItem(MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY);
            if (!raw) return;
            const payload = JSON.parse(raw) as MarketplaceOrchestratorBridgePayload;
            if (payload?.source === 'admin-llm') {
                const urlProductId = new URLSearchParams(window.location.search).get('product') || '';
                const bridgeTargetMatched = !payload.productId || payload.productId === selectedProduct.id || payload.productId === urlProductId;
                if (bridgeTargetMatched) {
                    setProjectName(payload.projectName || initialProjectName);
                    setTaskDraft(payload.task || initialTaskDraft);
                }
            }
            localStorage.removeItem(MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY);
        } catch {
        }
    }, [initialProjectName, initialTaskDraft, selectedProduct.id]);

    React.useEffect(() => {
        const checks = (activeStage?.substeps || []).reduce<Record<string, boolean>>((acc, item) => {
            acc[item.id] = Boolean(item.checked);
            return acc;
        }, {});
        setStageSubstepChecks(checks);
    }, [activeStage?.id]);

    const handleAuth = React.useCallback(async () => {
        setAuthLoading(true);
        setAuthMessage('');
        try {
            if (authMode === 'signup') {
                const signupResponse = await fetch(`${apiBaseUrl}/api/auth/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: username.trim(),
                        email: email.trim(),
                        password,
                        full_name: fullName.trim(),
                        member_type: memberType,
                        business_name: memberType === 'individual' ? null : businessName.trim(),
                        business_registration_number: memberType === 'individual' ? null : businessRegistrationNumber.trim(),
                        representative_name: memberType === 'corporation' ? representativeName.trim() : null,
                    }),
                });
                const signupPayload = await signupResponse.json().catch(() => null);
                if (!signupResponse.ok) {
                    throw new Error(signupPayload?.detail || '회원가입에 실패했습니다.');
                }
            }

            const formData = new URLSearchParams();
            formData.set('username', email.trim());
            formData.set('password', password);

            const loginResponse = await fetch(`${apiBaseUrl}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData.toString(),
            });
            const loginPayload = await loginResponse.json().catch(() => null);
            if (!loginResponse.ok || !loginPayload?.access_token) {
                throw new Error(loginPayload?.detail || '로그인에 실패했습니다.');
            }
            if (typeof window !== 'undefined') {
                localStorage.setItem(CUSTOMER_TOKEN_KEY, loginPayload.access_token);
            }
            setToken(loginPayload.access_token);
            await loadMyInfo(loginPayload.access_token);
            await loadHistory(loginPayload.access_token);
            setAuthMessage(authMode === 'signup' ? '회원가입과 로그인이 완료되었습니다.' : '로그인되었습니다.');
        } catch (error: any) {
            setAuthMessage(error?.message || '인증 처리 중 오류가 발생했습니다.');
        } finally {
            setAuthLoading(false);
        }
    }, [apiBaseUrl, authMode, businessName, businessRegistrationNumber, email, fullName, loadHistory, loadMyInfo, memberType, password, representativeName, username]);

    const createStageRun = React.useCallback(async () => {
        if (!authHeaders) {
            throw new Error('로그인 후 주문을 시작할 수 있습니다.');
        }
        const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders,
            },
            body: JSON.stringify({
                task: buildTask(selectedProduct, taskDraft, projectName),
                mode: 'full',
                project_name: projectName.trim() || selectedProduct.id,
            }),
        });
        const payload = await response.json().catch(() => null);
        if (!response.ok || !payload?.run_id) {
            throw new Error(payload?.detail || '고객 오케스트레이터 stage run 생성에 실패했습니다.');
        }
        setRunId(payload.run_id);
        setStageRun(payload);
        return payload.run_id as string;
    }, [apiBaseUrl, authHeaders, projectName, selectedProduct, taskDraft]);

    const submitOrchestration = React.useCallback(async () => {
        setSubmitLoading(true);
        setErrorText('');
        try {
            const effectiveRunId = runId || await createStageRun();
            const effectiveStageId = stageRun?.current_stage_id || 'ARCH-001';
            const acceptedResponse = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/accepted`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(authHeaders || {}),
                },
                body: JSON.stringify({
                    task: buildTask(selectedProduct, taskDraft, projectName),
                    mode: 'full',
                    project_name: projectName.trim() || selectedProduct.id,
                    stage_run_id: effectiveRunId,
                    stage_id: effectiveStageId,
                }),
            });
            const acceptedPayload = await acceptedResponse.json().catch(() => null) as { accepted?: boolean; stage_run?: SharedOrchestratorStageRun; message?: string } | null;
            if (!acceptedResponse.ok || !acceptedPayload?.accepted) {
                throw new Error((acceptedPayload as any)?.detail || '고객 오케스트레이터 접수에 실패했습니다.');
            }
            if (acceptedPayload.stage_run) {
                setStageRun(acceptedPayload.stage_run);
                setRunId(acceptedPayload.stage_run.run_id);
            }
            if (acceptedPayload.message) {
                setResultText(acceptedPayload.message);
            }

            const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(authHeaders || {}),
                },
                body: JSON.stringify({
                    task: buildTask(selectedProduct, taskDraft, projectName),
                    mode: 'full',
                    project_name: projectName.trim() || selectedProduct.id,
                    stage_run_id: effectiveRunId,
                    stage_id: effectiveStageId,
                }),
            });
            const streamText = await response.text();
            const resultEvent = streamText
                .split('\n\n')
                .map((chunk) => chunk.replace(/^data:\s*/gm, '').trim())
                .filter(Boolean)
                .map((chunk) => {
                    try {
                        return JSON.parse(chunk);
                    } catch {
                        return null;
                    }
                })
                .filter(Boolean)
                .find((item: any) => item?.event === 'result') as { payload?: CustomerOrchestrateResult } | undefined;
            const payload = resultEvent?.payload ?? null;
            if (!response.ok || !payload) {
                throw new Error('고객 오케스트레이터 스트림 실행에 실패했습니다.');
            }
            const result = payload.result || {};
            setResultText(result.final_output || result.completion_summary || '실행 결과가 준비되었습니다.');
            if (result.stage_run) {
                setStageRun(result.stage_run);
                setRunId(result.stage_run.run_id);
            } else {
                await refreshStageRun(effectiveRunId);
            }
            await loadHistory();
        } catch (error: any) {
            setErrorText(error?.message || '고객 오케스트레이터 실행 중 오류가 발생했습니다.');
        } finally {
            setSubmitLoading(false);
        }
    }, [apiBaseUrl, authHeaders, createStageRun, loadHistory, projectName, refreshStageRun, runId, selectedProduct, stageRun?.current_stage_id, taskDraft]);

    const updateStageStatus = React.useCallback(async (status: 'passed' | 'failed' | 'manual_correction') => {
        if (!runId || !stageRun?.current_stage_id || !authHeaders) return;
        setStageLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders,
                },
                body: JSON.stringify({
                    run_id: runId,
                    stage_id: stageRun.current_stage_id,
                    status,
                    note: stageNoteDraft,
                    manual_correction: status === 'manual_correction' ? stageNoteDraft : '',
                    substep_checks: stageSubstepChecks,
                    revision_note: stageRevisionNote,
                }),
            });
            const payload = await response.json().catch(() => null);
            if (!response.ok || !payload) {
                throw new Error(payload?.detail || '단계 상태 업데이트에 실패했습니다.');
            }
            setStageRun(payload);
            setStageNoteDraft('');
            setStageRevisionNote('');
            await loadHistory();
        } catch (error: any) {
            setErrorText(error?.message || '단계 상태 업데이트 중 오류가 발생했습니다.');
        } finally {
            setStageLoading(false);
        }
    }, [apiBaseUrl, authHeaders, loadHistory, runId, stageNoteDraft, stageRevisionNote, stageRun?.current_stage_id, stageSubstepChecks]);

    const sendStageChat = React.useCallback(async () => {
        const content = chatInput.trim();
        if (!content || !authHeaders) return;
        setChatLoading(true);
        setErrorText('');
        try {
            const userMessage: ConversationMessage = {
                role: 'user',
                speaker: '고객',
                content,
                timestamp: new Date().toISOString(),
                step_title: activeStage?.title,
            };
            const nextConversation = [...conversation, userMessage];
            setConversation(nextConversation);
            const response = await fetch(`${apiBaseUrl}/api/marketplace/customer-orchestrate/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders,
                },
                body: JSON.stringify({
                    task: buildTask(selectedProduct, taskDraft, projectName),
                    message: content,
                    conversation: nextConversation,
                    run_id: runId || undefined,
                    stage_id: stageRun?.current_stage_id || undefined,
                    project_name: projectName.trim() || selectedProduct.id,
                    companion_mode: 'hybrid',
                    conversation_mode: conversationTonePresetConfig.conversationMode,
                    multi_turn_enabled: true,
                    response_style: conversationTonePresetConfig.responseStyle,
                    tone_preset: conversationTonePreset,
                    max_tokens: 640,
                    output_dir: generatedProgramSummary?.output_dir || undefined,
                    project_memory: {
                        reverse_question_mode: reverseQuestionMode,
                        tone_preset: conversationTonePreset,
                        pending_tasks: [stageNoteDraft, stageRevisionNote].filter(Boolean),
                    },
                    context_tags: [
                        'customer-orchestrator',
                        'manual-10step',
                        'free-dialogue',
                        'reverse-question',
                        reverseQuestionModeConfig.tag,
                        conversationTonePresetConfig.tag,
                    ],
                }),
            });
            const data = await response.json().catch(() => null);
            if (!response.ok || !data) {
                throw new Error(data?.detail || '고객 협업 대화 호출에 실패했습니다.');
            }
            setConversation(Array.isArray(data.conversation) ? data.conversation : nextConversation);
            if (data.stage_chat?.pending_revision_note && content.startsWith('/revise')) {
                setStageRevisionNote((prev) => [prev, data.stage_chat.pending_revision_note].filter(Boolean).join('\n'));
            }
            if (content.startsWith('/pass')) {
                await updateStageStatus('passed');
            } else if (content.startsWith('/fix') || content.startsWith('/revise')) {
                await updateStageStatus('manual_correction');
            } else if (content.startsWith('/fail')) {
                await updateStageStatus('failed');
            } else if (content.startsWith('/verify') || content.startsWith('/resume')) {
                await refreshStageRun();
                await loadHistory();
            }
            setChatInput('');
        } catch (error: any) {
            setErrorText(error?.message || '고객 협업 대화 처리 중 오류가 발생했습니다.');
        } finally {
            setChatLoading(false);
        }
    }, [activeStage?.title, apiBaseUrl, authHeaders, chatInput, conversation, conversationTonePreset, conversationTonePresetConfig.conversationMode, conversationTonePresetConfig.responseStyle, conversationTonePresetConfig.tag, generatedProgramSummary?.output_dir, loadHistory, projectName, refreshStageRun, reverseQuestionMode, reverseQuestionModeConfig.tag, runId, selectedProduct, stageNoteDraft, stageRevisionNote, stageRun?.current_stage_id, taskDraft, updateStageStatus]);

    return (
        <div className="workspace-shell">
            {!terminalFocusedView && <MarketplaceLeftRail activeRailId="orchestrator" />}
            <main className="workspace-stage">
                <div className="min-h-screen bg-[#0b0f16] px-6 py-10 text-[#e6edf3]">
                    <div className={`mx-auto ${terminalFocusedView ? 'max-w-[980px]' : 'max-w-[1680px]'} space-y-6`}>
                        <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">오케스트레이터 터미널</p>
                                <h1 className={`${terminalFocusedView ? 'mt-2 text-3xl' : 'mt-3 text-5xl'} font-bold text-white`}>핵심 3모드 실행 콘솔</h1>
                                <p className={`${terminalFocusedView ? 'mt-3 max-w-[820px] text-sm leading-6' : 'mt-4 max-w-[1040px] text-xl leading-relaxed'} text-[#aab4c0]`}>
                                    기능 로직은 백그라운드에 유지하고, 화면은 주문 입력과 역질문 실행 중심으로만 압축합니다.
                                </p>
                            </div>
                            {!terminalFocusedView && <div className="flex flex-wrap gap-3">
                                <a
                                    href="/marketplace"
                                    onClick={(event) => {
                                        event.preventDefault();
                                        window.location.assign('/marketplace');
                                    }}
                                    className="rounded-2xl border border-[#30363d] bg-[#11161d] px-5 py-3 text-base font-semibold text-white no-underline"
                                >
                                    마켓플레이스로 돌아가기
                                </a>
                            </div>}
                        </div>

                        <div className="rounded-[24px] border border-[#25304a] bg-[#10182b] p-5">
                            {!terminalFocusedView && (
                                <>
                                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">오케스트레이터 핵심 사용법</p>
                                    <div className="mt-3 space-y-2 text-sm text-[#d2d9e3]">
                                        <p>1. 프로젝트명과 주문 내용을 입력합니다.</p>
                                        <p>2. 시작은 버튼 또는 `/run` 하나만 사용합니다.</p>
                                        <p>3. 카드 판정은 `/pass`, `/fix`, `/fail`로 처리합니다.</p>
                                        <p>4. 상태 확인은 `/verify`, 질문/수정은 `/ask`, `/search`, `/news`, `/revise`를 사용합니다.</p>
                                    </div>
                                </>
                            )}
                            <div className={`${terminalFocusedView ? 'rounded-2xl border border-[#25304a] bg-[#0f1523] p-4' : 'mt-4 rounded-2xl border border-[#25304a] bg-[#0f1523] p-4'}`}>
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-semibold text-white">터미널 핵심 3모드</p>
                                        {terminalFocusedView && <p className="mt-1 text-xs text-[#9fb0c2]">수동 상태 카드 없이 역질문 흐름만 유지합니다.</p>}
                                    </div>
                                    <span className="rounded-xl border border-[#2a7cff] px-3 py-2 text-xs font-semibold text-[#9ecbff]">기능만 표시</span>
                                </div>
                                <div className="mt-3 grid gap-2 md:grid-cols-3">
                                    {REVERSE_QUESTION_MODE_CONFIGS.map((mode) => {
                                        const active = mode.id === reverseQuestionMode;
                                        return (
                                            <button
                                                key={mode.id}
                                                type="button"
                                                onClick={() => setReverseQuestionMode(mode.id)}
                                                className={`rounded-xl border px-3 py-3 text-left transition ${active ? 'border-[#58c9ff] bg-[#112239] text-white' : 'border-[#2b3340] bg-[#0d1117] text-[#c9d1d9]'}`}
                                            >
                                                <p className="text-sm font-semibold">{mode.label}</p>
                                                <p className="mt-1 text-xs leading-5 opacity-90">{mode.description}</p>
                                            </button>
                                        );
                                    })}
                                </div>
                                <div className="mt-4 border-t border-[#2b3340] pt-4">
                                    <p className="text-sm font-semibold text-white">말투 강도</p>
                                    <p className="mt-2 text-xs text-[#9fb0c2]">
                                        버튼 선택 없이 오케스트레이터가 먼저 3종(자유대화/간결/실행형)을 질문하고, 답변에 따라 자동 확정합니다.
                                    </p>
                                </div>
                                <p className="mt-3 text-xs text-[#9fb0c2]">
                                    현재 모드: <span className="font-semibold text-[#d7f3ff]">{reverseQuestionModeConfig.label}</span> · 말투: <span className="font-semibold text-[#d7f3ff]">자동질문</span>
                                </p>
                            </div>
                        </div>

                        {!terminalFocusedView && (
                            <div className="rounded-[24px] border border-[#2a3a5f] bg-[#0f1728] p-5">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#7fd3ff]">120엔진 우측 6레일</p>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="rounded-xl border border-[#2f5ea8] px-3 py-1 text-xs font-semibold text-[#9ecbff]">
                                            {selectedEngineRail ? `${selectedEngineRail.rail_id} · ${selectedEngineRail.slot_start}-${selectedEngineRail.slot_end}` : '레일 대기'}
                                        </span>
                                        {selectedEngineRail && (
                                            <button
                                                type="button"
                                                disabled={smokeTestLoading}
                                                onClick={() => void runRailSmokeTest(selectedEngineRail.rail_id)}
                                                className="rounded-xl border border-[#4a8a4a] bg-[#0d2010] px-3 py-1 text-xs font-semibold text-[#56d364] disabled:opacity-50"
                                            >
                                                {smokeTestLoading ? '테스트 중…' : `▶ Smoke Test (${selectedEngineRail.rail_id})`}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className="mt-3 rounded-xl border border-[#30466f] bg-[#0b1322] p-3 text-xs text-[#c9d1d9]">
                                    <p className="font-semibold text-[#9ecbff]">사용 단계 가이드 (엔진 모델 활용 순서)</p>
                                    <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                                        <div className="rounded-lg border border-[#2a3348] bg-[#0a1220] px-2.5 py-2">
                                            <p className="font-semibold text-white">1) 문제 정의</p>
                                            <p className="mt-1 text-[11px] text-[#9fb0c2]">프로젝트 목표/입출력/제약을 명령어로 고정</p>
                                        </div>
                                        <div className="rounded-lg border border-[#2a3348] bg-[#0a1220] px-2.5 py-2">
                                            <p className="font-semibold text-white">2) 레일 선택</p>
                                            <p className="mt-1 text-[11px] text-[#9fb0c2]">튜브에서 슬롯 클릭 후, 해당 카드 용도 확인</p>
                                        </div>
                                        <div className="rounded-lg border border-[#2a3348] bg-[#0a1220] px-2.5 py-2">
                                            <p className="font-semibold text-white">3) 정식본 검증</p>
                                            <p className="mt-1 text-[11px] text-[#9fb0c2]">정식/배포 슬롯은 운영 시나리오 중심으로 확인하고, 일반 슬롯은 템플릿 검증을 수행</p>
                                        </div>
                                        <div className="rounded-lg border border-[#2a3348] bg-[#0a1220] px-2.5 py-2">
                                            <p className="font-semibold text-white">4) 파이프라인 조합</p>
                                            <p className="mt-1 text-[11px] text-[#9fb0c2]">통과 슬롯을 순차/병렬로 연결해 최종 결과 생성</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-3 rounded-xl border border-[#2a3a5f] bg-[#0a1220] p-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#7ab9ff]">튜브형 120엔진 맵 (6레일 x 20슬롯)</p>
                                        <p className="text-[11px] text-[#8ea3bd]">슬롯 클릭 시 해당 레일/카드로 이동합니다.</p>
                                    </div>
                                    {hoveredTubeSlot && (
                                        <div className="mt-2 rounded-lg border border-[#35507a] bg-[#0d182a] px-3 py-2 text-[11px] text-[#d2d9e3]">
                                            <p className="font-semibold text-[#9ecbff]">툴팁 · #{hoveredTubeSlot.slot} {hoveredTubeSlot.engineName}</p>
                                            <p className="mt-0.5 text-[#8fb0d4]">{hoveredTubeSlot.railId} · {hoveredTubeSlot.category} · {getCategoryUsageLabel(hoveredTubeSlot.category)}</p>
                                            <p className="mt-1 text-[#7ab9ff]">운영 입력 예시</p>
                                            <pre className="mt-0.5 whitespace-pre-wrap text-[10px] text-[#c9d1d9]">{hoveredTubeSlot.inputExample}</pre>
                                            <p className="mt-1 text-[#7ab9ff]">운영 출력 예시</p>
                                            <pre className="mt-0.5 whitespace-pre-wrap text-[10px] text-[#c9d1d9]">{hoveredTubeSlot.outputExample}</pre>
                                        </div>
                                    )}
                                    <div className="mt-3 space-y-3">
                                        {tubeRails.map(({ rail, slots, summary }) => (
                                            <div key={`tube-${rail.rail_id}`} className="rounded-lg border border-[#2a3348] bg-[#0b1320] px-3 py-2.5">
                                                <div className="mb-2 flex flex-wrap items-center gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleSelectEngineRail(rail.rail_id)}
                                                        className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${selectedEngineRailId === rail.rail_id ? 'border-[#58c9ff] bg-[#12314f] text-[#d7f3ff]' : 'border-[#35507a] bg-[#0f1e33] text-[#9ecbff]'}`}
                                                    >
                                                        {rail.rail_id}
                                                    </button>
                                                    <span className="text-[10px] text-[#9fb0c2]">슬롯 {rail.slot_start}-{rail.slot_end}</span>
                                                    <span className="text-[10px] text-[#6f88a8]">·</span>
                                                    <span className="text-[10px] text-[#8fb0d4]">{summary.join(', ') || 'general'}</span>
                                                    <div className="ml-auto flex items-center gap-1">
                                                        <span className="rounded border border-[#2a4a2a] bg-[#0a1a0a] px-1.5 py-0.5 text-[10px] font-semibold text-[#56d364]">
                                                            S {railLiveRates[rail.rail_id]?.smoke != null ? `${railLiveRates[rail.rail_id]?.smoke}%` : '-'}
                                                        </span>
                                                        <span className="rounded border border-[#2a3348] bg-[#0d1117] px-1.5 py-0.5 text-[10px] font-semibold text-[#7ab9ff]">
                                                            E {railLiveRates[rail.rail_id]?.experiment != null ? `${railLiveRates[rail.rail_id]?.experiment}%` : '-'}
                                                        </span>
                                                        <span className="rounded border border-[#3a2a00] bg-[#1f1400] px-1.5 py-0.5 text-[10px] font-semibold text-[#f0a000]">
                                                            P {railLiveRates[rail.rail_id]?.pipeline != null ? `${railLiveRates[rail.rail_id]?.pipeline}%` : '-'}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="relative overflow-x-auto pb-1">
                                                    <div className="absolute left-2 right-2 top-1/2 h-[2px] -translate-y-1/2 bg-gradient-to-r from-[#203656] via-[#2b4c79] to-[#203656]" />
                                                    <div className="relative flex min-w-max items-center gap-1.5">
                                                        {slots.map((slot) => {
                                                            const isActive = slot.slot === focusedSlotNumber || slot.slot === selectedEngineSlotRows[0]?.slot;
                                                            return (
                                                                <button
                                                                    key={`tube-slot-${slot.slot}`}
                                                                    type="button"
                                                                    onClick={() => {
                                                                        setFocusedSlotNumber(slot.slot);
                                                                        handleSelectEngineRail(rail.rail_id);
                                                                    }}
                                                                    onMouseEnter={() => {
                                                                        setHoveredTubeSlot({
                                                                            slot: slot.slot,
                                                                            railId: railIdBySlot[slot.slot] || rail.rail_id,
                                                                            engineName: slot.engine_name_ko || '엔진명 미정',
                                                                            category: slot.category || 'general',
                                                                            inputExample: slot.experiment_template_ko || slot.usage_description_ko || '예시 입력 미정',
                                                                            outputExample: getCategoryOutputExample(slot.category),
                                                                        });
                                                                    }}
                                                                    onMouseLeave={() => setHoveredTubeSlot((prev) => (prev?.slot === slot.slot ? null : prev))}
                                                                    title={`#${slot.slot} ${slot.engine_name_ko || ''}`}
                                                                    className={`rounded-full border px-2 py-1 text-[10px] font-semibold transition ${isActive ? 'border-[#56d364] bg-[#12381f] text-[#d7ffe1]' : 'border-[#2f4668] bg-[#0d182a] text-[#c8d3e4] hover:border-[#4f739f]'}`}
                                                                >
                                                                    {slot.slot}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {smokeTestResult && (
                                    <div className="mt-3 rounded-xl border border-[#2a4a2a] bg-[#0a1a0a] px-4 py-3 text-xs text-[#d2d9e3]">
                                        <p className="font-semibold text-[#56d364]">
                                            Smoke 결과 · {smokeTestResult.rail_id} — 통과 {smokeTestResult.passed ?? 0} / 실패 {smokeTestResult.failed ?? 0} · {smokeTestResult.pass_rate_pct ?? 0}%
                                        </p>
                                        <div className="mt-2 grid grid-cols-4 gap-1 sm:grid-cols-5 xl:grid-cols-10">
                                            {(smokeTestResult.results || []).map((r) => (
                                                <span
                                                    key={`smoke-${r.slot}`}
                                                    title={r.error || r.file || `slot ${r.slot}`}
                                                    className={`rounded px-1 py-0.5 text-center text-[10px] font-bold ${r.status === 'passed' ? 'bg-[#12381f] text-[#56d364]' : r.status === 'timeout' ? 'bg-[#3a2a00] text-[#f0a000]' : 'bg-[#2a0f0f] text-[#f85149]'}`}
                                                >
                                                    #{r.slot}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                                    {selectedEngineSlotRows.length === 0 ? (
                                        <p className="text-sm text-[#aab4c0]">선택된 레일 슬롯이 아직 없습니다.</p>
                                    ) : selectedEngineSlotRows.map((row) => {
                                        const official = isOfficialSlot(row);
                                        const launchResult = slotLaunchResults[row.slot];
                                        const isLoading = !!slotLaunchLoading[row.slot];
                                        const experimentResult = slotExperimentResults[row.slot];
                                        const experimentLoading = !!slotExperimentLoading[row.slot];
                                        const experimentInput = slotExperimentInputs[row.slot] ?? row.experiment_template_ko ?? '';
                                        const isFocused = row.slot === focusedSlotNumber;
                                        return (
                                            <div
                                                key={`slot-${row.slot}`}
                                                ref={(node) => {
                                                    slotCardRefs.current[row.slot] = node;
                                                }}
                                                className={`rounded-xl border px-3 py-2 text-xs text-[#d2d9e3] ${isFocused ? 'border-[#56d364] bg-[#0f1b14]' : 'border-[#2a3348] bg-[#0d1117]'}`}
                                            >
                                                {/* 카드 헤더 — 클릭 시 상세 확장 */}
                                                <button
                                                    type="button"
                                                    onClick={() => setExpandedSlotNumber((prev) => prev === row.slot ? null : row.slot)}
                                                    className="w-full text-left"
                                                >
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="min-w-0">
                                                            <p className="font-semibold text-white">
                                                                #{row.slot} · <span className="text-[#9ecbff]">{row.engine_name_ko || row.engine_id || 'UNASSIGNED'}</span>
                                                            </p>
                                                            <p className="mt-0.5 truncate text-[10px] text-[#6a8090]">{row.file || '파일 미할당'}</p>
                                                            <p className="mt-0.5 text-[10px] font-semibold text-[#7ab9ff]">{getCategoryUsageLabel(row.category)}</p>
                                                            <p className="mt-0.5 text-[10px] text-[#6a8a9a]">{row.category || 'general'} · {row.priority || 'P9'} · {row.slot_status || 'pending'}</p>
                                                            {official && <p className="mt-0.5 text-[10px] font-semibold text-[#56d364]">정식본 · 배포 가능 확정</p>}
                                                        </div>
                                                        <span className={`shrink-0 rounded border px-2 py-1 text-[11px] font-semibold ${expandedSlotNumber === row.slot ? 'border-[#2f6f45] bg-[#0d2015] text-[#56d364]' : 'border-[#2f5ea8] bg-[#0f1f36] text-[#9ecbff]'}`}>
                                                            {expandedSlotNumber === row.slot ? '▲ 상세 닫기' : '▼ 상세 보기'}
                                                        </span>
                                                    </div>
                                                </button>

                                                {/* 상세 확장 패널 — 클릭 시 열림 */}
                                                {expandedSlotNumber === row.slot && (() => {
                                                    const detail = getEngineDetail(row.category);
                                                    return (
                                                        <div className="mt-3 space-y-2 border-t border-[#2a3348] pt-3">
                                                            {/* 이 엔진이 하는 일 */}
                                                            <div className="rounded-lg border border-[#2a3a5f] bg-[#0a1322] px-2.5 py-2">
                                                                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#7ab9ff]">이 엔진이 하는 일</p>
                                                                <p className="mt-1 text-[11px] leading-5 text-[#d2d9e3]">{row.usage_description_ko || detail.description}</p>
                                                            </div>
                                                            {/* 입력 / 출력 */}
                                                            <div className="grid grid-cols-2 gap-2">
                                                                <div className="rounded-lg border border-[#1f4a2f] bg-[#0a1a0f] px-2 py-1.5">
                                                                    <p className="text-[10px] font-semibold text-[#56d364]">▶ 입력 형태</p>
                                                                    <p className="mt-0.5 text-[10px] leading-4 text-[#c9d1d9]">{detail.input}</p>
                                                                </div>
                                                                <div className="rounded-lg border border-[#3a2a00] bg-[#1a1200] px-2 py-1.5">
                                                                    <p className="text-[10px] font-semibold text-[#f0a000]">◀ 출력 형태</p>
                                                                    <p className="mt-0.5 text-[10px] leading-4 text-[#c9d1d9]">{detail.output}</p>
                                                                </div>
                                                            </div>
                                                            {/* 연결 순서 */}
                                                            <div className="rounded-lg border border-[#3a2f6a] bg-[#0d0f20] px-2.5 py-2">
                                                                <p className="text-[10px] font-semibold text-[#b48aff]">엔진 연결 순서</p>
                                                                <p className="mt-1 text-[10px] text-[#9fb0c2]"><span className="text-[#7ab9ff]">이전 단계:</span> {detail.upstream}</p>
                                                                <p className="mt-0.5 text-[10px] text-[#9fb0c2]"><span className="text-[#f0a000]">다음 단계:</span> {detail.downstream}</p>
                                                            </div>
                                                            {/* 프로그램 예시 */}
                                                            <div className="rounded-lg border border-[#2a3a5f] bg-[#090e18] px-2.5 py-2">
                                                                <p className="text-[10px] font-semibold text-[#9ecbff]">이 엔진으로 만들 수 있는 프로그램</p>
                                                                {detail.programs.map((prog, i) => (
                                                                    <p key={i} className="mt-0.5 text-[10px] text-[#c9d1d9]">▪ {prog}</p>
                                                                ))}
                                                            </div>
                                                            {/* 파이프라인에 추가 */}
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    setPipelineBlocks((prev) => {
                                                                        if (prev.some((b) => b.slot === row.slot)) return prev;
                                                                        return [...prev, {
                                                                            slot: row.slot,
                                                                            category: row.category || 'general',
                                                                            label: row.engine_name_ko || `슬롯 ${row.slot}`,
                                                                            template_override: row.experiment_template_ko || '',
                                                                        }];
                                                                    });
                                                                }}
                                                                className="w-full rounded-lg border border-[#3fb950] bg-[#071210] px-2 py-1.5 text-[11px] font-semibold text-[#56d364] hover:bg-[#0d2010]"
                                                            >
                                                                + 이 엔진을 파이프라인에 추가
                                                            </button>
                                                        </div>
                                                    );
                                                })()}
                                                <textarea
                                                    value={experimentInput}
                                                    onChange={(event) => setSlotExperimentInputs((prev) => ({ ...prev, [row.slot]: event.target.value }))}
                                                    placeholder={official ? '운영 템플릿이 자동 주입됩니다. 필요 시 배포 시나리오에 맞게 조정하세요' : '기본 템플릿이 자동 주입됩니다. 필요하면 수정하세요'}
                                                    rows={2}
                                                    className="mt-2 w-full rounded-lg border border-[#2a3348] bg-[#0b1320] px-2 py-1.5 text-[11px] text-[#d2d9e3]"
                                                />
                                                <p className="mt-1 text-[10px] text-[#7ab9ff]">{official ? '정식본 운영 시나리오 자동 주입됨 · 버튼으로 즉시 검증 가능' : '기본 실험 시나리오 자동 주입됨 · 버튼만 눌러 즉시 실험 가능'}</p>
                                                <button
                                                    type="button"
                                                    disabled={experimentLoading}
                                                    onClick={() => void runSlotExperiment(row)}
                                                    className="mt-2 w-full rounded-lg border border-[#1f6f45] bg-[#0d2010] px-2 py-1.5 text-[11px] font-semibold text-[#56d364] hover:bg-[#12381f] disabled:opacity-50"
                                                >
                                                    {experimentLoading ? (official ? '정식본 검증 실행 중…' : '실험 실행 중…') : (official ? '▶ 정식본 검증 실행' : '▶ 기능 실험 실행')}
                                                </button>
                                                {experimentResult && (
                                                    <div className="mt-1 rounded border border-[#2a3348] bg-[#0a1220] px-2 py-1.5">
                                                        <p className={`text-[10px] font-semibold ${experimentResult.status === 'ok' ? 'text-[#56d364]' : experimentResult.status === 'running' ? 'text-[#7ab9ff]' : 'text-[#f85149]'}`}>
                                                            {experimentResult.status === 'running' ? '실험 진행 중' : experimentResult.status}
                                                            {experimentResult.experiment_type ? ` · ${experimentResult.experiment_type}` : ''}
                                                            {experimentResult.callable ? ` · ${experimentResult.callable}` : ''}
                                                        </p>
                                                        {experimentResult.error && <p className="mt-1 text-[10px] text-[#f85149]">{experimentResult.error}</p>}
                                                        {experimentResult.message && <p className="mt-1 text-[10px] text-[#9fb0c2]">{experimentResult.message}</p>}
                                                        {experimentResult.output_preview != null && (
                                                            <pre className="mt-1 whitespace-pre-wrap text-[10px] text-[#c9d1d9]">{typeof experimentResult.output_preview === 'string' ? experimentResult.output_preview : JSON.stringify(experimentResult.output_preview, null, 2)}</pre>
                                                        )}
                                                    </div>
                                                )}
                                                <button
                                                    type="button"
                                                    disabled={isLoading}
                                                    onClick={() => void launchSlot(row)}
                                                    className="mt-2 w-full rounded-lg border border-[#2a7cff] bg-[#0f1e3a] px-2 py-1.5 text-[11px] font-semibold text-[#7ab9ff] hover:bg-[#112848] disabled:opacity-50"
                                                >
                                                    {isLoading ? '실행 중…' : '▶ 실행 (dry_run)'}
                                                </button>
                                                {launchResult && (
                                                    <p className={`mt-1 text-[10px] font-semibold ${launchResult.status === 'ok' || launchResult.status === 'passed' ? 'text-[#56d364]' : launchResult.status === 'running' ? 'text-[#7ab9ff]' : 'text-[#f85149]'}`}>
                                                        {launchResult.status === 'running' ? '…' : launchResult.status}{launchResult.message ? ` · ${launchResult.message}` : ''}{launchResult.error ? ` · ${launchResult.error}` : ''}
                                                    </p>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* ── R1~R6 레일 대표 슬롯 검증 데모 ──────────────────────────── */}
                        {!terminalFocusedView && (
                            <div className="rounded-[24px] border border-[#3a2f6a] bg-[#0d0f20] p-5">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#b48aff]">R1~R6 레일 대표 슬롯 검증 데모</p>
                                        <p className="mt-1 text-xs text-[#9a86cc]">각 레일(slot 1/21/41/61/81/101)에서 실험 템플릿을 자동 실행하는 화면 캡처용 검증 시나리오</p>
                                    </div>
                                    <button
                                        type="button"
                                        disabled={railDemoLoading}
                                        onClick={() => void runRailDemo()}
                                        className="rounded-xl border border-[#7c4aff] bg-[#120c2a] px-4 py-2 text-xs font-semibold text-[#b48aff] hover:bg-[#1a1040] disabled:opacity-50"
                                    >
                                        {railDemoLoading ? '검증 실행 중…' : '▶ 6레일 대표 슬롯 실험 실행'}
                                    </button>
                                </div>
                                {railDemoResult && (
                                    <div className="mt-4 space-y-3">
                                        <div className="flex flex-wrap gap-3 text-xs">
                                            <span className="rounded-xl bg-[#12381f] px-3 py-1 font-semibold text-[#56d364]">통과 {railDemoResult.passed}/{railDemoResult.total}</span>
                                            <span className={`rounded-xl px-3 py-1 font-semibold ${railDemoResult.failed > 0 ? 'bg-[#2a0f0f] text-[#f85149]' : 'bg-[#12381f] text-[#56d364]'}`}>
                                                실패 {railDemoResult.failed}
                                            </span>
                                            <span className="rounded-xl bg-[#0f1e3a] px-3 py-1 font-semibold text-[#7ab9ff]">통과율 {railDemoResult.pass_rate_pct}%</span>
                                        </div>
                                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                                            {railDemoResult.demo_results.map((entry) => (
                                                <div key={entry.rail_id} className={`rounded-xl border p-3 text-xs ${entry.passed ? 'border-[#1f4a2f] bg-[#0a1a0f]' : 'border-[#4a1f1f] bg-[#1a0a0a]'}`}>
                                                    <div className="flex items-center gap-2">
                                                        <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${entry.passed ? 'bg-[#12381f] text-[#56d364]' : 'bg-[#2a0f0f] text-[#f85149]'}`}>{entry.rail_id}</span>
                                                        <span className="font-semibold text-[#d2d9e3]">slot {entry.slot}</span>
                                                        <span className="text-[#9fb0c2]">{entry.category}</span>
                                                    </div>
                                                    <p className="mt-1 font-medium text-[#b48aff]">{entry.engine_name_ko}</p>
                                                    <p className="mt-1 truncate text-[10px] text-[#7ab9ff]">템플릿: {entry.experiment_template_ko.slice(0, 80)}</p>
                                                    <div className="mt-1.5 rounded border border-[#2a3348] bg-[#050a14] px-2 py-1.5">
                                                        <p className={`text-[10px] font-semibold ${entry.passed ? 'text-[#56d364]' : 'text-[#f85149]'}`}>
                                                            {entry.result.status}{entry.result.experiment_type ? ` · ${entry.result.experiment_type}` : ''}
                                                        </p>
                                                        {entry.result.error && <p className="mt-0.5 text-[10px] text-[#f85149]">{entry.result.error}</p>}
                                                        {entry.result.output_preview != null && (
                                                            <pre className="mt-1 max-h-24 overflow-y-auto whitespace-pre-wrap text-[10px] text-[#c9d1d9]">
                                                                {typeof entry.result.output_preview === 'string'
                                                                    ? entry.result.output_preview
                                                                    : JSON.stringify(entry.result.output_preview, null, 2)}
                                                            </pre>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ── 블럭 파이프라인 빌더 ──────────────────────────────────── */}
                        {!terminalFocusedView && (
                            <div className="rounded-[24px] border border-[#1f4a3a] bg-[#081510] p-5">
                                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#3fb950]">120엔진 블럭 파이프라인</p>
                                <p className="mt-1 text-xs text-[#7aba8a]">슬롯 번호를 추가해 엔진을 블럭으로 연결하고, 명령어 한 줄로 체인 실행합니다.</p>

                                <div className="mt-4 space-y-3">
                                    {/* 명령어 입력 */}
                                    <div>
                                        <label className="mb-1 block text-xs font-semibold text-[#9fb0c2]">사용자 명령어 (파이프라인 전체 입력)</label>
                                        <input
                                            value={pipelineCommand}
                                            onChange={(e) => setPipelineCommand(e.target.value)}
                                            placeholder="예: 한국어 텍스트를 분석하고 감정 기반 음악을 생성하라"
                                            className="w-full rounded-xl border border-[#1f4a3a] bg-[#0a1a0f] px-4 py-2.5 text-sm text-white placeholder-[#4a6a5a]"
                                        />
                                    </div>

                                    {/* 모드 선택 */}
                                    <div className="flex gap-2">
                                        {(['sequential', 'parallel'] as const).map((m) => (
                                            <button
                                                key={m}
                                                type="button"
                                                onClick={() => setPipelineMode(m)}
                                                className={`rounded-xl border px-3 py-1.5 text-xs font-semibold transition-colors ${pipelineMode === m ? 'border-[#3fb950] bg-[#0d2010] text-[#56d364]' : 'border-[#2a3348] bg-[#0d1117] text-[#9fb0c2]'}`}
                                            >
                                                {m === 'sequential' ? '순차 실행 (체인)' : '병렬 실행'}
                                            </button>
                                        ))}
                                        <span className="ml-auto self-center rounded-xl border border-[#2a3348] px-3 py-1.5 text-xs text-[#7ab9ff]">
                                            {pipelineBlocks.length}개 블럭
                                        </span>
                                    </div>

                                    {/* 블럭 추가 */}
                                    <div className="flex gap-2">
                                        <input
                                            value={pipelineBlockInput}
                                            onChange={(e) => setPipelineBlockInput(e.target.value)}
                                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addPipelineBlock(); } }}
                                            placeholder="슬롯 번호 입력 (1~120)"
                                            className="flex-1 rounded-xl border border-[#1f4a3a] bg-[#0a1a0f] px-3 py-2 text-sm text-white placeholder-[#4a6a5a]"
                                        />
                                        <button
                                            type="button"
                                            onClick={addPipelineBlock}
                                            className="rounded-xl border border-[#3fb950] bg-[#0d2010] px-4 py-2 text-xs font-semibold text-[#56d364] hover:bg-[#12381f]"
                                        >
                                            + 블럭 추가
                                        </button>
                                    </div>

                                    {/* 블럭 목록 */}
                                    {pipelineBlocks.length > 0 && (
                                        <div className="flex flex-wrap gap-2">
                                            {pipelineBlocks.map((block, idx) => (
                                                <div key={block.slot} className="flex items-center gap-1.5 rounded-xl border border-[#1f4a3a] bg-[#0a1a0f] px-3 py-1.5 text-xs">
                                                    <span className="font-bold text-[#3fb950]">#{idx + 1}</span>
                                                    <span className="text-[#9ecbff]">slot {block.slot}</span>
                                                    <span className="text-[#7aba8a]">{block.label}</span>
                                                    <span className="text-[#6a8a7a]">[{block.category}]</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => removePipelineBlock(block.slot)}
                                                        className="ml-1 text-[#f85149] hover:text-[#ff7b72]"
                                                    >
                                                        ✕
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* 형성될 프로그램 설명 */}
                                    {pipelineBlocks.length > 0 && (
                                        <div className="rounded-lg border border-[#3a2f6a] bg-[#0d0f20] px-3 py-2.5">
                                            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#b48aff]">이 조합으로 형성될 프로그램</p>
                                            <p className="mt-1 text-[11px] leading-5 text-[#d2d9e3]">{getProgramFormationDescription(pipelineBlocks)}</p>
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {[...new Set(pipelineBlocks.map((b) => b.category))].map((cat) => {
                                                    const detail = getEngineDetail(cat);
                                                    return (
                                                        <span key={cat} className="rounded border border-[#2a3a5f] bg-[#0a1322] px-1.5 py-0.5 text-[10px] text-[#9ecbff]">
                                                            {cat}: {detail.output.split(',')[0]}
                                                        </span>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* 실행 버튼 */}
                                    <button
                                        type="button"
                                        disabled={pipelineLoading || pipelineBlocks.length === 0}
                                        onClick={() => void runPipeline()}
                                        className="w-full rounded-xl border border-[#3fb950] bg-[#0d2010] px-4 py-3 text-sm font-bold text-[#56d364] hover:bg-[#12381f] disabled:opacity-40"
                                    >
                                        {pipelineLoading
                                            ? `파이프라인 실행 중… (${pipelineBlocks.length}개 블럭)`
                                            : `▶ 파이프라인 실행 (${pipelineMode === 'sequential' ? '순차 체인' : '병렬'} · ${pipelineBlocks.length}개 블럭)`}
                                    </button>

                                    {/* 파이프라인 결과 */}
                                    {pipelineResult && (
                                        <div className="rounded-xl border border-[#2a3348] bg-[#050a14] p-4 space-y-3">
                                            <div className="flex flex-wrap gap-2 text-xs">
                                                <span className={`rounded-xl px-3 py-1 font-semibold ${pipelineResult.status === 'ok' ? 'bg-[#12381f] text-[#56d364]' : pipelineResult.status === 'partial' ? 'bg-[#3a2a00] text-[#f0a000]' : 'bg-[#2a0f0f] text-[#f85149]'}`}>
                                                    {pipelineResult.status}
                                                </span>
                                                <span className="rounded-xl bg-[#0f1e3a] px-3 py-1 text-[#7ab9ff]">{pipelineResult.mode}</span>
                                                <span className="rounded-xl bg-[#0a1a0f] px-3 py-1 text-[#7aba8a]">통과 {pipelineResult.passed_blocks}/{pipelineResult.block_count}</span>
                                                <span className="rounded-xl bg-[#0d1020] px-3 py-1 text-[#9fb0c2]">ID: {pipelineResult.pipeline_id}</span>
                                            </div>

                                            {/* 블럭별 결과 */}
                                            <div className="space-y-2">
                                                {pipelineResult.block_results.map((br, idx) => (
                                                    <div key={`pipe-block-${idx}`} className={`rounded-lg border p-2 text-xs ${br.status === 'ok' ? 'border-[#1f4a2f] bg-[#0a1a0f]' : 'border-[#4a1f1f] bg-[#1a0a0a]'}`}>
                                                        <div className="flex items-center gap-2">
                                                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${br.status === 'ok' ? 'bg-[#12381f] text-[#56d364]' : 'bg-[#2a0f0f] text-[#f85149]'}`}>#{idx + 1}</span>
                                                            <span className="font-semibold text-white">slot {br.slot} · {br.label}</span>
                                                            <span className="text-[#7ab9ff]">[{br.category}]</span>
                                                            <span className={`ml-auto font-semibold ${br.status === 'ok' ? 'text-[#56d364]' : 'text-[#f85149]'}`}>{br.status}</span>
                                                        </div>
                                                        {br.experiment_type && <p className="mt-0.5 text-[10px] text-[#9fb0c2]">{br.experiment_type}</p>}
                                                        {br.error && <p className="mt-0.5 text-[10px] text-[#f85149]">{br.error}</p>}
                                                        {br.output_preview != null && (
                                                            <pre className="mt-1 max-h-20 overflow-y-auto whitespace-pre-wrap text-[10px] text-[#c9d1d9]">
                                                                {typeof br.output_preview === 'string' ? br.output_preview : JSON.stringify(br.output_preview, null, 2)}
                                                            </pre>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>

                                            {/* 최종 합성 결과 */}
                                            <div className="rounded-xl border border-[#3fb950] bg-[#071210] p-3">
                                                <p className="text-xs font-bold text-[#56d364]">▼ 최종 합성 출력</p>
                                                <pre className="mt-1.5 whitespace-pre-wrap text-xs text-[#c9d1d9]">{pipelineResult.final_output}</pre>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className={terminalFocusedView ? 'space-y-6' : 'grid gap-6 xl:grid-cols-[0.7fr_1.3fr]'}>
                            <section className="space-y-6">
                                {!terminalFocusedView && <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">선택 상품</p>
                                    <h2 className="mt-4 text-4xl font-bold text-white">{selectedProduct.title}</h2>
                                    <p className="mt-4 text-lg leading-8 text-[#aab4c0]">{selectedProduct.summary}</p>
                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <span className="rounded-full border border-[#30363d] bg-[#0d1117] px-4 py-2 text-sm text-[#d2d9e3]">{selectedProduct.category}</span>
                                        <span className="rounded-full border border-[#31c45d] px-4 py-2 text-sm font-bold text-[#31c45d]">{selectedProduct.price}</span>
                                    </div>
                                </div>}

                                <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="text-[11px] font-semibold tracking-[0.28em] text-[#58c9ff]">CODE GENERATOR</span>
                                        <p className="text-2xl font-bold text-white">마켓플레이스 오케스트레이터</p>
                                        <span className="rounded-full bg-[#12381f] px-2 py-1 text-[11px] text-[#3fb950]">Enter 실행형</span>
                                        {terminalFocusedView && <span className="rounded-full bg-[#0f2747] px-2 py-1 text-[11px] text-[#9ecbff]">기능만 표시</span>}
                                    </div>
                                    <p className="mt-2 text-xs text-[#8b949e]">로그인 후 프로젝트 설정과 주문 내용을 입력하면 오케스트레이터가 역질문식으로 바로 진행합니다.</p>
                                    <div className={`mt-4 grid gap-4 ${terminalFocusedView ? 'xl:grid-cols-[220px_1fr]' : ''}`}>
                                        <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-4">
                                            <div className="flex items-center justify-between gap-2">
                                                <p className="text-sm font-semibold text-white">회원 / 내정보</p>
                                                {me && <span className="rounded-full border border-[#31c45d] px-3 py-1 text-xs font-semibold text-[#31c45d]">로그인됨</span>}
                                            </div>
                                            {!me ? (
                                                <form
                                                    className="mt-4 space-y-3"
                                                    onSubmit={(event) => {
                                                        event.preventDefault();
                                                        void handleAuth();
                                                    }}
                                                >
                                                    <div className="flex gap-2 text-sm">
                                                        <button type="button" onClick={() => setAuthMode('login')} className={`rounded-xl px-4 py-2 ${authMode === 'login' ? 'bg-[#2a7cff] text-white' : 'bg-[#0d1117] text-[#c9d1d9]'}`}>로그인</button>
                                                        <button type="button" onClick={() => setAuthMode('signup')} className={`rounded-xl px-4 py-2 ${authMode === 'signup' ? 'bg-[#2a7cff] text-white' : 'bg-[#0d1117] text-[#c9d1d9]'}`}>회원가입</button>
                                                    </div>
                                                    <input id="orch-email" name="email" autoComplete={authMode === 'signup' ? 'email' : 'username'} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="이메일" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                    {authMode === 'signup' && (
                                                        <>
                                                            <input id="orch-username" name="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="사용자명" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                            <input id="orch-fullname" name="fullName" autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="이름 / 담당자명" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                            <select id="orch-membertype" name="memberType" value={memberType} onChange={(e) => setMemberType(e.target.value as CustomerMemberType)} className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white">
                                                                <option value="individual">개인</option>
                                                                <option value="sole_proprietor">개인사업자</option>
                                                                <option value="corporation">법인사업자</option>
                                                            </select>
                                                            {memberType !== 'individual' && (
                                                                <>
                                                                    <input id="orch-businessname" name="businessName" autoComplete="organization" value={businessName} onChange={(e) => setBusinessName(e.target.value)} placeholder={memberType === 'corporation' ? '법인명' : '상호명'} className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                                    <input id="orch-businessreg" name="businessRegistrationNumber" autoComplete="off" value={businessRegistrationNumber} onChange={(e) => setBusinessRegistrationNumber(e.target.value)} placeholder="사업자등록번호" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                                </>
                                                            )}
                                                            {memberType === 'corporation' && <input id="orch-repname" name="representativeName" autoComplete="name" value={representativeName} onChange={(e) => setRepresentativeName(e.target.value)} placeholder="대표자명" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />}
                                                        </>
                                                    )}
                                                    <input type="password" autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="비밀번호" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                                    <button type="submit" disabled={authLoading} className="w-full rounded-2xl bg-[#19c3f3] px-5 py-3 text-base font-bold text-[#041018]">
                                                        {authLoading ? '처리 중...' : authMode === 'signup' ? '회원가입 후 시작' : '로그인 후 시작'}
                                                    </button>
                                                    {authMessage && <p className="text-sm text-[#d2d9e3]">{authMessage}</p>}
                                                </form>
                                            ) : (
                                                <div className="mt-4 space-y-2 text-sm text-[#d2d9e3]">
                                                    <p>이메일: {me.email}</p>
                                                    <p>사용자명: {me.username}</p>
                                                    <p>가입 유형: {MEMBER_TYPE_LABELS[(me.member_type as CustomerMemberType) || 'individual']}</p>
                                                    {me.business_name && <p>사업자명/법인명: {me.business_name}</p>}
                                                    {me.business_registration_number && <p>사업자등록번호: {me.business_registration_number}</p>}
                                                    {me.representative_name && <p>대표자명: {me.representative_name}</p>}
                                                </div>
                                            )}
                                        </div>
                                        <div className="space-y-3">
                                            {sourceProjectTitle && (
                                                <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] px-4 py-3 text-sm text-[#d2d9e3]">
                                                    연결된 마켓 프로젝트: <span className="font-semibold text-white">{sourceProjectTitle}</span>
                                                </div>
                                            )}
                                            <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="프로젝트명" className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                            <textarea value={taskDraft} onChange={(e) => setTaskDraft(e.target.value)} rows={7} className="w-full rounded-xl border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-white" />
                                            <div className="flex flex-wrap gap-3">
                                                <button type="button" onClick={createStageRun} disabled={!token || submitLoading} className="rounded-2xl border border-[#30363d] bg-[#11161d] px-5 py-3 text-base font-semibold text-white">
                                                    단계 카드 시작
                                                </button>
                                                <button type="button" onClick={submitOrchestration} disabled={!token || submitLoading} className="rounded-2xl bg-[#2a7cff] px-5 py-3 text-base font-bold text-white">
                                                    {submitLoading ? '실행 중...' : '주문하기'}
                                                </button>
                                            </div>
                                            {errorText && <p className="text-sm text-[#ffb3ad]">{errorText}</p>}
                                        </div>
                                    </div>
                                </div>
                            </section>

                            <section className="space-y-6">
                                <OrchestratorStageCardPanel
                                    tone="customer"
                                    title="오케스트레이터 터미널"
                                    description={terminalFocusedView ? '주문 입력 이후에는 역질문과 핵심 카드 흐름만 유지합니다.' : '백그라운드 기능은 유지하고, 화면은 핵심 대화/카드 동작만 표시합니다.'}
                                    stageRun={stageRun}
                                    stageNoteDraft={stageNoteDraft}
                                    onStageNoteDraftChange={setStageNoteDraft}
                                    substepChecks={stageSubstepChecks}
                                    onSubstepChecksChange={setStageSubstepChecks}
                                    revisionNote={stageRevisionNote}
                                    onRevisionNoteChange={setStageRevisionNote}
                                    stageUpdateLoading={stageLoading}
                                    onMarkPassed={() => updateStageStatus('passed')}
                                    onMarkManualCorrection={() => updateStageStatus('manual_correction')}
                                    onMarkFailed={() => updateStageStatus('failed')}
                                    onRefresh={() => refreshStageRun()}
                                    operationalVerificationLabel="고객 stage run 새로고침"
                                    commandRules={terminalFocusedView ? [
                                        '주문 입력 후 역질문 답변을 이어가며 카드 흐름을 진행합니다.',
                                        '필요한 판정만 통과/보정/미통과로 표시하고 나머지 상태 카드는 숨깁니다.',
                                        '`/ask`, `/search`, `/news`, `/revise`만 핵심 명령으로 사용합니다.',
                                    ] : [
                                        '로그인 후 주문 입력을 작성하고 Enter 대신 주문하기 버튼으로 실행합니다.',
                                        '단계 카드 통과/보정/미통과는 고객이 직접 확인하며 다음 카드로 진행합니다.',
                                        '`/ask`, `/search`, `/news`는 동료처럼 질문/검색/주요뉴스 탐색을 수행합니다.',
                                        '`/revise`는 중간 설계 변경, `/resume`은 변경 반영 후 흐름 재개입니다.',
                                        '완료/로그/재시도 큐는 하단 이력 패널에서 즉시 확인합니다.',
                                    ]}
                                    conversation={conversation}
                                    chatInput={chatInput}
                                    onChatInputChange={setChatInput}
                                    chatLoading={chatLoading}
                                    onSubmitChat={sendStageChat}
                                />

                                {!compactUi && (
                                    <SharedOrchestratorFollowUpCard
                                        tone="customer"
                                        title="공통 후속 제안 카드"
                                        summary="고객 오케스트레이터도 관리자와 같은 기준으로 후속 제안과 우선순위를 표시합니다."
                                        scoreLabel="우선순위"
                                        scoreValue={customerHistoryStats.cumulativeScore}
                                        scoreAxes={[
                                            { id: 'severity', label: 'severity', score: customerFollowUpScore.axes.severity, detail: `publish readiness=${generatedProgramSummary?.publish_ready ? 'ready' : 'blocked'}`, tone: generatedProgramSummary?.publish_ready ? 'good' : 'warning' },
                                            { id: 'recency', label: 'recency', score: customerFollowUpScore.axes.recency, detail: `active stage=${activeStage?.status || 'idle'}`, tone: activeStage?.status === 'failed' ? 'warning' : 'neutral' },
                                            { id: 'approval_risk', label: 'approval_risk', score: customerFollowUpScore.axes.approvalRisk, detail: `approval history=${generatedProgramSummary?.approval_history_count ?? 0}건`, tone: (generatedProgramSummary?.approval_history_count ?? 0) > 0 ? 'warning' : 'good' },
                                            { id: 'hard_gate_impact', label: 'hard_gate_impact', score: customerFollowUpScore.axes.hardGateImpact, detail: `delivery gate=${generatedProgramSummary?.delivery_gate_blocked ? 'blocked' : 'open'}`, tone: generatedProgramSummary?.delivery_gate_blocked ? 'warning' : 'good' },
                                            { id: 'operational_risk', label: 'operational_risk', score: customerFollowUpScore.axes.operationalRisk, detail: `retry queue=${retryQueue.length}건`, tone: retryQueue.length > 0 ? 'warning' : 'good' },
                                            { id: 'self_run_priority', label: 'self_run_priority', score: customerFollowUpScore.axes.selfRunPriority, detail: `stage run=${generatedProgramSummary?.stage_run_status || 'unknown'}`, tone: (generatedProgramSummary?.stage_run_status === 'failed' || generatedProgramSummary?.stage_run_status === 'manual_correction') ? 'warning' : 'neutral' },
                                        ]}
                                        recommendations={customerFollowUpRecommendations}
                                        metrics={[
                                            { label: 'publish readiness', value: generatedProgramSummary?.publish_ready ? 'ready' : 'blocked', tone: generatedProgramSummary?.publish_ready ? 'good' : 'warning' },
                                            { label: 'delivery gate', value: generatedProgramSummary?.delivery_gate_blocked ? 'blocked' : 'open', tone: generatedProgramSummary?.delivery_gate_blocked ? 'warning' : 'good' },
                                            { label: 'retry queue', value: `${retryQueue.length}건`, tone: retryQueue.length > 0 ? 'warning' : 'good' },
                                            { label: 'active stage', value: activeStage?.status || 'idle', tone: activeStage?.status === 'failed' ? 'warning' : 'neutral' },
                                            { label: '누적 평균', value: `${customerHistoryStats.averageScore}점`, tone: customerHistoryStats.averageScore >= customerHistoryStats.latestScore ? 'warning' : 'good' },
                                            { label: '직전 대비', value: `${customerHistoryStats.momentum >= 0 ? '+' : ''}${customerHistoryStats.momentum}점`, tone: customerHistoryStats.momentum > 0 ? 'warning' : 'good' },
                                            { label: 'approval history', value: `${generatedProgramSummary?.approval_history_count ?? 0}건`, tone: (generatedProgramSummary?.approval_history_count ?? 0) > 0 ? 'warning' : 'good' },
                                            { label: 'stage run', value: generatedProgramSummary?.stage_run_status || 'unknown', tone: (generatedProgramSummary?.stage_run_status === 'failed' || generatedProgramSummary?.stage_run_status === 'manual_correction') ? 'warning' : 'neutral' },
                                        ]}
                                        trendPoints={[
                                            { label: '직전', value: customerHistoryStats.previousScore ?? customerHistoryStats.latestScore },
                                            { label: '현재', value: customerHistoryStats.latestScore },
                                            { label: '평균', value: customerHistoryStats.averageScore },
                                            { label: '피크', value: customerHistoryStats.peakScore },
                                        ]}
                                        actionLabel="주문하기"
                                        actionBusyLabel="실행 중..."
                                        actionDisabled={!token || submitLoading}
                                        onAction={() => void submitOrchestration()}
                                    />
                                )}

                                {(!terminalFocusedView || resultText || generatedProgramSummary) && <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                    <p className="text-lg font-semibold text-white">실행 결과</p>
                                    <pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-[#25304a] bg-[#0f1523] p-4 text-sm leading-7 text-[#d2d9e3]">{resultText || '아직 실행 결과가 없습니다.'}</pre>
                                    {generatedProgramSummary && (
                                        <div className="mt-4 rounded-2xl border border-[#25304a] bg-[#0f1523] p-4 text-sm text-[#d2d9e3]">
                                            <p className="font-semibold text-white">실프로그램 출고 요약</p>
                                            {generatedProgramSummary.output_dir && <p className="mt-2 break-all">출력 경로: {generatedProgramSummary.output_dir}</p>}
                                            {generatedProgramSummary.output_archive_path && <p className="break-all">출고 ZIP: {generatedProgramSummary.output_archive_path}</p>}
                                            <p>validation profile: {generatedProgramSummary.validation_profile || '-'}</p>
                                            <p>publish readiness: {generatedProgramSummary.publish_ready ? 'ready' : 'blocked'}</p>
                                            <p>shipping zip reproduction: {generatedProgramSummary.shipping_zip_ok ? 'pass' : 'fail'}</p>
                                            {!!generatedProgramSummary.publish_targets?.length && <p>publish targets: {generatedProgramSummary.publish_targets.join(', ')}</p>}
                                            {!!generatedProgramSummary.required_tests?.length && <p>required tests: {generatedProgramSummary.required_tests.join(', ')}</p>}
                                            {generatedProgramSummary.delivery_gate_message && <p className="text-[#ffb3ad]">gate: {generatedProgramSummary.delivery_gate_message}</p>}
                                        </div>
                                    )}
                                </div>}

                                {!compactUi && (
                                    <div className="grid gap-6 xl:grid-cols-3">
                                        <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                            <p className="text-lg font-semibold text-white">내 완료 이력</p>
                                            <div className="mt-4 space-y-3 text-sm text-[#d2d9e3]">
                                                {safeCompletions.length === 0 ? <p>완료 이력이 없습니다.</p> : safeCompletions.map((item) => (
                                                    <div key={item.id} className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-3">
                                                        <p className="font-semibold text-white">{item.project_name}</p>
                                                        <p>{item.mode} · 시도 {item.attempts}</p>
                                                        <p>{item.gate_passed ? '상품 기준 통과' : '보정 필요'}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                            <p className="text-lg font-semibold text-white">실행 로그</p>
                                            <div className="mt-4 space-y-3 text-sm text-[#d2d9e3]">
                                                {safeLogs.length === 0 ? <p>로그가 없습니다.</p> : safeLogs.map((item) => (
                                                    <div key={item.id} className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-3">
                                                        <p className="font-semibold text-white">{item.message}</p>
                                                        <p>{item.flow_id || '-'} / {item.step_id || '-'} / {item.action || '-'}</p>
                                                        <p>{item.status}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                                            <p className="text-lg font-semibold text-white">재시도 큐</p>
                                            <div className="mt-4 space-y-3 text-sm text-[#d2d9e3]">
                                                {safeRetryQueue.length === 0 ? <p>재시도 큐가 없습니다.</p> : safeRetryQueue.map((item) => (
                                                    <div key={item.id} className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-3">
                                                        <p className="font-semibold text-white">{item.queue_name}</p>
                                                        <p>{item.status} · 시도 {item.attempt_count || 0}</p>
                                                        <p>{item.last_error || '마지막 오류 없음'}</p>
                                                        <button
                                                            type="button"
                                                            onClick={() => void replayRetryQueueItem(item.id)}
                                                            className="mt-3 rounded-xl border border-[#2a7cff] px-3 py-2 text-xs font-semibold text-[#9ecbff]"
                                                        >
                                                            재시도 다시 실행
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </section>
                        </div>
                    </div>
                </div>
            </main>
            {!terminalFocusedView && (
                <MarketplaceRightRail
                    activeRailId={selectedEngineRailId}
                    engineRails={engineRails}
                    onRailSelect={handleSelectEngineRail}
                />
            )}
        </div>
    );
}
