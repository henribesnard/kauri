"""
Schemas Pydantic pour le Chat Service
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat query"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for history")


class SourceDocument(BaseModel):
    """Source document used in RAG - Enhanced for sourcing"""
    title: str = Field(..., description="Document title (structured path)")
    score: float = Field(..., description="Relevance score")

    # Enhanced fields for document sourcing
    category: Optional[str] = Field(None, description="Document category (doctrine, jurisprudence, etc.)")
    section: Optional[str] = Field(None, description="Section/subsection")
    file_path: Optional[str] = Field(None, description="Source file path")
    document_type: Optional[str] = Field(None, description="Type: acte_uniforme, plan_comptable, etc.")
    metadata_summary: Optional[Dict[str, str]] = Field(None, description="Additional metadata (livre, titre, article)")


class ChatResponse(BaseModel):
    """Response schema for chat query"""
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: Optional[str] = Field(None, description="Assistant message ID for feedback")
    query: str = Field(..., description="User query")
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents")
    model_used: str = Field(..., description="LLM model used")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    latency_ms: float = Field(..., description="Response latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (intent_type, retrieval_type, etc.)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class StreamChunk(BaseModel):
    """Streaming response chunk"""
    type: str = Field(..., description="Chunk type: sources, token, status, done, message_id, error")
    content: Optional[str] = Field(None, description="Content for token, status or error chunks")
    sources: Optional[List[SourceDocument]] = Field(None, description="Sources for sources chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for done chunk")
    message_id: Optional[str] = Field(None, description="Message ID for message_id chunk")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    environment: str
    database: str
    vector_db: str
    llm_provider: str


class Message(BaseModel):
    """Generic message response"""
    message: str
