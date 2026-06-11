import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ... import schemas
from ...api.deps import get_current_user, require_admin
from ...crud import job as job_crud
from ...database import get_db
from ...models import Jobs, User

router = APIRouter(prefix="/api", tags=["jobs"])

_UPWORK_JOB_PATH = re.compile(r"/(?:jobs/~|nx/proposals/job/~)", re.I)
_JUNK_TITLE = re.compile(
    r"monthly\s+connects|connects\s+and\s+full\s+access|upwork'?s\s+mindful\s+ai|"
    r"mindful\s+ai|get\s+\d+\s+connects|\d+\s+monthly\s+connects|"
    r"maximize your earnings|service fee|refer(?: a)? friend",
    re.I,
)


def _validate_extension_job_payload(job: schemas.ExtensionJobIn) -> None:
    title = (job.jobTitle or "").strip()
    if len(title) < 8 or _JUNK_TITLE.search(title):
        raise HTTPException(status_code=400, detail="Invalid or promotional job title")

    url = (job.url or "").strip()
    if url and "upwork.com" in url.lower() and not _UPWORK_JOB_PATH.search(url):
        raise HTTPException(status_code=400, detail="URL must be an Upwork job posting")


def _to_extension_job(job: Jobs):
    return {
        "id": job.id,
        "userId": job.user_id,
        "jobTitle": job.title or "",
        "company": job.role or job.description or "",
        "jobDetails": job.description or "",
        "skills": job.skills or [],
        "experienceLevel": job.experience_level or "",
        "hourlyRange": job.hourly_range or "",
        "hourly": job.hourly or "",
        "fixedPrice": job.fixed_price or "",
        "projectLength": job.project_length or "",
        "url": job.url,
        "posted": job.posted or "",
        "coverLetter": job.cover_letter or "",
        "connects": job.connects or "",
        "appliedAt": job.applied_date,
        "status": (job.status or "applied").lower(),
    }


@router.get("/jobs")
def read_my_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = job_crud.get_jobs_by_user(db, current_user.id)
    return [_to_extension_job(job) for job in jobs]

@router.get("/allJobs")
def read_all_jobs_admin(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    jobs = job_crud.get_all_jobs(db)
    return [_to_extension_job(job) for job in jobs]


@router.post("/jobs")
def create_job(
    job: schemas.ExtensionJobIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_extension_job_payload(job)

    now = datetime.now(timezone.utc).isoformat()
    user_key = current_user.id

    db_job = schemas.ItemCreate(
        id=job.id or f"ext-{uuid4().hex}",
        user_id=user_key,
        title=job.jobTitle,
        role=job.role,
        description=job.jobDetails,
        skills=job.skills,
        experience_level=job.experienceLevel,
        hourly_range=job.hourlyRange,
        hourly=job.hourly,
        project_length=job.projectLength,
        fixed_price=job.fixedPrice,
        url=job.url,
        posted=job.posted,
        applied_date=job.appliedAt or now,
        status=(job.status or "applied").lower(),
        cover_letter=job.coverLetter,
        connects=job.connects,
        created_at=now,
        updated_at=now,
        source="extension",
    )

    if job_crud.find_if_job_existing(db, db_job):
        raise HTTPException(status_code=409, detail="Job already exists for this user")

    created = job_crud.create_job(db, db_job)
    return _to_extension_job(created)


@router.patch("/jobs/{job_id}")
def update_job(
    job_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_job = job_crud.get_job_by_id(db, job_id)
    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role != "admin" and existing_job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden for this user")

    next_status = (updates.get("status") or existing_job.status or "applied").lower()
    updated = job_crud.update_job(
        db,
        existing_job,
        {"status": next_status, "updated_at": datetime.now(timezone.utc).isoformat()},
    )
    return _to_extension_job(updated)


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_job = job_crud.get_job_by_id(db, job_id)
    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role != "admin" and existing_job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden for this user")

    job_crud.delete_job(db, job_id)
    return {"ok": True, "id": job_id}
