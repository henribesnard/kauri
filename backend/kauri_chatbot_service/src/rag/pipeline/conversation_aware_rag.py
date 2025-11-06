"""
Conversation-Aware RAG Pipeline
Extends RAG pipeline with conversation history and message persistence
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import uuid
from sqlalchemy.orm import Session
import structlog

from src.rag.pipeline.rag_pipeline import RAGPipeline
from src.services.conversation_service import ConversationService
from src.schemas.chat import SourceDocument

logger = structlog.get_logger()


class ConversationAwareRAG:
    """
    RAG Pipeline with conversation history and persistence

    Features:
    - Retrieves conversation history for context
    - Persists user messages and assistant responses
    - Auto-generates conversation titles
    - Maintains conversation continuity
    """

    def __init__(self, rag_pipeline: RAGPipeline):
        """
        Initialize Conversation-Aware RAG

        Args:
            rag_pipeline: Base RAG pipeline instance
        """
        self.rag_pipeline = rag_pipeline
        self.max_history_messages = 10  # Keep last N messages for context

    def _build_conversation_context(self, messages: List[Dict[str, Any]]) -> str:
        """
        Build conversation context from message history

        Args:
            messages: List of previous messages

        Returns:
            Formatted conversation history string
        """
        if not messages:
            return ""

        context_parts = ["HISTORIQUE DE CONVERSATION:\n"]

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                context_parts.append(f"Utilisateur: {content}")
            elif role == "assistant":
                context_parts.append(f"Assistant: {content}")

        context_parts.append("\n" + "=" * 80 + "\n")
        return "\n".join(context_parts)

    def _augment_system_prompt_with_history(
        self,
        base_system_prompt: str,
        has_history: bool
    ) -> str:
        """
        Augment system prompt with instructions for conversation continuity

        Args:
            base_system_prompt: Original system prompt
            has_history: Whether conversation history exists

        Returns:
            Augmented system prompt
        """
        if not has_history:
            return base_system_prompt

        return base_system_prompt + """

