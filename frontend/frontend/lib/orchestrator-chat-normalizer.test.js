const assert = require('node:assert/strict');
const { dedupeConversationMessages } = require('./orchestrator-chat-normalizer.testable.js');

function message(overrides) {
    return {
        role: 'assistant',
        content: 'default message',
        speaker: null,
        timestamp: null,
        step_title: null,
        ...overrides,
    };
}

const removesEmptyContent = dedupeConversationMessages([
    message({ content: '   ' }),
    message({ content: 'kept message', timestamp: '2026-04-22T00:00:00Z' }),
]);
assert.equal(removesEmptyContent.length, 1);
assert.equal(removesEmptyContent[0].content, 'kept message');

const fallbackWithoutTimestamp = dedupeConversationMessages([
    message({ role: 'user', content: '  Hello   World  ' }),
    message({ role: 'user', content: 'hello world' }),
]);
assert.equal(fallbackWithoutTimestamp.length, 1);
assert.equal(fallbackWithoutTimestamp[0].content, 'hello world');

const latestMessageWins = dedupeConversationMessages([
    message({ role: 'assistant', content: 'same content', timestamp: '2026-04-22T00:00:00Z', speaker: 'bot' }),
    message({ role: 'assistant', content: 'same content', timestamp: '2026-04-22T00:05:00Z', speaker: 'bot' }),
]);
assert.equal(latestMessageWins.length, 1);
assert.equal(latestMessageWins[0].timestamp, '2026-04-22T00:05:00Z');

const looseNormalization = dedupeConversationMessages([
    message({ role: 'USER', content: 'Need   Summary', speaker: 'Admin' }),
    message({ role: 'user', content: 'need summary', speaker: 'admin' }),
    message({ role: 'assistant', content: 'need summary', speaker: 'admin' }),
]);
assert.equal(looseNormalization.length, 2);
assert.equal(looseNormalization[0].role, 'user');
assert.equal(looseNormalization[0].content, 'need summary');
assert.equal(looseNormalization[1].role, 'assistant');

console.log('orchestrator-chat-normalizer tests passed');
