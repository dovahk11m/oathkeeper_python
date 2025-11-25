# app/routers/group.py
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.models import (
    GroupSummaryRequest,
    GroupSummaryResponse,
)
from app.services.group_service import compute_group_summary

router = APIRouter()


@router.post("/group/summary", response_model=GroupSummaryResponse)
async def get_group_summary(req: GroupSummaryRequest) -> Dict[str, Any]:
    """
    여러 plan_id의 메트릭 데이터를 종합하여 그룹 전체의 누적 통계와 자연어 요약을 함께 반환합니다. (v2)
    
    - **plan_ids**: 분석할 plan_id 목록 (최소 1개 이상)
    - **style**: 텍스트 스타일 (예: "친근한 톤으로", "데이터 분석가처럼 객관적인 톤으로")
    - **notes**: 추가 요청사항 (예: "지각 빈도가 높은 경향이 있는지 분석해주세요")
    - **mode**: 생성 모드 - "rules" (규칙 기반) | "llm" (LLM 사용, 기본값)
    
    **응답 구조:**
    - data.group_summary: 그룹 통계 데이터
    - data.text_summary: 자연어 요약 텍스트
    
    일부 plan_id에 문제가 있는 경우 warnings 배열에 포함되며,
    모든 plan_id에 문제가 있는 경우 409 Conflict를 반환합니다.
    """
    try:
        integrated_summary, warnings = compute_group_summary(
            plan_ids=req.plan_ids,
            style=req.style,
            notes=req.notes,
            mode=req.mode
        )
        
        return {
            "success": True,
            "data": integrated_summary,
            "warnings": warnings if warnings else None
        }
    except HTTPException:
        # compute_group_summary에서 발생한 HTTPException은 그대로 전파
        raise
    except Exception as e:
        # 예상치 못한 에러
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": f"An error occurred while computing group summary: {str(e)}"
            }
        )
