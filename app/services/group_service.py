# app/services/group_service.py
import os
import requests
from typing import Dict, Any, List, Tuple, Optional
from fastapi import HTTPException
from app.storage import has_plan_dir, iter_metrics

# ===== 공통 유틸 =====
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default


def _safe_int(x, default=0):
    try:
        return int(x)
    except:
        return default


# ===== 그룹 요약 집계 =====
def compute_group_summary(plan_ids: List[int]) -> Tuple[Dict[str, Any], List[str]]:
    """
    여러 플랜의 메트릭을 집계하여 그룹 요약 생성
    
    Args:
        plan_ids: 분석할 plan_id 목록
    
    Returns:
        (summary_dict, warnings_list)
        
    Raises:
        HTTPException: 모든 plan_id에 데이터가 없는 경우 409 Conflict
    """
    warnings = []
    all_records = []
    valid_plan_ids = []
    
    # 각 plan_id의 메트릭 데이터 수집
    for plan_id in plan_ids:
        # plan 디렉터리 존재 확인
        if not has_plan_dir(plan_id):
            warnings.append(f"plan_id '{plan_id}' was not found.")
            continue
        
        # 메트릭 데이터 읽기
        records = list(iter_metrics(plan_id))
        if not records:
            warnings.append(f"plan_id '{plan_id}' has no metrics data.")
            continue
        
        all_records.extend(records)
        valid_plan_ids.append(plan_id)
    
    # 모든 plan_id에 문제가 있는 경우
    if not all_records:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NO_DATA",
                "message": "No data available for the given plan_ids."
            }
        )
    
    # 집계 계산
    total_records = len(all_records)
    total_distance = 0.0
    total_travel = 0
    total_late = 0
    total_wait = 0
    
    for r in all_records:
        total_distance += _safe_float(r.get("distance_km", 0))
        total_travel += _safe_int(r.get("travel_minutes", 0))
        total_late += _safe_int(r.get("late_minutes", 0) if r.get("late_minutes") is not None else 0)
        total_wait += _safe_int(r.get("wait_minutes", 0) if r.get("wait_minutes") is not None else 0)
    
    # 플랜당 평균 계산
    num_plans = len(valid_plan_ids)
    avg_distance_per_plan = total_distance / num_plans if num_plans > 0 else 0.0
    avg_travel_per_plan = total_travel / num_plans if num_plans > 0 else 0.0
    avg_late_per_plan = total_late / num_plans if num_plans > 0 else 0.0
    avg_wait_per_plan = total_wait / num_plans if num_plans > 0 else 0.0
    
    summary = {
        "total_plans_analyzed": num_plans,
        "total_records": total_records,
        "total_distance_km": round(total_distance, 2),
        "avg_distance_per_plan_km": round(avg_distance_per_plan, 2),
        "total_travel_minutes": int(total_travel),
        "avg_travel_minutes_per_plan": round(avg_travel_per_plan, 2),
        "total_late_minutes": int(total_late),
        "avg_late_minutes_per_plan": round(avg_late_per_plan, 2),
        "total_wait_minutes": int(total_wait),
        "avg_wait_minutes_per_plan": round(avg_wait_per_plan, 2),
    }
    
    return summary, warnings


# ===== 그룹 요약 텍스트 생성 =====
def group_summary_to_text(
    summary: Dict[str, Any],
    style: str = "",
    notes: str = "",
    mode: str = "llm"
) -> str:
    """
    그룹 요약 데이터를 자연어로 변환
    
    Args:
        summary: compute_group_summary()의 결과
        style: 텍스트 스타일 (예: "친근한 톤으로")
        notes: 추가 요청사항
        mode: 생성 모드 - "rules" (규칙 기반) | "llm" (LLM 사용)
    
    Returns:
        자연어 요약 텍스트
    """
    if mode == "llm":
        return _llm_text_with_ollama(summary, style=style, notes=notes)
    else:
        return _rules_text(summary)


