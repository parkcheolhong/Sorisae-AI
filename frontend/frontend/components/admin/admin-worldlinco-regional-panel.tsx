'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

type RegionalManager = {
    manager_id: string;
    user_id: number;
    name?: string;
    country_code?: string;
    region_code?: string;
    office_name?: string | null;
    contact_email?: string | null;
    active?: boolean;
};

type RegionalUser = {
    user_id: number;
    username?: string;
    email?: string;
    full_name?: string | null;
    agent_name?: string;
    agent_code?: string;
    created_at?: string;
    user_created_at?: string | null;
    is_active?: boolean;
    payment_count?: number;
    paid_commission_minor?: number;
    pending_commission_minor?: number;
    has_initial_payment?: boolean;
};

type RegionalDashboard = {
    country_code?: string;
    region_code?: string;
    scope?: Record<string, unknown>;
    stats?: {
        attributed_users?: number;
        paying_users?: number;
        agent_count?: number;
        pending_commission_minor?: number;
        awaiting_bank_commission_minor?: number;
        paid_out_commission_minor?: number;
        payout_count?: number;
        local_revenue_event_count?: number;
        pending_local_revenue_minor?: number;
        awaiting_bank_local_revenue_minor?: number;
        paid_out_local_revenue_minor?: number;
        local_revenue_payout_count?: number;
    };
    agent_summaries?: Array<{
        agent_id: string;
        agent_name?: string;
        agent_code?: string;
        attributed_users?: number;
        paid_out_minor?: number;
        pending_minor?: number;
    }>;
    recent_events?: Array<Record<string, unknown>>;
    recent_payouts?: Array<Record<string, unknown>>;
    office_bank_account?: Record<string, unknown> | null;
};

type AdminWorldlincoRegionalPanelProps = {
    apiBaseUrl: string;
    mode?: 'admin' | 'regional';
};

function formatKrw(minor: number): string {
    return `${Number(minor || 0).toLocaleString('ko-KR')}원`;
}

