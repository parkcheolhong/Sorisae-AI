from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    credit_balance: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    demo_url: Optional[str] = None
    github_url: Optional[str] = None
    image_url: Optional[str] = None


class ProjectCreate(ProjectBase):
    category_id: int
    tags: Optional[List[str]] = []


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    demo_url: Optional[str] = None
    github_url: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None


class ProjectSubscriptionInfo(BaseModel):
    product_code: str
    product_name: str
    product_description: Optional[str] = None
    plan_code: Optional[str] = None
    plan_name: Optional[str] = None
    currency: Optional[str] = None
    amount_minor: Optional[int] = None
    provider: Optional[str] = None


class Project(ProjectBase):
    id: int
    category_id: int
    author_id: Optional[int] = None
    file_key: Optional[str] = None
    downloads: int = 0
    rating: float = 0.0
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[Category] = None
    tags: List[Tag] = []
    subscription: Optional[ProjectSubscriptionInfo] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    projects: List[Project]
    total: int
    skip: int = 0
    limit: int = 12


class ReviewBase(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str


class ReviewCreate(ReviewBase):
    project_id: int


class Review(ReviewBase):
    id: int
    project_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewWithUser(Review):
    user: User


class PurchaseBase(BaseModel):
    project_id: int
    payment_method: str = Field(default="card")


class PurchaseCreate(PurchaseBase):
    pass


class Purchase(BaseModel):
    id: int
    project_id: int
    buyer_id: int
    amount: float
    status: str
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseResponse(Purchase):
    project: Optional[Project] = None
    payment_url: Optional[str] = None
    payment_mode: Optional[str] = None
    payment_provider: Optional[str] = None
    payment_simulation: Optional[bool] = None
    payment_message: Optional[str] = None


class PaymentInitResult(BaseModel):
    payment_url: str
    order_id: str
    transaction_id: str


class PaymentCallbackResponse(BaseModel):
    status: str
    purchase_id: int
    transaction_id: str
    payment_mode: str
    payment_provider: str
    payment_simulation: bool
    payment_message: str


class FileUploadResponse(BaseModel):
    file_key: str
    file_url: str
    file_size: int
    content_type: str


class DownloadTokenResponse(BaseModel):
    token: str
    expires_in: int
    download_url: str


class SubscriptionStatusResponse(BaseModel):
    user_id: int
    subscription_status: str
    product_code: Optional[str] = None
    plan_code: Optional[str] = None
    entitlement_set: List[str] = []
    period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    device_limit: int = 0
    active_device_count: int = 0
    source: Optional[str] = None


class MobileSubscriptionVerifyRequest(BaseModel):
    platform: str = Field(pattern="^(ios|android)$")
    product_code: str = Field(min_length=1, max_length=100)
    plan_code: str = Field(min_length=1, max_length=100)
    purchase_token_or_receipt: str = Field(min_length=1, max_length=20000)
    transaction_id: Optional[str] = Field(default=None, max_length=255)
    external_product_id: Optional[str] = Field(default=None, max_length=150)
    external_price_id: Optional[str] = Field(default=None, max_length=150)


class MobileSubscriptionVerifyResponse(SubscriptionStatusResponse):
    verified: bool
    source_original_id: Optional[str] = None
    verification_mode: str
    verification_simulated: bool


class CheckoutSessionCreateRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=100)
    plan_code: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="stripe", pattern="^(stripe)$")
    success_url: str = Field(min_length=1, max_length=2000)
    cancel_url: str = Field(min_length=1, max_length=2000)


class CheckoutSessionResponse(BaseModel):
    provider: str
    checkout_url: str
    session_id: str
    expires_in: int
    verification_mode: str
    verification_simulated: bool


class SubscriptionCatalogPlanSummary(BaseModel):
    plan_code: str
    plan_name: str
    billing_period: str
    provider: str
    currency: str
    amount_minor: int


class SubscriptionCatalogItem(BaseModel):
    product_code: str
    product_name: str
    product_description: Optional[str] = None
    product_family: str
    subscription_status: str = "none"
    cancel_at_period_end: bool = False
    period_end: Optional[datetime] = None
    active_plan: Optional[SubscriptionCatalogPlanSummary] = None
    entitlement_set: List[str] = []


class SubscriptionActionRequest(BaseModel):
    product_code: Optional[str] = Field(default=None, min_length=1, max_length=100)


class SubscriptionActionResponse(SubscriptionStatusResponse):
    applied: bool
    ignored: bool = False
    reason_code: str


