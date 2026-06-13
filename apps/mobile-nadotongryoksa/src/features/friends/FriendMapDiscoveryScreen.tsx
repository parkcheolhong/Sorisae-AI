import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import * as Location from 'expo-location';
import {
  acceptFriendRequest,
  createFriendRequest,
  getIncomingFriendRequests,
  getNearbyDiscoveryUsers,
  upsertDiscoveryLocation,
  rejectFriendRequest,
} from '../../api/friends';
import type {
  AcceptedFriendActionPayload,
  DiscoveryGender,
  FriendRequestItem,
  NearbyDiscoveryUser,
} from './types';

const AUTO_REFRESH_INTERVAL_MS = 90 * 1000;

interface Props {
  token: string;
  nickname: string;
  gender?: DiscoveryGender;
  autoMode?: boolean;
  onFriendAccepted?: (payload: AcceptedFriendActionPayload) => void | Promise<void>;
};

function genderLabel(gender: DiscoveryGender): string {
  switch (gender) {
    case 'male':
      return '남';
    case 'female':
      return '여';
    case 'other':
      return '기타';
    default:
      return '미설정';
  }
}

function formatDistanceMeters(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)}m`;
  }
  if (meters < 100_000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${Math.round(meters / 1000)}km`;
}

function statusLabel(status: NearbyDiscoveryUser['friendshipStatus']): string {
  switch (status) {
    case 'friend':
      return '이미 친구';
    case 'outgoing_pending':
      return '요청 보냄';
    case 'incoming_pending':
      return '상대 요청 도착';
    default:
      return '요청 가능';
  }
}

