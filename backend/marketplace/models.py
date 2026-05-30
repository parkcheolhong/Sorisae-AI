"""
Database models for marketplace
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

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
    native_language = Column(String(10), nullable=True)
    country = Column(String(10), nullable=True)
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