class DeviceRegisterRequest(BaseModel):
    product_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=255)
    device_type: str = Field(min_length=1, max_length=30)
    platform: str = Field(min_length=1, max_length=30)
    app_version: Optional[str] = Field(default=None, max_length=50)
    os_version: Optional[str] = Field(default=None, max_length=50)
    last_ip: Optional[str] = Field(default=None, max_length=100)


class DeviceRegisterResponse(SubscriptionStatusResponse):
    registered: bool
    device_id: str
    device_revoked: bool = False


class DeviceRevokeRequest(BaseModel):
    product_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=255)


class DeviceRevokeResponse(SubscriptionStatusResponse):
    revoked: bool
    device_id: str


class MobileLicenseCheckRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=255)


class MobileLicenseCheckResponse(SubscriptionStatusResponse):
    allowed: bool
    reason_code: str
    device_registered: bool


class SubscriptionProjectLinkRequest(BaseModel):
    project_id: int = Field(ge=1)
    product_code: str = Field(min_length=1, max_length=100)


class SubscriptionProjectLinkResponse(BaseModel):
    project_id: int
    product_code: str
    linked: bool


class SubscriptionWebhookRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    event_type: str = Field(min_length=1, max_length=100)
    user_id: Optional[int] = Field(default=None, ge=1)
    product_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    plan_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    external_customer_id: Optional[str] = Field(default=None, max_length=150)
    external_subscription_id: Optional[str] = Field(default=None, max_length=150)
    original_transaction_id: Optional[str] = Field(default=None, max_length=255)
    latest_transaction_id: Optional[str] = Field(default=None, max_length=255)
    purchase_token_hash: Optional[str] = Field(default=None, max_length=255)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    event_time: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    reason_code: Optional[str] = Field(default=None, max_length=50)
    signature_valid: Optional[bool] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionWebhookResponse(BaseModel):
    provider: str
    event_id: str
    processed: bool
    ignored: bool = False
    reason_code: str
    subscription_status: Optional[str] = None
    delivery_attempt_id: Optional[int] = None


class AdStoryboardItem(BaseModel):
    cut: int = Field(ge=1, le=720)
    title: str = Field(min_length=1, max_length=120)
    duration_sec: int = Field(ge=1, le=60)
    narration_line: str = Field(min_length=1, max_length=500)
    visual_focus: str = Field(min_length=1, max_length=300)
    scene_prompt: str = Field(min_length=1, max_length=2000)
    designer_prompt: Optional[str] = Field(default=None, max_length=4000)
    motion_speed_percent: Optional[int] = Field(default=None, ge=25, le=300)
    source_scenario: Optional[str] = Field(default=None, max_length=4000)
    asset_source: str = Field(default="auto", pattern="^(auto|portrait|product|custom)$")
    product_index: Optional[int] = Field(default=None, ge=0, le=20)
    asset_ref: Optional[str] = Field(default=None, max_length=5_000_000)
    start_sec: Optional[int] = Field(default=None, ge=0, le=60)
    end_sec: Optional[int] = Field(default=None, ge=1, le=60)


class AdStoryboardReviewItem(BaseModel):
    cut: int = Field(ge=1, le=20)
    status: str = Field(pattern="^(pending|approved|needs-fix)$")
    note: str = Field(default="", max_length=2000)


class AdVideoOrderCreate(BaseModel):
    storyboard: List[AdStoryboardItem] = Field(default_factory=list)
    storyboard_review: List[AdStoryboardReviewItem] = Field(default_factory=list)
    title: str = Field(min_length=2, max_length=200)
    image_prompt: str = Field(min_length=2, max_length=5_000_000)
    portrait_image_prompt: Optional[str] = Field(default=None, max_length=5_000_000)
    product_image_prompts: List[str] = Field(default_factory=list)
    subject_type: str = Field(default="auto", pattern="^(auto|human|robot|character|product)$")
    background_prompt: str = Field(min_length=2, max_length=2000)
    caption_text: str = Field(min_length=2, max_length=4000)
    scenario_script: Optional[str] = Field(default=None, max_length=4000)
    voice_gender: str = Field(default="female", pattern="^(female|male)$")
    engine_type: str = Field(default="dedicated_engine", pattern="^(external_api|internal_ffmpeg|dedicated_engine)$")
    action_template_key: Optional[str] = Field(default=None, max_length=100)
    motion_tempo: Optional[str] = Field(default="normal", pattern="^(slow|normal|fast|run)$")
    duration_seconds: int = Field(default=60, ge=15, le=60)
    visual_style: str = Field(default="photorealistic", max_length=100)
    cut_count: int = Field(default=12, ge=1, le=480)
    subtitle_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    render_quality: str = Field(default="high", pattern="^(standard|high|ultra)$")
    audio_volume: int = Field(default=100, ge=0, le=200)


