"""Authentication endpoints for user login and identity retrieval."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUser, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate with employee ID or email and retrieve a JWT bearer token.",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate credentials and generate a signed access token.

    Note: Sensitive details such as passwords are never logged.
    """
    # TODO(Module 11): rate limit login
    user = authenticate_user(db, payload.identifier, payload.password)
    settings = get_settings()

    from app.core.jwt import create_access_token

    token = create_access_token(user.id)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=CurrentUser.model_validate(user),
    )


@router.get(
    "/me",
    response_model=CurrentUser,
    status_code=status.HTTP_200_OK,
    summary="Current Authenticated User",
    description="Retrieve profile and location details of the authenticated caller. Never exposes password hashes.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUser:
    """Return the profile of the authenticated caller."""
    return CurrentUser.model_validate(current_user)


# Note: There is no server-side logout endpoint in this stateless JWT architecture.
# User logout is executed on the client by clearing the stored access token from sessionStorage.

