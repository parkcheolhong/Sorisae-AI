import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  AppState,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import * as Speech from 'expo-speech';

import { getFriends } from '../../../api/friends';
import { getVoIPToneService } from '../../../services/voipToneService';
import { announceServerVoice } from '../../../utils/voiceAnnounce';
import {
  sanitizeChatTextForSpeech,
  loadChatReadAloudEnabled,
  shouldReadAloudIncoming,
  subscribeChatReadAloudEnabled,
} from '../../sorisae/companionChatReadAloud';
import { useGlobalSettings } from '../../settings/globalSettings';
import type { Friend } from '../../friends/types';
import { addChatRoomMembers, connectChatRoomEvents, getChatRoomDetail, listChatRoomMessages, markChatRoomRead, sendChatRoomMessage, updateChatRoomSettings } from '../api';
import { resolveChatNarratorLang } from '../chatNarratorLanguage';
import { pickReadAloudContent } from '../chatReadAloud';
import {
  DESIGNATED_LANGUAGE_MISMATCH_MESSAGE,
  textMatchesDesignatedLanguage,
} from '../../translation/designatedLanguage';
import { mergeTranscriptIntoDraft } from '../chatVoiceInput';
import { MicWaveform } from '../MicWaveform';
import { useChatVoiceInput } from '../useChatVoiceInput';
import { shareChatInvite } from '../../sns-share/snsShare';
import { getFeatureUiText } from '../../i18n/featureUiCatalog';
import { BidirectionalLanguagePairBadge } from '../../i18n/BidirectionalLanguagePairBadge';
import { formatFlagPrefixedName, resolveUserCountryFlag } from '../../i18n/userDisplayIdentity';
import { getUiLang } from '../../i18n/uiI18n';
import { resolveUserOutputLang } from '../../i18n/userLanguagePolicy';
import type { LangCode } from '../../language/languageCatalog';
import type { ChatMessageItem, ChatRoomDetail, ChatRoomSummary } from '../types';

const GROUP_MEMBER_LIMIT_OPTIONS = [3, 5, 10] as const;

function buildGroupInviteStatusLabel(detail: ChatRoomDetail, room: ChatRoomSummary, options?: { currentPrefix?: boolean }): string {
  const memberLimit = detail.member_limit ?? room.member_limit ?? 10;
  const memberCount = detail.members.length;

  if (detail.allow_member_invites && detail.can_invite_members === false && memberCount >= memberLimit) {
    return options?.currentPrefix
      ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteAllowedFull')
      : getFeatureUiText('chat.groupFullNoInvite');
  }

  if (detail.allow_member_invites) {
    return options?.currentPrefix ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteAllowed') : getFeatureUiText('chat.groupInviteAllowed');
  }

  return options?.currentPrefix ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteOwnerOnly') : getFeatureUiText('chat.groupInviteOwnerOnly');
}

function buildRoomSubtitle(detail: ChatRoomDetail | null, room: ChatRoomSummary): string {
  if (!detail) {
    return room.room_type;
  }

  if (detail.room_type !== 'direct') {
    const memberLimit = detail.member_limit ?? room.member_limit ?? 10;
    return getFeatureUiText('chat.groupSubtitle', { members: detail.members.length, limit: memberLimit, mode: detail.translation_mode, invite: buildGroupInviteStatusLabel(detail, room) });
  }

  const preferredLanguage = detail.counterpart?.preferred_language?.trim();
  return preferredLanguage
    ? getFeatureUiText('chat.directSubtitleAuto')
    : getFeatureUiText('chat.directSubtitle');
}

function normalizeLanguageCode(value?: string | null): string | null {
  const normalized = value?.trim().toLowerCase();
  return normalized || null;
}

// [목업 #4] 언어 선택 바 표시용 국기/라벨.
function chatLangChip(code?: string | null): { flag: string; label: string } {
  const c = (code || '').trim().toLowerCase();
  const map: Record<string, { flag: string; label: string }> = {
    ko: { flag: '🇰🇷', label: '한국어' }, en: { flag: '🇺🇸', label: 'English' },
    ja: { flag: '🇯🇵', label: '日本語' }, zh: { flag: '🇨🇳', label: '中文' },
    'zh-cn': { flag: '🇨🇳', label: '中文' }, 'zh-tw': { flag: '🇹🇼', label: '繁體' }, 'zh-hk': { flag: '🇭🇰', label: '粵語' },
    es: { flag: '🇪🇸', label: '스페인어' }, fr: { flag: '🇫🇷', label: 'Français' },
    de: { flag: '🇩🇪', label: 'Deutsch' }, it: { flag: '🇮🇹', label: 'Italiano' },
    pt: { flag: '🇵🇹', label: 'Português' }, ru: { flag: '🇷🇺', label: 'Русский' },
    ar: { flag: '🇸🇦', label: 'العربية' }, hi: { flag: '🇮🇳', label: 'हिन्दी' },
    th: { flag: '🇹🇭', label: 'ไทย' }, vi: { flag: '🇻🇳', label: 'Tiếng Việt' },
    id: { flag: '🇮🇩', label: 'Indonesia' }, tr: { flag: '🇹🇷', label: 'Türkçe' },
  };
  return map[c] ?? { flag: '🌐', label: code ? code.toUpperCase() : getFeatureUiText('chat.langAuto') };
}

// 서버 timestamp 는 naive UTC 를 'Z' 로 직렬화하지만, 캐시/레거시/WS 경로에서
// 타임존 표기가 없는 값이 올 수 있으므로 방어적으로 UTC(Z)로 간주한다.
// (타임존 누락 시 JS new Date 가 로컬시간으로 파싱 → KST ~9h 오프셋/일부 기기 Invalid Date)
export function normalizeIsoUtc(iso: string): string {
  const trimmed = iso.trim();
  if (!trimmed) return trimmed;
  // 이미 Z 또는 ±hh:mm 오프셋이 있으면 그대로 사용
  if (/[zZ]$/.test(trimmed) || /[+-]\d{2}:?\d{2}$/.test(trimmed)) return trimmed;
  // 'YYYY-MM-DDTHH:MM:SS(.ffffff)?' 형태면 UTC 로 간주
  return trimmed + 'Z';
}

