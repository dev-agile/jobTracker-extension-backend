"""Compute bidding intelligence from tracked jobs — no extra tables needed."""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..crud import job as job_crud
from ..crud import user as user_crud
from ..models import Jobs, User
from ..schemas.intelligence import (
    AlertItem,
    FunnelStage,
    IntelligenceReport,
    JobRow,
    KeywordRow,
    KpiItem,
    MemberDetail,
    MemberRow,
    MonthTrend,
    ProposalRow,
    SegItem,
)

MEMBER_COLORS = ["#0E8F5C", "#D8961F", "#2aa56f", "#7e8c85", "#DF4F37", "#3b82f6"]
CONNECT_COST = 0.15
REPLIED = frozenset({"screening", "interview", "offer"})
INTERVIEW = frozenset({"interview", "offer"})
WON = frozenset({"offer"})


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:26], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_money(text: str | None) -> float:
    if not text:
        return 0.0
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    if not nums:
        return 0.0
    try:
        return float(nums[0])
    except ValueError:
        return 0.0


def _parse_connects(text: str | None) -> int:
    if not text:
        return 0
    m = re.search(r"\d+", text)
    return int(m.group()) if m else 0


def _budget_tier(job: Jobs) -> str:
    amount = _parse_money(job.fixed_price) or _parse_money(job.salary) or _parse_money(job.hourly_range)
    if amount >= 10000:
        return "$10k+"
    if amount >= 2000:
        return "$2k–10k"
    if amount >= 500:
        return "$500–2k"
    return "Sub-$500"


def _budget_label(job: Jobs) -> str:
    if job.fixed_price:
        return job.fixed_price
    if job.salary:
        return job.salary
    if job.hourly_range:
        return job.hourly_range
    if job.hourly:
        return job.hourly
    return "—"


def _status(job: Jobs) -> str:
    return (job.status or "applied").lower()


def _in_month(job: Jobs, year: int, month: int) -> bool:
    d = _parse_date(job.applied_date) or _parse_date(job.created_at)
    if not d:
        return False
    return d.year == year and d.month == month


def _filter_jobs(jobs: list[Jobs], year: int | None, month: int | None) -> list[Jobs]:
    if year is None or month is None:
        return jobs
    return [j for j in jobs if _in_month(j, year, month)]


def _funnel_counts(jobs: list[Jobs]) -> list[FunnelStage]:
    total = len(jobs)
    by = Counter(_status(j) for j in jobs)
    replied = sum(by.get(s, 0) for s in REPLIED)
    interviews = sum(by.get(s, 0) for s in INTERVIEW)
    hired = sum(by.get(s, 0) for s in WON)
    viewed = replied + by.get("rejected", 0)
    if viewed == 0 and total:
        viewed = total - by.get("ghosted", 0)
    return [
        FunnelStage(label="Proposals submitted", count=total),
        FunnelStage(label="Viewed by client", count=viewed),
        FunnelStage(label="Client replied", count=replied),
        FunnelStage(label="Interview / chat", count=interviews),
        FunnelStage(label="Hired", count=hired),
    ]


def _pct(num: int, den: int) -> float:
    return round(num / den * 100, 1) if den else 0.0


def _member_lane(jobs: list[Jobs]) -> str:
    skills: Counter[str] = Counter()
    for j in jobs:
        for s in j.skills or []:
            skills[s.strip()] += 1
    if not skills:
        return "General"
    top = skills.most_common(1)[0][0].lower()
    if any(k in top for k in ("seo", "content", "writing")):
        return "SEO" if "seo" in top else "Content"
    if any(k in top for k in ("figma", "design", "ui", "ux", "logo")):
        return "Design"
    return "Web Dev"


def _status_ui(status: str) -> tuple[str, str, str]:
    mapping = {
        "offer": ("Hired", "st-hired", "ok"),
        "interview": ("Interviewing", "st-intv", "warn"),
        "screening": ("Replied", "st-reply", "ok"),
        "applied": ("Viewed", "st-view", "warn"),
        "rejected": ("Rejected", "st-none", "bad"),
        "ghosted": ("No response", "st-none", "bad"),
    }
    return mapping.get(status, ("Applied", "st-view", "warn"))


def _month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%b %Y")


def _spark(values: list[float], n: int = 10) -> list[float]:
    if len(values) <= n:
        return values
    step = len(values) / n
    return [values[int(i * step)] for i in range(n)]


