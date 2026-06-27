import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

const MOCK_RUN_ID = 'dod4_redis_decision_e2e';
const REDIS_TECH_TITLE = 'Redis 캐시 계층';

function buildStageDefs() {
    return [
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
}

function buildDiscussStageRun() {
    const stages = buildStageDefs().map((def) => {
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
                    status: 'running' as const,
                    check_label: '협업 Q&A 진행 중',
                    checked: false,
                }]
                : [],
        };
    });

    return {
        run_id: MOCK_RUN_ID,
        scope: 'marketplace',
        project_name: 'dod4-redis-e2e',
        mode: 'manual_10step',
        status: 'running',
        current_stage_id: 'ARCH-004',
        final_completed: false,
        stages,
    };
}

function buildExecutedStageRun() {
    const stages = buildStageDefs().map((def) => {
        let status: 'pending' | 'running' | 'passed' = 'pending';
        let checkLabel = '대기';
        if (def.id === 'ARCH-001' || def.id === 'ARCH-002' || def.id === 'ARCH-003' || def.id === 'ARCH-004') {
            status = 'passed';
            checkLabel = '통과';
        } else if (def.id === 'ARCH-005') {
            status = 'running';
            checkLabel = '진행 중';
        }
        return {
            ...def,
            status,
            check_label: checkLabel,
            substeps: def.id === 'ARCH-004'
                ? [{
                    id: 'ARCH-004-CARD-01',
                    title: '핵심 엔진 계약',
                    summary: 'Redis 캐시 계층 반영',
                    sequence: 1,
                    status: 'passed' as const,
                    check_label: '통과',
                    checked: true,
                }]
                : [],
        };
    });

    return {
        run_id: MOCK_RUN_ID,
        scope: 'marketplace',
        project_name: 'dod4-redis-e2e',
        mode: 'manual_10step',
        status: 'running',
        current_stage_id: 'ARCH-005',
        final_completed: false,
        stages,
    };
}

function buildDiscussChatResponse(stageRun: ReturnType<typeof buildDiscussStageRun>) {
    return {
        session_id: 'dod4-redis-session',
        conversation: [
            { role: 'user', content: '4단계 Redis 캐시 아이디어 제안해줘', speaker: '고객' },
            { role: 'assistant', content: '4단계 핵심 엔진 주변에 Redis 캐시 계층을 두는 방안을 제안합니다.', speaker: '오케스트레이터' },
        ],
        technology_recommendations: [{
            title: REDIS_TECH_TITLE,
            source: 'collaborative-discuss',
            rationale: '세션·조회 캐시를 Redis로 분리하면 API 응답 지연을 줄일 수 있습니다.',
            adoption_risk: 'low',
            implementation_difficulty: 'medium',
            operating_cost: 'moderate',
            alternative: 'in-memory LRU',
        }],
        evidence_highlights: [{
            title: 'Redis 캐시 패턴',
            source_label: 'web-grounding-stub',
            why_it_matters: '4단계 엔진 경계에 캐시 계층을 두면 후속 API 단계 부하가 줄어듭니다.',
            trust_score: 0.82,
        }],
        proposal_items: [],
        next_action_suggestions: [],
        diagnostics: {
            orchestrator_core: 'autonomous_turn_controller',
            autonomous_intent: 'stage_discuss',
            stage_command: 'discuss',
            stage_number: 4,
            stages_completed: 3,
            stages_total: 11,
            current_stage: 'STAGE-04',
            execution_state: 'executing',
            approval_state: 'none',
            requires_approval: false,
            stage_command_hint: '협업 Q&A 중 — Redis 제안을 DecisionCard에서 반영할 수 있습니다.',
            llm_connected: false,
            agent_results: [
                { agent: 'reasoner', status: 'success' },
                { agent: 'planner', status: 'success' },
            ],
            synced_stage_run: stageRun,
        },
    };
}

function buildExecuteChatResponse(stageRun: ReturnType<typeof buildExecutedStageRun>) {
    return {
        session_id: 'dod4-redis-session',
        conversation: [
            { role: 'user', content: '4단계 Redis 캐시 아이디어 제안해줘', speaker: '고객' },
            { role: 'assistant', content: '4단계 핵심 엔진 주변에 Redis 캐시 계층을 두는 방안을 제안합니다.', speaker: '오케스트레이터' },
            { role: 'user', content: '4단계 진행해줘', speaker: '고객' },
            { role: 'assistant', content: 'Redis 캐시 계층을 반영하고 4단계 코드 생성을 시작합니다.', speaker: '오케스트레이터' },
        ],
        technology_recommendations: [],
        proposal_items: [],
        next_action_suggestions: [],
        diagnostics: {
            orchestrator_core: 'autonomous_turn_controller',
            autonomous_intent: 'code_generation',
            stage_command: 'execute',
            stage_number: 4,
            stages_completed: 4,
            stages_total: 11,
            current_stage: 'STAGE-04',
            execution_state: 'executing',
            approval_state: 'none',
            requires_approval: false,
            stage_command_hint: '4단계 execute — coder가 Redis 반영 코드를 생성 중입니다.',
            llm_connected: false,
            agent_results: [
                { agent: 'reasoner', status: 'success' },
                { agent: 'planner', status: 'success' },
                { agent: 'coder', status: 'running' },
            ],
            synced_stage_run: stageRun,
        },
    };
}

