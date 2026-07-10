'use client';

import * as React from 'react';
import { getAdminToken } from '@/lib/admin-session';

type LanguageBreakdown = {
    language: string;
    language_label: string;
    count: number;
    sample_body: string;
    countries: string[];
};

type BulkChatPreview = {
    preview_id: string;
    source_text: string;
    source_lang: string;
    recipient_count: number;
    language_breakdown: LanguageBreakdown[];
};

type BulkChatCampaign = {
    campaign_id: string;
    created_at: string;
    initiated_by: string;
    dry_run: boolean;
    recipient_count: number;
    sent_count: number;
    failed_count: number;
    push_sent_count?: number;
    language_breakdown: LanguageBreakdown[];
};

type AdminWorldlincoBulkChatPanelProps = {
    apiBaseUrl: string;
};

const COMMON_COUNTRY_OPTIONS = [
    'KR', 'US', 'JP', 'CN', 'TW', 'HK', 'VN', 'TH', 'ID', 'PH', 'SG', 'MY',
    'GB', 'DE', 'FR', 'ES', 'IT', 'RU', 'SA', 'AE', 'IN', 'BR', 'MX', 'AU',
];

export default function AdminWorldlincoBulkChatPanel({ apiBaseUrl }: AdminWorldlincoBulkChatPanelProps) {
    const [sourceText, setSourceText] = React.useState(
        'WorldLinco 베타 안내: 로그인 후 친구와 통역통화·채팅을 바로 이용하실 수 있습니다. 문의는 앱 설정을 확인해 주세요.',
    );
    const [sourceLang, setSourceLang] = React.useState('ko');
    const [activeOnly, setActiveOnly] = React.useState(true);
    const [selectedCountries, setSelectedCountries] = React.useState<string[]>([]);
    const [preview, setPreview] = React.useState<BulkChatPreview | null>(null);
    const [history, setHistory] = React.useState<BulkChatCampaign[]>([]);
    const [loading, setLoading] = React.useState(false);
    const [sending, setSending] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');

    const baseUrl = apiBaseUrl.replace(/\/$/, '');

    const buildPayload = React.useCallback(() => ({
        source_text: sourceText.trim(),
        source_lang: sourceLang,
        active_only: activeOnly,
        country_codes: selectedCountries.length > 0 ? selectedCountries : null,
    }), [activeOnly, selectedCountries, sourceLang, sourceText]);

    const loadHistory = React.useCallback(async () => {
        const token = getAdminToken();
        const response = await fetch(`${baseUrl}/api/admin/worldlinco/bulk-chat/history?limit=10`, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            cache: 'no-store',
        });
        if (!response.ok) {
            return;
        }
        const payload = await response.json() as { items?: BulkChatCampaign[] };
        setHistory(Array.isArray(payload.items) ? payload.items : []);
    }, [baseUrl]);

    React.useEffect(() => {
        void loadHistory();
    }, [loadHistory]);

    const runPreview = React.useCallback(async () => {
        setLoading(true);
        setError('');
        setMessage('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${baseUrl}/api/admin/worldlinco/bulk-chat/preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(buildPayload()),
            });
            if (!response.ok) {
                throw new Error(await response.text() || `미리보기 실패 (${response.status})`);
            }
            const payload = await response.json() as BulkChatPreview;
            setPreview(payload);
            setMessage(`미리보기 완료 — 발송 대상 ${payload.recipient_count}명`);
        } catch (previewError) {
            setError(previewError instanceof Error ? previewError.message : '미리보기에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    }, [baseUrl, buildPayload]);

    const runSend = React.useCallback(async (dryRun: boolean) => {
        if (!dryRun && !window.confirm('앱 채팅(번역 보관함)으로 안내를 발송합니다. 계속할까요?')) {
            return;
        }
        setSending(true);
        setError('');
        setMessage('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${baseUrl}/api/admin/worldlinco/bulk-chat/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    ...buildPayload(),
                    dry_run: dryRun,
                    confirm_send: !dryRun,
                }),
            });
            if (!response.ok) {
                throw new Error(await response.text() || `발송 실패 (${response.status})`);
            }
            const payload = await response.json() as BulkChatCampaign;
            setMessage(
                dryRun
                    ? `드라이런 완료 — 대상 ${payload.recipient_count}명 (실발송 없음)`
                    : `채팅 발송 완료 — 메시지 ${payload.sent_count} / 푸시 ${payload.push_sent_count ?? 0} / 실패 ${payload.failed_count}`,
            );
            await loadHistory();
        } catch (sendError) {
            setError(sendError instanceof Error ? sendError.message : '발송에 실패했습니다.');
        } finally {
            setSending(false);
        }
    }, [baseUrl, buildPayload, loadHistory]);

    const toggleCountry = React.useCallback((code: string) => {
        setSelectedCountries((prev) => (
            prev.includes(code) ? prev.filter((item) => item !== code) : [...prev, code]
        ));
    }, []);

    return (
        <div className="space-y-4" data-testid="admin-worldlinco-bulk-chat-panel">
            <p className="text-sm text-slate-600">
                가입 사용자에게 국가·프로필 언어 기준으로 번역된 안내를 앱 채팅(번역 보관함)과 푸시로 보냅니다.
                전화번호는 필요 없습니다. 미가입자 초대는 앱 내 SNS 공유(카카오·라인)를 사용하세요.
            </p>

            <label className="flex flex-col gap-1 text-sm">
                <span className="font-semibold">안내 문구 (원문)</span>
                <textarea
                    className="min-h-[120px] rounded border border-slate-300 px-3 py-2"
                    value={sourceText}
                    onChange={(event) => setSourceText(event.target.value)}
                    maxLength={500}
                />
                <span className="text-xs text-slate-500">{sourceText.length}/500 · 언어별 자동 번역 후 발송</span>
            </label>

            <div className="grid gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                    <span className="font-semibold">원문 언어</span>
                    <select
                        className="rounded border border-slate-300 px-3 py-2"
                        value={sourceLang}
                        onChange={(event) => setSourceLang(event.target.value)}
                    >
                        <option value="ko">한국어 (ko)</option>
                        <option value="en">English (en)</option>
                        <option value="ja">日本語 (ja)</option>
                        <option value="zh">中文简体 (zh)</option>
                    </select>
                </label>
                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={activeOnly}
                        onChange={(event) => setActiveOnly(event.target.checked)}
                    />
                    <span>활성 사용자만</span>
                </label>
            </div>

            <div>
                <p className="mb-2 text-sm font-semibold">국가 필터 (선택 — 미선택 시 전체)</p>
                <div className="flex flex-wrap gap-2">
                    {COMMON_COUNTRY_OPTIONS.map((code) => (
                        <button
                            key={`bulk-chat-country-${code}`}
                            type="button"
                            className={selectedCountries.includes(code) ? 'workspace-primary-button !py-1 !px-3 !text-xs' : 'workspace-ghost-button !py-1 !px-3 !text-xs'}
                            onClick={() => toggleCountry(code)}
                        >
                            {code}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                <button type="button" className="workspace-secondary-button" disabled={loading || sending} onClick={() => { void runPreview(); }}>
                    {loading ? '미리보기 중...' : '번역·대상 미리보기'}
                </button>
                <button type="button" className="workspace-ghost-button" disabled={sending} onClick={() => { void runSend(true); }}>
                    {sending ? '처리 중...' : '드라이런 (발송 없음)'}
                </button>
                <button type="button" className="workspace-primary-button" disabled={sending} onClick={() => { void runSend(false); }}>
                    {sending ? '발송 중...' : '채팅 일괄 발송'}
                </button>
            </div>

            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

            {preview ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="mb-2 text-sm font-semibold">언어별 번역 미리보기</p>
                    <div className="space-y-3">
                        {preview.language_breakdown.map((row) => (
                            <div key={`bulk-chat-lang-${row.language}`} className="rounded border border-slate-200 bg-white p-3 text-sm">
                                <p className="font-semibold">{row.language_label} ({row.language}) · {row.count}명</p>
                                <p className="text-xs text-slate-500">국가: {row.countries.length ? row.countries.join(', ') : '—'}</p>
                                <p className="mt-1 whitespace-pre-wrap">{row.sample_body}</p>
                            </div>
                        ))}
                    </div>
                </div>
            ) : null}

            {history.length > 0 ? (
                <div className="rounded-lg border border-slate-200 p-3">
                    <p className="mb-2 text-sm font-semibold">최근 발송 이력</p>
                    <div className="space-y-2 text-sm">
                        {history.map((item) => (
                            <div key={item.campaign_id} className="rounded border border-slate-100 bg-white p-2">
                                <p>{item.created_at} · {item.initiated_by} · {item.dry_run ? '드라이런' : '실발송'}</p>
                                <p>대상 {item.recipient_count} · 메시지 {item.sent_count} · 실패 {item.failed_count} · 푸시 {item.push_sent_count ?? 0}</p>
                            </div>
                        ))}
                    </div>
                </div>
            ) : null}
        </div>
    );
}
