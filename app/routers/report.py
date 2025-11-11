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
