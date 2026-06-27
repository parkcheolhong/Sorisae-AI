import type {
  ChatMessageCreatedEvent,
  ChatMembersAddResponse,
  ChatMessageItem,
  ChatMessageListResponse,
  ChatRoomDetail,
  ChatRoomListResponse,
  ChatRoomSocketEvent,
  ChatRoomSummary,
} from './types';

async function parseApiResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('로그인 세션이 만료되었습니다. 로그아웃 후 다시 로그인해 주세요.');
    }
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      throw new Error('서버가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.');
    }
    const message = typeof payload.detail === 'string' ? payload.detail : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

function buildAuthHeaders(token: string, includeJson = false) {
  return {
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
    Authorization: `Bearer ${token}`,
  };
}

function buildChatRoomWsUrl(apiBaseUrl: string, roomId: string, token: string): string {
  const wsBaseUrl = apiBaseUrl.replace(/^http/i, 'ws');
  const encodedRoomId = encodeURIComponent(roomId);
  const encodedToken = encodeURIComponent(token);
  return `${wsBaseUrl}/api/mobile/chat/rooms/${encodedRoomId}/ws?token=${encodedToken}`;
}

const CHAT_SOCKET_KEEPALIVE_MS = 20000;

function isChatRoomSocketEvent(payload: unknown): payload is ChatRoomSocketEvent {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  const candidate = payload as Partial<ChatRoomSocketEvent>;
  return candidate.type === 'chat_room_ready' || candidate.type === 'message_created';
}

export function connectChatRoomEvents(
  apiBaseUrl: string,
  token: string,
  roomId: string,
  onMessageCreated: (event: ChatMessageCreatedEvent) => void,
  onError?: (message: string) => void,
  onReady?: () => void,
): () => void {
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let activeSocket: WebSocket | null = null;
  let keepaliveTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectAttempt = 0;
  let closedManually = false;

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const stopKeepalive = () => {
    if (keepaliveTimer) {
      clearInterval(keepaliveTimer);
      keepaliveTimer = null;
    }
  };

  const startKeepalive = (socket: WebSocket) => {
    stopKeepalive();
    keepaliveTimer = setInterval(() => {
      if (closedManually || activeSocket !== socket) {
        stopKeepalive();
        return;
      }
      try {
        socket.send(JSON.stringify({ type: 'ping', room_id: roomId }));
      } catch {
        stopKeepalive();
      }
    }, CHAT_SOCKET_KEEPALIVE_MS);
  };

  const scheduleReconnect = () => {
    if (closedManually || reconnectTimer) {
      return;
    }
    const delayMs = Math.min(1000 * 2 ** reconnectAttempt, 5000);
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      openSocket();
    }, delayMs);
  };

  const openSocket = () => {
    if (closedManually) {
      return;
    }

    const socket = new WebSocket(buildChatRoomWsUrl(apiBaseUrl, roomId, token));
    activeSocket = socket;

    socket.onopen = () => {
      reconnectAttempt = 0;
      startKeepalive(socket);
      onReady?.();
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string);
        if (!isChatRoomSocketEvent(payload)) {
          return;
        }
        if (payload.type === 'message_created') {
          onMessageCreated(payload);
        }
      } catch {
        onError?.('실시간 채팅 이벤트를 해석하지 못했습니다.');
      }
    };

    socket.onerror = () => {
      // React Native WebSocket will usually raise onclose next; reconnect is scheduled there.
    };

    socket.onclose = () => {
      if (activeSocket === socket) {
        activeSocket = null;
      }
      stopKeepalive();
      if (closedManually) {
        return;
      }
      onError?.('채팅 실시간 연결이 끊겼습니다. 자동 복구를 시도합니다.');
      scheduleReconnect();
    };
  };

  openSocket();

  return () => {
    closedManually = true;
    clearReconnectTimer();
    stopKeepalive();
    activeSocket?.close();
    activeSocket = null;
  };
}

