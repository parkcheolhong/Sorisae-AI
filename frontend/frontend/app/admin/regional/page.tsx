'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import AdminWorldlincoRegionalPanel from '@/components/admin/admin-worldlinco-regional-panel';
import {
    clearAdminToken,
    getAdminToken,
} from '@/lib/admin-session';
import { redirectToAdminLogin } from '@/lib/admin-navigation';
import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';

export default function AdminRegionalPage() {
    const router = useRouter();
    const [ready, setReady] = React.useState(false);
    const [denied, setDenied] = React.useState(false);
    const apiBaseUrl = typeof window !== 'undefined' ? window.location.origin : '';

    React.useEffect(() => {
        const token = getAdminToken();
        if (!token) {
            redirectToAdminLogin(router);
            return;
        }

        void fetchWithAdminBootstrapRetry('/api/admin/worldlinco/regional/me', {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(async (response) => {
                if (!response.ok) {
                    setDenied(true);
                    return;
                }
                const me = await response.json() as { is_admin?: boolean; is_regional_manager?: boolean };
                if (!me.is_admin && !me.is_regional_manager) {
                    setDenied(true);
                    return;
                }
                setReady(true);
            })
            .catch(() => setDenied(true));
    }, [router]);

    if (denied) {
        return (
            <div className="mx-auto max-w-lg px-4 py-16 text-center space-y-4">
                <h1 className="text-xl font-semibold">접근 권한 없음</h1>
                <p className="text-sm text-muted-foreground">지역 관리자로 등록된 계정만 이 페이지에 접근할 수 있습니다.</p>
                <button
                    type="button"
                    className="text-sm underline"
                    onClick={() => {
                        clearAdminToken();
                        redirectToAdminLogin(router);
                    }}
                >
                    다시 로그인
                </button>
            </div>
        );
    }

    if (!ready) {
        return <p className="p-8 text-sm text-muted-foreground">지역 관리자 세션 확인 중...</p>;
    }

    return (
        <div className="min-h-screen bg-background">
            <header className="border-b px-4 py-3 flex items-center justify-between gap-3">
                <div>
                    <h1 className="text-lg font-semibold">WorldLinco 지역 관리자</h1>
                    <p className="text-xs text-muted-foreground">담당 국가·지역 귀속 유저 관리 · 지문 로그인은 <Link href="/admin/login" className="underline">로그인 화면</Link>에서 등록</p>
                </div>
                <Link href="/admin/login" className="text-xs underline text-muted-foreground">로그아웃</Link>
            </header>
            <main className="mx-auto max-w-6xl px-4 py-6">
                <AdminWorldlincoRegionalPanel apiBaseUrl={apiBaseUrl} mode="regional" />
            </main>
        </div>
    );
}
