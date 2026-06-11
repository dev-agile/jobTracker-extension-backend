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
    stacks_by_applied_jobs: dict[str, int] = Field(default_factory=dict)
    applied_count: int = 0
    response_rate_pct: float = 0.0
    data_quality_pct: float = 0.0
    number_of_connects_used_by_user: int = 0


class AdminMetrics(BaseModel):
    total_users: int
    total_jobs: int
    active_invites: int
    pending_invites: int = 0
    accepted_invites: int = 0
    active_users_7d: int = 0
    dormant_users: int = 0
    users_with_jobs: int = 0
    avg_jobs_per_user: float = 0.0
    data_quality_pct: float = 0.0
    response_rate_pct: float = 0.0
    jobs_by_status: dict[str, int]
    jobs_by_source: dict[str, int] = Field(default_factory=dict)
    pipeline: dict[str, int] = Field(default_factory=dict)
    users: list[UserSummary]
    total_stacks: dict[str, int] = Field(default_factory=dict)
    total_connects_used: int = 0


class JobUserContext(BaseModel):
    id: str
    email: EmailStr
    display_name: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None


class JobDetailAdmin(BaseModel):
    id: str
    userId: Optional[str] = None
    user: Optional[JobUserContext] = None
    jobTitle: Optional[str] = None
    role: Optional[str] = None
    jobDetails: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    experienceLevel: Optional[str] = None
    hourlyRange: Optional[str] = None
    hourly: Optional[str] = None
    projectLength: Optional[str] = None
    fixedPrice: Optional[str] = None
    coverLetter: Optional[str] = None
    connects: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    posted: Optional[str] = None
    appliedAt: Optional[str] = None
    status: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class JobOutAdmin(BaseModel):
    id: str
    userId: Optional[str] = None
    jobTitle: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    appliedAt: Optional[str] = None
    url: Optional[str] = None
