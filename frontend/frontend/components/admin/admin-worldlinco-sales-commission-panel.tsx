'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

type CommissionPolicy = {
    enabled?: boolean;
    initial_sale_percent?: number;
    recurring_user_fee_percent?: number;
    currency?: string;
    payment_condition?: string;
    settlement_mode?: string;
    settlement_cycle?: string;
    auto_settle_on_accrual?: boolean;
    min_payout_amount_minor?: number;
    approval_required?: boolean;
    note?: string;
};

type OfficeBankAccount = {
    country_code?: string;
    region_code?: string;
    office_name?: string | null;
    bank_name?: string;
    account_number_masked?: string;
    account_holder?: string;
    currency?: string;
    swift_code?: string | null;
    active?: boolean;
};

type LocalRevenuePolicy = {
    enabled?: boolean;
    mode?: string;
    note?: string;
    auto_settle_on_accrual?: boolean;
    fallback_to_hq_bank_enabled?: boolean;
    fallback_country_code?: string;
    fallback_region_code?: string;
};

type PayoutRecord = {
    id?: string;
    country_code?: string;
    region_code?: string;
    office_name?: string | null;
    bank_name?: string;
    account_number_masked?: string;
    account_holder?: string;
    amount_minor?: number;
    currency?: string;
    event_count?: number;
    transfer_reference?: string;
    transfer_simulated?: boolean;
    status?: string;
    created_at?: string;
};

type SalesAgent = {
    agent_id: string;
    name?: string;
    country_code?: string;
    region_code?: string;
    office_name?: string | null;
    contact_email?: string | null;
    active?: boolean;
    code?: string | null;
};

type CountrySettlement = {
    country_code: string;
    pending_minor: number;
    paid_out_minor?: number;
    approved_minor: number;
    awaiting_bank_minor?: number;
    event_count: number;
};

type AgentLedger = {
    agent_id: string;
    agent_name?: string;
    agent_code?: string;
    country_code?: string;
    pending_minor: number;
    paid_out_minor?: number;
    approved_minor: number;
    awaiting_bank_minor?: number;
    event_count: number;
};

type CommissionEvent = {
    id?: string;
    agent_name?: string;
    agent_code?: string;
    country_code?: string;
    user_id?: number;
    commission_type?: string;
    percent?: number;
    payment_amount_minor?: number;
    commission_amount_minor?: number;
    settlement_status?: string;
    created_at?: string;
};

type SalesCommissionDashboard = {
    updated_at?: string | null;
    commission_policy?: CommissionPolicy;
    local_revenue_settlement?: LocalRevenuePolicy;
    office_bank_accounts?: OfficeBankAccount[];
    agents?: SalesAgent[];
    country_settlements?: CountrySettlement[];
    agent_ledgers?: AgentLedger[];
    recent_events?: CommissionEvent[];
    recent_local_revenue_events?: Array<Record<string, unknown>>;
    recent_payouts?: PayoutRecord[];
    recent_local_revenue_payouts?: PayoutRecord[];
    stats?: {
        agent_count?: number;
        attribution_count?: number;
        pending_commission_minor?: number;
        awaiting_bank_commission_minor?: number;
        paid_out_commission_minor?: number;
        approved_commission_minor?: number;
        payout_count?: number;
        local_revenue_event_count?: number;
        pending_local_revenue_minor?: number;
        awaiting_bank_local_revenue_minor?: number;
        paid_out_local_revenue_minor?: number;
        local_revenue_payout_count?: number;
    };
};

type AgentDetail = SalesAgent & {
    invite_url?: string;
    deeplink?: string;
    qr_url?: string;
    attributed_users?: number;
    pending_commission_minor?: number;
    approved_commission_minor?: number;
};

type AdminWorldlincoSalesCommissionPanelProps = {
    apiBaseUrl: string;
};

function formatKrw(minor: number): string {
    return `${Number(minor || 0).toLocaleString('ko-KR')}원`;
}

