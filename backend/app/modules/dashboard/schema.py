from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MetricCard(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    gen_today: int
    gen_month: int
    total_downloads: int


class ActivityLogResponse(BaseModel):
    id: str
    user_name: Optional[str] = None
    action: str
    details: str
    timestamp: datetime


class ChartPoint(BaseModel):
    label: str
    value: int


class DashboardCharts(BaseModel):
    daily_documents: List[ChartPoint]
    user_growth: List[ChartPoint]


class DashboardUserResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    created_at: datetime


class DashboardFullResponse(BaseModel):
    metrics: MetricCard
    recent_activities: List[ActivityLogResponse]
    charts: DashboardCharts
    recent_users: List[DashboardUserResponse]