export function FriendMapDiscoveryScreen({
  token,
  nickname,
  gender = 'unknown',
  autoMode = true,
  onFriendAccepted,
}: Props) {
  const { width: windowWidth } = useWindowDimensions();
  const isNarrowWidth = windowWidth < 380;
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [nearbyUsers, setNearbyUsers] = useState<NearbyDiscoveryUser[]>([]);
  const [incomingRequests, setIncomingRequests] = useState<FriendRequestItem[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setStatus('현재 위치와 주변 사용자를 불러오는 중...');
    try {
      const permission = await Location.getForegroundPermissionsAsync();
      const finalPermission = permission.granted ? permission : await Location.requestForegroundPermissionsAsync();
      if (!finalPermission.granted) {
        throw new Error('위치 권한이 필요합니다.');
      }

      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const { latitude, longitude, accuracy: rawAccuracy } = position.coords;
      const accuracy = rawAccuracy ?? undefined;
      const geocoded = await Location.reverseGeocodeAsync({ latitude, longitude });
      const countryCode = (geocoded?.[0]?.isoCountryCode ?? '').toUpperCase();

      await upsertDiscoveryLocation(
        {
          latitude,
          longitude,
          accuracy,
          countryCode,
          gender,
          nickname,
          shareOnMap: true,
        },
        token,
      );

      const [nearby, incoming] = await Promise.all([
        getNearbyDiscoveryUsers({ lat: latitude, lon: longitude }, token),
        getIncomingFriendRequests(token),
      ]);
      setNearbyUsers(nearby.users);
      setIncomingRequests(incoming.requests);
      setStatus(
        `내 좌표 ${latitude.toFixed(5)}, ${longitude.toFixed(5)} · 국가 ${countryCode || 'UNKNOWN'} · 앱 사용자 ${nearby.total}명 (거리순)`,
      );
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '친구찾기 로딩 실패';
      setStatus(`실패 · ${message}`);
    } finally {
      setLoading(false);
    }
  }, [gender, nickname, token]);

  useEffect(() => {
    void refresh();
    if (!autoMode) {
      return;
    }
    const interval = setInterval(() => {
      void refresh();
    }, AUTO_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [autoMode, refresh]);

  const handleRequestFriend = useCallback(async (user: NearbyDiscoveryUser) => {
    try {
      const result = await createFriendRequest(user.userId, token);
      Alert.alert(
        result.autoAccepted ? '친구등록 완료' : '친구 요청',
        result.autoAccepted
          ? `${user.nickname}님과 친구로 연결되었습니다.`
          : `${user.nickname}님에게 친구 요청을 보냈습니다. 상대방 수락 후 목록에 표시됩니다.`,
      );
      await refresh();
    } catch (error: unknown) {
      Alert.alert('친구등록 실패', error instanceof Error ? error.message : '친구등록 실패');
    }
  }, [refresh, token]);

  const handleAccept = useCallback(async (request: FriendRequestItem) => {
    try {
      const accepted = await acceptFriendRequest(request.requestId, token);
      await refresh();
      if (onFriendAccepted) {
        Alert.alert(
          '친구 추가',
          `${request.senderNickname}님을 친구로 추가했습니다. 바로 이어서 무엇을 할지 선택하세요.`,
          [
            {
              text: '친구 목록 보기',
              onPress: () => {
                void onFriendAccepted({ action: 'friend-folder', friend: accepted.friend });
              },
            },
            {
              text: '채팅 열기',
              onPress: () => {
                void onFriendAccepted({ action: 'chat', friend: accepted.friend });
              },
            },
            {
              text: '보이스톡 시작',
              onPress: () => {
                void onFriendAccepted({ action: 'voip', friend: accepted.friend });
              },
            },
          ],
        );
        return;
      }
      Alert.alert('친구 추가', `${request.senderNickname}님을 친구로 추가했습니다.`);
    } catch (error: unknown) {
      Alert.alert('수락 실패', error instanceof Error ? error.message : '친구 요청 수락 실패');
    }
  }, [onFriendAccepted, refresh, token]);

  const handleReject = useCallback(async (request: FriendRequestItem) => {
    try {
      await rejectFriendRequest(request.requestId, token);
      await refresh();
    } catch (error: unknown) {
      Alert.alert('거절 실패', error instanceof Error ? error.message : '친구 요청 거절 실패');
    }
  }, [refresh, token]);

  return (
    <View style={[styles.container, isNarrowWidth && styles.containerCompact]}>
      <Text style={styles.title}>🗺 친구찾기</Text>
      <Text style={styles.subtitle}>
        {autoMode
          ? 'GPS와 프로필 정보로 앱 사용자를 거리순으로 표시합니다. km 제한 없이 전체 노출되며, 백그라운드 알림도 동작합니다.'
          : '내 위치를 올리고 앱 사용자를 거리순으로 확인한 뒤 좌표를 눌러 Google 지도에서 확인하고 친구 요청을 보낼 수 있습니다.'}
      </Text>

      {autoMode ? (
        <View style={styles.autoDetectRow}>
          <Text style={styles.autoDetectBadge}>{loading ? '⏳ 자동 감지 중...' : '📍 주변 친구 자동 감지'}</Text>
          <Text style={styles.autoDetectHint}>성별·위치는 프로필에서 자동 반영 · 90초마다 갱신</Text>
        </View>
      ) : null}

      {status ? <Text style={styles.statusText}>{status}</Text> : null}

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>수신 친구 요청</Text>
          {loading && incomingRequests.length === 0 ? <ActivityIndicator color="#6ee7b7" /> : null}
          {incomingRequests.length === 0 ? <Text style={styles.emptyText}>대기 중인 요청이 없습니다.</Text> : null}
          {incomingRequests.map((request) => (
            <View key={request.requestId} style={styles.requestCard}>
              <Text style={styles.requestName}>{request.senderCountryFlag || '🌐'} {request.senderNickname} ({genderLabel(request.senderGender)})</Text>
              <Text style={styles.requestMeta}>보이스 ID {request.senderVoiceId || '없음'}</Text>
              <View style={[styles.actionRow, isNarrowWidth && styles.actionRowCompact]}>
                <Pressable style={[styles.acceptBtn, isNarrowWidth && styles.actionButtonCompact]} onPress={() => { void handleAccept(request); }}>
                  <Text style={styles.acceptBtnText}>수락</Text>
                </Pressable>
                <Pressable style={[styles.rejectBtn, isNarrowWidth && styles.actionButtonCompact]} onPress={() => { void handleReject(request); }}>
                  <Text style={styles.rejectBtnText}>거절</Text>
                </Pressable>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>주변 사용자</Text>
          {nearbyUsers.length === 0 ? <Text style={styles.emptyText}>주변에 표출 중인 사용자가 없습니다. 두 계정 모두 친구찾기를 열어야 보입니다.</Text> : null}
          {nearbyUsers.map((user) => (
            <View key={user.userId} style={styles.userCard}>
              <Text style={styles.userName}>{user.countryFlag || '🌐'} {user.nickname} ({genderLabel(user.gender)})</Text>
              <Text style={styles.userMeta}>거리 {formatDistanceMeters(user.distanceM)} · 좌표 {user.latitude.toFixed(5)}, {user.longitude.toFixed(5)}</Text>
              <Text style={styles.userMeta}>상태 {statusLabel(user.friendshipStatus)} · 보이스 ID {user.voiceId || '없음'}</Text>
              <View style={[styles.actionRow, isNarrowWidth && styles.actionRowCompact]}>
                <Pressable style={[styles.mapBtn, isNarrowWidth && styles.actionButtonCompact]} onPress={() => { void Linking.openURL(user.googleMapsUrl); }}>
                  <Text style={styles.mapBtnText}>Google 지도</Text>
                </Pressable>
                <Pressable
                  style={[styles.requestBtn, isNarrowWidth && styles.actionButtonCompact, user.friendshipStatus !== 'available' && styles.requestBtnDisabled]}
                  disabled={user.friendshipStatus !== 'available'}
                  onPress={() => { void handleRequestFriend(user); }}
                >
                  <Text style={styles.requestBtnText}>{user.friendshipStatus === 'available' ? '친구 요청' : statusLabel(user.friendshipStatus)}</Text>
                </Pressable>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
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
    color: '#e2e8f0',
    fontSize: 18,
    fontWeight: '700',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 6,
    marginBottom: 12,
    lineHeight: 18,
  },
  autoDetectRow: {
    marginBottom: 10,
    gap: 4,
  },
  autoDetectBadge: {
    color: '#79c0ff',
    fontSize: 12,
    fontWeight: '700',
  },
  autoDetectHint: {
    color: '#64748b',
    fontSize: 11,
    lineHeight: 16,
  },
  statusText: {
    color: '#79c0ff',
    fontSize: 12,
    marginBottom: 12,
  },
  scrollContent: {
    paddingBottom: 20,
    gap: 16,
  },
  section: {
    gap: 10,
  },
  sectionTitle: {
    color: '#e2e8f0',
    fontSize: 15,
    fontWeight: '700',
  },
  emptyText: {
    color: '#64748b',
    fontSize: 12,
  },
  requestCard: {
    backgroundColor: '#1e2533',
    borderRadius: 12,
    padding: 12,
  },
  requestName: {
    color: '#e2e8f0',
    fontSize: 14,
    fontWeight: '700',
  },
  requestMeta: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 4,
  },
  userCard: {
    backgroundColor: '#1e2533',
    borderRadius: 12,
    padding: 12,
  },
  userName: {
    color: '#e2e8f0',
    fontSize: 14,
    fontWeight: '700',
  },
  userMeta: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 4,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
  },
  actionRowCompact: {
    flexWrap: 'wrap',
  },
  actionButtonCompact: {
    flexBasis: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  mapBtn: {
    backgroundColor: '#0f766e',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  mapBtnText: {
    color: '#ecfeff',
    fontSize: 12,
    fontWeight: '700',
  },
  requestBtn: {
    backgroundColor: '#6ee7b7',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  requestBtnDisabled: {
    backgroundColor: '#334155',
  },
  requestBtnText: {
    color: '#0b0f16',
    fontSize: 12,
    fontWeight: '700',
  },
  acceptBtn: {
    backgroundColor: '#6ee7b7',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  acceptBtnText: {
    color: '#0b0f16',
    fontSize: 12,
    fontWeight: '700',
  },
  rejectBtn: {
    backgroundColor: '#7f1d1d',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  rejectBtnText: {
    color: '#fee2e2',
    fontSize: 12,
    fontWeight: '700',
  },
});