export default function AdminWorldlincoRegionalPanel({
    apiBaseUrl,
    mode = 'admin',
}: AdminWorldlincoRegionalPanelProps) {
    const base = apiBaseUrl.replace(/\/$/, '');
    const isAdminMode = mode === 'admin';

    const [dashboard, setDashboard] = React.useState<RegionalDashboard | null>(null);
    const [users, setUsers] = React.useState<RegionalUser[]>([]);
    const [managers, setManagers] = React.useState<RegionalManager[]>([]);
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');

    const [viewCountry, setViewCountry] = React.useState('KR');
    const [viewRegion, setViewRegion] = React.useState('KR');

    const [managerUserId, setManagerUserId] = React.useState('');
    const [managerName, setManagerName] = React.useState('');
    const [managerCountry, setManagerCountry] = React.useState('KR');
    const [managerRegion, setManagerRegion] = React.useState('KR');
    const [managerOffice, setManagerOffice] = React.useState('');
    const [managerEmail, setManagerEmail] = React.useState('');

    const authHeaders = React.useCallback((): HeadersInit => {
        const token = getAdminToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
    }, []);

    const scopeQuery = React.useCallback(() => {
        if (!isAdminMode) {
            return '';
        }
        const params = new URLSearchParams({
            country_code: viewCountry.trim().toUpperCase(),
            region_code: (viewRegion.trim() || viewCountry).toUpperCase(),
        });
        return `?${params.toString()}`;
    }, [isAdminMode, viewCountry, viewRegion]);

    const loadManagers = React.useCallback(async () => {
        if (!isAdminMode) {
            return;
        }
        const response = await fetch(`${base}/api/admin/worldlinco/regional/managers`, { headers: authHeaders() });
        if (!response.ok) {
            throw new Error(`지역 관리자 목록 불러오기 실패 (${response.status})`);
        }
        const data = await response.json() as { managers?: RegionalManager[] };
        setManagers(data.managers || []);
    }, [authHeaders, base, isAdminMode]);

    const loadRegionalData = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const query = scopeQuery();
            const usersQuery = query ? `${query}&limit=100` : '?limit=100';
            const [dashboardRes, usersRes] = await Promise.all([
                fetch(`${base}/api/admin/worldlinco/regional/dashboard${query}`, { headers: authHeaders() }),
                fetch(`${base}/api/admin/worldlinco/regional/users${usersQuery}`, { headers: authHeaders() }),
            ]);
            if (!dashboardRes.ok) {
                throw new Error(`대시보드 불러오기 실패 (${dashboardRes.status})`);
            }
            if (!usersRes.ok) {
                throw new Error(`유저 목록 불러오기 실패 (${usersRes.status})`);
            }
            setDashboard((await dashboardRes.json()) as RegionalDashboard);
            const usersData = await usersRes.json() as { users?: RegionalUser[] };
            setUsers(usersData.users || []);
            if (isAdminMode) {
                await loadManagers();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '불러오기 실패');
        } finally {
            setLoading(false);
        }
    }, [authHeaders, base, isAdminMode, loadManagers, scopeQuery]);

    React.useEffect(() => {
        void loadRegionalData();
    }, [loadRegionalData]);

    const handleCreateManager = async () => {
        const userId = Number(managerUserId);
        if (!Number.isFinite(userId) || userId <= 0 || !managerName.trim()) {
            setError('user_id와 이름을 입력하세요.');
            return;
        }
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const response = await fetch(`${base}/api/admin/worldlinco/regional/managers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    user_id: userId,
                    name: managerName.trim(),
                    country_code: managerCountry.trim().toUpperCase(),
                    region_code: (managerRegion.trim() || managerCountry).toUpperCase(),
                    office_name: managerOffice.trim() || null,
                    contact_email: managerEmail.trim() || null,
                    active: true,
                }),
            });
            if (!response.ok) {
                throw new Error(`지역 관리자 등록 실패 (${response.status})`);
            }
            const data = await response.json() as { managers?: RegionalManager[] };
            setManagers(data.managers || []);
            setManagerUserId('');
            setManagerName('');
            setManagerOffice('');
            setManagerEmail('');
            setMessage('지역 관리자가 등록되었습니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '등록 실패');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <p className="text-sm text-muted-foreground">지역 관리자 대시보드 불러오는 중...</p>;
    }

    if (error && !dashboard) {
        return (
            <div className="space-y-2">
                <p className="text-sm text-destructive">{error}</p>
                <button type="button" className="text-sm underline" onClick={() => { void loadRegionalData(); }}>다시 시도</button>
            </div>
        );
    }

    const stats = dashboard?.stats || {};

    return (
        <div className="space-y-6">
            <div className="rounded-lg border p-4 space-y-3">
                <div>
                    <h3 className="text-sm font-semibold">
                        {isAdminMode ? '지역 관리자 · 국가/지역 유저 대시보드' : '내 담당 지역 유저 관리'}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        영업 QR로 귀속된 가입자만 표시됩니다. 담당: {dashboard?.country_code}/{dashboard?.region_code}
                    </p>
                </div>
                {isAdminMode ? (
                    <div className="grid gap-3 sm:grid-cols-3">
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">국가 코드</span>
                            <input className="w-full rounded border px-3 py-2 font-mono" value={viewCountry} onChange={(e) => setViewCountry(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">지역 코드</span>
                            <input className="w-full rounded border px-3 py-2 font-mono" value={viewRegion} onChange={(e) => setViewRegion(e.target.value)} />
                        </label>
                        <div className="flex items-end">
                            <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => { void loadRegionalData(); }}>
                                조회
                            </button>
                        </div>
                    </div>
                ) : null}
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">귀속 가입자</p>
                    <p className="text-2xl font-bold">{stats.attributed_users ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">결제 유저</p>
                    <p className="text-2xl font-bold">{stats.paying_users ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">현지 매출 이체 완료</p>
                    <p className="text-2xl font-bold">{formatKrw(stats.paid_out_local_revenue_minor ?? 0)}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">영업자 수</p>
                    <p className="text-2xl font-bold">{stats.agent_count ?? 0}</p>
                </div>
            </div>

            {isAdminMode ? (
                <div className="rounded-lg border p-4 space-y-4">
                    <h3 className="text-sm font-semibold">지역 관리자 등록</h3>
                    <p className="text-xs text-muted-foreground">
                        가입된 users.id 를 지정하면 해당 국가·지역 대시보드만 로그인 후 볼 수 있습니다. (/admin/regional)
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">User ID</span>
                            <input className="w-full rounded border px-3 py-2 font-mono" value={managerUserId} onChange={(e) => setManagerUserId(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">이름</span>
                            <input className="w-full rounded border px-3 py-2" value={managerName} onChange={(e) => setManagerName(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">국가</span>
                            <input className="w-full rounded border px-3 py-2 font-mono" value={managerCountry} onChange={(e) => setManagerCountry(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">지역</span>
                            <input className="w-full rounded border px-3 py-2 font-mono" value={managerRegion} onChange={(e) => setManagerRegion(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">영업부</span>
                            <input className="w-full rounded border px-3 py-2" value={managerOffice} onChange={(e) => setManagerOffice(e.target.value)} />
                        </label>
                        <label className="text-sm space-y-1">
                            <span className="text-muted-foreground">이메일</span>
                            <input className="w-full rounded border px-3 py-2" value={managerEmail} onChange={(e) => setManagerEmail(e.target.value)} />
                        </label>
                    </div>
                    <button type="button" className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" disabled={saving} onClick={() => { void handleCreateManager(); }}>
                        {saving ? '등록 중...' : '지역 관리자 등록'}
                    </button>
                    {managers.length > 0 ? (
                        <div className="overflow-x-auto rounded-lg border">
                            <table className="min-w-full text-sm">
                                <thead className="bg-muted/40">
                                    <tr>
                                        <th className="px-3 py-2 text-left">이름</th>
                                        <th className="px-3 py-2 text-left">User ID</th>
                                        <th className="px-3 py-2 text-left">국가/지역</th>
                                        <th className="px-3 py-2 text-left">상태</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {managers.map((row) => (
                                        <tr key={row.manager_id} className="border-t">
                                            <td className="px-3 py-2">{row.name}</td>
                                            <td className="px-3 py-2 font-mono">{row.user_id}</td>
                                            <td className="px-3 py-2 font-mono text-xs">{row.country_code}/{row.region_code}</td>
                                            <td className="px-3 py-2">{row.active ? '활성' : '비활성'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : null}
                </div>
            ) : null}

            <div>
                <h3 className="mb-2 text-sm font-semibold">귀속 가입 유저 ({users.length}명)</h3>
                {users.length === 0 ? (
                    <p className="text-sm text-muted-foreground">해당 지역 귀속 유저가 없습니다.</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">유저</th>
                                    <th className="px-3 py-2 text-left">이메일</th>
                                    <th className="px-3 py-2 text-left">영업자</th>
                                    <th className="px-3 py-2 text-left">가입</th>
                                    <th className="px-3 py-2 text-right">결제</th>
                                    <th className="px-3 py-2 text-right">수수료</th>
                                    <th className="px-3 py-2 text-left">상태</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((user) => (
                                    <tr key={user.user_id} className="border-t">
                                        <td className="px-3 py-2">{user.username || `#${user.user_id}`}</td>
                                        <td className="px-3 py-2 text-xs">{user.email}</td>
                                        <td className="px-3 py-2 text-xs">{user.agent_name} <span className="font-mono">{user.agent_code}</span></td>
                                        <td className="px-3 py-2 text-xs">{(user.user_created_at || user.created_at || '').replace('T', ' ').slice(0, 10)}</td>
                                        <td className="px-3 py-2 text-right">{user.payment_count ?? 0}</td>
                                        <td className="px-3 py-2 text-right">{formatKrw((user.paid_commission_minor ?? 0) + (user.pending_commission_minor ?? 0))}</td>
                                        <td className="px-3 py-2 text-xs">{user.is_active === false ? '비활성' : user.has_initial_payment ? '결제함' : '미결제'}</td>
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
