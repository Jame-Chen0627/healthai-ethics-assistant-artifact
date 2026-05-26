from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..data import kb
from ..models import ChatMessage, ChatRequirementPreference, ChatSession, User
from ..schemas import (
    CreateRequirementsRequest,
    CreateRequirementsResponse,
    ValidateRequirementsRequest,
    ValidateRequirementsResponse,
    CompareScenariosRequest,
    CompareScenariosResponse,
    EthicsChatRequest,
    EthicsChatResponse,
    FrameworkInfo,
    FindingInfo,
)
from ..services import ethics_service
from .auth import get_current_user

router = APIRouter(prefix="/ethics", tags=["ethics"])


# ── Knowledge-base lookups ─────────────────────────────────────────


@router.get("/frameworks", response_model=list[FrameworkInfo])
def list_frameworks() -> list[dict]:
    return kb.get_frameworks()


@router.get("/framework-names")
def list_framework_names() -> dict:
    return {"frameworks": kb.get_framework_names()}


@router.get("/findings", response_model=list[FindingInfo])
def list_findings(
    dimension: str | None = None,
    stakeholder: str | None = None,
    source: str | None = None,
) -> list[dict]:
    return kb.find_findings(dimension=dimension, stakeholder=stakeholder, source=source)


# ── Helpers ────────────────────────────────────────────────────────


def _persist(
    db: Session,
    user: User | None,
    session_id: int | None,
    mode: str,
    stakeholder: str,
    request_payload: dict,
    response_payload: dict,
) -> None:
    """Persist request + response into a chat session if the user is logged in."""
    if user is None or session_id is None:
        return
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or sess.user_id != user.id:
        return
    sess.mode = mode
    sess.stakeholder = stakeholder
    db.add(
        ChatMessage(
            session_id=sess.id,
            role="user",
            content=__safe_dump({"mode": mode, "request": request_payload}),
        )
    )
    db.add(
        ChatMessage(
            session_id=sess.id,
            role="assistant",
            content=__safe_dump({"mode": mode, "response": response_payload}),
        )
    )
    db.commit()


def __safe_dump(obj: dict) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


def _suppressed_for_session(db: Session, user: User | None, session_id: int | None) -> list[dict]:
    if user is None or session_id is None:
        return []
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or sess.user_id != user.id:
        return []
    rows = (
        db.query(ChatRequirementPreference)
        .filter(
            ChatRequirementPreference.session_id == sess.id,
            ChatRequirementPreference.status == "suppressed",
        )
        .order_by(ChatRequirementPreference.updated_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "title": r.title,
            "dimension": r.dimension,
            "requirement_text": r.requirement_text,
        }
        for r in rows
    ]


# ── Three modes ───────────────────────────────────────────────────


@router.post("/create", response_model=CreateRequirementsResponse)
async def create(
    payload: CreateRequirementsRequest,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = await ethics_service.create_requirements(
            stakeholder=payload.stakeholder,
            system_context=payload.system_context,
            concern_text=payload.concern_text,
            dimensions=payload.dimensions,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {type(e).__name__}: {e}")

    _persist(db, user, payload.session_id, "create", payload.stakeholder, payload.model_dump(), result)
    return result


@router.post("/validate", response_model=ValidateRequirementsResponse)
async def validate(
    payload: ValidateRequirementsRequest,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = await ethics_service.validate_requirements(
            stakeholder=payload.stakeholder,
            requirement_text=payload.requirement_text,
            framework_names=payload.framework_names,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {type(e).__name__}: {e}")

    _persist(db, user, payload.session_id, "validate", payload.stakeholder, payload.model_dump(), result)
    return result


@router.post("/compare", response_model=CompareScenariosResponse)
async def compare(
    payload: CompareScenariosRequest,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = await ethics_service.compare_scenarios(
            stakeholder=payload.stakeholder,
            requirement_text=payload.requirement_text,
            dimension=payload.dimension,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {type(e).__name__}: {e}")

    _persist(db, user, payload.session_id, "compare", payload.stakeholder, payload.model_dump(), result)
    return result


# ── Unified chat (auto-classify + dispatch) ───────────────────────


@router.post("/chat", response_model=EthicsChatResponse, response_model_by_alias=True)
async def chat(
    payload: EthicsChatRequest,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        debug_records: list | None = [] if payload.debug else None
        params_override = None
        if (
            payload.model_override
            or payload.temperature_override is not None
            or payload.max_tokens_override is not None
        ):
            params_override = {
                "model": payload.model_override,
                "temperature": payload.temperature_override,
                "max_tokens": payload.max_tokens_override,
            }
        result = await ethics_service.chat(
            stakeholder=payload.stakeholder,
            prompt=payload.prompt,
            system_context_hint=payload.system_context,
            custom_persona=payload.custom_persona,
            rag_docs=payload.rag_docs,
            suppressed_requirements=(
                _suppressed_for_session(db, user, payload.session_id)
                + (payload.suppressed_requirements or [])
            ),
            topic=payload.topic,
            topic_prompt=payload.topic_prompt,
            params_override=params_override,
            debug_sink=debug_records,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {type(e).__name__}: {e}")

    message_id: int | None = None

    if user is not None and payload.session_id is not None:
        sess = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if sess and sess.user_id == user.id:
            sess.mode = result["mode"]
            sess.stakeholder = payload.stakeholder
            if payload.system_context is not None:
                sess.system_context = payload.system_context
            if payload.custom_persona is not None:
                sess.custom_persona = payload.custom_persona
            if payload.topic is not None:
                sess.topic = payload.topic
            if payload.topic_prompt is not None:
                sess.topic_prompt = payload.topic_prompt
            # Auto-title from first user message
            if sess.title in (None, "", "New Session", "New Chat") and not sess.messages:
                snippet = payload.prompt.strip().splitlines()[0]
                sess.title = (snippet[:60] + "…") if len(snippet) > 60 else snippet
            db.add(
                ChatMessage(session_id=sess.id, role="user", content=payload.prompt)
            )
            assistant_msg = ChatMessage(
                session_id=sess.id,
                role="assistant",
                content=__safe_dump(result),
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            message_id = assistant_msg.id

    result["message_id"] = message_id
    if debug_records is not None:
        result["debug"] = debug_records
    # Map service key "validate" → schema field alias
    return result