class AdVideoOrder(BaseModel):
    id: int
    public_job_id: Optional[str] = None
    trace_id: Optional[str] = None
    flow_id: Optional[str] = None
    step_id: Optional[str] = None
    action: Optional[str] = None
    user_id: int
    title: str
    image_prompt: str
    portrait_image_prompt: Optional[str] = None
    product_image_prompts: List[str] = Field(default_factory=list)
    storyboard: List[AdStoryboardItem] = Field(default_factory=list)
    storyboard_review: List[AdStoryboardReviewItem] = Field(default_factory=list)
    subject_type: str = "auto"
    background_prompt: str
    caption_text: str
    scenario_script: Optional[str] = None
    voice_gender: str
    engine_type: Optional[str] = None
    action_template_key: Optional[str] = None
    motion_tempo: Optional[str] = None
    duration_seconds: int
    visual_style: str
    cut_count: int
    subtitle_speed: float
    render_quality: str
    audio_volume: int
    status: str
    progress_percent: int = 0
    external_job_id: Optional[str] = None
    output_file_key: Optional[str] = None
    output_filename: Optional[str] = None
    output_video_key: Optional[str] = None
    output_video_filename: Optional[str] = None
    quality_score: Optional[float] = None
    quality_gate_passed: bool = False
    quality_feedback: Optional[str] = None
    face_consistency_score: Optional[float] = None
    product_consistency_score: Optional[float] = None
    sales_quality_decision: Optional[str] = None
    quality_retry_count: int = 0
    quality_checked_at: Optional[datetime] = None
    download_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdVideoOrderCreateResponse(BaseModel):
    order: AdVideoOrder
    download_url: Optional[str] = None


class LocalDesignerEngineRunRequest(BaseModel):
    title: str = Field(default="차 마시는 연속 장면", min_length=1, max_length=200)
    scenario_script: str = Field(min_length=2, max_length=4000)
    duration_seconds: int = Field(default=5, ge=1, le=60)
    frames_per_second: int = Field(default=8, ge=1, le=24)
    subtitle_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    visual_style: str = Field(default="photorealistic", max_length=100)
    lighting_preset: str = Field(default="soft-window", max_length=100)
    detail_template: str = Field(default="premium-commercial", max_length=100)
    advanced_render_mode: str = Field(default="photoreal-film", max_length=100)
    auto_motion_boost: bool = Field(default=True)
    pose_style_prompt: Optional[str] = Field(default=None, max_length=500)
    background_prompt: Optional[str] = None
    caption_text: Optional[str] = None
    portrait_image_prompt: Optional[str] = None
    product_image_prompts: List[str] = Field(default_factory=list)
    action_template_key: Optional[str] = None
    motion_tempo: Optional[str] = None
    storyboard: List[dict] = Field(default_factory=list)


class LocalDesignerEngineCut(BaseModel):
    cut: int
    title: str
    segment: str
    duration_sec: float
    frame_count: int
    start_frame: int
    end_frame: int
    motion_speed_percent: int
    designer_prompt: str
    scene_prompt: str
    narration_line: Optional[str] = None
    visual_focus: Optional[str] = None
    source_scenario: Optional[str] = None
    asset_source: Optional[str] = None
    product_index: Optional[int] = None
    asset_ref: Optional[str] = None
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None


class LocalDesignerEngineFrame(BaseModel):
    frame_index: int
    cut: int
    title: str
    image_path: str
    image_data_url: Optional[str] = None
    continuity_score: float
    motion_delta: Optional[float] = None


class LocalDesignerEngineSubtitleCue(BaseModel):
    start_ms: int
    end_ms: int
    text: str
    chars_per_second: float


class LocalDesignerEngineRunResponse(BaseModel):
    run_id: str
    title: str
    scenario_script: str
    output_dir: str
    duration_seconds: int
    frames_per_second: int
    total_frames: int
    storyboard: List[LocalDesignerEngineCut]
    frames: List[LocalDesignerEngineFrame]
    subtitle_cues: List[LocalDesignerEngineSubtitleCue]
    average_motion_delta: Optional[float] = None
    static_motion_warning: Optional[str] = None
    auto_motion_boost_applied: Optional[bool] = None
    render_profile: Optional[dict] = None
    execution: Optional[dict] = None


