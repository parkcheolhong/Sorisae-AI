import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  type LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  confirmFriendInvite,
  getFriends,
  getOutgoingFriendRequests,
  getRecentMissedVoipCalls,
  removeFriend,
  requestFriendInviteCode,
} from '../../api/friends';
import type { Friend, MissedVoipCall, OutgoingFriendRequestItem } from './types';

function formatPreferredLanguage(language?: string | null): string {
  const normalized = language?.trim();
  return normalized ? normalized.toUpperCase() : '미설정';
}

function buildTranslationContract(friend: Friend): string {
  const normalizedLanguage = friend.friendPreferredLanguage?.trim();
  if (normalizedLanguage) {
    return `채팅/통화 시 상대 지정 언어 ${normalizedLanguage.toUpperCase()} 기준 자동 통번역`;
  }

  const normalizedCountry = friend.friendCountryCode?.trim().toUpperCase();
  return normalizedCountry
    ? `상대 지정 언어 미설정 · 가입 국가 ${normalizedCountry} fallback`
    : '상대 지정 언어 미설정 · 가입 국가 fallback 대기';
}

interface Props {
  userId: number;
  token: string;
  currentUserEmail?: string;
  visible?: boolean;
  embeddedInScrollView?: boolean;
  autoCallVoiceId?: string | null;
  onAutoCallConsumed?: () => void;
  onFriendSelected?: (friend: Friend) => void;
}

function logFriendFolderDiag(event: string, payload: Record<string, unknown>) {
  console.log('[FRIEND_FOLDER_DIAG]', JSON.stringify({ event, ...payload }));
}

