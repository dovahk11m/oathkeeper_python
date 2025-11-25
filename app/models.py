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


# ===== 그룹 요약 관련 모델 =====

class GroupSummaryRequest(BaseModel):
    """그룹 요약 요청"""
    plan_ids: list[int] = Field(..., min_length=1, description="분석할 plan_id 목록")


class GroupSummaryData(BaseModel):
    """그룹 요약 데이터"""
    total_plans_analyzed: int
    total_records: int
    total_distance_km: float
    avg_distance_per_plan_km: float
    total_travel_minutes: int
    avg_travel_minutes_per_plan: float
    total_late_minutes: int
    avg_late_minutes_per_plan: float
    total_wait_minutes: int
    avg_wait_minutes_per_plan: float


class GroupSummaryResponse(BaseModel):
    """그룹 요약 응답"""
    success: bool
    data: GroupSummaryData
    warnings: Optional[list[str]] = None


class GroupTextSummaryRequest(BaseModel):
    """그룹 텍스트 요약 요청"""
    plan_ids: list[int] = Field(..., min_length=1, description="분석할 plan_id 목록")
    style: str = Field(default="", description="텍스트 스타일 (예: '친근한 톤으로')")
    notes: str = Field(default="", description="추가 요청사항")
    mode: str = Field(default="llm", description="생성 모드: rules | prompt | llm")
    seed: Optional[int] = Field(default=None, description="랜덤 시드")


class GroupTextSummaryResponse(BaseModel):
    """그룹 텍스트 요약 응답"""
    success: bool
    data: str
    warnings: Optional[list[str]] = None
