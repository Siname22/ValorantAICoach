from abc import ABC, abstractmethod

from .client import BaseHTTPClient
from .config import ProviderConfig
from .models import ProviderHealth


class BaseProvider(ABC):
    """
    Abstract base class for all external service providers.
    Each provider implementation will inherit from this class.
    """

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._client: BaseHTTPClient | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the provider."""
        pass

    @property
    def client(self) -> BaseHTTPClient:
        """Lazily initializes and returns the BaseHTTPClient."""
        if self._client is None:
            self._client = BaseHTTPClient(self.config, self.name)
        return self._client

    async def initialize(self) -> None:
        """
        Optional initialization logic for the provider.
        Called when the provider is first created or resolved.
        """
        return None

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check on the provider.

        Returns:
            A ProviderHealth object indicating the status.
        """
        pass

    async def close(self) -> None:
        """
        Closes any resources held by the provider (e.g., HTTP client).
        """
        if self._client:
            await self._client.close()
