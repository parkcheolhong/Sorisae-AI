import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { getFriends } from '../../../api/friends';
import type { Friend } from '../../friends/types';
import { createDirectChatRoom, createGroupChatRoom, ensureSelfChatRoom, listChatRooms } from '../api';
import type { ChatRoomSummary } from '../types';
import type { LangCode } from '../../language/languageCatalog';
import { getLangLabelText, isSupportedLangCode } from '../../language/languageCatalog';
import { BidirectionalLanguagePairBadge } from '../../i18n/BidirectionalLanguagePairBadge';
import { getFeatureUiText } from '../../i18n/featureUiCatalog';

const GROUP_MEMBER_LIMIT_OPTIONS = [3, 5, 10] as const;

function formatPreferredLanguage(language?: string | null): string {
  const normalized = language?.trim().toLowerCase();
  if (normalized && isSupportedLangCode(normalized)) {
    return getLangLabelText(normalized);
  }
  return getFeatureUiText('chat.list.langUnset');
}

// 서버 last_message_at(naive UTC, 'Z')을 로컬 기준으로 표시.
// 타임존 표기가 없으면 UTC 로 간주(레거시/캐시 방어) → KST ~9h 오프셋/Invalid Date 방지.
// 오늘이면 '오전/오후 h:mm', 그 외엔 'M/D' 로 축약 표시한다.
function formatRoomTime(iso?: string | null): string {
  const raw = (iso ?? '').trim();
  if (!raw) return '';
  const normalized = /[zZ]$/.test(raw) || /[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return '';
  const now = new Date();
  const sameDay = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  if (sameDay) {
    const h = d.getHours();
    const m = d.getMinutes().toString().padStart(2, '0');
    const ampm = h < 12 ? getFeatureUiText('chat.am') : getFeatureUiText('chat.pm');
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return `${ampm} ${h12}:${m}`;
  }
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function buildTranslationHint(language?: string | null, _countryCode?: string | null): string {
  if (language?.trim()) {
    return getFeatureUiText('chat.peerLangAutoTranslate');
  }
  return getFeatureUiText('chat.peerLangAutoDetect');
}

function getRoomAlertLabel(room: ChatRoomSummary): string | null {
  if (room.last_message_type === 'system_invite') {
    return getFeatureUiText('chat.list.alertGroupInvite');
  }
  if (room.last_message_type === 'system_announcement') {
    return getFeatureUiText('chat.list.alertAnnouncement');
  }
  if (room.last_message_type === 'translation' || room.last_message_type === 'ocr' || room.last_message_type === 'song_translation') {
    return getFeatureUiText('chat.list.alertTranslation');
  }
  if (room.unread_count > 0) {
    return getFeatureUiText('chat.list.alertNewMessage');
  }
  return null;
}

function buildChatRoomSelector(room: ChatRoomSummary): string {
  return `worldlinco-chat-room-${room.room_id}`;
}

function buildGroupRoomMeta(room: ChatRoomSummary): string {
  if (room.room_type === 'direct') {
    return getFeatureUiText('chat.list.directRoom');
  }
  const memberLimit = room.member_limit ?? 10;
  return getFeatureUiText('chat.list.groupRoomMeta', { count: room.member_count, limit: memberLimit });
}

interface Props {
  apiBaseUrl: string;
  token: string;
  userId: number;
  fromLang?: LangCode;
  toLang?: LangCode;
  visible?: boolean;
  refreshKey?: number;
  onOpenRoom: (room: ChatRoomSummary) => void;
  autoCallVoiceId?: string | null;
  onAutoCallConsumed?: () => void;
  onStartFriendVoiceCall?: (friend: Friend) => void | Promise<void>;
  openGroupSignal?: number;
}

export function ChatRoomListScreen({
  apiBaseUrl,
  token,
  userId,
  fromLang = 'ko',
  toLang = 'en',
  visible = true,
  refreshKey = 0,
  onOpenRoom,
  autoCallVoiceId = null,
  onAutoCallConsumed,
  onStartFriendVoiceCall,
  openGroupSignal = 0,
}: Props) {
  const [rooms, setRooms] = useState<ChatRoomSummary[]>([]);
  const [friends, setFriends] = useState<Friend[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');
  const [showGroupComposer, setShowGroupComposer] = useState(false);
  const [groupTitle, setGroupTitle] = useState('');
  const [groupMemberLimit, setGroupMemberLimit] = useState<number>(10);
  const [selectedGroupMemberIds, setSelectedGroupMemberIds] = useState<number[]>([]);
  const [allowMemberInvites, setAllowMemberInvites] = useState(false);
  const [expandedFriendId, setExpandedFriendId] = useState<number | null>(null);
  const autoCallKeyRef = useRef<string | null>(null);
  const openGroupSignalRef = useRef<number>(openGroupSignal);
  const unreadRoomCount = rooms.filter((room) => room.unread_count > 0).length;
  const unreadMessageCount = rooms.reduce((sum, room) => sum + room.unread_count, 0);
  const latestRoom = rooms.find((room) => !!room.last_message_at) ?? rooms[0] ?? null;

  useEffect(() => {
    if (!autoCallVoiceId) {
      autoCallKeyRef.current = null;
      return;
    }

    if (!visible || loading || !onStartFriendVoiceCall) {
      return;
    }

    const normalizedTarget = autoCallVoiceId.trim().toLowerCase();
    if (!normalizedTarget || autoCallKeyRef.current === normalizedTarget) {
      return;
    }

    const matchedFriend = friends.find((friend) => {
      const voiceId = String(friend.friendVoiceId || '').trim().toLowerCase();
      const userIdValue = String(friend.friendUserId || '').trim().toLowerCase();
      const emailValue = String(friend.friendEmail || '').trim().toLowerCase();
      return voiceId === normalizedTarget || userIdValue === normalizedTarget || emailValue === normalizedTarget;
    });

    if (!matchedFriend) {
      return;
    }

    autoCallKeyRef.current = normalizedTarget;
    onAutoCallConsumed?.();
    void Promise.resolve(onStartFriendVoiceCall(matchedFriend));
  }, [autoCallVoiceId, friends, loading, onAutoCallConsumed, onStartFriendVoiceCall, visible]);

  // [단체채팅 1탭] 채팅 허브의 "단체채팅" 액션 타일에서 보낸 신호로 그룹방 작성기를 펼친다.
  useEffect(() => {
    if (openGroupSignal && openGroupSignal !== openGroupSignalRef.current) {
      openGroupSignalRef.current = openGroupSignal;
      setShowGroupComposer(true);
      setError('');
    }
  }, [openGroupSignal]);
  const latestRoomAlert = latestRoom ? getRoomAlertLabel(latestRoom) : null;
  const maxSelectableMembers = Math.max(groupMemberLimit - 1, 0);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [nextRooms, friendPayload] = await Promise.all([
        listChatRooms(apiBaseUrl, token),
        getFriends(userId, token),
      ]);
      setRooms(nextRooms);
      setFriends(friendPayload.friends.filter((friend: Friend) => friend.friendUserId !== null));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.list.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, token, userId]);

  useEffect(() => {
    if (!visible) {
      return;
    }
    void load();
  }, [load, refreshKey, visible]);

  const handleOpenSelfRoom = useCallback(async () => {
    setBusyAction('self-room');
    setError('');
    try {
      const room = await ensureSelfChatRoom(apiBaseUrl, token);
      onOpenRoom(room);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.list.vaultFailed'));
    } finally {
      setBusyAction('');
    }
  }, [apiBaseUrl, onOpenRoom, token]);

  const handleOpenDirectRoom = useCallback(async (friend: Friend) => {
    if (!friend.friendUserId) {
      return;
    }
    setBusyAction(`friend-${friend.id}`);
    setError('');
    try {
      const room = await createDirectChatRoom(apiBaseUrl, token, friend.friendUserId);
      onOpenRoom(room);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.list.friendRoomFailed'));
    } finally {
      setBusyAction('');
    }
  }, [apiBaseUrl, onOpenRoom, token]);

  const toggleGroupMember = useCallback((friendUserId: number | null | undefined) => {
    if (!friendUserId) {
      return;
    }
    setError('');
    setSelectedGroupMemberIds((prev) => {
      if (prev.includes(friendUserId)) {
        return prev.filter((id) => id !== friendUserId);
      }
      if (prev.length >= maxSelectableMembers) {
        setError(getFeatureUiText('chat.list.groupCapacityLimit', { limit: groupMemberLimit }));
        return prev;
      }
      return [...prev, friendUserId];
    });
  }, [groupMemberLimit, maxSelectableMembers]);

  const handleCreateGroupRoom = useCallback(async () => {
    const title = groupTitle.trim();
    if (!title) {
      setError(getFeatureUiText('chat.list.groupNameRequired'));
      return;
    }
    if (selectedGroupMemberIds.length === 0) {
      setError(getFeatureUiText('chat.list.groupMemberRequired'));
      return;
    }
    if (selectedGroupMemberIds.length + 1 > groupMemberLimit) {
      setError(getFeatureUiText('chat.list.groupOverCapacity', { limit: groupMemberLimit }));
      return;
    }
    setBusyAction('group-room');
    setError('');
    try {
      const room = await createGroupChatRoom(apiBaseUrl, token, {
        title,
        memberUserIds: selectedGroupMemberIds,
        allowMemberInvites,
        memberLimit: groupMemberLimit,
      });
      setShowGroupComposer(false);
      setGroupTitle('');
      setGroupMemberLimit(10);
      setSelectedGroupMemberIds([]);
      setAllowMemberInvites(false);
      onOpenRoom(room);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : getFeatureUiText('chat.list.groupFailed'));
    } finally {
      setBusyAction('');
    }
  }, [allowMemberInvites, apiBaseUrl, groupMemberLimit, groupTitle, onOpenRoom, selectedGroupMemberIds, token]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{getFeatureUiText('chat.list.title')}</Text>
      <BidirectionalLanguagePairBadge fromLang={fromLang} toLang={toLang} compact />
      <View style={styles.summaryCard}>
        <View style={styles.summaryHeaderRow}>
          <Text style={styles.summaryTitle}>{getFeatureUiText('chat.list.summaryTitle')}</Text>
          <Text style={styles.summaryMetric}>{getFeatureUiText('chat.list.summaryMetric', { rooms: unreadRoomCount, unread: unreadMessageCount })}</Text>
        </View>
        {latestRoom ? (
          <>
            <View style={styles.summaryRoomHeader}>
              <Text style={styles.summaryRoomTitle}>{latestRoom.title}</Text>
              {latestRoomAlert ? (
                <View style={styles.alertPill}>
                  <Text style={styles.alertPillText}>{latestRoomAlert}</Text>
                </View>
              ) : null}
            </View>
            <Text style={styles.summaryPreview}>{latestRoom.last_message_preview || getFeatureUiText('chat.list.noPreview')}</Text>
            <Text style={styles.summaryMeta}>{formatRoomTime(latestRoom.last_message_at) || getFeatureUiText('chat.list.noRecentTime')}</Text>
          </>
        ) : (
          <Text style={styles.summaryPreview}>{getFeatureUiText('chat.list.noRecentChat')}</Text>
        )}
      </View>
      <View style={styles.quickRow}>
        <Pressable style={styles.primaryButton} onPress={() => { void handleOpenSelfRoom(); }} disabled={busyAction === 'self-room'}>
          <Text style={styles.primaryButtonText}>{busyAction === 'self-room' ? getFeatureUiText('chat.list.opening') : getFeatureUiText('chat.list.openVault')}</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => setShowGroupComposer((prev) => !prev)}>
          <Text style={styles.secondaryButtonText}>{showGroupComposer ? getFeatureUiText('chat.list.closeGroup') : getFeatureUiText('chat.list.createGroup')}</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => { void load(); }} disabled={loading}>
          <Text style={styles.secondaryButtonText}>{loading ? getFeatureUiText('chat.list.refreshing') : getFeatureUiText('chat.list.refresh')}</Text>
        </Pressable>
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {loading ? <ActivityIndicator color="#1e6fe0" style={styles.loader} /> : null}

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {showGroupComposer ? (
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>{getFeatureUiText('chat.list.groupTitle')}</Text>
            <Text style={styles.emptyText}>{getFeatureUiText('chat.list.groupHint')}</Text>
            <TextInput
              style={styles.groupInput}
              placeholder={getFeatureUiText('chat.list.groupPlaceholder')}
              placeholderTextColor="#8a93a3"
              value={groupTitle}
              onChangeText={setGroupTitle}
            />
            <View style={styles.limitSection}>
              <Text style={styles.policyTitle}>{getFeatureUiText('chat.list.capacityTitle')}</Text>
              <Text style={styles.capacityMeta}>{getFeatureUiText('chat.list.capacityMeta', { count: selectedGroupMemberIds.length + 1 })}</Text>
              <View style={styles.limitOptionRow}>
                {GROUP_MEMBER_LIMIT_OPTIONS.map((option) => {
                  const active = groupMemberLimit === option;
                  return (
                    <Pressable
                      key={`group-member-limit-${option}`}
                      style={[styles.limitOptionChip, active && styles.limitOptionChipActive]}
                      onPress={() => {
                        setGroupMemberLimit(option);
                        setError('');
                      }}
                    >
                      <Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{getFeatureUiText('chat.list.fixedMembers', { n: option })}</Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            <Pressable style={styles.policyRow} onPress={() => setAllowMemberInvites((prev) => !prev)}>
              <View style={[styles.policyCheck, allowMemberInvites && styles.policyCheckActive]}>
                <Text style={styles.policyCheckText}>{allowMemberInvites ? '✓' : ''}</Text>
              </View>
              <View style={styles.policyTextWrap}>
                <Text style={styles.policyTitle}>{getFeatureUiText('chat.list.memberInviteTitle')}</Text>
                <Text style={styles.policyMeta}>{getFeatureUiText('chat.list.memberInviteMeta')}</Text>
              </View>
            </Pressable>
            <View style={styles.memberPickWrap}>
              {friends.length === 0 ? (
                <Text style={styles.emptyText}>{getFeatureUiText('chat.list.noFriendsForGroup')}</Text>
              ) : (
                friends.map((friend) => {
                  const { friendUserId } = friend;
                  const active = !!friendUserId && selectedGroupMemberIds.includes(friendUserId);
                  return (
                    <Pressable
                      key={`group-friend-${friend.id}`}
                      style={[styles.memberChip, active && styles.memberChipActive]}
                      onPress={() => toggleGroupMember(friendUserId)}
                    >
                      <Text style={[styles.memberChipText, active && styles.memberChipTextActive]}>
                        {friend.friendCountryFlag || '🌐'} {friend.friendUsername || friend.friendEmail}
                      </Text>
                    </Pressable>
                  );
                })
              )}
            </View>
            <Pressable
              style={[styles.primaryButton, busyAction === 'group-room' && styles.disabledButton]}
              onPress={() => { void handleCreateGroupRoom(); }}
              disabled={busyAction === 'group-room'}
            >
              <Text style={styles.primaryButtonText}>{busyAction === 'group-room' ? getFeatureUiText('chat.list.creatingGroup') : getFeatureUiText('chat.list.openGroup')}</Text>
            </Pressable>
          </View>
        ) : null}

        {/* [단일 통로] 채팅 진입 즉시 등록 친구목록을 화면 안에 나열 → 탭하면 바로 1:1 번역 채팅 시작.
            (별도 모달/허브를 거치지 않는다. 보이스톡도 같은 행에서 바로 연결.) */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>{getFeatureUiText('chat.list.friendsTitle')}</Text>
          {friends.length === 0 ? (
            <Text style={styles.emptyText}>{getFeatureUiText('chat.list.noFriends')}</Text>
          ) : (
            friends.map((friend) => {
              const expanded = expandedFriendId === friend.id;
              const label = friend.friendUsername || friend.friendEmail;
              const canVoip = Boolean(friend.friendUserId || friend.friendVoiceId);
              return (
                <View key={`chat-friend-${friend.id}`} style={styles.friendRowBlock}>
                  <Pressable
                    style={styles.friendRowHead}
                    onPress={() => setExpandedFriendId((prev) => (prev === friend.id ? null : friend.id))}
                    accessibilityRole="button"
                    accessibilityLabel={`${label} ${expanded ? '닫기' : '열기'}`}
                  >
                    <View style={styles.friendTextWrap}>
                      <Text style={styles.friendTitle}>{friend.friendCountryFlag || '🌐'} {label}</Text>
                      <Text style={styles.friendMeta}>{getFeatureUiText('chat.directSubtitleAuto')} · {formatPreferredLanguage(friend.friendPreferredLanguage)}</Text>
                    </View>
                    <Text style={styles.friendChevron}>{expanded ? '▾' : '›'}</Text>
                  </Pressable>
                  {expanded ? (
                    <View style={styles.friendActions}>
                      <Pressable
                        style={[styles.friendVoipButton, !canVoip && styles.friendActionDisabled]}
                        disabled={!canVoip || !onStartFriendVoiceCall}
                        onPress={() => { void onStartFriendVoiceCall?.(friend); }}
                        accessibilityRole="button"
                        accessibilityLabel={`통역통화, ${label}`}
                        testID={`worldlinco-friend-voice-call-${friend.friendUserId ?? friend.id}`}
                      >
                        <Text style={styles.friendVoipButtonText}>{getFeatureUiText('chat.list.voipCall')}</Text>
                      </Pressable>
                      <Pressable
                        style={styles.friendChatButton}
                        onPress={() => { void handleOpenDirectRoom(friend); }}
                        disabled={busyAction === `friend-${friend.id}`}
                        accessibilityRole="button"
                        accessibilityLabel={`채팅, ${label}`}
                        testID={`worldlinco-chat-direct-friend-${friend.friendUserId ?? friend.id}`}
                      >
                        <Text style={styles.friendChatButtonText}>{busyAction === `friend-${friend.id}` ? getFeatureUiText('chat.list.opening') : getFeatureUiText('chat.list.chatBtn')}</Text>
                      </Pressable>
                    </View>
                  ) : null}
                </View>
              );
            })
          )}
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>{getFeatureUiText('chat.list.recentRooms')}</Text>
          {rooms.length === 0 ? (
            <Text style={styles.emptyText}>{getFeatureUiText('chat.list.noRooms')}</Text>
          ) : (
            rooms.map((room) => {
              const alertLabel = getRoomAlertLabel(room);
              return (
                <Pressable
                  key={`chat-room-${room.room_id}`}
                  style={styles.roomCard}
                  onPress={() => onOpenRoom(room)}
                  accessibilityRole="button"
                  accessibilityLabel={buildChatRoomSelector(room)}
                  testID={buildChatRoomSelector(room)}
                >
                  <View style={styles.roomHeaderRow}>
                    <View style={styles.roomTitleWrap}>
                      <Text style={styles.roomTitle}>{room.title}</Text>
                      {alertLabel ? (
                        <View style={styles.alertPill}>
                          <Text style={styles.alertPillText}>{alertLabel}</Text>
                        </View>
                      ) : null}
                    </View>
                    {room.unread_count > 0 ? (
                      <View style={styles.unreadBadge}>
                        <Text style={styles.unreadBadgeText}>{room.unread_count}</Text>
                      </View>
                    ) : null}
                  </View>
                  <Text style={styles.roomMeta}>{buildGroupRoomMeta(room)}</Text>
                  {room.room_type === 'direct' ? (
                    <Text style={styles.roomHint}>{buildTranslationHint(room.counterpart?.preferred_language, null)}</Text>
                  ) : null}
                  <Text style={styles.roomPreview}>{room.last_message_preview || getFeatureUiText('chat.list.noMessages')}</Text>
                  <Text style={styles.roomTime}>{formatRoomTime(room.last_message_at)}</Text>
                </Pressable>
              );
            })
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 12 },
  title: { color: '#1a1f36', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#5f6b80', fontSize: 14, lineHeight: 20 },
  summaryCard: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#ffffff',
    padding: 16,
    gap: 6,
  },
  summaryHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  summaryTitle: { color: '#1a1f36', fontSize: 15, fontWeight: '800' },
  summaryMetric: { color: '#1e6fe0', fontSize: 12, fontWeight: '700' },
  summaryRoomHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  summaryRoomTitle: { color: '#1a1f36', fontSize: 14, fontWeight: '700' },
  summaryPreview: { color: '#3a4356', fontSize: 13, lineHeight: 18 },
  summaryMeta: { color: '#5f6b80', fontSize: 12 },
  alertPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#bcd3f0',
    backgroundColor: '#e8f1ff',
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  alertPillText: { color: '#1e6fe0', fontSize: 11, fontWeight: '800' },
  quickRow: { flexDirection: 'row', gap: 10 },
  primaryButton: {
    flex: 1,
    backgroundColor: '#1f6feb',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#ffffff', fontWeight: '700' },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#ffffff',
  },
  secondaryButtonText: { color: '#3a4356', fontWeight: '700' },
  disabledButton: { opacity: 0.7 },
  errorText: { color: '#e5484d', fontSize: 13 },
  loader: { marginTop: 4 },
  scrollContent: { gap: 12, paddingBottom: 12 },
  sectionCard: {
    backgroundColor: '#ffffff',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dce6f2',
    padding: 14,
    gap: 10,
  },
  sectionTitle: { color: '#1a1f36', fontSize: 16, fontWeight: '800' },
  emptyText: { color: '#5f6b80', fontSize: 13, lineHeight: 19 },
  groupInput: {
    color: '#1a1f36',
    backgroundColor: '#f4f9ff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#dce6f2',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  limitSection: { gap: 8 },
  capacityMeta: { color: '#5f6b80', fontSize: 12, lineHeight: 18 },
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
  memberPickWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  policyRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#f4f9ff',
    padding: 12,
  },
  policyCheck: {
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
  policyCheckActive: { backgroundColor: '#1f6feb', borderColor: '#1e6fe0' },
  policyCheckText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  policyTextWrap: { flex: 1, gap: 3 },
  policyTitle: { color: '#1a1f36', fontSize: 13, fontWeight: '700' },
  policyMeta: { color: '#5f6b80', fontSize: 12, lineHeight: 18 },
  memberChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#dce6f2',
    backgroundColor: '#f4f9ff',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  memberChipActive: { backgroundColor: '#e3f0ff', borderColor: '#1e6fe0' },
  memberChipText: { color: '#3a4356', fontSize: 12, fontWeight: '700' },
  memberChipTextActive: { color: '#1e6fe0' },
  friendRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  friendRowBlock: { borderBottomWidth: 1, borderBottomColor: '#e3eaf5', paddingVertical: 4 },
  friendRowHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10 },
  friendChevron: { color: '#8a93a3', fontSize: 18, fontWeight: '700', paddingLeft: 8 },
  friendActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingBottom: 10 },
  friendActionDisabled: { opacity: 0.45 },
  friendTextWrap: { flex: 1, gap: 2 },
  friendTitle: { color: '#1a1f36', fontSize: 14, fontWeight: '700' },
  friendMeta: { color: '#5f6b80', fontSize: 12 },
  friendHint: { color: '#1e6fe0', fontSize: 11, lineHeight: 16 },
  friendActionColumn: { gap: 8, alignItems: 'stretch' },
  friendVoipButton: {
    flexGrow: 1,
    flexBasis: '47%',
    borderRadius: 9,
    paddingVertical: 11,
    alignItems: 'center',
    backgroundColor: '#2563eb',
  },
  friendVoipButtonText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  friendVoiceButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#1f6f43',
  },
  friendVoiceButtonText: { color: '#d2f4de', fontWeight: '800' },
  friendChatButton: {
    flexGrow: 1,
    flexBasis: '47%',
    borderRadius: 9,
    paddingVertical: 11,
    alignItems: 'center',
    backgroundColor: '#7c3aed',
  },
  friendChatButtonText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  roomCard: {
    gap: 5,
    padding: 12,
    borderRadius: 14,
    backgroundColor: '#f4f9ff',
    borderWidth: 1,
    borderColor: '#dce6f2',
  },
  roomHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  roomTitleWrap: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  roomTitle: { color: '#1a1f36', fontSize: 15, fontWeight: '800', flex: 1 },
  unreadBadge: {
    minWidth: 24,
    height: 24,
    paddingHorizontal: 6,
    borderRadius: 999,
    backgroundColor: '#1f6feb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  unreadBadgeText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  roomMeta: { color: '#5f6b80', fontSize: 12 },
  roomHint: { color: '#1e6fe0', fontSize: 11 },
  roomPreview: { color: '#3a4356', fontSize: 13, lineHeight: 18 },
  roomTime: { color: '#8a93a3', fontSize: 11 },
});