export function FriendFolderScreen({ userId, token, currentUserEmail, visible = true, embeddedInScrollView = false, autoCallVoiceId = null, onAutoCallConsumed, onFriendSelected }: Props) {
  const { width: windowWidth } = useWindowDimensions();
  const isNarrowWidth = windowWidth < 380;
  const normalizedToken = token?.trim() ?? '';
  const [friends, setFriends] = useState<Friend[]>([]);
  const [friendTotal, setFriendTotal] = useState(0);
  const [outgoingRequests, setOutgoingRequests] = useState<OutgoingFriendRequestItem[]>([]);
  const [missedCalls, setMissedCalls] = useState<MissedVoipCall[]>([]);
  const [loading, setLoading] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [verificationChannel, setVerificationChannel] = useState<'email' | 'phone'>('email');
  const [inviteStep, setInviteStep] = useState<'form' | 'verify'>('form');
  const [inviteSessionToken, setInviteSessionToken] = useState('');
  const [maskedTarget, setMaskedTarget] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [addLoading, setAddLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastLayoutLogRef = useRef<Record<string, string>>({});
  const autoCallAttemptedRef = useRef<string | null>(null);

  const logLayoutMetric = useCallback((key: string, payload: Record<string, unknown>) => {
    const serialized = JSON.stringify(payload);
    if (lastLayoutLogRef.current[key] === serialized) {
      return;
    }
    lastLayoutLogRef.current[key] = serialized;
    logFriendFolderDiag(key, payload);
  }, []);

  const handleMeasuredLayout = useCallback((key: string, extra: Record<string, unknown> = {}) => {
    return (event: LayoutChangeEvent) => {
      const { width, height, x, y } = event.nativeEvent.layout;
      logLayoutMetric(key, {
        user_id: userId,
        visible,
        narrow: isNarrowWidth,
        width,
        height,
        x,
        y,
        ...extra,
      });
    };
  }, [isNarrowWidth, logLayoutMetric, userId, visible]);

  const load = useCallback(async () => {
    if (!normalizedToken) {
      setLoading(false);
      setError(null);
      setOutgoingRequests([]);
      setMissedCalls([]);
      logFriendFolderDiag('skip_load_missing_token', {
        user_id: userId,
        visible,
      });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [data, outgoing] = await Promise.all([
        getFriends(userId, normalizedToken),
        getOutgoingFriendRequests(normalizedToken),
      ]);
      setFriends(data.friends);
      setFriendTotal(data.total);
      setOutgoingRequests(outgoing.requests);

      try {
        const missed = await getRecentMissedVoipCalls(normalizedToken);
        setMissedCalls(missed);
      } catch (e: unknown) {
        setMissedCalls([]);
        setError((previousError) => previousError ?? (e instanceof Error ? e.message : '부재중 통화를 불러올 수 없습니다.'));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '친구 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [normalizedToken, userId, visible]);

  useEffect(() => {
    if (!visible) {
      autoCallAttemptedRef.current = null;
      return;
    }
    if (!normalizedToken) {
      return;
    }
    void load();
  }, [load, normalizedToken, visible]);

  useEffect(() => {
    const normalizedTarget = autoCallVoiceId?.trim().toLowerCase();
    if (!visible || !normalizedTarget || loading || !onFriendSelected) {
      return;
    }
    if (autoCallAttemptedRef.current === normalizedTarget) {
      return;
    }

    const matchedFriend = friends.find((friend) => {
      const voiceId = friend.friendVoiceId?.trim().toLowerCase();
      return voiceId === normalizedTarget || voiceId?.includes(normalizedTarget) === true;
    });
    if (!matchedFriend) {
      return;
    }

    autoCallAttemptedRef.current = normalizedTarget;
    logFriendFolderDiag('auto_call_voice_id', {
      user_id: userId,
      voice_id: autoCallVoiceId,
      friend_id: matchedFriend.id,
      friend_voice_id: matchedFriend.friendVoiceId ?? null,
    });
    onAutoCallConsumed?.();
    onFriendSelected(matchedFriend);
  }, [autoCallVoiceId, friends, loading, onAutoCallConsumed, onFriendSelected, userId, visible]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    logFriendFolderDiag('data_snapshot', {
      user_id: userId,
      visible,
      narrow: isNarrowWidth,
      window_width: windowWidth,
      friend_total: friendTotal,
      friends_length: friends.length,
      friend_ids: friends.map((friend) => friend.id),
      friend_user_ids: friends.map((friend) => friend.friendUserId),
      friend_voice_ids: friends.map((friend) => friend.friendVoiceId ?? null),
      friend_emails: friends.map((friend) => friend.friendEmail),
      outgoing_total: outgoingRequests.length,
      missed_total: missedCalls.length,
      loading,
      error,
    });
  }, [error, friendTotal, friends, isNarrowWidth, loading, missedCalls.length, outgoingRequests.length, userId, visible, windowWidth]);

  const resetInviteForm = useCallback(() => {
    setInviteStep('form');
    setInviteSessionToken('');
    setMaskedTarget('');
    setOtpCode('');
    setDisplayName('');
    setEmail('');
    setPhone('');
    setVerificationChannel('email');
  }, []);

  const handleRequestInviteCode = useCallback(async () => {
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedName = displayName.trim();
    const trimmedPhone = phone.trim();
    if (!trimmedEmail) {
      setError('친구 이메일을 입력해 주세요.');
      return;
    }
    if (!trimmedEmail.includes('@')) {
      setError('올바른 이메일 형식을 입력해 주세요.');
      return;
    }
    if (verificationChannel === 'phone' && !trimmedPhone) {
      setError('전화 인증을 선택한 경우 연락처를 입력해 주세요.');
      return;
    }
    setAddLoading(true);
    setError(null);
    try {
      const response = await requestFriendInviteCode({
        targetEmail: trimmedEmail,
        displayName: trimmedName || undefined,
        phoneNumber: trimmedPhone || undefined,
        verificationChannel,
      }, token);
      setInviteSessionToken(response.sessionToken);
      setMaskedTarget(response.maskedTarget);
      if (response.devOtpHint) {
        setOtpCode(response.devOtpHint);
      }
      setInviteStep('verify');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '인증 코드 요청에 실패했습니다.');
    } finally {
      setAddLoading(false);
    }
  }, [displayName, email, phone, token, verificationChannel]);

  const handleConfirmInvite = useCallback(async () => {
    const trimmedOtp = otpCode.trim();
    if (!inviteSessionToken || trimmedOtp.length < 6) {
      setError('6자리 인증 코드를 입력해 주세요.');
      return;
    }
    setAddLoading(true);
    setError(null);
    try {
      await confirmFriendInvite({
        inviteSessionToken,
        verificationCode: trimmedOtp,
      }, token);
      resetInviteForm();
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '친구 인증 확인에 실패했습니다.');
    } finally {
      setAddLoading(false);
    }
  }, [inviteSessionToken, load, otpCode, resetInviteForm, token]);

  const handleRemove = useCallback((friend: Friend) => {
    Alert.alert(
      '친구 삭제',
      `${friend.friendUsername || friend.friendEmail}을(를) 친구 목록에서 삭제할까요?`,
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              await removeFriend(friend.id, token);
              await load();
            } catch (e: unknown) {
              Alert.alert('오류', e instanceof Error ? e.message : '삭제 실패');
            }
          },
        },
      ],
    );
  }, [token, load]);

  const renderHeaderContent = useCallback(() => (
    <>
      {outgoingRequests.length ? (
        <View style={styles.pendingSection}>
          <Text style={styles.pendingTitle}>보낸 요청</Text>
          {outgoingRequests.map((request) => (
            <View key={request.requestId} style={styles.pendingRow}>
              <Text style={styles.pendingName}>
                {(request.receiverCountryFlag || '🌐').trim()} {request.receiverNickname}
              </Text>
              <Text style={styles.pendingMeta}>
                {request.receiverCountryCode || '국가 미상'} · {request.receiverGender || 'unknown'} · 상태 요청 보냄
              </Text>
              <Text style={styles.pendingMeta}>
                보이스 ID {request.receiverVoiceId || '없음'}
              </Text>
              <Text style={styles.pendingMeta}>{request.createdAt}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {missedCalls.length ? (
        <View style={styles.missedSection}>
          <Text style={styles.missedTitle}>부재중 보이스톡</Text>
          {missedCalls.slice(0, 5).map((item) => (
            <View key={`${item.callId}-${item.id}`} style={styles.missedRow}>
              <Text style={styles.missedCaller}>{item.callerLabel}</Text>
              <Text style={styles.missedMeta}>
                {(item.callerPreferredLanguage || 'unknown').toUpperCase()} · {item.callerCountryCode || '국가 미상'}
              </Text>
              <Text style={styles.missedMeta}>{item.createdAt}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </>
  ), [missedCalls, outgoingRequests]);

  const renderFriendRow = useCallback((item: Friend) => {
    const canStartVoiceCall = Boolean(item.friendUserId || item.friendVoiceId);
    const handlePressVoiceCall = () => {
      if (!canStartVoiceCall) {
        Alert.alert('ID 연결 필요', '보이스톡은 앱 보이스 ID 또는 사용자 ID가 있는 대상만 연결할 수 있습니다.');
        return;
      }
      if (onFriendSelected) {
        onFriendSelected(item);
      }
    };

    return (
      <View
        key={`friend-row-${item.id}`}
        style={[styles.friendRow, isNarrowWidth && styles.friendRowCompact]}
        onLayout={handleMeasuredLayout('friend_row_layout', {
          friend_id: item.id,
          friend_user_id: item.friendUserId,
          friend_email: item.friendEmail,
          friend_voice_id: item.friendVoiceId ?? null,
        })}
      >
        <View
          style={[styles.friendInfo, isNarrowWidth && styles.friendInfoCompact]}
          onLayout={handleMeasuredLayout('friend_info_layout', {
            friend_id: item.id,
            friend_user_id: item.friendUserId,
            friend_email: item.friendEmail,
            friend_voice_id: item.friendVoiceId ?? null,
          })}
        >
          <Text style={styles.friendName}>{item.friendUsername || item.friendEmail.split('@')[0]}</Text>
          <Text style={styles.friendEmail}>{item.friendEmail}</Text>
          {item.friendPhone ? (
            <Text style={styles.friendPhone}>📞 {item.friendPhone}</Text>
          ) : (
            <Text style={styles.friendPhoneEmpty}>📞 번호 없음</Text>
          )}
          {item.friendVoiceId ? (
            <Text style={styles.friendVoiceId}>보이스 ID {item.friendVoiceId}</Text>
          ) : (
            <Text style={styles.friendPhoneEmpty}>보이스 ID 없음</Text>
          )}
          {(item.friendPreferredLanguage || item.friendGender || item.friendCountryCode) ? (
            <Text style={styles.friendMeta}>
              지정 언어 {formatPreferredLanguage(item.friendPreferredLanguage)}
              {' · '}
              {(item.friendCountryFlag || (item.friendCountryCode ? '🌐' : '')).trim()} {item.friendCountryCode || '국가 미상'}
              {' · '}
              {item.friendGender || 'unknown'}
            </Text>
          ) : null}
          <Text style={styles.friendContract}>{buildTranslationContract(item)}</Text>
        </View>
        <View style={[styles.friendActions, isNarrowWidth && styles.friendActionsCompact]}>
          <Pressable
            style={[styles.voiceCallBtn, !canStartVoiceCall && styles.voiceCallBtnDisabled, isNarrowWidth && styles.friendActionBtnCompact]}
            onPress={handlePressVoiceCall}
            disabled={!canStartVoiceCall}
            accessibilityRole="button"
            accessibilityLabel={`보이스톡 걸기, ${item.friendUsername || item.friendEmail}`}
            testID={item.friendVoiceId ? `worldlinco-friend-voice-call-${item.friendVoiceId}` : undefined}
          >
            <Text style={[styles.voiceCallBtnText, !canStartVoiceCall && styles.voiceCallBtnTextDisabled]}>보이스톡 걸기</Text>
          </Pressable>
          <Pressable
            style={[styles.removeBtn, isNarrowWidth && styles.friendActionBtnCompact]}
            onPress={() => handleRemove(item)}
            accessibilityRole="button"
            accessibilityLabel={`친구 삭제, ${item.friendUsername || item.friendEmail}`}
          >
            <Text style={styles.removeBtnText}>삭제</Text>
          </Pressable>
        </View>
      </View>
    );
  }, [handleMeasuredLayout, handleRemove, isNarrowWidth, onFriendSelected]);

  return (
    <View style={[styles.container, isNarrowWidth && styles.containerCompact]} onLayout={handleMeasuredLayout('container_layout')}>
      <Text style={styles.title}>👥 내 친구 목록</Text>
      <View style={styles.summaryCard}>
        <Text style={styles.summaryText}>조회 계정: {currentUserEmail || '알 수 없음'}</Text>
        <Text style={styles.summaryText}>사용자 ID: {userId}</Text>
        <Text style={styles.summaryText}>친구 수: {friendTotal}</Text>
      </View>

      <View style={styles.manualSection}>
        <Text style={styles.manualTitle}>✏️ 수기 등록 (OTP 인증 필수)</Text>
        <Text style={styles.manualHint}>
          베타·실전 모두 이메일 또는 전화 OTP 확인 후 친구가 등록됩니다.
          앱 가입 계정은 이메일 인증만으로 연결됩니다.
        </Text>
        {inviteStep === 'form' ? (
          <>
            <View style={styles.channelRow}>
              <Pressable
                style={[styles.channelBtn, verificationChannel === 'email' && styles.channelBtnActive]}
                onPress={() => setVerificationChannel('email')}
              >
                <Text style={styles.channelBtnText}>이메일 인증</Text>
              </Pressable>
              <Pressable
                style={[styles.channelBtn, verificationChannel === 'phone' && styles.channelBtnActive]}
                onPress={() => setVerificationChannel('phone')}
              >
                <Text style={styles.channelBtnText}>전화 인증</Text>
              </Pressable>
            </View>
            <TextInput
              style={styles.inputFull}
              placeholder="이름 (표시용, 예: 홍길동)"
              placeholderTextColor="#888"
              value={displayName}
              onChangeText={setDisplayName}
              autoCapitalize="words"
              editable={!addLoading}
              testID="friend-manual-display-name"
            />
            <TextInput
              style={styles.inputFull}
              placeholder="이메일 (필수, 예: friend@example.com)"
              placeholderTextColor="#888"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              editable={!addLoading}
              testID="friend-manual-email"
            />
            <TextInput
              style={styles.inputFull}
              placeholder={verificationChannel === 'phone' ? '연락처 (전화 인증 필수)' : '연락처 (미가입 시 권장)'}
              placeholderTextColor="#888"
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              editable={!addLoading}
              testID="friend-manual-phone"
            />
            <Pressable
              style={[styles.addBtnFull, addLoading && styles.addBtnDisabled]}
              onPress={() => { void handleRequestInviteCode(); }}
              disabled={addLoading}
              testID="friend-manual-request-otp"
            >
              <Text style={styles.addBtnText}>{addLoading ? '요청 중...' : '인증 코드 받기'}</Text>
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.verifyHint}>
              {maskedTarget} 으로 인증 코드를 보냈습니다. 6자리 코드를 입력해 주세요.
            </Text>
            <TextInput
              style={styles.inputFull}
              placeholder="6자리 인증 코드"
              placeholderTextColor="#888"
              value={otpCode}
              onChangeText={setOtpCode}
              keyboardType="number-pad"
              maxLength={6}
              editable={!addLoading}
              testID="friend-manual-otp"
            />
            <Pressable
              style={[styles.addBtnFull, addLoading && styles.addBtnDisabled]}
              onPress={() => { void handleConfirmInvite(); }}
              disabled={addLoading}
              testID="friend-manual-submit"
            >
              <Text style={styles.addBtnText}>{addLoading ? '확인 중...' : '인증 후 친구 등록'}</Text>
            </Pressable>
            <Pressable
              style={styles.backBtn}
              onPress={() => {
                setInviteStep('form');
                setOtpCode('');
                setError(null);
              }}
            >
              <Text style={styles.backBtnText}>입력 다시하기</Text>
            </Pressable>
          </>
        )}
      </View>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {loading ? (
        <ActivityIndicator color="#6ee7b7" style={styles.loader} />
      ) : (
        embeddedInScrollView ? (
          <View
            style={styles.list}
            onLayout={handleMeasuredLayout('embedded_list_layout', { row_count: friends.length })}
          >
            {renderHeaderContent()}
            {friends.length === 0 ? <Text style={styles.emptyText}>친구가 없습니다. 위 수기 등록으로 베타 상대를 추가해 보세요.</Text> : friends.map(renderFriendRow)}
          </View>
        ) : (
          <FlatList
            data={friends}
            keyExtractor={(item) => String(item.id)}
            onLayout={handleMeasuredLayout('flatlist_layout', { row_count: friends.length })}
            onContentSizeChange={(width, height) => {
              logLayoutMetric('flatlist_content_size', {
                user_id: userId,
                visible,
                narrow: isNarrowWidth,
                width,
                height,
                row_count: friends.length,
              });
            }}
            ListHeaderComponent={renderHeaderContent()}
            ListEmptyComponent={<Text style={styles.emptyText}>친구가 없습니다. 위 수기 등록으로 베타 상대를 추가해 보세요.</Text>}
            renderItem={({ item }) => renderFriendRow(item)}
            contentContainerStyle={styles.list}
          />
        )
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0f16',
    padding: 20,
  },
  containerCompact: {
    padding: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#e2e8f0',
    marginBottom: 16,
  },
  summaryCard: {
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#1f2937',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  summaryText: {
    color: '#cbd5e1',
    fontSize: 13,
    marginBottom: 4,
  },
  manualSection: {
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#2563eb',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    gap: 10,
  },
  manualTitle: {
    color: '#93c5fd',
    fontSize: 15,
    fontWeight: '700',
  },
  manualHint: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 18,
  },
  inputFull: {
    backgroundColor: '#1e2533',
    color: '#e2e8f0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  addBtnFull: {
    backgroundColor: '#6ee7b7',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    alignItems: 'center',
  },
  channelRow: {
    flexDirection: 'row',
    gap: 8,
  },
  channelBtn: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#1e2533',
  },
  channelBtnActive: {
    borderColor: '#60a5fa',
    backgroundColor: '#172554',
  },
  channelBtnText: {
    color: '#e2e8f0',
    fontSize: 13,
    fontWeight: '600',
  },
  verifyHint: {
    color: '#cbd5e1',
    fontSize: 13,
    lineHeight: 18,
  },
  backBtn: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  backBtnText: {
    color: '#93c5fd',
    fontSize: 13,
  },
  addRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  addRowCompact: {
    flexWrap: 'wrap',
  },
  input: {
    flex: 1,
    backgroundColor: '#1e2533',
    color: '#e2e8f0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  inputCompact: {
    minWidth: '100%',
  },
  addBtn: {
    backgroundColor: '#6ee7b7',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    justifyContent: 'center',
  },
  addBtnCompact: {
    width: '100%',
    alignItems: 'center',
  },
  addBtnDisabled: {
    opacity: 0.5,
  },
  addBtnText: {
    color: '#0b0f16',
    fontWeight: 'bold',
    fontSize: 13,
  },
  errorText: {
    color: '#f87171',
    fontSize: 13,
    marginBottom: 8,
  },
  loader: {
    marginTop: 24,
  },
  missedSection: {
    backgroundColor: '#161722',
    borderWidth: 1,
    borderColor: '#3a2430',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    gap: 8,
  },
  missedTitle: {
    color: '#fda4af',
    fontSize: 14,
    fontWeight: '700',
  },
  missedRow: {
    backgroundColor: '#20141b',
    borderRadius: 8,
    padding: 10,
  },
  missedCaller: {
    color: '#ffe4e6',
    fontSize: 13,
    fontWeight: '600',
  },
  missedMeta: {
    color: '#fbcfe8',
    fontSize: 12,
    marginTop: 2,
  },
  pendingSection: {
    backgroundColor: '#13202c',
    borderWidth: 1,
    borderColor: '#1d4f73',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    gap: 8,
  },
  pendingTitle: {
    color: '#93c5fd',
    fontSize: 14,
    fontWeight: '700',
  },
  pendingRow: {
    backgroundColor: '#162433',
    borderRadius: 8,
    padding: 10,
  },
  pendingName: {
    color: '#dbeafe',
    fontSize: 13,
    fontWeight: '600',
  },
  pendingMeta: {
    color: '#bfdbfe',
    fontSize: 12,
    marginTop: 2,
  },
  emptyText: {
    color: '#64748b',
    textAlign: 'center',
    marginTop: 32,
    fontSize: 14,
  },
  list: {
    paddingBottom: 16,
  },
  friendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e2533',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  friendRowCompact: {
    flexDirection: 'column',
    alignItems: 'stretch',
  },
  friendInfo: {
    flex: 1,
  },
  friendInfoCompact: {
    flexBasis: '100%',
    width: '100%',
  },
  friendActions: {
    width: 150,
    gap: 8,
    marginLeft: 12,
  },
  friendActionsCompact: {
    width: '100%',
    marginLeft: 0,
    marginTop: 10,
  },
  friendActionBtnCompact: {
    width: '100%',
    alignItems: 'center',
  },
  friendName: {
    color: '#e2e8f0',
    fontWeight: '600',
    fontSize: 14,
  },
  friendEmail: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 2,
  },
  friendPhone: {
    color: '#6ee7b7',
    fontSize: 12,
    marginTop: 2,
  },
  friendVoiceId: {
    color: '#79c0ff',
    fontSize: 12,
    marginTop: 2,
  },
  friendMeta: {
    color: '#cbd5e1',
    fontSize: 12,
    marginTop: 2,
  },
  friendContract: {
    color: '#7dd3fc',
    fontSize: 11,
    lineHeight: 16,
    marginTop: 4,
  },
  friendPhoneEmpty: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 2,
  },
  removeBtn: {
    backgroundColor: '#3f1f1f',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignItems: 'center',
  },
  voiceCallBtn: {
    backgroundColor: '#0d2a4a',
    borderWidth: 1,
    borderColor: '#3b82f6',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 9,
    alignItems: 'center',
  },
  voiceCallBtnDisabled: {
    opacity: 0.45,
    borderColor: '#334155',
    backgroundColor: '#1f2937',
  },
  voiceCallBtnText: {
    color: '#bfdbfe',
    fontSize: 12,
    fontWeight: '800',
  },
  voiceCallBtnTextDisabled: {
    color: '#94a3b8',
  },
  removeBtnText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '600',
  },
});
