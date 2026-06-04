from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class InviteCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None


class InviteOut(BaseModel):
    id: str
    email: EmailStr
    token: str
    invite_url: str
    invited_by_email: Optional[str] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    status: str  # pending | accepted | expired

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    id: str
    email: EmailStr
    display_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    total_jobs: int = 0
    jobs_by_status: dict[str, int] = Field(default_factory=dict)


class AdminMetrics(BaseModel):
    total_users: int
    total_jobs: int
    active_invites: int
    jobs_by_status: dict[str, int]
    users: list[UserSummary]


class JobOutAdmin(BaseModel):
    id: str
    userId: Optional[str] = None
    jobTitle: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    appliedAt: Optional[str] = None
    url: Optional[str] = None
