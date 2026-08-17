'use client';

import Link from 'next/link';
import { resolveApiBaseUrl } from '@/lib/api';
import { ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS } from '@/lib/orchestrator-live-flow';
import {
    isAutonomousProgressSnapshot,
    ORCHESTRATOR_LIVE_PROGRESS_EVENT,
    ORCHESTRATOR_LIVE_PROGRESS_KEY,
    type OrchestratorLiveProgressSnapshot,
} from '@/lib/orchestrator-live-progress';
import { useEffect, useMemo, useRef, useState } from 'react';

const ADMIN_LLM_PRESET_TASK_KEY = 'admin_llm_preset_task_v1';
const MARKETPLACE_ORCHESTRATOR_PATH = '/marketplace/orchestrator';
const ORCHESTRATOR_STAGE_ORDER = ['DESIGN', 'PLAN', 'GENERATE', 'BUILD', 'TEST', 'REFLEXION', 'FIX', 'DONE'];

type RuntimeConfigSnapshot = {
    code_generation_strategy?: string;
    selected_profile?: string;
    model_routes?: Record<string, string>;
};

type OrchestratorPreset = {
    id: string;
    title: string;
    mode: string;
    task: string;
    description: string;
    accentClass: string;
};

type RuntimeModeRow = {
    mode: string;
    requestedPipeline: string;
    genericEffective: string;
    nextjsEffective: string;
    executionShape: string;
    parallelNote: string;
};

type ConversationRouteRow = {
    surface: string;
    requestedAgent: string;
    effectiveRoute: string;
    executionShape: string;
    note: string;
};

const ORCHESTRATOR_PRESETS: OrchestratorPreset[] = [
    {
        id: 'self-diagnosis',
        title: '자가진단',
        mode: 'review',
        description: '현재 오케스트레이터의 상태머신, DoD, 메모리, 동적 도구 권한의 누락/충돌을 진단',
        accentClass: 'bg-amber-500 hover:bg-amber-600',
        task: `오케스트레이터 자가진단 실행

1. 현재 detect_mode, pipeline, required_files, validation_profile, dod_targets 결정 흐름을 진단
2. FIX 이전 Reflexion 단계와 Root Cause Analysis 주입이 실제로 연결되는지 점검
3. knowledge/success_cases.json, knowledge/failed_cases.json, knowledge/runs 누적 구조를 점검
4. backend/llm/tools 동적 도구 생성/로드 권한과 보안 경계를 점검
5. 관리자 UI에서 orchestration_spec, state_history, apply_error 노출이 충분한지 점검
6. 문제점은 우선순위 순으로 정리하고 즉시 수정이 필요한 항목을 명확히 제안`,
    },
    {
        id: 'self-improvement',
        title: '자가개선',
        mode: 'full',
        description: '루프 품질과 재시도 품질을 높이기 위한 개선 항목을 구현 중심으로 적용',
        accentClass: 'bg-blue-600 hover:bg-blue-700',
        task: `오케스트레이터 자가개선 적용

1. planner가 mode, pipeline, required_files, validation_profile, dod_targets를 JSON으로 먼저 결정하도록 유지/보강
2. reviewer Root Cause Analysis를 다음 GENERATE 프롬프트 최상단에 강제 주입하도록 유지/보강
3. 동일 실패 반복을 줄이기 위한 Reflexion -> FIX -> GENERATE 흐름을 점검하고 개선
4. knowledge 경험 메모리 주입 품질을 개선해 유사 사례 재사용률을 높이기
5. 관리자 UI에서 적용 상태와 orchestration_spec를 명확하게 노출`,
    },
    {
        id: 'self-expansion',
        title: '자가확장',
        mode: 'plan',
        description: 'Python/FastAPI 외 React, Go, Rust, 도구 확장 시나리오까지 확장 계획 수립',
        accentClass: 'bg-emerald-600 hover:bg-emerald-700',
        task: `오케스트레이터 자가확장 계획 수립

1. Python/FastAPI 외 React/Next.js, Go, Rust 작업에서도 required_files와 validation_profile을 동적으로 설계하도록 확장
2. dynamic_python_tool을 기반으로 보안 점검기, 성능 점검기, API 테스트기 등 런타임 도구 확장 시나리오를 설계
3. 경험 메모리에서 프레임워크별 성공/실패 패턴을 분류 저장하는 구조를 제안
4. 관리자 UI에서 자가진단/자가개선/자가확장 3단계를 순차 실행할 수 있는 운영 흐름을 정리`,
    },
];