function isExecuteMessage(message: string): boolean {
    const normalized = String(message || '').trim();
    return /진행해/.test(normalized) || /반영하고/.test(normalized);
}

async function installDoD4Mocks(page: Page) {
    let stageRun = buildDiscussStageRun();
    let executed = false;

    await page.route('**/api/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ email: 'dod4-e2e@test.local', role: 'customer' }),
        });
    });

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
            const body = route.request().postDataJSON() as { message?: string } | null;
            const message = String(body?.message || '').trim();
            if (isExecuteMessage(message)) {
                executed = true;
                stageRun = buildExecutedStageRun();
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(buildExecuteChatResponse(stageRun)),
                });
                return;
            }
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(buildDiscussChatResponse(stageRun)),
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

        if (method === 'GET' && url.includes('/progress/')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    run_id: MOCK_RUN_ID,
                    status: executed ? 'running' : 'idle',
                    stage_number: 4,
                    stage_command: executed ? 'execute' : 'discuss',
                    substeps: executed
                        ? [{ id: 'STAGE-04 · coder', status: 'running', message: 'Redis 반영 코드 생성' }]
                        : [],
                    logs: executed
                        ? [{ id: 'exec-1', message: '4단계 execute 시작', timestamp: new Date().toISOString() }]
                        : [],
                }),
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
    await page.addInitScript(() => {
        window.localStorage.setItem('admin_token', 'admin-regression-mock-token');
    });
    await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
}

test.describe('DoD-4 Redis discuss → DecisionCard → execute → passed', () => {
    test('marketplace full scenario: Redis proposal, apply, live rail execute, ARCH-004 passed', async ({ page }) => {
        await installDoD4Mocks(page);
        await openMarketplaceOrchestrator(page);

        const stageStartButton = page.getByRole('button', { name: '단계 카드 시작' });
        await expect(stageStartButton).toBeEnabled({ timeout: 30_000 });
        await stageStartButton.click();

        const chatInput = page.getByRole('textbox', { name: /협업 대화 입력|대화형 터미널 입력/ });
        await expect(chatInput).toBeVisible({ timeout: 30_000 });
        await chatInput.fill('4단계 Redis 캐시 아이디어 제안해줘');
        await page.getByRole('button', { name: /협업 대화 전송|실행하기/ }).click();

        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail.getByTestId('orchestrator-discuss-banner')).toBeVisible({ timeout: 30_000 });
        await expect(rail.getByText(/intent:.*discuss/i)).toBeVisible();
        await expect(rail.getByText(/cmd: discuss/i)).toBeVisible();

        const decisionPanel = page.getByTestId('orchestrator-decision-panel');
        await expect(decisionPanel.getByTestId('orchestrator-decision-card')).toBeVisible();
        await expect(decisionPanel.getByText(REDIS_TECH_TITLE)).toBeVisible();
        await expect(decisionPanel.getByTestId('orchestrator-decision-evidence')).toBeVisible();

        const applyButton = decisionPanel.getByTestId('orchestrator-decision-apply');
        await expect(applyButton).toHaveText('반영하고 4단계 진행');

        const executeChatResponse = page.waitForResponse(
            (response) => {
                if (!response.url().includes('/customer-orchestrate/chat') || response.request().method() !== 'POST') {
                    return false;
                }
                try {
                    const body = response.request().postDataJSON() as { message?: string } | null;
                    return isExecuteMessage(String(body?.message || ''));
                } catch {
                    return false;
                }
            },
            { timeout: 30_000 },
        );
        await applyButton.click();
        await executeChatResponse;

        await expect(page.getByText('4단계 진행해줘')).toBeVisible({ timeout: 15_000 });
        await expect(rail.getByText('cmd: execute')).toBeVisible({ timeout: 30_000 });
        await expect(rail.getByText('intent: code generation')).toBeVisible();
        await expect(rail.locator('span').filter({ hasText: 'coder · running' }).first()).toBeVisible();

        const arch004 = page.locator('[data-stage-id="ARCH-004"]');
        await expect(arch004).toHaveAttribute('data-stage-status', 'passed', { timeout: 30_000 });

        const arch005 = page.locator('[data-stage-id="ARCH-005"]');
        await expect(arch005).toHaveAttribute('data-stage-status', 'running');
    });
});
