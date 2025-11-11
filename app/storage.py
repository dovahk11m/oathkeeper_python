# app/storage.py
import os, json
from typing import Iterator, Dict, Any, Optional
from datetime import datetime, timezone

DATA_ROOT = os.getenv("DATA_ROOT", os.path.join(os.getcwd(), "data"))

# ---------- 내부 경로 ----------
def _plan_dir(plan_id: int) -> str:
    return os.path.join(DATA_ROOT, f"plan_{plan_id}")

def _metrics_path(plan_id: int) -> str:
    return os.path.join(_plan_dir(plan_id), "metrics.jsonl")

# (호환용) 외부에서 쓰던 이름이 있으면 같이 제공
def metrics_file_path(plan_id: int) -> str:
    return _metrics_path(plan_id)

# ---------- 디렉터리 유틸 ----------
def ensure_plan_dir(plan_id: int) -> str:
    d = _plan_dir(plan_id)
    os.makedirs(d, exist_ok=True)
    return d

def has_plan_dir(plan_id: int) -> bool:
    return os.path.isdir(_plan_dir(plan_id))

# ---------- 직렬화 유틸 ----------
def _default_serializer(o):
    if isinstance(o, datetime):
        return o.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Type {type(o)} not serializable")

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

# ---------- 입출력 ----------
def append_metrics_line(plan_id: int, rec: Dict[str, Any]) -> None:
    """
    플랜별 jsonl에 1줄씩 추가 저장.
    - datetime은 ISO8601로 직렬화
    - created_at 없으면 현재(UTC)로 보강
    """
    ensure_plan_dir(plan_id)
    if not rec.get("created_at"):
        rec["created_at"] = datetime.now(timezone.utc)

    path = _metrics_path(plan_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=_default_serializer) + "\n")

def iter_metrics(plan_id: int) -> Iterator[Dict[str, Any]]:
    """
    metrics.jsonl을 한 줄씩 읽어 dict로 yield.
    파일이 없으면 그냥 종료.
    """
    path = _metrics_path(plan_id)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                yield json.loads(s)
            except Exception:
                # 잘못된 라인은 스킵
                continue
