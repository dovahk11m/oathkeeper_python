# app/routers/metrics.py
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.models import MetricsPayload
from app.storage import append_metrics_line

router = APIRouter(tags=["metrics"])

@router.post("/analyze")
async def analyze_metrics(payload: MetricsPayload) -> Dict[str, Any]:
    rec = payload.model_dump(mode="json")
    plan_id = rec["plan_id"]

    if not isinstance(plan_id, int) or plan_id <= 0:
        raise HTTPException(status_code=404, detail={"code": "PLAN_NOT_FOUND", "message": "Invalid plan id."})

    append_metrics_line(plan_id, rec)

    late = rec.get("late_minutes") or 0
    wait = rec.get("wait_minutes") or 0
    score = max(0, 100 - late - 0.5 * wait)

    return {
        "success": True,
        "data": {
            "plan_id": plan_id,
            "member_id": rec["member_id"],
            "score": round(score, 2),
            "summary": f"{rec['distance_km']:.2f}km 이동, {rec['travel_minutes']}분 소요",
        },
    }
