"""Google Gemini LLM & Vision provider implementation using google-genai."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from backend.providers.base.config import ProviderConfig
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.llm.base import BaseLLMProvider
from backend.providers.llm.exceptions import (
    LLMGenerationError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


class GeminiConfig(ProviderConfig):
    """Configuration for Gemini LLM Provider."""

    base_url: str = "https://generativelanguage.googleapis.com"
    api_key: str | None = None
    default_model: str = "gemini-2.5-flash"


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM provider supporting text and multimodal inference."""

    def __init__(
        self,
        config: GeminiConfig | None = None,
        *,
        api_key: str | None = None,
        default_model: str = "gemini-2.5-flash",
    ) -> None:
        cfg = config or GeminiConfig(
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            default_model=default_model,
        )
        super().__init__(cfg)
        self.config: GeminiConfig = cfg
        self._api_key = (
            self.config.api_key if self.config.api_key else os.getenv("GEMINI_API_KEY")
        )
        self._default_model = self.config.default_model

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def _get_client(self) -> Any:
        if not self.is_configured:
            return None
        try:
            from google import genai

            return genai.Client(api_key=self._api_key.strip())
        except ImportError:
            logger.warning("google-genai package not installed")
            return None
        except Exception as exc:
            logger.warning(
                "Failed to initialize google-genai client: %s", type(exc).__name__
            )
            return None

    async def health_check(self) -> ProviderHealth:
        """Check if Gemini credentials are configured and reachable."""
        if not self.is_configured:
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message="GEMINI_API_KEY is not configured",
            )
        return ProviderHealth(
            status=ProviderStatus.HEALTHY,
            message="Gemini provider configured",
        )

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        model: str | None = None,
    ) -> str:
        """Generate text using Gemini."""
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError(
                "Gemini LLM provider is not configured (GEMINI_API_KEY missing)."
            )

        target_model = model or self._default_model

        def _call_api() -> str:
            from google.genai import types

            config = (
                types.GenerateContentConfig(system_instruction=system_instruction)
                if system_instruction
                else None
            )
            resp = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            return resp.text or ""

        try:
            return await asyncio.to_thread(_call_api)
        except Exception as exc:
            logger.warning("Gemini text generation error: %s", type(exc).__name__)
            raise LLMGenerationError(f"Gemini generation failed: {exc}") from exc

    async def generate_multimodal(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        *,
        response_mime_type: str = "application/json",
        model: str | None = None,
    ) -> str:
        """Generate structured response from image bytes and prompt."""
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError(
                "Gemini vision provider is not configured (GEMINI_API_KEY missing)."
            )

        target_model = model or self._default_model

        def _call_api() -> str:
            from google.genai import types

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            resp = client.models.generate_content(
                model=target_model,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type=response_mime_type,
                ),
            )
            return resp.text or ""

        try:
            return await asyncio.to_thread(_call_api)
        except Exception as exc:
            logger.warning("Gemini vision generation error: %s", type(exc).__name__)
            raise LLMGenerationError(
                f"Gemini multimodal generation failed: {exc}"
            ) from exc
