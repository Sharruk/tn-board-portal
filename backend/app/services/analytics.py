from collections import deque, defaultdict
from threading import Lock
from datetime import datetime

_lock = Lock()
_recent: deque = deque(maxlen=20)
_counts: dict = defaultdict(int)


def track_search(term: str, result_count: int) -> None:
    normalized = term.strip().lower()
    with _lock:
        _counts[normalized] += 1
        _recent.appendleft({
            "term": term,
            "result_count": result_count,
            "searched_at": datetime.utcnow().isoformat(),
        })


def get_analytics() -> dict:
    with _lock:
        popular = sorted(_counts.items(), key=lambda x: -x[1])[:20]
        return {
            "popular_searches": [{"term": t, "count": c} for t, c in popular],
            "recent_searches": list(_recent),
        }
