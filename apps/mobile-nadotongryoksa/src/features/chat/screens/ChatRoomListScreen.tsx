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

const GROUP_MEMBER_LIMIT_OPTIONS = [3, 5, 10] as const;

function formatPreferredLanguage(language?: string | null): string {
  const normalized = language?.trim();
  return normalized ? normalized.toUpperCase() : '미설정';
}

function buildTranslationHint(language?: string | null, countryCode?: string | null): string {
  const normalizedLanguage = language?.trim();
  if (normalizedLanguage) {
    return `상대 지정 언어 ${normalizedLanguage.toUpperCase()} 자동 번역`;
  }

  const normalizedCountry = countryCode?.trim().toUpperCase();
  return normalizedCountry
    ? `상대 지정 언어 미설정 · 가입 국가 ${normalizedCountry} fallback`
    : '상대 지정 언어 미설정 · 가입 국가 fallback 대기';
}

function getRoomAlertLabel(room: ChatRoomSummary): string | null {
  if (room.last_message_type === 'system_invite') {
    return '그룹 초대';
  }
  if (room.last_message_type === 'translation' || room.last_message_type === 'ocr' || room.last_message_type === 'song_translation') {
    return '번역 결과 도착';
  }
  if (room.unread_count > 0) {
    return '새 메시지';
  }
  return null;
}

function buildChatRoomSelector(room: ChatRoomSummary): string {
  return `worldlinco-chat-room-${room.room_id}`;
}

function buildGroupRoomMeta(room: ChatRoomSummary): string {
  if (room.room_type === 'direct') {
    return '1:1 대화';
  }
  const memberLimit = room.member_limit ?? 10;
  return `${room.member_count}명 참여 · 정원 ${memberLimit}명 고정`;
}

interface Props {
  apiBaseUrl: string;
  token: string;
  userId: number;
  visible?: boolean;
  refreshKey?: number;
  onOpenRoom: (room: ChatRoomSummary) => void;
  autoCallVoiceId?: string | null;
  onAutoCallConsumed?: () => void;
  onStartFriendVoiceCall?: (friend: Friend) => void | Promise<void>;
}

