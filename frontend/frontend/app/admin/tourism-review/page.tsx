'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { resolveApiBaseUrl } from '@/lib/api';
import { getAdminToken } from '@/lib/admin-session';
import { redirectToAdminLogin } from '@/lib/admin-navigation';

type ReviewMode = 'poi' | 'retrieval';

type ReviewRow = {
    item_type: ReviewMode;
    query?: string | null;
    place_source?: string | null;
    place_source_id?: string | null;
    place_name?: string | null;
    category?: string | null;
    address?: string | null;
    country?: string | null;
    score?: number | null;
    groupQuery?: string | null;
    verdict: string | null;
    note: string;
};

type ReviewStats = {
    available: boolean;
    total_labels?: number;
    reviewers?: number;
    by_verdict?: Record<string, number>;
    human_precision_retrieval?: number | null;
    poi_accuracy?: number | null;
    error?: string;
};

type FeedbackBlock = {
    total: number;
    thumbs_up: number;
    thumbs_down: number;
    thumbs_up_rate?: number | null;
    nps?: number | null;
    nps_responses: number;
    promoters: number;
    passives: number;
    detractors: number;
    avg_nps?: number | null;
    avg_total_ms?: number | null;
};

type FeedbackStats = {
    available: boolean;
    overall?: FeedbackBlock;
    by_variant?: Record<string, FeedbackBlock>;
    error?: string;
};

