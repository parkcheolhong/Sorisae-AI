import Constants from 'expo-constants';
import type {
  AcceptFriendRequestResponse,
  AddFriendPayload,
  DiscoveryLocationPayload,
  Friend,
  FriendInviteConfirmPayload,
  FriendInviteRequestPayload,
  FriendInviteRequestResponse,
  FriendListResponse,
  IncomingFriendRequestResponse,
  MissedVoipCall,
  NearbyDiscoveryResponse,
  OutgoingFriendRequestResponse,
} from '../features/friends/types';

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  'http://10.0.2.2:8000';

function mapFriendApiError(status: number, fallback: string): Error {
  if (status === 401 || status === 403) {
    return new Error('로그인 세션이 만료되었습니다. 로그아웃 후 다시 로그인해 주세요.');
  }
  if (status === 502 || status === 503 || status === 504) {
    return new Error('서버가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.');
  }
  return new Error(`${fallback}: ${status}`);
}

export async function getFriends(userId: number, token: string): Promise<FriendListResponse> {
  const res = await fetch(`${BASE_URL}/api/users/${userId}/friends`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw mapFriendApiError(res.status, '친구 목록 조회 실패');
  return res.json() as Promise<FriendListResponse>;
}

export async function requestFriendInviteCode(
  payload: FriendInviteRequestPayload,
  token: string,
): Promise<FriendInviteRequestResponse> {
  const res = await fetch(`${BASE_URL}/api/friends/invites/request-code`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      targetEmail: payload.targetEmail.trim(),
      phoneNumber: payload.phoneNumber?.trim() || undefined,
      displayName: payload.displayName?.trim() || undefined,
      verificationChannel: payload.verificationChannel || 'email',
    }),
  });
  const body = await res.json().catch(() => null) as { detail?: string } | FriendInviteRequestResponse | null;
  if (!res.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : null;
    throw new Error(detail || `친구 인증 요청 실패: ${res.status}`);
  }
  return body as FriendInviteRequestResponse;
}

export async function confirmFriendInvite(
  payload: FriendInviteConfirmPayload,
  token: string,
): Promise<Friend> {
  const res = await fetch(`${BASE_URL}/api/friends/invites/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => null) as { detail?: string } | Friend | null;
  if (!res.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : null;
    throw new Error(detail || `친구 인증 확인 실패: ${res.status}`);
  }
  return body as Friend;
}

export async function addFriend(payload: AddFriendPayload, token: string): Promise<Friend> {
  const res = await fetch(`${BASE_URL}/api/friends`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      targetEmail: payload.targetEmail.trim(),
      phoneNumber: payload.phoneNumber?.trim() || undefined,
      displayName: payload.displayName?.trim() || undefined,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null) as { detail?: string } | null;
    const detail = typeof body?.detail === 'string' ? body.detail : null;
    throw new Error(detail || `친구 추가 실패: ${res.status}`);
  }
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
  if (!res.ok) throw mapFriendApiError(res.status, '보낸 친구 요청 조회 실패');
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
