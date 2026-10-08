from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

EmailType = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        to_lower=True,
        strip_whitespace=True,
    ),
]


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user."""

    email: EmailType = Field(..., description="User's unique email address")
    password: str = Field(
        ..., min_length=8, description="User's password (minimum 8 characters)"
    )


class UserLoginRequest(BaseModel):
    """Payload for authenticating a user."""

    email: EmailType = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """OAuth2-compatible Bearer token response."""

    access_token: str = Field(..., description="JWT bearer access token")
    token_type: str = Field("bearer", description="Token scheme")


class UserResponse(BaseModel):
    """Public user profile."""

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    is_active: bool = Field(..., description="Whether the user account is active")
    created_at: str = Field(
        ..., description="Account creation timestamp in ISO 8601 UTC format"
    )


class LinkPlayerAccountRequest(BaseModel):
    """Request to link a Valorant player identity to the authenticated user."""

    game_name: str = Field(..., min_length=1, max_length=64, description="In-game name")
    tag_line: str = Field(
        ..., min_length=1, max_length=16, description="Tag line (e.g. EU1)"
    )
    region: str | None = Field(
        None, max_length=16, description="Optional region (e.g. eu, na, latam)"
    )
    is_primary: bool = Field(
        False, description="Whether this should be set as the user's primary identity"
    )


class LinkedPlayerAccountResponse(BaseModel):
    """Details of a linked Riot/Valorant player identity."""

    id: str = Field(..., description="Unique link identifier")
    user_id: str = Field(..., description="Associated user ID")
    game_name: str = Field(..., description="In-game name")
    tag_line: str = Field(..., description="Tag line")
    puuid: str | None = Field(None, description="Riot unique identifier if resolved")
    region: str | None = Field(None, description="Player region")
    is_primary: bool = Field(
        ..., description="Whether this is the user's primary identity"
    )
    linked_at: str = Field(
        ..., description="Timestamp when account was linked in ISO 8601 UTC format"
    )
