"""
Conversation model for storing user conversation threads
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.models.database import Base


class Conversation(Base):
    """
    Conversation model - represents a thread of messages between user and assistant
    """
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Advanced features
    is_archived = Column(Boolean, default=False, nullable=False)
    extra_data = Column("metadata", JSONB, default=dict, nullable=True)  # Renamed to avoid SQLAlchemy conflict

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    tags = relationship(
        "ConversationTag",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_user_updated', 'user_id', 'updated_at'),
        Index('idx_conversation_user_archived', 'user_id', 'is_archived'),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_archived": self.is_archived,
            "metadata": self.extra_data,
            "message_count": len(self.messages) if self.messages else 0
        }
