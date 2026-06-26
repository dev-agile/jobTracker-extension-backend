import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...api.deps import require_admin
from ...core.config import get_settings
from ...crud import job as job_crud
from ...crud import user as user_crud
from ...crud import activity as activity_crud

from ...database import get_db
from ...models import Jobs, User, UserInvite
from ...schemas.admin import (
    ActivityOut,
    AdminMetrics,
    InviteCreate,
    InviteOut,
    JobDetailAdmin,
    JobOutAdmin,
    JobUserContext,
    LeaderBoardUser,
    UserSummary,
)
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


def _to_extension_job(job: Jobs, user: User | None = None) -> JobOutAdmin:
    user_ctx = None
    if user:
        user_ctx = JobUserContext(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )
    return {
        "id": job.id,
        "userId": job.user_id,
        "user": user_ctx,
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

@router.get("/allJobs")
def read_all_jobs_admin(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    jobs = job_crud.get_all_jobs(db)
    job_with_user: list[JobOutAdmin] = []
    for job in jobs:
        user = user_crud.get_user_by_id(db, job.user_id) if job.user_id else None
        job_with_user.append(_to_extension_job(job, user))
    return job_with_user

@router.get("/users", response_model=list[UserSummary])
def admin_list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    metrics = build_admin_metrics(db)
    return metrics.users


@router.get("/users/{user_id}/jobs", response_model=list[JobOutAdmin])
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

@router.delete("/invites/{invite_id}", status_code=204)
def delete_invite(invite_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    invite = user_crud.get_invite_by_id(db, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    user_crud.delete_invite(db, invite_id)
    return {"ok": True, "id": invite_id}

@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    activity_crud.delete_activity_by_user(db, user_id)
    user_crud.delete_invite(db, user.user_invite_id)
    job_crud.delete_jobs_by_user(db, user_id)
    user_crud.delete_user(db, user_id)

    return {"ok": True, "id": user_id}

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

@router.get("/recent-activity", response_model=list[ActivityOut])
def recent_activity(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return activity_crud.get_recent_activity(db)

@router.get("/leaderboard", response_model=list[LeaderBoardUser])
def leaderboard(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = user_crud.list_users(db)
    jobs_per_user = job_crud.count_jobs_by_user(db)
    leaderboard: list[LeaderBoardUser] = []
    for user in users:
        if user.role == "user":
            total_jobs = jobs_per_user.get(user.id, 0)
            jobs_by_status = job_crud.count_jobs_by_user_and_status(db, user.id)

            interview_count = jobs_by_status.get("interview", 0)
            offer_count = jobs_by_status.get("offer", 0)
            rejected_count = jobs_by_status.get("rejected", 0)

            response_rate = (interview_count + offer_count + rejected_count) / total_jobs if total_jobs > 0 else 0
            response_rate = round(response_rate * 100, 1)
            leaderboard.append(LeaderBoardUser(
                id=user.id, 
                email=user.email, 
                display_name=user.display_name, 
                role=user.role,
                total_jobs=total_jobs,
                interview_count=interview_count,
                offer_count=offer_count,
                rejected_count=rejected_count,
                response_rate=response_rate,
            ))
            leaderboard.sort(
                key=lambda u: (u.response_rate, u.total_jobs),
                reverse=True,
            )
    return leaderboard  

@router.delete("/jobs/{job_id}", status_code=200)
def delete_job(job_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    job = job_crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    activity_crud.delete_activity_by_job(db, job.id)
    job_crud.delete_job(db, job_id)
    return {"ok": True, "id": job_id}