const CURRENT_RUNTIME_MERMAID = `flowchart TD
    A["Input<br/>orchestrate request"] --> B["mode=full 전수 검사 해석"]
    B --> C["planner spec resolve<br/>required_files / validation_profile / dod_targets"]
    C --> D["DESIGN"]
    D --> E["PLAN"]
    E --> F["GENERATE"]
    F --> G{"auto_apply?"}
    G -->|no| H["응답 반환"]
    G -->|yes| I["artifact write"]
    I --> J["required_files 검사"]
    J --> K{"필수 파일 충족?"}
    K -->|no| R["REFLEXION"]
    K -->|yes| L["structure_compliance 검사"]
    L --> M{"구조 적합?"}
    M -->|no| R
    M -->|yes| N["BUILD / TEST / DoD 검증"]
    N --> O{"검증 통과?"}
    O -->|no| R
    O -->|yes| P["completion_gate"]
    P --> Q{"fallback-only 없음?"}
    Q -->|no| R
    Q -->|yes| S["semantic_audit"]
    S --> T{"semantic_audit 통과?"}
    T -->|no| R
    T -->|yes| U["python_security_policy 조건부 검사"]
    U --> V["DONE"]
    R --> W["FIX"]
    W --> F`;

const RUNTIME_MODE_ROWS: RuntimeModeRow[] = [
    {
        mode: 'review',
        requestedPipeline: 'reviewer',
        genericEffective: 'reviewer',
        nextjsEffective: 'reviewer',
        executionShape: '순차 단일 단계',
        parallelNote: '병렬 분기 없음',
    },
    {
        mode: 'plan',
        requestedPipeline: 'planner',
        genericEffective: 'planner',
        nextjsEffective: 'planner',
        executionShape: '순차 단일 단계',
        parallelNote: '병렬 분기 없음',
    },
    {
        mode: 'code',
        requestedPipeline: 'planner -> coder',
        genericEffective: 'planner',
        nextjsEffective: 'planner',
        executionShape: '순차 단일 경량 흐름',
        parallelNote: '현재 auto_generator 기준으로 coder는 제거됨',
    },
    {
        mode: 'full',
        requestedPipeline: 'planner -> coder -> reviewer + validation gates',
        genericEffective: 'planner -> reasoner -> reviewer -> required_files -> structure -> completion_gate -> semantic_audit',
        nextjsEffective: 'planner -> reviewer -> required_files -> structure -> completion_gate -> semantic_audit',
        executionShape: '순차 다단계 전수 검사',
        parallelNote: '완료 판정은 생성이 아니라 검증 게이트 전체 통과 기준',
    },
    {
        mode: 'design',
        requestedPipeline: 'designer',
        genericEffective: 'planner -> reasoner (fallback)',
        nextjsEffective: 'designer',
        executionShape: '순차 단일 또는 fallback 2단계',
        parallelNote: 'designer는 nextjs_react 계열에서만 그대로 유지됨',
    },
    {
        mode: 'program_5step',
        requestedPipeline: 'reviewer -> planner -> reviewer -> coder -> planner -> designer -> coder -> coder -> reviewer',
        genericEffective: 'reviewer -> planner -> reviewer -> planner -> reviewer',
        nextjsEffective: 'reviewer -> planner -> reviewer -> planner -> designer -> reviewer',
        executionShape: '순차 다단계',
        parallelNote: '현재 코드상 진짜 async 병렬 fan-out 은 없고 designer도 조건부 포함',
    },
];

const CONVERSATION_ROUTE_ROWS: ConversationRouteRow[] = [
    {
        surface: '관리자 chat 기본값',
        requestedAgent: 'reasoner',
        effectiveRoute: 'reasoner 직접 응답',
        executionShape: '순차 단일 응답',
        note: '관리자 UI 기본 chat agent 가 reasoner 로 설정됨',
    },
    {
        surface: '관리자 voice 기본값',
        requestedAgent: 'reasoner',
        effectiveRoute: 'reasoner 직접 응답',
        executionShape: '순차 단일 응답',
        note: 'voice gateway 기본 agent 도 reasoner',
    },
    {
        surface: 'chat 요청이 chat agent 로 들어온 경우',
        requestedAgent: 'chat',
        effectiveRoute: '상황에 따라 reasoner 로 승격',
        executionShape: '순차 라우팅',
        note: 'research action implementation 성격이면 reasoner 로 재선택',
    },
    {
        surface: 'chat 요청이 non-reasoner 에이전트로 들어온 경우',
        requestedAgent: 'chat 또는 coder 등',
        effectiveRoute: 'reasoner 브리핑 생성 후 선택 에이전트 응답',
        executionShape: '선행 브리프 + 최종 응답의 2단계 순차',
        note: '병렬이 아니라 reasoner brief 가 먼저 생성됨',
    },
    {
        surface: '질문 연구 액션 보조 라우팅',
        requestedAgent: 'question research action',
        effectiveRoute: 'reasoner',
        executionShape: '순차 단일 응답',
        note: '현재 관리자 UI 기본값이 모두 reasoner',
    },
];

