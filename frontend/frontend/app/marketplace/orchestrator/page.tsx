import MarketplaceOrchestratorClient from './marketplace-orchestrator-client';

export const dynamic = 'force-dynamic';

const generatorMarketplaceProducts = [
    {
        id: 'project-scanner-starter',
        title: '프로젝트 스캐너 스타터 팩',
        category: '구조 진단형',
        price: '189,000원',
        summary: '프로젝트 구조 검색, 문제 포인트, 상품화 가능한 엔진을 복구합니다.',
        highlights: ['구조화하여', '엔진 추출', '해적점 지도'],
    },
    {
        id: 'security-guard-bundle',
        title: '보안 강화 패키지',
        category: '보안 강화형',
        price: '249,000원',
        summary: '인증·권한·민감정보 바깥쪽을 상품으로 독점 보안 가드를 구성합니다.',
        highlights: ['인증', '권한 부여', '보안 가드'],
    },
    {
        id: 'self-healing-ops-suite',
        title: '자가 치유 운영 제품군',
        category: '운영 복구형',
        price: '279,000원',
        summary: '실패 루프 복구, 자체 실행 자동 구성, 운영 상황 흐름을 한 번에 제공합니다.',
        highlights: ['자동 복구', '자체 실행 묶음', '운영 메모장'],
    },
    {
        id: 'code-generator-deployment-kit',
        title: '코드 생성기 배포 키트',
        category: '실배포 구현형',
        price: '329,000원',
        summary: '실배포를 포함하는 코드 생성, 런타임 정책, 패키징과 배포 스모크 컨텍스트까지 함께 구성합니다.',
        highlights: ['완성형 코드 생성', '런타임 정책', '배포 패키징'],
    },
    {
        id: 'powerpoint-deck-builder',
        title: 'AI 파워포인트 엔진',
        category: '발표자료 자동화형',
        price: '219,000원',
        summary: '발표 목적에 맞는 슬라이드 구성 preview와 최종 pptx 패키지까지 자동 생성합니다.',
        highlights: ['슬라이드 개요', '핵심 메시지', 'pptx 산출물'],
    },
];

const getGeneratorMarketplaceProduct = (productId?: string | null) => (
    generatorMarketplaceProducts.find((product) => product.id === productId) || null
);

export default async function MarketplaceOrchestratorPage({
    searchParams,
}: {
    searchParams?:
        | Promise<Record<string, string | string[] | undefined>>
        | Record<string, string | string[] | undefined>;
}) {
    const resolvedSearchParams = await Promise.resolve(searchParams || {});
    const productParam = resolvedSearchParams.product;
    const projectTitleParam = resolvedSearchParams.projectTitle;
    const projectIdParam = resolvedSearchParams.projectId;
    const projectSummaryParam = resolvedSearchParams.projectSummary;
    const selectedProductId = Array.isArray(productParam) ? productParam[0] : productParam;
    const selectedProjectTitle = Array.isArray(projectTitleParam) ? projectTitleParam[0] : projectTitleParam;
    const selectedProjectId = Array.isArray(projectIdParam) ? projectIdParam[0] : projectIdParam;
    const selectedProjectSummary = Array.isArray(projectSummaryParam) ? projectSummaryParam[0] : projectSummaryParam;
    const selectedProduct = getGeneratorMarketplaceProduct(selectedProductId) || generatorMarketplaceProducts[0];
    const initialProjectName = (selectedProjectTitle || selectedProjectId || selectedProduct.id || '').trim() || selectedProduct.id;
    const initialTaskDraft = selectedProjectTitle
        ? [
            `${selectedProduct.title} 기준으로 ${selectedProjectTitle} 프로젝트 주문을 시작합니다.`,
            selectedProjectSummary ? `프로젝트 요약: ${selectedProjectSummary}` : null,
            '필수 기능, 운영 조건, 수정 우선순위, 납품 기준을 바로 이어서 구체적으로 입력하세요.',
        ].filter(Boolean).join('\n')
        : `${selectedProduct.title} 상품으로 만들고 싶은 프로젝트 목표, 사용자, 필수 기능, 제약을 입력하세요.`;

    return (
        <MarketplaceOrchestratorClient
            selectedProduct={selectedProduct}
            initialProjectName={initialProjectName}
            initialTaskDraft={initialTaskDraft}
            sourceProjectTitle={selectedProjectTitle || null}
        />
    );
}
