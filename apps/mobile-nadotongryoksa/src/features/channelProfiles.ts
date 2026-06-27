// WorldLinco 채널 프로파일 SSOT.
// 성격이 다른 서비스를 채널별 프로파일로 분리한다(V.2 Delivery 채널 경계의 씨앗).
//   - face : 여행 대면 통역 — 자동 언어 감지(bilingual) + GPS 지역 힌트
//   - voip : VoIP 통역 통화 — 지정 언어 고정(designated, 언어 락)
//   - chat : 채팅 번역      — 지정 언어 고정(designated, 언어 락)
//
// 참고 설계: docs/worldlinco-v2/SERVICE_SEPARATION_DESIGN.md

export type VoiceChannel = 'face' | 'voip' | 'chat';

// 백엔드 voice-translate payload의 mode 필드와 1:1 대응한다.
export type VoiceChannelMode = 'bilingual' | 'designated';

export interface ChannelProfile {
  readonly channel: VoiceChannel;
  readonly mode: VoiceChannelMode;
  // 자동 언어 감지 사용 여부(대면 통역만 true).
  readonly bilingual: boolean;
  // GPS 지역 힌트 전달 여부(대면 통역만 true).
  readonly useGpsRegionHint: boolean;
  // STT를 지정 언어로 고정할지 여부(VoIP/채팅 true).
  readonly lockLanguage: boolean;
}

export const CHANNEL_PROFILES: Record<VoiceChannel, ChannelProfile> = {
  face: {
    channel: 'face',
    mode: 'bilingual',
    bilingual: true,
    useGpsRegionHint: true,
    lockLanguage: false,
  },
  voip: {
    channel: 'voip',
    mode: 'designated',
    bilingual: false,
    useGpsRegionHint: false,
    lockLanguage: true,
  },
  chat: {
    channel: 'chat',
    mode: 'designated',
    bilingual: false,
    useGpsRegionHint: false,
    lockLanguage: true,
  },
};

export function getChannelProfile(channel: VoiceChannel): ChannelProfile {
  return CHANNEL_PROFILES[channel];
}
