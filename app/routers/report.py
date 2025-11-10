# app/routers/report.py  (교체)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Optional, Dict, Any

from app.services.report_service import compute_summary, save_summary, summary_to_text

router = APIRouter()

class TextOptions(BaseModel):
    # 모르는 필드 들어와도 422 안나게 방어
    model_config = ConfigDict(extra="ignore")

    mode: str = "rules"      # "rules" | "prompt" | (추후 "llm")
    style: str = ""
    notes: str = ""
    seed: Optional[int] = None
    # 문자열/정수 키 모두 들어와도 받도록 Dict[str, str]로 받고 아래서 int 변환
    name_map: Optional[Dict[str, str]] = Field(default=None, description="memberId->name 매핑")

@router.get("/report/{plan_id}")
async def get_report(plan_id: int):
    summary = compute_summary(plan_id)
    if summary["overall"]["total_records"] == 0:
        raise HTTPException(status_code=404, detail="No metrics found for this plan.")
    paths = save_summary(plan_id, summary)
    return {"summary": summary, "saved": paths}

@router.get("/report/{plan_id}/text")
async def get_report_text(plan_id: int):
    summary = compute_summary(plan_id)
    if summary["overall"]["total_records"] == 0:
        raise HTTPException(status_code=404, detail="No metrics found for this plan.")
    return {"plan_id": plan_id, "text": summary_to_text(summary, mode="rules")}

@router.post("/report/{plan_id}/text")
async def get_report_text_prompted(plan_id: int, opts: TextOptions):
    summary = compute_summary(plan_id)
    if summary["overall"]["total_records"] == 0:
        raise HTTPException(status_code=404, detail="No metrics found for this plan.")

    # name_map 키(int)로 변환 (스프링이 문자열 키로 보낼 때 대비)
    nm_int: Optional[Dict[int, str]] = None
    if opts.name_map:
        nm_int = {}
        for k, v in opts.name_map.items():
            try:
                nm_int[int(k)] = v
            except Exception:
                # 숫자로 안 바뀌면 그냥 버림(안전)
                pass

    txt = summary_to_text(
        summary,
        mode=opts.mode,
        style=opts.style,
        notes=opts.notes,
        seed=opts.seed,
        name_map=nm_int,
    )
    return {"plan_id": plan_id, "mode": opts.mode, "text": txt}
