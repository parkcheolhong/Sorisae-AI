import Link from 'next/link';

export default function SorisaeDashboardSeparatedPage() {
    return (
        <main className="min-h-screen bg-[#080b12] px-6 py-16 text-[#e5edf8]">
            <div className="mx-auto max-w-3xl rounded-2xl border border-[#2a3346] bg-[#111827] p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#7fb2ff]">Separated Route</p>
                <h1 className="mt-3 text-3xl font-semibold">소리새 대시보드는 분리되어 비활성화되었습니다.</h1>
                <p className="mt-4 text-sm text-[#c6d5ee]">
                    CODE AI 중앙 관제는 관리자 대시보드 경로에서만 운영합니다. 소리새 서비스 점검은 마켓플레이스 전용 경로에서 수행하세요.
                </p>
                <div className="mt-8 flex flex-wrap gap-3">
                    <Link
                        href="/admin"
                        className="rounded-lg border border-[#3b4b6d] bg-[#1a2540] px-4 py-2 text-sm font-semibold text-[#dbe8ff] hover:bg-[#243154]"
                    >
                        CODE AI 관리자 대시보드
                    </Link>
                    <Link
                        href="/marketplace/worldlinco"
                        className="rounded-lg border border-[#33553f] bg-[#152b1f] px-4 py-2 text-sm font-semibold text-[#c9f1d5] hover:bg-[#1a3527]"
                    >
                        WorldLinco 서비스 점검 화면
                    </Link>
                </div>
            </div>
        </main>
    );
}
