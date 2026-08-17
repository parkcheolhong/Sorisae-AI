export interface OrchestratorConversationMessage {
    role: string;
    content: string;
    speaker?: string | null;
    step_id?: string | null;
    step_title?: string | null;
    timestamp?: string | null;
    // This interface is exported for reuse in page.tsx
}

const normalizeConversationMessageKey = (message: Partial<OrchestratorConversationMessage>) => (
    [
        String(message.role || '').trim(),
        String(message.speaker || '').trim(),
        String(message.step_title || '').trim(),
        String(message.content || '').replace(/\s+/g, ' ').trim(),
    ].join('||')
);

export const dedupeConversationMessages = (messages: OrchestratorConversationMessage[]) => {
    const deduped: OrchestratorConversationMessage[] = [];
    for (const message of messages) {
        const normalizedContent = String(message.content || '').trim();
        if (!normalizedContent) {
            continue;
        }
        const nextMessage: OrchestratorConversationMessage = {
            ...message,
            content: normalizedContent,
        };
        const previous = deduped[deduped.length - 1];
        if (
            previous
            && normalizeConversationMessageKey(previous)
            === normalizeConversationMessageKey(nextMessage)
        ) {
            continue;
        }
        deduped.push(nextMessage);
    }
    return deduped;
};