const pct = (v?: number | null): string => (v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`);

const POI_VERDICTS: Array<[string, string]> = [
    ['correct', '정확'],
    ['incorrect', '부정확'],
    ['unsure', '모름'],
];
const RETRIEVAL_VERDICTS: Array<[string, string]> = [
    ['relevant', '관련'],
    ['irrelevant', '무관'],
    ['unsure', '모름'],
];

export default function AdminTourismReviewPage() {
    const router = useRouter();
    const apiBaseUrl = resolveApiBaseUrl();

    const [mode, setMode] = useState<ReviewMode>('poi');
    const [reviewer, setReviewer] = useState('');
    const [n, setN] = useState(20);
    const [k, setK] = useState(5);
    const [rows, setRows] = useState<ReviewRow[]>([]);
    const [stats, setStats] = useState<ReviewStats | null>(null);
    const [feedback, setFeedback] = useState<FeedbackStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    const authHeaders = useCallback((): Record<string, string> => {
        const token = getAdminToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
    }, []);

    const loadStats = useCallback(async () => {
        try {
            const res = await fetch(`${apiBaseUrl}/api/tourism-review/stats`, { headers: authHeaders() });
            const data = (await res.json().catch(() => null)) as ReviewStats | null;
            if (data) setStats(data);
        } catch {
            /* stats 는 보조 정보이므로 실패 무시 */
        }
        try {
            const res = await fetch(`${apiBaseUrl}/api/tourism-feedback/stats`, { headers: authHeaders() });
            const data = (await res.json().catch(() => null)) as FeedbackStats | null;
            if (data) setFeedback(data);
        } catch {
            /* 베타 피드백 stats 도 보조 정보 */
        }
    }, [apiBaseUrl, authHeaders]);

    useEffect(() => {
        if (!getAdminToken()) {
            redirectToAdminLogin(router);
            return;
        }
        void loadStats();
    }, [router, loadStats]);

    const loadSample = useCallback(async () => {
        setLoading(true);
        setError('');
        setMessage('');
        try {
            const url = new URL(`${apiBaseUrl}/api/tourism-review/sample`);
            url.searchParams.set('mode', mode);
            url.searchParams.set('n', String(n));
            url.searchParams.set('k', String(k));
            const res = await fetch(url.toString(), { headers: authHeaders() });
            if (res.status === 401 || res.status === 403) {
                redirectToAdminLogin(router);
                return;
            }
            const data = await res.json().catch(() => null);
            if (!res.ok || !data) throw new Error((data as any)?.detail || `표본 조회 실패(${res.status})`);

            const next: ReviewRow[] = [];
            if (mode === 'poi') {
                for (const it of (data.items || []) as any[]) {
                    next.push({
                        item_type: 'poi',
                        place_source: it.place_source,
                        place_source_id: it.place_source_id,
                        place_name: it.place_name,
                        category: it.category,
                        address: it.address,
                        country: it.country,
                        verdict: null,
                        note: '',
                    });
                }
            } else {
                for (const b of (data.batches || []) as any[]) {
                    for (const r of (b.results || []) as any[]) {
                        next.push({
                            item_type: 'retrieval',
                            query: b.query,
                            groupQuery: b.query,
                            place_source: r.place_source,
                            place_source_id: r.place_source_id,
                            place_name: r.place_name,
                            category: r.category,
                            address: r.address,
                            score: r.score,
                            verdict: null,
                            note: '',
                        });
                    }
                }
            }
            setRows(next);
            setMessage(`표본 ${next.length}건 로드`);
            void loadStats();
        } catch (e: any) {
            setError(e.message || '표본을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, authHeaders, mode, n, k, router, loadStats]);

    const setVerdict = (idx: number, verdict: string) => {
        setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, verdict } : r)));
    };
    const setNote = (idx: number, note: string) => {
        setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, note } : r)));
    };

    const submitLabels = useCallback(async () => {
        const labels = rows
            .filter((r) => r.verdict)
            .map((r) => ({
                item_type: r.item_type,
                query: r.query ?? null,
                place_source: r.place_source ?? null,
                place_source_id: r.place_source_id ?? null,
                place_name: r.place_name ?? null,
                category: r.category ?? null,
                verdict: r.verdict,
                note: r.note || null,
            }));
        if (!labels.length) {
            setMessage('선택된 라벨이 없습니다.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${apiBaseUrl}/api/tourism-review/labels`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({ reviewer: reviewer || null, labels }),
            });
            const data = await res.json().catch(() => null);
            if (!res.ok || !data) throw new Error((data as any)?.detail || `저장 실패(${res.status})`);
            setMessage(`저장 ${data.saved || 0}건`);
            void loadStats();
        } catch (e: any) {
            setError(e.message || '라벨 저장에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, authHeaders, rows, reviewer, loadStats]);

    const verdictOptions = mode === 'poi' ? POI_VERDICTS : RETRIEVAL_VERDICTS;
    let lastGroup: string | null = null;

    return (
        <div className="min-h-screen bg-[#0d1117] px-4 py-8 text-[#e6edf3]">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold text-[#79c0ff]">🧭 관광 데이터 사람검수</h1>
                        <p className="mt-1 text-sm text-[#8b949e]">
                            전문가 검수(휴먼 인더루프). POI 분류·실재성 또는 검색 결과 관련성을 라벨링하면 자동 메트릭과 상호보완됩니다.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/admin" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]">
                            관리자 대시보드
                        </Link>
                        <Link href="/admin/llm" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]">
                            LLM 제어 패널
                        </Link>
                    </div>
                </div>

                <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                    <label className="flex flex-col text-xs text-[#8b949e]">
                        검수자
                        <input
                            value={reviewer}
                            onChange={(e) => setReviewer(e.target.value)}
                            placeholder="이름/ID"
                            className="mt-1 w-40 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                        />
                    </label>
                    <label className="flex flex-col text-xs text-[#8b949e]">
                        모드
                        <select
                            value={mode}
                            onChange={(e) => setMode(e.target.value as ReviewMode)}
                            className="mt-1 w-36 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                        >
                            <option value="poi">POI 검수</option>
                            <option value="retrieval">검색 관련성</option>
                        </select>
                    </label>
                    {mode === 'poi' ? (
                        <label className="flex flex-col text-xs text-[#8b949e]">
                            표본 수(n)
                            <input
                                type="number"
                                min={1}
                                max={200}
                                value={n}
                                onChange={(e) => setN(Number(e.target.value) || 1)}
                                className="mt-1 w-24 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                            />
                        </label>
                    ) : (
                        <label className="flex flex-col text-xs text-[#8b949e]">
                            top-k
                            <input
                                type="number"
                                min={1}
                                max={20}
                                value={k}
                                onChange={(e) => setK(Number(e.target.value) || 1)}
                                className="mt-1 w-24 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                            />
                        </label>
                    )}
                    <button
                        onClick={() => void loadSample()}
                        disabled={loading}
                        className="rounded-lg bg-[#1f6feb] px-4 py-2 text-sm font-semibold text-white hover:bg-[#388bfd] disabled:opacity-50"
                    >
                        표본 불러오기
                    </button>
                    <button
                        onClick={() => void submitLabels()}
                        disabled={loading || rows.length === 0}
                        className="rounded-lg border border-[#30363d] bg-[#0d1117] px-4 py-2 text-sm font-semibold text-[#e6edf3] hover:bg-[#21262d] disabled:opacity-50"
                    >
                        라벨 제출
                    </button>
                </div>

                {stats && (
                    <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4 text-sm">
                        {stats.available ? (
                            <div className="flex flex-wrap gap-x-6 gap-y-1 text-[#9be8b3]">
                                <span>총 라벨 {stats.total_labels ?? 0}</span>
                                <span>검수자 {stats.reviewers ?? 0}</span>
                                <span>사람 정밀도(검색) {stats.human_precision_retrieval ?? '—'}</span>
                                <span>POI 정확도 {stats.poi_accuracy ?? '—'}</span>
                            </div>
                        ) : (
                            <span className="text-[#8b949e]">검수 DB 비활성</span>
                        )}
                    </div>
                )}

                {feedback && (
                    <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4 text-sm">
                        <div className="mb-2 font-bold text-[#79c0ff]">📊 파일럿 베타 피드백 (NPS · A/B)</div>
                        {feedback.available && feedback.overall ? (
                            <>
                                <div className="flex flex-wrap gap-x-6 gap-y-1 text-[#9be8b3]">
                                    <span>응답 {feedback.overall.total}</span>
                                    <span>NPS {feedback.overall.nps ?? '—'} (n={feedback.overall.nps_responses})</span>
                                    <span>👍 비율 {pct(feedback.overall.thumbs_up_rate)} ({feedback.overall.thumbs_up}/{feedback.overall.thumbs_up + feedback.overall.thumbs_down})</span>
                                    <span>추천{feedback.overall.promoters} · 중립{feedback.overall.passives} · 비추{feedback.overall.detractors}</span>
                                </div>
                                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                    {feedback.by_variant &&
                                        Object.entries(feedback.by_variant).map(([variant, b]) => (
                                            <div key={variant} className="rounded-lg border border-[#21262d] bg-[#0d1117] p-2 text-xs text-[#8b949e]">
                                                <span className="font-bold text-[#e6edf3]">변형 {variant}</span> · 응답 {b.total} · NPS {b.nps ?? '—'} (n={b.nps_responses}) · 👍 {pct(b.thumbs_up_rate)}
                                            </div>
                                        ))}
                                </div>
                            </>
                        ) : (
                            <span className="text-[#8b949e]">피드백 DB 비활성</span>
                        )}
                    </div>
                )}

                {message && <div className="mb-3 text-sm text-[#9be8b3]">{message}</div>}
                {error && (
                    <div className="mb-3 rounded-lg border border-[#f78166] bg-[rgba(247,129,102,0.12)] p-3 text-sm text-[#ffb3a7]">{error}</div>
                )}

                <div className="space-y-2">
                    {rows.map((row, idx) => {
                        const showGroup = mode === 'retrieval' && row.groupQuery && row.groupQuery !== lastGroup;
                        if (showGroup) lastGroup = row.groupQuery ?? null;
                        return (
                            <div key={`${row.place_source}-${row.place_source_id}-${idx}`}>
                                {showGroup && (
                                    <div className="mb-1 mt-4 text-sm font-bold text-[#79c0ff]">질의: {row.groupQuery}</div>
                                )}
                                <div className="rounded-xl border border-[#21262d] bg-[#151b23] p-3">
                                    <div className="text-sm font-semibold text-[#e6edf3]">
                                        {row.place_name || '(이름없음)'} <span className="text-[#8b949e]">· {row.category || '(미지정)'}</span>
                                    </div>
                                    <div className="mt-1 text-xs text-[#8b949e]">
                                        {[row.address, row.country, mode === 'retrieval' ? `score ${row.score}` : null, `${row.place_source}/${row.place_source_id}`]
                                            .filter(Boolean)
                                            .join(' · ')}
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {verdictOptions.map(([v, label]) => (
                                            <button
                                                key={v}
                                                onClick={() => setVerdict(idx, v)}
                                                className={`rounded-full border px-3 py-1 text-xs ${
                                                    row.verdict === v
                                                        ? 'border-[#1f6feb] bg-[#1f6feb] text-white'
                                                        : 'border-[#30363d] bg-[#0d1117] text-[#e6edf3] hover:bg-[#21262d]'
                                                }`}
                                            >
                                                {label}
                                            </button>
                                        ))}
                                        <input
                                            value={row.note}
                                            onChange={(e) => setNote(idx, e.target.value)}
                                            placeholder="메모(선택)"
                                            className="ml-1 flex-1 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-1 text-xs text-[#e6edf3]"
                                        />
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                    {rows.length === 0 && !loading && (
                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-6 text-sm text-[#8b949e]">
                            모드를 선택하고 “표본 불러오기”를 누르세요.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
