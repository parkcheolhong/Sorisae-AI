/**
 * Discuss-mode live flow + stage card contract checks (source-level).
 *
 * Run: node tests/orchestrator-live-flow-discuss.test.mjs
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');

const liveFlowSource = fs.readFileSync(path.join(frontendRoot, 'lib/orchestrator-live-flow.ts'), 'utf8');
const stageCardSource = fs.readFileSync(path.join(frontendRoot, 'shared/orchestrator-stage-card-panel.tsx'), 'utf8');
const liveRailSource = fs.readFileSync(path.join(frontendRoot, 'shared/orchestrator-live-flow-rail.tsx'), 'utf8');
const discussBannerSource = fs.readFileSync(path.join(frontendRoot, 'shared/orchestrator-discuss-banner.tsx'), 'utf8');
const marketplaceSource = fs.readFileSync(
    path.join(frontendRoot, 'app/marketplace/orchestrator/marketplace-orchestrator-client.tsx'),
    'utf8',
);

assert.ok(
    liveFlowSource.includes('export function isDiscussIntent'),
    'orchestrator-live-flow must export isDiscussIntent',
);
assert.ok(
    liveFlowSource.includes('export function resolveDiscussArchId'),
    'orchestrator-live-flow must export resolveDiscussArchId',
);
assert.ok(
    liveFlowSource.includes("'ARCH-004'"),
    'resolveDiscussArchId must map stage 4 to ARCH-004',
);
assert.ok(
    stageCardSource.includes('orchestrator-stage-discuss-overlay'),
    'StageCardPanel must expose discuss overlay test id',
);
assert.ok(
    stageCardSource.includes('orchestrator-discuss-arch004-badge'),
    'StageCardPanel must expose ARCH-004 discuss badge',
);
assert.ok(
    stageCardSource.includes('orchestrator-stage-grid-discuss-highlight'),
    'StageCardPanel must highlight discuss stage in grid',
);
assert.ok(
    liveRailSource.includes('OrchestratorDiscussBanner'),
    'Live flow rail must mount discuss banner in discuss mode',
);
assert.ok(
    liveRailSource.includes('orchestrator-live-flow-stage-discuss'),
    'Live flow rail must tag active discuss stage chip',
);
assert.ok(
    discussBannerSource.includes('orchestrator-discuss-banner'),
    'Discuss banner component must expose stable test id',
);
assert.ok(
    marketplaceSource.includes('resolveDiscussArchId'),
    'Marketplace orchestrator must wire resolveDiscussArchId for rail/card sync',
);
assert.ok(
    marketplaceSource.includes('highlightStageId={discussHighlightArchId}'),
    'Marketplace orchestrator must pass highlightStageId to StageCardPanel',
);

assert.ok(
    liveRailSource.includes('orchestrator-live-flow-progress-polling'),
    'Live flow rail must expose progress polling badge',
);
assert.ok(
    liveRailSource.includes('orchestrator-live-flow-progress-logs'),
    'Live flow rail must expose progress log strip',
);
assert.ok(
    liveRailSource.includes('orchestrator-live-flow-substeps'),
    'Live flow rail must expose substep trace',
);
assert.ok(
    marketplaceSource.includes('mergeLiveFlowWithProgress'),
    'Marketplace must merge HTTP progress into live flow snapshot',
);

const discuss4Spec = fs.readFileSync(
    path.join(frontendRoot, 'tests/orchestrator-discuss4-stage-run.playwright.spec.ts'),
    'utf8',
);
assert.ok(
    discuss4Spec.includes('data-stage-id="ARCH-005"'),
    'Discuss-4 Playwright must assert ARCH-005 pending via data-stage-status',
);
assert.ok(
    discuss4Spec.includes('data-stage-id="ARCH-004"'),
    'Discuss-4 Playwright must assert ARCH-004 discuss highlight',
);

assert.ok(
    liveRailSource.includes('orchestrator-live-flow-voice-entry'),
    'Live flow rail must expose voice entry badge',
);

const dod4Spec = fs.readFileSync(
    path.join(frontendRoot, 'tests/orchestrator-dod4-redis-decision.playwright.spec.ts'),
    'utf8',
);
assert.ok(
    dod4Spec.includes('orchestrator-decision-apply'),
    'DoD-4 Playwright must click decision apply button',
);
assert.ok(
    dod4Spec.includes('data-stage-status'),
    'DoD-4 Playwright must assert stage card passed status',
);

assert.ok(
    marketplaceSource.includes('OrchestratorThreeTrackDiagram'),
    'Marketplace must mount three-track execution diagram',
);
assert.ok(
    marketplaceSource.includes('showLegacyStructuredResponse'),
    'Marketplace must hide legacy structured-response when Decision Panel has items',
);

const adminLlmSource = fs.readFileSync(
    path.join(frontendRoot, 'app/admin/llm/page.tsx'),
    'utf8',
);
assert.ok(
    adminLlmSource.includes('orchestrator-workbench'),
    'Admin llm must expose unified orchestrator workbench test id',
);

console.log('orchestrator live-flow discuss contract checks passed');
