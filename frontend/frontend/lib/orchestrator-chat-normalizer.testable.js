function normalizeCompareValue(value) {
    return String(value || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLocaleLowerCase();
}

function normalizeDisplayValue(value) {
    return String(value || '')
        .replace(/\s+/g, ' ')
        .trim();
}

function buildStrictConversationKey(message) {
    return [
        normalizeCompareValue(message.role),
        normalizeCompareValue(message.speaker),
        normalizeCompareValue(message.step_title),
        normalizeCompareValue(message.timestamp),
        normalizeCompareValue(message.content),
    ].join('::');
}

function buildFallbackConversationKey(message) {
    return [
        normalizeCompareValue(message.role),
        normalizeCompareValue(message.speaker),
        normalizeCompareValue(message.step_title),
        normalizeCompareValue(message.content),
    ].join('::');
}

function dedupeConversationMessages(messages) {
    const seenStrict = new Set();
    const seenFallback = new Set();
    const result = [];

    for (const message of [...(messages || [])].reverse()) {
        const normalized = {
            role: normalizeDisplayValue(message?.role),
            content: normalizeDisplayValue(message?.content),
            speaker: normalizeDisplayValue(message?.speaker) || null,
            timestamp: normalizeDisplayValue(message?.timestamp) || null,
            step_title: normalizeDisplayValue(message?.step_title) || null,
        };

        if (!normalized.content) {
            continue;
        }

        const fallbackKey = buildFallbackConversationKey(normalized);
        const strictKey = normalized.timestamp ? buildStrictConversationKey(normalized) : '';

        if (seenFallback.has(fallbackKey)) {
            continue;
        }
        if (strictKey && seenStrict.has(strictKey)) {
            continue;
        }

        seenFallback.add(fallbackKey);
        if (strictKey) {
            seenStrict.add(strictKey);
        }
        result.push(normalized);
    }

    return result.reverse();
}

module.exports = {
    dedupeConversationMessages,
};
