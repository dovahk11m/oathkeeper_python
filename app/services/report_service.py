# app/services/report_service.py
import os, json, random, requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.storage import ensure_plan_dir, iter_metrics

# ===== 공통 유틸 =====
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _safe_float(x, default=0.0):
    try: return float(x)
    except: return default

def _safe_int(x, default=0):
    try: return int(x)
    except: return default

# ===== 요약 집계 =====
def compute_summary(plan_id: int) -> Dict[str, Any]:
    records = list(iter_metrics(plan_id) or [])
    total_records = len(records)

    per_member: Dict[int, Dict[str, Any]] = {}
    total_dist = 0.0
    total_minutes = 0
    total_late = 0
    total_wait = 0

    for r in records:
        mid = _safe_int(r.get("member_id"))
        d = _safe_float(r.get("distance_km"))
        t = _safe_int(r.get("travel_minutes"))
        l = _safe_int(r.get("late_minutes"), 0) if r.get("late_minutes") is not None else 0
        w = _safe_int(r.get("wait_minutes"), 0) if r.get("wait_minutes") is not None else 0

        if mid not in per_member:
            per_member[mid] = {
                "member_id": mid, "member_name": None,
                "distance_km": 0.0, "travel_minutes": 0,
                "late_minutes": 0, "wait_minutes": 0, "records": 0
            }
        m = per_member[mid]
        m["distance_km"] += d
        m["travel_minutes"] += t
        m["late_minutes"] += l
        m["wait_minutes"] += w
        m["records"] += 1

        total_dist += d
        total_minutes += t
        total_late += l
        total_wait += w

    members = list(per_member.values())
    # 정렬: 거리 우선, 동률이면 시간
    members.sort(key=lambda m: (m["distance_km"], m["travel_minutes"]), reverse=True)

    avg_dist = round(total_dist / total_records, 2) if total_records else 0.0
    avg_minutes = round(total_minutes / total_records, 2) if total_records else 0.0

    return {
        "plan_id": plan_id,
        "generated_at": _now_iso(),
        "overall": {
            "total_records": total_records,
            "total_distance_km": round(total_dist, 2),
            "total_travel_minutes": int(total_minutes),
            "avg_distance_km": avg_dist,
            "avg_travel_minutes": avg_minutes,
            "total_late_minutes": int(total_late),
            "total_wait_minutes": int(total_wait),
        },
        "members": members,
        "highlights": _make_highlights(members)
    }

