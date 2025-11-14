# app/routers/report.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Optional, Dict, Any
from app.services.report_service import compute_summary, save_summary, summary_to_text

router = APIRouter()

class TextOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: str = "rules"
    style: str = ""
    notes: str = ""
    seed: Optional[int] = None
    name_map: Optional[Dict[str, str]] = Field(default=None)

def _assert_ready_or_409(plan_id: int, summary: dict):
    if summary["overall"]["total_records"] == 0:
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Plan not finished or no metrics yet."})

@router.get("/report/{plan_id}")
async def get_report(plan_id: int):
    summary = compute_summary(plan_id)
    _assert_ready_or_409(plan_id, summary)
    paths = save_summary(plan_id, summary)
    return {"success": True, "data": {"summary": summary, "saved": paths}}

@router.get("/report/{plan_id}/text")
async def get_report_text(plan_id: int):
    summary = compute_summary(plan_id)
    _assert_ready_or_409(plan_id, summary)
    return {"success": True, "data": summary_to_text(summary, mode="rules")}

@router.post("/report/{plan_id}/text")
async def get_report_text_prompted(plan_id: int, opts: TextOptions):
    summary = compute_summary(plan_id)
    _assert_ready_or_409(plan_id, summary)

    nm_int: Optional[Dict[int, str]] = None
    if opts.name_map:
        nm_int = {}
        for k, v in opts.name_map.items():
            try:
                nm_int[int(k)] = v
            except:
                pass

    txt = summary_to_text(
        summary,
        mode=opts.mode,
        style=opts.style,
        notes=opts.notes,
        seed=opts.seed,
        name_map=nm_int,
    )
    return {"success": True, "data": {"plan_id": plan_id, "mode": opts.mode, "text": txt}}

def compute_summary(plan_id: int) -> Dict[str, Any]:
    from app.storage import iter_metrics
    from collections import defaultdict
    from datetime import datetime, timezone

    metrics_iter = iter_metrics(plan_id)
    summary: Dict[str, Any] = {
        "overall": {
            "total_records": 0,
            "by_type": defaultdict(int),
            "first_record_at": None,
            "last_record_at": None,
        },
        "details": [],
    }

    for rec in metrics_iter:
        summary["overall"]["total_records"] += 1
        mtype = rec.get("type", "unknown")
        summary["overall"]["by_type"][mtype] += 1

        created_at_str = rec.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if (summary["overall"]["first_record_at"] is None) or (created_at < summary["overall"]["first_record_at"]):
                summary["overall"]["first_record_at"] = created_at
            if (summary["overall"]["last_record_at"] is None) or (created_at > summary["overall"]["last_record_at"]):
                summary["overall"]["last_record_at"] = created_at

        summary["details"].append(rec)

    # Convert defaultdict to regular dict for JSON serialization
    summary["overall"]["by_type"] = dict(summary["overall"]["by_type"])

    return summary