"""Bounded, server-side Gemini chat with sanitized failures."""

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from backend.app.core.config import get_settings
from backend.app.schemas.chat_schemas import ChatMessage
from backend.app.services.chat_persona import build_system_prompt

DEFAULT_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
)


class ChatUnavailableError(Exception):
    """The chat provider is not configured or rejected its credentials."""


class ChatTemporaryError(Exception):
    """All configured models were temporarily unavailable."""


class ChatProviderError(Exception):
    """An unexpected or invalid provider response occurred."""


@dataclass(frozen=True)
class ChatResult:
    reply: str
    model: str
    fallback_used: bool


class ChatGateway(Protocol):
    async def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        message: str,
        history: list[ChatMessage],
    ) -> str: ...


class GeminiChatGateway:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        message: str,
        history: list[ChatMessage],
    ) -> str:
        def call() -> str:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=10_000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            try:
                sdk_history = [
                    types.Content(
                        role="model" if item.role == "assistant" else "user",
                        parts=[types.Part.from_text(text=item.content)],
                    )
                    for item in history
                ]
                chat = client.chats.create(
                    model=model,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                        max_output_tokens=1024,
                    ),
                    history=sdk_history,
                )
                return (chat.send_message(message).text or "").strip()
            finally:
                client.close()

        return await asyncio.to_thread(call)


def _error_status(error: Exception) -> int | None:
    for value in (
        getattr(error, "status_code", None),
        getattr(error, "code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        if isinstance(value, int):
            return value
    match = re.search(r"\b(401|403|404|429|500|502|503|504)\b", str(error))
    return int(match.group(1)) if match else None


class ChatService:
    def __init__(
        self,
        gateway: ChatGateway | None,
        *,
        models: tuple[str, ...] = DEFAULT_MODELS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.gateway = gateway
        self.models = models
        self.sleep = sleep

    @classmethod
    def from_settings(
        cls, api_key: str | None, model: str | None = None
    ) -> "ChatService":
        models = tuple(dict.fromkeys((model or DEFAULT_MODELS[0], *DEFAULT_MODELS)))
        return cls(GeminiChatGateway(api_key) if api_key else None, models=models)

    async def reply(
        self,
        message: str,
        history: list[ChatMessage],
        player_context: str | None,
    ) -> ChatResult:
        if self.gateway is None:
            raise ChatUnavailableError("El coach de IA no está configurado.")
        prompt = build_system_prompt(player_context=player_context)
        transient = False
        for model in self.models:
            for attempt in range(3):
                try:
                    reply = await self.gateway.generate(
                        model=model,
                        system_prompt=prompt,
                        message=message,
                        history=history,
                    )
                    if not reply.strip():
                        raise ChatProviderError(
                            "El coach devolvió una respuesta vacía."
                        )
                    return ChatResult(reply.strip(), model, model != self.models[0])
                except ChatProviderError:
                    raise
                except Exception as error:
                    status = _error_status(error)
                    if status in (401, 403):
                        raise ChatUnavailableError(
                            "La configuración del coach de IA necesita revisión."
                        ) from None
                    if status == 404:
                        break
                    if status in (429, 500, 502, 503, 504) or isinstance(
                        error, (TimeoutError, ConnectionError)
                    ):
                        transient = True
                        if attempt < 2:
                            await self.sleep(float(attempt + 1))
                        continue
                    raise ChatProviderError(
                        "El coach tuvo un problema inesperado. Inténtalo de nuevo."
                    ) from None
        if transient:
            raise ChatTemporaryError(
                "El servicio de IA está temporalmente saturado. Inténtalo de nuevo."
            )
        raise ChatUnavailableError(
            "La configuración del coach de IA necesita revisión."
        )


def get_chat_service() -> ChatService:
    settings = get_settings()
    return ChatService.from_settings(settings.gemini_api_key, settings.gemini_model)
