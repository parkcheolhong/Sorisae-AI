'use client';

import React from 'react';

interface RuntimeConfigPanelProps {
    data: {
        runtimeEditorOpen: boolean;
        runtimeDraft: any;
        runtimeLoading: boolean;
        runtimeSaving: boolean;
        orchestratorSystemSaving: boolean;
        runtimeMessage: string;
        runtimeConfig: any;
        quantCompareLoading: boolean;
        quantCompareMessage: string;
        quantCompareSummary: any;
        orchestratorSystemLoading: boolean;
        orchestratorSystemSettings: any;
        orchestratorSystemMessage: string;
        orchestratorSystemOpen: Record<string, boolean>;
    };
    actions: {
        toggleEditor: () => void;
        refresh: () => void;
        saveRuntime: () => void;
        saveSystem: () => void;
        applyModelTuningLevel: (level: number) => void;
        applyTokenTuningLevel: (level: number) => void;
        applyTimeoutTuningLevel: (level: number) => void;
        updateRuntimeField: (field: string, value: string) => void;
        updateRuntimeToggle: (field: string, value: boolean) => void;
        updateAdvisoryToggle: (field: string, value: boolean) => void;
        updateAdvisoryNumeric: (field: string, value: string) => void;
        applyRuntimeProfile: (profile: any) => void;
        applyFeaturedModelAction: (row: any, action: any) => void;
        applyFunctionalModelGrade: (row: any, grade: any) => void;
        fetchLatestQuantCompareSummary: () => void;
        updateRuntimeModelRoute: (...args: any[]) => void;
        updateGlobalExecutionPreference: (enabled: boolean) => void;
        updateGlobalExecutionNumeric: (...args: any[]) => void;
        updateRuntimeExecutionMode: (...args: any[]) => void;
        updateRuntimeExecutionNumeric: (...args: any[]) => void;
        loadOrchestratorSystemSettings: () => void;
        toggleOrchestratorSystemSection: (sectionId: string) => void;
        updateOrchestratorSystemSettingValue: (fieldKey: string, value: string) => void;
    };
    helpers: {
        runtimeTuningLevels: readonly number[];
        runtimeFields: Array<[string, string]>;
        defaultAdvisoryControls: any;
        modelGradeRows: any[];
        getMissingGradeModels: (availableModels: string[], targets: Record<string, string>) => string[];
        isGradeActive: (modelRoutes: Record<string, string>, targets: Record<string, string>) => boolean;
        codingQ4Tag: string;
        codingQ5Tag: string;
        codingQ6Tag: string;
        codingQ8Tag: string;
        formatMetricNumber: (value: number | null, digits?: number, suffix?: string) => string;
        modelRouteFields: Array<[string, string]>;
        runtimePolicyHints: Record<string, string>;
        executionModeLabels: Record<string, string>;
        resolveHybridExecutionNumGpu: (control?: any) => number | string;
    };
}

