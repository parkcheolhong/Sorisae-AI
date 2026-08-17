import Link from 'next/link';

const PRIVACY_ITEMS = [
    {
        title: '수집 목적',
        body: '회원 확인, 계정 보호, 비밀번호 재설정, 고위험 작업 검증을 위해 본인확인 정보를 처리합니다.',
    },
    {
        title: '수집 항목',
        body: '이름, 생년월일, 휴대전화번호, CI/DI, 공급사 결과 코드 등 본인확인 공급사가 제공하는 인증 결과를 처리할 수 있습니다.',
    },
    {
        title: '보유 및 이용 기간',
        body: '법령 및 내부 보안 정책에 따라 필요한 기간 동안만 보관하며, 보유 목적 달성 후 지체 없이 파기합니다.',
    },
    {
        title: '제3자 제공 및 위탁',
        body: '본인확인 절차 수행을 위해 PASS, KMC, KCB 등 본인확인 기관 또는 관련 위탁사를 이용할 수 있습니다.',
    },
    {
        title: '이용자 권리',
        body: '이용자는 개인정보 열람, 정정, 삭제, 처리정지 요청을 할 수 있으며, 서비스 문의 채널을 통해 접수할 수 있습니다.',
    },
];

export default function PrivacyPage() {
    return (
        <main className="min-h-screen bg-[#0d1117] px-4 py-10 text-[#e6edf3]">
            <div className="mx-auto max-w-4xl">
                <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-[#8b949e]">Metanova Commercial Policy</p>
                        <h1 className="mt-2 text-3xl font-bold text-white">개인정보처리방침</h1>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/terms" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm hover:bg-[#21262d]">
                            이용약관
                        </Link>
                        <Link href="/admin" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm hover:bg-[#21262d]">
                            관리자 대시보드
                        </Link>
                    </div>
                </div>
                <div className="rounded-2xl border border-[#30363d] bg-[#161b22] p-6 shadow-[0_0_0_1px_rgba(148,163,184,0.06)]">
                    <p className="text-sm leading-7 text-[#c9d1d9]">
                        본 페이지는 본인확인 공급사 상용 심사와 운영 전환을 위한 공개 개인정보처리방침 페이지입니다.
                    </p>
                    <div className="mt-6 space-y-5">
                        {PRIVACY_ITEMS.map((item) => (
                            <section key={item.title} className="rounded-xl border border-[#30363d] bg-[#0d1117] p-5">
                                <h2 className="text-lg font-semibold text-[#79c0ff]">{item.title}</h2>
                                <p className="mt-2 text-sm leading-7 text-[#c9d1d9]">{item.body}</p>
                            </section>
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
