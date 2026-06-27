/**
 * Orchestrator TTS humanization contract.
 * Run: node tests/orchestrator-speech.test.mjs
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const speechSource = fs.readFileSync(path.join(frontendRoot, 'lib/orchestrator-speech.ts'), 'utf8');
const voiceEntrySource = fs.readFileSync(path.join(frontendRoot, 'lib/orchestrator-voice-entry.ts'), 'utf8');

assert.ok(speechSource.includes('humanizeOrchestratorSpeech'));
assert.ok(speechSource.includes("utterance.rate = 0.88"));
assert.ok(speechSource.includes('splitSpeechSentences'));
assert.ok(speechSource.includes('speakWithServerTts'));
assert.ok(speechSource.includes('/api/llm/voice/synthesize'));
assert.ok(speechSource.includes('나머지는 화면에서 이어서 확인해 주세요'));
assert.ok(speechSource.includes('레디스'));
assert.ok(voiceEntrySource.includes('반영해서 진행할까요?'));
assert.ok(!voiceEntrySource.includes('「'));

console.log('orchestrator-speech.test.mjs: ok');
