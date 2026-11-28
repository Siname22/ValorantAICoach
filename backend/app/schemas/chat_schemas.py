from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Region = Literal["eu", "na", "ap", "kr", "br", "latam"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chat messages cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def user_message_limit(self) -> "ChatMessage":
        if self.role == "user" and len(self.content) > 4000:
            raise ValueError("User chat messages cannot exceed 4000 characters")
        return self


class ChatPlayer(BaseModel):
    game_name: str = Field(min_length=1, max_length=64)
    tag_line: str = Field(min_length=1, max_length=16)
    region: Region


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    player: ChatPlayer | None = None

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chat message cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def history_size(self) -> "ChatRequest":
        if sum(len(item.content.encode("utf-8")) for item in self.history) > 128 * 1024:
            raise ValueError("Chat history is too large")
        return self


class ChatResponse(BaseModel):
    reply: str
    model: str
    fallback_used: bool
