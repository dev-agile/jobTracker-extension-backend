import logging

from sqlalchemy.orm import Session

from .core.config import get_settings
from .crud import user as user_crud
from .database import SessionLocal
from .models import Jobs, User, UserInvite  # noqa: F401 — register models

logger = logging.getLogger(__name__)


def seed_admin() -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        user_crud.ensure_admin_user(db, settings.admin_email, settings.admin_password)
        logger.info("Admin user ensured")
    except Exception:
        logger.exception(
            "Could not seed admin user (DB may be unavailable or migrations pending). "
            "App will start anyway."
        )
    finally:
        db.close()
