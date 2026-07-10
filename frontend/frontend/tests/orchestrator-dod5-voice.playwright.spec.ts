import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

const VOICE_TRANSCRIPT = '4단계 Redis 캐시 아이디어 제안해줘';
const REDIS_TECH_TITLE = 'Redis 캐시 계층';

function installMockSpeechRecognition(page: Page, transcript: string) {
    return page.addInitScript((spokenText: string) => {
        class MockSpeechRecognition {
            lang = 'ko-KR';
            interimResults = false;
            maxAlternatives = 1;
            onresult: ((event: { results?: Array<Array<{ transcript?: string }>> }) => void) | null = null;
            onerror: ((event: { error?: string }) => void) | null = null;
            onend: (() => void) | null = null;

            start() {
                window.setTimeout(() => {
                    this.onresult?.({
                        results: [[{ transcript: spokenText }]],
                    });
                    this.onend?.();
                }, 30);
            }

            stop() {
                this.onend?.();
            }
        }

        const speechWindow = window as Window & {
            SpeechRecognition?: typeof MockSpeechRecognition;
            webkitSpeechRecognition?: typeof MockSpeechRecognition;
        };
        speechWindow.SpeechRecognition = MockSpeechRecognition;
        speechWindow.webkitSpeechRecognition = MockSpeechRecognition;
    }, transcript);
}

async function seedMarketplaceAuth(page: Page) {
    await page.addInitScript(() => {
        window.localStorage.setItem('customer_token', 'customer-regression-mock-token');
        window.localStorage.setItem('admin_token', 'admin-regression-mock-token');
    });
}

async function seedAdminAuth(page: Page) {
    await page.addInitScript(() => {
        window.localStorage.setItem('admin_token', 'admin-regression-mock-token');
    });
}

function buildDiscussStageRun() {
    const defs = [
        { id: 'ARCH-001', label: '1단계', title: '구조 설계', summary: '요구사항·구조 고정', sequence: 1 },
        { id: 'ARCH-002', label: '2단계', title: '폴더·기초', summary: '골조 생성', sequence: 2 },
        { id: 'ARCH-003', label: '3단계', title: '골조 구현', summary: '설계 반영', sequence: 3 },
        { id: 'ARCH-004', label: '4단계', title: '핵심엔진 구성', summary: '엔진 계약', sequence: 4 },
        { id: 'ARCH-005', label: '5단계', title: '로직(ID식별)', summary: '로직 고정', sequence: 6 },
    ];
    const stages = defs.map((def) => {
        let status: 'pending' | 'running' | 'passed' = 'pending';
        let checkLabel = '대기';
        if (def.id === 'ARCH-001' || def.id === 'ARCH-002' || def.id === 'ARCH-003') {
            status = 'passed';
            checkLabel = '통과';
        } else if (def.id === 'ARCH-004') {
            status = 'running';
            checkLabel = '협업 Q&A';
        }
        return { ...def, status, check_label: checkLabel, substeps: [] };
    });
    return {
        run_id: 'dod5_voice_e2e',
        scope: 'marketplace',
        project_name: 'dod5-voice-e2e',
        mode: 'manual_10step',
        status: 'running',
        current_stage_id: 'ARCH-004',
        final_completed: false,
        stages,
    };
}

function buildDiscussDiagnostics(stageRun: ReturnType<typeof buildDiscussStageRun>) {
    return {
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
        voice_entry: true,
        voice_speaker: '고객(음성)',
        agent_results: [
            { agent: 'reasoner', status: 'success' },
            { agent: 'planner', status: 'success' },
        ],
        synced_stage_run: stageRun,
    };
}

async function installMarketplaceVoiceMocks(page: Page) {
    const stageRun = buildDiscussStageRun();
    let sawVoiceTags = false;

    await page.route('**/api/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ email: 'dod5-voice@test.local', role: 'customer' }),
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
            const body = route.request().postDataJSON() as {
                message?: string;
                context_tags?: string[];
            } | null;
            const tags = Array.isArray(body?.context_tags) ? body.context_tags : [];
            sawVoiceTags = tags.includes('voice-stt') && tags.includes('voice-entry');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 'dod5-voice-session',
                    conversation: [
                        { role: 'user', content: body?.message || VOICE_TRANSCRIPT, speaker: '고객(음성)' },
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
                    evidence_highlights: [],
                    proposal_items: [],
                    next_action_suggestions: [],
                    diagnostics: buildDiscussDiagnostics(stageRun),
                }),
            });
            return;
        }

        if (url.includes('/completions/my') || url.includes('/logs/my') || url.includes('/retry-queue/my')) {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) });
            return;
        }

        if (url.includes('/generated-programs/latest')) {
            await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'none' }) });
            return;
        }

        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    });

    return {
        assertVoiceTags: () => expect(sawVoiceTags).toBe(true),
    };
}

