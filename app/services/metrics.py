from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..crud import job as job_crud
from ..crud import user as user_crud
from ..schemas.admin import AdminMetrics, UserSummary


def _invite_counts(invites, now: datetime) -> tuple[int, int, int]:
    pending = accepted = active = 0
    for inv in invites:
        if inv.accepted_at is not None:
            accepted += 1
        elif inv.expires_at > now:
            pending += 1
            active += 1
    return active, pending, accepted


def build_admin_metrics(db: Session) -> AdminMetrics:
    users = user_crud.list_users(db)
    end_users = [u for u in users if u.role != "admin"]
    jobs_per_user = job_crud.count_jobs_by_user(db)
    global_status = job_crud.count_jobs_by_status(db)
    total_jobs = sum(global_status.values())
    jobs_by_source = job_crud.count_jobs_by_source(db)
    pipeline = job_crud.build_pipeline(global_status)
    data_quality_pct = job_crud.global_data_quality_pct(db)
    response_rate_pct = job_crud.response_rate_pct(global_status)

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    active_users_7d = 0
    dormant_users = 0
    for u in end_users:
        if u.last_login_at is None:
            dormant_users += 1
            continue
        login = u.last_login_at
        if login.tzinfo is None:
            login = login.replace(tzinfo=timezone.utc)
        if login >= week_ago:
            active_users_7d += 1
        elif login < month_ago:
            dormant_users += 1

    now_invites = user_crud.list_invites(db)
    active_invites, pending_invites, accepted_invites = _invite_counts(now_invites, now)

    users_with_jobs = sum(1 for u in end_users if jobs_per_user.get(u.id, 0) > 0)
    avg_jobs = round(total_jobs / len(end_users), 1) if end_users else 0.0

    summaries: list[UserSummary] = []
    for u in end_users:
        by_status = job_crud.count_jobs_by_user_and_status(db, u.id)
        user_jobs = job_crud.get_jobs_for_user(db, u.id)
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
                stacks_by_applied_jobs=job_crud.stacks_by_applied_jobs(user_jobs),
                applied_count=by_status.get("applied", 0),
                number_of_connects_used_by_user=job_crud.number_of_connects_used_by_user(db, u.id),
                response_rate_pct=job_crud.response_rate_pct(by_status),
                data_quality_pct=job_crud.data_quality_for_jobs(user_jobs),
            )
        )

    summaries.sort(key=lambda s: s.total_jobs, reverse=True)

    return AdminMetrics(
        total_users=len(end_users),
        total_jobs=total_jobs,
        active_invites=active_invites,
        pending_invites=pending_invites,
        accepted_invites=accepted_invites,
        active_users_7d=active_users_7d,
        dormant_users=dormant_users,
        users_with_jobs=users_with_jobs,
        avg_jobs_per_user=avg_jobs,
        data_quality_pct=data_quality_pct,
        response_rate_pct=response_rate_pct,
        jobs_by_status=global_status,
        jobs_by_source=jobs_by_source,
        pipeline=pipeline,
        users=summaries,
    )
