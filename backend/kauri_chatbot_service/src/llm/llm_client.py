"""
LLM Client with DeepSeek primary and OpenAI fallback
"""
from typing import Dict, Any, Optional, AsyncGenerator
import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = structlog.get_logger()


class LLMClient:
    """
    LLM Client supporting multiple providers with fallback
    Primary: DeepSeek
    Fallback: OpenAI
    """

    def __init__(self):
        self.primary_provider = settings.llm_provider
        self.primary_model = settings.llm_model
        self.fallback_provider = settings.llm_fallback_provider
        self.fallback_model = settings.llm_fallback_model
        
        # Initialize clients
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key
        )
        
        logger.info(
            "llm_client_initialized",
            primary=f"{self.primary_provider}/{self.primary_model}",
            fallback=f"{self.fallback_provider}/{self.fallback_model}"
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Generate completion from LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature override
            max_tokens: Max tokens override
            use_fallback: Force use of fallback provider
            
        Returns:
            Dict with 'content', 'model', 'tokens_used'
        """
        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Try primary provider first
        if not use_fallback:
            try:
                return await self._generate_with_provider(
                    self.primary_provider,
                    self.primary_model,
                    messages,
                    temp,
                    max_tok
                )
            except Exception as e:
                logger.warning(
                    "primary_llm_failed_switching_to_fallback",
                    provider=self.primary_provider,
                    error=str(e)
                )
                # Fall through to fallback
        
        # Use fallback
        return await self._generate_with_provider(
            self.fallback_provider,
            self.fallback_model,
            messages,
            temp,
            max_tok
        )

    async def _generate_with_provider(
        self,
        provider: str,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Generate with specific provider"""
        
        if provider == "deepseek":
            client = self.deepseek_client
        elif provider == "openai":
            client = self.openai_client
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            
            logger.info(
                "llm_generation_success",
                provider=provider,
                model=model,
                tokens=tokens_used
            )
            
            return {
                "content": content,
                "model": f"{provider}/{model}",
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            logger.error(
                "llm_generation_failed",
                provider=provider,
                model=model,
                error=str(e)
            )
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_fallback: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming completion
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature override
            max_tokens: Max tokens override
            use_fallback: Force use of fallback provider
            
        Yields:
            Text chunks
        """
        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Select provider
        if use_fallback:
            provider = self.fallback_provider
            model = self.fallback_model
        else:
            provider = self.primary_provider
            model = self.primary_model
        
        # Select client
        if provider == "deepseek":
            client = self.deepseek_client
        elif provider == "openai":
            client = self.openai_client
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(
                "llm_stream_failed",
                provider=provider,
                model=model,
                error=str(e)
            )
            # Try fallback if not already using it
            if not use_fallback:
                async for chunk in self.generate_stream(
                    prompt, system_prompt, temperature, max_tokens, use_fallback=True
                ):
                    yield chunk
            else:
                raise


# Global instance
llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    """
    Get the global LLM client instance

    Returns:
        LLMClient: The global instance
    """
    return llm_client