// [목업 #4] 채팅 시각(오전/오후 h:mm) 포맷.
function formatChatClock(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(normalizeIsoUtc(iso));
  if (Number.isNaN(d.getTime())) return '';
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  const ampm = h < 12 ? getFeatureUiText('chat.am') : getFeatureUiText('chat.pm');
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${ampm} ${h12}:${m}`;
}

function resolveFixedMessageLanguages(detail: ChatRoomDetail | null, room: ChatRoomSummary, userId: number): { sourceLang: string | null; targetLang: string | null } {
  if (!detail) {
    return {
      sourceLang: null,
      targetLang: normalizeLanguageCode(room.counterpart?.preferred_language),
    };
  }

  const me = detail.members.find((member) => member.user_id === userId);
  const counterpartMember = detail.members.find((member) => member.user_id !== userId);
  const sourceLang = normalizeLanguageCode(me?.preferred_language) || normalizeLanguageCode(detail.default_source_lang);
  const targetLang = normalizeLanguageCode(detail.counterpart?.preferred_language)
    || normalizeLanguageCode(counterpartMember?.preferred_language)
    || normalizeLanguageCode(detail.default_target_lang);

  return { sourceLang, targetLang };
}

function isGroupRoom(detail: ChatRoomDetail | null, room: ChatRoomSummary): boolean {
  return (detail?.room_type || room.room_type) === 'group' && room.title !== '번역 보관함';
}

function getEffectiveTranslatedBody(message: ChatMessageItem): string | null {
  return message.viewer_translation?.translated_body?.trim() || message.translated_body?.trim() || null;
}

function getEffectiveTranslationStatus(message: ChatMessageItem): string | null {
  return message.viewer_translation?.translation_status || message.translation_status || null;
}

function getDeliverySummaryLabel(message: ChatMessageItem): string | null {
  const summary = message.delivery_summary;
  if (!summary || summary.recipient_count <= 0) {
    return null;
  }

  if (summary.status === 'partial_failed') {
    return getFeatureUiText('chat.deliveryPartial', { done: summary.done_count, total: summary.recipient_count, failed: summary.failed_count });
  }
  if (summary.status === 'failed') {
    return getFeatureUiText('chat.deliveryFailed', { failed: summary.failed_count, total: summary.recipient_count });
  }
  if (summary.status === 'pending') {
    return getFeatureUiText('chat.deliveryPending', { pending: summary.pending_count, total: summary.recipient_count });
  }
  return getFeatureUiText('chat.deliveryDone', { done: summary.done_count, total: summary.recipient_count });
}

function upsertMessageItem(messages: ChatMessageItem[], incoming: ChatMessageItem): ChatMessageItem[] {
  const existingIndex = messages.findIndex((message) => message.message_id === incoming.message_id);
  if (existingIndex >= 0) {
    const nextMessages = [...messages];
    nextMessages[existingIndex] = incoming;
    return nextMessages;
  }
  return [...messages, incoming];
}

function buildChatMessageSelector(message: ChatMessageItem): string {
  return `worldlinco-chat-message-${message.message_id}`;
}

function buildChatMessageAccessibilityLabel(message: ChatMessageItem): string {
  const preview = message.body.replace(/\s+/g, ' ').trim().slice(0, 80);
  return `worldlinco-chat-message-${message.message_id} ${message.sender_label} ${preview}`.trim();
}

interface Props {
  apiBaseUrl: string;
  token: string;
  userId: number;
  room: ChatRoomSummary;
  visible?: boolean;
  refreshKey?: number;
  initialDraft?: string;
  userCountryCode?: string;
  userPreferredLanguage?: string;
  userDisplayName?: string;
  onBack: () => void;
  onRoomChanged?: () => void;
}

export function ChatRoomScreen({
  apiBaseUrl,
  token,
  userId,
  room,
  visible = true,
  refreshKey = 0,
  initialDraft = '',
  userCountryCode = '',
  userPreferredLanguage = '',
  userDisplayName = '',
  onBack,
  onRoomChanged,
}: Props) {
  const [detail, setDetail] = useState<ChatRoomDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [draft, setDraft] = useState(initialDraft);
  // [Phase5.11] 채팅 입력 마이크/텍스트 겸용 — 음성 인식 결과를 입력칸에 합쳐 채운다(확인 후 전송).
  const handleVoiceTranscript = useCallback((text: string) => {
    setDraft((prev) => mergeTranscriptIntoDraft(prev, text));
  }, []);
  // 음성 STT 원문은 말하는 주체(=로컬 사용자)의 지정 언어가 source 다. 상대 언어는 bilingual 보조용.
  const voiceLangs = resolveFixedMessageLanguages(detail, room, userId);
  const viewerOutputLang = resolveUserOutputLang(
    detail?.members.find((m) => m.user_id === userId)?.preferred_language,
    getUiLang() as LangCode,
  );
  const chatNarratorLang = useMemo(() => resolveChatNarratorLang({
    countryCode: userCountryCode,
    preferredLanguage: userPreferredLanguage || detail?.members.find((m) => m.user_id === userId)?.preferred_language,
    viewerOutputLang,
  }), [detail, userCountryCode, userPreferredLanguage, userId, viewerOutputLang]);
  const myFlag = resolveUserCountryFlag(userCountryCode, userPreferredLanguage || detail?.members.find((m) => m.user_id === userId)?.preferred_language);
  const myDisplayLabel = formatFlagPrefixedName(myFlag, userDisplayName || getFeatureUiText('chat.me'));

  const resolveMemberFlag = useCallback((memberUserId: number, preferredLanguage?: string | null) => {
    if (memberUserId === userId) {
      return myFlag;
    }
    return resolveUserCountryFlag(null, preferredLanguage);
  }, [myFlag, userId]);

  const resolveSenderDisplayLabel = useCallback((message: ChatMessageItem, isMine: boolean) => {
    const directRoom = (detail?.room_type || room.room_type) === 'direct';
    if (isMine) {
      return myDisplayLabel;
    }
    if (directRoom) {
      const peerLang = detail?.counterpart?.preferred_language
        || detail?.members.find((m) => m.user_id !== userId)?.preferred_language;
      const peerFlag = resolveUserCountryFlag(null, peerLang);
      const peerName = detail?.counterpart?.nickname || detail?.title || room.title || getFeatureUiText('chat.peer');
      return formatFlagPrefixedName(peerFlag, peerName);
    }
    const member = detail?.members.find((m) => m.nickname === message.sender_label || m.user_id === message.sender_user_id);
    const flag = resolveMemberFlag(member?.user_id ?? -1, member?.preferred_language);
    return formatFlagPrefixedName(flag, message.sender_label);
  }, [detail, myDisplayLabel, resolveMemberFlag, room.room_type, room.title, userId]);
  const { autoListen } = useGlobalSettings();
  const { status: voiceStatus, error: voiceError, toggle: toggleVoiceInput } = useChatVoiceInput(
    voiceLangs.sourceLang,
    voiceLangs.targetLang,
    handleVoiceTranscript,
    autoListen,
  );
  // [Phase5.11] SNS 연동 초대 — 카카오톡/라인/문자 등 OS 공유 시트로 채팅 초대를 보낸다.
  const handleSnsInvite = useCallback(() => {
    void shareChatInvite({ apiBase: apiBaseUrl, roomId: room.room_id });
  }, [apiBaseUrl, room.room_id]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [friends, setFriends] = useState<Friend[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteSelection, setInviteSelection] = useState<number[]>([]);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [pendingMemberLimit, setPendingMemberLimit] = useState<number>(room.member_limit ?? 10);
  const readAloudEnabledRef = useRef(false);
  useEffect(() => {
    void loadChatReadAloudEnabled().then((enabled) => {
      readAloudEnabledRef.current = enabled;
    });
    return subscribeChatReadAloudEnabled((enabled) => {
      readAloudEnabledRef.current = enabled;
    });
  }, []);
  const appStateRef = useRef(AppState.currentState);
  const hasLoadedOnceRef = useRef(false);
  const isDirectRoom = detail?.room_type === 'direct';
  const isGroupViewerRoom = isGroupRoom(detail, room);
  const headerPeerFlag = resolveUserCountryFlag(
    null,
    detail?.counterpart?.preferred_language || detail?.members.find((m) => m.user_id !== userId)?.preferred_language,
  );
  const headerTitleText = isDirectRoom
    ? formatFlagPrefixedName(headerPeerFlag, detail?.counterpart?.nickname || detail?.title || room.title)
    : (detail?.title || room.title);
  const chatPairFromLang = voiceLangs.sourceLang || userPreferredLanguage || getUiLang();
  const chatPairToLang = voiceLangs.targetLang
    || detail?.counterpart?.preferred_language
    || detail?.default_target_lang
    || room.counterpart?.preferred_language
    || chatPairFromLang;

  const renderMessageContent = useCallback((message: ChatMessageItem) => {
    const effectiveTranslatedBody = getEffectiveTranslatedBody(message);
    const effectiveTranslationStatus = getEffectiveTranslationStatus(message);

    if (message.message_type === 'system_invite') {
      return (
        <View style={styles.systemCard}>
          <Text style={styles.systemCardTitle}>{getFeatureUiText('chat.memberInviteCard')}</Text>
          <Text style={styles.systemCardBody}>{message.body}</Text>
        </View>
      );
    }

    if (message.message_type === 'system_announcement') {
      return (
        <View style={styles.systemCard}>
          <Text style={styles.systemCardTitle}>{getFeatureUiText('chat.worldlincoNotice')}</Text>
          <Text style={styles.systemCardBody}>{message.body}</Text>
        </View>
      );
    }

    if (message.message_type === 'ocr') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>{getFeatureUiText('chat.ocrTitle')}</Text>
          <Text style={styles.specialLabel}>{getFeatureUiText('chat.extractLabel')}</Text>
          <Text noI18n style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>{getFeatureUiText('chat.translationLabel')}</Text>
              <Text noI18n style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (message.message_type === 'song_translation') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>{getFeatureUiText('chat.songTitle')}</Text>
          <Text style={styles.specialLabel}>{getFeatureUiText('chat.songMemo')}</Text>
          <Text noI18n style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>{getFeatureUiText('chat.songLyrics')}</Text>
              <Text noI18n style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (message.message_type === 'translation') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>{getFeatureUiText('chat.shareTitle')}</Text>
          <Text style={styles.specialLabel}>{getFeatureUiText('chat.shareOriginal')}</Text>
          <Text noI18n style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>{getFeatureUiText('chat.shareTranslated')}</Text>
              <Text noI18n style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (isGroupViewerRoom && !message.mine) {
      return (
        <View style={styles.translatedIncomingWrap}>
          {effectiveTranslatedBody ? (
            <Text noI18n style={styles.messageBody}>{effectiveTranslatedBody}</Text>
          ) : (
            <Text noI18n style={styles.messageBody}>{message.body}</Text>
          )}
          <Text noI18n style={styles.messageOriginal}>{message.body}</Text>
          {effectiveTranslationStatus === 'failed' ? (
            <Text style={styles.messageStatusError}>{getFeatureUiText('chat.myTranslationFailed')}</Text>
          ) : null}
        </View>
      );
    }

    if (isDirectRoom && !message.mine && effectiveTranslatedBody) {
      return (
        <View style={styles.translatedIncomingWrap}>
          <Text noI18n style={styles.messageBody}>{effectiveTranslatedBody}</Text>
          <Text noI18n style={styles.messageOriginal}>{message.body}</Text>
        </View>
      );
    }

    return <Text noI18n style={styles.messageBody}>{message.body}</Text>;
  }, [isDirectRoom, isGroupViewerRoom]);

  const load = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const [nextDetail, nextMessages] = await Promise.all([
        getChatRoomDetail(apiBaseUrl, token, room.room_id),
        listChatRoomMessages(apiBaseUrl, token, room.room_id, { limit: 200 }),
      ]);
      setDetail(nextDetail);
      setMessages(nextMessages);
      hasLoadedOnceRef.current = true;
      if (silent) {
        setError('');
      }
      const latestMessage = nextMessages[nextMessages.length - 1];
      await markChatRoomRead(apiBaseUrl, token, room.room_id, latestMessage?.message_id);
    } catch (e: unknown) {
      if (!silent) {
        setError(e instanceof Error ? e.message : getFeatureUiText('chat.loadRoomFailed'));
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [apiBaseUrl, room.room_id, token]);

  useEffect(() => {
    if (!visible) {
      return;
    }
    void load();
  }, [load, refreshKey, visible]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    let cancelled = false;
    const disconnect = connectChatRoomEvents(
      apiBaseUrl,
      token,
      room.room_id,
      (event) => {
        if (cancelled || event.room_id !== room.room_id) {
          return;
        }
        // 채팅 수신음: 상대가 보낸 '새' 메시지일 때만 알림음(내 메시지/중복 이벤트는 제외).
        const isIncoming = event.message.sender_user_id != null && event.message.sender_user_id !== userId;
        setMessages((prev) => {
          const alreadySeen = prev.some((existing) => existing.message_id === event.message.message_id);
          if (isIncoming && !alreadySeen) {
            setTimeout(() => {
              try {
                getVoIPToneService().playMessageTone();
              } catch {
                // 알림음 실패는 무시(메시지 표시는 계속).
              }
            }, 0);
            // [Phase6.0] 사용자 명령(토글 ON) 시 수신 메시지를 음성으로 읽어준다.
            const { text, lang } = pickReadAloudContent(event.message, chatNarratorLang);
            if (shouldReadAloudIncoming({ enabled: readAloudEnabledRef.current, isIncoming: true, text })) {
              const speakText = sanitizeChatTextForSpeech(text);
              setTimeout(() => {
                try {
                  console.log('[CHAT_READALOUD_AUTO_TRIGGER]', JSON.stringify({ lang, userCountryCode, text_len: speakText.length }));
                  // 서버 합성(Edge neural) 우선 경로를 사용해 VoIP/Push와 톤을 일치시킨다.
                  // 실패 시 announceServerVoice 내부에서 단말 TTS로 자동 폴백한다.
                  void announceServerVoice(speakText, lang, userCountryCode);
                } catch {
                  // 낭독 실패는 무시(메시지 표시는 계속).
                }
              }, 0);
            }
          }
          return upsertMessageItem(prev, event.message);
        });
        void markChatRoomRead(apiBaseUrl, token, room.room_id, event.message.message_id);
      },
      (message) => {
        if (!cancelled) {
          setError((prev) => prev || message);
        }
      },
      () => {
        if (!cancelled) {
          setError('');
          if (hasLoadedOnceRef.current) {
            void load({ silent: true });
          }
        }
      },
    );

    return () => {
      cancelled = true;
      disconnect();
      // [Phase6.0] 방을 떠나거나 비활성화되면 진행 중인 낭독을 정지.
      try {
        Speech.stop();
      } catch {
        // 정지 실패는 무시.
      }
    };
  }, [apiBaseUrl, load, room.room_id, token, visible]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    const subscription = AppState.addEventListener('change', (nextAppState) => {
      const wasBackgrounded = /inactive|background/.test(appStateRef.current);
      appStateRef.current = nextAppState;
      if (wasBackgrounded && nextAppState === 'active' && hasLoadedOnceRef.current) {
        void load({ silent: true });
      }
    });

    return () => {
      subscription.remove();
    };
  }, [load, visible]);

  useEffect(() => {
    setDraft(initialDraft);
  }, [initialDraft, room.room_id]);

  useEffect(() => {
    if (detail?.member_limit) {
      setPendingMemberLimit(detail.member_limit);
      return;
    }
    if (room.member_limit) {
      setPendingMemberLimit(room.member_limit);
    }
  }, [detail?.member_limit, room.member_limit]);

  useEffect(() => {
    if (!visible || !inviteOpen || detail?.room_type !== 'group') {
      return;
    }
    let cancelled = false;
    const loadFriends = async () => {
      try {
        const friendPayload = await getFriends(userId, token);
        if (!cancelled) {
          setFriends(friendPayload.friends.filter((friend: Friend) => friend.friendUserId !== null));
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : getFeatureUiText('chat.loadFriendsFailed'));
        }
      }
    };
    void loadFriends();
    return () => {
      cancelled = true;
    };
  }, [detail?.room_type, inviteOpen, token, userId, visible]);

  const handleSend = useCallback(async () => {
    const trimmed = draft.trim();
    if (!trimmed || sending) {
      return;
    }
    const languagePair = resolveFixedMessageLanguages(detail, room, userId);
    if (languagePair.sourceLang && !textMatchesDesignatedLanguage(trimmed, languagePair.sourceLang)) {
      setError(DESIGNATED_LANGUAGE_MISMATCH_MESSAGE);
      return;
    }
    setSending(true);
    setError('');
    try {
      const nextMessage = await sendChatRoomMessage(apiBaseUrl, token, room.room_id, {
        body: trimmed,
        sourceLang: languagePair.sourceLang,
        targetLang: languagePair.targetLang,
        requestTranslation: true,
      });
      setMessages((prev) => [...prev, nextMessage]);
      setDraft('');
      await markChatRoomRead(apiBaseUrl, token, room.room_id, nextMessage.message_id);
      onRoomChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.sendFailed'));
    } finally {
      setSending(false);
    }
  }, [apiBaseUrl, detail, draft, onRoomChanged, room, room.room_id, sending, token, userId]);

  const toggleInviteSelection = useCallback((friendUserId: number | null | undefined) => {
    if (!friendUserId) {
      return;
    }
    setInviteSelection((prev) => (
      prev.includes(friendUserId)
        ? prev.filter((id) => id !== friendUserId)
        : [...prev, friendUserId]
    ));
  }, []);

  const handleInviteMembers = useCallback(async () => {
    if (inviteSelection.length === 0 || inviteLoading) {
      return;
    }
    setInviteLoading(true);
    setError('');
    try {
      const payload = await addChatRoomMembers(apiBaseUrl, token, room.room_id, inviteSelection);
      setDetail(payload.room);
      setInviteSelection([]);
      setInviteOpen(false);
      await load();
      onRoomChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.inviteFailed'));
    } finally {
      setInviteLoading(false);
    }
  }, [apiBaseUrl, inviteLoading, inviteSelection, load, onRoomChanged, room.room_id, token]);

  const handleToggleInvitePolicy = useCallback(async () => {
    if (!detail || settingsSaving) {
      return;
    }
    setSettingsSaving(true);
    setError('');
    try {
      const nextDetail = await updateChatRoomSettings(apiBaseUrl, token, room.room_id, {
        allowMemberInvites: !detail.allow_member_invites,
      });
      setDetail(nextDetail);
      onRoomChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.settingsFailed'));
    } finally {
      setSettingsSaving(false);
    }
  }, [apiBaseUrl, detail, onRoomChanged, room.room_id, settingsSaving, token]);

  const handleSaveMemberLimit = useCallback(async () => {
    if (!detail || settingsSaving) {
      return;
    }
    if (pendingMemberLimit < detail.members.length) {
      setError(getFeatureUiText('chat.memberLimitTooSmall', { count: detail.members.length, limit: pendingMemberLimit }));
      return;
    }
    if (pendingMemberLimit === detail.member_limit) {
      return;
    }
    setSettingsSaving(true);
    setError('');
    try {
      const nextDetail = await updateChatRoomSettings(apiBaseUrl, token, room.room_id, {
        memberLimit: pendingMemberLimit,
      });
      setDetail(nextDetail);
      onRoomChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.memberLimitFailed'));
    } finally {
      setSettingsSaving(false);
    }
  }, [apiBaseUrl, detail, onRoomChanged, pendingMemberLimit, room.room_id, settingsSaving, token]);

  const canInviteMembers = !!detail?.can_invite_members;
  const canEditRoomSettings = detail?.room_type === 'group' && detail.title !== '번역 보관함' && detail.owner_user_id === userId;
  const currentMemberIds = new Set((detail?.members ?? []).map((member) => member.user_id));
  const invitableFriends = friends.filter((friend) => friend.friendUserId && !currentMemberIds.has(friend.friendUserId));

  return (
    <View
      style={styles.container}
      accessibilityLabel={`worldlinco-chat-room-screen-${room.room_id}`}
      testID={`worldlinco-chat-room-screen-${room.room_id}`}
    >
      <View style={styles.headerRow}>
        <Pressable
          style={styles.backButton}
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="worldlinco-chat-room-back"
          testID="worldlinco-chat-room-back"
        >
          <Text style={styles.backButtonText}>←</Text>
        </Pressable>
        <View style={styles.headerAvatar}>
          <Text style={styles.headerAvatarText}>
            {(detail?.title || room.title || '👤').trim().slice(0, 1).toUpperCase()}
          </Text>
          {isDirectRoom ? <View style={styles.headerOnlineDot} /> : null}
        </View>
        <View style={styles.headerTextWrap}>
          <Text style={styles.title} numberOfLines={1}>{headerTitleText}</Text>
          {isDirectRoom ? (
            <Text style={styles.headerOnline}>{getFeatureUiText('chat.online')}</Text>
          ) : (
            <Text style={styles.subtitle} numberOfLines={1}>{buildRoomSubtitle(detail, room)}</Text>
          )}
        </View>
        <Pressable
          style={styles.snsInviteButton}
          onPress={handleSnsInvite}
          accessibilityRole="button"
          accessibilityLabel="worldlinco-chat-sns-invite"
          testID="worldlinco-chat-sns-invite"
        >
          <Text style={styles.snsInviteButtonText}>{getFeatureUiText('chat.snsInvite')}</Text>
        </Pressable>
        {canInviteMembers ? (
          <Pressable style={styles.inviteButton} onPress={() => setInviteOpen((prev) => !prev)}>
            <Text style={styles.inviteButtonText}>{inviteOpen ? getFeatureUiText('chat.inviteClose') : getFeatureUiText('chat.inviteOpen')}</Text>
          </Pressable>
        ) : null}
        {canEditRoomSettings ? (
          <Pressable style={styles.settingButton} onPress={() => setSettingsOpen((prev) => !prev)}>
            <Text style={styles.settingButtonText}>{settingsOpen ? getFeatureUiText('chat.settingsClose') : getFeatureUiText('chat.settingsOpen')}</Text>
          </Pressable>
        ) : null}
      </View>

      {settingsOpen ? (
        <View style={styles.settingsPanel}>
          <Text style={styles.settingsTitle}>{getFeatureUiText('chat.settingsTitle')}</Text>
          <View style={styles.settingsSection}>
            <Text style={styles.settingsLabel}>{getFeatureUiText('chat.memberLimitChange')}</Text>
            <Text style={styles.settingsMeta}>{getFeatureUiText('chat.memberLimitMeta')}</Text>
            <View style={styles.limitOptionRow}>
              {GROUP_MEMBER_LIMIT_OPTIONS.map((option) => {
                const active = pendingMemberLimit === option;
                return (
                  <Pressable
                    key={`room-setting-member-limit-${option}`}
                    style={[styles.limitOptionChip, active && styles.limitOptionChipActive]}
                    onPress={() => {
                      setPendingMemberLimit(option);
                      setError('');
                    }}
                    disabled={settingsSaving}
                  >
                    <Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{getFeatureUiText('chat.memberLimitFixed', { count: option })}</Text>
                  </Pressable>
                );
              })}
            </View>
            <Pressable style={[styles.settingSaveButton, settingsSaving && styles.sendButtonDisabled]} onPress={() => { void handleSaveMemberLimit(); }} disabled={settingsSaving || pendingMemberLimit === detail?.member_limit}>
              <Text style={styles.settingSaveButtonText}>{settingsSaving ? getFeatureUiText('chat.memberLimitSaving') : getFeatureUiText('chat.memberLimitSave', { count: pendingMemberLimit })}</Text>
            </Pressable>
            <Text style={styles.settingsStatus}>{getFeatureUiText('chat.memberLimitStatus', { limit: detail?.member_limit ?? room.member_limit ?? 10, active: detail?.members.length ?? room.member_count })}</Text>
          </View>
          <View style={styles.settingsSection}>
            <Text style={styles.settingsLabel}>{getFeatureUiText('chat.invitePolicy')}</Text>
            <Pressable style={styles.settingsToggleRow} onPress={() => { void handleToggleInvitePolicy(); }} disabled={settingsSaving}>
              <View style={[styles.settingsToggleBox, detail?.allow_member_invites && styles.settingsToggleBoxActive]}>
                <Text style={styles.settingsToggleMark}>{detail?.allow_member_invites ? '✓' : ''}</Text>
              </View>
              <View style={styles.settingsTextWrap}>
                <Text style={styles.settingsLabel}>{getFeatureUiText('chat.membersCanInvite')}</Text>
                <Text style={styles.settingsMeta}>{getFeatureUiText('chat.membersCanInviteMeta')}</Text>
              </View>
            </Pressable>
            <Text style={styles.settingsStatus}>{settingsSaving ? getFeatureUiText('chat.settingsSaving') : (detail ? buildGroupInviteStatusLabel(detail, room, { currentPrefix: true }) : getFeatureUiText('chat.settingsLoading'))}</Text>
          </View>
        </View>
      ) : null}

      {detail?.members?.length ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.memberRailScroll}
          contentContainerStyle={styles.memberRail}
        >
          {detail.members.map((member) => (
            <View key={`member-${member.user_id}`} style={styles.memberBadge}>
              <Text style={styles.memberBadgeText}>
                {formatFlagPrefixedName(resolveMemberFlag(member.user_id, member.preferred_language), member.nickname)}
              </Text>
            </View>
          ))}
        </ScrollView>
      ) : null}

      {inviteOpen ? (
        <View style={styles.invitePanel}>
          <Text style={styles.invitePanelTitle}>{getFeatureUiText('chat.invitePanelTitle')}</Text>
          {invitableFriends.length === 0 ? (
            <Text style={styles.inviteEmptyText}>{getFeatureUiText('chat.inviteEmpty')}</Text>
          ) : (
            <View style={styles.inviteChipWrap}>
              {invitableFriends.map((friend) => {
                const { friendUserId } = friend;
                const active = !!friendUserId && inviteSelection.includes(friendUserId);
                return (
                  <Pressable
                    key={`invite-friend-${friend.id}`}
                    style={[styles.inviteChip, active && styles.inviteChipActive]}
                    onPress={() => toggleInviteSelection(friendUserId)}
                  >
                    <Text style={[styles.inviteChipText, active && styles.inviteChipTextActive]}>
                      {friend.friendCountryFlag || '🌐'} {friend.friendUsername || friend.friendEmail}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          )}
          <Pressable style={[styles.sendButton, inviteLoading && styles.sendButtonDisabled]} onPress={() => { void handleInviteMembers(); }} disabled={inviteLoading || inviteSelection.length === 0}>
            <Text style={styles.sendButtonText}>{inviteLoading ? getFeatureUiText('chat.inviteSaving') : getFeatureUiText('chat.inviteSubmit')}</Text>
          </Pressable>
        </View>
      ) : null}

      {/* 언어 선택 바 — 사용자 화면 비노출(회원가입 언어 기준 양방향 자동). 파이프라인은 voiceLangs 유지. */}
      <View style={styles.aiChipWrap}>
        <View style={styles.aiChip}>
          <Text style={styles.aiChipText}>{getFeatureUiText('chat.aiChip')}</Text>
        </View>
        <BidirectionalLanguagePairBadge fromLang={chatPairFromLang} toLang={chatPairToLang} compact />
        <Text style={styles.narratorPolicyHint}>{getFeatureUiText('chat.narratorCountryPolicyHint')}</Text>
      </View>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {loading ? <ActivityIndicator color="#1e6fe0" style={styles.loader} /> : null}

      <ScrollView style={styles.messageScroll} contentContainerStyle={styles.messageList}>
        {messages.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>{getFeatureUiText('chat.emptyRoom')}</Text>
          </View>
        ) : (
          messages.map((message) => {
            const isMine = !!message.mine;
            const clock = formatChatClock(message.created_at);
            // 특수 메시지(OCR/노래/번역공유/시스템)는 기존 카드 형태 유지.
            if (message.message_type !== 'text') {
              return (
                <View
                  key={message.message_id}
                  style={[styles.messageBubble, isMine ? styles.messageBubbleMine : styles.messageBubbleOther]}
                  accessibilityLabel={buildChatMessageAccessibilityLabel(message)}
                  testID={buildChatMessageSelector(message)}
                >
                  <Text style={[styles.messageSender, isMine ? styles.messageSenderMine : styles.messageSenderOther]}>
                    {resolveSenderDisplayLabel(message, isMine)}
                  </Text>
                  {renderMessageContent(message)}
                </View>
              );
            }
            // [목업 #4] 텍스트 말풍선: 원문(작게) + 번역(굵게) + 🔊, 시간/읽음표시.
            const translated = getEffectiveTranslatedBody(message);
            const speakLang = chatNarratorLang;
            const speak = () => {
              const speakBody = translated || message.body;
              try {
                console.log('[CHAT_READALOUD_MANUAL_TRIGGER]', JSON.stringify({ speakLang, userCountryCode, text_len: String(speakBody || '').length }));
                // 채팅 수동 읽어주기도 서버 합성 우선으로 통일한다.
                void announceServerVoice(speakBody, speakLang, userCountryCode);
              } catch {
                /* 낭독 실패 무시 */
              }
            };
            return (
              <View
                key={message.message_id}
                style={[styles.msgRow, isMine ? styles.msgRowMine : styles.msgRowPeer]}
                accessibilityLabel={buildChatMessageAccessibilityLabel(message)}
                testID={buildChatMessageSelector(message)}
              >
                {!isMine ? (
                  <View style={styles.msgAvatar}>
                    <Text style={styles.msgAvatarText}>
                      {((isDirectRoom ? (detail?.title || room.title) : message.sender_label) || '상').trim().slice(0, 1).toUpperCase()}
                    </Text>
                  </View>
                ) : null}
                <View style={[styles.msgCol, isMine ? styles.msgColMine : styles.msgColPeer]}>
                  {!isMine && !isDirectRoom ? (
                    <Text style={styles.peerName}>{resolveSenderDisplayLabel(message, false)}</Text>
                  ) : null}
                  <View style={[styles.bubble, isMine ? styles.bubbleMine : styles.bubblePeer]}>
                    {translated ? (
                      <Text noI18n style={[styles.bubbleOriginal, isMine && styles.bubbleOriginalMine]}>{message.body}</Text>
                    ) : null}
                    <View style={styles.bubbleTransRow}>
                      <Text noI18n style={[styles.bubbleTranslated, isMine && styles.bubbleTranslatedMine]}>
                        {translated || message.body}
                      </Text>
                      <Pressable onPress={speak} accessibilityRole="button" accessibilityLabel="worldlinco-chat-speak" hitSlop={8}>
                        <Text style={[styles.speakIcon, isMine && styles.speakIconMine]}>🔊</Text>
                      </Pressable>
                    </View>
                  </View>
                  <Text style={[styles.msgTime, isMine && styles.msgTimeMine]}>
                    {clock}{isMine ? '  ✓✓' : ''}
                  </Text>
                  {isGroupViewerRoom && isMine && getDeliverySummaryLabel(message) ? (
                    <View style={styles.deliveryBadge}>
                      <Text style={styles.deliveryBadgeText}>{getDeliverySummaryLabel(message)}</Text>
                    </View>
                  ) : null}
                </View>
              </View>
            );
          })
        )}
      </ScrollView>

      {/* 음성 오류만 슬림하게 노출(자동 듣기 토글 제거 — 마이크는 입력 바에서 직접 ON/OFF). */}
      {voiceError ? (
        <Text style={styles.voiceErrorText} testID="worldlinco-chat-voice-error">{voiceError}</Text>
      ) : null}

      {/* 입력 바: 🎙️ 마이크(ON이면 파형) + 입력 + 원형 전송. 받은 메시지는 표기 없이 자동 낭독된다. */}
      <View style={styles.composerBar}>
        <Pressable
          style={[
            styles.composerMic,
            voiceStatus === 'recording' && styles.composerMicRecording,
            voiceStatus === 'transcribing' && styles.composerMicBusy,
          ]}
          onPress={() => { toggleVoiceInput(); }}
          disabled={voiceStatus === 'transcribing'}
          accessibilityRole="button"
          accessibilityLabel={voiceStatus === 'recording' ? 'worldlinco-chat-mic-on' : 'worldlinco-chat-mic-button'}
          testID="worldlinco-chat-mic-button"
        >
          <Text style={styles.composerMicIcon}>
            {voiceStatus === 'recording' ? '⏹️' : voiceStatus === 'transcribing' ? '⏳' : '🎙️'}
          </Text>
        </Pressable>
        {voiceStatus === 'recording' ? (
          <View style={styles.composerWave} testID="worldlinco-chat-mic-wave">
            <MicWaveform active color="#e5484d" />
          </View>
        ) : (
          <TextInput
            style={styles.composerInput}
            placeholder={voiceStatus === 'transcribing' ? getFeatureUiText('chat.transcribing') : getFeatureUiText('chat.inputPlaceholder')}
            placeholderTextColor="#9aa6b8"
            value={draft}
            onChangeText={setDraft}
            multiline
            accessibilityLabel="worldlinco-chat-message-input"
            testID="worldlinco-chat-message-input"
          />
        )}
        <Pressable
          style={[styles.composerSend, sending && styles.composerSendDisabled]}
          onPress={() => { void handleSend(); }}
          disabled={sending}
          accessibilityRole="button"
          accessibilityLabel="worldlinco-chat-send-button"
          testID="worldlinco-chat-send-button"
        >
          <Text style={styles.composerSendIcon}>{sending ? '…' : '➤'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, gap: 10, padding: 4 },
  /* light reskin: GitHub-dark → 소리새 라이트 */
  headerRow: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  backButton: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#ffffff',
  },
  backButtonText: { color: '#3a4356', fontWeight: '700' },
  headerTextWrap: { flex: 1, gap: 2 },
  title: { color: '#1a1f36', fontSize: 22, fontWeight: '800' },
  subtitle: { color: '#5f6b80', fontSize: 13 },
  inviteButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#e3f0ff',
  },
  inviteButtonText: { color: '#1e6fe0', fontWeight: '800' },
  snsInviteButton: {
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#e6f7ef',
    borderWidth: 1,
    borderColor: '#19c37d',
  },
  snsInviteButtonText: { color: '#1f9d57', fontWeight: '800', fontSize: 12 },
  readAloudButton: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 10,
    backgroundColor: '#f4f9ff',
    marginRight: 6,
  },
  readAloudButtonActive: { backgroundColor: '#e6f7ef' },
  readAloudButtonText: { color: '#5f6b80', fontWeight: '800' },
  readAloudButtonTextActive: { color: '#1f9d57' },
  settingButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#fff7e6',
  },
  settingButtonText: { color: '#b45309', fontWeight: '800' },
  settingsPanel: {
    gap: 10,
    backgroundColor: '#ffffff',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dce6f2',
    padding: 12,
  },
  settingsSection: { gap: 10 },
  settingsTitle: { color: '#1a1f36', fontSize: 15, fontWeight: '800' },
  settingsToggleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#f4f9ff',
    padding: 12,
  },
  settingsToggleBox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#bcd3f0',
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  settingsToggleBoxActive: { backgroundColor: '#1f6feb', borderColor: '#1e6fe0' },
  settingsToggleMark: { color: '#fff', fontSize: 12, fontWeight: '800' },
  settingsTextWrap: { flex: 1, gap: 3 },
  settingsLabel: { color: '#1a1f36', fontSize: 13, fontWeight: '700' },
  settingsMeta: { color: '#5f6b80', fontSize: 12, lineHeight: 18 },
  settingsStatus: { color: '#1e6fe0', fontSize: 12, fontWeight: '700' },
  limitOptionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  limitOptionChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#f4f9ff',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  limitOptionChipActive: { backgroundColor: '#e3f0ff', borderColor: '#1e6fe0' },
  limitOptionText: { color: '#3a4356', fontSize: 12, fontWeight: '700' },
  limitOptionTextActive: { color: '#1e6fe0' },
  settingSaveButton: {
    alignSelf: 'flex-start',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#1f6feb',
  },
  settingSaveButtonText: { color: '#fff', fontWeight: '800' },
  memberRailScroll: { flexGrow: 0, flexShrink: 0, maxHeight: 40 },
  memberRail: { gap: 8, alignItems: 'center' },
  memberBadge: {
    alignSelf: 'center',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dce6f2',
  },
  memberBadgeText: { color: '#3a4356', fontSize: 12, fontWeight: '700' },
  invitePanel: {
    gap: 10,
    backgroundColor: '#ffffff',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dce6f2',
    padding: 12,
  },
  invitePanelTitle: { color: '#1a1f36', fontSize: 15, fontWeight: '800' },
  inviteEmptyText: { color: '#5f6b80', fontSize: 13 },
  inviteChipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  inviteChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#f4f9ff',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  inviteChipActive: { backgroundColor: '#e3f0ff', borderColor: '#1e6fe0' },
  inviteChipText: { color: '#3a4356', fontSize: 12, fontWeight: '700' },
  inviteChipTextActive: { color: '#1e6fe0' },
  errorText: { color: '#e5484d', fontSize: 13 },
  loader: { marginTop: 4 },
  messageScroll: { flex: 1, minHeight: 200 },
  messageList: { gap: 10, paddingBottom: 8, flexGrow: 1 },
  emptyCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#dce6f2',
    padding: 14,
  },
  emptyText: { color: '#5f6b80', fontSize: 13, lineHeight: 20 },
  systemCard: {
    gap: 4,
    backgroundColor: 'rgba(15,23,42,0.04)',
    borderRadius: 12,
    padding: 10,
  },
  systemCardTitle: { color: '#1a1f36', fontSize: 13, fontWeight: '800' },
  systemCardBody: { color: '#3a4356', fontSize: 13, lineHeight: 19 },
  specialCard: { gap: 5 },
  specialTitle: { color: '#1a1f36', fontSize: 13, fontWeight: '800' },
  specialLabel: { color: '#5f6b80', fontSize: 11, fontWeight: '700' },
  messageBubble: {
    borderRadius: 16,
    padding: 12,
    gap: 4,
    maxWidth: '92%',
  },
  messageBubbleMine: {
    alignSelf: 'flex-end',
    backgroundColor: '#e3f0ff',
  },
  messageBubbleOther: {
    alignSelf: 'flex-start',
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dce6f2',
  },
  translatedIncomingWrap: { gap: 6 },
  messageSender: { fontSize: 12, fontWeight: '800' },
  messageSenderMine: { color: '#1e6fe0' },
  messageSenderOther: { color: '#0a7d4b' },
  messageBody: { color: '#000000', fontSize: 14, lineHeight: 20, fontWeight: '500' },
  messageOriginal: { color: '#4a5568', fontSize: 12, lineHeight: 18 },
  messageTranslated: { color: '#1f9d57', fontSize: 13, lineHeight: 19 },
  messageStatusError: { color: '#e5484d', fontSize: 12, fontWeight: '700' },
  deliveryBadge: {
    marginTop: 4,
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: '#f4f9ff',
    borderWidth: 1,
    borderColor: '#bcd3f0',
  },
  deliveryBadgeText: { color: '#1e6fe0', fontSize: 11, fontWeight: '800' },
  messageMeta: { color: '#8a93a3', fontSize: 11 },
  composerWrap: {
    gap: 10,
    backgroundColor: '#ffffff',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dce6f2',
    padding: 12,
  },
  input: {
    minHeight: 76,
    color: '#1a1f36',
    backgroundColor: '#f4f9ff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#dce6f2',
    paddingHorizontal: 12,
    paddingVertical: 10,
    textAlignVertical: 'top',
  },
  composerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 10,
  },
  micButton: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#e8f1ff',
    borderWidth: 1,
    borderColor: '#bcd3f0',
  },
  micButtonRecording: { backgroundColor: '#fdecec', borderColor: '#e5484d' },
  micButtonBusy: { opacity: 0.7 },
  micButtonHandsFreeOn: { backgroundColor: '#e6f7ef', borderColor: '#19c37d' },
  micButtonHandsFreeOnText: { color: '#1f9d57' },
  micButtonText: { color: '#1e6fe0', fontWeight: '800' },
  voiceErrorText: { color: '#e5484d', fontSize: 12, fontWeight: '700' },
  sendButton: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#1f6feb',
  },
  sendButtonDisabled: { opacity: 0.7 },
  sendButtonText: { color: '#fff', fontWeight: '800' },

  // ── [목업 #4] 헤더 아바타/온라인 ──
  headerAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#e3effb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerAvatarText: { color: '#0b2e5e', fontSize: 18, fontWeight: '800' },
  headerOnlineDot: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#34c759',
    borderWidth: 2,
    borderColor: '#ffffff',
  },
  headerOnline: { color: '#19a44b', fontSize: 13, fontWeight: '700' },

  // ── [목업 #4] 언어 선택 바 ──
  langBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    backgroundColor: '#ffffff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e1ecf7',
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  langBarSide: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  langBarFlag: { fontSize: 18 },
  langBarText: { color: '#1a1f36', fontSize: 14, fontWeight: '700' },
  langBarSwap: { color: '#7c8aa0', fontSize: 16 },

  // ── [목업 #4] AI 번역 칩 ──
  aiChipWrap: { alignItems: 'center', gap: 8, paddingHorizontal: 12 },
  aiChip: {
    backgroundColor: '#eaf2ff',
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 14,
  },
  aiChipText: { color: '#1e6fe0', fontSize: 12, fontWeight: '800' },
  narratorPolicyHint: { color: '#5f6b80', fontSize: 11, textAlign: 'center' },

  // ── [목업 #4] 말풍선 페어 ──
  msgRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, maxWidth: '100%' },
  msgRowMine: { justifyContent: 'flex-end' },
  msgRowPeer: { justifyContent: 'flex-start' },
  msgAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#e3effb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  msgAvatarText: { color: '#0b2e5e', fontSize: 13, fontWeight: '800' },
  msgCol: { maxWidth: '80%', gap: 3 },
  msgColMine: { alignItems: 'flex-end' },
  msgColPeer: { alignItems: 'flex-start' },
  peerName: { color: '#5f6b80', fontSize: 12, fontWeight: '700', marginLeft: 4 },
  bubble: { borderRadius: 18, paddingVertical: 10, paddingHorizontal: 14 },
  bubblePeer: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e1ecf7',
    borderTopLeftRadius: 6,
  },
  bubbleMine: {
    backgroundColor: '#1f6feb',
    borderTopRightRadius: 6,
  },
  bubbleOriginal: { color: '#6b7686', fontSize: 13, lineHeight: 18, marginBottom: 3 },
  bubbleOriginalMine: { color: '#cfe0fb' },
  bubbleTransRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  bubbleTranslated: { color: '#10172a', fontSize: 16, lineHeight: 23, fontWeight: '700', flexShrink: 1 },
  bubbleTranslatedMine: { color: '#ffffff' },
  speakIcon: { color: '#1e6fe0', fontSize: 16, marginBottom: 1 },
  speakIconMine: { color: '#cfe0fb' },
  msgTime: { color: '#9aa6b8', fontSize: 11, marginHorizontal: 4 },
  msgTimeMine: { color: '#9aa6b8' },

  // ── [목업 #4] 입력 바 ──
  composerTopRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 4 },
  handsFreeChip: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#eef4fb',
    borderWidth: 1,
    borderColor: '#d7e6f7',
  },
  handsFreeChipOn: { backgroundColor: '#e6f7ef', borderColor: '#19c37d' },
  handsFreeChipText: { color: '#5f6b80', fontWeight: '800', fontSize: 12 },
  handsFreeChipTextOn: { color: '#1f9d57' },
  composerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#ffffff',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#e1ecf7',
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  composerMic: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#eef4fb',
  },
  composerMicRecording: { backgroundColor: '#fdecec' },
  composerMicBusy: { opacity: 0.7 },
  composerMicIcon: { fontSize: 20 },
  composerInput: {
    flex: 1,
    color: '#1a1f36',
    fontSize: 15,
    maxHeight: 96,
    paddingVertical: 6,
    paddingHorizontal: 4,
    textAlignVertical: 'center',
  },
  composerWave: { flex: 1, alignItems: 'flex-start', justifyContent: 'center', paddingHorizontal: 6 },
  composerSend: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#e8453c',
    alignItems: 'center',
    justifyContent: 'center',
  },
  composerSendDisabled: { opacity: 0.6 },
  composerSendIcon: { color: '#ffffff', fontSize: 18, fontWeight: '800' },
});