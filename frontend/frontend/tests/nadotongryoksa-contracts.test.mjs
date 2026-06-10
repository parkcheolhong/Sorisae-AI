/**
 * WorldLinco/Nadotongryoksa contract checks.
 *
 * These source-level assertions guard API response keys and artifact names that
 * are otherwise easy to regress without spinning up the full backend.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendRoot, '..', '..');

const pageSource = fs.readFileSync(path.join(frontendRoot, 'app/marketplace/nadotongryoksa/page.tsx'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf8'));
const adminWorkflow = fs.readFileSync(path.join(repoRoot, '.github/workflows/admin-regression.yml'), 'utf8');

assert.ok(
    !pageSource.includes('project_id: 0'),
    'WorldLinco purchases must resolve a real marketplace project id',
);
assert.ok(
    pageSource.includes('resolveNadotongryoksaProjectId'),
    'WorldLinco payment flow should resolve the seeded marketplace project',
);
assert.ok(
    pageSource.includes('data.purchases ?? data.items ?? []'),
    'Purchase history must consume the backend purchases response key',
);
assert.ok(
    pageSource.includes('data.translated ?? data.result ?? spokenText'),
    'Interpreter call mode must consume the backend translated response key',
);
assert.ok(
    pageSource.includes("const NADO_APK_FILENAME = 'nadotongryoksa-v1.apk'"),
    'APK download should target the seeded Nadotongryoksa artifact',
);
assert.ok(
    !pageSource.includes('nadotongryoksa-v8.apk'),
    'APK download must not request the non-existent v8 artifact',
);

assert.ok(
    packageJson.scripts['ci:admin-regression:full']?.includes('tests/admin-llm-render.playwright.spec.ts'),
    'Admin full regression script must exist and include the full-lane specs',
);
assert.ok(
    adminWorkflow.includes("'frontend/frontend/playwright.config.ts'"),
    'Admin full regression path filter must include the TypeScript Playwright config',
);
assert.ok(
    !adminWorkflow.includes("'frontend/frontend/playwright.config.cjs'"),
    'Admin full regression path filter should not reference the removed CJS config',
);

console.log('✓ nadotongryoksa contract checks: PASS');