class LocalVideoConnectorSection(BaseModel):
    section_id: str
    title: str
    cut_start: int
    cut_end: int
    frame_start: int
    frame_end: int
    duration_sec: float
    transition: str
    editorial_prompt: str
    subtitle_start_ms: int
    subtitle_end_ms: int
    manifest_path: str


class LocalVideoConnectorPlanRequest(BaseModel):
    title: str = Field(default="비디오 연결 라인", min_length=1, max_length=200)
    scenario_script: str = Field(min_length=2, max_length=4000)
    duration_seconds: int = Field(default=5, ge=1, le=60)
    frames_per_second: int = Field(default=8, ge=1, le=24)
    total_frames: int = Field(ge=1, le=2000)
    storyboard: List[LocalDesignerEngineCut]
    frames: List[LocalDesignerEngineFrame]
    subtitle_cues: List[LocalDesignerEngineSubtitleCue] = Field(default_factory=list)


class LocalVideoConnectorPlanResponse(BaseModel):
    run_id: str
    title: str
    scenario_script: str
    output_dir: str
    ffconcat_path: str
    sections: List[LocalVideoConnectorSection]
    execution: Optional[dict] = None


class ExecutionIdentity(BaseModel):
    flow_id: str
    step_id: str
    action: str
    route_id: str
    front_block_id: str


class AdStrategyPlan(BaseModel):
    primary_strategy: str
    alternatives: List[str] = Field(default_factory=list)
    hook_style: str
    campaign_goal: str
    rationale: List[str] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class AudienceProfileItem(BaseModel):
    id: str
    label: str
    intent: str
    pain_points: List[str] = Field(default_factory=list)
    tone: str
    cta_style: str


class AudienceProfilePlan(BaseModel):
    profiles: List[AudienceProfileItem] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class CreativeVariantItem(BaseModel):
    variant_id: str
    strategy_type: str
    hook_style: str
    narrative_style: str
    cta_style: str
    platform_target: str
    audience_id: str
    audience_label: str


class CreativeVariantPlan(BaseModel):
    variants: List[CreativeVariantItem] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class StoryStateSection(BaseModel):
    section_id: str
    title: str
    role_type: str
    object_type: str
    location_type: str
    emotion: str
    action: str
    camera_style: str
    lighting_style: str
    continuity_rule: str
    allowed_changes: List[str] = Field(default_factory=list)
    source_text: str
    variant_ids: List[str] = Field(default_factory=list)


class StoryStatePlan(BaseModel):
    sections: List[StoryStateSection] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class PlatformFormatItem(BaseModel):
    platform: str
    aspect_ratio: str
    caption_density: str
    cta_density: str
    duration_profiles: List[int] = Field(default_factory=list)


class PlatformFormatPlan(BaseModel):
    formats: List[PlatformFormatItem] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class CaptionVariantItem(BaseModel):
    variant_id: str
    headline: str
    body: str
    cta: str
    subtitle_speed: float
    tone: str


class CaptionPlan(BaseModel):
    captions: List[CaptionVariantItem] = Field(default_factory=list)
    execution: Optional[ExecutionIdentity] = None


class LocalCampaignPlanRequest(BaseModel):
    title: str = Field(default="멀티 광고 캠페인", min_length=1, max_length=200)
    scenario_script: str = Field(min_length=2, max_length=4000)
    product_catalog: List[str] = Field(default_factory=list)
    background_prompt: Optional[str] = None
    caption_text: Optional[str] = None
    portrait_image_prompt: Optional[str] = None
    storyboard: List[dict] = Field(default_factory=list)
    action_template_key: Optional[str] = None
    motion_tempo: Optional[str] = None
    brand_tone: Optional[str] = None
    campaign_goal: str = Field(default="conversion", min_length=1, max_length=50)
    platform_targets: List[str] = Field(default_factory=list)
    audience_input: List[str] = Field(default_factory=list)
    creative_modes: List[str] = Field(default_factory=list)
    duration_profiles: List[int] = Field(default_factory=lambda: [5, 15, 30, 60])
    subtitle_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    preview_fps: int = Field(default=8, ge=1, le=24)
    autonomy_level: str = Field(default="full", min_length=1, max_length=50)


class LocalCampaignPlanResponse(BaseModel):
    strategy_plan: AdStrategyPlan
    audience_plan: AudienceProfilePlan
    variant_plan: CreativeVariantPlan
    story_state_plan: StoryStatePlan
    format_plan: PlatformFormatPlan
    caption_plan: CaptionPlan
    image_line: LocalDesignerEngineRunResponse
    video_line: LocalVideoConnectorPlanResponse
    execution: Optional[ExecutionIdentity] = None


