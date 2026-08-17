import { expect, test, type Page } from '@playwright/test';

const MARKETPLACE_BASE_URL = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL ?? 'http://localhost:3000';

const FIXTURES = {
    categories: [
        { id: 1, name: 'AI 파워포인트 엔진', description: '파워포인트 생성' },
    ],
    projects: {
        projects: [
            {
                id: 701,
                title: '테스트 파워포인트 프로젝트',
                description: 'Playwright marketplace powerpoint fixture',
                price: 219000,
                category_id: 1,
                downloads: 2,
                rating: 5.0,
                is_active: true,
                tags: [{ id: 31, name: 'ai-powerpoint' }],
                category: { id: 1, name: 'AI 파워포인트 엔진', description: '파워포인트 생성' },
            },
        ],
        total: 1,
        skip: 0,
        limit: 24,
    },
    overview: {
        projects: 1,
        users: 5,
        purchases: 3,
        reviews: 2,
    },
    revenue: {
        total_revenue: 657000,
        total_purchases: 3,
        average_purchase_amount: 219000,
    },
    topProjects: [
        { id: 701, title: '테스트 파워포인트 프로젝트', downloads: 2, rating: 5.0, price: 219000 },
    ],
    featureCatalog: [
        {
            feature_id: 'ai-powerpoint',
            title: 'AI 파워포인트 엔진',
            summary: '슬라이드 개요 preview 와 final pptx 패키지를 생성합니다.',
            popup_mode: 'powerpoint-builder',
            status: 'enabled',
            supports_photo_upload: false,
            supports_final_phase: true,
        },
    ],
};

async function installMarketplacePowerPointMock(page: Page) {
    await page.addInitScript(({ fixtures }: { fixtures: typeof FIXTURES }) => {
        const streamBody = [
            {
                event: 'state',
                payload: {
                    run_id: 'run-ai-powerpoint-001',
                    state: 'preview_running',
                    progress: { percent: 11, step: 'preview_started', state: 'preview_running', message: 'presentation outline 생성을 시작합니다.', updated_at: '2026-04-29T06:30:01.000Z' },
                },
            },
            {
                event: 'artifact',
                payload: {
                    run_id: 'run-ai-powerpoint-001',
                    state: 'preview_ready',
                    artifact: {
                        artifact_id: 'powerpoint-preview-001',
                        artifact_type: 'presentation',
                        phase: 'preview',
                        state: 'preview_ready',
                        title: 'Presentation Preview Artifact',
                        prompt_summary: '분기 실적 발표용 슬라이드 개요 preview',
                        keywords: ['quarterly', 'kpi', 'presentation'],
                        notes: ['슬라이드 1-6 개요가 준비되었습니다.'],
                        generated_at: '2026-04-29T06:30:02.000Z',
                    },
                    progress: { percent: 45, step: 'preview_ready', state: 'preview_ready', message: 'presentation preview 가 준비되었습니다.', updated_at: '2026-04-29T06:30:02.000Z' },
                },
            },
            {
                event: 'state',
                payload: {
                    run_id: 'run-ai-powerpoint-001',
                    state: 'final_running',
                    progress: { percent: 73, step: 'final_started', state: 'final_running', message: 'pptx 패키징을 진행합니다.', updated_at: '2026-04-29T06:30:03.000Z' },
                },
            },
            {
                event: 'quality_review',
                payload: {
                    run_id: 'run-ai-powerpoint-001',
                    state: 'quality_review',
                    quality_review: {
                        passed: true,
                        score: 0.97,
                        issues: [],
                    },
                    progress: { percent: 88, step: 'quality_review', state: 'quality_review', message: 'presentation quality 검토를 진행합니다.', updated_at: '2026-04-29T06:30:04.000Z' },
                },
            },
            {
                event: 'completed',
                payload: {
                    run_id: 'run-ai-powerpoint-001',
                    state: 'completed',
                    artifact_manifest: {
                        preview_artifact: {
                            artifact_id: 'powerpoint-preview-001',
                            artifact_type: 'presentation',
                            phase: 'preview',
                            state: 'preview_ready',
                            title: 'Presentation Preview Artifact',
                            prompt_summary: '분기 실적 발표용 슬라이드 개요 preview',
                            keywords: ['quarterly', 'kpi', 'presentation'],
                            notes: ['슬라이드 1-6 개요가 준비되었습니다.'],
                            generated_at: '2026-04-29T06:30:02.000Z',
                        },
                        final_artifact: {
                            artifact_id: 'powerpoint-final-001',
                            artifact_type: 'presentation',
                            phase: 'final',
                            state: 'completed',
                            title: 'Presentation Final Artifact',
                            prompt_summary: '분기 실적 발표용 pptx final package',
                            keywords: ['quarterly', 'kpi', 'pptx'],
                            delivery_assets: [
                                {
                                    format: 'pptx',
                                    path: '/tmp/QuarterlyDeck.pptx',
                                    path_hint: 'QuarterlyDeck.pptx',
                                    size_bytes: 38912,
                                    exists: true,
                                    generated_at: '2026-04-29T06:30:06.000Z',
                                },
                            ],
                            generated_at: '2026-04-29T06:30:06.000Z',
                            notes: ['pptx 결과물이 최신 생성 파일입니다.'],
                        },
                    },
                    quality_review: {
                        passed: true,
                        score: 0.97,
                        issues: [],
                    },
                    progress: { percent: 100, step: 'completed', state: 'completed', message: 'presentation 결과물이 준비되었습니다.', updated_at: '2026-04-29T06:30:06.000Z' },
                },
            },
        ].map((item) => `data: ${JSON.stringify(item)}\n\n`).join('');

        const originalFetch = window.fetch.bind(window);
        window.fetch = async (input, init) => {
            const requestUrl = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input);
            const url = new URL(requestUrl, window.location.origin);
            const path = url.pathname;

            const jsonResponse = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
                status,
                headers: { 'Content-Type': 'application/json' },
            });

            if (path.endsWith('/api/marketplace/categories')) {
                return jsonResponse(fixtures.categories);
            }
            if (path.endsWith('/api/marketplace/projects')) {
                return jsonResponse(fixtures.projects);
            }
            if (path.endsWith('/api/marketplace/stats/overview')) {
                return jsonResponse(fixtures.overview);
            }
            if (path.endsWith('/api/marketplace/stats/revenue')) {
                return jsonResponse(fixtures.revenue);
            }
            if (path.endsWith('/api/marketplace/stats/top-projects')) {
                return jsonResponse(fixtures.topProjects);
            }
            if (path.endsWith('/api/marketplace/feature-catalog')) {
                return jsonResponse(fixtures.featureCatalog);
            }
            if (path.endsWith('/api/marketplace/feature-orchestrate/accepted')) {
                return jsonResponse({
                    run_id: 'run-ai-powerpoint-001',
                    stage_run: {
                        run_id: 'run-ai-powerpoint-001',
                        current_stage_id: 'preview',
                        status: 'running',
                        final_completed: false,
                    },
                });
            }
            if (path.includes('/api/marketplace/feature-orchestrate/stage-runs/')) {
                return jsonResponse({
                    run_id: 'run-ai-powerpoint-001',
                    current_stage_id: 'quality_review',
                    status: 'completed',
                    final_completed: true,
                });
            }
            if (path.endsWith('/api/marketplace/feature-orchestrate/stream')) {
                return new Response(streamBody, {
                    status: 200,
                    headers: {
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        Connection: 'keep-alive',
                    },
                });
            }

            return originalFetch(input, init);
        };
    }, {
        fixtures: FIXTURES,
    });
}

