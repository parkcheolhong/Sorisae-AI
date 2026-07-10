/**
 * G-5-3 orchestrator chat endpoint SSOT contract.
 *
 * Run: node tests/orchestrator-chat-endpoints.test.mjs
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');

const read = (relativePath) => fs.readFileSync(path.join(frontendRoot, relativePath), 'utf8');

const endpointsSource = read('lib/orchestrator-chat-endpoints.ts');
const chatClientSource = read('lib/orchestrator-chat-client.ts');
const adminChatSource = read('lib/use-orchestrator-chat.ts');
const marketplaceSource = read('app/marketplace/orchestrator/marketplace-orchestrator-client.tsx');
const autonomousClientSource = read('lib/autonomous-orchestrator-client.ts');

assert.ok(endpointsSource.includes("ORCHESTRATOR_ADMIN_CHAT_PATH = '/api/llm/orchestrate/chat'"));
assert.ok(endpointsSource.includes("ORCHESTRATOR_MARKETPLACE_CHAT_PATH = '/api/marketplace/customer-orchestrate/chat'"));
assert.ok(endpointsSource.includes("ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH = '/api/llm/autonomous/chat'"));

assert.ok(chatClientSource.includes('postAdminOrchestratorChat'));
assert.ok(chatClientSource.includes('postCustomerOrchestratorChat'));
assert.ok(chatClientSource.includes('buildAdminOrchestratorChatUrl'));
assert.ok(chatClientSource.includes('buildMarketplaceOrchestratorChatUrl'));

assert.ok(adminChatSource.includes('postAdminOrchestratorChat'), 'admin chat must use SSOT client');
assert.ok(!adminChatSource.includes('/api/llm/orchestrate/chat`'), 'admin chat must not inline orchestrate URL');

assert.ok(marketplaceSource.includes('postCustomerOrchestratorChat'), 'marketplace must use SSOT client');
assert.ok(!marketplaceSource.includes('/api/marketplace/customer-orchestrate/chat`'), 'marketplace must not inline customer URL');

assert.ok(autonomousClientSource.includes('postAdminOrchestratorChat'), 'debug panel must route via orchestrate/chat');
assert.ok(autonomousClientSource.includes('postDebugRawAutonomousChat'), 'raw autonomous path reserved for scripts');

console.log('orchestrator-chat-endpoints.test.mjs: ok');
