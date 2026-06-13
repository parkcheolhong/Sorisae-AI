export interface Friend {
  id: number;
  userId: number;
  friendUserId: number | null;
  friendVoiceId?: string | null;
  friendPreferredLanguage?: string | null;
  friendUsername: string;
  friendEmail: string;
  friendPhone?: string;
  friendCountryCode?: string;
  friendCountryFlag?: string;
  friendGender?: DiscoveryGender;
  addedAt: string;
}

export interface AddFriendPayload {
  targetEmail: string;
  phoneNumber?: string;
}

export interface FriendListResponse {
  friends: Friend[];
  total: number;
}

export type DiscoveryGender = 'male' | 'female' | 'other' | 'unknown';

export interface NearbyDiscoveryUser {
  userId: number;
  nickname: string;
  gender: DiscoveryGender;
  countryCode: string;
  countryFlag: string;
  latitude: number;
  longitude: number;
  accuracy?: number | null;
  distanceM: number;
  voiceId?: string | null;
  friendshipStatus: 'available' | 'friend' | 'outgoing_pending' | 'incoming_pending';
  googleMapsUrl: string;
  updatedAt: string;
}

export interface NearbyDiscoveryResponse {
  status: string;
  users: NearbyDiscoveryUser[];
  total: number;
  viewerLatitude: number;
  viewerLongitude: number;
  radiusM: number | null;
}

export interface DiscoveryLocationPayload {
  latitude: number;
  longitude: number;
  accuracy?: number;
  countryCode?: string;
  gender?: DiscoveryGender;
  nickname?: string;
  shareOnMap?: boolean;
}

export interface FriendRequestItem {
  requestId: string;
  senderUserId: number;
  senderNickname: string;
  senderGender: DiscoveryGender;
  senderCountryCode: string;
  senderCountryFlag: string;
  senderVoiceId?: string | null;
  createdAt: string;
  status: string;
}

export interface IncomingFriendRequestResponse {
  requests: FriendRequestItem[];
  total: number;
}

export interface OutgoingFriendRequestItem {
  requestId: string;
  receiverUserId: number;
  receiverNickname: string;
  receiverGender: DiscoveryGender;
  receiverCountryCode: string;
  receiverCountryFlag: string;
  receiverVoiceId?: string | null;
  createdAt: string;
  status: string;
}

export interface OutgoingFriendRequestResponse {
  requests: OutgoingFriendRequestItem[];
  total: number;
}

export interface AcceptFriendRequestResponse {
  status: string;
  requestId: string;
  friend: Friend;
}

export type AcceptedFriendAction = 'friend-folder' | 'chat' | 'voip';

export interface AcceptedFriendActionPayload {
  action: AcceptedFriendAction;
  friend: Friend;
}

export interface MissedVoipCall {
  id: number;
  callId: string;
  createdAt: string;
  callerUserId?: number | null;
  callerVoiceId?: string | null;
  callerLabel: string;
  callerPreferredLanguage?: string | null;
  callerCountryCode?: string | null;
  status: string;
}
