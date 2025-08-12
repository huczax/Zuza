from pathlib import Path
import json

def compute_diff(today_dir: Path) -> dict:
    cur = _load_urls(today_dir / "run.jsonl")
    prev_dir = _prev_dir(today_dir)
    prev = _load_urls(prev_dir / "run.jsonl") if prev_dir else set()

    added = sorted(list(cur - prev))
    removed = sorted(list(prev - cur))

    return {
        "added": added,
        "removed": removed,
        "ratio_change": (len(added) + len(removed)) / max(1, len(prev)),
        "prev_dir": str(prev_dir) if prev_dir else None,
    }

def _load_urls(path: Path) -> set[str]:
    if not path.exists(): return set()
    urls = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            for k, v in rec.items():
                if k.endswith("image") or k.endswith("image_url"):
                    if isinstance(v, str):
                        urls.add(v)
        except Exception:
            pass
    return urls

def _prev_dir(today_dir: Path) -> Path | None:
    parent = today_dir.parent
    dirs = sorted([d for d in parent.iterdir() if d.is_dir()])
    if len(dirs) < 2: return None
    return dirs[-2]
