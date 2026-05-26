from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="New Session")
    # 'create' | 'validate' | 'compare' | 'chat' (free-form fallback)
    mode = Column(String(20), default="chat")
    # 'HCP' | 'SEng' | 'HCR'
    stakeholder = Column(String(20), nullable=True)
    # Free-form topic label chosen at chat creation, e.g. "HealthAI Ethics",
    # "Cybersecurity Requirements", or a user-supplied custom topic name.
    topic = Column(String(120), nullable=True)
    # Optional free-form prompt describing the custom topic; used to steer
    # the LLM when the topic is not one of the built-ins.
    topic_prompt = Column(Text, nullable=True)
    # Per-chat context restored whenever the session is reopened.
    system_context = Column(Text, nullable=True)
    custom_persona = Column(Text, nullable=True)
    custom_persona_name = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )
    requirement_preferences = relationship(
        "ChatRequirementPreference",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatRequirementPreference.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class ChatRequirementPreference(Base):
    __tablename__ = "chat_requirement_preferences"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # accepted | rejected | suppressed
    requirement_key = Column(String(64), nullable=False, index=True)
    title = Column(String(240), nullable=True)
    dimension = Column(String(40), nullable=True)
    description = Column(Text, nullable=True)
    requirement_text = Column(Text, nullable=False)
    guideline_refs = Column(Text, nullable=True)
    source_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("ChatSession", back_populates="requirement_preferences")
