import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(".env.example")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://priyanshu:mypassword123@localhost:5432/jobtracker",
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production-use-long-random-string")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    invite_expire_hours: int = int(os.getenv("INVITE_EXPIRE_HOURS", "72"))
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@jobtracker.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin-change-me")
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
