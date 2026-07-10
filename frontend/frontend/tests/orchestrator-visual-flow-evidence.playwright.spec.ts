import * as fs from 'node:fs';
import * as path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

const EVIDENCE_DATE = process.env.ORCHESTRATOR_EVIDENCE_DATE || '20260617';
const EVIDENCE_DIR = path.resolve(__dirname, '../../../evidence', `orchestrator-visual-flow-${EVIDENCE_DATE}`);
const VOICE_TRANSCRIPT = '4단계 Redis 캐시 아이디어 제안해줘';

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
                    this.onresult?.({ results: [[{ transcript: spokenText }]] });
                    this.onend?.();
                }, 30);
            }
            stop() { this.onend?.(); }
        }
        const w = window as Window & { SpeechRecognition?: typeof MockSpeechRecognition; webkitSpeechRecognition?: typeof MockSpeechRecognition };
        w.SpeechRecognition = MockSpeechRecognition;
        w.webkitSpeechRecognition = MockSpeechRecognition;
    }, transcript);
}

async function installMarketplaceDiscussMocks(page: Page) {
    await page.route('**/api/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ email: 'evidence@test.local', role: 'customer' }),
        });
    });

    const stageRun = {
        run_id: 'evidence_visual_flow',
        scope: 'marketplace',
        project_name: 'evidence-flow',
        mode: 'manual_10step',
        status: 'running',
        current_stage_id: 'ARCH-004',
        final_completed: false,
        stages: [
            { id: 'ARCH-004', label: '4단계', title: '핵심엔진 구성', summary: '엔진 계약', sequence: 4, status: 'running', check_label: '협업 Q&A', substeps: [] },
        ],
    };

    await page.route('**/api/marketplace/customer-orchestrate/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        if (method === 'POST' && url.includes('/chat')) {
            const body = route.request().postDataJSON() as { context_tags?: string[]; message?: string } | null;
            const tags = Array.isArray(body?.context_tags) ? body.context_tags : [];
            const isVoice = tags.includes('voice-stt');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 'evidence-session',
                    conversation: [
                        { role: 'user', content: body?.message || '4단계 Redis 캐시 아이디어', speaker: isVoice ? '고객(음성)' : '고객' },
                        { role: 'assistant', content: 'Redis 캐시 계층 제안', speaker: '오케스트레이터' },
                    ],
                    technology_recommendations: [{
                        title: 'Redis 캐시 계층',
                        rationale: '4단계 엔진 경계 캐시',
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
                        ...(isVoice ? { voice_entry: true, voice_speaker: '고객(음성)' } : {}),
                        synced_stage_run: stageRun,
                    },
                }),
            });
            return;
        }

        if (method === 'POST' && url.includes('/stage-runs') && !url.includes('/update')) {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stageRun) });
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
}

