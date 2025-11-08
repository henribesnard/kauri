"""
Message model for storing individual messages in conversations
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.models.database import Base


class Message(Base):
    """
    Message model - represents a single message in a conversation
    Can be from 'user' or 'assistant'
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    # RAG-specific fields
    sources = Column(JSONB, default=list, nullable=True)  # List of source documents
    extra_data = Column("metadata", JSONB, default=dict, nullable=True)  # model_used, tokens, latency, intent_type, etc.

    # User feedback (only for assistant messages)
    user_feedback = Column(JSONB, default=dict, nullable=True)  # {"rating": "positive"|"negative", "comment": str, "feedback_at": timestamp}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_message_role"),
        Index('idx_message_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_message_deleted', 'deleted_at'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"

    def to_dict(self, include_deleted=False):
        """Convert to dictionary for JSON serialization"""
        if self.deleted_at and not include_deleted:
            return None

        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "metadata": self.extra_data,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None
        }