def _rules_text(summary: Dict[str, Any]) -> str:
    """규칙 기반 텍스트 생성 (LLM 없이)"""
    total_plans = summary.get("total_plans_analyzed", 0)
    total_records = summary.get("total_records", 0)
    total_distance = summary.get("total_distance_km", 0)
    avg_distance = summary.get("avg_distance_per_plan_km", 0)
    total_late = summary.get("total_late_minutes", 0)
    avg_late = summary.get("avg_late_minutes_per_plan", 0)
    total_travel = summary.get("total_travel_minutes", 0)
    avg_travel = summary.get("avg_travel_minutes_per_plan", 0)
    
    # 기본 요약
    lines = [
        f"분석된 {total_plans}개의 약속에 따르면,",
        f"총 {total_records}건의 기록이 있으며,",
        f"전체 이동 거리는 {total_distance:.1f}km입니다."
    ]
    
    # 평균 정보
    lines.append(f"약속당 평균 {avg_distance:.1f}km를 이동했으며,")
    lines.append(f"평균 {avg_travel:.1f}분이 소요되었습니다.")
    
    # 지각 정보 (있는 경우)
    if total_late > 0:
        lines.append(f"평균 {avg_late:.1f}분의 지각 시간을 기록했습니다.")
        
        # 지각 경향 분석
        if avg_late > 10:
            lines.append("약속 시간을 준수하는 데 약간의 어려움이 있는 경향을 보입니다.")
        elif avg_late > 5:
            lines.append("대체로 시간을 잘 지키는 편이나 개선의 여지가 있습니다.")
        else:
            lines.append("시간 관리가 잘 되고 있습니다.")
    else:
        lines.append("시간 약속을 잘 지키고 있습니다.")
    
    # 이동 거리 분석
    if avg_distance > 50:
        lines.append("전반적으로 장거리 이동이 잦은 편입니다.")
    elif avg_distance > 20:
        lines.append("중거리 이동이 주를 이루고 있습니다.")
    else:
        lines.append("비교적 가까운 거리에서 만나고 있습니다.")
    
    return " ".join(lines)


def _llm_text_with_ollama(summary: Dict[str, Any], style: str = "", notes: str = "") -> str:
    """Ollama LLM을 사용한 텍스트 생성"""
    
    # 프롬프트 구성
    data_lines = [
        f"총 약속 수: {summary.get('total_plans_analyzed', 0)}개",
        f"총 기록 수: {summary.get('total_records', 0)}건",
        f"총 이동 거리: {summary.get('total_distance_km', 0):.1f}km",
        f"약속당 평균 이동 거리: {summary.get('avg_distance_per_plan_km', 0):.1f}km",
        f"총 이동 시간: {summary.get('total_travel_minutes', 0)}분",
        f"약속당 평균 이동 시간: {summary.get('avg_travel_minutes_per_plan', 0):.1f}분",
        f"총 지각 시간: {summary.get('total_late_minutes', 0)}분",
        f"약속당 평균 지각 시간: {summary.get('avg_late_minutes_per_plan', 0):.1f}분",
    ]
    
    prompt_head = (
        "아래는 여러 약속에 대한 그룹 통계 데이터입니다. "
        "이 데이터를 바탕으로 그룹의 전반적인 활동 패턴을 3~5문장으로 요약해주세요.\n\n"
        "요구사항:\n"
        "- 한국어로 작성\n"
        "- 객관적이고 명확한 톤\n"
        "- 숫자와 단위는 정확히 유지\n"
        "- 이동 패턴, 시간 관리 경향 등을 분석\n"
        "- 메타표현이나 프롬프트 문구는 출력하지 말 것\n"
    )
    
    if style:
        prompt_head += f"- 스타일: {style}\n"
    if notes:
        prompt_head += f"- 추가 요청: {notes}\n"
    
    prompt = prompt_head + "\n데이터:\n" + "\n".join(data_lines)
    
    # Ollama API 호출
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "system": "항상 한국어로만 답합니다. 지시문은 출력하지 않습니다.",
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=90
        )
        response.raise_for_status()
        
        text = response.json().get("response", "").strip()
        return _sanitize_tone(text)
        
    except Exception as e:
        # LLM 실패 시 fallback으로 rules 모드 사용
        return _rules_text(summary)


def _sanitize_tone(text: str) -> str:
    """부적절한 표현 정제"""
    replacements = {
        "운동": "이동",
        "달리며": "이동하며",
        "달리다": "이동하다",
        "달렸": "이동했",
        "완주": "도착",
        "기록을 세웠": "기록이 있었",
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text
