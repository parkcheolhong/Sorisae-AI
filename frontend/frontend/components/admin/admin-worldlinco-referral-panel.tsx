'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

type ReferralSignup = {
    id?: string;
    referrer_user_id?: number;
    referrer_username?: string;
    referrer_code?: string;
    referred_user_id?: number;
    referred_username?: string;
    referred_email?: string;
    created_at?: string;
    first_payment_discount_applied_at?: string | null;
};

type ReferralDiscountPolicy = {
    enabled?: boolean;
    percent?: number;
    applies_to?: string;
    target?: string;
    stripe_coupon_id?: string | null;
    google_offer_id?: string | null;
    apple_offer_id?: string | null;
    note?: string;
};

type ReferralDashboardPayload = {
    updated_at?: string | null;
    total_signups: number;
    referrer_count: number;
    leaders: Array<{
        referrer_user_id: number;
        referrer_username?: string;
        referrer_code?: string;
        signup_count: number;
    }>;
    recent_signups: ReferralSignup[];
    discount_policy?: ReferralDiscountPolicy;
    discount_stats?: {
        eligible_pending?: number;
        discount_applied_count?: number;
    };
};

type AdminWorldlincoReferralPanelProps = {
    apiBaseUrl: string;
};

export default function AdminWorldlincoReferralPanel({ apiBaseUrl }: AdminWorldlincoReferralPanelProps) {
    const [payload, setPayload] = React.useState<ReferralDashboardPayload | null>(null);
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');

    const [discountEnabled, setDiscountEnabled] = React.useState(false);
    const [discountPercent, setDiscountPercent] = React.useState('3');
    const [stripeCouponId, setStripeCouponId] = React.useState('');
    const [googleOfferId, setGoogleOfferId] = React.useState('referral-first-payment-3pct');
    const [appleOfferId, setAppleOfferId] = React.useState('referral-first-payment-3pct');
    const [discountNote, setDiscountNote] = React.useState('');

    const applyPayload = React.useCallback((data: ReferralDashboardPayload) => {
        setPayload(data);
        const policy = data.discount_policy || {};
        setDiscountEnabled(Boolean(policy.enabled));
        setDiscountPercent(String(policy.percent ?? 3));
        setStripeCouponId(String(policy.stripe_coupon_id || ''));
        setGoogleOfferId(String(policy.google_offer_id || 'referral-first-payment-3pct'));
        setAppleOfferId(String(policy.apple_offer_id || 'referral-first-payment-3pct'));
        setDiscountNote(String(policy.note || ''));
    }, []);

    const load = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/referrals`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!response.ok) {
                throw new Error(`불러오기 실패 (${response.status})`);
            }
            const data = (await response.json()) as ReferralDashboardPayload;
            applyPayload(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : '불러오기 실패');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, applyPayload]);

    React.useEffect(() => {
        load();
    }, [load]);

    const handleSaveDiscountPolicy = async () => {
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/referrals/discount-policy`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    enabled: discountEnabled,
                    percent: Number(discountPercent),
                    stripe_coupon_id: stripeCouponId.trim() || null,
                    google_offer_id: googleOfferId.trim() || null,
                    apple_offer_id: appleOfferId.trim() || null,
                    note: discountNote.trim() || null,
                }),
            });
            if (!response.ok) {
                throw new Error(`저장 실패 (${response.status})`);
            }
            const data = (await response.json()) as ReferralDashboardPayload;
            applyPayload(data);
            setMessage('추천 할인 정책이 저장되었습니다.');
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <p className="text-sm text-muted-foreground">추천인 집계 불러오는 중...</p>;
    }

    if (error && !payload) {
        return (
            <div className="space-y-2">
                <p className="text-sm text-destructive">{error}</p>
                <button type="button" className="text-sm underline" onClick={() => { load(); }}>다시 시도</button>
            </div>
        );
    }

    const leaders = payload?.leaders || [];
    const recent = payload?.recent_signups || [];

    return (
        <div className="space-y-6">
            <div className="rounded-lg border p-4 space-y-4">
                <div>
                    <h3 className="text-sm font-semibold">추천 첫 결제 할인 정책</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        추천 QR로 가입한 사용자의 첫 결제에 Stripe · Google Play · App Store 할인을 자동 적용합니다.
                    </p>
                </div>
                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={discountEnabled}
                        onChange={(event) => setDiscountEnabled(event.target.checked)}
                    />
                    할인 활성화 (ON/OFF)
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">할인율 (%)</span>
                        <input
                            className="w-full rounded border px-3 py-2"
                            value={discountPercent}
                            onChange={(event) => setDiscountPercent(event.target.value)}
                        />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">Stripe Coupon ID (선택)</span>
                        <input
                            className="w-full rounded border px-3 py-2 font-mono text-xs"
                            value={stripeCouponId}
                            onChange={(event) => setStripeCouponId(event.target.value)}
                            placeholder="비우면 Checkout 시 자동 생성"
                        />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">Google Play Offer ID</span>
                        <input
                            className="w-full rounded border px-3 py-2 font-mono text-xs"
                            value={googleOfferId}
                            onChange={(event) => setGoogleOfferId(event.target.value)}
                        />
                    </label>
                    <label className="text-sm space-y-1">
                        <span className="text-muted-foreground">App Store Offer ID</span>
                        <input
                            className="w-full rounded border px-3 py-2 font-mono text-xs"
                            value={appleOfferId}
                            onChange={(event) => setAppleOfferId(event.target.value)}
                        />
                    </label>
                </div>
                <label className="text-sm space-y-1 block">
                    <span className="text-muted-foreground">메모</span>
                    <textarea
                        className="w-full rounded border px-3 py-2 min-h-[72px]"
                        value={discountNote}
                        onChange={(event) => setDiscountNote(event.target.value)}
                    />
                </label>
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
                        disabled={saving}
                        onClick={() => { void handleSaveDiscountPolicy(); }}
                    >
                        {saving ? '저장 중...' : '할인 정책 저장'}
                    </button>
                    {message ? <span className="text-sm text-green-700">{message}</span> : null}
                    {error ? <span className="text-sm text-destructive">{error}</span> : null}
                </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">총 추천 가입</p>
                    <p className="text-2xl font-bold">{payload?.total_signups ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">활성 추천인</p>
                    <p className="text-2xl font-bold">{payload?.referrer_count ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">할인 대기</p>
                    <p className="text-2xl font-bold">{payload?.discount_stats?.eligible_pending ?? 0}</p>
                </div>
                <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">할인 적용 완료</p>
                    <p className="text-2xl font-bold">{payload?.discount_stats?.discount_applied_count ?? 0}</p>
                </div>
            </div>

            <div>
                <h3 className="mb-2 text-sm font-semibold">추천인 순위</h3>
                {leaders.length === 0 ? (
                    <p className="text-sm text-muted-foreground">아직 추천 가입 기록이 없습니다.</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">추천인</th>
                                    <th className="px-3 py-2 text-left">코드</th>
                                    <th className="px-3 py-2 text-right">가입 수</th>
                                </tr>
                            </thead>
                            <tbody>
                                {leaders.map((leader) => (
                                    <tr key={leader.referrer_user_id} className="border-t">
                                        <td className="px-3 py-2">{leader.referrer_username || `#${leader.referrer_user_id}`}</td>
                                        <td className="px-3 py-2 font-mono text-xs">{leader.referrer_code}</td>
                                        <td className="px-3 py-2 text-right font-semibold">{leader.signup_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div>
                <h3 className="mb-2 text-sm font-semibold">최근 추천 가입 (50건)</h3>
                {recent.length === 0 ? (
                    <p className="text-sm text-muted-foreground">기록 없음</p>
                ) : (
                    <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm">
                            <thead className="bg-muted/40">
                                <tr>
                                    <th className="px-3 py-2 text-left">시각</th>
                                    <th className="px-3 py-2 text-left">추천인</th>
                                    <th className="px-3 py-2 text-left">신규 가입자</th>
                                    <th className="px-3 py-2 text-left">첫 결제 할인</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recent.map((row) => (
                                    <tr key={row.id || `${row.referrer_user_id}-${row.referred_user_id}`} className="border-t">
                                        <td className="px-3 py-2 whitespace-nowrap">{row.created_at || '—'}</td>
                                        <td className="px-3 py-2">{row.referrer_username} ({row.referrer_code})</td>
                                        <td className="px-3 py-2">{row.referred_username} · {row.referred_email}</td>
                                        <td className="px-3 py-2">{row.first_payment_discount_applied_at ? '적용됨' : '대기'}</td>
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
