import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');

const capabilityPanel = fs.readFileSync(path.join(frontendRoot, 'components/ui/CapabilityPanel.tsx'), 'utf8');
const orchestration = fs.readFileSync(path.join(frontendRoot, 'lib/admin-capability-orchestration.ts'), 'utf8');
const expansionRun = fs.readFileSync(path.join(frontendRoot, 'lib/admin-expansion-experiment-run.ts'), 'utf8');
const presets = fs.readFileSync(path.join(frontendRoot, 'lib/admin-self-run-presets.ts'), 'utf8');

assert.match(capabilityPanel, /확장 실험 self-expansion 실행/);
assert.match(capabilityPanel, /PowerShell 명령이 아닙니다/);
assert.match(orchestration, /action\.id === 'code-generator'/);
assert.match(orchestration, /executeSelfWorkflow\('self-expansion'/);
assert.match(expansionRun, /tower_crane_expansion/);
assert.match(presets, /'self-expansion': 'full'/);

console.log('admin-expansion-experiment-run.test.mjs passed');
