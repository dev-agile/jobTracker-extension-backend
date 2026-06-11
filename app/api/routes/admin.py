import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...api.deps import require_admin
from ...core.config import get_settings
from ...crud import job as job_crud
from ...crud import user as user_crud
from ...database import get_db
from ...models import Jobs, User, UserInvite
from ...schemas.admin import (
    AdminMetrics,
    InviteCreate,
    InviteOut,
    JobDetailAdmin,
    JobOutAdmin,
    JobUserContext,
    UserSummary,
)
from ...schemas.intelligence import IntelligenceReport, MemberDetail
from ...services.intelligence import build_intelligence, build_member_detail
from ...services.metrics import build_admin_metrics

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _invite_status(invite: UserInvite) -> str:
    if invite.accepted_at:
        return "accepted"
    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        return "expired"
    return "pending"


def _invite_url(token: str) -> str:
    base = os.getenv("ADMIN_APP_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/invite/{token}"


def _to_invite_out(invite: UserInvite, db: Session) -> InviteOut:
    inviter = user_crud.get_user_by_id(db, invite.invited_by_id)
    return InviteOut(
        id=invite.id,
        email=invite.email,
        token=invite.token,
        invite_url=_invite_url(invite.token),
        invited_by_email=inviter.email if inviter else None,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        created_at=invite.created_at,
        status=_invite_status(invite),
    )


def _to_extension_job(job: Jobs) -> dict:
    return {
        "id": job.id,
        "userId": job.user_id,
        "jobTitle": job.title or "",
        "role": job.role or job.description or "",
        "jobDetails": job.description or "",
        "skills": job.skills or [],
        "experienceLevel": job.experience_level or "",
        "hourlyRange": job.hourly_range or "",
        "hourly": job.hourly or "",
        "projectLength": job.project_length or "",
        "url": job.url,
        "posted": job.posted or "",
        "appliedAt": job.applied_date,
        "status": (job.status or "applied").lower(),
    }


def _to_job_detail_admin(job: Jobs, user: User | None = None) -> JobDetailAdmin:
    user_ctx = None
    if user:
        user_ctx = JobUserContext(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )
    return JobDetailAdmin(
        id=job.id,
        userId=job.user_id,
        user=user_ctx,
        jobTitle=job.title,
        role=job.role,
        jobDetails=job.description,
        skills=list(job.skills or []),
        experienceLevel=job.experience_level,
        hourlyRange=job.hourly_range,
        hourly=job.hourly,
        projectLength=job.project_length,
        fixedPrice=job.fixed_price,
        coverLetter=job.cover_letter,
        connects=job.connects,
        source=job.source,
        url=job.url,
        posted=job.posted,
        appliedAt=job.applied_date,
        status=(job.status or "applied").lower(),
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )


@router.get("/metrics", response_model=AdminMetrics)
def admin_metrics(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return build_admin_metrics(db)


@router.get("/intelligence", response_model=IntelligenceReport)
def admin_intelligence(
    year: int | None = None,
    month: int | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return build_intelligence(db, year=year, month=month)


@router.get("/intelligence/users/{user_id}", response_model=MemberDetail)
def admin_member_intelligence(
    user_id: str,
    year: int | None = None,
    month: int | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    detail = build_member_detail(db, user_id, year=year, month=month)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    return detail


@router.get("/users", response_model=list[UserSummary])
def admin_list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    metrics = build_admin_metrics(db)
    return metrics.users


@router.get("/users/{user_id}/jobs")
def admin_user_jobs(
    user_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    jobs = job_crud.get_jobs_by_user(db, user_id)
    return [_to_extension_job(j) for j in jobs]


@router.get("/users/{user_id}/jobs/{job_id}", response_model=JobDetailAdmin)
def admin_user_job_detail(
    user_id: str,
    job_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    job = job_crud.get_job_by_id(db, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_job_detail_admin(job, user)


@router.get("/invites", response_model=list[InviteOut])
def list_invites(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    invites = user_crud.list_invites(db)
    return [_to_invite_out(i, db) for i in invites]


@router.post("/invites", response_model=InviteOut, status_code=201)
def create_invite(
    body: InviteCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email = body.email.lower().strip()
    if user_crud.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="User already registered")
    if user_crud.get_pending_invite_by_email(db, email):
        raise HTTPException(status_code=400, detail="Pending invite already exists for this email")

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.invite_expire_hours)
    invite = user_crud.create_invite(
        db,
        email=email,
        invited_by_id=admin.id,
        expires_at=expires_at,
    )
    return _to_invite_out(invite, db)
