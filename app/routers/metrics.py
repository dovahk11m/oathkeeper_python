from fastapi import APIRouter, Query
from app.models import MetricsPayload
from app.storage import append_metrics_line
from typing import Optional

router = APIRouter()

@router.post("/analyze")
async def analyze_metrics(payload: MetricsPayload):
    """
    스프링에서 들어온 메트릭을 플랜별 jsonl에 저장 후 요약치 일부 반환.
    - model_dump(mode="json") 로 datetime을 ISO 문자열로 변환
    - storage.append_metrics_line 에서도 datetime 안전 직렬화
    """
    rec = payload.model_dump(mode="json") 
    plan_id = rec["plan_id"]
    append_metrics_line(plan_id, rec)

    late = rec.get("late_minutes") or 0
    wait = rec.get("wait_minutes") or 0
    score = max(0, 100 - late - 0.5 * wait)

    return {
        "plan_id": plan_id,
        "member_id": rec["member_id"],
        "score": round(score, 2),
        "summary": f"{rec['distance_km']:.2f}km 이동, {rec['travel_minutes']}분 소요"
    }

# (리포트 라우트는 기존 report_service를 쓰는 경우 그대로 두면 됩니다)
