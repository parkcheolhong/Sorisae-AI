import React, { useCallback, useEffect, useRef, useState } from 'react';
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

import { getFriends } from '../../../api/friends';
import type { Friend } from '../../friends/types';
import { addChatRoomMembers, connectChatRoomEvents, getChatRoomDetail, listChatRoomMessages, markChatRoomRead, sendChatRoomMessage, updateChatRoomSettings } from '../api';
import {
  DESIGNATED_LANGUAGE_MISMATCH_MESSAGE,
  textMatchesDesignatedLanguage,
} from '../../translation/designatedLanguage';
import type { ChatMessageItem, ChatRoomDetail, ChatRoomSummary } from '../types';

const GROUP_MEMBER_LIMIT_OPTIONS = [3, 5, 10] as const;

function buildGroupInviteStatusLabel(detail: ChatRoomDetail, room: ChatRoomSummary, options?: { currentPrefix?: boolean }): string {
  const memberLimit = detail.member_limit ?? room.member_limit ?? 10;
  const memberCount = detail.members.length;

  if (detail.allow_member_invites && detail.can_invite_members === false && memberCount >= memberLimit) {
    return options?.currentPrefix
      ? '현재: 정책은 멤버 초대 허용이지만 정원 만석으로 추가 초대 불가'
      : '정원 만석으로 추가 초대 불가';
  }

  if (detail.allow_member_invites) {
    return options?.currentPrefix ? '현재: 멤버 초대 허용' : '멤버 초대 허용';
  }

  return options?.currentPrefix ? '현재: owner만 초대' : 'owner만 초대';
}

function buildRoomSubtitle(detail: ChatRoomDetail | null, room: ChatRoomSummary): string {
  if (!detail) {
    return room.room_type;
  }

  if (detail.room_type !== 'direct') {
    const memberLimit = detail.member_limit ?? room.member_limit ?? 10;
    return `${detail.members.length}명 / 정원 ${memberLimit}명 · ${detail.translation_mode} · ${buildGroupInviteStatusLabel(detail, room)}`;
  }

  const preferredLanguage = detail.counterpart?.preferred_language?.trim();
  return preferredLanguage
    ? `1:1 대화 · 상대 지정 언어 ${preferredLanguage.toUpperCase()} 자동 번역`
    : '1:1 대화 · 상대 지정 언어 미설정';
}

