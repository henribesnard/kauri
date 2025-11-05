"""
Pydantic schemas for Conversations and Messages
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# ============================================
# Message Schemas
# ============================================

class MessageBase(BaseModel):
    """Base schema for messages"""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Source documents")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: uuid.UUID = Field(..., description="Message ID")
    conversation_id: uuid.UUID = Field(..., description="Conversation ID")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp (soft delete)")

    class Config:
        from_attributes = True


# ============================================
# Conversation Schemas
# ============================================

class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation metadata")


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=255, description="New title")
    is_archived: Optional[bool] = Field(None, description="Archive status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata to merge")


class ConversationResponse(BaseModel):
    """Schema for conversation response (without messages)"""
    id: uuid.UUID = Field(..., description="Conversation ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(..., description="Archive status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Conversation metadata")
    message_count: int = Field(..., description="Number of messages in conversation")

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Schema for conversation with messages"""
    messages: List[MessageResponse] = Field(default_factory=list, description="Conversation messages")
    tags: List[str] = Field(default_factory=list, description="Conversation tags")


class ConversationListResponse(BaseModel):
    """Schema for listing conversations"""
    conversations: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


# ============================================
# Tag Schemas
# ============================================

class TagCreate(BaseModel):
    """Schema for creating tags"""
    tags: List[str] = Field(..., min_items=1, description="List of tags to add")


class TagRemove(BaseModel):
    """Schema for removing a tag"""
    tag: str = Field(..., description="Tag to remove")


class TagResponse(BaseModel):
    """Schema for tag response"""
    id: uuid.UUID = Field(..., description="Tag ID")
    conversation_id: uuid.UUID = Field(..., description="Conversation ID")
    tag: str = Field(..., description="Tag name")

    class Config:
        from_attributes = True


# ============================================
# Statistics Schema
# ============================================

class ConversationStats(BaseModel):
    """Schema for conversation statistics"""
    total_conversations: int = Field(..., description="Total number of conversations")
    active_conversations: int = Field(..., description="Number of active conversations")
    archived_conversations: int = Field(..., description="Number of archived conversations")
    total_messages: int = Field(..., description="Total number of messages")
