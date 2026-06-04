from sqlalchemy.orm import Session

from .core.config import get_settings
from .crud import user as user_crud
from .database import SessionLocal
from .models import User, UserInvite, Jobs  # noqa: F401 — register models


def seed_admin() -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        user_crud.ensure_admin_user(db, settings.admin_email, settings.admin_password)
    finally:
        db.close()
