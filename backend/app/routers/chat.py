"""Free-form chat fallback (SSE streaming) for the Ethics Assistant.

Persists into ChatSession/ChatMessage when the user is logged in and supplies
a session_id. The system prompt is biased toward the healthcare-AI ethics
domain, with optional stakeholder context.
"""

import hashlib
import json
import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from ..database import get_db
from ..models import ChatRequirementPreference, ChatSession, ChatMessage, User
from ..schemas import (
    ChatSessionCreate,
    ChatSessionRename,
    ChatSessionSummary,
    ChatSessionDetail,
    ChatMessageResponse,
    ChatStreamRequest,
    RequirementPreferenceInput,
    RequirementPreferenceResponse,
)
from ..services.docx_service import build_requirements_doc, build_requirements_preview
from ..services.llm_service import stream_chat_with_gemini
from .auth import get_current_user, require_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


_STAKEHOLDER_LABELS = {
    "HCP": "Healthcare Professional (clinician, nurse, radiologist)",
    "SEng": "Software Engineer building healthcare AI systems",
    "HCR": "Healthcare Researcher",
}


def _system_prompt_for(stakeholder: str | None, topic: str | None = None, topic_prompt: str | None = None) -> str:
    if topic and topic.strip().lower() not in ("", "healthai ethics", "healthai-ethics"):
        # Generic topic-aware assistant. The Create / Validate / Compare modes
        # remain available via the /ethics/chat endpoint; this prompt is the
        # free-form streaming fallback.
        base = (
            f"You are a Requirements Engineering Assistant for the topic: {topic.strip()}. "
            "Help the user reason about and refine implementable requirements. "
            "Be concise and concrete; cite well-known standards or guidelines for the topic when relevant."
        )
        if topic_prompt and topic_prompt.strip():
            base += f"\n\nTopic context provided by the user:\n{topic_prompt.strip()}"
    else:
        base = (
            "You are the HealthAI Ethics Assistant. You help users reason about "
            "ethical requirements for healthcare AI systems across five dimensions: "
            "privacy, safety, bias, transparency, and accountability. "
            "Reference EU AI Act and NIST AI RMF articles when relevant, and be concise."
        )
    if stakeholder and stakeholder in _STAKEHOLDER_LABELS:
        base += f"\n\nThe user is a {_STAKEHOLDER_LABELS[stakeholder]}; tailor wording accordingly."
    return base


def _get_owned_session(db: Session, session_id: int, user: User) -> ChatSession:
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


