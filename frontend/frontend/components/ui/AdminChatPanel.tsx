'use client';

import Link from 'next/link';
import type React from 'react';
import { resolveMarketplaceSiteHref } from '@/lib/canonical-site';

export type ChatFunctionMode = 'auto' | 'question' | 'research' | 'action';
export type AdminConversationMode = 'auto' | 'directive_fixed' | 'research_fixed';

export interface ConversationMessage {
    role: string;
    content: string;
    speaker?: string | null;
    timestamp?: string | null;
}

export interface RoutedTextFeatureOption {
    key: 'question' | 'research' | 'action';
    title: string;
}

interface AdminChatPanelProps {
    adminConversationMode: AdminConversationMode;
    setAdminConversationMode: (value: AdminConversationMode) => void;
    chatFunctionMode: ChatFunctionMode;
    setChatFunctionMode: (value: ChatFunctionMode) => void;
    routedTextFeatures: RoutedTextFeatureOption[];
    conversation: ConversationMessage[];
    chatInput: string;
    setUnifiedPrompt: (value: string) => void;
    examples: string[];
    workOutputDir: string;
    liveOutputDir: string;
    chatLoading: boolean;
    voiceListening: boolean;
    onSendMessage: () => void;
    onStartVoiceInput: () => void;
}

export default function AdminChatPanel({
    adminConversationMode,
    setAdminConversationMode,
    chatFunctionMode,
    setChatFunctionMode,
    routedTextFeatures,
    conversation,
    chatInput,
    setUnifiedPrompt,
    examples,
    workOutputDir,
    liveOutputDir,
    chatLoading,
    voiceListening,
    onSendMessage,
    onStartVoiceInput,
}: AdminChatPanelProps) {
    const marketplaceHomeHref = resolveMarketplaceSiteHref('/marketplace');
    const marketplaceOrchestratorHref = resolveMarketplaceSiteHref('/marketplace/orchestrator');

    const currentConversationModeLabel = adminConversationMode === 'directive_fixed'
        ? '지시형 고정'
        : adminConversationMode === 'research_fixed'
            ? '연구형 고정'
            : '자동';

    const currentFunctionLabel = chatFunctionMode === 'auto'
        ? '자동 판단'
        : routedTextFeatures.find((feature) => feature.key === chatFunctionMode)?.title;

    return (
        <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
            <div className="mb-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                <label className="mb-2 block text-xs text-[#8b949e]">현재 작업 폴더</label>
                <input
                    type="text"
                    value={workOutputDir}
                    readOnly
                    className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                />
                <p className="mt-2 text-xs text-[#8b949e]">챗봇이 현재 작업 폴더를 기준으로 바로 수정/실행하며, 같은 프로젝트는 한 폴더 안에서 누적 작업을 이어갑니다.</p>
            </div>
            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold text-[#e6edf3]">고객 주문 기반 자율 생성기 이동</p>
                        <p className="mt-2 text-xs text-[#8b949e]">자가진단, 외부 참고 결과 패널은 고객 주문 기반 자율 생성기와 같은 방향을 보도록 마켓플레이스 오케스트레이터로 넘기고, 관리자 화면은 챗봇 지시와 수동 검토에 집중합니다.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link prefetch={false} href={marketplaceOrchestratorHref} className="rounded-lg bg-[#1f6feb] px-4 py-2 text-sm font-semibold text-white no-underline">
                            고객 주문 생성기 열기
                        </Link>
                        <Link prefetch={false} href={marketplaceHomeHref} className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] no-underline">
                            마켓플레이스 이동
                        </Link>
                    </div>
                </div>
            </div>
            <div className="mb-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold text-[#58a6ff]">관리자 지시형 챗봇</h2>
                    <span className="rounded-full bg-[#12381f] px-2 py-1 text-[11px] text-[#3fb950]">챗봇 중심</span>
                </div>
                <p className="text-xs text-[#8b949e]">관리자 화면에서는 필요한 수정과 구현을 대화로 지시하고, 이 창에서 수동 검토와 실험 기록을 이어갑니다.</p>
                <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <div className="text-xs font-semibold text-[#79c0ff]">대화 모드 고정</div>
                            <p className="mt-1 text-xs text-[#8b949e]">지시형 또는 연구형을 고정하면 백엔드가 메시지 내용을 다시 자동 재분류하지 않습니다.</p>
                        </div>
                        <span className="rounded-full bg-[#21262d] px-2 py-1 text-[11px] text-[#e6edf3]">
                            현재 모드 {currentConversationModeLabel}
                        </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button type="button" onClick={() => setAdminConversationMode('directive_fixed')} className={`rounded-2xl border px-3 py-2 text-sm ${adminConversationMode === 'directive_fixed' ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}>
                            지시형 고정
                        </button>
                        <button type="button" onClick={() => setAdminConversationMode('research_fixed')} className={`rounded-2xl border px-3 py-2 text-sm ${adminConversationMode === 'research_fixed' ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}>
                            연구형 고정
                        </button>
                        <button type="button" onClick={() => setAdminConversationMode('auto')} className={`rounded-2xl border px-3 py-2 text-sm ${adminConversationMode === 'auto' ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}>
                            자동
                        </button>
                    </div>
                </div>
                <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <div className="text-xs font-semibold text-[#79c0ff]">대화 기능 선택</div>
                            <p className="mt-1 text-xs text-[#8b949e]">기본은 작업 지시이며, 필요할 때만 질문 응답이나 정보 수집으로 바꿉니다.</p>
                        </div>
                        <span className="rounded-full bg-[#21262d] px-2 py-1 text-[11px] text-[#e6edf3]">
                            현재 기능 {currentFunctionLabel}
                        </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button type="button" onClick={() => setChatFunctionMode('auto')} className={`rounded-2xl border px-3 py-2 text-sm ${chatFunctionMode === 'auto' ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}>
                            자동 판단
                        </button>
                        {routedTextFeatures.map((feature) => {
                            const selected = chatFunctionMode === feature.key;
                            return (
                                <button
                                    key={feature.key}
                                    type="button"
                                    onClick={() => setChatFunctionMode(feature.key)}
                                    className={`rounded-2xl border px-3 py-2 text-sm ${selected ? 'border-[#1f6feb] bg-[#0f2747] text-white' : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3]'}`}
                                >
                                    {feature.title}
                                </button>
                            );
                        })}
                    </div>
                </div>
                <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3 text-xs text-[#8b949e]">
                    자동 추천, 외부 참고 결과 패널은 관리자 화면에서 숨기고 챗봇 지시/수동 검토 중심으로만 남깁니다.
                </div>
            </div>
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
                            onClick={() => setUnifiedPrompt(example)}
                            className="rounded-2xl border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs text-[#58a6ff]"
                        >
                            {example}
                        </button>
                    ))}
                </div>
                <textarea
                    value={chatInput}
                    onChange={(e) => setUnifiedPrompt(e.target.value)}
                    placeholder="예: 관리자 응답 중복 제거해줘 / 이 파일 기준으로 바로 수정해줘 / 필요한 코드만 바로 구현해줘"
                    className="box-border min-h-[108px] w-full resize-y rounded-lg border border-[#30363d] bg-[#0d1117] p-3 text-sm text-[#e6edf3]"
                />
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[#8b949e]">
                    <span>현재 작업 폴더 {workOutputDir || liveOutputDir || '-'}</span>
                    <span>현재 기능 {currentFunctionLabel}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                    <button
                        type="button"
                        onClick={onSendMessage}
                        disabled={chatLoading || !chatInput.trim()}
                        className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${chatLoading || !chatInput.trim() ? 'bg-[#21262d]' : 'bg-[#1f6feb]'}`}
                    >
                        {chatLoading ? '응답 대기 중...' : '지시 보내기'}
                    </button>
                    <Link prefetch={false} href={marketplaceOrchestratorHref} className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] no-underline">
                        고객 주문 생성기는 마켓플레이스에서
                    </Link>
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
    );
}
