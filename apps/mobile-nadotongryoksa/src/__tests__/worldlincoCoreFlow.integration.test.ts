import { beforeEach, describe, expect, it, jest } from '@jest/globals';

jest.mock('expo-constants', () => ({
  expoConfig: {
    extra: {
      apiBaseUrl: 'http://127.0.0.1:8000',
    },
  },
}));

jest.mock('react-native', () => ({
  Platform: { OS: 'android' },
}));

import {
  callLoginApi,
  fetchVoipCallResumeSnapshot,
  requestEndVoipCall,
} from '../app/appApiClient';
import { sendChatRoomMessage } from '../features/chat/api';
import { translateText } from '../api/translate';

describe('worldlinco core flow integration', () => {
  let fetchMock: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    jest.clearAllMocks();
    fetchMock = jest.fn<typeof fetch>();
    global.fetch = fetchMock;
  });

  it('automates login -> translate -> voip snapshot/end -> chat send minimal flow', async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'token-abc' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ translated: '안녕하세요', engine: 'nado' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          call_id: 'call-1',
          signaling_server: 'wss://signal.example.com',
          turn_servers: [],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ended' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          message_id: 'msg-1',
          room_id: 'room-1',
          sender_label: 'qa-user',
          message_type: 'text',
          body: '안녕하세요',
          translated_body: null,
          created_at: '2026-08-13T00:00:00.000Z',
          mine: true,
        }),
      } as Response);

    const token = await callLoginApi('qa@worldlinco.dev', 'pw1234');
    expect(token).toBe('token-abc');

    const translated = await translateText('hello', 'en', 'ko', 5000);
    expect(translated.translated).toBe('안녕하세요');

    const voip = await fetchVoipCallResumeSnapshot('https://api.example.com', token, 'call-1');
    expect(voip?.call_id).toBe('call-1');

    await requestEndVoipCall('https://api.example.com', token, 'call-1', 'good');

    const chatMessage = await sendChatRoomMessage('https://api.example.com', token, 'room-1', {
      body: translated.translated,
      sourceLang: 'en',
      targetLang: 'ko',
      requestTranslation: false,
    });
    expect(chatMessage.message_id).toBe('msg-1');

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://127.0.0.1:8000/api/auth/login',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://127.0.0.1:8000/api/llm/translate',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      'https://api.example.com/api/v1/voip/calls/active-current?last_call_id=call-1',
      expect.objectContaining({ headers: { Authorization: 'Bearer token-abc' } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      'https://api.example.com/api/v1/voip/calls/call-1/end',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      'https://api.example.com/api/mobile/chat/rooms/room-1/messages',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
