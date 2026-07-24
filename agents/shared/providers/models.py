from pydantic import Field

from agents.shared.models import AgentModel


class ProviderConfig(AgentModel):
    """Base configuration model for any provider."""

    api_key: str = Field(..., min_length=1, description="API key for the provider")
    base_url: str = Field(
        "", description="Base URL for the provider API", pattern="^https?://"
    )


class LLMProviderConfig(ProviderConfig):
    """Configuration specific to LLM providers."""

    model_name: str = Field(..., description="Name of the LLM model to use")
    temperature: float = Field(
        0.7, ge=0.0, le=1.0, description="Sampling temperature for LLM"
    )
    max_tokens: int = Field(1024, ge=1, description="Maximum tokens to generate")


class ToolProviderConfig(ProviderConfig):
    """Configuration specific to tool providers."""

    # Example: specific settings for a web scraping tool provider
    headless: bool = Field(True, description="Run browser in headless mode")


class ProviderHealth(AgentModel):
    """Model for reporting provider health status."""

    status: str = Field(..., description="Health status (e.g., 'healthy', 'unhealthy')")
    message: str = Field("", description="Detailed health message")
    timestamp: str = Field(..., description="Timestamp of the health check")
