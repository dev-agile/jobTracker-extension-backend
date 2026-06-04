from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.security import hash_password, verify_password
from ..models import User, UserInvite


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(func.lower(User.email) == email.lower()).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str = "user",
    display_name: str | None = None,
) -> User:
    user = User(
        id=str(uuid4()),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def get_invite_by_token(db: Session, token: str) -> UserInvite | None:
    return db.query(UserInvite).filter(UserInvite.token == token).first()


def get_pending_invite_by_email(db: Session, email: str) -> UserInvite | None:
    now = datetime.now(timezone.utc)
    return (
        db.query(UserInvite)
        .filter(
            func.lower(UserInvite.email) == email.lower(),
            UserInvite.accepted_at.is_(None),
            UserInvite.expires_at > now,
        )
        .first()
    )


def create_invite(
    db: Session,
    *,
    email: str,
    invited_by_id: str,
    expires_at: datetime,
    token: str | None = None,
) -> UserInvite:
    invite = UserInvite(
        id=str(uuid4()),
        email=email.lower().strip(),
        token=token or uuid4().hex,
        invited_by_id=invited_by_id,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def list_invites(db: Session) -> list[UserInvite]:
    return db.query(UserInvite).order_by(UserInvite.created_at.desc()).all()


def mark_invite_accepted(db: Session, invite: UserInvite) -> UserInvite:
    invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invite)
    return invite


def ensure_admin_user(db: Session, email: str, password: str) -> User:
    existing = get_user_by_email(db, email)
    if existing:
        if existing.role != "admin":
            existing.role = "admin"
            existing.password_hash = hash_password(password)
            db.commit()
            db.refresh(existing)
        return existing
    return create_user(db, email=email, password=password, role="admin", display_name="Admin")
