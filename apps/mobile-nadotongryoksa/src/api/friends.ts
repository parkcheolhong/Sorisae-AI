import Constants from 'expo-constants';
import type { Friend, AddFriendPayload, FriendListResponse } from '../features/friends/types';

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  'http://10.0.2.2:8000';

export async function getFriends(userId: number, token: string): Promise<FriendListResponse> {
  const res = await fetch(`${BASE_URL}/api/users/${userId}/friends`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`친구 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<FriendListResponse>;
}

export async function addFriend(payload: AddFriendPayload, token: string): Promise<Friend> {
  const res = await fetch(`${BASE_URL}/api/friends`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`친구 추가 실패: ${res.status}`);
  return res.json() as Promise<Friend>;
}

export async function removeFriend(friendId: number, token: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/${friendId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`친구 삭제 실패: ${res.status}`);
}