function normalizeLanguageCode(value?: string | null): string | null {
  const normalized = value?.trim().toLowerCase();
  return normalized || null;
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
    return `배달 ${summary.done_count}/${summary.recipient_count} · 실패 ${summary.failed_count}`;
  }
  if (summary.status === 'failed') {
    return `배달 실패 ${summary.failed_count}/${summary.recipient_count}`;
  }
  if (summary.status === 'pending') {
    return `배달 중 ${summary.pending_count}/${summary.recipient_count}`;
  }
  return `배달 완료 ${summary.done_count}/${summary.recipient_count}`;
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
  onBack,
  onRoomChanged,
}: Props) {
  const [detail, setDetail] = useState<ChatRoomDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [draft, setDraft] = useState(initialDraft);
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
  const appStateRef = useRef(AppState.currentState);
  const hasLoadedOnceRef = useRef(false);
  const isDirectRoom = detail?.room_type === 'direct';
  const isGroupViewerRoom = isGroupRoom(detail, room);

  const renderMessageContent = useCallback((message: ChatMessageItem) => {
    const effectiveTranslatedBody = getEffectiveTranslatedBody(message);
    const effectiveTranslationStatus = getEffectiveTranslationStatus(message);

    if (message.message_type === 'system_invite') {
      return (
        <View style={styles.systemCard}>
          <Text style={styles.systemCardTitle}>멤버 초대</Text>
          <Text style={styles.systemCardBody}>{message.body}</Text>
        </View>
      );
    }

    if (message.message_type === 'ocr') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>OCR 결과</Text>
          <Text style={styles.specialLabel}>추출 텍스트</Text>
          <Text style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>번역 텍스트</Text>
              <Text style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (message.message_type === 'song_translation') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>노래 번역</Text>
          <Text style={styles.specialLabel}>원문/작업 메모</Text>
          <Text style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>번역 가사</Text>
              <Text style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (message.message_type === 'translation') {
      return (
        <View style={styles.specialCard}>
          <Text style={styles.specialTitle}>번역 공유</Text>
          <Text style={styles.specialLabel}>원문</Text>
          <Text style={styles.messageBody}>{message.body}</Text>
          {effectiveTranslatedBody ? (
            <>
              <Text style={styles.specialLabel}>번역문</Text>
              <Text style={styles.messageTranslated}>{effectiveTranslatedBody}</Text>
            </>
          ) : null}
        </View>
      );
    }

    if (isGroupViewerRoom && !message.mine) {
      return (
        <View style={styles.translatedIncomingWrap}>
          {effectiveTranslatedBody ? (
            <Text style={styles.messageBody}>{effectiveTranslatedBody}</Text>
          ) : (
            <Text style={styles.messageBody}>{message.body}</Text>
          )}
          <Text style={styles.messageOriginal}>{message.body}</Text>
          {effectiveTranslationStatus === 'failed' ? (
            <Text style={styles.messageStatusError}>내 번역 생성 실패</Text>
          ) : null}
        </View>
      );
    }

    if (isDirectRoom && !message.mine && effectiveTranslatedBody) {
      return (
        <View style={styles.translatedIncomingWrap}>
          <Text style={styles.messageBody}>{effectiveTranslatedBody}</Text>
          <Text style={styles.messageOriginal}>{message.body}</Text>
        </View>
      );
    }

    return <Text style={styles.messageBody}>{message.body}</Text>;
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
        setError(e instanceof Error ? e.message : '대화방을 불러오지 못했습니다.');
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
        setMessages((prev) => upsertMessageItem(prev, event.message));
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
          setError(e instanceof Error ? e.message : '초대 가능한 친구를 불러오지 못했습니다.');
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
      setError(e instanceof Error ? e.message : '메시지를 전송하지 못했습니다.');
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
      setError(e instanceof Error ? e.message : '멤버를 초대하지 못했습니다.');
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
      setError(e instanceof Error ? e.message : '방 설정을 저장하지 못했습니다.');
    } finally {
      setSettingsSaving(false);
    }
  }, [apiBaseUrl, detail, onRoomChanged, room.room_id, settingsSaving, token]);

  const handleSaveMemberLimit = useCallback(async () => {
    if (!detail || settingsSaving) {
      return;
    }
    if (pendingMemberLimit < detail.members.length) {
      setError(`현재 활성 멤버가 ${detail.members.length}명이라 정원을 ${pendingMemberLimit}명으로 줄일 수 없습니다.`);
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
      setError(e instanceof Error ? e.message : '방 정원을 저장하지 못했습니다.');
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
          <Text style={styles.backButtonText}>← 목록</Text>
        </Pressable>
        <View style={styles.headerTextWrap}>
          <Text style={styles.title}>{detail?.title || room.title}</Text>
          <Text style={styles.subtitle}>{buildRoomSubtitle(detail, room)}</Text>
        </View>
        {canInviteMembers ? (
          <Pressable style={styles.inviteButton} onPress={() => setInviteOpen((prev) => !prev)}>
            <Text style={styles.inviteButtonText}>{inviteOpen ? '초대 닫기' : '멤버 초대'}</Text>
          </Pressable>
        ) : null}
        {canEditRoomSettings ? (
          <Pressable style={styles.settingButton} onPress={() => setSettingsOpen((prev) => !prev)}>
            <Text style={styles.settingButtonText}>{settingsOpen ? '설정 닫기' : '방 설정'}</Text>
          </Pressable>
        ) : null}
      </View>

      {settingsOpen ? (
        <View style={styles.settingsPanel}>
          <Text style={styles.settingsTitle}>방 설정</Text>
          <View style={styles.settingsSection}>
            <Text style={styles.settingsLabel}>정원 변경</Text>
            <Text style={styles.settingsMeta}>생성자 입장 후에도 3명, 5명, 10명 고정방으로 바꿀 수 있습니다. 현재 활성 멤버 수보다 작게는 저장되지 않습니다.</Text>
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
                    <Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{option}명 고정</Text>
                  </Pressable>
                );
              })}
            </View>
            <Pressable style={[styles.settingSaveButton, settingsSaving && styles.sendButtonDisabled]} onPress={() => { void handleSaveMemberLimit(); }} disabled={settingsSaving || pendingMemberLimit === detail?.member_limit}>
              <Text style={styles.settingSaveButtonText}>{settingsSaving ? '정원 저장 중...' : `정원 ${pendingMemberLimit}명으로 저장`}</Text>
            </Pressable>
            <Text style={styles.settingsStatus}>현재: 정원 {detail?.member_limit ?? room.member_limit ?? 10}명 · 활성 멤버 {detail?.members.length ?? room.member_count}명</Text>
          </View>
          <View style={styles.settingsSection}>
            <Text style={styles.settingsLabel}>초대 정책</Text>
          <Pressable style={styles.settingsToggleRow} onPress={() => { void handleToggleInvitePolicy(); }} disabled={settingsSaving}>
            <View style={[styles.settingsToggleBox, detail?.allow_member_invites && styles.settingsToggleBoxActive]}>
              <Text style={styles.settingsToggleMark}>{detail?.allow_member_invites ? '✓' : ''}</Text>
            </View>
            <View style={styles.settingsTextWrap}>
              <Text style={styles.settingsLabel}>멤버도 초대 가능</Text>
              <Text style={styles.settingsMeta}>끄면 owner만 초대할 수 있고, 켜면 현재 멤버도 새 친구를 초대할 수 있습니다.</Text>
            </View>
          </Pressable>
          <Text style={styles.settingsStatus}>{settingsSaving ? '설정 저장 중...' : (detail ? buildGroupInviteStatusLabel(detail, room, { currentPrefix: true }) : '현재 설정 불러오는 중...')}</Text>
          </View>
        </View>
      ) : null}

      {detail?.members?.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.memberRail}>
          {detail.members.map((member) => (
            <View key={`member-${member.user_id}`} style={styles.memberBadge}>
              <Text style={styles.memberBadgeText}>{member.nickname}</Text>
            </View>
          ))}
        </ScrollView>
      ) : null}

      {inviteOpen ? (
        <View style={styles.invitePanel}>
          <Text style={styles.invitePanelTitle}>초대할 친구 선택</Text>
          {invitableFriends.length === 0 ? (
            <Text style={styles.inviteEmptyText}>추가로 초대할 수 있는 친구가 없습니다.</Text>
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
            <Text style={styles.sendButtonText}>{inviteLoading ? '초대 중...' : '선택 멤버 초대'}</Text>
          </Pressable>
        </View>
      ) : null}

      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {loading ? <ActivityIndicator color="#79c0ff" style={styles.loader} /> : null}

      <ScrollView style={styles.messageScroll} contentContainerStyle={styles.messageList}>
        {messages.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>아직 메시지가 없습니다. 첫 메시지를 보내면 이 방이 번역/채팅 히스토리의 시작점이 됩니다.</Text>
          </View>
        ) : (
          messages.map((message) => (
            <View
              key={message.message_id}
              style={[styles.messageBubble, message.mine ? styles.messageBubbleMine : styles.messageBubbleOther]}
              accessibilityLabel={buildChatMessageAccessibilityLabel(message)}
              testID={buildChatMessageSelector(message)}
            >
              <Text style={styles.messageSender}>{message.sender_label}</Text>
              {renderMessageContent(message)}
              {isGroupViewerRoom && message.mine && message.message_type === 'text' && getDeliverySummaryLabel(message) ? (
                <View style={styles.deliveryBadge}>
                  <Text style={styles.deliveryBadgeText}>{getDeliverySummaryLabel(message)}</Text>
                </View>
              ) : null}
              {message.message_type === 'text' && getEffectiveTranslatedBody(message) && !(isDirectRoom && !message.mine) && !(isGroupViewerRoom && !message.mine) ? (
                <Text style={styles.messageTranslated}>{getEffectiveTranslatedBody(message)}</Text>
              ) : null}
              <Text style={styles.messageMeta}>{message.message_type} · {message.created_at}</Text>
            </View>
          ))
        )}
      </ScrollView>

      <View style={styles.composerWrap}>
        <TextInput
          style={styles.input}
          placeholder="메시지를 입력하세요"
          placeholderTextColor="#6e7681"
          value={draft}
          onChangeText={setDraft}
          multiline
          accessibilityLabel="worldlinco-chat-message-input"
          testID="worldlinco-chat-message-input"
        />
        <Pressable
          style={styles.sendButton}
          onPress={() => { void handleSend(); }}
          disabled={sending}
          accessibilityRole="button"
          accessibilityLabel="worldlinco-chat-send-button"
          testID="worldlinco-chat-send-button"
        >
          <Text style={styles.sendButtonText}>{sending ? '전송 중...' : '보내기'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 12 },
  headerRow: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  backButton: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#111827',
  },
  backButtonText: { color: '#c9d1d9', fontWeight: '700' },
  headerTextWrap: { flex: 1, gap: 2 },
  title: { color: '#f0f6fc', fontSize: 22, fontWeight: '800' },
  subtitle: { color: '#8b949e', fontSize: 13 },
  inviteButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#17324d',
  },
  inviteButtonText: { color: '#79c0ff', fontWeight: '800' },
  settingButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#2b1f14',
  },
  settingButtonText: { color: '#f2c078', fontWeight: '800' },
  settingsPanel: {
    gap: 10,
    backgroundColor: '#111827',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1f2a37',
    padding: 12,
  },
  settingsSection: { gap: 10 },
  settingsTitle: { color: '#f0f6fc', fontSize: 15, fontWeight: '800' },
  settingsToggleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#0f1723',
    padding: 12,
  },
  settingsToggleBox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#38506d',
    backgroundColor: '#111827',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  settingsToggleBoxActive: { backgroundColor: '#1f6feb', borderColor: '#79c0ff' },
  settingsToggleMark: { color: '#fff', fontSize: 12, fontWeight: '800' },
  settingsTextWrap: { flex: 1, gap: 3 },
  settingsLabel: { color: '#f0f6fc', fontSize: 13, fontWeight: '700' },
  settingsMeta: { color: '#8b949e', fontSize: 12, lineHeight: 18 },
  settingsStatus: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
  limitOptionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  limitOptionChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#0f1723',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  limitOptionChipActive: { backgroundColor: '#17324d', borderColor: '#79c0ff' },
  limitOptionText: { color: '#c9d1d9', fontSize: 12, fontWeight: '700' },
  limitOptionTextActive: { color: '#79c0ff' },
  settingSaveButton: {
    alignSelf: 'flex-start',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#1f6feb',
  },
  settingSaveButtonText: { color: '#fff', fontWeight: '800' },
  memberRail: { gap: 8 },
  memberBadge: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#243244',
  },
  memberBadgeText: { color: '#c9d1d9', fontSize: 12, fontWeight: '700' },
  invitePanel: {
    gap: 10,
    backgroundColor: '#111827',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1f2a37',
    padding: 12,
  },
  invitePanelTitle: { color: '#f0f6fc', fontSize: 15, fontWeight: '800' },
  inviteEmptyText: { color: '#8b949e', fontSize: 13 },
  inviteChipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  inviteChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#0f1723',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  inviteChipActive: { backgroundColor: '#17324d', borderColor: '#79c0ff' },
  inviteChipText: { color: '#c9d1d9', fontSize: 12, fontWeight: '700' },
  inviteChipTextActive: { color: '#79c0ff' },
  errorText: { color: '#ff7b72', fontSize: 13 },
  loader: { marginTop: 4 },
  messageScroll: { maxHeight: 420 },
  messageList: { gap: 10, paddingBottom: 8 },
  emptyCard: {
    backgroundColor: '#111827',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#1f2a37',
    padding: 14,
  },
  emptyText: { color: '#8b949e', fontSize: 13, lineHeight: 20 },
  systemCard: {
    gap: 4,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderRadius: 12,
    padding: 10,
  },
  systemCardTitle: { color: '#f0f6fc', fontSize: 13, fontWeight: '800' },
  systemCardBody: { color: '#c9d1d9', fontSize: 13, lineHeight: 19 },
  specialCard: { gap: 5 },
  specialTitle: { color: '#f0f6fc', fontSize: 13, fontWeight: '800' },
  specialLabel: { color: '#8b949e', fontSize: 11, fontWeight: '700' },
  messageBubble: {
    borderRadius: 16,
    padding: 12,
    gap: 4,
    maxWidth: '92%',
  },
  messageBubbleMine: {
    alignSelf: 'flex-end',
    backgroundColor: '#17324d',
  },
  messageBubbleOther: {
    alignSelf: 'flex-start',
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#243244',
  },
  translatedIncomingWrap: { gap: 6 },
  messageSender: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
  messageBody: { color: '#f0f6fc', fontSize: 14, lineHeight: 20 },
  messageOriginal: { color: '#8b949e', fontSize: 12, lineHeight: 18 },
  messageTranslated: { color: '#9be9a8', fontSize: 13, lineHeight: 19 },
  messageStatusError: { color: '#ff7b72', fontSize: 12, fontWeight: '700' },
  deliveryBadge: {
    marginTop: 4,
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: '#0f1723',
    borderWidth: 1,
    borderColor: '#38506d',
  },
  deliveryBadgeText: { color: '#79c0ff', fontSize: 11, fontWeight: '800' },
  messageMeta: { color: '#6e7681', fontSize: 11 },
  composerWrap: {
    gap: 10,
    backgroundColor: '#111827',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1f2a37',
    padding: 12,
  },
  input: {
    minHeight: 76,
    color: '#f0f6fc',
    backgroundColor: '#0f1723',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#243244',
    paddingHorizontal: 12,
    paddingVertical: 10,
    textAlignVertical: 'top',
  },
  sendButton: {
    alignSelf: 'flex-end',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#1f6feb',
  },
  sendButtonDisabled: { opacity: 0.7 },
  sendButtonText: { color: '#fff', fontWeight: '800' },
});