def _requirement_key(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _pref_payload(row: ChatRequirementPreference) -> dict:
    try:
        refs = json.loads(row.guideline_refs or "[]")
    except Exception:
        refs = []
    return {
        "id": row.id,
        "session_id": row.session_id,
        "status": row.status,
        "requirement_key": row.requirement_key,
        "title": row.title,
        "dimension": row.dimension,
        "description": row.description,
        "requirement_text": row.requirement_text,
        "guideline_refs": refs,
        "source_message_id": row.source_message_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _first_user_prompt(db: Session, session_id: int) -> str:
    row = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        .order_by(ChatMessage.id.asc())
        .first()
    )
    if not row:
        return ""
    text = row.content or ""
    try:
        parsed = json.loads(text)
        request = parsed.get("request") if isinstance(parsed, dict) else None
        if isinstance(request, dict):
            return (
                request.get("prompt")
                or request.get("concern_text")
                or request.get("requirement_text")
                or text
            )
    except Exception:
        pass
    return text


def _requirements_preview(db: Session, sess: ChatSession, chat_url: str | None = None) -> dict:
    rows = (
        db.query(ChatRequirementPreference)
        .filter(ChatRequirementPreference.session_id == sess.id)
        .order_by(ChatRequirementPreference.id.asc())
        .all()
    )
    prefs = [_pref_payload(r) for r in rows]
    return build_requirements_preview(
        sess,
        prefs,
        first_prompt=_first_user_prompt(db, sess.id),
        chat_url=chat_url,
    )


# ── Session CRUD ──────────────────────────────────────────────────


@router.post("/sessions", response_model=ChatSessionSummary, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = ChatSession(
        user_id=user.id,
        title=payload.title or "New Session",
        mode=payload.mode or "chat",
        stakeholder=payload.stakeholder,
        topic=payload.topic,
        topic_prompt=payload.topic_prompt,
        system_context=payload.system_context,
        custom_persona=payload.custom_persona,
        custom_persona_name=payload.custom_persona_name,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return ChatSessionSummary.model_validate(sess)


@router.get("/sessions", response_model=list[ChatSessionSummary])
def list_sessions(
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [ChatSessionSummary.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(
    session_id: int,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    return ChatSessionDetail(
        id=sess.id,
        title=sess.title,
        mode=sess.mode,
        stakeholder=sess.stakeholder,
        topic=sess.topic,
        topic_prompt=sess.topic_prompt,
        system_context=sess.system_context,
        custom_persona=sess.custom_persona,
        custom_persona_name=sess.custom_persona_name,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        messages=[ChatMessageResponse.model_validate(m) for m in sess.messages],
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionSummary)
def rename_session(
    session_id: int,
    payload: ChatSessionRename,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    fields = payload.model_fields_set
    if "title" in fields and payload.title is not None:
        sess.title = payload.title
    if "topic" in fields:
        sess.topic = payload.topic
    if "topic_prompt" in fields:
        sess.topic_prompt = payload.topic_prompt
    db.commit()
    db.refresh(sess)
    return ChatSessionSummary.model_validate(sess)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    db.delete(sess)
    db.commit()
    return None


# ── Requirement preferences / export ──────────────────────────────


@router.get("/sessions/{session_id}/requirements", response_model=list[RequirementPreferenceResponse])
def list_requirement_preferences(
    session_id: int,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    rows = (
        db.query(ChatRequirementPreference)
        .filter(ChatRequirementPreference.session_id == sess.id)
        .order_by(ChatRequirementPreference.updated_at.desc())
        .all()
    )
    return [_pref_payload(r) for r in rows]


@router.post("/sessions/{session_id}/requirements", response_model=RequirementPreferenceResponse)
def upsert_requirement_preference(
    session_id: int,
    payload: RequirementPreferenceInput,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    key = _requirement_key(payload.requirement_text)
    row = (
        db.query(ChatRequirementPreference)
        .filter(
            ChatRequirementPreference.session_id == sess.id,
            ChatRequirementPreference.requirement_key == key,
        )
        .first()
    )
    if row is None:
        row = ChatRequirementPreference(session_id=sess.id, requirement_key=key)
    row.status = payload.status
    row.title = payload.title
    row.dimension = payload.dimension
    row.description = payload.description
    row.requirement_text = payload.requirement_text
    row.guideline_refs = json.dumps(payload.guideline_refs or [], ensure_ascii=False)
    row.source_message_id = payload.source_message_id
    db.add(row)
    db.commit()
    db.refresh(row)
    return _pref_payload(row)


@router.get("/sessions/{session_id}/requirements-doc")
def export_requirements_doc(
    session_id: int,
    chat_url: str | None = None,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    preview = _requirements_preview(db, sess, chat_url=chat_url)
    doc = build_requirements_doc(preview)
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", sess.title or "requirements").strip("_")
    return Response(
        content=doc,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename or "requirements"}.docx"'},
    )


@router.get("/sessions/{session_id}/requirements-doc-preview")
def preview_requirements_doc(
    session_id: int,
    chat_url: str | None = None,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_owned_session(db, session_id, user)
    return _requirements_preview(db, sess, chat_url=chat_url)


# ── Streaming chat (auth optional) ────────────────────────────────


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_msg = payload.messages[-1]
    if last_msg.role != "user":
        raise HTTPException(status_code=400, detail="last message must be from user")

    system_context = _system_prompt_for(payload.stakeholder)

    sess_id_for_persistence: int | None = None
    persist_session_factory: sessionmaker | None = None
    if user is not None and payload.session_id is not None:
        sess = _get_owned_session(db, payload.session_id, user)
        # Re-derive system prompt now that we have the session's topic.
        system_context = _system_prompt_for(
            payload.stakeholder, topic=sess.topic, topic_prompt=sess.topic_prompt
        )
        user_msg = ChatMessage(session_id=sess.id, role="user", content=last_msg.content)
        db.add(user_msg)
        if sess.title in (None, "", "New Session", "New Chat") and len(sess.messages) == 0:
            sess.title = (last_msg.content[:60] + "…") if len(last_msg.content) > 60 else last_msg.content
        if payload.stakeholder and not sess.stakeholder:
            sess.stakeholder = payload.stakeholder
        db.commit()
        sess_id_for_persistence = sess.id
        persist_session_factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)

    msgs_for_llm = [{"role": m.role, "content": m.content} for m in payload.messages]

    async def event_generator():
        full_text_parts: list[str] = []
        try:
            async for chunk in stream_chat_with_gemini(
                msgs_for_llm, context_text=system_context
            ):
                full_text_parts.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
        except Exception as e:
            err_payload = {"type": "error", "message": f"{type(e).__name__}: {e}"}
            yield f"data: {json.dumps(err_payload)}\n\n"
            return

        full_text = "".join(full_text_parts)
        message_id: int | None = None
        if sess_id_for_persistence is not None and persist_session_factory is not None and full_text:
            persist_db = persist_session_factory()
            try:
                assistant_msg = ChatMessage(
                    session_id=sess_id_for_persistence,
                    role="assistant",
                    content=full_text,
                )
                persist_db.add(assistant_msg)
                sess_row = persist_db.query(ChatSession).filter(ChatSession.id == sess_id_for_persistence).first()
                if sess_row is not None:
                    sess_row.title = sess_row.title  # touch row
                persist_db.commit()
                persist_db.refresh(assistant_msg)
                message_id = assistant_msg.id
            finally:
                persist_db.close()

        done_payload = {"type": "done", "message_id": message_id}
        yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
