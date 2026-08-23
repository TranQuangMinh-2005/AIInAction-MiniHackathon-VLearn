"""A-10 — Learning analytics: lỗ hổng kiến thức + gợi ý ôn tập.

Tín hiệu (local, không DB mới):
- Memory (A-06): khái niệm đã hỏi (count, last_asked), misconception, câu hỏi lặp.
- Trace (A-07): số turn, turn lỗi/off_topic (tín hiệu "không tìm thấy"), theo learner_id.
- Feedback (A-07): rating 👍👎 gắn trace_id → điểm trung bình của learner.

Output GET /api/learners/{id}/gaps:
  { gaps: [{concept, ask_count, last_asked, misconception, related_docs, suggestion}],
    signals_total, traces, errors, avg_rating, refreshed_at }
"""

from __future__ import annotations

import time

from agent.memory.store import get_state
from agent.observability.trace import feedback_ratings, traces_for
from agent.rag import DOC_TITLES, slide_index

MAX_GAPS = 5
MIN_SIGNALS = 3  # card frontend chỉ hiện khi signals_total >= 3


def build_gaps(learner_id: str) -> dict:
    memory = get_state(learner_id) if learner_id else {}
    traces = traces_for(learner_id) if learner_id else []
    ratings = (
        feedback_ratings([t.get("trace_id") for t in traces]) if traces else {}
    )

    concepts = sorted(
        memory.get("concepts", []),
        key=lambda item: item.get("count", 0),
        reverse=True,
    )
    misconceptions = memory.get("misconceptions", []) or []
    errors = sum(1 for t in traces if t.get("error"))
    off_topic = sum(
        1 for t in traces if t.get("intent") == "off_topic"
    )
    rating_values = list(ratings.values())
    avg_rating = (
        round(sum(rating_values) / len(rating_values), 2)
        if rating_values
        else None
    )

    gaps = []
    for item in concepts[:MAX_GAPS]:
        concept = item.get("name", "").strip()
        if not concept:
            continue
        related = _related_docs(concept)
        gaps.append(
            {
                "concept": concept,
                "ask_count": item.get("count", 1),
                "last_asked": item.get("last_asked"),
                "misconception": (
                    next(
                        (m for m in misconceptions if concept.casefold() in m.casefold()),
                        None,
                    )
                ),
                "related_docs": related,
                "suggestion": f"Ôn lại {concept}?",
            }
        )

    signals_total = (
        sum(item.get("count", 0) for item in concepts)
        + len(misconceptions)
        + errors
        + off_topic
        + len(rating_values)
    )

    return {
        "gaps": gaps,
        "signals_total": signals_total,
        "min_signals": MIN_SIGNALS,
        "traces": len(traces),
        "errors": errors,
        "off_topic": off_topic,
        "avg_rating": avg_rating,
        "refreshed_at": time.time(),
    }


def _related_docs(concept: str, k: int = 2) -> list[dict]:
    """Tìm doc/trang liên quan khái niệm qua slide index (BM25, toàn corpus)."""
    try:
        results = slide_index.retrieve(concept, k=k, scope="corpus")
    except Exception:
        return []
    docs: list[dict] = []
    for result in results:
        docs.append(
            {
                "doc_id": result["doc_id"],
                "title": DOC_TITLES.get(result["doc_id"], result["doc_id"]),
                "page": result["page"],
            }
        )
    return docs