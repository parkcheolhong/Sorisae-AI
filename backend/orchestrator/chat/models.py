from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AutoConnectMeta(BaseModel):
    connection_id: Optional[str] = None
    flow_id: Optional[str] = None
    step_id: Optional[str] = None
    action: Optional[str] = None
    route_id: Optional[str] = None
    panel_id: Optional[str] = None
    capability_id: Optional[str] = None
    command_id: Optional[str] = None


class ConversationMessage(BaseModel):
    role: str
    content: str
    speaker: Optional[str] = None
    step_id: Optional[str] = None
    step_title: Optional[str] = None
    timestamp: Optional[str] = None
    connection_id: Optional[str] = None
    flow_id: Optional[str] = None
    action: Optional[str] = None
    route_id: Optional[str] = None
    panel_id: Optional[str] = None


class OrchestratorChatRequest(BaseModel):
    task: str = ""
    message: str
    agent_key: str = "chat"
    mode: str = "manual_9step"
    manual_mode: bool = True
    companion_mode: str = "hybrid"
    conversation_mode: str = "auto"
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    max_tokens: int = 768
    lightweight: bool = False
    multi_turn_enabled: bool = True
    response_style: str = "balanced"
    tone_preset: str = "auto"
    reverse_question_mode: Optional[str] = None
    message_kind: Optional[str] = None
    conversation: List[Dict[str, Any]] = Field(default_factory=list)
    context_tags: List[str] = Field(default_factory=list)
    project_root: Optional[str] = None
    project_memory: Dict[str, Any] = Field(default_factory=dict)
    auto_connect: Optional[AutoConnectMeta] = None


class WebGroundingItem(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: str
    domain: Optional[str] = None
    source_type: str = "general"
    trust_score: float = 0


class AdvisoryQuestion(BaseModel):
    prompt: str
    reason: Optional[str] = None


class AdvisoryEvidenceItem(BaseModel):
    title: str
    source_label: str
    source_type: str = "general"
    trust_score: float = 0
    why_it_matters: str
    url: Optional[str] = None


class AdvisoryNextAction(BaseModel):
    title: str
    action_type: str = "chat"
    detail: str
    recommended_mode: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)


class ProposalItem(BaseModel):
    title: str
    category: str = "proposal"
    detail: str
    benefit: Optional[str] = None
    tradeoff: Optional[str] = None


class TechnologyRecommendation(BaseModel):
    title: str
    source: str = "llm"
    adoption_risk: str
    implementation_difficulty: str
    operating_cost: str
    alternative: str
    rationale: str


class TargetPatchHint(BaseModel):
    file_id: str
    section_id: Optional[str] = None
    feature_id: Optional[str] = None
    chunk_id: Optional[str] = None
    reason: str


class FlowTraceStep(BaseModel):
    flow_id: str
    step_id: str
    action: str
    title: str
    trace_id: str
    step_number: Optional[int] = None
    state: Optional[str] = None


class FlowTraceCommand(BaseModel):
    command_id: str
    command_text: str
    flow_id: str
    step_id: str
    action: str
    title: str
    trace_id: str


class OrchestratorStageChatContext(BaseModel):
    run_id: Optional[str] = None
    stage_id: Optional[str] = None
    stage_label: Optional[str] = None
    stage_title: Optional[str] = None
    stage_status: Optional[str] = None
    scope: Optional[str] = None
    project_name: Optional[str] = None
    semi_auto_step_count: int = 10
    semi_auto_mode: str = "manual_10step"
    command_modes: List[str] = Field(default_factory=lambda: ["/run", "/pass", "/fix", "/fail", "/verify", "/search", "/news", "/ask", "/revise", "/resume"])
    collaboration_modes: List[str] = Field(default_factory=lambda: ["directive", "research", "news", "companion", "revision"])
    can_pause_for_revision: bool = True
    can_search_web: bool = True
    can_companion_chat: bool = True
    pending_revision_note: Optional[str] = None
    last_command: Optional[str] = None


class OrchestratorChatResponse(BaseModel):
    reply: ConversationMessage
    conversation: List[ConversationMessage] = Field(default_factory=list)
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    grounding_mode: str = "internal"
    grounding_note: Optional[str] = None
    companion_mode: str = "hybrid"
    web_results: List[WebGroundingItem] = Field(default_factory=list)
    suggested_companion_mode: Optional[str] = None
    suggested_companion_reason: Optional[str] = None
    conversation_stage: str = "general"
    clarification_questions: List[AdvisoryQuestion] = Field(default_factory=list)
    evidence_highlights: List[AdvisoryEvidenceItem] = Field(default_factory=list)
    next_action_suggestions: List[AdvisoryNextAction] = Field(default_factory=list)
    flow_trace: List[FlowTraceStep] = Field(default_factory=list)
    command_plan: List[FlowTraceCommand] = Field(default_factory=list)
    active_trace: Optional[FlowTraceStep] = None
    message_kind: str = "general"
    multi_turn_enabled: bool = True
    conversation_summary: Optional[str] = None
    suggested_prompts: List[str] = Field(default_factory=list)
    inferred_goal: Optional[str] = None
    proposal_items: List[ProposalItem] = Field(default_factory=list)
    new_technology_candidates: List[str] = Field(default_factory=list)
    technology_recommendations: List[TechnologyRecommendation] = Field(default_factory=list)
    target_patch_hints: List[TargetPatchHint] = Field(default_factory=list)
    project_root: Optional[str] = None
    project_memory: Dict[str, Any] = Field(default_factory=dict)
    auto_connect: Optional[AutoConnectMeta] = None
    stage_chat: Optional[OrchestratorStageChatContext] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
