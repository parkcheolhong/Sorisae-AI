/**
 * Voice STT SSOT helpers (orchestrator-voice-entry.ts).
 *
 * Run: node tests/orchestrator-voice-entry.test.mjs
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');

const voiceEntryPath = path.join(frontendRoot, 'lib/orchestrator-voice-entry.ts');
const voiceEntrySource = fs.readFileSync(voiceEntryPath, 'utf8');

assert.ok(voiceEntrySource.includes("ORCHESTRATOR_VOICE_CONTEXT_TAGS = ['voice-stt', 'voice-entry']"));
assert.ok(voiceEntrySource.includes('resolveVoiceSpeaker'));
assert.ok(voiceEntrySource.includes('enrichVoiceMessageForStage'));

const adminChatSource = fs.readFileSync(path.join(frontendRoot, 'lib/use-orchestrator-chat.ts'), 'utf8');
const marketplaceSource = fs.readFileSync(
    path.join(frontendRoot, 'app/marketplace/orchestrator/marketplace-orchestrator-client.tsx'),
    'utf8',
);
const liveRailSource = fs.readFileSync(path.join(frontendRoot, 'shared/orchestrator-live-flow-rail.tsx'), 'utf8');
const decisionCardSource = fs.readFileSync(path.join(frontendRoot, 'shared/orchestrator-decision-card.tsx'), 'utf8');

assert.ok(adminChatSource.includes('useOrchestratorVoiceStt'), 'admin chat must use shared voice STT hook');
assert.ok(!adminChatSource.includes('webkitSpeechRecognition'), 'admin chat must not duplicate browser STT');
assert.ok(marketplaceSource.includes('enrichVoiceMessageForStage'), 'marketplace must enrich voice transcripts');
assert.ok(marketplaceSource.includes('buildVoiceContextTags'), 'marketplace must use voice context tag SSOT');
assert.ok(liveRailSource.includes('orchestrator-live-flow-voice-entry'), 'live rail must show voice entry badge');
assert.ok(decisionCardSource.includes('buildVoiceDecisionConfirmation'), 'decision card must speak apply confirmation');

console.log('orchestrator voice-entry contract checks passed');