def build_intelligence(db: Session, year: int | None = None, month: int | None = None) -> IntelligenceReport:
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1

    all_jobs = job_crud.get_all_jobs(db)
    users = [u for u in user_crud.list_users(db) if u.role != "admin"]
    user_map = {u.id: u for u in users}

    cur_jobs = _filter_jobs(all_jobs, year, month)
    prev_jobs = _filter_jobs(all_jobs, prev_y, prev_m)

    cur_funnel = _funnel_counts(cur_jobs)
    prev_funnel = _funnel_counts(prev_jobs)
    total = cur_funnel[0].count or 1
    prev_total = prev_funnel[0].count or 1

    reply_cur = _pct(cur_funnel[2].count, total)
    reply_prev = _pct(prev_funnel[2].count, prev_total)
    win_cur = _pct(cur_funnel[4].count, total)
    win_prev = _pct(prev_funnel[4].count, prev_total)
    hires_cur = cur_funnel[4].count
    hires_prev = prev_funnel[4].count

    connects_cur = sum(_parse_connects(j.connects) for j in cur_jobs)
    connects_prev = sum(_parse_connects(j.connects) for j in prev_jobs)
    spend_cur = round(connects_cur * CONNECT_COST, 2)
    spend_prev = round(connects_prev * CONNECT_COST, 2)

    revenue_cur = sum(_parse_money(j.fixed_price or j.salary) for j in cur_jobs if _status(j) in WON)
    revenue_prev = sum(_parse_money(j.fixed_price or j.salary) for j in prev_jobs if _status(j) in WON)

    cost_hire_cur = round(spend_cur / hires_cur, 2) if hires_cur else 0
    cost_hire_prev = round(spend_prev / hires_prev, 2) if hires_prev else 0
    roi_cur = round(revenue_cur / spend_cur, 1) if spend_cur else 0

  # monthly trends (last 10 months)
    trends: list[MonthTrend] = []
    for i in range(9, -1, -1):
        d = datetime(year, month, 1) - timedelta(days=1)
        for _ in range(i):
            d = d.replace(day=1) - timedelta(days=1)
        m_jobs = _filter_jobs(all_jobs, d.year, d.month)
        f = _funnel_counts(m_jobs)
        t_total = f[0].count or 1
        trends.append(
            MonthTrend(
                month=d.strftime("%b"),
                proposals=f[0].count,
                reply_pct=_pct(f[2].count, t_total),
                win_pct=_pct(f[4].count, t_total),
            )
        )

    spark_prop = _spark([t.proposals for t in trends])
    spark_reply = _spark([t.reply_pct for t in trends])
    spark_win = _spark([t.win_pct for t in trends])

    spark_hires = []
    spark_rev = []
    spark_spend = []
    spark_roi = []
    for i in range(9, -1, -1):
        anchor = datetime(year, month, 1)
        m = anchor.month - i
        y = anchor.year
        while m <= 0:
            m += 12
            y -= 1
        mj = _filter_jobs(all_jobs, y, m)
        fj = _funnel_counts(mj)
        spark_hires.append(float(fj[4].count))
        spark_rev.append(sum(_parse_money(j.fixed_price or j.salary) for j in mj if _status(j) in WON) / 1000)
        sc = sum(_parse_connects(j.connects) for j in mj) * CONNECT_COST
        spark_spend.append(sc)
        spark_roi.append(revenue_cur / sc if sc else 0)

    def delta_str(cur: float, prev: float, suffix: str = "", invert: bool = False) -> tuple[str, bool]:
        diff = cur - prev
        up = diff >= 0
        if invert:
            up = not up
        if suffix == "pt":
            return (f"{'+' if diff >= 0 else ''}{diff:.1f}pt", up)
        if suffix == "%":
            pct = (diff / prev * 100) if prev else 0
            return (f"{'+' if pct >= 0 else ''}{pct:.1f}%", up)
        return (f"{'+' if diff >= 0 else ''}{diff:.0f}", up)

    kpis = [
        KpiItem(label="Proposals sent", value=str(total), delta=delta_str(total, prev_total, "%")[0], up=delta_str(total, prev_total, "%")[1], spark=spark_prop),
        KpiItem(label="Reply rate", value=f"{reply_cur}%", delta=delta_str(reply_cur, reply_prev, "pt")[0], up=delta_str(reply_cur, reply_prev, "pt")[1], spark=spark_reply),
        KpiItem(label="Win rate", value=f"{win_cur}%", delta=delta_str(win_cur, win_prev, "pt")[0], up=delta_str(win_cur, win_prev, "pt")[1], flag=win_cur < win_prev, spark=spark_win),
        KpiItem(label="Hires", value=str(hires_cur), delta=delta_str(hires_cur, hires_prev)[0], up=delta_str(hires_cur, hires_prev)[1], spark=spark_hires),
        KpiItem(label="Revenue", value=f"${revenue_cur/1000:.1f}k" if revenue_cur >= 1000 else f"${revenue_cur:.0f}", delta=delta_str(revenue_cur, revenue_prev, "%")[0], up=delta_str(revenue_cur, revenue_prev, "%")[1], spark=spark_rev),
        KpiItem(label="Connects spent", value=f"${spend_cur:.0f}", delta=delta_str(spend_cur, spend_prev, "%")[0], up=not delta_str(spend_cur, spend_prev, "%")[1], spark=spark_spend),
        KpiItem(label="Cost / hire", value=f"${cost_hire_cur:.1f}" if cost_hire_cur else "—", delta=delta_str(cost_hire_cur, cost_hire_prev, "%")[0] if cost_hire_prev else "—", up=cost_hire_cur <= cost_hire_prev if cost_hire_prev else True, spark=spark_spend),
        KpiItem(label="ROI", value=f"{roi_cur:.0f}×" if roi_cur else "—", delta=f"+{max(0, roi_cur - (revenue_prev/spend_prev if spend_prev else 0)):.0f}×" if spend_prev else "—", up=True, spark=spark_roi),
    ]

    members: list[MemberRow] = []
    for i, u in enumerate(users):
        u_jobs = [j for j in cur_jobs if j.user_id == u.id]
        uf = _funnel_counts(u_jobs)
        ut = uf[0].count or 1
        name = u.display_name or u.email.split("@")[0]
        members.append(
            MemberRow(
                id=u.id,
                name=name,
                lane=_member_lane(job_crud.get_jobs_for_user(db, u.id)),
                color=MEMBER_COLORS[i % len(MEMBER_COLORS)],
                proposals=ut,
                view_pct=_pct(uf[1].count, ut),
                reply_pct=_pct(uf[2].count, ut),
                interviews=uf[3].count,
                hires=uf[4].count,
                win_pct=_pct(uf[4].count, ut),
                revenue=sum(_parse_money(j.fixed_price or j.salary) for j in u_jobs if _status(j) in WON),
            )
        )
    members.sort(key=lambda m: m.win_pct, reverse=True)

    # segment funnel
    seg_groups: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        lane = _member_lane([j])
        tier = _budget_tier(j)
        key = f"{lane} · {tier}"
        seg_groups[key].append(j)

    seg_funnel = []
    for key, gj in sorted(seg_groups.items(), key=lambda x: _pct(_funnel_counts(x[1])[4].count, len(x[1])), reverse=True)[:8]:
        gf = _funnel_counts(gj)
        gt = len(gj) or 1
        win = _pct(gf[4].count, gt)
        seg_funnel.append({
            "segment": key,
            "sent": gt,
            "view_pct": _pct(gf[1].count, gt),
            "reply_pct": _pct(gf[2].count, gt),
            "interview_pct": _pct(gf[3].count, gt),
            "win_pct": win,
            "best": win >= win_cur + 3,
            "bad": win < win_cur - 3 and gt >= 5,
        })

    # keywords
    kw_jobs: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        for skill in j.skills or []:
            k = skill.strip()
            if k:
                kw_jobs[k].append(j)

    keywords: list[KeywordRow] = []
    for kw, kj in kw_jobs.items():
        kf = _funnel_counts(kj)
        kt = len(kj) or 1
        avg_b = sum(_parse_money(j.fixed_price or j.salary) for j in kj) / kt
        win = _pct(kf[4].count, kt)
        tier = 1 if len(kj) >= 80 else 2 if len(kj) >= 50 else 3 if len(kj) >= 30 else 4
        keywords.append(
            KeywordRow(
                keyword=kw,
                count=len(kj),
                reply_pct=_pct(kf[2].count, kt),
                win_pct=win,
                avg_budget=f"${avg_b:,.0f}" if avg_b >= 1000 else f"${avg_b:.0f}",
                tier=tier,
            )
        )
    keywords.sort(key=lambda k: k.count, reverse=True)

    avg_win = win_cur

    # title patterns
    def title_bucket(title: str) -> str:
        t = (title or "").lower()
        if t.startswith("build"):
            return '"Build a…"'
        if "migrat" in t or "rebuild" in t:
            return '"Migrate / rebuild"'
        if "design" in t:
            return '"Design a…"'
        if "fix" in t or "debug" in t:
            return '"Fix / debug"'
        if "need" in t and "developer" in t:
            return '"Need a developer"'
        if "looking for" in t or "help" in t:
            return '"Looking for help"'
        return "Other"

    title_groups: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        title_groups[title_bucket(j.title or "")].append(j)

    title_patterns = []
    for label, tj in title_groups.items():
        if label == "Other":
            continue
        tf = _funnel_counts(tj)
        title_patterns.append(SegItem(label=label, value=_pct(tf[4].count, len(tj)), text=f"{_pct(tf[4].count, len(tj))}% win"))
    title_patterns.sort(key=lambda x: x.value, reverse=True)

    # lane win rates
    lane_groups: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        lane_groups[_member_lane([j])].append(j)
    lane_win = [SegItem(label=k, value=_pct(_funnel_counts(v)[4].count, len(v)), text=f"{_pct(_funnel_counts(v)[4].count, len(v))}% win") for k, v in lane_groups.items()]
    lane_win.sort(key=lambda x: x.value, reverse=True)

    budget_groups: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        budget_groups[_budget_tier(j)].append(j)
    order = ["$10k+", "$2k–10k", "$500–2k", "Sub-$500"]
    budget_win = [SegItem(label=t, value=_pct(_funnel_counts(budget_groups[t])[4].count, len(budget_groups[t])), text=f"{_pct(_funnel_counts(budget_groups[t])[4].count, len(budget_groups[t]))}% win") for t in order if budget_groups[t]]

    country_groups: dict[str, list[Jobs]] = defaultdict(list)
    for j in cur_jobs:
        loc = (j.location or "Unknown").strip() or "Unknown"
        country_groups[loc[:30]].append(j)
    country_reply = sorted(
        [SegItem(label=k, value=_pct(_funnel_counts(v)[2].count, len(v)), text=f"{_pct(_funnel_counts(v)[2].count, len(v))}% reply") for k, v in country_groups.items() if len(v) >= 2],
        key=lambda x: x.value,
        reverse=True,
    )[:6]

    verified = [j for j in cur_jobs if j.profile and "payment" in (j.profile or "").lower()]
    quality_win = [
        SegItem(label="Has profile context", value=_pct(_funnel_counts(verified)[4].count, len(verified) or 1), text=f"{_pct(_funnel_counts(verified)[4].count, len(verified) or 1)}% win"),
        SegItem(label="All jobs", value=win_cur, text=f"{win_cur}% win"),
    ]

    # what changed (prev vs 2 months ago rough)
    what_changed = [
        SegItem(label="Proposal volume", value=abs(total - prev_total), text=f"{total} vs {prev_total}", color="var(--coral)" if total < prev_total else "var(--accent)"),
        SegItem(label="Reply rate shift", value=abs(reply_cur - reply_prev), text=f"{reply_cur}% vs {reply_prev}%", color="var(--coral)" if reply_cur < reply_prev else "var(--accent)"),
        SegItem(label="Win rate shift", value=abs(win_cur - win_prev), text=f"{win_cur}% vs {win_prev}%", color="var(--coral)" if win_cur < win_prev else "var(--accent)"),
    ]

    roi_kpis = [
        KpiItem(label="Connects spent", value=f"${spend_cur:.0f}", delta=f"{connects_cur:,} connects", up=False),
        KpiItem(label="Cost per proposal", value=f"${spend_cur/total:.2f}" if total else "—", delta=delta_str(spend_cur / total, spend_prev / prev_total, "%")[0] if prev_total else "—", up=spend_cur / total <= spend_prev / prev_total if prev_total else True),
        KpiItem(label="Cost per hire", value=f"${cost_hire_cur:.1f}" if cost_hire_cur else "—", delta=delta_str(cost_hire_cur, cost_hire_prev, "%")[0] if cost_hire_prev else "—", up=cost_hire_cur <= cost_hire_prev if cost_hire_prev else True),
        KpiItem(label="Revenue / proposal", value=f"${revenue_cur/total:.0f}" if total else "—", delta=delta_str(revenue_cur / total, revenue_prev / prev_total, "%")[0] if prev_total else "—", up=True),
    ]

    sub500 = budget_groups.get("Sub-$500", [])
    waste_seg = [
        SegItem(label="Sub-$500 jobs", value=sum(_parse_connects(j.connects) for j in sub500) * CONNECT_COST, text=f"${sum(_parse_connects(j.connects) for j in sub500) * CONNECT_COST:.0f} spent"),
        SegItem(label="Ghosted jobs", value=sum(_parse_connects(j.connects) for j in cur_jobs if _status(j) == "ghosted") * CONNECT_COST, text="low conversion"),
    ]

    boost_seg = [
        SegItem(label="High-budget ($2k+)", value=_pct(_funnel_counts([j for j in cur_jobs if _budget_tier(j) in ("$2k–10k", "$10k+")])[4].count, len([j for j in cur_jobs if _budget_tier(j) in ("$2k–10k", "$10k+")]) or 1), text="win rate"),
        SegItem(label="Standard bids", value=win_cur, text=f"{win_cur}% overall"),
    ]

    stale_cutoff = now - timedelta(days=21)
    stale_jobs = sum(
        1
        for j in all_jobs
        if _status(j) == "applied"
        and (d := _parse_date(j.applied_date) or _parse_date(j.created_at))
        and d < stale_cutoff
    )

    alerts: list[AlertItem] = []
    for m in members:
        all_u = [j for j in all_jobs if j.user_id == m.id]
        recent = [j for j in all_u if (d := _parse_date(j.applied_date)) and d >= now - timedelta(days=21)]
        old = [j for j in all_u if (d := _parse_date(j.applied_date)) and d < now - timedelta(days=21) and d >= now - timedelta(days=90)]
        if len(recent) >= 5 and len(old) >= 5:
            r_reply = _pct(sum(1 for j in recent if _status(j) in REPLIED), len(recent))
            o_reply = _pct(sum(1 for j in old if _status(j) in REPLIED), len(old))
            if o_reply - r_reply >= 15:
                alerts.append(AlertItem(level="bad", title=f"{m.name}'s reply rate fell sharply", body=f"{o_reply}% → {r_reply}% over 3 weeks.", when="recent"))
    if win_cur < win_prev and prev_funnel[4].count:
        alerts.append(AlertItem(level="bad", title="Agency win rate dipped vs last month", body=f"{win_prev}% → {win_cur}% ({_month_label(prev_y, prev_m)} → {_month_label(year, month)}).", when="1d ago"))
    if stale_jobs:
        alerts.append(AlertItem(level="warn", title=f"{stale_jobs} applications stuck at 'applied' for 21+ days", body="Update statuses or mark as ghosted for accurate funnel.", when="6h ago"))
    if members:
        best = max(members, key=lambda x: x.win_pct)
        alerts.append(AlertItem(level="ok", title=f"{best.name} leads win rate at {best.win_pct}%", body=f"Top performer in {_month_label(year, month)}.", when="1d ago"))

    proposals: list[ProposalRow] = []
    for j in sorted(cur_jobs, key=lambda x: _parse_date(x.applied_date) or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if not (j.cover_letter or j.title):
            continue
        u = user_map.get(j.user_id)
        label, st_cls, sc = _status_ui(_status(j))
        proposals.append(
            ProposalRow(
                id=j.id,
                user_id=j.user_id or "",
                title=j.title or "Untitled",
                by=u.display_name or u.email if u else "Unknown",
                color=MEMBER_COLORS[users.index(u) % len(MEMBER_COLORS)] if u in users else "#7e8c85",
                lane=_member_lane([j]),
                budget=_budget_label(j),
                location=j.location or "—",
                status=label,
                status_class=sc,
                value=_budget_label(j) if _status(j) in WON else ("pending" if _status(j) == "interview" else "—"),
                text=(j.cover_letter or "")[:500],
            )
        )

    kw_insights = []
    for kw in keywords[:3]:
        kw_insights.append({
            "keyword": kw.keyword,
            "lane": _member_lane(kw_jobs.get(kw.keyword, [])),
            "win": f"{kw.win_pct}% win · {kw.avg_budget} avg",
            "text": f"Appears in {kw.count} bids with {kw.reply_pct}% reply rate. {'Strong lane — prioritize.' if kw.win_pct > avg_win else 'Review fit — below average win rate.'}",
            "bad": kw.win_pct < avg_win - 2,
        })

    compare_win = [
        SegItem(label=_month_label(year, month), value=win_cur, text=f"{win_cur}% win"),
        SegItem(label=_month_label(prev_y, prev_m), value=win_prev, text=f"{win_prev}% win"),
    ]

    movers = []
    for m in members:
        prev_u = [j for j in prev_jobs if j.user_id == m.id]
        pw = _pct(_funnel_counts(prev_u)[4].count, len(prev_u) or 1)
        movers.append({"name": m.name, "lane": m.lane, "color": m.color, "win_pct": m.win_pct, "delta": round(m.win_pct - pw, 1)})
    movers.sort(key=lambda x: x["delta"], reverse=True)

    return IntelligenceReport(
        period_label=_month_label(year, month),
        prev_period_label=_month_label(prev_y, prev_m),
        kpis=kpis,
        funnel=cur_funnel,
        members=members,
        seg_funnel=seg_funnel,
        keywords=keywords[:20],
        title_patterns=title_patterns[:6],
        lane_win=lane_win,
        budget_win=budget_win,
        country_reply=country_reply,
        quality_win=quality_win,
        trends=trends,
        what_changed=what_changed,
        roi_kpis=roi_kpis,
        boost_seg=boost_seg,
        waste_seg=waste_seg,
        alerts=alerts,
        proposals=proposals[:50],
        keyword_insights=kw_insights,
        compare_win=compare_win,
        movers=movers[:8],
        stale_jobs=stale_jobs,
        avg_win_pct=avg_win,
    )


def build_member_detail(db: Session, user_id: str, year: int | None = None, month: int | None = None) -> MemberDetail | None:
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        return None

    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month

    all_u_jobs = job_crud.get_jobs_for_user(db, user_id)
    cur_jobs = _filter_jobs(all_u_jobs, year, month)
    users = [u for u in user_crud.list_users(db) if u.role != "admin"]
    idx = next((i for i, u in enumerate(users) if u.id == user_id), 0)

    funnel = _funnel_counts(cur_jobs)
    total = funnel[0].count or 1
    name = user.display_name or user.email.split("@")[0]

    kw_count: Counter[str] = Counter()
    for j in cur_jobs:
        for s in j.skills or []:
            if s.strip():
                kw_count[s.strip()] += 1

    calendar = [0] * 31
    for j in cur_jobs:
        d = _parse_date(j.applied_date)
        if d and d.year == year and d.month == month:
            day = d.day - 1
            if 0 <= day < 31:
                calendar[day] += 1
    max_cal = max(calendar) or 1
    cal_levels = [min(4, max(0, round(c / max_cal * 4))) for c in calendar]

    jobs: list[JobRow] = []
    for j in sorted(cur_jobs, key=lambda x: _parse_date(x.applied_date) or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        label, st_cls, _ = _status_ui(_status(j))
        jobs.append(
            JobRow(
                id=j.id,
                title=j.title or "—",
                keywords=list(j.skills or [])[:6],
                client=j.role or j.location or "—",
                budget=_budget_label(j),
                applied=_parse_date(j.applied_date).strftime("%b %d") if _parse_date(j.applied_date) else "—",
                status=_status(j),
                status_label=label,
                status_class=st_cls,
            )
        )

    revenue = sum(_parse_money(j.fixed_price or j.salary) for j in cur_jobs if _status(j) in WON)

    return MemberDetail(
        id=user_id,
        name=name,
        lane=_member_lane(all_u_jobs),
        color=MEMBER_COLORS[idx % len(MEMBER_COLORS)],
        joined=user.created_at.strftime("%b %Y") if user.created_at else "—",
        kpis=[
            ["Applied this month", str(total)],
            ["Reply rate", f"{_pct(funnel[2].count, total)}%"],
            ["Hires", str(funnel[4].count)],
            ["Revenue", f"${revenue/1000:.1f}k" if revenue >= 1000 else f"${revenue:.0f}"],
        ],
        funnel=funnel,
        keywords=[SegItem(label=k, value=v, text=f"{v} bids") for k, v in kw_count.most_common(6)],
        calendar=cal_levels,
        jobs=jobs,
        proposals=total,
    )
