export interface Friend {
  id: number;
  userId: number;
  friendUserId: number;
  friendUsername: string;
  friendEmail: string;
  friendPhone?: string;
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
