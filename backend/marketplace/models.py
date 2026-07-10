"""
Database models for marketplace
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint, text  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import relationship  # pyright: ignore[reportMissingImports]

from .database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


project_tags = Table(
    'project_tags',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime, default=_utcnow_naive)

    projects = relationship("Project", back_populates="category")


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow_naive)

    projects = relationship("Project", secondary=project_tags, back_populates="tags")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200))
    member_type = Column(String(30), nullable=False, default='individual')
    business_name = Column(String(200))
    business_registration_number = Column(String(50))
    representative_name = Column(String(120))
    hashed_password = Column(String(255))
    avatar_url = Column(String(500))
    preferred_language = Column(String(16), nullable=True)
    country_code = Column(String(8), nullable=True)
    phone_number = Column(String(40), nullable=True, index=True)
    credit_balance = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_staff = Column(Boolean, nullable=False, default=False)
    is_superuser = Column(Boolean, nullable=False, default=False)
    passkey_enabled = Column(Boolean, nullable=False, default=False)
    passkey_credential_id = Column(String(255), nullable=True, unique=True, index=True)
    passkey_public_key = Column(Text, nullable=True)
    passkey_device_label = Column(String(120), nullable=True)
    passkey_sign_count = Column(Integer, nullable=False, default=0)
    passkey_registered_at = Column(DateTime, nullable=True)
    native_language = Column(String(10), nullable=True)   # ISO 639-1 language code, e.g. 'ko', 'en', 'zh'
    country = Column(String(10), nullable=True)            # ISO 3166-1 alpha-2 country code, e.g. 'KR', 'US'
    created_at = Column(DateTime, default=_utcnow_naive)

    projects = relationship("Project", back_populates="author")
    reviews = relationship("Review", back_populates="user")
    purchases = relationship("Purchase", back_populates="buyer")
    ad_video_orders = relationship("AdVideoOrder", back_populates="user")


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    image_url = Column(String(500))
    demo_url = Column(String(500))
    github_url = Column(String(500))
    file_key = Column(String(500))
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)

    category = relationship("Category", back_populates="projects")
    author = relationship("User", back_populates="projects")
    tags = relationship("Tag", secondary=project_tags, back_populates="projects")
    reviews = relationship("Review", back_populates="project")
    purchases = relationship("Purchase", back_populates="project")


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=_utcnow_naive)

    project = relationship('Project', back_populates='reviews')
    user = relationship('User', back_populates='reviews')


class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Purchase(Base):
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    payment_method = Column(String(50))
    transaction_id = Column(String(255), unique=True)
    receipt_url = Column(String(500))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)

    project = relationship('Project', back_populates='purchases')
    buyer = relationship('User', back_populates='purchases')


class DownloadToken(Base):
    __tablename__ = 'download_tokens'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow_naive)


class AdVideoOrderStatus(str, enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    PROCESSING = "processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class AdVideoOrder(Base):
    __tablename__ = 'ad_video_orders'

    id = Column(Integer, primary_key=True, index=True)
    public_job_id = Column(String(36), nullable=True, unique=True, index=True)
    trace_id = Column(String(120), nullable=True, index=True)
    flow_id = Column(String(40), nullable=True, index=True)
    step_id = Column(String(40), nullable=True, index=True)
    action = Column(String(80), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    image_prompt = Column(Text, nullable=False)
    portrait_image_prompt = Column(Text, nullable=True)
    product_image_prompts = Column(Text, nullable=True)
    storyboard_json = Column(Text, nullable=True)
    storyboard_review_json = Column(Text, nullable=True)
    storyboard_review_history_json = Column(Text, nullable=True)
    subject_type = Column(String(30), nullable=False, default='auto')
    background_prompt = Column(Text, nullable=False)
    caption_text = Column(Text, nullable=False)
    scenario_script = Column(Text, nullable=True)
    voice_gender = Column(String(20), nullable=False, default='female')
    engine_type = Column(String(30), nullable=False, default='dedicated_engine')
    action_template_key = Column(String(100), nullable=True)
    motion_tempo = Column(String(20), nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=60)
    visual_style = Column(String(100), nullable=False, default='photorealistic')
    cut_count = Column(Integer, nullable=False, default=32)
    subtitle_speed = Column(Float, nullable=False, default=1.0)
    render_quality = Column(String(20), nullable=False, default='high')
    audio_volume = Column(Integer, nullable=False, default=100)
    status = Column(String(20), nullable=False, default=AdVideoOrderStatus.PENDING.value, index=True)
    progress_percent = Column(Integer, nullable=False, default=0)
    external_job_id = Column(String(255), nullable=True)
    output_file_key = Column(String(500), nullable=True)
    output_filename = Column(String(255), nullable=True)
    output_video_key = Column(String(500), nullable=True)
    output_video_filename = Column(String(255), nullable=True)
    quality_score = Column(Float, nullable=True)
    quality_gate_passed = Column(Boolean, nullable=False, default=False)
    quality_feedback = Column(Text, nullable=True)
    face_consistency_score = Column(Float, nullable=True)
    product_consistency_score = Column(Float, nullable=True)
    sales_quality_decision = Column(String(30), nullable=True)
    quality_retry_count = Column(Integer, nullable=False, default=0)
    quality_checked_at = Column(DateTime, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)

    user = relationship('User', back_populates='ad_video_orders')
    settlement_logs = relationship('AdVideoOrderSettlementLog', back_populates='order')


class AdVideoOrderSettlementLog(Base):
    __tablename__ = 'ad_video_order_settlement_logs'
    __table_args__ = (
        UniqueConstraint('order_id', 'period_day', name='uq_ad_video_order_settlement_order_day'),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('ad_video_orders.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=AdVideoOrderStatus.PENDING.value, index=True)
    engine_type = Column(String(30), nullable=False, default='dedicated_engine', index=True)
    render_quality = Column(String(20), nullable=False, default='high', index=True)
    currency = Column(String(10), nullable=False, default='USD')
    settlement_version = Column(String(20), nullable=False, default='v1')
    prompt_tokens = Column(Integer, nullable=False, default=0)
    render_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    local_cost = Column(Float, nullable=False, default=0.0)
    external_cost = Column(Float, nullable=False, default=0.0)
    storage_cost = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    period_day = Column(String(10), nullable=False, index=True)
    period_month = Column(String(7), nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)

    order = relationship('AdVideoOrder', back_populates='settlement_logs')


class CustomerOrchestratorCompletion(Base):
    __tablename__ = 'customer_orchestrator_completions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    trace_id = Column(String(120), nullable=True, index=True)
    flow_id = Column(String(40), nullable=True, index=True)
    step_id = Column(String(40), nullable=True, index=True)
    action = Column(String(80), nullable=True)
    project_name = Column(String(200), nullable=False)
    mode = Column(String(50), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    output_dir = Column(Text, nullable=True)
    postcheck_ok = Column(Boolean, nullable=True)
    gate_passed = Column(Boolean, nullable=False, default=False)
    override_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class FeatureExecutionLog(Base):
    __tablename__ = 'feature_execution_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    feature_id = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(String(120), nullable=True, index=True)
    status = Column(String(40), nullable=False, index=True)
    trace_id = Column(String(120), nullable=True, index=True)
    flow_id = Column(String(40), nullable=True, index=True)
    step_id = Column(String(40), nullable=True, index=True)
    action = Column(String(80), nullable=True)
    run_id = Column(String(120), nullable=True, index=True)
    prompt = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    output_payload_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class FeatureRetryQueue(Base):
    __tablename__ = 'feature_retry_queue'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    feature_id = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(String(120), nullable=True, index=True)
    queue_name = Column(String(80), nullable=True)
    status = Column(String(40), nullable=False, default='pending', index=True)
    trace_id = Column(String(120), nullable=True, index=True)
    flow_id = Column(String(40), nullable=True, index=True)
    step_id = Column(String(40), nullable=True, index=True)
    action = Column(String(80), nullable=True)
    payload_json = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=True, default=0)
    max_attempts = Column(Integer, nullable=True, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)


class CallModeAuditLog(Base):
    __tablename__ = 'call_mode_audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(120), nullable=False, index=True)
    session_id = Column(String(120), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    requested_mode = Column(String(80), nullable=True)
    resolved_mode = Column(String(80), nullable=True)
    auto_relay_requested = Column(Boolean, nullable=False, default=False)
    auto_relay_applied = Column(Boolean, nullable=False, default=False)
    call_route = Column(String(80), nullable=True)
    caller_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    callee_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    callee_phone = Column(String(40), nullable=True)
    status = Column(String(40), nullable=True)
    error_code = Column(String(120), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    call_quality = Column(String(40), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class UserActiveSession(Base):
    """계정당 단일 활성 세션 강제. 로그인 시 새 session_id 를 기록(덮어쓰기)하고,
    인증 시 토큰의 sid 가 이 값과 다르면 401 → 다른 단말/웹은 자동 로그아웃된다.
    (DB 영속 → 백엔드 재시작에도 단일 세션 보장 유지)
    """
    __tablename__ = 'user_active_sessions'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    session_id = Column(String(64), nullable=False)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)


class VoipDeviceToken(Base):
    """계정(user_id)에 등록된 VoIP 착신용 FCM 토큰.

    운영 정책은 사용자당 최신 1개 활성 토큰을 유지하는 것이다. 로그인/토큰 등록 시
    최신 토큰을 남기고 이전 토큰은 정리해, 동일 계정 다중 단말 동시 링을 방지한다.
    (DB 영속 → 백엔드 재시작 후에도 최신 활성 토큰 정책 유지)
    """
    __tablename__ = 'voip_device_tokens'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    fcm_token = Column(String(512), nullable=False, unique=True, index=True)
    platform = Column(String(20), nullable=False, default='android')
    created_at = Column(DateTime, default=_utcnow_naive)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)


class Friend(Base):
    __tablename__ = 'friends'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    friend_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    friend_email = Column(String(255), nullable=True, index=True)
    friend_username = Column(String(255), nullable=True)
    friend_phone = Column(String(40), nullable=True)
    added_at = Column(DateTime, default=_utcnow_naive, index=True)

    friend_user = relationship("User", foreign_keys=[friend_user_id])


class FriendRequest(Base):
    __tablename__ = 'friend_requests'

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), nullable=False, unique=True, index=True)
    sender_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    receiver_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    sender_nickname = Column(String(120), nullable=True)
    sender_gender = Column(String(20), nullable=True)
    sender_country_code = Column(String(8), nullable=True)
    sender_voice_id = Column(String(120), nullable=True)
    status = Column(String(20), nullable=False, default='pending', index=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    responded_at = Column(DateTime, nullable=True)


class FriendDiscoveryLocation(Base):
    __tablename__ = 'friend_discovery_locations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    nickname = Column(String(120), nullable=True)
    gender = Column(String(20), nullable=True)
    country_code = Column(String(8), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    share_on_map = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=_utcnow_naive, index=True)


class ChatRoom(Base):
    __tablename__ = 'chat_rooms'

    id = Column(Integer, primary_key=True, index=True)
    room_uuid = Column(String(64), nullable=False, unique=True, index=True)
    room_type = Column(String(20), nullable=False, default='direct', index=True)
    title = Column(String(200), nullable=True)
    owner_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    default_source_lang = Column(String(16), nullable=True)
    default_target_lang = Column(String(16), nullable=True)
    translation_mode = Column(String(20), nullable=True)
    allow_member_invites = Column(Boolean, nullable=False, default=False)
    member_limit = Column(Integer, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    last_message_id = Column(Integer, nullable=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class ChatRoomMember(Base):
    __tablename__ = 'chat_room_members'

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False, default='member')
    membership_status = Column(String(20), nullable=False, default='active', index=True)
    joined_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    left_at = Column(DateTime, nullable=True)
    mute_notifications = Column(Boolean, nullable=False, default=False)
    pinned_order = Column(Integer, nullable=True)
    last_read_message_id = Column(Integer, ForeignKey('chat_messages.id'), nullable=True)
    last_read_at = Column(DateTime, nullable=True)


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, index=True)
    message_uuid = Column(String(64), nullable=False, unique=True, index=True)
    room_id = Column(Integer, ForeignKey('chat_rooms.id'), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    message_type = Column(String(24), nullable=False, default='text')
    body = Column(Text, nullable=False)
    translated_body = Column(Text, nullable=True)
    body_source_lang = Column(String(16), nullable=True)
    body_target_lang = Column(String(16), nullable=True)
    translation_engine = Column(String(40), nullable=True)
    translation_status = Column(String(20), nullable=True)
    reply_to_message_id = Column(Integer, ForeignKey('chat_messages.id'), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    # DB 컬럼이 NOT NULL 이므로 ORM 이 항상 기본값('{}')을 넣도록 모델에 매핑한다.
    # (모델에 미정의 시 INSERT 가 컬럼을 생략 → NULL → NotNullViolation 으로 채팅 전송 500 발생했음)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class ChatMessageTranslation(Base):
    __tablename__ = 'chat_message_translations'

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('chat_messages.id'), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    target_lang = Column(String(16), nullable=True)
    translated_body = Column(Text, nullable=True)
    translation_engine = Column(String(40), nullable=True)
    translation_status = Column(String(20), nullable=True)
    failure_code = Column(String(80), nullable=True)
    failure_detail = Column(Text, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)


class TripSession(Base):
    __tablename__ = 'trip_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    status = Column(String(20), nullable=False, default='active', index=True)
    origin_country = Column(String(8), nullable=True)
    destination_country = Column(String(8), nullable=True)
    destination_city = Column(String(32), nullable=True)
    travel_start_date = Column(String(10), nullable=True)
    travel_end_date = Column(String(10), nullable=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    budget_currency = Column(String(8), nullable=True)
    context_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class ConversationTurn(Base):
    __tablename__ = 'conversation_turns'

    id = Column(Integer, primary_key=True, index=True)
    trip_session_id = Column(Integer, ForeignKey('trip_sessions.id'), nullable=False, index=True)
    turn_index = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    utterance = Column(Text, nullable=False)
    language_code = Column(String(16), nullable=True)
    intent = Column(String(80), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    slots_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class TravelSlot(Base):
    __tablename__ = 'travel_slots'
    __table_args__ = (
        UniqueConstraint('trip_session_id', 'slot_key', name='uq_travel_slots_session_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    trip_session_id = Column(Integer, ForeignKey('trip_sessions.id'), nullable=False, index=True)
    source_turn_id = Column(Integer, ForeignKey('conversation_turns.id'), nullable=True, index=True)
    slot_key = Column(String(64), nullable=False, index=True)
    slot_value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    provenance = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class FeedbackEvent(Base):
    __tablename__ = 'feedback_events'

    id = Column(Integer, primary_key=True, index=True)
    trip_session_id = Column(Integer, ForeignKey('trip_sessions.id'), nullable=True, index=True)
    conversation_turn_id = Column(Integer, ForeignKey('conversation_turns.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    feedback_type = Column(String(40), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class PartnerCatalog(Base):
    __tablename__ = 'partner_catalog'

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False, index=True)
    integration_type = Column(String(40), nullable=False, default='affiliate')
    active = Column(Boolean, nullable=False, default=True, index=True)
    regions_json = Column(Text, nullable=False, default='[]', server_default=text("'[]'"))
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class PartnerConnector(Base):
    __tablename__ = 'partner_connectors'

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(String(80), nullable=False, unique=True, index=True)
    partner_id = Column(String(80), ForeignKey('partner_catalog.partner_id'), nullable=False, index=True)
    auth_type = Column(String(40), nullable=False, default='api_key')
    secret_ref_id = Column(String(255), nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default='inactive', index=True)
    last_tested_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class RoutingPolicy(Base):
    __tablename__ = 'routing_policies'

    id = Column(Integer, primary_key=True, index=True)
    policy_version = Column(String(32), nullable=False, default='v1')
    country_code = Column(String(8), nullable=False, index=True)
    city_code = Column(String(16), nullable=True, index=True)
    category = Column(String(20), nullable=False, index=True)
    primary_partner_id = Column(String(80), nullable=True, index=True)
    fallback_partner_ids_json = Column(Text, nullable=False, default='[]', server_default=text("'[]'"))
    priority = Column(Integer, nullable=False, default=100)
    active = Column(Boolean, nullable=False, default=True, index=True)
    updated_by = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class RecommendationEvent(Base):
    __tablename__ = 'recommendation_events'

    id = Column(Integer, primary_key=True, index=True)
    trip_session_id = Column(Integer, ForeignKey('trip_sessions.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    category = Column(String(20), nullable=False, index=True)
    partner_id = Column(String(80), nullable=True, index=True)
    recommendation_rank = Column(Integer, nullable=True)
    recommendation_payload_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class PartnerClickEvent(Base):
    __tablename__ = 'partner_click_events'

    id = Column(Integer, primary_key=True, index=True)
    recommendation_event_id = Column(Integer, ForeignKey('recommendation_events.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    partner_id = Column(String(80), nullable=False, index=True)
    click_ref = Column(String(120), nullable=True, unique=True, index=True)
    landing_url = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class BookingEvent(Base):
    __tablename__ = 'booking_events'

    id = Column(Integer, primary_key=True, index=True)
    partner_click_event_id = Column(Integer, ForeignKey('partner_click_events.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    partner_id = Column(String(80), nullable=False, index=True)
    booking_ref = Column(String(120), nullable=True, unique=True, index=True)
    status = Column(String(40), nullable=False, default='initiated', index=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    raw_payload_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class AttributionLedger(Base):
    __tablename__ = 'attribution_ledger'

    id = Column(Integer, primary_key=True, index=True)
    booking_event_id = Column(Integer, ForeignKey('booking_events.id'), nullable=True, index=True)
    partner_id = Column(String(80), nullable=False, index=True)
    ledger_type = Column(String(30), nullable=False, default='commission', index=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default='USD')
    settlement_status = Column(String(30), nullable=False, default='pending', index=True)
    settled_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class Consent(Base):
    __tablename__ = 'consents'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    consent_type = Column(String(40), nullable=False, index=True)
    purpose = Column(String(120), nullable=False)
    status = Column(String(20), nullable=False, default='granted', index=True)
    policy_version = Column(String(32), nullable=True)
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)


class PrivacyAuditLog(Base):
    __tablename__ = 'privacy_audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(80), nullable=True, index=True)
    resource_id = Column(String(120), nullable=True, index=True)
    legal_basis = Column(String(120), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=False, default='{}', server_default=text("'{}'"))
    created_at = Column(DateTime, default=_utcnow_naive, index=True)


class WorldlincoJsonDocument(Base):
    """WorldLinco referral/sales ledgers as JSONB documents (multi-instance SSOT)."""

    __tablename__ = 'worldlinco_json_documents'

    store_key = Column(String(64), primary_key=True)
    payload_json = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, index=True)