def _make_highlights(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not members:
        return {"top_distance_member_id": None, "top_minutes_member_id": None,
                "top_late_member_id": None, "top_wait_member_id": None}
    def top_or_none(key):
        return max(members, key=lambda m: m[key]) if any(m[key] for m in members) else None
    top_distance = max(members, key=lambda m: m["distance_km"])
    top_minutes  = max(members, key=lambda m: m["travel_minutes"])
    top_late     = top_or_none("late_minutes")
    top_wait     = top_or_none("wait_minutes")
    return {
        "top_distance_member_id": top_distance["member_id"],
        "top_distance_km": round(top_distance["distance_km"], 2),
        "top_minutes_member_id": top_minutes["member_id"],
        "top_minutes": int(top_minutes["travel_minutes"]),
        "top_late_member_id": (top_late["member_id"] if top_late else None),
        "top_late_minutes": (int(top_late["late_minutes"]) if top_late else 0),
        "top_wait_member_id": (top_wait["member_id"] if top_wait else None),
        "top_wait_minutes": (int(top_wait["wait_minutes"]) if top_wait else 0),
    }

def save_summary(plan_id: int, summary: Dict[str, Any]) -> Dict[str, str]:
    plan_dir = ensure_plan_dir(plan_id)
    os.makedirs(os.path.join(plan_dir, "summary_history"), exist_ok=True)

    summary_path = os.path.join(plan_dir, "summary.json")
    hist_path = os.path.join(
        plan_dir, "summary_history",
        f"{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    )

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return {"summary_path": summary_path, "history_path": hist_path}

# ===================== 텍스트 생성 =====================

def _get_name(mid: int, mems, name_map: Optional[Dict[Any, str]]):
    """name_map의 키가 str/int 섞여와도 안전하게 이름을 찾는다."""
    if isinstance(name_map, dict):
        if mid in name_map:
            return name_map[mid]
        s = str(mid)
        if s in name_map:
            return name_map[s]
    for m in mems:
        if m.get("member_id") == mid:
            nm = m.get("member_name")
            if nm:
                return nm
    return f"회원#{mid}"

def summary_to_text(summary: Dict[str, Any],
                    mode: str = "rules",
                    style: str = "",
                    notes: str = "",
                    seed: Optional[int] = None,
                    name_map: Optional[Dict[int, str]] = None) -> str:
    """
    mode: "rules" | "prompt" | "llm"
    name_map: {memberId: "이름"} -> '회원#id' 대신 이름 사용
    """
    if seed is not None:
        random.seed(seed)

    mems = summary.get("members", [])

    # ✅ 공통 이름 조회 사용
    def name(mid: int) -> str:
        return _get_name(mid, mems, name_map)

    if mode == "llm":
        return _llm_text_with_ollama(summary, style=style, notes=notes, name_map=name_map)

    if mode == "rules":
        return _rules_text(summary, name)

    # ===== prompt 변주형 (LLM 없이 자연스러운 문장) =====
    base_lines = _rules_insights_lines(summary, name)

    openers = [
        "이번 약속을 간단히 정리해볼게요.",
        "데이터로 보면 이런 그림이에요.",
        "핵심만 빠르게 요약해드릴게요.",
        "전체 흐름은 이렇게 보입니다."
    ]
    closers = [
        "다음 약속은 더 편해질 거예요!",
        "조금만 조정하면 훨씬 좋아집니다.",
        "서로 한 걸음씩만 양보해봐요 🙂",
        "좋은 합의 기대합니다!"
    ]
    s = (style or "").lower()
    if "친근" in style or "casual" in s:
        openers += ["편하게 보면요,", "라이트하게 보면,"]
        closers += ["가볍게 시도해봐요!", "파이팅! 💪"]
    if "공식" in style or "formal" in s or "엄밀" in style:
        openers += ["요약 보고 드립니다.", "지표 기준으로 정리합니다."]
        closers += ["이상입니다.", "참고 바랍니다."]

    # notes는 출력에 노출하지 않고 문장 구성에만 영향
    if notes:
        if any(k in notes for k in ["강조", "비교"]):
            base_lines.sort(key=lambda x: ("더 걸렸" in x or "길어요" in x), reverse=True)
        if any(k in notes for k in ["격려", "응원", "파이팅"]):
            closers = ["다음 약속도 파이팅!", "좋은 합의 기대합니다!", "조금만 조정하면 훨씬 좋아져요!"]

    random.shuffle(base_lines)
    trailings = ["", "!", " 🙂", " 😉", " ✅", " ✨"]
    varied = [ln + random.choice(trailings) for ln in base_lines]

    head = random.choice(openers)
    tail = random.choice(closers)
    return "\n".join([f"약속 #{summary.get('plan_id')} {head}"] + varied + [tail])

def _rules_text(summary: Dict[str, Any], name_fn) -> str:
    ov = summary.get("overall", {})
    mems = summary.get("members", [])
    pid = summary.get("plan_id")

    total_records = ov.get('total_records', 0)
    total_km      = ov.get('total_distance_km', 0)
    total_min     = ov.get('total_travel_minutes', 0)

    # 상위 3명만 간단히 언급
    top = sorted(
        mems, key=lambda m: (m.get("distance_km", 0), m.get("travel_minutes", 0)),
        reverse=True
    )[:3]

    head = (
        f"약속 #{pid}의 요약입니다. 총 {total_records}건의 기록이 있으며, "
        f"최근에 종료된 약속 기준으로 정리했습니다."
    )

    mid  = f"전체 이동은 {total_km:.2f}km, 소요 시간은 {total_min}분이었습니다."
    if top:
        parts = [
            f"{name_fn(m['member_id'])}은(는) {m.get('distance_km',0):.2f}km를 이동했고 "
            f"{m.get('travel_minutes',0)}분이 걸렸습니다" for m in top
        ]
        mid += " " + " ".join(parts)

    tail = "다음 약속도 시간 여유를 두고 이동하면 더 편하게 만날 수 있어요."

    return " ".join([head, mid, tail]).strip()


def _rules_insights_lines(summary: Dict[str, Any], name_fn) -> List[str]:
    """
    비교/역설/격려 등 핵심 팩트 문장 생성(LLM 없이 자연스럽게).
    late_minutes가 들어오면 '지각' 축 비교로 확장 가능.
    """
    mems = summary.get("members", [])
    if not mems:
        return ["기록이 없습니다."]

    lines: List[str] = []

    # 1) 이동시간 비교(가장 오래 vs 가장 짧게)
    by_minutes = sorted(mems, key=lambda m: m.get("travel_minutes", 0), reverse=True)
    if len(by_minutes) >= 2:
        worst, best = by_minutes[0], by_minutes[-1]
        diff = int((worst.get("travel_minutes") or 0) - (best.get("travel_minutes") or 0))
        if diff >= 5:
            lines.append(f"{name_fn(worst['member_id'])}님이 {name_fn(best['member_id'])}님보다 이동 시간이 {diff}분 더 걸렸어요")

    # 2) '가까운데 느린' 역설 케이스 (거리 대비 시간)
    avg_dist = summary["overall"].get("avg_distance_km", 0) or 0.0
    for m in mems:
        dist = m.get("distance_km", 0) or 0.0
        mins = m.get("travel_minutes", 0) or 0
        if avg_dist > 0 and dist <= 0.8 * avg_dist and mins >= 15:
            lines.append(f"{name_fn(m['member_id'])}님은 거리는 가까운데 이동에 시간이 조금 더 걸리는 편이에요(약 {mins}분)")

    # 3) 지각/대기 데이터가 있으면 비교 문장 추가(평균 지각분)
    with_late = [m for m in mems if (m.get("late_minutes") or 0) > 0]
    if len(with_late) >= 2:
        by_late = sorted(mems, key=lambda m: (m.get("late_minutes", 0) / max(1, m.get("records", 1))), reverse=True)
        worst, best = by_late[0], by_late[-1]
        worst_avg = round((worst.get("late_minutes", 0)) / max(1, worst.get("records", 1)), 1)
        best_avg  = round((best.get("late_minutes", 0)) / max(1, best.get("records", 1)), 1)
        if worst_avg - best_avg >= 2:
            lines.append(f"{name_fn(worst['member_id'])}님이 {name_fn(best['member_id'])}님보다 평균 {worst_avg - best_avg}분 늦는 경향이 있어요")

    if not lines:
        lines.append("전체적으로 비슷한 패턴이에요. 약간만 조정하면 더 좋아질 거예요")

    return lines

# ====== Ollama LLM 호출 ======
def _sanitize_tone(text: str) -> str:
    repl = {
        "운동": "이동",
        "달리며": "이동하며",
        "달리다": "이동하다",
        "달렸": "이동했",
        "완주": "도착",
        "기록을 세웠": "기록이 있었",
        "seemds": "seems",  # 오타 방어
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text

def _llm_text_with_ollama(summary: dict, style: str = "", notes: str = "", name_map: Optional[Dict[int, str]] = None) -> str:
    ov = summary.get("overall", {})
    mems = summary.get("members", [])

    def nm(mid: int) -> str:
        return _get_name(mid, mems, name_map)

    lines = [f"약속 #{summary.get('plan_id')}"]
    lines.append(f"총 {ov.get('total_records',0)}건, 이동 {ov.get('total_distance_km',0)}km / {ov.get('total_travel_minutes',0)}분")
    for m in mems:
        lines.append(f"- {nm(m['member_id'])}: {m.get('distance_km',0)}km, {m.get('travel_minutes',0)}분")

    head = (
        "아래 데이터를 한국어로 3~5문장으로 간결히 요약하세요. 지시는 출력하지 말 것.\n"
        "- 도메인 톤: 약속/도착/이동 맥락으로만 표현 (여행 경로 요약처럼)\n"
        "- 금지어: 운동, 달리다, 완주, 레이스, 페이스, 기록을 세우다, 스퍼트, 질주\n"
        "- 시작 문장 예: ‘약속 #4의 요약입니다. 총 21건의 기록이 있으며, 최근에 종료된 약속 기준으로 정리했습니다.’\n"
        "- 숫자/단위는 유지, 비교 1문장, 마지막은 짧은 격려. 메타표현/프롬프트 문구 금지."
    )
    if style:
        head += f"\n- 톤/스타일: {style}"
    if notes:
        head += f"\n- 지시사항(출력 금지): {notes}"

    prompt = head + "\n\n" + "\n".join(lines)

    payload = {
        "model": OLLAMA_MODEL,
        "system": "항상 한국어로만 답합니다. 지시문은 출력하지 않습니다.",
        "prompt": prompt,
        "stream": False
    }
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
    r.raise_for_status()
    text = r.json().get("response", "").strip()

    return _sanitize_tone(text)
