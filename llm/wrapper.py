"""
ATTCO LiteLLM Foundation Wrapper.
Provides async model completions with structured tracing, retry handling, and token accounting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import litellm
from litellm import acompletion
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

# LiteLLM configs
litellm.telemetry = False
litellm.success_callback = ["langsmith"]
litellm.failure_callback = ["langsmith"]

class LLMWrapper:
    """Async wrapper for LiteLLM with built-in retries and tracing."""

    def __init__(self, provider: str, model_id: str, temperature: float = 0.0, max_tokens: int = 2048, timeout_s: int = 30) -> None:
        self.provider = provider
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.full_model_name = f"{provider}/{model_id}" if provider not in model_id else model_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((litellm.exceptions.RateLimitError, litellm.exceptions.APIConnectionError, litellm.exceptions.Timeout)),
        reraise=True
    )
    async def agenerate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        """
        Execute an async completion call to the underlying model.
        Returns the LiteLLM response object.
        """
        logger.debug("llm_call_started", model=self.full_model_name, message_count=len(messages))
        try:
            kwargs: Dict[str, Any] = {
                "model": self.full_model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout": self.timeout_s,
            }
            if tools:
                kwargs["tools"] = tools
            
            response = await acompletion(**kwargs)
            
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            
            logger.debug(
                "llm_call_completed",
                model=self.full_model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
            return response
            
        except Exception as e:
            logger.exception("llm_call_failed", model=self.full_model_name, error=str(e))
            raise