export default function AdminWorldlincoSalesCommissionPanel({ apiBaseUrl }: AdminWorldlincoSalesCommissionPanelProps) {
    const base = apiBaseUrl.replace(/\/$/, '');
    const [payload, setPayload] = React.useState<SalesCommissionDashboard | null>(null);
    const [selectedAgent, setSelectedAgent] = React.useState<AgentDetail | null>(null);
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');

    const [policyEnabled, setPolicyEnabled] = React.useState(true);
    const [initialPercent, setInitialPercent] = React.useState('30');
    const [recurringPercent, setRecurringPercent] = React.useState('10');
    const [policyNote, setPolicyNote] = React.useState('');
    const [localRevenueEnabled, setLocalRevenueEnabled] = React.useState(true);
    const [localRevenueNote, setLocalRevenueNote] = React.useState('');
    const [hqFallbackEnabled, setHqFallbackEnabled] = React.useState(true);
    const [hqFallbackCountry, setHqFallbackCountry] = React.useState('KR');

    const [agentName, setAgentName] = React.useState('');
    const [agentCountry, setAgentCountry] = React.useState('KR');
    const [agentOffice, setAgentOffice] = React.useState('');
    const [agentEmail, setAgentEmail] = React.useState('');

    const [bankCountry, setBankCountry] = React.useState('KR');
    const [bankRegion, setBankRegion] = React.useState('KR');
    const [bankOfficeName, setBankOfficeName] = React.useState('');
    const [bankName, setBankName] = React.useState('');
    const [bankAccountNumber, setBankAccountNumber] = React.useState('');
    const [bankAccountHolder, setBankAccountHolder] = React.useState('');
    const [bankCurrency, setBankCurrency] = React.useState('KRW');
    const [bankSwift, setBankSwift] = React.useState('');

    const applyPayload = React.useCallback((data: SalesCommissionDashboard) => {
        setPayload(data);
        const policy = data.commission_policy || {};
        setPolicyEnabled(Boolean(policy.enabled));
        setInitialPercent(String(policy.initial_sale_percent ?? 30));
        setRecurringPercent(String(policy.recurring_user_fee_percent ?? 10));
        setPolicyNote(String(policy.note || ''));
        const localPolicy = data.local_revenue_settlement || {};
        setLocalRevenueEnabled(Boolean(localPolicy.enabled));
        setLocalRevenueNote(String(localPolicy.note || ''));
        setHqFallbackEnabled(localPolicy.fallback_to_hq_bank_enabled !== false);
        setHqFallbackCountry(String(localPolicy.fallback_country_code || 'KR'));
    }, []);

    const authHeaders = React.useCallback((): HeadersInit => {
        const token = getAdminToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
    }, []);

    const load = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission`, {
                headers: authHeaders(),
            });
            if (!response.ok) {
                throw new Error(`불러오기 실패 (${response.status})`);
            }
            applyPayload((await response.json()) as SalesCommissionDashboard);
        } catch (err) {
            setError(err instanceof Error ? err.message : '불러오기 실패');
        } finally {
            setLoading(false);
        }
    }, [applyPayload, authHeaders, base]);

    React.useEffect(() => {
        void load();
    }, [load]);

    const handleSavePolicy = async () => {
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/policy`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    enabled: policyEnabled,
                    initial_sale_percent: Number(initialPercent),
                    recurring_user_fee_percent: Number(recurringPercent),
                    note: policyNote.trim() || null,
                }),
            });
            if (!response.ok) {
                throw new Error(`저장 실패 (${response.status})`);
            }
            applyPayload((await response.json()) as SalesCommissionDashboard);
            setMessage('수수료 정책이 저장되었습니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveLocalRevenuePolicy = async () => {
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/local-revenue-policy`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    enabled: localRevenueEnabled,
                    mode: 'full_local_revenue',
                    fallback_to_hq_bank_enabled: hqFallbackEnabled,
                    fallback_country_code: hqFallbackCountry.trim().toUpperCase() || 'KR',
                    fallback_region_code: hqFallbackCountry.trim().toUpperCase() || 'KR',
                    note: localRevenueNote.trim() || null,
                }),
            });
            if (!response.ok) {
                throw new Error(`저장 실패 (${response.status})`);
            }
            applyPayload((await response.json()) as SalesCommissionDashboard);
            setMessage('현지 매출 정산 정책이 저장되었습니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleCreateAgent = async () => {
        if (!agentName.trim()) {
            setError('영업자 이름을 입력하세요.');
            return;
        }
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/agents`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    name: agentName.trim(),
                    country_code: agentCountry.trim().toUpperCase(),
                    office_name: agentOffice.trim() || null,
                    contact_email: agentEmail.trim() || null,
                    active: true,
                }),
            });
            if (!response.ok) {
                throw new Error(`영업자 생성 실패 (${response.status})`);
            }
            const created = (await response.json()) as AgentDetail;
            setSelectedAgent(created);
            setAgentName('');
            setAgentOffice('');
            setAgentEmail('');
            await load();
            setMessage(`영업자 QR 생성 완료: ${created.code}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '영업자 생성 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveBankAccount = async () => {
        if (!bankName.trim() || !bankAccountNumber.trim() || !bankAccountHolder.trim()) {
            setError('은행명, 계좌번호, 예금주를 입력하세요.');
            return;
        }
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/bank-accounts`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    country_code: bankCountry.trim().toUpperCase(),
                    region_code: bankRegion.trim().toUpperCase() || bankCountry.trim().toUpperCase(),
                    office_name: bankOfficeName.trim() || null,
                    bank_name: bankName.trim(),
                    account_number: bankAccountNumber.trim(),
                    account_holder: bankAccountHolder.trim(),
                    currency: bankCurrency.trim().toUpperCase() || 'KRW',
                    swift_code: bankSwift.trim() || null,
                    active: true,
                }),
            });
            if (!response.ok) {
                throw new Error(`통장 저장 실패 (${response.status})`);
            }
            const data = await response.json() as { dashboard?: SalesCommissionDashboard };
            if (data.dashboard) {
                applyPayload(data.dashboard);
            } else {
                await load();
            }
            setBankAccountNumber('');
            setMessage('지정 통장이 저장되었고, 대기 중인 현지 매출이 자동 이체됩니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '통장 저장 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleRunAutoSettlement = async (params: { country_code?: string; region_code?: string }) => {
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/settlements/run-auto`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify(params),
            });
            if (!response.ok) {
                throw new Error(`자동 정산 실행 실패 (${response.status})`);
            }
            const data = await response.json() as {
                settlement?: { paid_count?: number; total_commission_minor?: number; total_revenue_minor?: number; status?: string };
                dashboard?: SalesCommissionDashboard;
            };
            if (data.dashboard) {
                applyPayload(data.dashboard);
            } else {
                await load();
            }
            const count = data.settlement?.paid_count ?? 0;
            const total = data.settlement?.total_revenue_minor ?? data.settlement?.total_commission_minor ?? 0;
            setMessage(count > 0 ? `${count}건 · ${Number(total).toLocaleString()} (minor) 자동 이체 완료` : '이체할 대기 매출/수수료가 없거나 통장 미등록입니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '자동 정산 실행 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleLoadAgentDetail = async (agentId: string) => {
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/sales-commission/agents/${agentId}`, {
                headers: authHeaders(),
            });
            if (!response.ok) {
                throw new Error(`영업자 조회 실패 (${response.status})`);
            }
            setSelectedAgent((await response.json()) as AgentDetail);
        } catch (err) {
            setError(err instanceof Error ? err.message : '영업자 조회 실패');
        }
    };

    if (loading) {
        return <p className="text-sm text-muted-foreground">영업 수수료 정산 불러오는 중...</p>;
    }

    if (error && !payload) {
        return (
            <div className="space-y-2">
                <p className="text-sm text-destructive">{error}</p>
                <button type="button" className="text-sm underline" onClick={() => { void load(); }}>다시 시도</button>
            </div>
        );
    }

    const agents = payload?.agents || [];
    const countrySettlements = payload?.country_settlements || [];
    const agentLedgers = payload?.agent_ledgers || [];
    const recentEvents = payload?.recent_events || [];
    const recentPayouts = payload?.recent_payouts || [];
    const bankAccounts = payload?.office_bank_accounts || [];

    return (
        <div className="space-y-6">
            <div className="rounded-lg border p-4 space-y-4">
                <div>
                    <h3 className="text-sm font-semibold">영업 수수료 정책</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        초기 영업 30%, 재사용자 10%. 결제 확정 시 적립 후 국가·지역 영업부 지정 통장으로 자동 이체됩니다. 수동 승인 없이 즉시 정산됩니다.
                    </p>
                </div>
                <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={policyEnabled} onChange={(e) => setPolicyEnabled(e.target.checked)} />
                    수수료 정산 활성화
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">초기 영업 수수료 (%)</span>
                        <input className="w-full rounded border px-3 py-2" value={initialPercent} onChange={(e) => setInitialPercent(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">재사용자 관리비 (%)</span>
                        <input className="w-full rounded border px-3 py-2" value={recurringPercent} onChange={(e) => setRecurringPercent(e.target.value)} />
                    </label>
                </div>
                <label className="text-sm space-y-1 block">
                    <span className="text-muted-foreground">메모</span>
                    <textarea className="w-full rounded border px-3 py-2 min-h-[72px]" value={policyNote} onChange={(e) => setPolicyNote(e.target.value)} />
                </label>
                <button type="button" className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" disabled={saving} onClick={() => { void handleSavePolicy(); }}>
                    {saving ? '저장 중...' : '정책 저장'}
                </button>
            </div>

            <div className="rounded-lg border p-4 space-y-4">
                <div>
                    <h3 className="text-sm font-semibold">현지 통화 · 현지 매출 전액 정산</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        사용자 국가·결제 통화 기준으로 매출 전액을 해당 국가 영업부 지정 통장(현지 통화)으로 자동 이체합니다. 현지 통장이 없으면 본사 통장(기본 KR)으로 폴백합니다. 활성화 시 수수료는 장부 추적만 하고 별도 이체하지 않습니다.
                    </p>
                </div>
                <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={localRevenueEnabled} onChange={(e) => setLocalRevenueEnabled(e.target.checked)} />
                    현지 매출 전액 정산 활성화
                </label>
                <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={hqFallbackEnabled} onChange={(e) => setHqFallbackEnabled(e.target.checked)} />
                    현지 통장 미등록 시 본사 통장으로 폴백
                </label>
                <label className="text-sm space-y-1 block max-w-xs">
                    <span className="text-muted-foreground">본사 폴백 국가 코드</span>
                    <input className="w-full rounded border px-3 py-2 font-mono" value={hqFallbackCountry} onChange={(e) => setHqFallbackCountry(e.target.value)} disabled={!hqFallbackEnabled} />
                </label>
                <label className="text-sm space-y-1 block">
                    <span className="text-muted-foreground">메모</span>
                    <textarea className="w-full rounded border px-3 py-2 min-h-[72px]" value={localRevenueNote} onChange={(e) => setLocalRevenueNote(e.target.value)} />
                </label>
                <button type="button" className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" disabled={saving} onClick={() => { void handleSaveLocalRevenuePolicy(); }}>
                    {saving ? '저장 중...' : '현지 매출 정책 저장'}
                </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-5">
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">등록 영업자</p>
                    <p className="text-2xl font-bold">{payload?.stats?.agent_count ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">영업 귀속 가입</p>
                    <p className="text-2xl font-bold">{payload?.stats?.attribution_count ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">통장 미등록</p>
                    <p className="text-2xl font-bold">{formatKrw(payload?.stats?.awaiting_bank_commission_minor ?? 0)}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">자동 이체 완료</p>
                    <p className="text-2xl font-bold">{formatKrw(payload?.stats?.paid_out_commission_minor ?? 0)}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">현지 매출 이체 완료</p>
                    <p className="text-2xl font-bold">{formatKrw(payload?.stats?.paid_out_local_revenue_minor ?? 0)}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">현지 매출 통장 미등록</p>
                    <p className="text-2xl font-bold">{formatKrw(payload?.stats?.awaiting_bank_local_revenue_minor ?? 0)}</p>
                </div>
            </div>

            <div className="rounded-lg border p-4 space-y-4">
                <div>
                    <h3 className="text-sm font-semibold">국가·지역 영업부 지정 통장</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        국가/지역별 현지 매출 전액은 현지 통화 통장으로 이체됩니다. 현지 통장이 없으면 본사(KR) 통장으로 폴백하며, 본사 통장도 없으면 대기 상태로 쌓입니다.
                    </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">국가 코드</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={bankCountry} onChange={(e) => setBankCountry(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">지역 코드</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={bankRegion} onChange={(e) => setBankRegion(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">영업부명</span>
                        <input className="w-full rounded border px-3 py-2" value={bankOfficeName} onChange={(e) => setBankOfficeName(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">은행명</span>
                        <input className="w-full rounded border px-3 py-2" value={bankName} onChange={(e) => setBankName(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">계좌번호</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={bankAccountNumber} onChange={(e) => setBankAccountNumber(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">예금주</span>
                        <input className="w-full rounded border px-3 py-2" value={bankAccountHolder} onChange={(e) => setBankAccountHolder(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">통화 (ISO)</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={bankCurrency} onChange={(e) => setBankCurrency(e.target.value)} placeholder="KRW, THB, JPY..." />
                    </label>
                    <label className="text-sm space-y-1 sm:col-span-2">
                        <span className="text-muted-foreground">SWIFT (해외, 선택)</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={bankSwift} onChange={(e) => setBankSwift(e.target.value)} />
                    </label>
                </div>
                <button type="button" className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" disabled={saving} onClick={() => { void handleSaveBankAccount(); }}>
                    {saving ? '저장 중...' : '지정 통장 저장 · 자동 정산'}
                </button>
                {bankAccounts.length > 0 ? (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">국가/지역</th>
                                    <th className="px-3 py-2 text-left">영업부</th>
                                    <th className="px-3 py-2 text-left">은행</th>
                                    <th className="px-3 py-2 text-left">계좌</th>
                                    <th className="px-3 py-2 text-left">통화</th>
                                    <th className="px-3 py-2 text-left">예금주</th>
                                </tr>
                            </thead>
                            <tbody>
                                {bankAccounts.map((row) => (
                                    <tr key={`${row.country_code}-${row.region_code}`} className="border-t">
                                        <td className="px-3 py-2 font-mono text-xs">{row.country_code}/{row.region_code}</td>
                                        <td className="px-3 py-2">{row.office_name || '-'}</td>
                                        <td className="px-3 py-2">{row.bank_name}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{row.account_number_masked}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{row.currency || 'KRW'}</td>
                                        <td className="px-3 py-2">{row.account_holder}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : null}
            </div>

            <div className="rounded-lg border p-4 space-y-4">
                <h3 className="text-sm font-semibold">영업자 등록 · QR 생성</h3>
                <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">이름</span>
                        <input className="w-full rounded border px-3 py-2" value={agentName} onChange={(e) => setAgentName(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">국가 코드</span>
                        <input className="w-full rounded border px-3 py-2 font-mono" value={agentCountry} onChange={(e) => setAgentCountry(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">영업부/지사</span>
                        <input className="w-full rounded border px-3 py-2" value={agentOffice} onChange={(e) => setAgentOffice(e.target.value)} />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">연락 이메일</span>
                        <input className="w-full rounded border px-3 py-2" value={agentEmail} onChange={(e) => setAgentEmail(e.target.value)} />
                    </label>
                </div>
                <button type="button" className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" disabled={saving} onClick={() => { void handleCreateAgent(); }}>
                    {saving ? '생성 중...' : '영업자 QR 생성'}
                </button>
            </div>

            {selectedAgent ? (
                <div className="rounded-lg border p-4 space-y-3">
                    <h3 className="text-sm font-semibold">선택 영업자 QR · {selectedAgent.name}</h3>
                    <p className="text-xs font-mono">{selectedAgent.code}</p>
                    {selectedAgent.qr_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={selectedAgent.qr_url} alt="sales-agent-qr" className="h-40 w-40 rounded border bg-white p-2" />
                    ) : null}
                    <p className="text-xs break-all text-muted-foreground">{selectedAgent.invite_url}</p>
                    <p className="text-xs break-all text-muted-foreground">{selectedAgent.deeplink}</p>
                    <p className="text-sm">귀속 가입 {selectedAgent.attributed_users ?? 0}명 · 대기 {formatKrw(selectedAgent.pending_commission_minor ?? 0)}</p>
                </div>
            ) : null}

            <div>
                <h3 className="mb-2 text-sm font-semibold">등록 영업자</h3>
                {agents.length === 0 ? (
                    <p className="text-sm text-muted-foreground">등록된 영업자가 없습니다.</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">이름</th>
                                    <th className="px-3 py-2 text-left">국가</th>
                                    <th className="px-3 py-2 text-left">코드</th>
                                    <th className="px-3 py-2 text-left">QR</th>
                                </tr>
                            </thead>
                            <tbody>
                                {agents.map((agent) => (
                                    <tr key={agent.agent_id} className="border-t">
                                        <td className="px-3 py-2">{agent.name}</td>
                                        <td className="px-3 py-2">{agent.country_code}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{agent.code}</td>
                                        <td className="px-3 py-2">
                                            <button type="button" className="text-xs underline" onClick={() => { void handleLoadAgentDetail(agent.agent_id); }}>
                                                QR 보기
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold">국가별 정산 현황</h3>
                    <button type="button" className="text-xs underline disabled:opacity-50" disabled={saving} onClick={() => { void handleRunAutoSettlement({}); }}>
                        전체 자동 정산 실행
                    </button>
                </div>
                {countrySettlements.length === 0 ? (
                    <p className="text-sm text-muted-foreground">정산 내역 없음</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">국가</th>
                                    <th className="px-3 py-2 text-right">통장 미등록</th>
                                    <th className="px-3 py-2 text-right">이체 완료</th>
                                    <th className="px-3 py-2 text-right">건수</th>
                                    <th className="px-3 py-2 text-right">재실행</th>
                                </tr>
                            </thead>
                            <tbody>
                                {countrySettlements.map((row) => (
                                    <tr key={row.country_code} className="border-t">
                                        <td className="px-3 py-2 font-mono">{row.country_code}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(row.awaiting_bank_minor ?? 0)}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(row.paid_out_minor ?? row.approved_minor)}</td>
                                        <td className="px-3 py-2 text-right">{row.event_count}</td>
                                        <td className="px-3 py-2 text-right">
                                            <button
                                                type="button"
                                                className="text-xs underline disabled:opacity-50"
                                                disabled={saving}
                                                onClick={() => { void handleRunAutoSettlement({ country_code: row.country_code }); }}
                                            >
                                                국가 자동 이체
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div>
                <h3 className="mb-2 text-sm font-semibold">영업자별 원장</h3>
                {agentLedgers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">원장 없음</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">영업자</th>
                                    <th className="px-3 py-2 text-left">코드</th>
                                    <th className="px-3 py-2 text-right">통장 미등록</th>
                                    <th className="px-3 py-2 text-right">이체 완료</th>
                                </tr>
                            </thead>
                            <tbody>
                                {agentLedgers.map((row) => (
                                    <tr key={row.agent_id} className="border-t">
                                        <td className="px-3 py-2">{row.agent_name || row.agent_id.slice(0, 8)}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{row.agent_code}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(row.awaiting_bank_minor ?? 0)}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(row.paid_out_minor ?? row.approved_minor)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div>
                <h3 className="mb-2 text-sm font-semibold">최근 자동 이체 내역</h3>
                {recentPayouts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">이체 내역 없음</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">시각</th>
                                    <th className="px-3 py-2 text-left">국가/지역</th>
                                    <th className="px-3 py-2 text-left">통장</th>
                                    <th className="px-3 py-2 text-right">금액</th>
                                    <th className="px-3 py-2 text-left">참조</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentPayouts.slice(0, 20).map((payout) => (
                                    <tr key={payout.id} className="border-t">
                                        <td className="px-3 py-2 text-xs">{payout.created_at?.replace('T', ' ').slice(0, 19)}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{payout.country_code}/{payout.region_code}</td>
                                        <td className="px-3 py-2 text-xs">{payout.bank_name} {payout.account_number_masked}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(payout.amount_minor ?? 0)}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{payout.transfer_reference}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div>
                <h3 className="mb-2 text-sm font-semibold">최근 수수료 이벤트</h3>
                {recentEvents.length === 0 ? (
                    <p className="text-sm text-muted-foreground">이벤트 없음</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">시각</th>
                                    <th className="px-3 py-2 text-left">영업자</th>
                                    <th className="px-3 py-2 text-left">유형</th>
                                    <th className="px-3 py-2 text-right">수수료</th>
                                    <th className="px-3 py-2 text-left">상태</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentEvents.slice(0, 30).map((event) => (
                                    <tr key={event.id} className="border-t">
                                        <td className="px-3 py-2 text-xs">{event.created_at?.replace('T', ' ').slice(0, 19)}</td>
                                        <td className="px-3 py-2">{event.agent_name}</td>
                                        <td className="px-3 py-2 text-xs">{event.commission_type} ({event.percent}%)</td>
                                        <td className="px-3 py-2 text-right">{formatKrw(event.commission_amount_minor ?? 0)}</td>
                                        <td className="px-3 py-2 text-xs">{event.settlement_status}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {(message || error) ? (
                <div className="text-sm">
                    {message ? <p className="text-green-700">{message}</p> : null}
                    {error ? <p className="text-destructive">{error}</p> : null}
                </div>
            ) : null}
        </div>
    );
}
