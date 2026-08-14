// App.tsx 에서 분리한 딥링크 URL 파서(순수 함수, 런타임 상태 비의존).
import type { AppEntryDeepLinkTarget } from './appTypes';
import { parseSectionRailKey } from '../features/navigation/sectionRegistry';
import type { CallInitResponse } from '../services/voipCallClient';
import { getDefaultVoipTurnServers, normalizeTurnServers } from '../features/voip/voipSignaling';
import {
    VOIP_INCOMING_LINK_SCHEMES,
    VOIP_INCOMING_LINK_PATH,
    APP_ENTRY_RAIL_LINK_PATH,
    APP_ENTRY_CHAT_LINK_PATH,
    APP_ENTRY_VOIP_LINK_PATH,
    APP_ENTRY_INVITE_LINK_PATH,
    APP_ENTRY_SALES_LINK_PATH,
    APP_ENTRY_AUTH_LINK_PATH,
} from './appConstants';

export function parseSalesAgentFromUrl(url: string): string | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
            if (resolvedPath === APP_ENTRY_SALES_LINK_PATH) {
                const ref = String(parsed.searchParams.get('ref') || '').trim().toUpperCase();
                return ref.startsWith('WS') ? ref : null;
            }
        }
        const pathMatch = parsed.pathname.match(/\/api\/marketplace\/worldlinco\/sales\/invite\/([A-Za-z0-9]+)/i);
        if (pathMatch?.[1]) {
            const code = pathMatch[1].toUpperCase();
            return code.startsWith('WS') ? code : null;
        }
        return null;
    } catch {
        return null;
    }
}

export function parseReferralFromUrl(url: string): string | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
            if (resolvedPath === APP_ENTRY_INVITE_LINK_PATH) {
                const ref = String(parsed.searchParams.get('ref') || '').trim().toUpperCase();
                return ref.startsWith('WL') ? ref : null;
            }
        }
        const pathMatch = parsed.pathname.match(/\/api\/marketplace\/worldlinco\/invite\/([A-Za-z0-9]+)/i);
        if (pathMatch?.[1]) {
            const code = pathMatch[1].toUpperCase();
            return code.startsWith('WL') ? code : null;
        }
        const refParam = String(parsed.searchParams.get('ref') || '').trim().toUpperCase();
        return refParam.startsWith('WL') ? refParam : null;
    } catch {
        return null;
    }
}

