from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FunnelStage(BaseModel):
    label: str
    count: int


class KpiItem(BaseModel):
    label: str
    value: str
    delta: str
    up: bool
    flag: bool = False
    spark: list[float] = Field(default_factory=list)


class SegItem(BaseModel):
    label: str
    value: float
    text: str
    color: Optional[str] = None


class MemberRow(BaseModel):
    id: str
    name: str
    lane: str
    color: str
    proposals: int
    view_pct: float
    reply_pct: float
    interviews: int
    hires: int
    win_pct: float
    revenue: float
    avg_apply: str = "—"


class KeywordRow(BaseModel):
    keyword: str
    count: int
    reply_pct: float
    win_pct: float
    avg_budget: str
    tier: int


class ProposalRow(BaseModel):
    id: str
    user_id: str
    title: str
    by: str
    color: str
    lane: str
    budget: str
    status: str
    status_class: str
    value: str
    text: str


class AlertItem(BaseModel):
    level: str  # bad | warn | ok
    title: str
    body: str
    when: str = ""


class JobRow(BaseModel):
    id: str
    title: str
    keywords: list[str]
    client: str
    budget: str
    applied: str
    status: str
    status_label: str
    status_class: str


class MemberDetail(BaseModel):
    id: str
    name: str
    lane: str
    color: str
    joined: str
    kpis: list[list[str]]
    funnel: list[FunnelStage]
    keywords: list[SegItem]
    calendar: list[int]
    jobs: list[JobRow]
    proposals: int


class MonthTrend(BaseModel):
    month: str
    proposals: int
    reply_pct: float
    win_pct: float


class IntelligenceReport(BaseModel):
    period_label: str
    prev_period_label: str
    kpis: list[KpiItem]
    funnel: list[FunnelStage]
    members: list[MemberRow]
    seg_funnel: list[dict]
    keywords: list[KeywordRow]
    title_patterns: list[SegItem]
    lane_win: list[SegItem]
    budget_win: list[SegItem]
    country_reply: list[SegItem]
    quality_win: list[SegItem]
    trends: list[MonthTrend]
    what_changed: list[SegItem]
    roi_kpis: list[KpiItem]
    boost_seg: list[SegItem]
    waste_seg: list[SegItem]
    alerts: list[AlertItem]
    proposals: list[ProposalRow]
    keyword_insights: list[dict]
    compare_win: list[SegItem]
    movers: list[dict]
    stale_jobs: int
    avg_win_pct: float
