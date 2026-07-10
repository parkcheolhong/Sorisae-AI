'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

type PromoEntry = {
    enabled?: boolean;
    title?: string;
    subtitle?: string;
    body?: string;
    cta_label?: string;
    cta_action?: string;
    accent_color?: string;
    image_url?: string;
};

type TourismPromoPayload = {
    version?: number;
    updated_at?: string | null;
    updated_by?: string | null;
    note?: string;
    entries?: Record<string, PromoEntry>;
};

type AdminWorldlincoTourismPromoPanelProps = {
    apiBaseUrl: string;
};

const CTA_ACTIONS = [
    { value: 'face_interpretation', label: '대면 통역' },
    { value: 'travel_booking', label: '여행 예약/주변 검색' },
    { value: 'none', label: '버튼 없음' },
];

export default function AdminWorldlincoTourismPromoPanel({ apiBaseUrl }: AdminWorldlincoTourismPromoPanelProps) {
    const [payload, setPayload] = React.useState<TourismPromoPayload | null>(null);
    const [selectedCountry, setSelectedCountry] = React.useState('KR');
    const [draft, setDraft] = React.useState<PromoEntry>({});
    const [note, setNote] = React.useState('');
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [message, setMessage] = React.useState('');
    const [error, setError] = React.useState('');

    const load = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/tourism-promo`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!response.ok) {
                throw new Error(`불러오기 실패 (${response.status})`);
            }
            const data = (await response.json()) as TourismPromoPayload;
            setPayload(data);
            setNote(String(data.note || ''));
            const codes = Object.keys(data.entries || {});
            const initial = codes.includes('KR') ? 'KR' : codes[0] || 'DEFAULT';
            setSelectedCountry(initial);
            setDraft((data.entries || {})[initial] || {});
        } catch (err) {
            setError(err instanceof Error ? err.message : '불러오기 실패');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl]);

    React.useEffect(() => {
        void load();
    }, [load]);

    React.useEffect(() => {
        const entry = payload?.entries?.[selectedCountry];
        setDraft(entry || {});
    }, [payload, selectedCountry]);

    const countryCodes = React.useMemo(() => {
        const codes = Object.keys(payload?.entries || {});
        return codes.length ? codes.sort() : ['DEFAULT'];
    }, [payload]);

    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/tourism-promo`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    note,
                    entries: {
                        [selectedCountry]: draft,
                    },
                }),
            });
            if (!response.ok) {
                throw new Error(`저장 실패 (${response.status})`);
            }
            const data = (await response.json()) as TourismPromoPayload;
            setPayload(data);
            setMessage(`${selectedCountry} 홍보 카드가 저장되었습니다. 앱 홈 중앙에 즉시 반영됩니다.`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <p className="text-sm text-muted-foreground">관광 홍보 설정 불러오는 중...</p>;
    }

    return (
        <div className="space-y-4" data-testid="admin-worldlinco-tourism-promo-panel">
            <p className="text-sm text-muted-foreground">
                국가별 관광 홍보 카드를 편집합니다. 저장 즉시 <code>/api/marketplace/worldlinco/tourism-promo</code> 에 반영되어 앱 번역 홈 중앙에 표시됩니다.
            </p>
            {payload?.updated_at ? (
                <p className="text-xs text-muted-foreground">마지막 수정: {payload.updated_at} · {payload.updated_by || '-'}</p>
            ) : null}

            <label className="block text-sm font-medium">국가 코드</label>
            <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={selectedCountry}
                onChange={(e) => setSelectedCountry(e.target.value.toUpperCase())}
                data-testid="admin-tourism-promo-country-select"
            >
                {countryCodes.map((code) => (
                    <option key={code} value={code}>{code}</option>
                ))}
            </select>

            <label className="flex items-center gap-2 text-sm">
                <input
                    type="checkbox"
                    checked={draft.enabled !== false}
                    onChange={(e) => setDraft((prev) => ({ ...prev, enabled: e.target.checked }))}
                />
                노출 활성화
            </label>

            <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="제목"
                value={draft.title || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, title: e.target.value }))}
            />
            <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="부제"
                value={draft.subtitle || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, subtitle: e.target.value }))}
            />
            <textarea
                className="min-h-[96px] w-full rounded-md border px-3 py-2 text-sm"
                placeholder="본문"
                value={draft.body || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, body: e.target.value }))}
            />
            <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="버튼 문구"
                value={draft.cta_label || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, cta_label: e.target.value }))}
            />
            <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={draft.cta_action || 'face_interpretation'}
                onChange={(e) => setDraft((prev) => ({ ...prev, cta_action: e.target.value }))}
            >
                {CTA_ACTIONS.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                ))}
            </select>
            <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="강조 색 (#1E6FE0)"
                value={draft.accent_color || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, accent_color: e.target.value }))}
            />
            <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="이미지 URL (선택)"
                value={draft.image_url || ''}
                onChange={(e) => setDraft((prev) => ({ ...prev, image_url: e.target.value }))}
            />

            <textarea
                className="min-h-[72px] w-full rounded-md border px-3 py-2 text-sm"
                placeholder="관리자 메모"
                value={note}
                onChange={(e) => setNote(e.target.value)}
            />

            <div className="flex gap-2">
                <button
                    type="button"
                    className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                    onClick={() => { void handleSave(); }}
                    disabled={saving}
                    data-testid="admin-tourism-promo-save"
                >
                    {saving ? '저장 중...' : '저장'}
                </button>
                <button type="button" className="rounded-md border px-4 py-2 text-sm" onClick={() => { void load(); }}>
                    새로고침
                </button>
            </div>

            {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
    );
}
