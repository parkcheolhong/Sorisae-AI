'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { resolveApiBaseUrl } from '@/lib/api';
import { getAdminToken } from '@/lib/admin-session';
import { redirectToAdminLogin } from '@/lib/admin-navigation';

type CarbonStats = {
    gpu_available: boolean;
    grid_intensity_g_per_kwh: number;
    fallback_power_w: number;
    last_power_w: number | null;
    totals: {
        calls: number;
        duration_s: number;
        energy_wh: number;
        carbon_g: number;
        avg_carbon_g_per_call: number;
        avg_energy_wh_per_call: number;
    };
    by_label: Record<string, { calls: number; duration_s: number; energy_wh: number; carbon_g: number; power_source?: string }>;
};

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
    return (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
            <div className="text-xs text-[#8b949e]">{label}</div>
            <div className="mt-1 text-2xl font-bold text-[#79c0ff]">{value}</div>
            {sub ? <div className="mt-1 text-xs text-[#8b949e]">{sub}</div> : null}
        </div>
    );
}

export default function AdminCarbonPage() {
    const router = useRouter();
    const apiBaseUrl = resolveApiBaseUrl();
    const [stats, setStats] = useState<CarbonStats | null>(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            redirectToAdminLogin(router);
            return;
        }
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${apiBaseUrl}/api/ops/carbon/stats`, { headers: { Authorization: `Bearer ${token}` } });
            if (res.status === 401 || res.status === 403) {
                redirectToAdminLogin(router);
                return;
            }
            const data = await res.json().catch(() => null);
            if (!res.ok || !data) throw new Error((data as any)?.detail || `조회 실패(${res.status})`);
            setStats(data as CarbonStats);
        } catch (e: any) {
            setError(e.message || '탄소 통계를 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, router]);

    useEffect(() => {
        void load();
    }, [load]);

    return (
        <div className="min-h-screen bg-[#0d1117] px-4 py-8 text-[#e6edf3]">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold text-[#79c0ff]">🌱 추론 탄소·전력 측정</h1>
                        <p className="mt-1 text-sm text-[#8b949e]">
                            추천(/answer) LLM 추론의 GPU 전력·에너지·탄소 누적 집계. nvidia-smi 실측(가용 시) 기반.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button onClick={() => void load()} className="rounded-lg bg-[#1f6feb] px-4 py-2 text-sm font-semibold text-white hover:bg-[#388bfd]">
                            새로고침
                        </button>
                        <Link href="/admin" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]">
                            관리자 대시보드
                        </Link>
                    </div>
                </div>

                {error && (
                    <div className="mb-4 rounded-lg border border-[#f78166] bg-[rgba(247,129,102,0.12)] p-3 text-sm text-[#ffb3a7]">{error}</div>
                )}

                {loading && !stats ? (
                    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-6 text-sm text-[#8b949e]">불러오는 중...</div>
                ) : stats ? (
                    <>
                        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                            <Card label="누적 추론 호출" value={`${stats.totals.calls}`} />
                            <Card label="누적 탄소" value={`${stats.totals.carbon_g} gCO₂`} sub={`평균 ${stats.totals.avg_carbon_g_per_call} g/호출`} />
                            <Card label="누적 에너지" value={`${stats.totals.energy_wh} Wh`} sub={`평균 ${stats.totals.avg_energy_wh_per_call} Wh/호출`} />
                            <Card label="현재 GPU 전력" value={stats.last_power_w != null ? `${stats.last_power_w} W` : '—'} sub={stats.gpu_available ? 'nvidia-smi 실측' : '폴백/미측정'} />
                        </div>

                        <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4 text-sm text-[#8b949e]">
                            그리드 배출계수 {stats.grid_intensity_g_per_kwh} gCO₂/kWh · GPU {stats.gpu_available ? '사용 가능' : '미가용'}
                            {stats.fallback_power_w ? ` · 폴백 전력 ${stats.fallback_power_w} W` : ''}
                        </div>

                        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                            <div className="mb-2 text-sm font-bold text-[#e6edf3]">라벨별 집계</div>
                            {Object.keys(stats.by_label).length === 0 ? (
                                <div className="text-sm text-[#8b949e]">아직 측정된 추론 호출이 없습니다.</div>
                            ) : (
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="text-[#8b949e]">
                                            <th className="py-1">라벨</th>
                                            <th className="py-1">호출</th>
                                            <th className="py-1">에너지(Wh)</th>
                                            <th className="py-1">탄소(gCO₂)</th>
                                            <th className="py-1">측정원</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.entries(stats.by_label).map(([label, v]) => (
                                            <tr key={label} className="border-t border-[#21262d] text-[#e6edf3]">
                                                <td className="py-1">{label}</td>
                                                <td className="py-1">{v.calls}</td>
                                                <td className="py-1">{v.energy_wh}</td>
                                                <td className="py-1">{v.carbon_g}</td>
                                                <td className="py-1 text-[#8b949e]">{v.power_source ?? '—'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </>
                ) : null}
            </div>
        </div>
    );
}
