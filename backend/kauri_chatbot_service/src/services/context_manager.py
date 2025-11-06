"""
Conversation Context Manager - Manages conversation history and context limits
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import structlog

from src.models.message import Message
from src.models.conversation import Conversation
from src.config import settings
from src.utils.token_counter import TokenCounter

logger = structlog.get_logger()


class ContextInfo:
    """Information about conversation context"""

    def __init__(
        self,
        total_tokens: int,
        max_tokens: int,
        warning_threshold_tokens: int,
        is_over_limit: bool,
        is_near_limit: bool,
        messages_included: int
    ):
        self.total_tokens = total_tokens
        self.max_tokens = max_tokens
        self.warning_threshold_tokens = warning_threshold_tokens
        self.is_over_limit = is_over_limit
        self.is_near_limit = is_near_limit
        self.messages_included = messages_included
        self.usage_percentage = (total_tokens / max_tokens * 100) if max_tokens > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "warning_threshold_tokens": self.warning_threshold_tokens,
            "is_over_limit": self.is_over_limit,
            "is_near_limit": self.is_near_limit,
            "usage_percentage": round(self.usage_percentage, 2),
            "messages_included": self.messages_included
        }


class ConversationContextManager:
    """
    Manages conversation context including:
    - Token counting and limits
    - History retrieval
    - Smart retrieval decision (use context vs. new search)
    """

    def __init__(self):
        self.max_context_tokens = settings.conversation_max_context_tokens
        self.warning_threshold = settings.conversation_context_warning_threshold
        self.max_messages = settings.conversation_history_max_messages
        self.warning_threshold_tokens = int(self.max_context_tokens * self.warning_threshold)

    def get_conversation_context(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        include_current_query: bool = True,
        current_query: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], ContextInfo]:
        """
        Get conversation context with token limits

        Args:
            db: Database session
            conversation_id: UUID of conversation
            include_current_query: Whether to include current query in token count
            current_query: Current user query

        Returns:
            Tuple of (messages, context_info)
        """
        # Get conversation messages (most recent first, then reverse)
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None)
        ).order_by(Message.created_at.desc()).limit(self.max_messages).all()

        messages = list(reversed(messages))  # Chronological order

        # Convert to dict format
        message_dicts = []
        for msg in messages:
            message_dict = {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "sources": msg.sources or [],
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            message_dicts.append(message_dict)

        # Calculate tokens
        total_tokens = TokenCounter.estimate_tokens_from_messages(message_dicts)

        # Add current query tokens if needed
        if include_current_query and current_query:
            total_tokens += TokenCounter.estimate_tokens(current_query)
            total_tokens += 10  # Overhead

        # Determine limits
        is_over_limit = total_tokens >= self.max_context_tokens
        is_near_limit = total_tokens >= self.warning_threshold_tokens

        context_info = ContextInfo(
            total_tokens=total_tokens,
            max_tokens=self.max_context_tokens,
            warning_threshold_tokens=self.warning_threshold_tokens,
            is_over_limit=is_over_limit,
            is_near_limit=is_near_limit,
            messages_included=len(message_dicts)
        )

        logger.info(
            "conversation_context_retrieved",
            conversation_id=str(conversation_id),
            total_tokens=total_tokens,
            max_tokens=self.max_context_tokens,
            is_over_limit=is_over_limit,
            is_near_limit=is_near_limit,
            messages_count=len(message_dicts)
        )

        return message_dicts, context_info

    def should_retrieve_new_documents(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]],
        intent_type: str
    ) -> bool:
        """
        Decide if new document retrieval is needed

        Logic:
        - If general_conversation or clarification -> no retrieval needed
        - If no conversation history -> retrieval needed
        - If query seems like follow-up/clarification -> check if sources in recent messages
        - Otherwise -> retrieval needed

        Args:
            query: Current user query
            conversation_history: List of previous messages
            intent_type: Intent classification result

        Returns:
            True if new retrieval needed, False if context sufficient
        """
        # Non-RAG intents don't need retrieval
        if intent_type in ["general_conversation", "clarification"]:
            logger.info("no_retrieval_needed_non_rag_intent", intent_type=intent_type)
            return False

        # No history -> need retrieval
        if not conversation_history:
            logger.info("retrieval_needed_no_history")
            return True

        # Check if this is a follow-up query (contains pronouns, short, etc.)
        is_follow_up = self._is_likely_follow_up(query)

        if is_follow_up:
            # Check if recent messages have sources
            has_recent_sources = self._has_recent_sources(conversation_history, lookback=2)

            if has_recent_sources:
                logger.info("no_retrieval_needed_follow_up_with_sources",
                          query=query[:100],
                          has_sources=True)
                return False
            else:
                logger.info("retrieval_needed_follow_up_no_sources",
                          query=query[:100])
                return True

        # Default: need retrieval for new questions
        logger.info("retrieval_needed_new_question", query=query[:100])
        return True

    def _is_likely_follow_up(self, query: str) -> bool:
        """
        Check if query is likely a follow-up question

        Heuristics:
        - Contains pronouns (ça, cela, il, elle, ce, cet, cette)
        - Short query (< 50 chars)
        - Starts with clarification words (et, mais, donc, pourquoi, comment, quoi)

        Args:
            query: User query

        Returns:
            True if likely follow-up
        """
        query_lower = query.lower().strip()

        # Follow-up indicators (French)
        follow_up_indicators = [
            "ça", "cela", "c'est quoi", "qu'est-ce", "pourquoi",
            "comment ça", "et ça", "et alors", "et donc", "donc",
            "mais", "et puis", "ensuite", "après", "avant",
            "peux-tu", "pouvez-vous", "explique", "précise",
            "donne", "montre"
        ]

        # Check for indicators
        has_indicator = any(indicator in query_lower for indicator in follow_up_indicators)

        # Short query is more likely follow-up
        is_short = len(query) < 50

        return has_indicator or is_short

    def _has_recent_sources(self, messages: List[Dict[str, Any]], lookback: int = 2) -> bool:
        """
        Check if recent assistant messages have sources

        Args:
            messages: List of messages
            lookback: Number of recent messages to check

        Returns:
            True if recent messages have sources
        """
        # Get recent assistant messages
        recent_assistant = [
            msg for msg in messages[-lookback:]
            if msg.get("role") == "assistant"
        ]

        # Check if any have sources
        for msg in recent_assistant:
            sources = msg.get("sources", [])
            if sources and len(sources) > 0:
                return True

        return False

    def format_context_for_llm(
        self,
        conversation_history: List[Dict[str, Any]],
        include_sources: bool = True
    ) -> str:
        """
        Format conversation history as context string for LLM

        Args:
            conversation_history: List of messages
            include_sources: Whether to include source information

        Returns:
            Formatted context string
        """
        if not conversation_history:
            return ""

        context_parts = ["### Historique de la conversation ###\n"]

        for msg in conversation_history:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            sources = msg.get("sources", [])

            context_parts.append(f"\n**{role}:** {content}")

            if include_sources and sources and role == "Assistant":
                context_parts.append("\n*Sources utilisées:*")
                for i, source in enumerate(sources[:3], 1):  # Limit to 3 sources
                    title = source.get("title", "Unknown")
                    context_parts.append(f"  {i}. {title}")

        context_parts.append("\n\n### Nouvelle question ###\n")

        return "\n".join(context_parts)


# Singleton instance
context_manager = ConversationContextManager()
