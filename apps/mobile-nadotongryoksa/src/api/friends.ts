import Constants from 'expo-constants';
import type {
  AcceptFriendRequestResponse,
  AddFriendPayload,
  DiscoveryLocationPayload,
  Friend,
  FriendListResponse,
  IncomingFriendRequestResponse,
  MissedVoipCall,
  NearbyDiscoveryResponse,
  OutgoingFriendRequestResponse,
} from '../features/friends/types';

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

export async function upsertDiscoveryLocation(payload: DiscoveryLocationPayload, token: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/discovery/location`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`지도 위치 업로드 실패: ${res.status}`);
}

export async function getNearbyDiscoveryUsers(
  params: { lat: number; lon: number; radiusM?: number | null },
  token: string,
): Promise<NearbyDiscoveryResponse> {
  const query = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
  });
  if (params.radiusM != null && params.radiusM > 0) {
    query.set('radius_m', String(params.radiusM));
  }
  const res = await fetch(`${BASE_URL}/api/friends/discovery/nearby?${query.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`주변 사용자 조회 실패: ${res.status}`);
  return res.json() as Promise<NearbyDiscoveryResponse>;
}

export async function createFriendRequest(receiverUserId: number, token: string): Promise<{ autoAccepted?: boolean }> {
  const res = await fetch(`${BASE_URL}/api/friends/requests`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ receiverUserId }),
  });
  if (!res.ok) throw new Error(`친구 요청 실패: ${res.status}`);
  const payload = await res.json().catch(() => ({})) as { autoAccepted?: boolean };
  return { autoAccepted: Boolean(payload.autoAccepted) };
}

export async function getIncomingFriendRequests(token: string): Promise<IncomingFriendRequestResponse> {
  const res = await fetch(`${BASE_URL}/api/friends/requests/incoming`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`수신 친구 요청 조회 실패: ${res.status}`);
  return res.json() as Promise<IncomingFriendRequestResponse>;
}

export async function getOutgoingFriendRequests(token: string): Promise<OutgoingFriendRequestResponse> {
  const res = await fetch(`${BASE_URL}/api/friends/requests/outgoing`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`보낸 친구 요청 조회 실패: ${res.status}`);
  return res.json() as Promise<OutgoingFriendRequestResponse>;
}

export async function acceptFriendRequest(requestId: string, token: string): Promise<AcceptFriendRequestResponse> {
  const res = await fetch(`${BASE_URL}/api/friends/requests/${requestId}/accept`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`친구 요청 수락 실패: ${res.status}`);
  return res.json() as Promise<AcceptFriendRequestResponse>;
}

export async function rejectFriendRequest(requestId: string, token: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/requests/${requestId}/reject`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`친구 요청 거절 실패: ${res.status}`);
}

export async function getRecentMissedVoipCalls(token: string): Promise<MissedVoipCall[]> {
  const res = await fetch(`${BASE_URL}/api/v1/voip/calls/missed/recent`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`부재중 통화 조회 실패: ${res.status}`);
  return res.json() as Promise<MissedVoipCall[]>;
}
