'use client';

import React from 'react';
import { resolveMarketplaceSiteHref } from '@/lib/canonical-site';

type AdminDirectivePanelAgentOption = {
    key: string;
    label: string;
    summary: string;
    modelKey: string;
};

type AdminDirectivePanelFeature = {
    key: string;
    title: string;
    description: string;
    lockedMode: string;
    lockedLogics: string[];
};

type AdminDirectivePanelConversationMessage = {
    role: string;
    content: string;
    speaker?: string;
    timestamp?: string;
};

type AdminDirectivePanelMarketplaceOffer = {
    id: string;
    title: string;
    subtitle: string;
    description: string;
    priceLabel: string;
    badge: string;
    tags: string[];
    primaryActionLabel: string;
    secondaryActionLabel: string;
};

interface AdminDirectivePanelProps {
    chatAgentKey: string;
    voiceAgentKey: string;
    llmConfiguredModels?: Record<string, string> | null;
    orchestratorAgentOptions: AdminDirectivePanelAgentOption[];
    mandatoryRules: string[];
    optionalRules: string[];
    enabledRules: string[];
    onToggleRule: (rule: string) => void;
    routedTextFeatures: AdminDirectivePanelFeature[];
    textFeatureAgents: Record<string, string>;
    onUpdateTextFeatureAgent: (featureKey: string, agentKey: string) => void;
    onSetChatAgentKey: (agentKey: string) => void;
    onSetVoiceAgentKey: (agentKey: string) => void;
    continueInPlace: boolean;
    onSetContinueInPlace: (value: boolean) => void;
    workOutputDir: string;
    onSetWorkOutputDir: (value: string) => void;
    chatFunctionMode: string;
    onSetChatFunctionMode: (value: string) => void;
    conversation: AdminDirectivePanelConversationMessage[];
    examples: string[];
    onApplyExample: (value: string) => void;
    chatInput: string;
    onSetChatInput: (value: string) => void;
    chatLoading: boolean;
    onPushUserMessage: () => Promise<void>;
    loading: boolean;
    canRun: boolean;
    onRun: () => Promise<void>;
    onStartVoiceInput: () => void;
    voiceListening: boolean;
    liveOutputDir: string;
    lastWebResultsCount: number;
    marketplaceOffers: AdminDirectivePanelMarketplaceOffer[];
    onApplyMarketplaceOffer: (offerId: string) => void;
    onOpenMarketplace: () => void;
}