function encodeMermaidToBase64Url(input: string): string {
    const bytes = new TextEncoder().encode(input);
    let binary = '';
    for (let i = 0; i < bytes.length; i += 1) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/g, '');
}

type Props = {
    title?: string;
    defaultOpen?: boolean;
};

export default function OrchestratorFlowSection({
    title = '전수 검사 오케스트레이터 상세 순서도',
    defaultOpen = false,
}: Props) {
    const apiBaseUrl = resolveApiBaseUrl();
    const [renderError, setRenderError] = useState<string | null>(null);
    const [renderedSvg, setRenderedSvg] = useState('');
    const [selectedPresetId, setSelectedPresetId] = useState<string>('');
    const [liveSnapshot, setLiveSnapshot] = useState<OrchestratorLiveProgressSnapshot | null>(null);
    const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfigSnapshot | null>(null);
    const renderIdRef = useRef(
        `orchestrator-flow-${Math.random().toString(36).slice(2)}`,
    );

    useEffect(() => {
        const loadSnapshot = () => {
            try {
                const raw = localStorage.getItem(
                    ORCHESTRATOR_LIVE_PROGRESS_KEY,
                );
                if (!raw) {
                    setLiveSnapshot(null);
                    return;
                }
                const parsed = JSON.parse(raw) as OrchestratorLiveProgressSnapshot;
                if (!parsed || typeof parsed !== 'object') {
                    setLiveSnapshot(null);
                    return;
                }
                setLiveSnapshot(parsed);
            } catch {
                setLiveSnapshot(null);
            }
        };

        const handleSnapshotEvent = () => loadSnapshot();
        loadSnapshot();
        window.addEventListener('storage', handleSnapshotEvent);
        window.addEventListener(
            ORCHESTRATOR_LIVE_PROGRESS_EVENT,
            handleSnapshotEvent as EventListener,
        );
        const timer = window.setInterval(loadSnapshot, 1000);

        return () => {
            window.removeEventListener('storage', handleSnapshotEvent);
            window.removeEventListener(
                ORCHESTRATOR_LIVE_PROGRESS_EVENT,
                handleSnapshotEvent as EventListener,
            );
            window.clearInterval(timer);
        };
    }, []);

    useEffect(() => {
        let cancelled = false;

        const loadRuntimeConfig = async () => {
            try {
                const response = await fetch(
                    `${apiBaseUrl}/api/llm/runtime-config`,
                );
                if (!response.ok) {
                    return;
                }
                const payload = (await response.json()) as RuntimeConfigSnapshot;
                if (!cancelled) {
                    setRuntimeConfig(payload);
                }
            } catch {
                if (!cancelled) {
                    setRuntimeConfig(null);
                }
            }
        };

        loadRuntimeConfig();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl]);

    const applyPreset = (preset: OrchestratorPreset) => {
        try {
            localStorage.setItem(ADMIN_LLM_PRESET_TASK_KEY, JSON.stringify(preset));
            setSelectedPresetId(preset.id);
            window.location.href = MARKETPLACE_ORCHESTRATOR_PATH;
        } catch {
            setSelectedPresetId('');
        }
    };

    const mermaidImageUrl = useMemo(() => {
        try {
            const encoded = encodeMermaidToBase64Url(CURRENT_RUNTIME_MERMAID);
            return `https://mermaid.ink/img/${encoded}`;
        } catch {
            return '';
        }
    }, []);

    useEffect(() => {
        let cancelled = false;

        async function renderDiagram() {
            try {
                const mermaid = (await import('mermaid')).default;
                mermaid.initialize({
                    startOnLoad: false,
                    securityLevel: 'loose',
                    theme: 'default',
                    themeVariables: {
                        background: '#ffffff',
                        primaryColor: '#eff6ff',
                        primaryBorderColor: '#1d4ed8',
                        primaryTextColor: '#0f172a',
                        lineColor: '#475569',
                        clusterBkg: '#f8fafc',
                        clusterBorder: '#cbd5e1',
                    },
                    flowchart: {
                        htmlLabels: true,
                        curve: 'basis',
                    },
                });

                const { svg } = await mermaid.render(
                    renderIdRef.current,
                    CURRENT_RUNTIME_MERMAID,
                );

                if (!cancelled) {
                    setRenderedSvg(svg);
                    setRenderError(null);
                }
            } catch (error) {
                if (!cancelled) {
                    const message =
                        error instanceof Error
                            ? error.message
                            : '알 수 없는 Mermaid 렌더링 오류';
                    setRenderedSvg('');
                    setRenderError(message);
                }
            }
        }

        renderDiagram();

        return () => {
            cancelled = true;
        };
    }, []);

    const showAutonomousStages = isAutonomousProgressSnapshot(liveSnapshot);

    return (
        <section className="bg-white border rounded-xl p-5 mb-6">
            <details className="group" open={defaultOpen}>
                <summary className="flex cursor-pointer list-none items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                    <h2 className="text-lg font-semibold text-gray-900">🧭 {title}</h2>
                    <span className="text-xs text-gray-500">
                        full 모드 · validation gates · 상태머신 기준
                    </span>
                </summary>

                <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
                    <div className="flex flex-wrap items-center gap-3">
                        {ORCHESTRATOR_PRESETS.map((preset) => (
                            <button
                                key={preset.id}
                                type="button"
                                onClick={() => applyPreset(preset)}
                                className={`rounded-lg px-4 py-2 text-sm font-semibold text-white transition ${preset.accentClass}`}
                            >
                                {preset.title}
                            </button>
                        ))}
                    </div>
                    <Link
                        href={MARKETPLACE_ORCHESTRATOR_PATH}
                        className="mt-3 inline-flex rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-medium text-blue-700 no-underline"
                    >
                        고객 오케스트레이터 열기
                    </Link>
                    <div className="mt-3 grid gap-2 md:grid-cols-3">
                        {ORCHESTRATOR_PRESETS.map((preset) => (
                            <div
                                key={`${preset.id}-desc`}
                                className={`rounded-lg border px-3 py-2 text-xs ${selectedPresetId === preset.id ? 'border-blue-400 bg-white text-blue-900' : 'border-blue-100 bg-white/70 text-blue-800'}`}
                            >
                                <p className="font-semibold">{preset.title}</p>
                                <p className="mt-1 leading-5">{preset.description}</p>
                                <p className="mt-1 text-[11px] opacity-80">
                                    mode={preset.mode}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="mt-4 rounded-lg border border-violet-100 bg-violet-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="text-base font-semibold text-violet-950">
                                현재 런타임 기준점
                            </h3>
                            <p className="text-xs text-violet-800">
                                backend runtime-config 를 기준으로 현재 기본 전략과
                                모델 라우트를 함께 보여줍니다.
                            </p>
                        </div>
                        <div className="grid gap-2 text-xs md:grid-cols-2">
                            <div className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-violet-900">
                                <p className="text-[11px] text-violet-600">
                                    code_generation_strategy
                                </p>
                                <p className="font-semibold">
                                    {runtimeConfig?.code_generation_strategy || '확인 실패'}
                                </p>
                            </div>
                            <div className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-violet-900">
                                <p className="text-[11px] text-violet-600">
                                    selected_profile
                                </p>
                                <p className="font-semibold">
                                    {runtimeConfig?.selected_profile || '확인 실패'}
                                </p>
                            </div>
                            <div className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-violet-900">
                                <p className="text-[11px] text-violet-600">chat route</p>
                                <p className="font-semibold">
                                    {runtimeConfig?.model_routes?.chat || '-'}
                                </p>
                            </div>
                            <div className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-violet-900">
                                <p className="text-[11px] text-violet-600">
                                    reasoner route
                                </p>
                                <p className="font-semibold">
                                    {runtimeConfig?.model_routes?.reasoning || '-'}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-4 rounded-lg border border-emerald-100 bg-emerald-50 p-4">
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h3 className="text-base font-semibold text-emerald-900">
                                실시간 진행 상태
                            </h3>
                            <p className="text-xs text-emerald-800">
                                최근 실행 기준 단계 이력과 요청 pipeline 을 현재 순서도와
                                대조할 수 있습니다.
                            </p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                            <span
                                className={`rounded-full px-3 py-1 ${
                                    liveSnapshot?.progressSource === 'autonomous_sse'
                                        ? 'bg-emerald-700 text-white'
                                        : liveSnapshot?.progressSource === 'autonomous_ws' || liveSnapshot?.wsConnected
                                            ? 'bg-emerald-700 text-white'
                                            : liveSnapshot?.progressSource === 'autonomous_poll'
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-amber-100 text-amber-800'
                                }`}
                            >
                                {liveSnapshot?.progressSource === 'autonomous_sse'
                                    ? 'SSE 연결됨'
                                    : liveSnapshot?.progressSource === 'autonomous_ws' || liveSnapshot?.wsConnected
                                        ? 'WS 연결됨'
                                        : liveSnapshot?.progressSource === 'autonomous_poll'
                                            ? 'Poll'
                                            : '실시간 대기'}
                            </span>
                            <span
                                className={`rounded-full px-3 py-1 ${liveSnapshot?.status === 'success' ? 'bg-emerald-700 text-white' : liveSnapshot?.status === 'failed' ? 'bg-red-100 text-red-700' : liveSnapshot?.status === 'running' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200'}`}
                            >
                                {liveSnapshot?.status || 'idle'}
                            </span>
                        </div>
                    </div>
                    {liveSnapshot ? (
                        <>
                            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-xs text-gray-500">현재 단계</p>
                                    <p className="text-sm font-semibold text-emerald-900">
                                        {liveSnapshot.currentState || '대기'}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-xs text-gray-500">실행 모드</p>
                                    <p className="text-sm text-gray-900">
                                        {liveSnapshot.mode || '-'}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-xs text-gray-500">업데이트 시각</p>
                                    <p className="text-sm text-gray-900">
                                        {liveSnapshot.updatedAt
                                            ? new Date(
                                                liveSnapshot.updatedAt,
                                            ).toLocaleTimeString('ko-KR')
                                            : '-'}
                                    </p>
                                </div>
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-xs text-gray-500">run_id</p>
                                    <p className="break-all text-sm text-gray-900">
                                        {liveSnapshot.runId || '-'}
                                    </p>
                                </div>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {showAutonomousStages
                                    ? ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.map((stage) => {
                                        const completed = typeof liveSnapshot.stagesCompleted === 'number'
                                            && liveSnapshot.stagesCompleted >= stage.number;
                                        const current = liveSnapshot.stageNumber === stage.number
                                            || liveSnapshot.currentStage === stage.label;
                                        return (
                                            <span
                                                key={stage.id}
                                                className={`rounded-full border px-3 py-1 text-xs font-semibold ${current ? 'border-blue-600 bg-blue-600 text-white' : completed ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-gray-200 bg-white text-gray-500'}`}
                                            >
                                                {stage.number}단계
                                            </span>
                                        );
                                    })
                                    : ORCHESTRATOR_STAGE_ORDER.map((stage) => {
                                        const reached =
                                            liveSnapshot.stateHistory?.includes(stage);
                                        const current =
                                            liveSnapshot.currentState === stage;
                                        return (
                                            <span
                                                key={stage}
                                                className={`rounded-full border px-3 py-1 text-xs font-semibold ${current ? 'border-blue-600 bg-blue-600 text-white' : reached ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-gray-200 bg-white text-gray-500'}`}
                                            >
                                                {stage}
                                            </span>
                                        );
                                    })}
                            </div>
                            {showAutonomousStages && liveSnapshot.activeSubstep && (
                                <p className="mt-2 text-xs text-emerald-800">
                                    active substep: {liveSnapshot.activeSubstep}
                                </p>
                            )}
                            <div className="mt-3 grid gap-3 xl:grid-cols-2">
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-sm font-medium text-gray-700 mb-2">
                                        단계 이력
                                    </p>
                                    <p className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                                        {liveSnapshot.stateHistory?.join(' → ') ||
                                            '아직 단계 이벤트 없음'}
                                    </p>
                                    {liveSnapshot.pipeline?.length > 0 && (
                                        <p className="mt-2 text-xs text-gray-500">
                                            pipeline: {liveSnapshot.pipeline.join(' → ')}
                                        </p>
                                    )}
                                </div>
                                <div className="rounded-lg border border-emerald-100 bg-white p-3">
                                    <p className="text-sm font-medium text-gray-700 mb-2">
                                        최근 실시간 로그
                                    </p>
                                    <div className="max-h-48 space-y-2 overflow-auto">
                                        {liveSnapshot.logs?.slice(0, 8).map((log) => (
                                            <div
                                                key={log.id}
                                                className="rounded border border-gray-200 bg-gray-50 p-2"
                                            >
                                                <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-gray-500">
                                                    <span>
                                                        {log.event}
                                                        {log.stage
                                                            ? ` · ${log.stage}`
                                                            : ''}
                                                    </span>
                                                    <span>
                                                        {new Date(
                                                            log.timestamp,
                                                        ).toLocaleTimeString(
                                                            'ko-KR',
                                                        )}
                                                    </span>
                                                </div>
                                                <p className="text-xs whitespace-pre-wrap break-words text-gray-800">
                                                    {log.message}
                                                </p>
                                            </div>
                                        ))}
                                        {(!liveSnapshot.logs ||
                                            liveSnapshot.logs.length === 0) && (
                                                <p className="text-xs text-gray-500">
                                                    아직 수집된 실시간 로그가 없습니다.
                                                </p>
                                            )}
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <p className="text-sm text-emerald-900">
                            실행 중인 오케스트레이터 스냅샷이 아직 없습니다. 실행 후
                            이 영역이 자동으로 갱신됩니다.
                        </p>
                    )}
                </div>

                <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3">
                        <h3 className="text-base font-semibold text-slate-950">
                            생성 모드 런타임 표
                        </h3>
                        <p className="text-xs text-slate-600">
                            현재 기본 전략은 auto_generator 입니다. 아래 표는 mode
                            요청값과 profile 별 실효 파이프라인을 구분해서 보여줍니다.
                        </p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full border-collapse text-sm">
                            <thead>
                                <tr className="bg-slate-100 text-slate-700">
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        mode
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        요청 파이프라인
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        generic 기타 profile
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        nextjs_react
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        실행 형태
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        병렬 여부 메모
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {RUNTIME_MODE_ROWS.map((row) => (
                                    <tr key={row.mode} className="align-top text-slate-800">
                                        <td className="border border-slate-200 px-3 py-2 font-semibold">
                                            {row.mode}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.requestedPipeline}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.genericEffective}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.nextjsEffective}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.executionShape}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.parallelNote}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3">
                        <h3 className="text-base font-semibold text-slate-950">
                            대화 라우팅 런타임 표
                        </h3>
                        <p className="text-xs text-slate-600">
                            대화는 병렬 fan-out 이 아니라, 라우팅 또는 reasoner 선행
                            브리핑 뒤 최종 응답으로 이어지는 순차 구조입니다.
                        </p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full border-collapse text-sm">
                            <thead>
                                <tr className="bg-slate-100 text-slate-700">
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        surface
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        요청 agent
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        실효 경로
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        실행 형태
                                    </th>
                                    <th className="border border-slate-200 px-3 py-2 text-left">
                                        메모
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {CONVERSATION_ROUTE_ROWS.map((row) => (
                                    <tr
                                        key={row.surface}
                                        className="align-top text-slate-800"
                                    >
                                        <td className="border border-slate-200 px-3 py-2 font-semibold whitespace-pre-wrap">
                                            {row.surface}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.requestedAgent}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.effectiveRoute}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.executionShape}
                                        </td>
                                        <td className="border border-slate-200 px-3 py-2 whitespace-pre-wrap">
                                            {row.note}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-sm font-medium text-gray-700 mb-2">
                            Mermaid 원문
                        </p>
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap overflow-auto max-h-80">
                            {CURRENT_RUNTIME_MERMAID}
                        </pre>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-sm font-medium text-gray-700 mb-2">
                            이미지 미리보기
                        </p>
                        {renderedSvg ? (
                            <div
                                className="w-full overflow-auto rounded border border-gray-200 bg-white p-2"
                                dangerouslySetInnerHTML={{ __html: renderedSvg }}
                            />
                        ) : (
                            <div className="text-xs text-gray-500 space-y-1">
                                <p>
                                    {renderError
                                        ? `Mermaid 인라인 렌더링에 실패했습니다: ${renderError}`
                                        : '다이어그램을 렌더링하는 중입니다.'}
                                </p>
                                {mermaidImageUrl ? (
                                    <a
                                        href={mermaidImageUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-blue-600 underline"
                                    >
                                        새 탭에서 다이어그램 열기
                                    </a>
                                ) : (
                                    <p>왼쪽 Mermaid 원문으로 렌더링하세요.</p>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </details>
        </section>
    );
}