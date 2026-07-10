'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

export type WorldlincoBillingPolicyPayload = {
    version?: number;
    updated_at?: string | null;
    updated_by?: string | null;
    access_mode?: 'free' | 'paid';
    billing_collection_paused?: boolean;
    promo_label?: string;
    promo_starts_at?: string | null;
    promo_ends_at?: string | null;
    auto_switch_to_paid_on_promo_end?: boolean;
    show_pricing_ui?: boolean;
    note?: string;
    effective?: {
        access_mode?: 'free' | 'paid';
        configured_access_mode?: string;
        billing_collection_paused?: boolean;
        free_access_active?: boolean;
        show_pricing_ui?: boolean;
        promo_label?: string;
        promo_starts_at?: string | null;
        promo_ends_at?: string | null;
        auto_switch_to_paid_on_promo_end?: boolean;
    };
};

type AdminWorldlincoBillingPolicyPanelProps = {
    apiBaseUrl: string;
};

function formatDate(value?: string | null): string {
    if (!value) {
        return '-';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

export default function AdminWorldlincoBillingPolicyPanel({ apiBaseUrl }: AdminWorldlincoBillingPolicyPanelProps) {
    const [data, setData] = React.useState<WorldlincoBillingPolicyPayload | null>(null);
    const [loading, setLoading] = React.useState(false);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');

    const [accessMode, setAccessMode] = React.useState<'free' | 'paid'>('free');
    const [billingPaused, setBillingPaused] = React.useState(false);
    const [promoLabel, setPromoLabel] = React.useState('베타 무료 기간');
    const [promoStartsAt, setPromoStartsAt] = React.useState('');
    const [promoEndsAt, setPromoEndsAt] = React.useState('');
    const [autoSwitchPaid, setAutoSwitchPaid] = React.useState(false);
    const [showPricingUi, setShowPricingUi] = React.useState(false);
    const [note, setNote] = React.useState('');

    const applyPayloadToForm = React.useCallback((payload: WorldlincoBillingPolicyPayload) => {
        setAccessMode(payload.access_mode === 'paid' ? 'paid' : 'free');
        setBillingPaused(Boolean(payload.billing_collection_paused));
        setPromoLabel(String(payload.promo_label || '베타 무료 기간'));
        setPromoStartsAt(String(payload.promo_starts_at || '').replace('Z', '').slice(0, 16));
        setPromoEndsAt(String(payload.promo_ends_at || '').replace('Z', '').slice(0, 16));
        setAutoSwitchPaid(Boolean(payload.auto_switch_to_paid_on_promo_end));
        setShowPricingUi(Boolean(payload.show_pricing_ui));
        setNote(String(payload.note || ''));
    }, []);

    const loadPolicy = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/billing-policy`, {
                headers: token ? { Authorization: `Bearer ${token}` } : undefined,
                cache: 'no-store',
            });
            if (!response.ok) {
                throw new Error(await response.text() || `불러오기 실패 (${response.status})`);
            }
            const payload = (await response.json()) as WorldlincoBillingPolicyPayload;
            setData(payload);
            applyPayloadToForm(payload);
        } catch (fetchError) {
            setError(fetchError instanceof Error ? fetchError.message : '요금 정책을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, applyPayloadToForm]);

    React.useEffect(() => {
        void loadPolicy();
    }, [loadPolicy]);

    const savePolicy = React.useCallback(async (patch: Partial<WorldlincoBillingPolicyPayload>, successMessage: string) => {
        setSaving(true);
        setError('');
        setMessage('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/billing-policy`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(patch),
            });
            if (!response.ok) {
                throw new Error(await response.text() || `저장 실패 (${response.status})`);
            }
            const payload = (await response.json()) as WorldlincoBillingPolicyPayload;
            setData(payload);
            applyPayloadToForm(payload);
            setMessage(successMessage);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : '요금 정책 저장에 실패했습니다.');
        } finally {
            setSaving(false);
        }
    }, [apiBaseUrl, applyPayloadToForm]);

    const handleSave = React.useCallback(async () => {
        await savePolicy({
            access_mode: accessMode,
            billing_collection_paused: billingPaused,
            promo_label: promoLabel.trim() || '프로모 기간',
            promo_starts_at: promoStartsAt ? `${promoStartsAt}:00Z` : null,
            promo_ends_at: promoEndsAt ? `${promoEndsAt}:00Z` : null,
            auto_switch_to_paid_on_promo_end: autoSwitchPaid,
            show_pricing_ui: showPricingUi,
            note: note.trim(),
        }, '요금 정책이 저장되었습니다. 모바일 앱은 포그라운드 복귀 시 자동 반영됩니다.');
    }, [accessMode, autoSwitchPaid, billingPaused, note, promoEndsAt, promoLabel, promoStartsAt, savePolicy, showPricingUi]);

    const effective = data?.effective;

    return (
        <div className="space-y-4" data-testid="admin-worldlinco-billing-policy-panel">
            <p className="text-sm text-slate-600">
                WorldLinco 앱의 무료/유료 전환과 요금 징수 중지·재개를 원격 제어합니다.
                저장 즉시 <code>/api/marketplace/worldlinco/billing-policy</code> 에 반영됩니다.
            </p>

            {loading ? <p className="text-sm text-slate-500">불러오는 중...</p> : null}
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

            {effective ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                    <p><strong>현재 적용:</strong> {effective.free_access_active ? '무료 접근 ON' : '유료 게이트 ON'}</p>
                    <p>설정 모드: {effective.configured_access_mode} · 실효 모드: {effective.access_mode}</p>
                    <p>요금 중지: {effective.billing_collection_paused ? '예' : '아니오'} · 요금 UI: {effective.show_pricing_ui ? '표시' : '숨김'}</p>
                    <p>마지막 갱신: {formatDate(data?.updated_at)} ({data?.updated_by || '-'})</p>
                </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                    <span className="font-semibold">접근 모드</span>
                    <select
                        className="rounded border border-slate-300 px-3 py-2"
                        value={accessMode}
                        onChange={(event) => setAccessMode(event.target.value as 'free' | 'paid')}
                    >
                        <option value="free">무료 (베타/프로모 — 로그인 사용자 기능 개방)</option>
                        <option value="paid">유료 (구매·구독 필요)</option>
                    </select>
                </label>

                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={billingPaused}
                        onChange={(event) => setBillingPaused(event.target.checked)}
                    />
                    <span>요금 징수/결제 게이트 일시 중지 (유료 모드에서도 무료처럼 이용)</span>
                </label>

                <label className="flex flex-col gap-1 text-sm">
                    <span className="font-semibold">프로모 라벨</span>
                    <input
                        className="rounded border border-slate-300 px-3 py-2"
                        value={promoLabel}
                        onChange={(event) => setPromoLabel(event.target.value)}
                    />
                </label>

                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={showPricingUi}
                        onChange={(event) => setShowPricingUi(event.target.checked)}
                    />
                    <span>앱에 요금표 UI 표시</span>
                </label>

                <label className="flex flex-col gap-1 text-sm">
                    <span className="font-semibold">프로모 시작 (UTC, 선택)</span>
                    <input
                        type="datetime-local"
                        className="rounded border border-slate-300 px-3 py-2"
                        value={promoStartsAt}
                        onChange={(event) => setPromoStartsAt(event.target.value)}
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm">
                    <span className="font-semibold">프로모 종료 (UTC, 선택)</span>
                    <input
                        type="datetime-local"
                        className="rounded border border-slate-300 px-3 py-2"
                        value={promoEndsAt}
                        onChange={(event) => setPromoEndsAt(event.target.value)}
                    />
                </label>

                <label className="flex items-center gap-2 text-sm md:col-span-2">
                    <input
                        type="checkbox"
                        checked={autoSwitchPaid}
                        onChange={(event) => setAutoSwitchPaid(event.target.checked)}
                    />
                    <span>프로모 종료일 이후 자동으로 유료(paid) 모드로 전환</span>
                </label>

                <label className="flex flex-col gap-1 text-sm md:col-span-2">
                    <span className="font-semibold">운영 메모</span>
                    <textarea
                        className="min-h-[72px] rounded border border-slate-300 px-3 py-2"
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                    />
                </label>
            </div>

            <div className="flex flex-wrap gap-2">
                <button type="button" className="workspace-primary-button" disabled={saving} onClick={() => { void handleSave(); }}>
                    {saving ? '저장 중...' : '정책 저장'}
                </button>
                <button
                    type="button"
                    className="workspace-secondary-button"
                    disabled={saving}
                    onClick={() => {
                        void savePolicy({
                            access_mode: 'free',
                            billing_collection_paused: false,
                            show_pricing_ui: false,
                            promo_label: '베타 무료 기간',
                        }, '무료(베타) 모드로 전환했습니다.');
                    }}
                >
                    무료(베타)로 전환
                </button>
                <button
                    type="button"
                    className="workspace-secondary-button"
                    disabled={saving}
                    onClick={() => {
                        void savePolicy({
                            access_mode: 'paid',
                            billing_collection_paused: false,
                            show_pricing_ui: true,
                            promo_label: '유료 서비스',
                        }, '유료 모드로 전환했습니다.');
                    }}
                >
                    유료로 전환
                </button>
                <button
                    type="button"
                    className="workspace-ghost-button"
                    disabled={saving}
                    onClick={() => {
                        void savePolicy({ billing_collection_paused: true }, '요금 징수/게이트를 일시 중지했습니다.');
                    }}
                >
                    요금 중지
                </button>
                <button
                    type="button"
                    className="workspace-ghost-button"
                    disabled={saving}
                    onClick={() => {
                        void savePolicy({ billing_collection_paused: false }, '요금 징수/게이트를 재개했습니다.');
                    }}
                >
                    요금 재개
                </button>
                <button type="button" className="workspace-ghost-button" disabled={loading} onClick={() => { void loadPolicy(); }}>
                    새로고침
                </button>
            </div>
        </div>
    );
}
