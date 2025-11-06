"""
API Routes for Conversation Management
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.models.database import get_db
from src.services.conversation_service import ConversationService
from src.services.context_manager import context_manager
from src.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages,
    ConversationListResponse,
    MessageResponse,
    TagCreate,
    TagRemove,
    TagResponse,
    ConversationStats,
    MessageFeedback,
    ConversationContextInfo
)
from src.auth.jwt_validator import get_current_user

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new conversation

    Args:
        data: Conversation creation data
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Created conversation
    """
    user_id = uuid.UUID(current_user["user_id"])

    conversation = ConversationService.create_conversation(
        db=db,
        user_id=user_id,
        title=data.title,
        metadata=data.metadata
    )

    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        metadata=conversation.extra_data or {},
        message_count=0
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    include_archived: bool = Query(False, description="Include archived conversations"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List user's conversations

    Args:
        include_archived: Include archived conversations
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        List of conversations with pagination info
    """
    user_id = uuid.UUID(current_user["user_id"])

    conversations = ConversationService.list_user_conversations(
        db=db,
        user_id=user_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset
    )

    # Convert to response schema
    conversation_responses = []
    for conv in conversations:
        conversation_responses.append(ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            is_archived=conv.is_archived,
            metadata=conv.extra_data or {},
            message_count=len(conv.messages) if conv.messages else 0
        ))

    return ConversationListResponse(
        conversations=conversation_responses,
        total=len(conversation_responses),
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=ConversationStats)
async def get_conversation_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get conversation statistics for the user

    Args:
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Conversation statistics
    """
    user_id = uuid.UUID(current_user["user_id"])
    stats = ConversationService.get_conversation_stats(db=db, user_id=user_id)
    return ConversationStats(**stats)


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: uuid.UUID,
    include_deleted: bool = Query(False, description="Include deleted messages"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a conversation with its messages

    Args:
        conversation_id: UUID of the conversation
        include_deleted: Include soft-deleted messages
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Conversation with messages
    """
    user_id = uuid.UUID(current_user["user_id"])

    conversation = ConversationService.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get messages
    messages = ConversationService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        include_deleted=include_deleted
    )

    # Convert messages to response schema
    message_responses = []
    for msg in messages:
        message_responses.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            sources=msg.sources or [],
            metadata=msg.extra_data or {},
            user_feedback=msg.user_feedback,
            created_at=msg.created_at,
            deleted_at=msg.deleted_at
        ))

    # Get tags
    tags = [tag.tag for tag in conversation.tags] if conversation.tags else []

    return ConversationWithMessages(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        metadata=conversation.extra_data or {},
        message_count=len(messages),
        messages=message_responses,
        tags=tags
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a conversation

    Args:
        conversation_id: UUID of the conversation
        data: Update data
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Updated conversation
    """
    user_id = uuid.UUID(current_user["user_id"])

    conversation = ConversationService.update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        title=data.title,
        is_archived=data.is_archived,
        metadata=data.metadata
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        metadata=conversation.extra_data or {},
        message_count=len(conversation.messages) if conversation.messages else 0
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a conversation (and all its messages)

    Args:
        conversation_id: UUID of the conversation
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        204 No Content on success
    """
    user_id = uuid.UUID(current_user["user_id"])

    deleted = ConversationService.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(None, ge=1, le=500, description="Limit number of messages (most recent)"),
    include_deleted: bool = Query(False, description="Include deleted messages"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages from a conversation

    Args:
        conversation_id: UUID of the conversation
        limit: Optional limit on messages
        include_deleted: Include soft-deleted messages
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        List of messages
    """
    user_id = uuid.UUID(current_user["user_id"])

    messages = ConversationService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        limit=limit,
        include_deleted=include_deleted
    )

    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            sources=msg.sources or [],
            metadata=msg.extra_data or {},
            created_at=msg.created_at,
            deleted_at=msg.deleted_at
        )
        for msg in messages
    ]


@router.delete("/{conversation_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a message

    Args:
        conversation_id: UUID of the conversation
        message_id: UUID of the message
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        204 No Content on success
    """
    user_id = uuid.UUID(current_user["user_id"])

    deleted = ConversationService.soft_delete_message(
        db=db,
        message_id=message_id,
        user_id=user_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )


@router.post("/{conversation_id}/tags", response_model=List[TagResponse])
async def add_tags(
    conversation_id: uuid.UUID,
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add tags to a conversation

    Args:
        conversation_id: UUID of the conversation
        data: Tags to add
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        List of created tags
    """
    user_id = uuid.UUID(current_user["user_id"])

    tags = ConversationService.add_tags(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        tags=data.tags
    )

    return [
        TagResponse(
            id=tag.id,
            conversation_id=tag.conversation_id,
            tag=tag.tag
        )
        for tag in tags
    ]


@router.delete("/{conversation_id}/tags/{tag}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag(
    conversation_id: uuid.UUID,
    tag: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a tag from a conversation

    Args:
        conversation_id: UUID of the conversation
        tag: Tag to remove
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        204 No Content on success
    """
    user_id = uuid.UUID(current_user["user_id"])

    removed = ConversationService.remove_tag(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        tag=tag
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )


@router.post("/{conversation_id}/generate-title", response_model=ConversationResponse)
async def auto_generate_title(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Auto-generate a title from the first user message

    Args:
        conversation_id: UUID of the conversation
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Updated conversation with generated title
    """
    user_id = uuid.UUID(current_user["user_id"])

    title = ConversationService.auto_generate_title(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )

    if not title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or no messages available"
        )

    conversation = ConversationService.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )

    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        metadata=conversation.extra_data or {},
        message_count=len(conversation.messages) if conversation.messages else 0
    )


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_200_OK)
async def add_message_feedback(
    message_id: uuid.UUID,
    feedback: MessageFeedback,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add feedback to a message

    Args:
        message_id: UUID of the message
        feedback: Feedback data
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Success message
    """
    user_id = uuid.UUID(current_user["user_id"])

    success = ConversationService.add_message_feedback(
        db=db,
        message_id=message_id,
        user_id=user_id,
        rating=feedback.rating,
        comment=feedback.comment
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or unauthorized"
        )

    return {"message": "Feedback added successfully"}


@router.get("/{conversation_id}/context-info", response_model=ConversationContextInfo)
async def get_conversation_context_info(
    conversation_id: uuid.UUID,
    include_current_query: bool = Query(False, description="Include hypothetical current query"),
    current_query: str = Query(None, description="Hypothetical current query"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get context information for a conversation

    Args:
        conversation_id: UUID of the conversation
        include_current_query: Whether to include current query in token count
        current_query: Optional current query to include in count
        db: Database session
        current_user: Authenticated user from JWT

    Returns:
        Context information
    """
    user_id = uuid.UUID(current_user["user_id"])

    # Verify user owns the conversation
    conversation = ConversationService.get_conversation(db, conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get context info
    _, context_info = context_manager.get_conversation_context(
        db=db,
        conversation_id=conversation_id,
        include_current_query=include_current_query,
        current_query=current_query
    )

    return ConversationContextInfo(**context_info.to_dict())
