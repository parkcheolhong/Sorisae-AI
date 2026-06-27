import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

const MOCK_RUN_ID = 'stage_run_discuss4_e2e';

function buildDiscuss4StageRun() {
    const stageDefs = [
        { id: 'ARCH-001', label: '1단계', title: '구조 설계', summary: '요구사항·구조 고정', sequence: 1 },
        { id: 'ARCH-002', label: '2단계', title: '폴더·기초', summary: '골조 생성', sequence: 2 },
        { id: 'ARCH-003', label: '3단계', title: '골조 구현', summary: '설계 반영', sequence: 3 },
        { id: 'ARCH-004', label: '4단계', title: '핵심엔진 구성', summary: '엔진 계약', sequence: 4 },
        { id: 'ARCH-0045', label: '4.5단계', title: 'Refiner/Fixer', summary: '구조 정리', sequence: 5 },
        { id: 'ARCH-005', label: '5단계', title: '로직(ID식별)', summary: '로직 고정', sequence: 6 },
        { id: 'ARCH-006', label: '6단계', title: '데이터', summary: '데이터 계약', sequence: 7 },
        { id: 'ARCH-007', label: '7단계', title: '서비스', summary: '서비스 조립', sequence: 8 },
        { id: 'ARCH-008', label: '8단계', title: 'API', summary: 'API 계약', sequence: 9 },
        { id: 'ARCH-009', label: '9단계', title: '프론트', summary: 'UI 마감', sequence: 10 },
        { id: 'ARCH-010', label: '10단계', title: '운영 협업/검증', summary: '운영 검증', sequence: 11 },
    ];

    const stages = stageDefs.map((def) => {
        let status: 'pending' | 'running' | 'passed' = 'pending';
        let checkLabel = '대기';
        if (def.id === 'ARCH-001' || def.id === 'ARCH-002' || def.id === 'ARCH-003') {
            status = 'passed';
            checkLabel = '통과';
        } else if (def.id === 'ARCH-004') {
            status = 'running';
            checkLabel = '협업 Q&A';
        }
        return {
            ...def,
            status,
            check_label: checkLabel,
            substeps: def.id === 'ARCH-004'
                ? [{
                    id: 'ARCH-004-CARD-01',
                    title: '핵심 엔진 계약',
                    summary: '도메인 핵심 엔진 계약',
                    sequence: 1,
                    status: 'running',
                    check_label: '협업 Q&A 진행 중',
                    checked: false,
                }]
                : [],
        };
    });

    return {
        run_id: MOCK_RUN_ID,
        scope: 'marketplace',
        project_name: 'discuss4-e2e',
        mode: 'manual_10step',
        status: 'running',
        current_stage_id: 'ARCH-004',
        final_completed: false,
        stages,
    };
}

function buildDiscuss4ChatResponse(stageRun: ReturnType<typeof buildDiscuss4StageRun>) {
    return {
        session_id: 'discuss4-e2e-session',
        conversation: [
            { role: 'user', content: '4단계 Redis 캐시 아이디어 제안해줘', speaker: '고객' },
            { role: 'assistant', content: 'Redis 캐시 계층을 4단계 엔진 주변에 두는 방안을 제안합니다.', speaker: 'reasoner' },
        ],
        diagnostics: {
            orchestrator_core: 'autonomous',
            autonomous_intent: 'stage_discuss',
            stage_command: 'discuss',
            stage_number: 4,
            stages_completed: 3,
            stages_total: 11,
            current_stage: 'STAGE-04',
            execution_state: 'executing',
            approval_state: 'none',
            requires_approval: false,
            stage_command_hint: '협업 Q&A 중 — 코드 생성은 「5단계 진행해줘」로 시작하세요.',
            llm_connected: false,
            agent_results: [
                { agent: 'reasoner', status: 'success' },
                { agent: 'planner', status: 'success' },
            ],
            synced_stage_run: stageRun,
        },
    };
}

async function installDiscuss4Mocks(page: Page) {
    const stageRun = buildDiscuss4StageRun();
    const chatPayload = buildDiscuss4ChatResponse(stageRun);

    await page.route('**/api/marketplace/customer-orchestrate/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        if (method === 'POST' && url.includes('/customer-orchestrate/stage-runs') && !url.includes('/update')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(stageRun),
            });
            return;
        }

        if (method === 'POST' && url.includes('/customer-orchestrate/chat')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(chatPayload),
            });
            return;
        }

        if (method === 'GET' && url.includes(`/stage-runs/${MOCK_RUN_ID}`)) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(stageRun),
            });
            return;
        }

        if (url.includes('/completions/my') || url.includes('/logs/my') || url.includes('/retry-queue/my')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ items: [] }),
            });
            return;
        }

        if (url.includes('/generated-programs/latest')) {
            await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'none' }) });
            return;
        }

        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ ok: true }),
        });
    });
}

async function openMarketplaceOrchestrator(page: Page) {
    await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
}

test.describe('Discuss-4 stage_run UX contract (G-4-3)', () => {
    test('marketplace discuss keeps ARCH-004 active and ARCH-005 pending', async ({ page }) => {
        await installDiscuss4Mocks(page);
        await openMarketplaceOrchestrator(page);

        await page.getByRole('button', { name: '단계 카드 시작' }).click();

        const chatInput = page.getByRole('textbox', { name: /협업 대화 입력|대화형 터미널 입력/ });
        await expect(chatInput).toBeVisible({ timeout: 30_000 });
        await chatInput.fill('4단계 Redis 캐시 아이디어 제안해줘');
        await page.getByRole('button', { name: /협업 대화 전송|실행하기/ }).click();

        await expect(page.getByTestId('orchestrator-discuss-banner').first()).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('orchestrator-live-flow-rail').getByTestId('orchestrator-discuss-banner')).toBeVisible();
        await expect(page.getByTestId('orchestrator-live-flow-stage-discuss')).toBeVisible();
        await expect(page.getByTestId('orchestrator-stage-discuss-overlay')).toBeVisible();
        await expect(page.getByTestId('orchestrator-discuss-arch004-badge')).toContainText('아이디어·기술 제안 대화 중');

        const arch004 = page.locator('[data-stage-id="ARCH-004"]');
        const arch005 = page.locator('[data-stage-id="ARCH-005"]');
        await expect(arch004).toHaveAttribute('data-stage-status', 'running');
        await expect(arch005).toHaveAttribute('data-stage-status', 'pending');
        await expect(page.getByTestId('orchestrator-stage-grid-discuss-highlight')).toHaveCount(1);
        await expect(page.getByTestId('orchestrator-stage-grid-discuss-highlight')).toHaveAttribute('data-stage-id', 'ARCH-004');
    });
});
