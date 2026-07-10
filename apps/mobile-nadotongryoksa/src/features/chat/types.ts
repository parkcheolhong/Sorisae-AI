export interface ChatCounterpart {
  user_id: number;
  nickname: string;
  voice_id?: string | null;
  preferred_language?: string | null;
}

export interface ChatRoomSummary {
  room_id: string;
  room_type: 'direct' | 'group' | 'system' | string;
  title: string;
  member_count: number;
  member_limit?: number | null;
  allow_member_invites?: boolean;
  can_invite_members?: boolean;
  unread_count: number;
  last_message_preview: string;
  last_message_type?: string | null;
  last_message_at: string;
  counterpart?: ChatCounterpart | null;
}

export interface ChatRoomMember {
  user_id: number;
  nickname: string;
  voice_id?: string | null;
  preferred_language?: string | null;
  role: string;
  membership_status: string;
}

export interface ChatRoomDetail {
  room_id: string;
  room_type: string;
  title: string;
  owner_user_id: number;
  default_source_lang?: string | null;
  default_target_lang?: string | null;
  translation_mode: string;
  member_limit?: number | null;
  allow_member_invites?: boolean;
  can_invite_members?: boolean;
  counterpart?: ChatCounterpart | null;
  members: ChatRoomMember[];
}

export interface ChatViewerTranslation {
  target_lang: string;
  translated_body?: string | null;
  translation_status?: string | null;
  failure_code?: string | null;
  failure_detail?: string | null;
}

export interface ChatDeliverySummary {
  recipient_count: number;
  pending_count: number;
  done_count: number;
  failed_count: number;
  skipped_count?: number;
  status?: string | null;
}

export interface ChatMessageItem {
  message_id: string;
  room_id: string;
  sender_user_id?: number | null;
  sender_label: string;
  sender_voice_id?: string | null;
  message_type: string;
  body: string;
  translated_body?: string | null;
  body_source_lang?: string | null;
  body_target_lang?: string | null;
  translation_status?: string | null;
  viewer_translation?: ChatViewerTranslation | null;
  delivery_summary?: ChatDeliverySummary | null;
  created_at: string;
  mine: boolean;
}

export interface ChatRoomReadyEvent {
  type: 'chat_room_ready';
  room_id: string;
  viewer_user_id: number;
}

export interface ChatMessageCreatedEvent {
  type: 'message_created';
  room_id: string;
  viewer_user_id: number;
  message: ChatMessageItem;
}

export type ChatRoomSocketEvent = ChatRoomReadyEvent | ChatMessageCreatedEvent;

export interface ChatRoomListResponse {
  items: ChatRoomSummary[];
  next_cursor?: string | null;
}

export interface ChatMessageListResponse {
  items: ChatMessageItem[];
  next_cursor?: string | null;
}

export interface ChatMembersAddResponse {
  room: ChatRoomDetail;
  added_user_ids: number[];
}