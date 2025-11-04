"""
Chat API Routes - RAG-powered Q&A endpoints with JWT protection
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import structlog
import json

from src.schemas.chat import ChatRequest, ChatResponse, StreamChunk
from src.auth.jwt_validator import get_current_user
from src.rag.pipeline.rag_pipeline import get_rag_pipeline

logger = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Standard RAG query endpoint (non-streaming)

    Protected with JWT authentication from User Service

    Args:
        request: Chat request with query and options
        current_user: Authenticated user from JWT token

    Returns:
        ChatResponse with answer, sources, and metadata
    """
    user_id = current_user.get("id")
    user_email = current_user.get("email")

    logger.info("chat_query_request",
               user_id=user_id,
               user_email=user_email,
               query=request.query[:100],
               conversation_id=request.conversation_id)

    try:
        # Get RAG pipeline
        rag_pipeline = get_rag_pipeline()

        # Execute query
        result = await rag_pipeline.query(
            query=request.query,
            conversation_id=request.conversation_id,
            use_reranking=True,  # Always use reranking for best quality
            use_fallback=False
        )

        logger.info("chat_query_success",
                   user_id=user_id,
                   conversation_id=result["conversation_id"],
                   latency_ms=result["latency_ms"],
                   num_sources=len(result["sources"]))

        return ChatResponse(**result)

    except Exception as e:
        logger.error("chat_query_error",
                    user_id=user_id,
                    error=str(e),
                    query=request.query[:100])
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement de la requête: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Streaming RAG query endpoint with Server-Sent Events

    Protected with JWT authentication from User Service

    Args:
        request: Chat request with query and options
        current_user: Authenticated user from JWT token

    Returns:
        StreamingResponse with SSE events

    Event types:
        - sources: Retrieved documents sent first
        - token: Each generated token
        - done: Completion metadata
        - error: Error information
    """
    user_id = current_user.get("id")
    user_email = current_user.get("email")

    logger.info("chat_stream_request",
               user_id=user_id,
               user_email=user_email,
               query=request.query[:100],
               conversation_id=request.conversation_id)

    async def event_generator():
        """Generator for SSE events"""
        try:
            # Get RAG pipeline
            rag_pipeline = get_rag_pipeline()

            # Stream results
            async for chunk in rag_pipeline.query_stream(
                query=request.query,
                conversation_id=request.conversation_id,
                use_reranking=True,
                use_fallback=False
            ):
                # Convert chunk to StreamChunk schema
                if chunk["type"] == "sources":
                    stream_chunk = StreamChunk(
                        type="sources",
                        sources=chunk["sources"],
                        metadata=chunk.get("metadata")
                    )
                elif chunk["type"] == "token":
                    stream_chunk = StreamChunk(
                        type="token",
                        content=chunk["content"]
                    )
                elif chunk["type"] == "done":
                    stream_chunk = StreamChunk(
                        type="done",
                        metadata=chunk["metadata"]
                    )
                    logger.info("chat_stream_success",
                               user_id=user_id,
                               conversation_id=chunk["metadata"].get("conversation_id"),
                               latency_ms=chunk["metadata"].get("latency_ms"))
                elif chunk["type"] == "error":
                    stream_chunk = StreamChunk(
                        type="error",
                        content=chunk["content"]
                    )
                    logger.error("chat_stream_error_chunk",
                                user_id=user_id,
                                error=chunk["content"])
                else:
                    continue  # Unknown chunk type

                # Send SSE event
                # Format: data: {json}\n\n
                yield f"data: {stream_chunk.model_dump_json()}\n\n"

        except Exception as e:
            logger.error("chat_stream_error",
                        user_id=user_id,
                        error=str(e),
                        query=request.query[:100])

            # Send error event
            error_chunk = StreamChunk(
                type="error",
                content=f"Erreur lors du traitement: {str(e)}"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/health")
async def chat_health():
    """
    Health check endpoint (no authentication required)

    Returns:
        Status information
    """
    return {
        "status": "ok",
        "service": "chat",
        "endpoints": {
            "query": "/api/v1/chat/query",
            "stream": "/api/v1/chat/stream"
        }
    }
