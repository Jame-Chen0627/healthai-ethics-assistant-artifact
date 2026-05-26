from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Shared literals ───────────────────────────────────────────────


Stakeholder = Literal["HCP", "SEng", "HCR"]
Mode = Literal["create", "validate", "compare", "chat"]
Dimension = Literal["privacy", "safety", "bias", "transparency", "accountability"]
RequirementPreferenceStatus = Literal["accepted", "rejected", "suppressed"]


# ── Chat (free-form fallback) ─────────────────────────────────────


class ChatMessageInput(BaseModel):
    role: str = Field(..., description="'user' | 'assistant' | 'system'")
    content: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    mode: Optional[Mode] = "chat"
    stakeholder: Optional[Stakeholder] = None
    topic: Optional[str] = Field(None, max_length=120, description="Topic label for this chat (e.g. 'HealthAI Ethics', 'Cybersecurity Requirements', custom name).")
    topic_prompt: Optional[str] = Field(None, description="Free-form description of the custom topic, used to steer the LLM.")
    system_context: Optional[str] = Field(None, description="Per-chat project/system context restored with the session.")
    custom_persona: Optional[str] = Field(None, description="Per-chat custom or inferred persona prompt restored with the session.")
    custom_persona_name: Optional[str] = Field(None, max_length=120, description="Display label for the per-chat custom persona.")


class ChatSessionRename(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    topic: Optional[str] = Field(None, max_length=120)
    topic_prompt: Optional[str] = None


class RequirementPreferenceInput(BaseModel):
    status: RequirementPreferenceStatus
    title: Optional[str] = Field(None, max_length=240)
    dimension: Optional[str] = Field(None, max_length=40)
    description: Optional[str] = None
    requirement_text: str = Field(..., min_length=1)
    guideline_refs: List[dict] = Field(default_factory=list)
    source_message_id: Optional[int] = None


class RequirementPreferenceResponse(RequirementPreferenceInput):
    id: int
    session_id: int
    requirement_key: str
    created_at: datetime
    updated_at: datetime


class ChatSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    mode: str
    stakeholder: Optional[str]
    topic: Optional[str] = None
    topic_prompt: Optional[str] = None
    custom_persona_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    system_context: Optional[str] = None
    custom_persona: Optional[str] = None
    messages: List[ChatMessageResponse]


class ChatStreamRequest(BaseModel):
    messages: List[ChatMessageInput] = Field(..., description="Full conversation history including the new user message")
    session_id: Optional[int] = Field(None, description="If provided and user is authenticated, persist messages to this session")
    stakeholder: Optional[Stakeholder] = None


# ── Knowledge base info ───────────────────────────────────────────


class FrameworkInfo(BaseModel):
    id: str
    framework: str
    article: str
    title: str
    summary: str
    detail: Optional[str] = None
    applies_to: List[str]
    source_label: Optional[str] = None
    source_url: Optional[str] = None


class FindingInfo(BaseModel):
    id: str
    source: str
    stakeholder: str
    dimension: str
    quote: str
    implication: str


# ── Ethics: Create Requirements ───────────────────────────────────


class GuidelineRef(BaseModel):
    id: str
    framework: str
    article: str
    title: Optional[str] = ""


class EthicalConcern(BaseModel):
    dimension: Dimension
    title: str
    description: str
    requirement: str
    guideline_refs: List[GuidelineRef] = Field(default_factory=list)


class CreateRequirementsRequest(BaseModel):
    stakeholder: Stakeholder
    system_context: str = Field(..., description="Description of the AI system being built")
    concern_text: str = Field(..., description="Free-text ethical concern to address")
    dimensions: Optional[List[Dimension]] = Field(
        None, description="Optional filter to bias the LLM toward specific ethical dimensions"
    )
    session_id: Optional[int] = None


class CreateRequirementsResponse(BaseModel):
    concerns: List[EthicalConcern]


# ── Ethics: Validate Requirements ─────────────────────────────────


class ValidationCheck(BaseModel):
    id: str
    framework: str
    article: str
    title: Optional[str] = ""
    status: Literal["valid", "missing", "not_applicable"]
    gap: str = ""
    suggested_addition: str = ""


class ValidateRequirementsRequest(BaseModel):
    stakeholder: Stakeholder
    requirement_text: str
    framework_names: Optional[List[str]] = Field(
        None, description="Optional subset of framework names to validate against (e.g. ['EU AI Act'])"
    )
    session_id: Optional[int] = None


class ValidateRequirementsResponse(BaseModel):
    checks: List[ValidationCheck]
    summary: str


# ── Ethics: Compare with Real-World Scenarios ─────────────────────


class ScenarioSuggestion(BaseModel):
    id: str
    source: Literal["interview", "reddit"]
    stakeholder: Stakeholder
    dimension: Dimension
    quote: str
    recommendation: str


class CompareScenariosRequest(BaseModel):
    stakeholder: Stakeholder
    requirement_text: str
    dimension: Optional[Dimension] = None
    session_id: Optional[int] = None


class CompareScenariosResponse(BaseModel):
    original_requirement: str
    suggestions: List[ScenarioSuggestion]
    enhanced_requirement: str


# ── Ethics: Unified chat (auto-classify) ──────────────────────────


class EthicsChatRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prompt: str = Field(..., min_length=1, description="Free-form user message")
    stakeholder: Stakeholder
    session_id: Optional[int] = None
    system_context: Optional[str] = Field(
        None,
        description="Optional sticky context for the session (e.g. 'diagnostic imaging AI'). Used by Create mode.",
    )
    custom_persona: Optional[str] = Field(
        None,
        description="Optional free-form persona description that overrides the built-in stakeholder label in prompts.",
    )
    topic: Optional[str] = Field(
        None, max_length=120,
        description="Topic label for this chat (e.g. 'Cybersecurity Requirements'). Steers the LLM when not the default healthcare topic.",
    )
    topic_prompt: Optional[str] = Field(
        None,
        description="Free-form description of a custom topic; injected into the system prompt to steer the LLM.",
    )
    debug: bool = Field(
        False,
        description="When true, the response includes a `debug` array with the full prompt + raw Gemini response for each LLM call. Used by Developer Mode.",
    )
    model_override: Optional[str] = Field(
        None,
        description="Developer Mode: override the Gemini model name for this request (e.g. 'gemini-2.5-pro').",
    )
    temperature_override: Optional[float] = Field(
        None, ge=0.0, le=2.0,
        description="Developer Mode: override the temperature for every LLM call in this request.",
    )
    max_tokens_override: Optional[int] = Field(
        None, ge=64, le=32768,
        description="Developer Mode: override maxOutputTokens for every LLM call in this request.",
    )
    rag_docs: Optional[List[dict]] = Field(
        None,
        description="Developer Mode: list of {name, content} reference documents prepended to the LLM user content as additional context.",
    )
    suppressed_requirements: Optional[List[dict]] = Field(
        None,
        description="Per-chat requirements the user cleared/suppressed; used to avoid similar new requirements.",
    )


class EthicsChatResponse(BaseModel):
    mode: Literal["create", "validate", "compare"]
    assistant_text: str = Field(
        "", description="Short natural-language preamble shown above the rendered cards"
    )
    create: Optional[CreateRequirementsResponse] = None
    validate_: Optional[ValidateRequirementsResponse] = Field(None, alias="validate")
    compare: Optional[CompareScenariosResponse] = None
    message_id: Optional[int] = None
    debug: Optional[list[dict]] = Field(
        None,
        description="Per-call debug records. Present only when the request set `debug=true`.",
    )

    model_config = ConfigDict(populate_by_name=True)
