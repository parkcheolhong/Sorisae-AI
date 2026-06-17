import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const progressSource = fs.readFileSync(path.join(frontendRoot, 'lib/orchestrator-live-progress.ts'), 'utf8');
const streamHookSource = fs.readFileSync(path.join(frontendRoot, 'lib/use-orchestrator-live-progress-stream.ts'), 'utf8');
const unifiedHookSource = fs.readFileSync(path.join(frontendRoot, 'lib/use-orchestrator-live-progress.ts'), 'utf8');

test('orchestrator live progress stream contract', () => {
    assert.ok(progressSource.includes("'autonomous_sse'"));
    assert.ok(progressSource.includes("'autonomous_ws'"));
    assert.ok(progressSource.includes('progress_streaming'));
    assert.ok(streamHookSource.includes('new EventSource'));
    assert.ok(streamHookSource.includes("addEventListener('progress'"));
    assert.ok(streamHookSource.includes('new WebSocket'));
    assert.ok(unifiedHookSource.includes('/orchestrate/stream/'));
    assert.ok(unifiedHookSource.includes('/customer-orchestrate/progress/stream/'));
});