export function ChatRoomListScreen({
  apiBaseUrl,
  token,
  userId,
  visible = true,
  refreshKey = 0,
  onOpenRoom,
  autoCallVoiceId = null,
  onAutoCallConsumed,
  onStartFriendVoiceCall,
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
  const autoCallKeyRef = useRef<string | null>(null);
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
      setError(e instanceof Error ? e.message : '채팅방 목록을 불러오지 못했습니다.');
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
      setError(e instanceof Error ? e.message : '번역 보관함을 열지 못했습니다.');
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
      setError(e instanceof Error ? e.message : '친구 채팅방을 열지 못했습니다.');
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
        setError(`정원 ${groupMemberLimit}명 방은 방장을 포함해 최대 ${groupMemberLimit}명까지만 입장할 수 있습니다.`);
        return prev;
      }
      return [...prev, friendUserId];
    });
  }, [groupMemberLimit, maxSelectableMembers]);

  const handleCreateGroupRoom = useCallback(async () => {
    const title = groupTitle.trim();
    if (!title) {
      setError('그룹방 이름을 입력해야 합니다.');
      return;
    }
    if (selectedGroupMemberIds.length === 0) {
      setError('초대할 친구를 한 명 이상 선택해야 합니다.');
      return;
    }
    if (selectedGroupMemberIds.length + 1 > groupMemberLimit) {
      setError(`현재 선택 인원은 정원 ${groupMemberLimit}명을 초과합니다.`);
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
      setError(e instanceof Error ? e.message : '그룹방을 만들지 못했습니다.');
    } finally {
      setBusyAction('');
    }
  }, [allowMemberInvites, apiBaseUrl, groupMemberLimit, groupTitle, onOpenRoom, selectedGroupMemberIds, token]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>채팅</Text>
      <Text style={styles.subtitle}>번역 결과를 보관하고, 친구와 1:1 또는 그룹 대화를 시작할 수 있습니다.</Text>
      <View style={styles.summaryCard}>
        <View style={styles.summaryHeaderRow}>
          <Text style={styles.summaryTitle}>채팅 알림 요약</Text>
          <Text style={styles.summaryMetric}>{unreadRoomCount}개 방 · {unreadMessageCount}개 미확인</Text>
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
            <Text style={styles.summaryPreview}>{latestRoom.last_message_preview || '최근 메시지 미리보기가 없습니다.'}</Text>
            <Text style={styles.summaryMeta}>{latestRoom.last_message_at || '최근 수신 시각 없음'}</Text>
          </>
        ) : (
          <Text style={styles.summaryPreview}>아직 채팅 알림 정보가 없습니다. 번역 보관함이나 친구 채팅을 열면 최근 대화와 미확인 수가 여기에 쌓입니다.</Text>
        )}
      </View>
      <View style={styles.quickRow}>
        <Pressable style={styles.primaryButton} onPress={() => { void handleOpenSelfRoom(); }} disabled={busyAction === 'self-room'}>
          <Text style={styles.primaryButtonText}>{busyAction === 'self-room' ? '열는 중...' : '번역 보관함 열기'}</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => setShowGroupComposer((prev) => !prev)}>
          <Text style={styles.secondaryButtonText}>{showGroupComposer ? '그룹방 닫기' : '그룹방 만들기'}</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => { void load(); }} disabled={loading}>
          <Text style={styles.secondaryButtonText}>{loading ? '새로고침 중...' : '새로고침'}</Text>
        </Pressable>
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {loading ? <ActivityIndicator color="#79c0ff" style={styles.loader} /> : null}

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {showGroupComposer ? (
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>그룹방 만들기</Text>
            <Text style={styles.emptyText}>친구를 골라 번역 채팅방을 바로 열 수 있습니다.</Text>
            <TextInput
              style={styles.groupInput}
              placeholder="예: 일본 여행 통역방"
              placeholderTextColor="#6e7681"
              value={groupTitle}
              onChangeText={setGroupTitle}
            />
            <View style={styles.limitSection}>
              <Text style={styles.policyTitle}>방 정원 선택</Text>
              <Text style={styles.capacityMeta}>방장 포함 기준으로 3명, 5명, 10명 고정방을 만들 수 있습니다. 현재 {selectedGroupMemberIds.length + 1}명 입장 예정</Text>
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
                      <Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{option}명 고정</Text>
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
                <Text style={styles.policyTitle}>멤버도 초대 가능</Text>
                <Text style={styles.policyMeta}>끄면 owner만 초대할 수 있고, 켜면 기존 멤버도 새 친구를 초대할 수 있습니다.</Text>
              </View>
            </Pressable>
            <View style={styles.memberPickWrap}>
              {friends.length === 0 ? (
                <Text style={styles.emptyText}>먼저 친구를 추가해야 그룹방을 만들 수 있습니다.</Text>
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
              <Text style={styles.primaryButtonText}>{busyAction === 'group-room' ? '그룹방 생성 중...' : '선택 멤버로 그룹방 열기'}</Text>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>빠른 시작</Text>
          {friends.length === 0 ? (
            <Text style={styles.emptyText}>앱 친구를 추가하면 여기서 바로 상대 지정 언어 기준 1:1 채팅을 열 수 있습니다.</Text>
          ) : (
            friends.slice(0, 6).map((friend) => (
              <View key={`chat-friend-${friend.id}`} style={styles.friendRow}>
                <View style={styles.friendTextWrap}>
                  <Text style={styles.friendTitle}>{friend.friendCountryFlag || '🌐'} {friend.friendUsername || friend.friendEmail}</Text>
                  <Text style={styles.friendMeta}>지정 언어 {formatPreferredLanguage(friend.friendPreferredLanguage)} · {friend.friendVoiceId || 'voice id 없음'}</Text>
                  <Text style={styles.friendHint}>{buildTranslationHint(friend.friendPreferredLanguage, friend.friendCountryCode)}</Text>
                </View>
                <View style={styles.friendActionColumn}>
                  <Pressable
                    style={styles.friendVoiceButton}
                    onPress={() => { void onStartFriendVoiceCall?.(friend); }}
                    disabled={!onStartFriendVoiceCall}
                    accessibilityRole="button"
                    accessibilityLabel={`보이스톡 걸기, ${friend.friendVoiceId || friend.friendUserId || friend.friendEmail || friend.id}`}
                    testID={`worldlinco-friend-voice-call-${friend.friendUserId ?? friend.id}`}
                  >
                    <Text style={styles.friendVoiceButtonText}>보이스톡</Text>
                  </Pressable>
                  <Pressable
                    style={styles.friendChatButton}
                    onPress={() => { void handleOpenDirectRoom(friend); }}
                    disabled={busyAction === `friend-${friend.id}`}
                    accessibilityRole="button"
                    accessibilityLabel={`worldlinco-chat-direct-friend-${friend.friendUserId ?? friend.id}`}
                    testID={`worldlinco-chat-direct-friend-${friend.friendUserId ?? friend.id}`}
                  >
                    <Text style={styles.friendChatButtonText}>{busyAction === `friend-${friend.id}` ? '여는 중...' : '채팅'}</Text>
                  </Pressable>
                </View>
              </View>
            ))
          )}
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>최근 대화방</Text>
          {rooms.length === 0 ? (
            <Text style={styles.emptyText}>아직 생성된 채팅방이 없습니다. 번역 보관함 또는 친구 채팅부터 시작하세요.</Text>
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
                  <Text style={styles.roomPreview}>{room.last_message_preview || '메시지가 아직 없습니다.'}</Text>
                  <Text style={styles.roomTime}>{room.last_message_at || ''}</Text>
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
  title: { color: '#f0f6fc', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#8b949e', fontSize: 14, lineHeight: 20 },
  summaryCard: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#243042',
    backgroundColor: '#0f172a',
    padding: 16,
    gap: 6,
  },
  summaryHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  summaryTitle: { color: '#f8fafc', fontSize: 15, fontWeight: '800' },
  summaryMetric: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
  summaryRoomHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  summaryRoomTitle: { color: '#e6edf3', fontSize: 14, fontWeight: '700' },
  summaryPreview: { color: '#c9d1d9', fontSize: 13, lineHeight: 18 },
  summaryMeta: { color: '#8b949e', fontSize: 12 },
  alertPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#35506c',
    backgroundColor: '#10253d',
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  alertPillText: { color: '#79c0ff', fontSize: 11, fontWeight: '800' },
  quickRow: { flexDirection: 'row', gap: 10 },
  primaryButton: {
    flex: 1,
    backgroundColor: '#1f6feb',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#f0f6fc', fontWeight: '700' },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#2f3b4b',
    backgroundColor: '#111827',
  },
  secondaryButtonText: { color: '#c9d1d9', fontWeight: '700' },
  disabledButton: { opacity: 0.7 },
  errorText: { color: '#ff7b72', fontSize: 13 },
  loader: { marginTop: 4 },
  scrollContent: { gap: 12, paddingBottom: 12 },
  sectionCard: {
    backgroundColor: '#111827',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1f2a37',
    padding: 14,
    gap: 10,
  },
  sectionTitle: { color: '#f0f6fc', fontSize: 16, fontWeight: '800' },
  emptyText: { color: '#8b949e', fontSize: 13, lineHeight: 19 },
  groupInput: {
    color: '#f0f6fc',
    backgroundColor: '#0f1723',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#243244',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  limitSection: { gap: 8 },
  capacityMeta: { color: '#8b949e', fontSize: 12, lineHeight: 18 },
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
  memberPickWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  policyRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#0f1723',
    padding: 12,
  },
  policyCheck: {
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
  policyCheckActive: { backgroundColor: '#1f6feb', borderColor: '#79c0ff' },
  policyCheckText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  policyTextWrap: { flex: 1, gap: 3 },
  policyTitle: { color: '#f0f6fc', fontSize: 13, fontWeight: '700' },
  policyMeta: { color: '#8b949e', fontSize: 12, lineHeight: 18 },
  memberChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#243244',
    backgroundColor: '#0f1723',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  memberChipActive: { backgroundColor: '#17324d', borderColor: '#79c0ff' },
  memberChipText: { color: '#c9d1d9', fontSize: 12, fontWeight: '700' },
  memberChipTextActive: { color: '#79c0ff' },
  friendRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  friendTextWrap: { flex: 1, gap: 2 },
  friendTitle: { color: '#f0f6fc', fontSize: 14, fontWeight: '700' },
  friendMeta: { color: '#8b949e', fontSize: 12 },
  friendHint: { color: '#7dd3fc', fontSize: 11, lineHeight: 16 },
  friendActionColumn: { gap: 8, alignItems: 'stretch' },
  friendVoiceButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#1f6f43',
  },
  friendVoiceButtonText: { color: '#d2f4de', fontWeight: '800' },
  friendChatButton: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#17324d',
  },
  friendChatButtonText: { color: '#79c0ff', fontWeight: '700' },
  roomCard: {
    gap: 5,
    padding: 12,
    borderRadius: 14,
    backgroundColor: '#0f1723',
    borderWidth: 1,
    borderColor: '#243244',
  },
  roomHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  roomTitleWrap: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  roomTitle: { color: '#f0f6fc', fontSize: 15, fontWeight: '800', flex: 1 },
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
  roomMeta: { color: '#8b949e', fontSize: 12 },
  roomHint: { color: '#7dd3fc', fontSize: 11 },
  roomPreview: { color: '#d1d7de', fontSize: 13, lineHeight: 18 },
  roomTime: { color: '#6e7681', fontSize: 11 },
});