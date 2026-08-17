'use client';

import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { AdminAdProductionStage } from '@/lib/admin-ad-production-analysis';

interface AdminTraceHistoryItem {
    id: number;
    trace_id: string;
    entity_type: string;
    entity_id: string | number;
    connection_id?: string | null;
    flow_id?: string | null;
    step_id?: string | null;
    action?: string | null;
    status: string;
    message: string;
    created_at: string;
}

interface AdminCompletionHistoryItem {
    id: number;
    project_name: string;
    mode: string;
    attempts: number;
    gate_passed: boolean;
    connection_id?: string | null;
    trace_id?: string | null;
    created_at: string;
}

interface AdminRetryQueueItem {
    id: number;
    trace_id: string;
    entity_type: string;
    entity_id: string | number;
    connection_id?: string | null;
    queue_name: string;
    attempt_count: number;
    max_attempts: number;
    status: string;
    last_error?: string | null;
}

interface AdminAdProductionPanelProps {
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    latestDedicatedCurrentStage: string;
    latestDedicatedWorkReady: boolean;
    latestDedicatedReadyCount: number;
    selectedFlowId: string;
    selectedStepId: string;
    selectedAction: string;
    filteredAdminCompletionHistory: AdminCompletionHistoryItem[];
    filteredAdminTraceHistory: AdminTraceHistoryItem[];
    filteredAdminRetryQueueItems: AdminRetryQueueItem[];
    latestDedicatedProductionStages: AdminAdProductionStage[];
    actionTemplateLabel: string;
    motionTempoLabel: string;
    humanInteractionRules: string[];
    onOpenMarketplaceBridge: () => void;
    onReloadTrace: () => void;
    onReplayRetryQueue: (id: number) => void;
    adminReplayQueueId: number | null;
    adminTraceFilter: string;
    onAdminTraceFilterChange: (value: string) => void;
    getSceneFrameHint: (durationSec?: number, motionSpeedPercent?: number) => number;
}

