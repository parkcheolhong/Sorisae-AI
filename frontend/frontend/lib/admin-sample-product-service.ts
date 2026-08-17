export interface SampleTemplate {
    key: string;
    title: string;
    description: string;
    price: number;
    demo_url: string;
    github_url: string;
    image_url: string;
    tags: string[];
}

export interface SampleCleanupResponse {
    ok: boolean;
    dry_run: boolean;
    pattern: string;
    matched: number;
    affected_ids: number[];
    titles: string[];
}

export const sampleTemplates: SampleTemplate[] = [
    {
        key: 'saas-admin-kit',
        title: 'AI SaaS 랜딩 + 관리자 대시보드 스타터 킷 (Next.js)',
        description: '테스트용 샘플: 랜딩/대시보드 화면과 운영형 UI 구성을 포함한 상품 템플릿.',
        price: 129000,
        demo_url: 'https://demo.example.com/saas-admin-kit',
        github_url: 'https://github.com/example/saas-admin-kit',
        image_url: 'https://picsum.photos/seed/saas-admin-kit/1200/675',
        tags: ['nextjs', 'dashboard', 'saas', 'landing', 'admin'],
    },
    {
        key: 'workflow-pack',
        title: 'AI 코드 생성 + UI 디자이너 워크플로우 템플릿 팩',
        description: '테스트용 샘플: 코드 생성과 디자이너 협업 흐름 검증용 워크플로우 패키지.',
        price: 99000,
        demo_url: 'https://demo.example.com/workflow-pack',
        github_url: 'https://github.com/example/workflow-pack',
        image_url: 'https://picsum.photos/seed/workflow-pack/1200/675',
        tags: ['ai', 'workflow', 'prompt', 'designer', 'productivity'],
    },
    {
        key: 'ops-bundle',
        title: 'Marketplace 운영 자동화 번들 (Ops Check + Full Diagnostics)',
        description: '테스트용 샘플: 운영 점검 리포트 및 진단 자동화 시나리오 검증용 번들.',
        price: 149000,
        demo_url: 'https://demo.example.com/ops-bundle',
        github_url: 'https://github.com/example/ops-bundle',
        image_url: 'https://picsum.photos/seed/ops-bundle/1200/675',
        tags: ['ops', 'diagnostics', 'monitoring', 'automation', 'marketplace'],
    },
];

function isUnauthorized(status: number) {
    return status === 401 || status === 403;
}

export async function getDefaultSampleCategoryId(options: {
    apiBaseUrl: string;
    headers: HeadersInit;
    fetchImpl?: typeof fetch;
}): Promise<number> {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/marketplace/categories`, { headers: options.headers });
    if (!response.ok) {
        throw new Error(`카테고리 조회 실패(${response.status})`);
    }
    const categories = await response.json().catch(() => []);
    if (!Array.isArray(categories) || categories.length === 0) {
        throw new Error('사용 가능한 카테고리가 없습니다. 먼저 카테고리를 생성해주세요.');
    }
    return categories[0].id;
}

export async function createAdminSampleProduct(options: {
    apiBaseUrl: string;
    token: string;
    template: SampleTemplate;
    selectedCategoryId: number;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const headers: HeadersInit = {
        Authorization: `Bearer ${options.token}`,
        'Content-Type': 'application/json',
    };
    const categoryId = options.selectedCategoryId > 0
        ? options.selectedCategoryId
        : await getDefaultSampleCategoryId({ apiBaseUrl: options.apiBaseUrl, headers, fetchImpl: fetcher });
    const payload: Record<string, unknown> = {
        ...options.template,
        category_id: categoryId,
    };
    const response = await fetcher(`${options.apiBaseUrl}/api/marketplace/projects`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SAMPLE_UNAUTHORIZED__');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(data?.detail || `샘플 상품 생성 실패(${response.status})`);
    }
    return data;
}

export async function createAdminBatchSamples(options: {
    apiBaseUrl: string;
    token: string;
    selectedCategoryId: number;
    targetCount: number;
    templates: SampleTemplate[];
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const headers: HeadersInit = {
        Authorization: `Bearer ${options.token}`,
        'Content-Type': 'application/json',
    };
    const categoryId = options.selectedCategoryId > 0
        ? options.selectedCategoryId
        : await getDefaultSampleCategoryId({ apiBaseUrl: options.apiBaseUrl, headers, fetchImpl: fetcher });
    let successCount = 0;

    for (let i = 0; i < options.targetCount; i++) {
        const base = options.templates[i % options.templates.length];
        const payload = {
            ...base,
            title: `${base.title} [샘플 ${String(i + 1).padStart(3, '0')}]`,
            description: `${base.description} (batch=${options.targetCount}, index=${i + 1})`,
            category_id: categoryId,
        };

        const response = await fetcher(`${options.apiBaseUrl}/api/marketplace/projects`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
        });
        if (isUnauthorized(response.status)) {
            throw new Error('__ADMIN_SAMPLE_UNAUTHORIZED__');
        }
        if (response.ok) {
            successCount += 1;
        }
    }

    return { successCount, targetCount: options.targetCount };
}

export async function cleanupAdminSampleProducts(options: {
    apiBaseUrl: string;
    token: string;
    pattern: string;
    dryRun: boolean;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/projects/cleanup-samples`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pattern: options.pattern, dry_run: options.dryRun }),
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SAMPLE_UNAUTHORIZED__');
    }
    const data = (await response.json().catch(() => null)) as SampleCleanupResponse | null;
    if (!response.ok || !data) {
        throw new Error((data as any)?.detail || `샘플 정리 요청 실패(${response.status})`);
    }
    return data;
}

export function assertAdminSampleProductServiceContract() {
    if (!Array.isArray(sampleTemplates) || sampleTemplates.length < 3) {
        throw new Error('admin sample product service contract 누락: 기본 샘플 템플릿 3종 필요');
    }
}
