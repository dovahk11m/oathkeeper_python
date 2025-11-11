# app/routers/metrics.py
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from app.models import MetricsPayload
from app.storage import append_metrics_line, has_plan_dir, iter_metrics
from app.services.report_service import compute_summary, summary_to_text

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

def _assert_plan_state(plan_id: int):
    if plan_id <= 0 or not has_plan_dir(plan_id):
        raise HTTPException(status_code=404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    first = next(iter_metrics(plan_id), None)
    if first is None:
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Plan not finished or no metrics yet."})

@router.get("/report/{plan_id}/text")
def read_text(plan_id: int):
    _assert_plan_state(plan_id)
    summary = compute_summary(plan_id)
    text = summary_to_text(summary, mode="rules")
    return {"success": True, "data": text}

@router.post("/report/{plan_id}/text")
def generate_text(plan_id: int, body: Optional[dict] = None):
    _assert_plan_state(plan_id)
    body = body or {}
    mode  = body.get("mode", "rules")     # 'rules' | 'prompt' | 'llm'
    style = body.get("style", "")
    notes = body.get("notes", "")
    name_map = body.get("name_map")       # {memberId: "이름"}

    summary = compute_summary(plan_id)
    text = summary_to_text(summary, mode=mode, style=style, notes=notes, name_map=name_map)
    return {"success": True, "data": text}