export default function RuntimeConfigPanel({ data, actions, helpers }: RuntimeConfigPanelProps) {
    const runtimeDraft = data.runtimeDraft;
    const advisoryDraft = {
        ...helpers.defaultAdvisoryControls,
        ...(runtimeDraft?.advisory_controls || {}),
    };
    const runtimeSectionCards = [
        {
            id: 'runtime-limits',
            title: '핵심 런타임 제한',
            summary: '토큰, 단계 시간, 전체 작업 시간, 포렌식 출력량을 즉시 수정합니다.',
            accent: 'border-[#1f6feb] bg-[#0f2747] text-[#9ecbff]',
        },
        {
            id: 'advisory-controls',
            title: '대화 / 추론 보조',
            summary: '보충 질문, 근거 패널, 과학적 추론, 시스템 사고를 기능별로 고정 관리합니다.',
            accent: 'border-[#238636] bg-[#132a1b] text-[#9be9a8]',
        },
        {
            id: 'model-grades',
            title: '기능별 모델 묶음',
            summary: '협업 대화, 추론, 코딩, 리뷰, 디자인 라우트를 기능군별로 묶어서 제어합니다.',
            accent: 'border-[#8957e5] bg-[#1f1630] text-[#d2a8ff]',
        },
        {
            id: 'execution-policy',
            title: '실행 정책',
            summary: 'GPU/CPU 우선, num_gpu, num_thread 를 전역 및 라우트별로 관리합니다.',
            accent: 'border-[#d29922] bg-[#2d210f] text-[#f2cc60]',
        },
        {
            id: 'system-settings',
            title: '전역 환경값',
            summary: '오케스트레이터 전역값과 시스템 설정을 같은 패널에서 확인·저장합니다.',
            accent: 'border-[#6e7681] bg-[#161b22] text-[#c9d1d9]',
        },
    ];
    const advisoryToggleFields: Array<[string, string]> = [
        ['clarification_questions_enabled', '보충 질문 활성화'],
        ['evidence_panel_enabled', '근거 패널 활성화'],
        ['next_action_suggestions_enabled', '다음 행동 제안 활성화'],
        ['scientific_reasoning_enabled', '과학적 추론 활성화'],
        ['systems_thinking_enabled', '시스템 사고 활성화'],
        ['future_tech_expansion_enabled', '미래 기술 확장 활성화'],
        ['cross_domain_synthesis_enabled', '교차 도메인 종합 활성화'],
        ['innovation_scenarios_enabled', '혁신 시나리오 활성화'],
    ];
    const advisoryNumericFields: Array<[string, string]> = [
        ['max_clarification_questions', '최대 보충 질문 수'],
        ['max_evidence_items', '최대 근거 항목 수'],
        ['max_next_actions', '최대 다음 행동 수'],
        ['max_innovation_scenarios', '최대 혁신 시나리오 수'],
        ['max_system_design_alternatives', '최대 시스템 설계 대안 수'],
    ];
    const summaryText = `현재 실행 요청 토큰: ${runtimeDraft?.default_request_max_tokens ?? '-'}${runtimeDraft?.selected_profile ? ` · 선택 프로필: ${runtimeDraft.selected_profile}` : ''}${data.runtimeConfig ? ` · 저장 위치: ${data.runtimeConfig.config_path}` : ''}`;
    const modelRoutes = runtimeDraft?.model_routes || {};
    const executionControls = runtimeDraft?.execution_controls || {};

    return (
        <div className="mb-6 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-[#58a6ff]">관리자 제한값 직접 수정</h2>
                    <p className="text-xs text-[#8b949e]">토큰, 단계 시간, 전체 작업 시간, 포렌식 출력량을 여기서 바로 바꾸고 즉시 적용합니다.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <button type="button" onClick={actions.toggleEditor} className="rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-2 text-xs text-[#e6edf3]">
                        {data.runtimeEditorOpen ? '접기' : '펼치기'}
                    </button>
                    <button type="button" onClick={actions.refresh} disabled={data.runtimeLoading} className="rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-2 text-xs text-[#e6edf3]">
                        {data.runtimeLoading ? '불러오는 중...' : '현재값 다시 불러오기'}
                    </button>
                </div>
            </div>
            <div className="mb-4 grid gap-3 xl:grid-cols-5">
                {runtimeSectionCards.map((section) => (
                    <div key={section.id} className={`rounded-xl border px-4 py-3 ${section.accent}`}>
                        <p className="text-sm font-semibold">{section.title}</p>
                        <p className="mt-2 text-xs leading-5 opacity-90">{section.summary}</p>
                    </div>
                ))}
            </div>
            {data.runtimeEditorOpen && runtimeDraft && (
                <div className="space-y-4">
                    <div className="grid gap-4 xl:grid-cols-2">
                        <div className="rounded-lg border border-[#1f6feb] bg-[#0d1117] p-4">
                            <div className="mb-3">
                                <h3 className="text-sm font-semibold text-[#e6edf3]">핵심 런타임 제한값</h3>
                                <p className="mt-1 text-xs text-[#8b949e]">토큰, 시간 제한, 포렌식 범위를 이 패널에서 즉시 수정합니다.</p>
                            </div>
                            <div className="grid gap-3 md:grid-cols-2">
                                {helpers.runtimeFields.map(([field, label]) => (
                                    <label key={field} className="block">
                                        <span className="mb-1 block text-xs text-[#8b949e]">{label}</span>
                                        <input
                                            type="number"
                                            value={runtimeDraft?.[field] ?? ''}
                                            onChange={(e) => actions.updateRuntimeField(field, e.target.value)}
                                            className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                                        />
                                    </label>
                                ))}
                            </div>
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                                <label className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-3 text-sm text-[#e6edf3]">
                                    <input
                                        type="checkbox"
                                        checked={!!runtimeDraft?.force_complete}
                                        onChange={(e) => actions.updateRuntimeToggle('force_complete', e.target.checked)}
                                    />
                                    completion gate 강제 유지
                                </label>
                                <label className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-3 text-sm text-[#e6edf3]">
                                    <input
                                        type="checkbox"
                                        checked={!!runtimeDraft?.allow_synthetic_fallback}
                                        onChange={(e) => actions.updateRuntimeToggle('allow_synthetic_fallback', e.target.checked)}
                                    />
                                    synthetic fallback 허용
                                </label>
                                <label className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-3 text-sm text-[#e6edf3] md:col-span-2">
                                    <input
                                        type="checkbox"
                                        checked={runtimeDraft?.gpu_only_preferred !== false}
                                        onChange={(e) => actions.updateRuntimeToggle('gpu_only_preferred', e.target.checked)}
                                    />
                                    GPU 우선 경로 유지
                                </label>
                            </div>
                        </div>

                        <div className="rounded-lg border border-[#238636] bg-[#0d1117] p-4">
                            <div className="mb-3">
                                <h3 className="text-sm font-semibold text-[#e6edf3]">Advisory control</h3>
                                <p className="mt-1 text-xs text-[#8b949e]">관리자 협업형 오케스트레이터의 질문, 근거, 과학적 추론, 시스템 사고, 미래 기술 확장 수준을 직접 노출합니다.</p>
                            </div>
                            <div className="grid gap-3">
                                {advisoryToggleFields.map(([field, label]) => (
                                    <label key={field} className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-3 text-sm text-[#e6edf3]">
                                        <input
                                            type="checkbox"
                                            checked={!!advisoryDraft[field]}
                                            onChange={(e) => actions.updateAdvisoryToggle(field, e.target.checked)}
                                        />
                                        {label}
                                    </label>
                                ))}
                            </div>
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                                {advisoryNumericFields.map(([field, label]) => (
                                    <label key={field} className="block">
                                        <span className="mb-1 block text-xs text-[#8b949e]">{label}</span>
                                        <input
                                            type="number"
                                            value={advisoryDraft[field] ?? ''}
                                            onChange={(e) => actions.updateAdvisoryNumeric(field, e.target.value)}
                                            className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                                        />
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="rounded-lg border border-[#8957e5] bg-[#0d1117] p-4">
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-[#e6edf3]">튜닝 프리셋 고정 패널</h3>
                                <p className="mt-1 text-xs text-[#8b949e]">모델, 토큰, timeout 레벨을 기능별 운영 기준으로 빠르게 고정합니다.</p>
                            </div>
                            <span className="rounded-full border border-[#30363d] bg-[#161b22] px-2 py-1 text-[11px] text-[#c9d1d9]">
                                현재 profile {runtimeDraft?.selected_profile || '-'}
                            </span>
                        </div>
                        <div className="grid gap-4 xl:grid-cols-3">
                            <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                                <div className="mb-2 flex items-center justify-between">
                                    <span className="text-xs font-semibold text-[#79c0ff]">모델 튜닝</span>
                                    <span className="text-xs text-[#8b949e]">현재 {runtimeDraft?.model_tuning_level ?? 0}</span>
                                </div>
                                <div className="flex gap-2">
                                    {helpers.runtimeTuningLevels.map((level) => (
                                        <button
                                            key={`model-${level}`}
                                            type="button"
                                            onClick={() => actions.applyModelTuningLevel(level)}
                                            className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${String(runtimeDraft?.model_tuning_level ?? 0) === String(level) ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#e6edf3]'}`}
                                        >
                                            {level}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                                <div className="mb-2 flex items-center justify-between">
                                    <span className="text-xs font-semibold text-[#79c0ff]">토큰 튜닝</span>
                                    <span className="text-xs text-[#8b949e]">현재 {runtimeDraft?.token_tuning_level ?? 0}</span>
                                </div>
                                <div className="flex gap-2">
                                    {helpers.runtimeTuningLevels.map((level) => (
                                        <button
                                            key={`token-${level}`}
                                            type="button"
                                            onClick={() => actions.applyTokenTuningLevel(level)}
                                            className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${String(runtimeDraft?.token_tuning_level ?? 0) === String(level) ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#e6edf3]'}`}
                                        >
                                            {level}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                                <div className="mb-2 flex items-center justify-between">
                                    <span className="text-xs font-semibold text-[#79c0ff]">Timeout 튜닝</span>
                                    <span className="text-xs text-[#8b949e]">현재 {runtimeDraft?.timeout_tuning_level ?? 0}</span>
                                </div>
                                <div className="flex gap-2">
                                    {helpers.runtimeTuningLevels.map((level) => (
                                        <button
                                            key={`timeout-${level}`}
                                            type="button"
                                            onClick={() => actions.applyTimeoutTuningLevel(level)}
                                            className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${String(runtimeDraft?.timeout_tuning_level ?? 0) === String(level) ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#e6edf3]'}`}
                                        >
                                            {level}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-lg border border-[#a371f7] bg-[#0d1117] p-4">
                        <div className="mb-3">
                            <h3 className="text-sm font-semibold text-[#e6edf3]">기능별 모델 고정 패널</h3>
                            <p className="mt-1 text-xs text-[#8b949e]">협업 대화, 추론, 코딩, 리뷰, 디자인을 각 기능군 카드로 나눠 즉시 고정합니다.</p>
                        </div>
                        <div className="grid gap-4 xl:grid-cols-2">
                            {helpers.modelGradeRows.map((row) => (
                                <div key={row.key} className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <h4 className="text-sm font-semibold text-[#e6edf3]">{row.title}</h4>
                                            <p className="mt-1 text-xs text-[#8b949e]">{row.description}</p>
                                        </div>
                                        <span className="rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-1 text-[11px] text-[#c9d1d9]">
                                            route {row.routeKeys.length}
                                        </span>
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {row.grades.map((grade: any) => (
                                            <button
                                                key={`${row.key}-${grade.key}`}
                                                type="button"
                                                onClick={() => actions.applyFunctionalModelGrade(row, grade)}
                                                className={`rounded-lg px-3 py-2 text-xs font-semibold ${helpers.isGradeActive(modelRoutes, grade.targets) ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#e6edf3]'}`}
                                            >
                                                {grade.label}
                                            </button>
                                        ))}
                                        {row.featuredAction && (
                                            <button
                                                type="button"
                                                onClick={() => actions.applyFeaturedModelAction(row, row.featuredAction)}
                                                className="rounded-lg border border-[#8957e5] bg-[#23163a] px-3 py-2 text-xs font-semibold text-[#d2a8ff]"
                                            >
                                                {row.featuredAction.label}
                                            </button>
                                        )}
                                    </div>
                                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-3 text-xs text-[#8b949e]">
                                        <p className="font-semibold text-[#c9d1d9]">현재 route 매핑</p>
                                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                                            {row.routeKeys.map((routeKey: string) => (
                                                <div key={`${row.key}-${routeKey}`} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2">
                                                    <p className="text-[11px] text-[#79c0ff]">{routeKey}</p>
                                                    <p className="mt-1 break-all text-[#e6edf3]">{modelRoutes?.[routeKey] || '-'}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-2">
                        <div className="rounded-lg border border-[#d29922] bg-[#0d1117] p-4">
                            <div className="mb-3">
                                <h3 className="text-sm font-semibold text-[#e6edf3]">실행 정책 고정 패널</h3>
                                <p className="mt-1 text-xs text-[#8b949e]">전역 GPU 우선 여부와 라우트별 실행 모드를 기능별로 고정합니다.</p>
                            </div>
                            <div className="grid gap-3">
                                <label className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-3 text-sm text-[#e6edf3]">
                                    <input
                                        type="checkbox"
                                        checked={runtimeDraft?.gpu_only_preferred !== false}
                                        onChange={(e) => actions.updateGlobalExecutionPreference(e.target.checked)}
                                    />
                                    전역 GPU 우선 정책 유지
                                </label>
                                <div className="grid gap-3 md:grid-cols-2">
                                    {helpers.modelRouteFields.slice(0, 6).map(([routeKey, label]) => (
                                        <div key={`execution-${routeKey}`} className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="text-xs font-semibold text-[#79c0ff]">{label}</span>
                                                <span className="text-[11px] text-[#8b949e]">{helpers.executionModeLabels[executionControls?.[routeKey]?.acceleration_mode || 'gpu_only'] || '-'}</span>
                                            </div>
                                            <div className="mt-2 grid gap-2">
                                                <select
                                                    value={executionControls?.[routeKey]?.acceleration_mode || 'gpu_only'}
                                                    onChange={(e) => actions.updateRuntimeExecutionMode(routeKey, e.target.value)}
                                                    className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                                                >
                                                    {Object.entries(helpers.executionModeLabels).map(([modeKey, modeLabel]) => (
                                                        <option key={`${routeKey}-${modeKey}`} value={modeKey}>{modeLabel}</option>
                                                    ))}
                                                </select>
                                                <div className="grid grid-cols-2 gap-2">
                                                    <input
                                                        type="number"
                                                        value={executionControls?.[routeKey]?.num_gpu ?? ''}
                                                        onChange={(e) => actions.updateRuntimeExecutionNumeric(routeKey, 'num_gpu', e.target.value)}
                                                        placeholder="num_gpu"
                                                        className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                                                    />
                                                    <input
                                                        type="number"
                                                        value={executionControls?.[routeKey]?.num_thread ?? ''}
                                                        onChange={(e) => actions.updateRuntimeExecutionNumeric(routeKey, 'num_thread', e.target.value)}
                                                        placeholder="num_thread"
                                                        className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="rounded-lg border border-[#6e7681] bg-[#0d1117] p-4">
                            <div className="mb-3 flex items-start justify-between gap-3">
                                <div>
                                    <h3 className="text-sm font-semibold text-[#e6edf3]">오케스트레이터 전역값 고정 패널</h3>
                                    <p className="mt-1 text-xs text-[#8b949e]">시스템 설정과 identity provider 운영값을 섹션별로 열고 저장합니다.</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={actions.loadOrchestratorSystemSettings}
                                    disabled={data.orchestratorSystemLoading}
                                    className="rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-2 text-xs text-[#e6edf3]"
                                >
                                    {data.orchestratorSystemLoading ? '불러오는 중...' : '전역값 새로고침'}
                                </button>
                            </div>
                            <div className="space-y-3">
                                {(data.orchestratorSystemSettings?.sections || []).map((section: any) => {
                                    const isOpen = !!data.orchestratorSystemOpen?.[section.id];
                                    return (
                                        <div key={section.id} className="rounded-lg border border-[#30363d] bg-[#161b22] overflow-hidden">
                                            <button
                                                type="button"
                                                onClick={() => actions.toggleOrchestratorSystemSection(section.id)}
                                                className="w-full px-3 py-3 text-left"
                                            >
                                                <div className="flex items-center justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-semibold text-[#e6edf3]">{section.title}</p>
                                                        <p className="mt-1 text-[11px] text-[#8b949e]">{section.description}</p>
                                                    </div>
                                                    <span className="text-[11px] text-[#8b949e]">{isOpen ? '접기' : '펼치기'}</span>
                                                </div>
                                            </button>
                                            {isOpen && (
                                                <div className="border-t border-[#30363d] p-3 grid gap-3 md:grid-cols-2">
                                                    {(section.fields || []).map((field: any) => (
                                                        <label key={field.key} className="block">
                                                            <span className="mb-1 block text-xs text-[#8b949e]">{field.label}</span>
                                                            {field.multiline ? (
                                                                <textarea
                                                                    rows={3}
                                                                    value={field.value ?? ''}
                                                                    onChange={(e) => actions.updateOrchestratorSystemSettingValue(field.key, e.target.value)}
                                                                    className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                                                                />
                                                            ) : (
                                                                <input
                                                                    type={field.sensitive ? 'password' : 'text'}
                                                                    value={field.value ?? ''}
                                                                    onChange={(e) => actions.updateOrchestratorSystemSettingValue(field.key, e.target.value)}
                                                                    className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                                                                />
                                                            )}
                                                        </label>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                            {data.orchestratorSystemMessage && (
                                <p className={`mt-3 text-sm ${data.orchestratorSystemMessage.includes('실패') ? 'text-[#f78166]' : 'text-[#3fb950]'}`}>
                                    {data.orchestratorSystemMessage}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            )}
            <div className="mt-4 flex flex-wrap items-center gap-3">
                {data.runtimeEditorOpen && <button type="button" onClick={actions.saveRuntime} disabled={data.runtimeSaving || !runtimeDraft} className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${data.runtimeSaving || !runtimeDraft ? 'bg-[#21262d]' : 'bg-[#1f6feb]'}`}>{data.runtimeSaving ? '저장 중...' : '제한값 저장 및 즉시 적용'}</button>}
                {data.runtimeEditorOpen && <button type="button" onClick={actions.saveSystem} disabled={data.orchestratorSystemSaving || !runtimeDraft} className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${data.orchestratorSystemSaving || !runtimeDraft ? 'bg-[#21262d]' : 'bg-[#238636]'}`}>{data.orchestratorSystemSaving ? '전역값 저장 중...' : '오케스트레이터 전역값 저장'}</button>}
                <span className="text-xs text-[#8b949e]">{summaryText}</span>
            </div>
            {data.runtimeMessage && <p className={`mt-3 text-sm ${data.runtimeMessage.includes('실패') ? 'text-[#f78166]' : 'text-[#3fb950]'}`}>{data.runtimeMessage}</p>}
        </div>
    );
}
