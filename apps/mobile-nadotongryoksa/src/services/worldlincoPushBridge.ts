import type { CallInitResponse } from './voipCallClient';

export type WorldlincoChatPushPayload = {
    type: 'chat_message';
    room_id: string;
    message_id?: string;
    sender_label?: string;
    body_preview?: string;
    alert_phrase?: string;
};

const DEFAULT_STUN_SERVERS = [
    { urls: ['stun:stun.l.google.com:19302'] },
];

export function parseChatMessageFcmData(
    data: Record<string, unknown> | undefined | null,
): WorldlincoChatPushPayload | null {
    if (!data || String(data.type ?? '') !== 'chat_message') {
        return null;
    }
    const roomId = String(data.room_id ?? '').trim();
    if (!roomId) {
        return null;
    }
    return {
        type: 'chat_message',
        room_id: roomId,
        message_id: data.message_id ? String(data.message_id) : undefined,
        sender_label: data.sender_label ? String(data.sender_label) : undefined,
        body_preview: data.body_preview ? String(data.body_preview) : undefined,
        alert_phrase: data.alert_phrase ? String(data.alert_phrase) : '친구야~',
    };
}

export function shouldPersistWorldlincoFcmData(
    data: Record<string, unknown> | undefined | null,
): boolean {
    if (!data) {
        return false;
    }
    const type = String(data.type ?? '');
    if (type === 'incoming_call') {
        return Boolean(String(data.call_id ?? '').trim());
    }
    if (type === 'chat_message') {
        return Boolean(String(data.room_id ?? '').trim());
    }
    return false;
}

export function parseWorldlincoFcmData(
    data: Record<string, unknown> | undefined | null,
): WorldlincoChatPushPayload | null {
    return parseChatMessageFcmData(data);
}