export default function AdminDirectivePanel({
    chatAgentKey,
    voiceAgentKey,
    llmConfiguredModels,
    orchestratorAgentOptions,
    mandatoryRules,
    optionalRules,
    enabledRules,
    onToggleRule,
    routedTextFeatures,
    textFeatureAgents,
    onUpdateTextFeatureAgent,
    onSetChatAgentKey,
    onSetVoiceAgentKey,
    continueInPlace,
    onSetContinueInPlace,
    workOutputDir,
    onSetWorkOutputDir,
    chatFunctionMode,
    onSetChatFunctionMode,
    conversation,
    examples,
    onApplyExample,
    chatInput,
    onSetChatInput,
    chatLoading,
    onPushUserMessage,
    loading,
    canRun,
    onRun,
    onStartVoiceInput,
    voiceListening,
    liveOutputDir,
    lastWebResultsCount,
    marketplaceOffers,
    onApplyMarketplaceOffer,
    onOpenMarketplace,
}: AdminDirectivePanelProps) {
    const marketplaceHomeHref = resolveMarketplaceSiteHref('/marketplace');
    const marketplaceOrchestratorHref = resolveMarketplaceSiteHref('/marketplace/orchestrator');

    return (
        <>
            <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                <label className="mb-1.5 block text-xs text-[#8b949e]">현재 적용 규칙 (버튼형)</label>
                <div className="mb-2">
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                        <label className="rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                            <span className="mb-2 block text-xs text-[#8b949e]">자연스런 이음 텍스트 기본 연결</span>
                            <select
                                title="자연스런 이음 텍스트 기본 연결"
                                value={chatAgentKey}
                                onChange={(e) => onSetChatAgentKey(e.target.value)}
                                className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                            >
                                {orchestratorAgentOptions.map((option) => (
                                    <option key={option.key} value={option.key}>
                                        {option.label} · {option.summary}
                                    </option>
                                ))}
                            </select>
                            <p className="mt-2 text-xs text-[#8b949e]">
                                연결 모델: {llmConfiguredModels?.[orchestratorAgentOptions.find((option) => option.key === chatAgentKey)?.modelKey || 'chat'] || 'N/A'}
                            </p>
                            <p className="mt-2 text-xs text-[#8b949e]">질문/정보수집/작업지시로 분기되지 않은 일반 대화는 이 기본 연결을 유지합니다.</p>
                        </label>
                        <label className="rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                            <span className="mb-2 block text-xs text-[#8b949e]">자연스런 이음 음성 기본 연결</span>
                            <select
                                title="자연스런 이음 음성 기본 연결"
                                value={voiceAgentKey}
                                onChange={(e) => onSetVoiceAgentKey(e.target.value)}
                                className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                            >
                                {orchestratorAgentOptions.map((option) => (
                                    <option key={option.key} value={option.key}>
                                        {option.label} · {option.summary}
                                    </option>
                                ))}
                            </select>
                            <p className="mt-2 text-xs text-[#8b949e]">
                                연결 모델: {llmConfiguredModels?.[orchestratorAgentOptions.find((option) => option.key === voiceAgentKey)?.modelKey || 'voice_chat'] || 'N/A'}
                            </p>
                            <p className="mt-2 text-xs text-[#8b949e]">음성은 자연스러운 대화 흐름을 유지하되 별도 음성 경로로 분리 연결됩니다.</p>
                        </label>
                    </div>
                    <span className="text-xs font-bold text-[#3fb950]">기본 연결 안내</span>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                        {mandatoryRules.map((rule) => (
                            <button
                                key={rule}
                                type="button"
                                disabled
                                className="cursor-not-allowed rounded-[18px] border border-[#30363d] bg-[#238636] px-3 py-1.5 text-xs font-semibold text-white opacity-95"
                            >
                                {rule}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <span className="text-xs font-bold text-[#58a6ff]">
                        선택 규칙 ({enabledRules.length}/{optionalRules.length})
                    </span>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                        {optionalRules.map((rule) => {
                            const enabled = enabledRules.includes(rule);
                            return (
                                <button
                                    key={rule}
                                    onClick={() => onToggleRule(rule)}
                                    type="button"
                                    className={`cursor-pointer rounded-[18px] border border-[#30363d] px-3 py-1.5 text-xs font-semibold ${enabled ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#8b949e]'}`}
                                >
                                    {enabled ? '✅ ' : '⬜ '}
                                    {rule}
                                </button>
                            );
                        })}
                    </div>

                    <div className="mt-4 rounded-lg border border-[#30363d] bg-[#11161d] p-4">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-[#3fb950]">기능별 연결 안내</span>
                            <span className="rounded-full border border-[#3fb950] px-2 py-0.5 text-[11px] text-[#3fb950]">프런트 표시</span>
                        </div>
                        <p className="mt-2 text-xs text-[#8b949e]">일반 대화와 기능별 흐름의 현재 연결 상태를 보여주는 안내 영역입니다.</p>
                        <div className="mt-3 grid gap-3 lg:grid-cols-3">
                            {routedTextFeatures.map((feature) => {
                                const connectedAgent = textFeatureAgents[feature.key];
                                const connectedOption = orchestratorAgentOptions.find((option) => option.key === connectedAgent);
                                return (
                                    <div key={feature.key} className="rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-sm font-semibold text-[#e6edf3]">{feature.title}</span>
                                            <span className="rounded-full bg-[#1f3a5f] px-2 py-0.5 text-[11px] text-[#79c0ff]">기본 모드 {feature.lockedMode}</span>
                                        </div>
                                        <p className="mt-2 text-xs text-[#8b949e]">{feature.description}</p>
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            {feature.lockedLogics.map((logic) => (
                                                <span key={`${feature.key}-${logic}`} className="rounded-[16px] border border-[#30363d] bg-[#238636] px-2.5 py-1 text-[11px] font-semibold text-white">
                                                    {logic}
                                                </span>
                                            ))}
                                        </div>
                                        <label className="mt-3 block">
                                            <span className="mb-2 block text-xs text-[#8b949e]">개별 연결 에이전트</span>
                                            <select
                                                title={`${feature.title} 개별 연결 에이전트`}
                                                value={connectedAgent}
                                                onChange={(e) => onUpdateTextFeatureAgent(feature.key, e.target.value)}
                                                className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                                            >
                                                {orchestratorAgentOptions.map((option) => (
                                                    <option key={`${feature.key}-${option.key}`} value={option.key}>
                                                        {option.label} · {option.summary}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>
                                        <p className="mt-2 text-xs text-[#8b949e]">
                                            연결 모델: {llmConfiguredModels?.[connectedOption?.modelKey || 'chat'] || 'N/A'}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                <div className="mb-3">
                    <label className="mb-1.5 block text-xs text-[#8b949e]">실행 제어</label>
                    <div className="rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-3">
                        <p className="text-sm text-[#8b949e]">
                            단계 선택은 화면에서 숨기고, 아래 통합 챗봇 통로에서 바로 대화와 실행을 이어갑니다.
                        </p>
                        <p className="mt-2 text-xs text-[#e3b341]">
                            내부 승인과 반영 완료는 1차 검증 상태이며, 최종 통과는 사용자가 오케스트레이터에서 직접 실험 후 인정합니다.
                        </p>
                        <label className="mt-3 flex items-center gap-2 text-xs text-[#e6edf3]">
                            <input
                                type="checkbox"
                                checked={continueInPlace}
                                onChange={(e) => onSetContinueInPlace(e.target.checked)}
                            />
                            현재 작업 폴더 계속 사용
                        </label>
                    </div>
                </div>
            </div>

            <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                <div className="mb-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                    <label className="mb-2 block text-xs text-[#8b949e]">현재 작업 폴더</label>
                    <input
                        type="text"
                        value={workOutputDir}
                        onChange={(e) => onSetWorkOutputDir(e.target.value)}
                        placeholder="예: C:\\...\\uploads\\projects\\project_20260309_xxxxxx"
                        className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                    />
                    <p className="mt-2 text-xs text-[#8b949e]">챗봇이 현재 작업 폴더를 기준으로 바로 수정/실행하도록 유지합니다.</p>
                </div>
                <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold text-[#e6edf3]">자동 · 반자동 오케스트레이션 이동</p>
                            <p className="mt-2 text-xs text-[#8b949e]">자가진단, 자가개선, 자가확장 같은 자동·반자동 실행 패널은 관리자 화면에서 빼고 마켓플레이스 오케스트레이터로 넘깁니다. 관리자 화면은 챗봇 지시와 즉시 실행에 집중합니다.</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <a href={marketplaceOrchestratorHref} className="rounded-lg bg-[#1f6feb] px-4 py-2 text-sm font-semibold text-white no-underline">
                                마켓플레이스 오케스트레이터 열기
                            </a>
                            <a href={marketplaceHomeHref} className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] no-underline">
                                마켓플레이스 이동
                            </a>
                        </div>
                    </div>
                </div>
                <div className="mb-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-semibold text-[#58a6ff]">Admin Directive Chatbot</h2>
                        <span className="rounded-full bg-[#12381f] px-2 py-1 text-[11px] text-[#3fb950]">챗봇 중심</span>
                    </div>
                    <p className="text-xs text-[#8b949e]">관리자 화면에서는 필요한 수정과 구현을 대화로 바로 지시하고, 이 창에서 즉시 실행합니다.</p>
                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <div className="text-xs font-semibold text-[#79c0ff]">대화 기능 선택</div>
                                <p className="mt-1 text-xs text-[#8b949e]">기본은 작업 지시이며, 필요할 때만 질문 응답이나 정보 수집으로 바꿉니다.</p>
                            </div>
                            <span className="rounded-full bg-[#21262d] px-2 py-1 text-[11px] text-[#e6edf3]">
                                현재 기능 {chatFunctionMode === 'auto' ? '자동 판단' : routedTextFeatures.find((feature) => feature.key === chatFunctionMode)?.title}
                            </span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <button
                                type="button"
                                onClick={() => onSetChatFunctionMode('auto')}
                                className={`rounded-2xl border px-3 py-2 text-sm ${chatFunctionMode === 'auto' ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}
                            >
                                자동 판단
                            </button>
                            {routedTextFeatures.map((feature) => {
                                const selected = chatFunctionMode === feature.key;
                                return (
                                    <button
                                        key={feature.key}
                                        type="button"
                                        onClick={() => onSetChatFunctionMode(feature.key)}
                                        className={`rounded-2xl border px-3 py-2 text-sm ${selected ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}
                                    >
                                        {feature.title}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3 text-xs text-[#8b949e]">
                        자동 추천, 반자동 실행, 외부 참고 결과 패널은 관리자 화면에서 숨기고 챗봇 본문과 직접 실행만 남깁니다.
                    </div>
                </div>
                <div className="mb-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold text-[#e6edf3]">코드생성기 전용 상품 진열</p>
                            <p className="mt-1 text-xs text-[#8b949e]">각 코드생성기의 주특기를 바로 상품으로 전환하고, 관리자 지시문과 마켓플레이스 진열 흐름을 한 번에 연결합니다.</p>
                        </div>
                        <button
                            type="button"
                            onClick={onOpenMarketplace}
                            className="rounded-lg border border-[#8957e5] bg-[#1f1630] px-3 py-2 text-xs font-semibold text-[#e9d5ff]"
                        >
                            마켓플레이스 전체 보기
                        </button>
                    </div>
                    <div className="mt-3 grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
                        {marketplaceOffers.map((offer) => (
                            <div key={offer.id} className="rounded-xl border border-[#30363d] bg-[#11161d] p-4">
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <p className="text-sm font-semibold text-[#e6edf3]">{offer.title}</p>
                                        <p className="mt-1 text-[11px] text-[#79c0ff]">{offer.subtitle}</p>
                                    </div>
                                    <span className="rounded-full border border-[#3fb950] px-2 py-1 text-[10px] font-semibold text-[#3fb950]">{offer.badge}</span>
                                </div>
                                <p className="mt-3 text-xs leading-5 text-[#8b949e]">{offer.description}</p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {offer.tags.map((tag) => (
                                        <span key={`${offer.id}-${tag}`} className="rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-1 text-xs text-[#c9d1d9]">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                                <div className="mt-4 flex items-center justify-between gap-2">
                                    <span className="text-sm font-semibold text-[#e3b341]">{offer.priceLabel}</span>
                                    <button
                                        type="button"
                                        onClick={() => onApplyMarketplaceOffer(offer.id)}
                                        className="rounded-lg bg-[#1f6feb] px-3 py-2 text-xs font-semibold text-white"
                                    >
                                        {offer.primaryActionLabel}
                                    </button>
                                </div>
                                <p className="mt-2 text-[11px] text-[#8b949e]">{offer.secondaryActionLabel}</p>
                            </div>
                        ))}
                    </div>
                </div>
                {lastWebResultsCount > 0 && (
                    <div className="mb-3 rounded-lg border border-[#1f6feb] bg-[#0f2747] p-3 text-xs text-[#9ecbff]">
                        최근 대화에서 웹 검색 근거 {lastWebResultsCount}건이 반영됐습니다. 필요하면 관리자 본문 패널에서 근거 상세를 확인한 뒤 feature-orchestrate로 연결하세요.
                    </div>
                )}
                <div className="mb-3 max-h-[340px] space-y-3 overflow-y-auto rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                    {conversation.map((message, index) => (
                        <div
                            key={`${message.timestamp || 'msg'}-${index}`}
                            className={`rounded-lg border px-4 py-3 ${message.role === 'user' ? 'ml-10 border-[#1f6feb] bg-[#0f2747]' : 'mr-10 border-[#30363d] bg-[#161b22]'}`}
                        >
                            <div className="mb-1 flex items-center justify-between gap-3 text-[11px] text-[#8b949e]">
                                <span>{message.speaker || message.role}</span>
                                <span>{message.timestamp ? new Date(message.timestamp).toLocaleTimeString('ko-KR') : ''}</span>
                            </div>
                            <p className="whitespace-pre-wrap break-words text-sm text-[#e6edf3]">{message.content}</p>
                        </div>
                    ))}
                </div>
                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                    <label className="mb-2 block text-xs font-semibold text-[#79c0ff]">지시 입력</label>
                    <div className="mb-3 flex flex-wrap gap-2">
                        {examples.map((example) => (
                            <button
                                key={example}
                                type="button"
                                onClick={() => onApplyExample(example)}
                                className="rounded-2xl border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs text-[#58a6ff]"
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                    <textarea
                        value={chatInput}
                        onChange={(e) => onSetChatInput(e.target.value)}
                        placeholder="예: 관리자 응답 중복 제거해줘 / 이 파일 기준으로 바로 수정해줘 / 필요한 코드만 바로 구현해줘"
                        className="box-border min-h-[108px] w-full resize-y rounded-lg border border-[#30363d] bg-[#0d1117] p-3 text-sm text-[#e6edf3]"
                    />
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[#8b949e]">
                        <span>현재 작업 폴더 {workOutputDir || liveOutputDir || '-'}</span>
                        <span>
                            현재 기능 {chatFunctionMode === 'auto' ? '자동 판단' : routedTextFeatures.find((feature) => feature.key === chatFunctionMode)?.title}
                        </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={() => void onPushUserMessage()}
                            disabled={chatLoading || !chatInput.trim()}
                            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${chatLoading || !chatInput.trim() ? 'bg-[#21262d]' : 'bg-[#1f6feb]'}`}
                        >
                            {chatLoading ? '응답 대기 중...' : '지시 보내기'}
                        </button>
                        <button
                            type="button"
                            onClick={() => void onRun()}
                            disabled={loading || !canRun}
                            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${loading || !canRun ? 'bg-[#21262d]' : 'bg-[#238636]'}`}
                        >
                            {loading ? '실행 중...' : '바로 실행'}
                        </button>
                        <a href={marketplaceOrchestratorHref} className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] no-underline">
                            자동 실행은 마켓플레이스에서
                        </a>
                        <button
                            type="button"
                            onClick={onStartVoiceInput}
                            disabled={chatLoading}
                            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${chatLoading ? 'bg-[#21262d]' : voiceListening ? 'bg-[#da3633]' : 'bg-[#238636]'}`}
                        >
                            {voiceListening ? '음성 듣는 중...' : '음성 지시'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
