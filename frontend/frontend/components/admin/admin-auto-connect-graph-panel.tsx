'use client';

import Link from 'next/link';
import type { AdminAutoConnectGraphEvent } from '@/lib/admin-auto-connect';

interface LookupCompletionItem {
    id: number;
    project_name: string;
    flow_id?: string | null;
    step_id?: string | null;
    action?: string | null;
    connection_id?: string | null;
    trace_id?: string | null;
}

interface LookupLogItem {
    id: number;
    status: string;
    message: string;
    connection_id?: string | null;
    trace_id?: string | null;
}

interface LookupRetryQueueItem {
    id: number;
    status: string;
    queue_name: string;
    attempt_count: number;
    max_attempts: number;
    connection_id?: string | null;
    trace_id?: string | null;
}

interface LookupResult {
    trace_key: string;
    connection_id: string;
    completions: LookupCompletionItem[];
    logs: LookupLogItem[];
    retry_queue: LookupRetryQueueItem[];
}

export interface AdminAutoConnectGraphPanelProps {
    activeEvent: AdminAutoConnectGraphEvent | null;
    events: AdminAutoConnectGraphEvent[];
    adminConnectionLookupId: string;
    onAdminConnectionLookupIdChange: (value: string) => void;
    onLoadActiveConnection: () => void;
    onLoadLookup: () => void;
    adminConnectionLookupLoading: boolean;
    adminConnectionLookupResult: LookupResult | null;
    adminReplayQueueId: number | null;
    onReplayRetryQueue: (id: number) => void;
}