test.describe('G-0-4-5 visual flow evidence capture', () => {
    test.beforeAll(() => {
        fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
        fs.writeFileSync(
            path.join(EVIDENCE_DIR, 'README.md'),
            [
                `# Orchestrator visual flow evidence (${EVIDENCE_DATE})`,
                '',
                '| File | Surface | Description |',
                '|------|---------|-------------|',
                '| `01-admin-workbench-live-flow.png` | Admin `/admin/llm` | Live Flow Rail + Decision Panel workbench |',
                '| `02-marketplace-three-track-discuss.png` | Marketplace | 3-track diagram + discuss DecisionCard |',
                '| `03-admin-voice-live-rail.png` | Admin | 음성 STT → voice badge + discuss rail (G-3-3-2) |',
                '| `04-marketplace-voice-live-rail.png` | Marketplace | 음성 STT → voice badge + DecisionCard (G-3-3-3) |',
                '',
                'Regenerate:',
                '',
                '```powershell',
                'cd frontend/frontend',
                'npm run e2e:orchestrator-visual-evidence',
                '```',
                '',
            ].join('\n'),
            'utf8',
        );
    });

    test('capture admin workbench screenshot', async ({ page }) => {
        await page.goto('/admin/llm', { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: 'AI 코드 제너레이터' })).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-workbench')).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible();
        await page.locator('[data-testid="orchestrator-workbench"]').screenshot({
            path: path.join(EVIDENCE_DIR, '01-admin-workbench-live-flow.png'),
        });
    });

    test('capture marketplace discuss screenshot', async ({ page }) => {
        await installMarketplaceDiscussMocks(page);
        await page.addInitScript(() => {
            window.localStorage.setItem('admin_token', 'admin-regression-mock-token');
        });
        await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
        await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-three-track-diagram')).toBeVisible();

        const stageStartButton = page.getByRole('button', { name: '단계 카드 시작' });
        await expect(stageStartButton).toBeEnabled({ timeout: 30_000 });
        await stageStartButton.click();

        const chatInput = page.getByRole('textbox', { name: /협업 대화 입력|대화형 터미널 입력/ });
        await chatInput.fill('4단계 Redis 캐시 아이디어');
        await page.getByRole('button', { name: /협업 대화 전송|실행하기/ }).click();
        await expect(page.getByTestId('orchestrator-decision-card')).toBeVisible({ timeout: 30_000 });

        await page.locator('[data-testid="orchestrator-live-flow-rail"]').screenshot({
            path: path.join(EVIDENCE_DIR, '02-marketplace-three-track-discuss.png'),
        });
    });

    test('capture admin voice STT evidence (G-3-3-2)', async ({ page }) => {
        await installMockSpeechRecognition(page, VOICE_TRANSCRIPT);
        await page.addInitScript(() => {
            window.localStorage.setItem('admin_token', 'admin-regression-mock-token');
        });
        await page.route('**/*orchestrate/chat*', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 'evidence-admin-voice',
                    reply: { content: '4단계 Redis 캐시 계층을 제안합니다.' },
                    technology_recommendations: [{ title: 'Redis 캐시 계층', rationale: '캐시', adoption_risk: 'low', implementation_difficulty: 'medium', operating_cost: 'moderate', alternative: 'memory' }],
                    diagnostics: {
                        orchestrator_core: 'autonomous_turn_controller',
                        autonomous_intent: 'stage_discuss',
                        stage_command: 'discuss',
                        stage_number: 4,
                        voice_entry: true,
                        voice_speaker: '관리자(음성)',
                    },
                }),
            });
        });
        await page.goto('/admin/llm', { waitUntil: 'domcontentloaded' });
        await expect(page.getByTestId('orchestrator-workbench')).toBeVisible({ timeout: 60_000 });
        const voiceButton = page.getByTestId('admin-orchestrator-voice-input-top');
        await expect(voiceButton).toBeEnabled({ timeout: 30_000 });
        await voiceButton.click();
        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail.getByTestId('orchestrator-live-flow-voice-entry')).toBeVisible({ timeout: 30_000 });
        await rail.screenshot({ path: path.join(EVIDENCE_DIR, '03-admin-voice-live-rail.png') });
    });

    test('capture marketplace voice STT evidence (G-3-3-3)', async ({ page }) => {
        await installMockSpeechRecognition(page, VOICE_TRANSCRIPT);
        await installMarketplaceDiscussMocks(page);
        await page.addInitScript(() => {
            window.localStorage.setItem('customer_token', 'customer-regression-mock-token');
        });
        await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
        await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
        await page.getByRole('button', { name: '단계 카드 시작' }).click();
        const voiceButton = page.getByTestId('marketplace-orchestrator-voice-input-top');
        await expect(voiceButton).toBeEnabled({ timeout: 30_000 });
        await voiceButton.click();
        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail.getByTestId('orchestrator-live-flow-voice-entry')).toBeVisible({ timeout: 30_000 });
        await expect(rail.getByText(/고객\(음성\)/)).toBeVisible();
        await rail.screenshot({ path: path.join(EVIDENCE_DIR, '04-marketplace-voice-live-rail.png') });
    });
});