CONTEXTE CONVERSATIONNEL:
Tu continues une conversation existante avec l'utilisateur. L'historique des messages précédents est fourni ci-dessus.
- Fais référence aux messages précédents si pertinent
- Maintiens la cohérence avec tes réponses précédentes
- Si l'utilisateur demande des clarifications, réfère-toi au contexte de la conversation"""

    async def query(
        self,
        db: Session,
        user_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_reranking: bool = True,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Execute RAG query with conversation history and persistence

        Args:
            db: Database session
            user_id: User UUID
            query: User question
            conversation_id: Optional conversation ID
            temperature: LLM temperature
            max_tokens: Max tokens
            use_reranking: Use reranking
            use_fallback: Use fallback LLM

        Returns:
            Dict with answer, sources, metadata, conversation_id
        """
        logger.info("conversation_aware_rag_query_start",
                   user_id=str(user_id),
                   query=query[:100],
                   conversation_id=str(conversation_id) if conversation_id else None)

        # Step 1: Get or create conversation
        conversation = ConversationService.get_or_create_conversation(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Step 2: Retrieve conversation history
        messages = ConversationService.get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            limit=self.max_history_messages
        )

        # Convert to dict format
        message_dicts = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        # Step 3: Save user message
        user_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content=query
        )

        logger.info("user_message_saved", message_id=str(user_message.id))

        # Step 4: Build conversation context
        conversation_context = self._build_conversation_context(message_dicts)

        # Step 5: Augment query with conversation history if exists
        # Note: We'll inject this into the RAG pipeline's context
        augmented_query = query
        if conversation_context:
            augmented_query = f"{conversation_context}\nNOUVELLE QUESTION:\n{query}"

        # Step 6: Execute RAG pipeline
        result = await self.rag_pipeline.query(
            query=augmented_query,
            conversation_id=str(conversation.id),
            db_session=db,
            temperature=temperature,
            max_tokens=max_tokens,
            use_reranking=use_reranking,
            use_fallback=use_fallback
        )

        # Step 7: Save assistant message
        sources_dict = [
            {"title": src.title, "score": src.score}
            for src in result.get("sources", [])
        ]

        assistant_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            sources=sources_dict,
            metadata={
                "model_used": result.get("model_used"),
                "tokens_used": result.get("tokens_used"),
                "latency_ms": result.get("latency_ms"),
                "intent_type": result.get("metadata", {}).get("intent_type")
            }
        )

        logger.info("assistant_message_saved", message_id=str(assistant_message.id))

        # Step 8: Auto-generate title if first user message
        if len(messages) == 0 and not conversation.title:
            ConversationService.auto_generate_title(
                db=db,
                conversation_id=conversation.id,
                user_id=user_id
            )

        # Step 9: Update result with conversation_id and message_id
        result["conversation_id"] = str(conversation.id)
        result["message_id"] = str(assistant_message.id)

        return result

    async def query_stream(
        self,
        db: Session,
        user_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_reranking: bool = True,
        use_fallback: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute RAG query with streaming and conversation persistence

        Args:
            db: Database session
            user_id: User UUID
            query: User question
            conversation_id: Optional conversation ID
            temperature: LLM temperature
            max_tokens: Max tokens
            use_reranking: Use reranking
            use_fallback: Use fallback LLM

        Yields:
            Stream chunks with sources, tokens, and metadata
        """
        logger.info("conversation_aware_rag_stream_start",
                   user_id=str(user_id),
                   query=query[:100],
                   conversation_id=str(conversation_id) if conversation_id else None)

        # Send initial status
        yield {
            "type": "status",
            "content": "Je réfléchis"
        }

        # Step 1: Get or create conversation
        conversation = ConversationService.get_or_create_conversation(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Step 2: Retrieve conversation history
        messages = ConversationService.get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            limit=self.max_history_messages
        )

        # Convert to dict format
        message_dicts = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        # Step 3: Save user message
        user_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content=query
        )

        # Step 4: Build conversation context
        conversation_context = self._build_conversation_context(message_dicts)

        # Step 5: Augment query with conversation history
        augmented_query = query
        if conversation_context:
            augmented_query = f"{conversation_context}\nNOUVELLE QUESTION:\n{query}"

        # Send searching status
        yield {
            "type": "status",
            "content": "Je cherche des sources pour vous répondre"
        }

        # Step 6: Stream RAG pipeline
        accumulated_response = []
        sources = []
        metadata = {}
        sources_received = False

        async for chunk in self.rag_pipeline.query_stream(
            query=augmented_query,
            conversation_id=str(conversation.id),
            db_session=db,
            temperature=temperature,
            max_tokens=max_tokens,
            use_reranking=use_reranking,
            use_fallback=use_fallback
        ):
            # Capture sources and metadata for later persistence
            if chunk["type"] == "sources":
                sources = chunk.get("sources", [])
                sources_received = True

                # Send status after receiving sources
                yield {
                    "type": "status",
                    "content": "J'ai trouvé des sources concordantes"
                }
            elif chunk["type"] == "token":
                # Send formulating status before first token
                if sources_received and len(accumulated_response) == 0:
                    yield {
                        "type": "status",
                        "content": "Je formule la réponse"
                    }
                accumulated_response.append(chunk.get("content", ""))
            elif chunk["type"] == "done":
                metadata = chunk.get("metadata", {})

            # Update conversation_id in metadata chunks
            if chunk["type"] == "done" and "metadata" in chunk:
                chunk["metadata"]["conversation_id"] = str(conversation.id)

            # Yield chunk to client
            yield chunk

        # Step 7: Save assistant message after streaming completes
        full_response = "".join(accumulated_response)

        sources_dict = [
            {"title": src.title, "score": src.score}
            for src in sources
        ]

        assistant_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            sources=sources_dict,
            metadata={
                "model_used": metadata.get("model_used"),
                "tokens_used": metadata.get("tokens_used"),
                "latency_ms": metadata.get("latency_ms"),
                "intent_type": metadata.get("intent_type")
            }
        )

        logger.info("assistant_message_saved_after_stream",
                   message_id=str(assistant_message.id))

        # Yield final chunk with message_id
        yield {
            "type": "message_id",
            "message_id": str(assistant_message.id)
        }

        # Step 8: Auto-generate title if first user message
        if len(messages) == 0 and not conversation.title:
            ConversationService.auto_generate_title(
                db=db,
                conversation_id=conversation.id,
                user_id=user_id
            )


# Singleton instance
_conversation_aware_rag_instance: Optional[ConversationAwareRAG] = None


def get_conversation_aware_rag() -> ConversationAwareRAG:
    """Get singleton Conversation-Aware RAG instance"""
    global _conversation_aware_rag_instance
    if _conversation_aware_rag_instance is None:
        from src.rag.pipeline.rag_pipeline import get_rag_pipeline
        rag_pipeline = get_rag_pipeline()
        _conversation_aware_rag_instance = ConversationAwareRAG(rag_pipeline)
    return _conversation_aware_rag_instance