export default function AdminAutoConnectGraphPanel({
    activeEvent,
    events,
    adminConnectionLookupId,
    onAdminConnectionLookupIdChange,
    onLoadActiveConnection,
    onLoadLookup,
    adminConnectionLookupLoading,
    adminConnectionLookupResult,
    adminReplayQueueId,
    onReplayRetryQueue,
}: AdminAutoConnectGraphPanelProps) {
    return (
        <div className="space-y-4">
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
                <p className="font-semibold">현재 active connection</p>
                <p className="mt-2 break-all text-base font-bold">{activeEvent?.connection_id || '없음'}</p>
                <p className="mt-1 text-xs text-indigo-800">
                    {activeEvent
                        ? `${activeEvent.panel_id} · ${activeEvent.flow_id} / ${activeEvent.step_id} / ${activeEvent.action}`
                        : '관리자 LLM 또는 대시보드 액션이 아직 graph에 기록되지 않았습니다.'}
                </p>
            </div>
            {events.length === 0 ? (
                <p className="text-sm text-gray-500">기록된 auto-connect graph 이벤트가 없습니다.</p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full text-xs">
                        <thead>
                            <tr className="border-b bg-gray-50 text-left text-gray-600">
                                <th className="px-3 py-2">상태</th>
                                <th className="px-3 py-2">connection_id</th>
                                <th className="px-3 py-2">패널 / route</th>
                                <th className="px-3 py-2">제목</th>
                                <th className="px-3 py-2">상세</th>
                                <th className="px-3 py-2">시간</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((event, index) => (
                                <tr key={`${event.id}:${index}`} className="border-b align-top text-gray-700 hover:bg-gray-50">
                                    <td className="px-3 py-2">{event.status}</td>
                                    <td className="break-all px-3 py-2 font-semibold text-indigo-700">{event.connection_id}</td>
                                    <td className="px-3 py-2">{event.panel_id}<br />{event.route_id}</td>
                                    <td className="px-3 py-2">{event.title}</td>
                                    <td className="max-w-[360px] whitespace-pre-wrap px-3 py-2">{event.detail}</td>
                                    <td className="whitespace-nowrap px-3 py-2">{new Date(event.created_at).toLocaleString('ko-KR', { hour12: false })}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="font-semibold text-slate-900">connection_id 기준 DB 조회</p>
                        <p className="mt-1 text-xs text-slate-600">active graph 또는 직접 입력한 connection_id로 completion/log/retry queue를 한 번에 확인합니다.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={onLoadActiveConnection}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        >
                            active 불러오기
                        </button>
                        <button
                            type="button"
                            onClick={onLoadLookup}
                            disabled={adminConnectionLookupLoading || !adminConnectionLookupId.trim()}
                            className="rounded-lg border border-indigo-300 bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                        >
                            {adminConnectionLookupLoading ? '조회 중...' : 'DB 조회'}
                        </button>
                    </div>
                </div>
                <div className="mt-3">
                    <input
                        id="admin-connection-lookup-id"
                        name="adminConnectionLookupId"
                        value={adminConnectionLookupId}
                        onChange={(event) => onAdminConnectionLookupIdChange(event.target.value)}
                        placeholder="FLOW-ADM-DASH:FLOW-ADM-DASH-2:OBSERVE:capability-id"
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
                    />
                </div>
                {adminConnectionLookupResult ? (
                    <div className="mt-4 space-y-3">
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                            <div className="rounded-lg border border-indigo-100 bg-white px-3 py-3 text-xs">
                                <p className="text-slate-500">trace_key</p>
                                <p className="mt-1 break-all font-semibold text-indigo-700">{adminConnectionLookupResult.trace_key}</p>
                            </div>
                            <div className="rounded-lg border border-emerald-100 bg-white px-3 py-3 text-xs">
                                <p className="text-slate-500">completion</p>
                                <p className="mt-1 font-semibold text-emerald-700">{adminConnectionLookupResult.completions.length}건</p>
                            </div>
                            <div className="rounded-lg border border-sky-100 bg-white px-3 py-3 text-xs">
                                <p className="text-slate-500">logs</p>
                                <p className="mt-1 font-semibold text-sky-700">{adminConnectionLookupResult.logs.length}건</p>
                            </div>
                            <div className="rounded-lg border border-amber-100 bg-white px-3 py-3 text-xs">
                                <p className="text-slate-500">retry queue</p>
                                <p className="mt-1 font-semibold text-amber-700">{adminConnectionLookupResult.retry_queue.length}건</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
                            <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
                                <p className="font-semibold text-gray-900">completion</p>
                                {adminConnectionLookupResult.completions.length === 0 ? <p className="mt-2 text-gray-500">조회 결과가 없습니다.</p> : (
                                    <div className="mt-2 space-y-2">
                                        {adminConnectionLookupResult.completions.map((item) => (
                                            <div key={`lookup-completion-${item.id}`} className="rounded-md border border-gray-200 px-3 py-2">
                                                <p className="font-semibold text-emerald-700">{item.project_name}</p>
                                                <p className="mt-1 text-gray-600">{item.flow_id || '-'} / {item.step_id || '-'} / {item.action || '-'}</p>
                                                <p className="mt-1 break-all text-[11px] text-gray-500">{item.connection_id || item.trace_id || '-'}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
                                <p className="font-semibold text-gray-900">logs</p>
                                {adminConnectionLookupResult.logs.length === 0 ? <p className="mt-2 text-gray-500">조회 결과가 없습니다.</p> : (
                                    <div className="mt-2 space-y-2">
                                        {adminConnectionLookupResult.logs.map((item) => (
                                            <div key={`lookup-log-${item.id}`} className="rounded-md border border-gray-200 px-3 py-2">
                                                <p className="font-semibold text-sky-700">{item.status}</p>
                                                <p className="mt-1 text-gray-700">{item.message}</p>
                                                <p className="mt-1 break-all text-[11px] text-gray-500">{item.connection_id || item.trace_id}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
                                <p className="font-semibold text-gray-900">retry queue</p>
                                {adminConnectionLookupResult.retry_queue.length === 0 ? <p className="mt-2 text-gray-500">조회 결과가 없습니다.</p> : (
                                    <div className="mt-2 space-y-2">
                                        {adminConnectionLookupResult.retry_queue.map((item) => (
                                            <div key={`lookup-queue-${item.id}`} className="rounded-md border border-gray-200 px-3 py-2">
                                                <div className="flex items-center justify-between gap-2">
                                                    <p className="font-semibold text-amber-700">#{item.id} · {item.status}</p>
                                                    <button
                                                        type="button"
                                                        onClick={() => onReplayRetryQueue(item.id)}
                                                        disabled={adminReplayQueueId === item.id || item.status === 'replayed'}
                                                        className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                                                    >
                                                        {adminReplayQueueId === item.id ? '재실행 중...' : item.status === 'replayed' ? '재실행됨' : 'worker 재실행'}
                                                    </button>
                                                </div>
                                                <p className="mt-1 text-gray-700">{item.queue_name} · {item.attempt_count}/{item.max_attempts}</p>
                                                <p className="mt-1 break-all text-[11px] text-gray-500">{item.connection_id || item.trace_id}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ) : (
                    <p className="mt-3 text-xs text-slate-500">조회할 connection_id를 입력하거나 active graph를 불러오세요.</p>
                )}
            </div>
            <div className="flex flex-wrap gap-2">
                <Link
                    href={activeEvent?.capability_id ? `/admin/llm?capability=${encodeURIComponent(activeEvent.capability_id)}` : '/admin/llm'}
                    className="rounded-lg border border-indigo-300 bg-white px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"
                >
                    active graph 상세 제어 열기
                </Link>
            </div>
        </div>
    );
}
