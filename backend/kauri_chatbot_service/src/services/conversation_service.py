"""
Conversation Service - Business logic for managing conversations and messages
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from src.models.conversation import Conversation
from src.models.message import Message
from src.models.conversation_tag import ConversationTag


class ConversationService:
    """Service for managing conversations and messages"""

    @staticmethod
    def create_conversation(
        db: Session,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation

        Args:
            db: Database session
            user_id: UUID of the user
            title: Optional title for the conversation
            metadata: Optional metadata dictionary

        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
            extra_data=metadata or {}
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Get existing conversation or create new one

        Args:
            db: Database session
            user_id: UUID of the user
            conversation_id: Optional existing conversation ID
            title: Optional title for new conversation

        Returns:
            Conversation object
        """
        if conversation_id:
            conversation = db.query(Conversation).filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            ).first()

            if conversation:
                return conversation

        # Create new conversation
        return ConversationService.create_conversation(db, user_id, title)

    @staticmethod
    def get_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Conversation]:
        """
        Get a conversation by ID (with user validation)

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)

        Returns:
            Conversation object or None
        """
        return db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        ).first()

    @staticmethod
    def list_user_conversations(
        db: Session,
        user_id: uuid.UUID,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """
        List conversations for a user

        Args:
            db: Database session
            user_id: UUID of the user
            include_archived: Include archived conversations
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of Conversation objects
        """
        query = db.query(Conversation).filter(Conversation.user_id == user_id)

        if not include_archived:
            query = query.filter(Conversation.is_archived == False)

        return query.order_by(desc(Conversation.updated_at)).limit(limit).offset(offset).all()

    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        """
        Update a conversation

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)
            title: Optional new title
            is_archived: Optional archived status
            metadata: Optional metadata to merge

        Returns:
            Updated Conversation object or None
        """
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)

        if not conversation:
            return None

        if title is not None:
            conversation.title = title

        if is_archived is not None:
            conversation.is_archived = is_archived

        if metadata is not None:
            # Merge metadata
            current_metadata = conversation.extra_data or {}
            current_metadata.update(metadata)
            conversation.extra_data = current_metadata

        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Delete a conversation (cascade deletes messages and tags)

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)

        Returns:
            True if deleted, False if not found
        """
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)

        if not conversation:
            return False

        db.delete(conversation)
        db.commit()
        return True

    @staticmethod
    def save_message(
        db: Session,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Save a new message to a conversation

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            role: 'user' or 'assistant'
            content: Message content
            sources: Optional list of source documents
            metadata: Optional metadata (model, tokens, latency, etc.)

        Returns:
            Created Message object
        """
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            extra_data=metadata or {}
        )
        db.add(message)

        # Update conversation's updated_at timestamp
        db.query(Conversation).filter(Conversation.id == conversation_id).update({
            "updated_at": datetime.utcnow()
        })

        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
        include_deleted: bool = False
    ) -> List[Message]:
        """
        Get messages from a conversation

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)
            limit: Optional limit on number of messages (most recent)
            include_deleted: Include soft-deleted messages

        Returns:
            List of Message objects
        """
        # Verify user owns the conversation
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return []

        query = db.query(Message).filter(Message.conversation_id == conversation_id)

        if not include_deleted:
            query = query.filter(Message.deleted_at.is_(None))

        query = query.order_by(Message.created_at)

        if limit:
            # Get the last N messages
            total = query.count()
            if total > limit:
                query = query.offset(total - limit)

        return query.all()

    @staticmethod
    def soft_delete_message(
        db: Session,
        message_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Soft delete a message

        Args:
            db: Database session
            message_id: UUID of the message
            user_id: UUID of the user (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        # Get message with conversation join for user validation
        message = db.query(Message).join(Conversation).filter(
            and_(
                Message.id == message_id,
                Conversation.user_id == user_id
            )
        ).first()

        if not message:
            return False

        message.deleted_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def add_tags(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        tags: List[str]
    ) -> List[ConversationTag]:
        """
        Add tags to a conversation

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)
            tags: List of tag strings

        Returns:
            List of created ConversationTag objects
        """
        # Verify user owns the conversation
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return []

        created_tags = []
        for tag in tags:
            # Check if tag already exists
            existing = db.query(ConversationTag).filter(
                and_(
                    ConversationTag.conversation_id == conversation_id,
                    ConversationTag.tag == tag.lower()
                )
            ).first()

            if not existing:
                conversation_tag = ConversationTag(
                    id=uuid.uuid4(),
                    conversation_id=conversation_id,
                    tag=tag.lower()
                )
                db.add(conversation_tag)
                created_tags.append(conversation_tag)

        db.commit()
        for tag in created_tags:
            db.refresh(tag)

        return created_tags

    @staticmethod
    def remove_tag(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        tag: str
    ) -> bool:
        """
        Remove a tag from a conversation

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user (for authorization)
            tag: Tag string to remove

        Returns:
            True if removed, False if not found
        """
        # Verify user owns the conversation
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return False

        tag_obj = db.query(ConversationTag).filter(
            and_(
                ConversationTag.conversation_id == conversation_id,
                ConversationTag.tag == tag.lower()
            )
        ).first()

        if not tag_obj:
            return False

        db.delete(tag_obj)
        db.commit()
        return True

    @staticmethod
    def get_conversation_stats(
        db: Session,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get statistics about user's conversations

        Args:
            db: Database session
            user_id: UUID of the user

        Returns:
            Dictionary with statistics
        """
        total_conversations = db.query(func.count(Conversation.id)).filter(
            Conversation.user_id == user_id
        ).scalar()

        active_conversations = db.query(func.count(Conversation.id)).filter(
            and_(
                Conversation.user_id == user_id,
                Conversation.is_archived == False
            )
        ).scalar()

        total_messages = db.query(func.count(Message.id)).join(Conversation).filter(
            Conversation.user_id == user_id
        ).scalar()

        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "archived_conversations": total_conversations - active_conversations,
            "total_messages": total_messages
        }

    @staticmethod
    def auto_generate_title(
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[str]:
        """
        Auto-generate a title from the first user message

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            user_id: UUID of the user

        Returns:
            Generated title or None
        """
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return None

        # Get first user message
        first_message = db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.role == "user",
                Message.deleted_at.is_(None)
            )
        ).order_by(Message.created_at).first()

        if not first_message:
            return None

        # Generate title from first 50 chars
        title = first_message.content[:50]
        if len(first_message.content) > 50:
            title += "..."

        conversation.title = title
        db.commit()
        db.refresh(conversation)

        return title

    @staticmethod
    def add_message_feedback(
        db: Session,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Add user feedback to a message

        Args:
            db: Database session
            message_id: UUID of the message
            user_id: UUID of the user (for authorization)
            rating: "positive" or "negative"
            comment: Optional comment

        Returns:
            True if feedback added, False if not found or unauthorized
        """
        # Get message with conversation join for user validation
        message = db.query(Message).join(Conversation).filter(
            and_(
                Message.id == message_id,
                Conversation.user_id == user_id,
                Message.role == "assistant"  # Only assistant messages can have feedback
            )
        ).first()

        if not message:
            return False

        # Update feedback
        feedback = {
            "rating": rating,
            "comment": comment,
            "feedback_at": datetime.utcnow().isoformat()
        }

        message.user_feedback = feedback
        db.commit()
        return True
