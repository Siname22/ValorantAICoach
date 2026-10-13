"""Abstract Base LLM Provider definition for text and multimodal inference."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.providers.base.models import ProviderHealth
from backend.providers.base.provider import BaseProvider


class BaseLLMProvider(BaseProvider, ABC):
    """Abstract interface for Large Language Model and Vision providers."""

    @property
    def name(self) -> str:
        return "llm"

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        model: str | None = None,
    ) -> str:
        """Generate text from a prompt and optional system instruction."""

    @abstractmethod
    async def generate_multimodal(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        *,
        response_mime_type: str = "application/json",
        model: str | None = None,
    ) -> str:
        """Generate content from a prompt combined with image bytes."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Perform a health check on the LLM provider."""