export async function listChatRooms(apiBaseUrl: string, token: string): Promise<ChatRoomSummary[]> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms`, {
    headers: buildAuthHeaders(token),
  });
  const payload = await parseApiResponse<ChatRoomListResponse>(response);
  return payload.items;
}

export async function ensureSelfChatRoom(apiBaseUrl: string, token: string): Promise<ChatRoomSummary> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/self`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({}),
  });
  return parseApiResponse<ChatRoomSummary>(response);
}

export async function createDirectChatRoom(apiBaseUrl: string, token: string, friendUserId: number): Promise<ChatRoomSummary> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/direct`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({ friend_user_id: friendUserId }),
  });
  return parseApiResponse<ChatRoomSummary>(response);
}

export async function createGroupChatRoom(
  apiBaseUrl: string,
  token: string,
  payload: {
    title: string;
    memberUserIds: number[];
    defaultSourceLang?: string | null;
    defaultTargetLang?: string | null;
    translationMode?: string;
    allowMemberInvites?: boolean;
    memberLimit?: number;
  },
): Promise<ChatRoomSummary> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/group`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({
      title: payload.title,
      member_user_ids: payload.memberUserIds,
      default_source_lang: payload.defaultSourceLang ?? null,
      default_target_lang: payload.defaultTargetLang ?? null,
      translation_mode: payload.translationMode ?? 'assist',
      allow_member_invites: payload.allowMemberInvites ?? false,
      member_limit: payload.memberLimit ?? 10,
    }),
  });
  return parseApiResponse<ChatRoomSummary>(response);
}

export async function getChatRoomDetail(apiBaseUrl: string, token: string, roomId: string): Promise<ChatRoomDetail> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}`, {
    headers: buildAuthHeaders(token),
  });
  return parseApiResponse<ChatRoomDetail>(response);
}

export async function updateChatRoomSettings(
  apiBaseUrl: string,
  token: string,
  roomId: string,
  payload: {
    allowMemberInvites?: boolean;
    memberLimit?: number;
  },
): Promise<ChatRoomDetail> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}/settings`, {
    method: 'PATCH',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({
      allow_member_invites: payload.allowMemberInvites,
      member_limit: payload.memberLimit,
    }),
  });
  return parseApiResponse<ChatRoomDetail>(response);
}

export async function listChatRoomMessages(
  apiBaseUrl: string,
  token: string,
  roomId: string,
  options?: { limit?: number },
): Promise<ChatMessageItem[]> {
  const limit = options?.limit;
  const query = typeof limit === 'number' && Number.isFinite(limit)
    ? `?limit=${encodeURIComponent(String(Math.max(1, Math.min(200, Math.floor(limit)))))}`
    : '';
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}/messages${query}`, {
    headers: buildAuthHeaders(token),
  });
  const payload = await parseApiResponse<ChatMessageListResponse>(response);
  return payload.items;
}

export async function sendChatRoomMessage(
  apiBaseUrl: string,
  token: string,
  roomId: string,
  payload: {
    messageType?: string;
    body: string;
    translatedBody?: string | null;
    sourceLang?: string | null;
    targetLang?: string | null;
    requestTranslation?: boolean;
  },
): Promise<ChatMessageItem> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}/messages`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({
      message_type: payload.messageType ?? 'text',
      body: payload.body,
      translated_body: payload.translatedBody ?? null,
      source_lang: payload.sourceLang ?? null,
      target_lang: payload.targetLang ?? null,
      request_translation: payload.requestTranslation ?? true,
    }),
  });
  return parseApiResponse<ChatMessageItem>(response);
}

export async function markChatRoomRead(apiBaseUrl: string, token: string, roomId: string, lastReadMessageId?: string | null): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}/read`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({ last_read_message_id: lastReadMessageId ?? null }),
  });
  await parseApiResponse<{ status: string }>(response);
}

export async function addChatRoomMembers(
  apiBaseUrl: string,
  token: string,
  roomId: string,
  memberUserIds: number[],
): Promise<ChatMembersAddResponse> {
  const response = await fetch(`${apiBaseUrl}/api/mobile/chat/rooms/${encodeURIComponent(roomId)}/members`, {
    method: 'POST',
    headers: buildAuthHeaders(token, true),
    body: JSON.stringify({ member_user_ids: memberUserIds }),
  });
  return parseApiResponse<ChatMembersAddResponse>(response);
}