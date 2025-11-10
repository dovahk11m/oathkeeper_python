from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_client import generate_ko

router = APIRouter()

class GenReq(BaseModel):
    system: str = "항상 한국어로만 답하세요."
    prompt: str

@router.post("/llm/generate")
async def llm_generate(req: GenReq):
    try:
        text = await generate_ko(req.system, req.prompt)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
