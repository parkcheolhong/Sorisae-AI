import Link from 'next/link';

const TERMS_SECTIONS = [
    {
        title: '제1조 목적',
        body: '본 약관은 메타노바 서비스와 관리자 계정 보호, 본인확인 기반 계정 복구 및 비밀번호 재설정 절차의 이용 조건을 정합니다.',
    },
    {
        title: '제2조 본인확인 고지',
        body: '계정 보호와 고위험 작업 검증을 위해 PASS, KMC, KCB 등 외부 본인확인 기관을 사용할 수 있으며, 인증 실패 또는 정보 불일치 시 일부 기능 이용이 제한될 수 있습니다.',
    },
    {
        title: '제3조 계정 복구 및 비밀번호 재설정',
        body: '관리자 또는 사용자 계정의 비밀번호 재설정, 민감 정보 변경, 고위험 작업 수행 시 추가 본인확인을 요구할 수 있습니다.',
    },
    {
        title: '제4조 금지행위',
        body: '타인 명의 도용, 허위 정보 입력, 인증 우회 시도, 서비스 운영을 방해하는 행위를 금지합니다.',
    },
    {
        title: '제5조 서비스 제한',
        body: '본인확인 실패, 운영 점검, 장애, 보안상 필요 시 서비스 전부 또는 일부를 제한할 수 있으며, 필요한 경우 공지합니다.',
    },
];

export default function TermsPage() {
    return (
        <main className="min-h-screen bg-[#0d1117] px-4 py-10 text-[#e6edf3]">
            <div className="mx-auto max-w-4xl">
                <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-[#8b949e]">Metanova Commercial Policy</p>
                        <h1 className="mt-2 text-3xl font-bold text-white">이용약관</h1>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/privacy" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm hover:bg-[#21262d]">
                            개인정보처리방침
                        </Link>
                        <Link href="/admin" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm hover:bg-[#21262d]">
                            관리자 대시보드
                        </Link>
                    </div>
                </div>
                <div className="rounded-2xl border border-[#30363d] bg-[#161b22] p-6 shadow-[0_0_0_1px_rgba(148,163,184,0.06)]">
                    <p className="text-sm leading-7 text-[#c9d1d9]">
                        본 약관은 상용 운영 전환 및 본인확인 공급사 심사 제출 기준을 충족하기 위한 공개 약관 페이지입니다.
                    </p>
                    <div className="mt-6 space-y-5">
                        {TERMS_SECTIONS.map((section) => (
                            <section key={section.title} className="rounded-xl border border-[#30363d] bg-[#0d1117] p-5">
                                <h2 className="text-lg font-semibold text-[#79c0ff]">{section.title}</h2>
                                <p className="mt-2 text-sm leading-7 text-[#c9d1d9]">{section.body}</p>
                            </section>
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
