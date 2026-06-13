import { useCallback, useEffect, useRef } from 'react';
import { Alert, AppState, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import {
  createFriendRequest,
  getNearbyDiscoveryUsers,
  upsertDiscoveryLocation,
} from '../../api/friends';
import type { DiscoveryGender, NearbyDiscoveryUser } from './types';

const PROMPT_COOLDOWN_MS = 10 * 60 * 1000;
const SCAN_INTERVAL_MS = 90 * 1000;
const NEAR_RADIUS_M = 800;
const DISMISSED_KEY = 'auto_nearby_friend_dismissed_v1';
const LAST_PROMPT_KEY = 'auto_nearby_friend_last_prompt_v1';

export type AutoDiscoveryGender = DiscoveryGender;

interface Options {
  enabled: boolean;
  token: string | null;
  userId: number | null;
  nickname: string;
  gender?: AutoDiscoveryGender;
  countryCode?: string;
  onFriendAccepted?: () => void;
}

function distanceLabel(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)}m`;
  }
  return `${(meters / 1000).toFixed(1)}km`;
}

function rangeLabel(meters: number): string {
  return meters <= NEAR_RADIUS_M ? '근거리' : '원거리';
}

async function loadDismissedUserIds(): Promise<Set<number>> {
  try {
    const raw = await AsyncStorage.getItem(DISMISSED_KEY);
    if (!raw) {
      return new Set();
    }
    const parsed = JSON.parse(raw) as number[];
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

async function persistDismissedUserIds(ids: Set<number>): Promise<void> {
  await AsyncStorage.setItem(DISMISSED_KEY, JSON.stringify(Array.from(ids)));
}

export function useAutoNearbyFriendDiscovery({
  enabled,
  token,
  userId,
  nickname,
  gender = 'unknown',
  countryCode = '',
  onFriendAccepted,
}: Options) {
  const scanningRef = useRef(false);
  const dismissedRef = useRef<Set<number>>(new Set());
  const lastPromptAtRef = useRef(0);

  const promptForUser = useCallback(async (user: NearbyDiscoveryUser) => {
    if (!token) {
      return;
    }

    const now = Date.now();
    if (now - lastPromptAtRef.current < PROMPT_COOLDOWN_MS) {
      return;
    }
    if (dismissedRef.current.has(user.userId)) {
      return;
    }

    lastPromptAtRef.current = now;
    await AsyncStorage.setItem(LAST_PROMPT_KEY, String(now));

    const range = rangeLabel(user.distanceM);
    const distance = distanceLabel(user.distanceM);

    Alert.alert(
      '주변 친구 감지',
      `${range}(${distance}) · ${user.countryFlag || '🌐'} ${user.nickname}님이 감지되었습니다.\n근거리(800m 이내)에서는 친구등록 시 즉시 연결됩니다.`,
      [
        {
          text: '나중에',
          style: 'cancel',
          onPress: () => {
            dismissedRef.current.add(user.userId);
            void persistDismissedUserIds(dismissedRef.current);
          },
        },
        {
          text: '친구등록',
          onPress: () => {
            void (async () => {
              try {
                const result = await createFriendRequest(user.userId, token);
                Alert.alert(
                  result.autoAccepted ? '친구등록 완료' : '친구 요청 전송',
                  result.autoAccepted
                    ? `${user.nickname}님과 친구로 연결되었습니다. 친구 목록에서 확인할 수 있습니다.`
                    : `${user.nickname}님에게 친구 요청을 보냈습니다. 상대방 수락 후 목록에 표시됩니다.`,
                );
                onFriendAccepted?.();
              } catch (error: unknown) {
                Alert.alert(
                  '친구등록 실패',
                  error instanceof Error ? error.message : '친구등록에 실패했습니다.',
                );
              }
            })();
          },
        },
      ],
    );
  }, [onFriendAccepted, token]);

  const runScan = useCallback(async () => {
    if (!enabled || !token || !userId || scanningRef.current || Platform.OS === 'web') {
      return;
    }

    scanningRef.current = true;
    try {
      const permission = await Location.getForegroundPermissionsAsync();
      const finalPermission = permission.granted
        ? permission
        : await Location.requestForegroundPermissionsAsync();
      if (!finalPermission.granted) {
        return;
      }

      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const { latitude, longitude, accuracy: rawAccuracy } = position.coords;

      await upsertDiscoveryLocation(
        {
          latitude,
          longitude,
          accuracy: rawAccuracy ?? undefined,
          countryCode: countryCode || undefined,
          gender,
          nickname,
          shareOnMap: true,
        },
        token,
      );

      const nearby = await getNearbyDiscoveryUsers(
        { lat: latitude, lon: longitude },
        token,
      );

      const candidates = nearby.users
        .filter((user) => user.userId !== userId)
        .filter((user) => user.friendshipStatus === 'available')
        .filter((user) => !dismissedRef.current.has(user.userId))
        .sort((a, b) => a.distanceM - b.distanceM);

      const closest = candidates[0];
      if (closest) {
        await promptForUser(closest);
      }
    } catch {
      // silent background scan — no manual UI required
    } finally {
      scanningRef.current = false;
    }
  }, [countryCode, enabled, gender, nickname, promptForUser, token, userId]);

  useEffect(() => {
    if (!enabled || !token || !userId) {
      return;
    }

    void (async () => {
      dismissedRef.current = await loadDismissedUserIds();
      const lastPromptRaw = await AsyncStorage.getItem(LAST_PROMPT_KEY);
      lastPromptAtRef.current = lastPromptRaw ? Number(lastPromptRaw) || 0 : 0;
    })();

    void runScan();
    const interval = setInterval(() => {
      void runScan();
    }, SCAN_INTERVAL_MS);

    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        void runScan();
      }
    });

    return () => {
      clearInterval(interval);
      subscription.remove();
    };
  }, [enabled, runScan, token, userId]);
}
