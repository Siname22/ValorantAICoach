import logging
from typing import Annotated, Any

from backend.app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from backend.app.dependencies.auth_deps import get_current_user
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.auth_schemas import (
    LinkedPlayerAccountResponse,
    LinkPlayerAccountRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from backend.app.services.player_service import (
    PlayerService,
    PlayerServiceUnavailableError,
)
from fastapi import APIRouter, Depends, HTTPException, Path, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

Service = Annotated[PlayerService, Depends(get_player_service)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    request: UserRegisterRequest,
    service: Service,
) -> UserResponse:
    """Create a new user with an email and secure hashed password."""
    try:
        user = await service.create_user(
            email=request.email,
            password_hash=get_password_hash(request.password),
        )
        return UserResponse(**user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        ) from None
    except PlayerServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User registration requires persistent database storage.",
        ) from None


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
async def login(
    request: UserLoginRequest,
    service: Service,
) -> TokenResponse:
    """Authenticate with email and password to receive a bearer access token."""
    try:
        user = await service.get_user_by_email(request.email)
    except PlayerServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication requires persistent database storage.",
        ) from None

    if user is None or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )

    token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """Return profile details for the currently authenticated user."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
    )


@router.post(
    "/me/accounts",
    response_model=LinkedPlayerAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a Valorant player identity to current user",
)
async def link_player_account(
    request: LinkPlayerAccountRequest,
    current_user: CurrentUser,
    service: Service,
) -> LinkedPlayerAccountResponse:
    """Link a Riot/Valorant in-game identity (name#tag) to the user's account."""
    puuid = None
    region = request.region
    try:
        player = await service.get_player(request.game_name, request.tag_line)
        puuid = player.puuid
        if not region and player.region:
            region = player.region
    except Exception:
        logger.debug(
            "Could not resolve live player identity for %s#%s during linking",
            request.game_name,
            request.tag_line,
        )

    try:
        account = await service.link_player_account(
            user_id=current_user["id"],
            game_name=request.game_name,
            tag_line=request.tag_line,
            puuid=puuid,
            region=region,
            is_primary=request.is_primary,
        )
        return LinkedPlayerAccountResponse(**account)
    except PlayerServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account linking requires persistent database storage.",
        ) from None


@router.get(
    "/me/accounts",
    response_model=list[LinkedPlayerAccountResponse],
    summary="List all player identities linked to current user",
)
async def list_linked_accounts(
    current_user: CurrentUser,
    service: Service,
) -> list[LinkedPlayerAccountResponse]:
    """Retrieve all Riot player identities linked to the authenticated user."""
    accounts = await service.list_linked_accounts(current_user["id"])
    return [LinkedPlayerAccountResponse(**acc) for acc in accounts]


@router.delete(
    "/me/accounts/{account_id}",
    summary="Remove a linked player identity",
)
async def delete_linked_account(
    account_id: Annotated[str, Path(min_length=1, max_length=64)],
    current_user: CurrentUser,
    service: Service,
) -> dict[str, Any]:
    """Unlink a player identity from the authenticated user."""
    deleted = await service.delete_linked_account(account_id, current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked player account not found.",
        )
    return {"status": "deleted", "account_id": account_id}