export default function AdminAdProductionPanel({
    latestDedicatedOrder,
    latestDedicatedCurrentStage,
    latestDedicatedWorkReady,
    latestDedicatedReadyCount,
    selectedFlowId,
    selectedStepId,
    selectedAction,
    filteredAdminCompletionHistory,
    filteredAdminTraceHistory,
    filteredAdminRetryQueueItems,
    latestDedicatedProductionStages,
    actionTemplateLabel,
    motionTempoLabel,
    humanInteractionRules,
    onOpenMarketplaceBridge,
    onReloadTrace,
    onReplayRetryQueue,
    adminReplayQueueId,
    adminTraceFilter,
    onAdminTraceFilterChange,
    getSceneFrameHint,
}: AdminAdProductionPanelProps) {
    return (
        <div className="rounded-lg border border-blue-100 bg-white px-4 py-3 text-sm text-gray-700 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="font-semibold text-gray-900">관리자 추적 패널</p>
                    <p className="mt-1 text-xs text-gray-500">마켓플레이스와 동일한 trace/log/retry 큐를 관리자 화면에서도 확인합니다.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <input
                        value={adminTraceFilter}
                        onChange={(event) => onAdminTraceFilterChange(event.target.value)}
                        className="rounded-md border border-gray-300 px-3 py-1 text-xs text-gray-700"
                        placeholder="trace / flow / step / action 검색"
                    />
                    <button
                        type="button"
                        onClick={onReloadTrace}
                        className="rounded-md border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                    >
                        추적 새로고침
                    </button>
                </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-md border border-cyan-100 bg-cyan-50 px-3 py-3 text-xs">
                    <p className="text-gray-500">생산 라인 분류</p>
                    <p className="mt-1 font-semibold text-cyan-700">{latestDedicatedOrder ? '4D dedicated line' : '대기 중'}</p>
                    <p className="mt-1 text-[11px] text-cyan-800">{latestDedicatedOrder ? `주문 #${latestDedicatedOrder.id} · ${latestDedicatedOrder.title}` : 'dedicated_engine 주문이 들어오면 자동 추적됩니다.'}</p>
                </div>
                <div className="rounded-md border border-violet-100 bg-violet-50 px-3 py-3 text-xs">
                    <p className="text-gray-500">현재 생산 단계</p>
                    <p className="mt-1 font-semibold text-violet-700">{latestDedicatedCurrentStage}</p>
                    <p className="mt-1 text-[11px] text-violet-800">6단 생산 라인 기준으로 다음 작업 단계를 표시합니다.</p>
                </div>
                <div className={`rounded-md border px-3 py-3 text-xs ${latestDedicatedWorkReady ? 'border-emerald-100 bg-emerald-50' : 'border-amber-100 bg-amber-50'}`}>
                    <p className="text-gray-500">작업 가능 여부</p>
                    <p className={`mt-1 font-semibold ${latestDedicatedWorkReady ? 'text-emerald-700' : 'text-amber-800'}`}>{latestDedicatedWorkReady ? '작업 가능' : '입력 보강 필요'}</p>
                    <p className={`mt-1 text-[11px] ${latestDedicatedWorkReady ? 'text-emerald-800' : 'text-amber-800'}`}>체크리스트 {latestDedicatedReadyCount}/6 완료</p>
                </div>
                <div className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-3 text-xs">
                    <p className="text-gray-500">현재 추적</p>
                    <p className="mt-1 font-semibold text-indigo-700">{selectedFlowId} / {selectedStepId} / {selectedAction}</p>
                    <p className="mt-1 break-all text-[11px] text-indigo-800">{`${selectedFlowId}:${selectedStepId}:${selectedAction}`}</p>
                </div>
                <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-3 text-xs">
                    <p className="text-gray-500">완료 이력</p>
                    <p className="mt-1 font-semibold text-gray-900">{filteredAdminCompletionHistory.length}건</p>
                </div>
                <div className="rounded-md border border-amber-100 bg-amber-50 px-3 py-3 text-xs">
                    <p className="text-gray-500">재시도 큐</p>
                    <p className="mt-1 font-semibold text-amber-800">{filteredAdminRetryQueueItems.length}건</p>
                </div>
            </div>

            <div className="rounded-lg border border-cyan-100 bg-cyan-50 px-3 py-3 space-y-3">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold text-cyan-900">4D 생산 라인 체크리스트</p>
                        <p className="mt-1 text-[11px] text-cyan-800">시나리오 · 배경 · 자막 · 이미지 · 컷 이음 · 연속성 6단이 모두 차야 dedicated 작업 가능 상태가 됩니다.</p>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${latestDedicatedWorkReady ? 'border-emerald-300 bg-emerald-100 text-emerald-700' : 'border-amber-300 bg-amber-100 text-amber-700'}`}>
                        {latestDedicatedReadyCount}/6
                    </span>
                </div>
                <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
                    {latestDedicatedProductionStages.map((stage) => (
                        <div key={stage.id} className={`rounded-lg border px-3 py-3 text-xs ${stage.ready ? 'border-emerald-200 bg-white text-emerald-800' : 'border-amber-200 bg-white text-amber-800'}`}>
                            <div className="flex items-center justify-between gap-2">
                                <p className="font-semibold">{stage.label} · {stage.title}</p>
                                <span className={`rounded-full px-2 py-0.5 ${stage.ready ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{stage.ready ? '완료' : '대기'}</span>
                            </div>
                            <p className="mt-2">{stage.detail}</p>
                        </div>
                    ))}
                </div>
            </div>

            {latestDedicatedOrder && (
                <div className="rounded-lg border border-sky-100 bg-sky-50 px-3 py-3 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold text-sky-900">행동 템플릿 / 사람-물체 규칙</p>
                            <p className="mt-1 text-[11px] text-sky-800">4D 디자이너 자연어 키프레임 기준과 영상 편집/이음 연결 기준을 같이 봅니다.</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-[11px]">
                            <button
                                type="button"
                                onClick={onOpenMarketplaceBridge}
                                className="rounded-md border border-sky-300 bg-sky-600 px-3 py-2 font-semibold text-white hover:bg-sky-700"
                            >
                                마켓플레이스 오케스트레이터 연결
                            </button>
                            <span className="rounded-full border border-sky-200 bg-white px-2 py-1 text-sky-700">템플릿 {actionTemplateLabel}</span>
                            <span className="rounded-full border border-sky-200 bg-white px-2 py-1 text-sky-700">속도 {motionTempoLabel}</span>
                        </div>
                    </div>
                    <ul className="grid grid-cols-1 gap-2 text-xs text-sky-900 xl:grid-cols-2">
                        {humanInteractionRules.map((rule) => (
                            <li key={rule} className="rounded-md border border-sky-100 bg-white px-3 py-2">• {rule}</li>
                        ))}
                    </ul>
                    {latestDedicatedOrder.scenario_script && (
                        <div className="rounded-md border border-sky-100 bg-white px-3 py-3 text-xs text-sky-900">
                            <p className="font-semibold">자연어 시나리오 원문</p>
                            <p className="mt-2 whitespace-pre-wrap">{latestDedicatedOrder.scenario_script}</p>
                        </div>
                    )}
                    <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
                        {(latestDedicatedOrder.storyboard || []).map((scene) => (
                            <div key={scene.cut} className="rounded-md border border-sky-100 bg-white px-3 py-3 text-xs text-sky-900">
                                <p className="font-semibold">컷 {scene.cut} · {scene.title || '무제'}</p>
                                <p className="mt-1 text-sky-700">속도 {scene.motion_speed_percent || 100}% · frame hint {getSceneFrameHint(scene.duration_sec, scene.motion_speed_percent)}장</p>
                                {scene.designer_prompt && <p className="mt-2 line-clamp-3 text-[11px] text-sky-800">디자이너 프롬프트: {scene.designer_prompt}</p>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="rounded-lg border border-gray-200 px-3 py-3 space-y-2">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-700">completion 이력 패널</p>
                    <span className="text-xs text-gray-500">connection_id 포함</span>
                </div>
                {filteredAdminCompletionHistory.length === 0 ? (
                    <p className="text-xs text-gray-500">저장된 completion 이력이 없습니다.</p>
                ) : (
                    <div className="max-h-56 overflow-y-auto rounded-md border border-gray-200">
                        <table className="w-full text-xs">
                            <thead className="bg-gray-50 text-gray-600">
                                <tr>
                                    <th className="px-2 py-2 text-left">시간</th>
                                    <th className="px-2 py-2 text-left">프로젝트</th>
                                    <th className="px-2 py-2 text-left">연결</th>
                                    <th className="px-2 py-2 text-left">결과</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAdminCompletionHistory.map((item) => (
                                    <tr key={item.id} className="border-t border-gray-100 align-top text-gray-700">
                                        <td className="whitespace-nowrap px-2 py-2">{new Date(item.created_at).toLocaleString('ko-KR', { hour12: false })}</td>
                                        <td className="px-2 py-2">
                                            <div className="font-medium text-emerald-700">{item.project_name}</div>
                                            <div className="text-[11px] text-gray-500">{item.mode} · attempts {item.attempts}</div>
                                        </td>
                                        <td className="break-all px-2 py-2 text-[11px] text-indigo-700">{item.connection_id || item.trace_id || '-'}</td>
                                        <td className="px-2 py-2">{item.gate_passed ? 'gate pass' : 'gate blocked'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="rounded-lg border border-gray-200 px-3 py-3 space-y-2">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-700">trace 이력 패널</p>
                    <span className="text-xs text-gray-500">Flow / Step / Action</span>
                </div>
                {filteredAdminTraceHistory.length === 0 ? (
                    <p className="text-xs text-gray-500">저장된 trace 이력이 없습니다.</p>
                ) : (
                    <div className="max-h-56 overflow-y-auto rounded-md border border-gray-200">
                        <table className="w-full text-xs">
                            <thead className="bg-gray-50 text-gray-600">
                                <tr>
                                    <th className="px-2 py-2 text-left">시간</th>
                                    <th className="px-2 py-2 text-left">Trace</th>
                                    <th className="px-2 py-2 text-left">connection_id</th>
                                    <th className="px-2 py-2 text-left">상태</th>
                                    <th className="px-2 py-2 text-left">메시지</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAdminTraceHistory.map((item) => (
                                    <tr key={item.id} className="border-t border-gray-100 align-top text-gray-700">
                                        <td className="whitespace-nowrap px-2 py-2">{new Date(item.created_at).toLocaleString('ko-KR', { hour12: false })}</td>
                                        <td className="px-2 py-2">
                                            <div className="font-medium text-indigo-700">{item.trace_id}</div>
                                            <div className="text-[11px] text-gray-500">{item.entity_type} / {item.entity_id}</div>
                                        </td>
                                        <td className="break-all px-2 py-2 text-[11px] text-indigo-700">{item.connection_id || '-'}</td>
                                        <td className="px-2 py-2">{item.status}</td>
                                        <td className="px-2 py-2">{item.message}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="rounded-lg border border-gray-200 px-3 py-3 space-y-2">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-700">로그 테이블 패널</p>
                    <span className="text-xs text-gray-500">DB 로그 표시</span>
                </div>
                {filteredAdminTraceHistory.length === 0 ? (
                    <p className="text-xs text-gray-500">표시할 로그가 없습니다.</p>
                ) : (
                    <div className="max-h-56 overflow-y-auto rounded-md border border-gray-200 bg-gray-50">
                        <div className="space-y-2 p-2">
                            {filteredAdminTraceHistory.map((item) => (
                                <div key={`admin-log-${item.id}`} className="rounded border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="font-medium text-indigo-700">{item.flow_id} / {item.step_id} / {item.action}</span>
                                        <span>{item.status}</span>
                                    </div>
                                    <div className="mt-1">{item.message}</div>
                                    <div className="mt-1 break-all text-[11px] text-indigo-700">{item.connection_id || item.trace_id}</div>
                                    <div className="mt-1 text-[11px] text-gray-500">{item.entity_type} / {item.entity_id} · {new Date(item.created_at).toLocaleString('ko-KR', { hour12: false })}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <div className="rounded-lg border border-gray-200 px-3 py-3 space-y-2">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-700">실패 재시도 큐 패널</p>
                    <span className="text-xs text-gray-500">retry queue 추적</span>
                </div>
                {filteredAdminRetryQueueItems.length === 0 ? (
                    <p className="text-xs text-gray-500">대기 중인 재시도 큐가 없습니다.</p>
                ) : (
                    <div className="max-h-56 overflow-y-auto rounded-md border border-gray-200">
                        <table className="w-full text-xs">
                            <thead className="bg-gray-50 text-gray-600">
                                <tr>
                                    <th className="px-2 py-2 text-left">Trace</th>
                                    <th className="px-2 py-2 text-left">connection_id</th>
                                    <th className="px-2 py-2 text-left">큐</th>
                                    <th className="px-2 py-2 text-left">시도</th>
                                    <th className="px-2 py-2 text-left">상태</th>
                                    <th className="px-2 py-2 text-left">오류</th>
                                    <th className="px-2 py-2 text-left">실행</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAdminRetryQueueItems.map((item) => (
                                    <tr key={item.id} className="border-t border-gray-100 align-top text-gray-700">
                                        <td className="px-2 py-2">
                                            <div className="font-medium text-indigo-700">{item.trace_id}</div>
                                            <div className="text-[11px] text-gray-500">{item.entity_type} / {item.entity_id}</div>
                                        </td>
                                        <td className="break-all px-2 py-2 text-[11px] text-indigo-700">{item.connection_id || '-'}</td>
                                        <td className="px-2 py-2">{item.queue_name}</td>
                                        <td className="px-2 py-2">{item.attempt_count} / {item.max_attempts}</td>
                                        <td className="px-2 py-2">{item.status}</td>
                                        <td className="px-2 py-2">{item.last_error || '-'}</td>
                                        <td className="px-2 py-2">
                                            <button
                                                type="button"
                                                onClick={() => onReplayRetryQueue(item.id)}
                                                disabled={adminReplayQueueId === item.id || item.status === 'replayed'}
                                                className="rounded-md border border-blue-300 bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                                            >
                                                {adminReplayQueueId === item.id ? '재실행 중...' : item.status === 'replayed' ? '재실행됨' : 'worker 재실행'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