test('marketplace ai-powerpoint launcher validates preview final and pptx download path', async ({ page }) => {
    await installMarketplacePowerPointMock(page);

    await page.goto(`${MARKETPLACE_BASE_URL}/marketplace`);

    await expect(page.getByTestId('marketplace-feature-launcher-grid')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('marketplace-feature-card-ai-powerpoint')).toContainText('AI 파워포인트 엔진');
    await expect(page.getByTestId('marketplace-feature-card-ai-powerpoint')).toContainText('슬라이드 개요');
    await expect(page.getByTestId('marketplace-feature-card-ai-powerpoint')).toContainText('pptx 다운로드');

    await page.getByTestId('marketplace-feature-launch-ai-powerpoint').click();

    await expect(page.getByTestId('marketplace-feature-orchestrator-popup')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('marketplace-popup-project-name')).toHaveValue('marketplace-powerpoint-run');
    await page.getByTestId('marketplace-popup-project-name').fill('playwright-powerpoint-check');
    await page.getByTestId('marketplace-popup-prompt').fill('분기 실적 발표용 pptx 자료를 생성한다. KPI, 리스크, 다음 액션 슬라이드를 포함한다.');
    await page.getByTestId('marketplace-popup-submit').click();

    await expect(page.getByTestId('marketplace-popup-run-id')).toContainText('run-ai-powerpoint-001');
    await expect(page.getByTestId('marketplace-live-view-current-state')).toContainText('완료');
    await expect(page.getByTestId('marketplace-progress-percent')).toContainText('100%');
    await expect(page.getByTestId('marketplace-progress-message')).toContainText('presentation 결과물이 준비되었습니다.');
    await expect(page.getByTestId('marketplace-progress-milestones')).toContainText('presentation outline 생성을 시작합니다.');
    await expect(page.getByTestId('marketplace-progress-milestones')).toContainText('presentation preview 가 준비되었습니다.');
    await expect(page.getByTestId('marketplace-progress-milestones')).toContainText('pptx 패키징을 진행합니다.');
    await expect(page.getByTestId('marketplace-progress-milestones')).toContainText('presentation quality 검토를 진행합니다.');

    await expect(page.getByTestId('marketplace-final-artifact-card')).toContainText('최종 PowerPoint Package');
    await expect(page.getByTestId('marketplace-final-artifact-card')).toContainText('분기 실적 발표용 pptx final package');
    await expect(page.getByTestId('marketplace-preview-artifact-card')).toContainText('슬라이드 1-6 개요가 준비되었습니다.');
    await expect(page.getByTestId('marketplace-final-artifact-card')).toContainText('pptx 결과물이 최신 생성 파일입니다.');

    await expect(page.getByTestId('marketplace-spreadsheet-downloads')).toBeVisible();
    await expect(page.getByTestId('marketplace-spreadsheet-download-pptx')).toContainText('playwright-powerpoint-check.pptx');
    await expect(page.getByTestId('marketplace-spreadsheet-download-latest-badge-pptx')).toContainText('최근 생성 파일');
    await expect(page.getByTestId('marketplace-quality-gate')).toContainText('97점');
});