class ImageGenerationEngineResponse(BaseModel):
    engine_id: str
    backend_type: str
    continuity_mode: str
    image_line: LocalDesignerEngineRunResponse
    execution: Optional[ExecutionIdentity] = None


class VideoGenerationEngineResponse(BaseModel):
    engine_id: str
    connector_mode: str
    video_line: LocalVideoConnectorPlanResponse
    execution: Optional[ExecutionIdentity] = None


class ImageToVideoPipelineRequest(BaseModel):
    title: str = Field(default="이미지-비디오 연결 파이프라인", min_length=1, max_length=200)
    scenario_script: str = Field(min_length=2, max_length=4000)
    duration_seconds: int = Field(default=5, ge=1, le=60)
    frames_per_second: int = Field(default=8, ge=1, le=24)
    subtitle_speed: float = Field(default=1.0, ge=0.5, le=2.0)


class ImageToVideoPipelineResponse(BaseModel):
    pipeline_id: str
    image_engine: ImageGenerationEngineResponse
    video_engine: VideoGenerationEngineResponse
    execution: Optional[ExecutionIdentity] = None


class FinalVideoRenderRequest(BaseModel):
    title: str = Field(default="final-video-render", min_length=1, max_length=200)
    ffconcat_path: str = Field(min_length=1, max_length=2000)
    frames_per_second: int = Field(default=8, ge=1, le=60)
    duration_seconds: Optional[int] = Field(default=None, ge=1, le=60)
    expected_total_frames: Optional[int] = Field(default=None, ge=1, le=5000)
    output_dir: Optional[str] = None
    output_basename: str = Field(default="final_output.mp4", min_length=1, max_length=200)


class FinalVideoRenderResponse(BaseModel):
    render_id: str
    status: str
    ffconcat_path: str
    output_mp4_path: Optional[str] = None
    log_path: Optional[str] = None
    error_message: Optional[str] = None
    execution: Optional[ExecutionIdentity] = None


class SelfRunVideoJobRequest(BaseModel):
    title: str = Field(default="self-run-video-job", min_length=1, max_length=200)
    scenario_script: str = Field(min_length=2, max_length=4000)
    duration_seconds: int = Field(default=5, ge=1, le=60)
    frames_per_second: int = Field(default=8, ge=1, le=24)
    subtitle_speed: float = Field(default=1.0, ge=0.5, le=2.0)


class SelfRunVideoJobResponse(BaseModel):
    job_id: str
    status: str
    output_dir: Optional[str] = None
    ffconcat_path: Optional[str] = None
    output_mp4_path: Optional[str] = None
    log_path: Optional[str] = None
    error_message: Optional[str] = None
    execution: Optional[ExecutionIdentity] = None


class SelfRunVideoWorkerStatus(BaseModel):
    running: bool
    queue_depth: int
    active_job_id: Optional[str] = None
    completed_job_count: int = 0
    execution: Optional[ExecutionIdentity] = None


class CustomerOrchestratorCompletionCreate(BaseModel):
    trace_id: Optional[str] = None
    flow_id: Optional[str] = None
    step_id: Optional[str] = None
    action: Optional[str] = None
    project_name: str = Field(min_length=1, max_length=200)
    mode: str = Field(min_length=1, max_length=50)
    attempts: int = Field(default=0, ge=0)
    output_dir: Optional[str] = None
    postcheck_ok: Optional[bool] = None
    gate_passed: bool = False
    override_used: bool = False


class CustomerOrchestratorCompletion(BaseModel):
    id: int
    user_id: int
    trace_id: Optional[str] = None
    flow_id: Optional[str] = None
    step_id: Optional[str] = None
    action: Optional[str] = None
    project_name: str
    mode: str
    attempts: int
    output_dir: Optional[str] = None
    postcheck_ok: Optional[bool] = None
    gate_passed: bool
    override_used: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeatureExecutionLog(BaseModel):
    id: int
    user_id: Optional[int] = None
    entity_type: str
    entity_id: str
    trace_id: str
    flow_id: str
    step_id: str
    action: str
    status: str
    message: str
    payload_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeatureRetryQueue(BaseModel):
    id: int
    user_id: Optional[int] = None
    entity_type: str
    entity_id: str
    trace_id: str
    flow_id: str
    step_id: str
    action: str
    queue_name: str
    status: str
    payload_json: Optional[str] = None
    last_error: Optional[str] = None
    attempt_count: int
    max_attempts: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
