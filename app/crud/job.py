from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas
from ..models import Jobs
from .roleAliases import normalize_stack


def get_jobs_by_user(db: Session, user_id: str):
    return db.query(Jobs).filter(Jobs.user_id == user_id).all()


def get_all_jobs(db: Session):
    return db.query(Jobs).all()


def create_job(db: Session, job: schemas.ItemCreate):
    data = job.model_dump() if hasattr(job, "model_dump") else job.dict()
    db_job = Jobs(**data)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def find_if_job_existing(db: Session, job: schemas.ItemCreate):
    if job.url:
        by_url = (
            db.query(Jobs)
            .filter(Jobs.user_id == job.user_id, Jobs.url == job.url)
            .first()
        )
        if by_url:
            return True

    if job.title:
        by_title = (
            db.query(Jobs)
            .filter(
                Jobs.user_id == job.user_id,
                Jobs.title == job.title,
            )
            .first()
        )
        if by_title:
            return True

    if job.description:
        by_description = (
            db.query(Jobs)
            .filter(
                Jobs.user_id == job.user_id,
                Jobs.description == job.description,
            )
            .first()
        )
        if by_description:
            return True

    return False


def delete_job(db: Session, job_id: str):
    existing_job = db.query(Jobs).filter(Jobs.id == job_id).first()
    if not existing_job:
        return False
    db.delete(existing_job)
    db.commit()
    return True


def get_job_by_id(db: Session, job_id: str):
    return db.query(Jobs).filter(Jobs.id == job_id).first()


def update_job(db: Session, job: Jobs, updates: dict):
    for field, value in updates.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


def count_jobs_by_user(db: Session) -> dict[str, int]:
    rows = db.query(Jobs.user_id, func.count(Jobs.id)).group_by(Jobs.user_id).all()
    return {user_id: count for user_id, count in rows if user_id}


def count_jobs_by_status(db: Session) -> dict[str, int]:
    rows = db.query(Jobs.status, func.count(Jobs.id)).group_by(Jobs.status).all()
    result: dict[str, int] = {}
    for status, count in rows:
        key = (status or "unknown").lower()
        result[key] = count
    return result


def count_jobs_by_user_and_status(db: Session, user_id: str) -> dict[str, int]:
    rows = (
        db.query(Jobs.status, func.count(Jobs.id))
        .filter(Jobs.user_id == user_id)
        .group_by(Jobs.status)
        .all()
    )
    return {(status or "unknown").lower(): count for status, count in rows}


def count_jobs_by_source(db: Session) -> dict[str, int]:
    rows = db.query(Jobs.source, func.count(Jobs.id)).group_by(Jobs.source).all()
    result: dict[str, int] = {}
    for source, count in rows:
        key = (source or "unknown").strip() or "unknown"
        result[key] = count
    return result


def _parse_connects(value) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).strip().split("-")[0].strip() or 0)
    except (TypeError, ValueError):
        return 0


def _job_is_complete(job: Jobs) -> bool:
    title = (job.title or "").strip()
    url = (job.url or "").strip()
    applied = (job.applied_date or "").strip()
    description = (job.description or "").strip()
    skills = (job.skills or [])
    cover_letter = (job.cover_letter or "").strip()
    connects = _parse_connects(job.connects)

    return len(title) >= 3 and bool(url) and bool(applied) and len(description) >= 10 and len(skills) >= 2 and len(cover_letter) >= 10 and connects >= 1

def data_missing_for_jobs(db: Session, user_id: str) -> list[str]:
    missing: set[str] = set()
    user_jobs = get_jobs_for_user(db, user_id)
    for job in user_jobs:
        if not _job_is_complete(job):
            missing.update(check_missing_data(job))
    return sorted(missing)


def check_missing_data(job: Jobs) -> list[str]:
    missing: list[str] = []
    if len((job.title or "").strip()) < 3:
        missing.append("title")
    if not (job.url or "").strip():
        missing.append("url")
    if not (job.applied_date or "").strip():
        missing.append("applied date")
    if len((job.description or "").strip()) < 10:
        missing.append("description")
    if len(job.skills or []) <= 0:
        missing.append("skills")
    if len((job.cover_letter or "").strip()) < 10:
        missing.append("cover letter")
    if _parse_connects(job.connects) < 1:
        missing.append("connects")
    return missing

def data_quality_for_jobs(jobs: list[Jobs]) -> float | None:
    if not jobs:
        return None
    complete = sum(1 for job in jobs if _job_is_complete(job))
    return round(complete / len(jobs) * 100, 1)


def global_data_quality_pct(db: Session) -> float | None:
    jobs = db.query(Jobs).all()
    return data_quality_for_jobs(jobs)


def get_jobs_for_user(db: Session, user_id: str) -> list[Jobs]:
    return db.query(Jobs).filter(Jobs.user_id == user_id).all()


PIPELINE_STATUSES = ("applied", "screening", "interview", "offer", "rejected", "ghosted")
RESPONSE_STATUSES = frozenset({"screening", "interview", "offer"})


def response_rate_pct(by_status: dict[str, int]) -> float:
    total = sum(by_status.values())
    if total == 0:
        return 0.0
    progressed = sum(by_status.get(s, 0) for s in RESPONSE_STATUSES)
    return round(progressed / total * 100, 1)


def build_pipeline(by_status: dict[str, int]) -> dict[str, int]:
    return {status: by_status.get(status, 0) for status in PIPELINE_STATUSES}

def number_of_connects_used_by_user(db: Session, user_id: str) -> int:
    jobs_per_user = get_jobs_for_user(db, user_id)
    return sum(_parse_connects(j.connects) for j in jobs_per_user)

def total_connects_used(jobs: list[Jobs]) -> int:
    return sum(_parse_connects(j.connects) for j in jobs)

def stacks_by_applied_jobs(jobs: list[Jobs]) -> dict[str, int]:
    counts = Counter(normalize_stack(j.role) for j in jobs)
    return dict(counts)

def delete_jobs_by_user(db:Session, user_id:str) -> None:
    db.query(Jobs).filter(Jobs.user_id == user_id).delete()
    db.commit()