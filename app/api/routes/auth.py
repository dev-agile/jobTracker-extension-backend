from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.security import create_access_token
from ...crud import user as user_crud
from ...database import get_db
from ...schemas.auth import AcceptInviteRequest, LoginRequest, TokenResponse, UserOut
from ..deps import get_current_user
from ...models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = user_crud.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
        ),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        display_name=current_user.display_name,
    )


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(body: AcceptInviteRequest, db: Session = Depends(get_db)):
    invite = user_crud.get_invite_by_token(db, body.token.strip())
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.accepted_at:
        raise HTTPException(status_code=400, detail="Invite already used")
    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status_code=400, detail="Invite expired")

    if user_crud.get_user_by_email(db, invite.email):
        raise HTTPException(status_code=400, detail="User already exists for this email")

    user = user_crud.create_user(
        db,
        email=invite.email,
        password=body.password,
        role="user",
        display_name=body.display_name,
    )
    user_crud.mark_invite_accepted(db, invite)
    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
        ),
    )


@router.get("/invite/{token}")
def preview_invite(token: str, db: Session = Depends(get_db)):
    """Public: check if invite is valid before showing accept form."""
    invite = user_crud.get_invite_by_token(db, token.strip())
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if invite.accepted_at:
        return {"valid": False, "reason": "already_used", "email": invite.email}
    if expires < now:
        return {"valid": False, "reason": "expired", "email": invite.email}
    return {"valid": True, "email": invite.email, "expires_at": invite.expires_at.isoformat()}
