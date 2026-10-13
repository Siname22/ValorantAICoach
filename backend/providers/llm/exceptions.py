"""Exceptions for LLM providers."""

from backend.providers.base.exceptions import ProviderError


class LLMProviderError(ProviderError):
    """Base exception for LLM provider errors."""


class LLMUnavailableError(LLMProviderError):
    """Raised when an LLM provider is not configured or unreachable."""


class LLMGenerationError(LLMProviderError):
    """Raised when LLM text or multimodal generation fails."""
