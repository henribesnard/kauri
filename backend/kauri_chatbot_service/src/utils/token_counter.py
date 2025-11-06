"""
Token counting utility for context management
Uses simple estimation based on character count (more reliable than tiktoken for multilingual)
"""
import re
from typing import List, Dict, Any


class TokenCounter:
    """
    Simple token counter using character-based estimation

    Rule of thumb:
    - 1 token ≈ 4 characters for English
    - 1 token ≈ 2-3 characters for French/multilingual
    - We use 3 characters per token as a conservative estimate
    """

    CHARS_PER_TOKEN = 3

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        Estimate number of tokens in text

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Estimate: ~3 chars per token (conservative for multilingual)
        return max(1, len(text) // cls.CHARS_PER_TOKEN)

    @classmethod
    def estimate_tokens_from_messages(cls, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate total tokens from list of messages

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total estimated tokens
        """
        total_tokens = 0

        for msg in messages:
            # Count role tokens
            role = msg.get('role', '')
            total_tokens += cls.estimate_tokens(role)

            # Count content tokens
            content = msg.get('content', '')
            total_tokens += cls.estimate_tokens(content)

            # Count sources tokens (if present)
            sources = msg.get('sources', [])
            for source in sources:
                if isinstance(source, dict):
                    title = source.get('title', '')
                    total_tokens += cls.estimate_tokens(title)

            # Add overhead for message formatting (~10 tokens per message)
            total_tokens += 10

        return total_tokens

    @classmethod
    def estimate_tokens_with_sources(cls, text: str, sources: List[Dict[str, Any]]) -> int:
        """
        Estimate tokens including source documents

        Args:
            text: Main text
            sources: List of source documents

        Returns:
            Total estimated tokens
        """
        total_tokens = cls.estimate_tokens(text)

        for source in sources:
            if isinstance(source, dict):
                # Title + small overhead
                title = source.get('title', '')
                total_tokens += cls.estimate_tokens(title)
                total_tokens += 5  # Overhead for formatting

        return total_tokens
