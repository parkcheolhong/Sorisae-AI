'use client';

import type { AdminAdOrderMonitorSummary, AdminAdOrderSettlementDashboard } from '@/lib/admin-dashboard-types';

interface AdminAdOrdersSummaryBlockProps {
    monitor: AdminAdOrderMonitorSummary | null;
    settlement: AdminAdOrderSettlementDashboard | null;
    settlementExporting: boolean;
    monitorApiUnavailable: boolean;
    settlementApiUnavailable: boolean;
    total: number;
    open: boolean;
    onOpenChange: (value: boolean | ((prev: boolean) => boolean)) => void;
    onRefresh: () => void;
    onExportSettlementCsv: () => void;
    buildSettlementConnectionId: (orderId: number) => string;
}

export default function AdminAdOrdersSummaryBlock({
    monitor,
    settlement,
    settlementExporting,
    monitorApiUnavailable,
    settlementApiUnavailable,
    total,
    open,
    onOpenChange,
    onRefresh,
    onExportSettlementCsv,
    buildSettlementConnectionId,
}: AdminAdOrdersSummaryBlockProps) {
    return (
        <>
            <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold text-gray-900">🎬 광고 영상 주문 모니터링</h2>
                    <button type="button" onClick={onRefresh} className="rounded-md border border-indigo-300 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50" data-testid="admin-storyboard-orders-refresh">주문 새로고침</button>
                    <button type="button" onClick={() => onOpenChange((prev) => !prev)} className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50" data-testid="admin-storyboard-orders-toggle">{open ? '접기' : '펼치기'}</button>
                    <button type="button" onClick={onExportSettlementCsv} disabled={settlementExporting} className="rounded-md border border-emerald-300 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50">{settlementExporting ? 'CSV 생성 중...' : 'CSV 정산 다운로드'}</button>
                </div>
                <span className="text-xs text-gray-500">최근 20건 / 전체 {total}건</span>
            </div>
            {monitor && (
                <div className="mb-4 space-y-4">
                    {(monitorApiUnavailable || settlementApiUnavailable) && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">최신 백엔드 관리자 정산 API가 아직 로드되지 않아 현재는 프런트 fallback 집계로 연결 중입니다. 백엔드 재시작 후 자동으로 서버 집계로 복귀합니다.</div>
                    )}
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
                        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-xs text-indigo-900"><p className="font-semibold">총 주문</p><p className="mt-2 text-2xl font-bold">{monitor.totals.total_orders.toLocaleString('ko-KR')}</p><p className="mt-1">활성 {monitor.totals.active_orders} · 완료 {monitor.totals.completed_orders}</p></div>
                        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900"><p className="font-semibold">완료율</p><p className="mt-2 text-2xl font-bold">{monitor.totals.completion_rate}%</p><p className="mt-1">평균 진행률 {monitor.totals.average_progress}%</p></div>
                        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900"><p className="font-semibold">실패율</p><p className="mt-2 text-2xl font-bold">{monitor.totals.failure_rate}%</p><p className="mt-1">실패 {monitor.totals.failed_orders}건</p></div>
                        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900"><p className="font-semibold">토큰 집계</p><p className="mt-2 text-2xl font-bold">{monitor.token_summary.estimated_total_tokens.toLocaleString('ko-KR')}</p><p className="mt-1">주문당 평균 {Math.round(monitor.token_summary.estimated_avg_tokens_per_order).toLocaleString('ko-KR')}</p></div>
                        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-xs text-sky-900"><p className="font-semibold">정산 라인</p><p className="mt-2 text-2xl font-bold">{monitor.settlement.total_estimated_cost.toLocaleString('ko-KR')} USD</p><p className="mt-1">주문당 {monitor.settlement.estimated_cost_per_order.toLocaleString('ko-KR')} USD</p></div>
                    </div>
                    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                        {[
                            { title: '상태 비율', items: monitor.ratios.status, barClass: 'bg-indigo-500' },
                            { title: '엔진 비율', items: monitor.ratios.engine, barClass: 'bg-emerald-500' },
                            { title: '품질 비율', items: monitor.ratios.quality, barClass: 'bg-amber-500' },
                        ].map(({ title, items, barClass }) => (
                            <div key={String(title)} className="rounded-lg border border-gray-200 bg-white p-4">
                                <p className="text-sm font-semibold text-gray-900">{title}</p>
                                <div className="mt-3 space-y-3">
                                    {items.map((item) => (
                                        <div key={item.key}>
                                            <div className="flex items-center justify-between text-xs text-gray-700"><span>{item.label}</span><span>{item.count}건 · {item.ratio}%</span></div>
                                            <div className="mt-1 h-2 rounded-full bg-gray-100"><div className={`h-2 rounded-full ${barClass}`} style={{ width: `${Math.max(4, item.ratio)}%` }} /></div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-800">
                        <p className="font-semibold text-gray-900">토큰 수 집계 / 정산 라인</p>
                        <div className="mt-3 grid grid-cols-1 gap-3 text-xs md:grid-cols-4">
                            <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2"><p className="text-gray-500">프롬프트 토큰</p><p className="mt-1 font-semibold text-gray-900">{monitor.token_summary.estimated_prompt_tokens.toLocaleString('ko-KR')}</p></div>
                            <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2"><p className="text-gray-500">렌더 토큰</p><p className="mt-1 font-semibold text-gray-900">{monitor.token_summary.estimated_render_tokens.toLocaleString('ko-KR')}</p></div>
                            <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2"><p className="text-gray-500">로컬/외부/저장</p><p className="mt-1 font-semibold text-gray-900">{monitor.settlement.local_cost_total.toFixed(2)} / {monitor.settlement.external_cost_total.toFixed(2)} / {monitor.settlement.storage_cost_total.toFixed(2)} USD</p></div>
                            <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2"><p className="text-blue-600">정산 요약</p><p className="mt-1 font-semibold text-blue-900">{monitor.settlement.settlement_line}</p></div>
                        </div>
                    </div>
                </div>
            )}
            {settlement && (
                <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                        <p className="text-sm font-semibold text-gray-900">일별 정산 차트</p>
                        <div className="mt-3 space-y-3">
                            {settlement.daily.map((point) => {
                                const width = Math.max(6, Math.min(100, point.total_cost * 10));
                                return <div key={`daily-${point.period}`}><div className="flex items-center justify-between text-xs text-gray-700"><span>{point.period}</span><span>{point.order_count}건 · {point.total_tokens.toLocaleString('ko-KR')} tokens · {point.total_cost.toFixed(2)} USD</span></div><div className="mt-1 h-2 rounded-full bg-gray-100"><div className="h-2 rounded-full bg-indigo-500" style={{ width: `${width}%` }} /></div></div>;
                            })}
                        </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                        <p className="text-sm font-semibold text-gray-900">월별 정산 차트</p>
                        <div className="mt-3 space-y-3">
                            {settlement.monthly.map((point) => {
                                const width = Math.max(6, Math.min(100, point.total_cost * 5));
                                return <div key={`monthly-${point.period}`}><div className="flex items-center justify-between text-xs text-gray-700"><span>{point.period}</span><span>{point.order_count}건 · {point.total_tokens.toLocaleString('ko-KR')} tokens · {point.total_cost.toFixed(2)} USD</span></div><div className="mt-1 h-2 rounded-full bg-gray-100"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${width}%` }} /></div></div>;
                            })}
                        </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-white p-4 xl:col-span-2">
                        <div className="flex items-center justify-between gap-3"><p className="text-sm font-semibold text-gray-900">주문별 실제 토큰/비용 로그 테이블</p><span className="text-xs text-gray-500">{settlement.settlement_line}</span></div>
                        <div className="mt-3 overflow-x-auto">
                            <table className="min-w-full text-xs">
                                <thead><tr className="border-b bg-gray-50 text-left text-gray-600"><th className="px-3 py-2">주문ID</th><th className="px-3 py-2">사용자</th><th className="px-3 py-2">상태</th><th className="px-3 py-2">엔진</th><th className="px-3 py-2">품질</th><th className="px-3 py-2">프롬프트 토큰</th><th className="px-3 py-2">렌더 토큰</th><th className="px-3 py-2">총 토큰</th><th className="px-3 py-2">정산 비용</th><th className="px-3 py-2">connection_id</th><th className="px-3 py-2">기준일</th></tr></thead>
                                <tbody>
                                    {settlement.recent_logs.map((log) => {
                                        const settlementConnectionId = buildSettlementConnectionId(log.order_id);
                                        return <tr key={`settlement-log-${log.order_id}-${log.period_day}`} className="border-b text-gray-700 hover:bg-gray-50"><td className="px-3 py-2">#{log.order_id}</td><td className="px-3 py-2">{log.user_id}</td><td className="px-3 py-2">{log.status}</td><td className="px-3 py-2">{log.engine_type}</td><td className="px-3 py-2">{log.render_quality}</td><td className="px-3 py-2">{log.prompt_tokens.toLocaleString('ko-KR')}</td><td className="px-3 py-2">{log.render_tokens.toLocaleString('ko-KR')}</td><td className="px-3 py-2 font-semibold text-gray-900">{log.total_tokens.toLocaleString('ko-KR')}</td><td className="px-3 py-2">{log.total_cost.toFixed(2)} {log.currency}</td><td className="break-all px-3 py-2 text-[11px] text-indigo-700">{settlementConnectionId}</td><td className="px-3 py-2">{log.period_day}</td></tr>;
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