export function parseAppEntryDeepLink(url: string): AppEntryDeepLinkTarget | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (!VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            return null;
        }

        const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
        if (resolvedPath === APP_ENTRY_SALES_LINK_PATH) {
            const salesAgentCode = String(parsed.searchParams.get('ref') || '').trim().toUpperCase();
            return salesAgentCode.startsWith('WS') ? { type: 'sales', salesAgentCode } : null;
        }
        if (resolvedPath === APP_ENTRY_INVITE_LINK_PATH) {
            const referralCode = String(parsed.searchParams.get('ref') || '').trim().toUpperCase();
            return referralCode.startsWith('WL') ? { type: 'invite', referralCode } : null;
        }

        if (resolvedPath === APP_ENTRY_RAIL_LINK_PATH) {
            const section = parseSectionRailKey(parsed.searchParams.get('section'));
            return section ? { type: 'rail', section } : null;
        }

        if (resolvedPath === APP_ENTRY_CHAT_LINK_PATH) {
            const roomId = String(parsed.searchParams.get('room_id') || '').trim();
            return roomId ? { type: 'chat', roomId } : null;
        }

        if (resolvedPath === APP_ENTRY_AUTH_LINK_PATH) {
            const accessToken = String(parsed.searchParams.get('access_token') || parsed.searchParams.get('token') || '').trim();
            if (!accessToken) {
                return null;
            }
            const userIdRaw = String(parsed.searchParams.get('user_id') || parsed.searchParams.get('uid') || '').trim();
            const parsedUserId = userIdRaw ? Number(userIdRaw) : NaN;
            const expiresInRaw = String(parsed.searchParams.get('expires_in') || '').trim();
            const parsedExpiresIn = expiresInRaw ? Number(expiresInRaw) : NaN;
            return {
                type: 'auth',
                provider: String(parsed.searchParams.get('provider') || '').trim().toLowerCase() || undefined,
                accessToken,
                refreshToken: String(parsed.searchParams.get('refresh_token') || '').trim() || undefined,
                idToken: String(parsed.searchParams.get('id_token') || '').trim() || undefined,
                expiresInSec: Number.isFinite(parsedExpiresIn) ? parsedExpiresIn : undefined,
                email: String(parsed.searchParams.get('email') || '').trim() || undefined,
                userId: Number.isFinite(parsedUserId) ? parsedUserId : undefined,
                username: String(parsed.searchParams.get('username') || '').trim() || undefined,
                displayName: String(parsed.searchParams.get('display_name') || parsed.searchParams.get('name') || '').trim() || undefined,
            };
        }

        if (resolvedPath !== APP_ENTRY_VOIP_LINK_PATH) {
            return null;
        }

        const action = String(parsed.searchParams.get('action') || 'open').trim().toLowerCase();
        const callId = String(parsed.searchParams.get('call_id') || '').trim() || undefined;
        const calleeVoiceId = String(parsed.searchParams.get('callee_voice_id') || '').trim() || undefined;
        const preferredLanguage = String(parsed.searchParams.get('preferred_language') || parsed.searchParams.get('source_lang') || '').trim().toLowerCase() || undefined;
        const calleePreferredLanguage = String(parsed.searchParams.get('callee_preferred_language') || parsed.searchParams.get('target_lang') || '').trim().toLowerCase() || undefined;
        const forceRetry = String(parsed.searchParams.get('force') || '').trim() === '1'
            || String(parsed.searchParams.get('retry') || '').trim() === '1';
        if (action === 'incoming') {
            return callId ? { type: 'voip', action: 'incoming', callId } : null;
        }
        if (action === 'validation') {
            return { type: 'voip', action: 'validation', calleeVoiceId, forceRetry, preferredLanguage, calleePreferredLanguage };
        }
        if (action === 'demo') {
            return { type: 'voip', action: 'demo', forceRetry, preferredLanguage, calleePreferredLanguage };
        }
        return { type: 'voip', action: 'open', calleeVoiceId, forceRetry, preferredLanguage, calleePreferredLanguage };
    } catch {
        return null;
    }
}

export function parseIncomingVoipDeepLink(url: string): (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (!VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            return null;
        }

        const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
        if (resolvedPath !== VOIP_INCOMING_LINK_PATH) {
            return null;
        }

        const callId = parsed.searchParams.get('call_id') || '';
        const signalingServer = parsed.searchParams.get('signaling_server') || '';
        if (!callId || !signalingServer) {
            return null;
        }

        const explicitParticipantRole = parsed.searchParams.get('participant_role');
        let inferredParticipantRole: 'caller' | 'callee' = explicitParticipantRole === 'callee' ? 'callee' : 'caller';
        if (explicitParticipantRole !== 'callee') {
            try {
                const signalingUrl = new URL(signalingServer);
                inferredParticipantRole = signalingUrl.searchParams.get('role') === 'callee' ? 'callee' : 'caller';
            } catch {
                inferredParticipantRole = 'caller';
            }
        }

        let turnServers: unknown = getDefaultVoipTurnServers();
        const encodedTurnServers = parsed.searchParams.get('turn_servers');
        if (encodedTurnServers) {
            try {
                turnServers = JSON.parse(encodedTurnServers);
            } catch {
                turnServers = getDefaultVoipTurnServers();
            }
        }

        return {
            call_id: callId,
            signaling_server: signalingServer,
            turn_servers: normalizeTurnServers(turnServers),
            call_route: parsed.searchParams.get('call_route') || 'app_webrtc',
            user_message: parsed.searchParams.get('user_message') || undefined,
            callee_app_online: parsed.searchParams.get('callee_app_online') === 'true',
            caller_voice_id: parsed.searchParams.get('caller_voice_id') || undefined,
            callee_voice_id: parsed.searchParams.get('callee_voice_id') || undefined,
            participant_role: inferredParticipantRole,
            display_label: parsed.searchParams.get('display_label') || undefined,
            display_language: parsed.searchParams.get('display_language') || undefined,
            display_country_code: parsed.searchParams.get('display_country_code') || undefined,
            status: parsed.searchParams.get('status') || undefined,
            caller_label: parsed.searchParams.get('caller_label') || undefined,
        };
    } catch {
        return null;
    }
}
