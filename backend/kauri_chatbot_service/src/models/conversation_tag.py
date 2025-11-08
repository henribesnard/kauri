"""
ConversationTag model for tagging and categorizing conversations
"""
import uuid
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.database import Base


class ConversationTag(Base):
    """
    ConversationTag model - represents tags/categories for conversations
    Examples: "comptabilité", "fiscalité", "audit", "ohada", etc.
    """
    __tablename__ = "conversation_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tag = Column(String(50), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="tags")

    # Constraints - prevent duplicate tags per conversation
    __table_args__ = (
        UniqueConstraint('conversation_id', 'tag', name='uq_conversation_tag'),
        Index('idx_tag_name', 'tag'),
    )

    def __repr__(self):
        return f"<ConversationTag(id={self.id}, conversation_id={self.conversation_id}, tag={self.tag})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "tag": self.tag
        }
