from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 스프링은 snake_case로 보냄: plan_id, member_id, distance_km, travel_minutes ...

class MetricsPayload(BaseModel):
    plan_id: int
    member_id: int
    distance_km: float = 0.0
    travel_minutes: int = 0
    late_minutes: Optional[int] = None
    wait_minutes: Optional[int] = None
    created_at: Optional[datetime] = None


class MemberSummary(BaseModel):
    member_id: int
    records: int
    total_distance_km: float
    avg_distance_km: float
    total_travel_minutes: int
    avg_travel_minutes: float
    avg_late_minutes: float
    avg_wait_minutes: float
    avg_score: float
    first_record_at: Optional[datetime] = None
    last_record_at: Optional[datetime] = None


class OverallSummary(BaseModel):
    members: int
    total_records: int
    total_distance_km: float
    avg_distance_km: float
    total_travel_minutes: int
    avg_travel_minutes: float
    avg_score: float
    first_record_at: Optional[datetime] = None
    last_record_at: Optional[datetime] = None


class ReportResponse(BaseModel):
    plan_id: int
    since: Optional[str] = None
    total_records: int
    members: list[MemberSummary]
    overall: OverallSummary
    summary_text: str
