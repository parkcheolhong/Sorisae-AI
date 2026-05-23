'use client';

export interface AdminGeneratorDetailModalAction {
    id: string;
    label: string;
    summary: string;
}

export interface AdminGeneratorDetailModalData {
    id: string;
    title: string;
    summary: string;
    finalStage: string;
    presetLabel: string;
    featureLabel: string;
    currentState: string;
    metric: string;
    detail: string;
    directivePreview: string;
    marketplaceOfferTitle: string;
    marketplaceOfferPrice: string;
    marketplaceOfferBadge: string;
    tags: string[];
    actions: AdminGeneratorDetailModalAction[];
}

interface AdminGeneratorDetailModalProps {
    modal: AdminGeneratorDetailModalData | null;
    onClose: () => void;
    onSelectAction: (actionId: string) => void;
}

export default function AdminGeneratorDetailModal({
    modal,
    onClose,
    onSelectAction,
}: AdminGeneratorDetailModalProps) {
    if (!modal) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" data-testid="admin-generator-detail-modal">
            <div className="w-full max-w-5xl rounded-2xl border border-[#30363d] bg-[#0d1117] p-5 text-[#e6edf3] shadow-[0_20px_80px_rgba(0,0,0,0.45)]">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#79c0ff]">Generator Control</p>
                        <h3 className="mt-2 text-2xl font-semibold text-white" data-testid="admin-generator-detail-modal-title">{modal.title}</h3>
                        <p className="mt-2 text-sm text-[#8b949e]">{modal.summary}</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm font-semibold text-[#e6edf3]"
                        data-testid="admin-generator-detail-modal-close"
                    >
                        닫기
                    </button>
                </div>

                <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                    <div className="space-y-4">
                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                            <div className="grid gap-3 md:grid-cols-2">
                                <div>
                                    <p className="text-xs text-[#8b949e]">최종 단계</p>
                                    <p className="mt-1 text-sm font-semibold text-[#e6edf3]">{modal.finalStage}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8b949e]">현재 상태</p>
                                    <p className="mt-1 text-sm font-semibold text-[#e6edf3]">{modal.currentState}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8b949e]">연결 preset</p>
                                    <p className="mt-1 text-sm font-semibold text-[#e6edf3]">{modal.presetLabel}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-[#8b949e]">기능 모드</p>
                                    <p className="mt-1 text-sm font-semibold text-[#e6edf3]">{modal.featureLabel}</p>
                                </div>
                            </div>
                            <div className="mt-4 rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                                <p className="text-xs text-[#8b949e]">지표</p>
                                <p className="mt-1 text-sm font-semibold text-[#79c0ff]">{modal.metric}</p>
                                <p className="mt-2 text-xs leading-5 text-[#c9d1d9]">{modal.detail}</p>
                            </div>
                        </div>

                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                            <p className="text-sm font-semibold text-[#e6edf3]">전용 제어 패널</p>
                            <p className="mt-1 text-xs text-[#8b949e]">이 코드생성기를 기준으로 preset, 기능 모드, 지시문, 마켓 상품 반영을 한 번에 전환합니다.</p>
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                                {modal.actions.map((action) => (
                                    <button
                                        key={action.id}
                                        type="button"
                                        onClick={() => onSelectAction(action.id)}
                                        className="rounded-xl border border-[#30363d] bg-[#0d1117] p-4 text-left hover:border-[#1f6feb]"
                                        data-testid={`admin-generator-action-${action.id}`}
                                    >
                                        <p className="text-sm font-semibold text-[#e6edf3]">{action.label}</p>
                                        <p className="mt-2 text-xs leading-5 text-[#8b949e]">{action.summary}</p>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                            <p className="text-sm font-semibold text-[#e6edf3]">지시문 프리뷰</p>
                            <pre className="mt-3 overflow-x-auto rounded-lg border border-[#30363d] bg-[#0d1117] p-3 text-xs leading-5 text-[#c9d1d9] whitespace-pre-wrap" data-testid="admin-generator-detail-modal-directive">
{modal.directivePreview}
                            </pre>
                        </div>

                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <p className="text-sm font-semibold text-[#e6edf3]">연결 상품</p>
                                    <p className="mt-1 text-xs text-[#79c0ff]">{modal.marketplaceOfferTitle}</p>
                                </div>
                                <span className="rounded-full border border-[#3fb950] px-2 py-1 text-[11px] font-semibold text-[#3fb950]">{modal.marketplaceOfferBadge}</span>
                            </div>
                            <p className="mt-3 text-lg font-bold text-[#e3b341]">{modal.marketplaceOfferPrice}</p>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {modal.tags.map((tag) => (
                                    <span key={`${modal.id}-${tag}`} className="rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-1 text-[11px] text-[#c9d1d9]">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
