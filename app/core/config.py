import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Project root: jobTracker-extension-backend/
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}. Set it in .env or the process environment.")
    return value


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/jobtracker",
    )
    jwt_secret: str = _require("JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    invite_expire_hours: int = int(os.getenv("INVITE_EXPIRE_HOURS", "72"))
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@jobtracker.com")
    admin_password: str = _require("ADMIN_PASSWORD")
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000",
        ).split(",")
        if o.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
