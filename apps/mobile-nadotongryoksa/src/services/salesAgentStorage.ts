import AsyncStorage from '@react-native-async-storage/async-storage';

const PENDING_SALES_AGENT_CODE_KEY = 'worldlinco_pending_sales_agent_code_v1';

export async function savePendingSalesAgentCode(code: string): Promise<void> {
    const normalized = String(code || '').trim().toUpperCase();
    if (!normalized.startsWith('WS')) {
        return;
    }
    await AsyncStorage.setItem(PENDING_SALES_AGENT_CODE_KEY, normalized);
}

export async function getPendingSalesAgentCode(): Promise<string | null> {
    const raw = await AsyncStorage.getItem(PENDING_SALES_AGENT_CODE_KEY);
    const normalized = String(raw || '').trim().toUpperCase();
    return normalized.startsWith('WS') ? normalized : null;
}

export async function consumePendingSalesAgentCode(): Promise<string | null> {
    const code = await getPendingSalesAgentCode();
    if (code) {
        await AsyncStorage.removeItem(PENDING_SALES_AGENT_CODE_KEY);
    }
    return code;
}
