/**
 * [기능 분리 Phase5.6g] VoIP 식별자/URL/TURN 순수 유틸 SSOT.
 *
 * App.tsx 인라인의 보이스ID/토픽 생성, WebSocket URL 빌더, TURN 서버 기본값/정규화를 분리한다.
 * 모두 순수(부수효과 없음) — 단위 테스트로 회귀 가드.
 */
import type { TURNServer } from '../../services/voipCallClient';

/** 사용자 ID → 보이스 ID(6자리 zero-pad). */
export const buildVoiceId = (userId: number): string => `nado-${String(userId).padStart(6, '0')}`;

/** 보이스 ID → VoIP 토픽(영숫자 외 _ 치환, 소문자). */
export const buildVoipTopic = (voiceId: string): string =>
    `worldlingo_voip_${voiceId.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;

/** http(s) API base + path + query → ws(s) WebSocket URL. */
export const buildVoipWebSocketUrl = (apiBase: string, path: string, query: Record<string, string> = {}): string => {
    const normalizedBase = apiBase.replace(/\/$/, '');
    const wsBase = normalizedBase.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:');
    const searchParams = new URLSearchParams(query);
    const queryString = searchParams.toString();
    return `${wsBase}${path}${queryString ? `?${queryString}` : ''}`;
};

/** STUN-only 기본 TURN 서버 목록(서버 미제공 시 폴백). */
export function getDefaultVoipTurnServers(): TURNServer[] {
    return [
        { urls: ['stun:stun.l.google.com:19302'] },
        { urls: ['stun:stun1.l.google.com:19302'] },
        { urls: ['stun:stun.cloudflare.com:3478'] },
    ];
}

/** 임의 입력을 유효한 TURNServer[] 로 정규화(유효 항목 없으면 기본값). */
export function normalizeTurnServers(rawValue: unknown): TURNServer[] {
    if (!Array.isArray(rawValue)) {
        return getDefaultVoipTurnServers();
    }
    const normalized = rawValue
        .map((entry): TURNServer | null => {
            if (!entry || typeof entry !== 'object') {
                return null;
            }
            const candidate = entry as { urls?: unknown; username?: unknown; credential?: unknown };
            const urls = Array.isArray(candidate.urls)
                ? candidate.urls.filter((url): url is string => typeof url === 'string' && Boolean(url.trim()))
                : [];
            if (!urls.length) {
                return null;
            }
            return {
                urls,
                username: typeof candidate.username === 'string' ? candidate.username : undefined,
                credential: typeof candidate.credential === 'string' ? candidate.credential : undefined,
            };
        })
        .filter((entry): entry is TURNServer => entry !== null);

    return normalized.length ? normalized : getDefaultVoipTurnServers();
}
