import os, json
from typing import Iterator, Dict, Any, Optional
from datetime import datetime, timezone

DATA_ROOT = os.environ.get("DATA_ROOT", os.path.join(os.getcwd(), "data"))

def ensure_plan_dir(plan_id: int) -> str:
    plan_dir = os.path.join(DATA_ROOT, f"plan_{plan_id}")
    os.makedirs(plan_dir, exist_ok=True)
    return plan_dir

def metrics_file_path(plan_id: int) -> str:
    return os.path.join(ensure_plan_dir(plan_id), "metrics.jsonl")

def _default_serializer(o):
    if isinstance(o, datetime):
        # UTC ISO8601 문자열로 직렬화
        return o.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Type {type(o)} not serializable")

def append_metrics_line(plan_id: int, record: Dict[str, Any]) -> None:
    """
    플랜별 jsonl에 한 줄 추가 저장.
    record 내 datetime은 default serializer로 ISO 문자열 변환.
    created_at이 없으면 현재시간(UTC)로 보강.
    """
    if not record.get("created_at"):
        record["created_at"] = datetime.now(timezone.utc)
    path = metrics_file_path(plan_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=_default_serializer) + "\n")

def iter_metrics(plan_id: int) -> Iterator[Dict[str, Any]]:
    path = metrics_file_path(plan_id)
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
                continue

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
