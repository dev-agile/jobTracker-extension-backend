from sqlalchemy.orm import Session

from ..crud import job as job_crud
from ..crud import user as user_crud
from ..schemas.admin import AdminMetrics, UserSummary


def build_admin_metrics(db: Session) -> AdminMetrics:
    users = user_crud.list_users(db)
    jobs_per_user = job_crud.count_jobs_by_user(db)
    global_status = job_crud.count_jobs_by_status(db)
    total_jobs = sum(global_status.values())

    now_invites = user_crud.list_invites(db)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    active_invites = sum(
        1 for i in now_invites if i.accepted_at is None and i.expires_at > now
    )

    summaries: list[UserSummary] = []
    for u in users:
        if u.role == "admin":
            continue
        by_status = job_crud.count_jobs_by_user_and_status(db, u.id)
        summaries.append(
            UserSummary(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                role=u.role,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
                total_jobs=jobs_per_user.get(u.id, 0),
                jobs_by_status=by_status,
            )
        )

    return AdminMetrics(
        total_users=len([u for u in users if u.role == "user"]),
        total_jobs=total_jobs,
        active_invites=active_invites,
        jobs_by_status=global_status,
        users=summaries,
    )
