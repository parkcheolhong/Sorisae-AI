/** Admin · Marketplace orchestrator chat SSOT paths (G-5-3). */
export const ORCHESTRATOR_ADMIN_CHAT_PATH = '/api/llm/orchestrate/chat';

export const ORCHESTRATOR_MARKETPLACE_CHAT_PATH = '/api/marketplace/customer-orchestrate/chat';

/** Raw TurnController HTTP — debug / scripts only; prefer ORCHESTRATOR_ADMIN_CHAT_PATH. */
export const ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH = '/api/llm/autonomous/chat';

export const ORCHESTRATOR_DEBUG_AUTONOMOUS_SESSION_PATH = '/api/llm/autonomous/session';

export function buildAdminOrchestratorChatUrl(apiBaseUrl: string): string {
    return `${apiBaseUrl.replace(/\/$/, '')}${ORCHESTRATOR_ADMIN_CHAT_PATH}`;
}

export function buildMarketplaceOrchestratorChatUrl(apiBaseUrl: string): string {
    return `${apiBaseUrl.replace(/\/$/, '')}${ORCHESTRATOR_MARKETPLACE_CHAT_PATH}`;
}
