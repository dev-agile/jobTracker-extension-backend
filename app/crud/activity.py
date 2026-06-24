from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.activity import Activity, ActivityType


def log_activity(
    db,
    *,
    type: ActivityType | str,
    message,
    actor_user_id=None,
    job_id=None,
    invite_id=None,
    metadata=None,
    actor_display_name=None,
):
    activity = Activity(
        id=str(uuid4()),
        type=type,
        message=message,
        actor_display_name=actor_display_name,
        actor_user_id=actor_user_id,
        job_id=job_id,
        user_invite_id=invite_id,
        activity_metadata=metadata,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity

def get_recent_activity(db: Session) -> list[Activity]:
    return db.query(Activity).order_by(Activity.created_at.desc()).limit(10).all()

def delete_activity_by_user(db: Session, user_id: str):
    db.query(Activity).filter(Activity.actor_user_id == user_id).delete()
    db.commit()

def delete_activity_by_job(db: Session, job_id: str):
    db.query(Activity).filter(Activity.job_id == job_id).delete()
    db.commit()