async function installAdminVoiceMocks(page: Page) {
    let sawVoiceTags = false;

    await page.route('**/*orchestrate/chat*', async (route) => {
        const body = route.request().postDataJSON() as {
            message?: string;
            context_tags?: string[];
        } | null;
        const tags = Array.isArray(body?.context_tags) ? body.context_tags : [];
        sawVoiceTags = tags.includes('voice-stt') && tags.includes('voice-entry');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                session_id: 'dod5-admin-voice-session',
                reply: { content: '4단계 핵심 엔진 주변에 Redis 캐시 계층을 두는 방안을 제안합니다.' },
                conversation: [
                    { role: 'user', content: body?.message || VOICE_TRANSCRIPT, speaker: '관리자(음성)' },
                    { role: 'assistant', content: '4단계 핵심 엔진 주변에 Redis 캐시 계층을 두는 방안을 제안합니다.' },
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
                diagnostics: {
                    orchestrator_core: 'autonomous_turn_controller',
                    autonomous_intent: 'stage_discuss',
                    stage_command: 'discuss',
                    stage_number: 4,
                    stages_completed: 3,
                    stages_total: 11,
                    voice_entry: true,
                    voice_speaker: '관리자(음성)',
                    agent_results: [
                        { agent: 'reasoner', status: 'success' },
                        { agent: 'planner', status: 'success' },
                    ],
                },
            }),
        });
    });

    return {
        assertVoiceTags: () => expect(sawVoiceTags).toBe(true),
    };
}

test.describe('DoD-5 voice STT → discuss scenario', () => {
    test('marketplace: mic STT triggers Redis discuss, voice badge, DecisionCard', async ({ page }) => {
        await seedMarketplaceAuth(page);
        await installMockSpeechRecognition(page, VOICE_TRANSCRIPT);
        const mocks = await installMarketplaceVoiceMocks(page);
        await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
        await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });

        const voiceButton = page.getByTestId('marketplace-orchestrator-voice-input-top');
        await expect(voiceButton).toBeEnabled({ timeout: 30_000 });

        const stageStartButton = page.getByRole('button', { name: '단계 카드 시작' });
        await expect(stageStartButton).toBeEnabled({ timeout: 30_000 });
        await stageStartButton.click();

        const chatResponse = page.waitForResponse(
            (response) => response.url().includes('/customer-orchestrate/chat') && response.request().method() === 'POST',
            { timeout: 30_000 },
        );
        await voiceButton.click();
        await chatResponse;
        await mocks.assertVoiceTags();

        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail.getByTestId('orchestrator-live-flow-voice-entry')).toBeVisible({ timeout: 30_000 });
        await expect(rail.getByText(/고객\(음성\)/)).toBeVisible();
        await expect(rail.getByTestId('orchestrator-discuss-banner')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-panel').getByText(REDIS_TECH_TITLE)).toBeVisible();
    });

    test('admin: mic STT triggers Redis discuss and voice badge on live rail', async ({ page }) => {
        await seedAdminAuth(page);
        await installMockSpeechRecognition(page, VOICE_TRANSCRIPT);
        const mocks = await installAdminVoiceMocks(page);
        await page.route('**/api/auth/me', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ email: 'dod5-admin@test.local', is_admin: true }),
            });
        });
        await page.goto('/admin/llm', { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: 'AI 코드 제너레이터' })).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-workbench')).toBeVisible({ timeout: 60_000 });

        const voiceButton = page.getByTestId('admin-orchestrator-voice-input-top');
        await expect(voiceButton).toBeEnabled({ timeout: 30_000 });

        const chatResponse = page.waitForResponse(
            (response) => response.url().includes('orchestrate/chat') && response.request().method() === 'POST',
            { timeout: 30_000 },
        );
        await voiceButton.click();
        await chatResponse;
        await mocks.assertVoiceTags();

        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail.getByTestId('orchestrator-live-flow-voice-entry')).toBeVisible({ timeout: 30_000 });
        await expect(rail.getByText(/관리자\(음성\)/)).toBeVisible();
        await expect(rail.getByTestId('orchestrator-discuss-banner')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-panel').getByText(REDIS_TECH_TITLE)).toBeVisible();
    });
});
