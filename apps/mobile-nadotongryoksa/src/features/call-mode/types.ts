export type CallMode = 'pstn_assist' | 'voip_full_auto';

export const DEFAULT_CALL_MODE: CallMode = 'pstn_assist';

export function getCallModeLabel(mode: CallMode): string {
    return mode === 'voip_full_auto' ? 'VoIP 완전자동' : '일반통화 보조';
}
