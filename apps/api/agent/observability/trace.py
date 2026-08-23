"""A-07 — Eval & Observability (phần 2): trace mỗi turn + feedback rating.

- record_trace(): JSONL mỗi turn {trace_id, ts, mode, intent, tools, tool_match,
  latency_ms, tokens_in_est, tokens_out_est, cost_usd_est, error}.
- estimate: tokens ≈ chars/4 (ước lượng trung thực, ghi rõ _est); cost theo
  giá gpt-4o-mini xấp xỉ (in $0.00000015/token, out $0.00000060/token) → cost≠0.
- record_feedback(): JSONL rating 👍👎 kèm trace_id (endpoint /api/feedback).
- tool_match: alias theo từ vựng golden set Lab Coach (gate_run.py TC01–TC24)
  — mapping được ghi rõ ở _GOLDEN_TOOL_MAP (không phải kết quả tạo ra).
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import uuid
from pathlib import Path

# Render/deploy: có thể trỏ ra persistent disk qua VLEARN_OBS_DIR
_OBS_DIR_DEFAULT = Path(__file__).resolve().parent / "data"
OBS_DIR = Path(os.getenv("VLEARN_OBS_DIR", _OBS_DIR_DEFAULT)).expanduser()

# Alias golden-vocabulary (từng là tool của golden set Lab Coach) cho gate
# REAL tool-match. Mapping TRUNG THỰC theo ngữ nghĩa:
#   lookup = truy xuất slide/tài liệu · papers = research/paper arXiv ·
#   fetch = lấy nội dung web (Tavily/DDG) · format = summary map-reduce ·
#   clarify = chưa rõ/hỏi lại · no_tool = từ chối/không dùng tool.
_GOLDEN_TOOL_MAP = {
    "slide_search": "lookup",
    "summarize_doc": "format",
    "web_search_arxiv": "papers",
    "web_search_tavily": "fetch",
    "refuse_off_topic": "no_tool",
    "clarify": "clarify",
}

_TOKENS_PER_CHAR = 4.0
_COST_IN_PER_TOKEN = 0.00000015
_COST_OUT_PER_TOKEN = 0.00000060


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text or "") / _TOKENS_PER_CHAR))


def _trace_path() -> Path:
    return OBS_DIR / "traces.jsonl"


def _feedback_path() -> Path:
    return OBS_DIR / "feedback.jsonl"


def _append(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass  # observability lỗi không chặn luồng trả lời


def golden_tool_alias(tool: str | None) -> str | None:
    if not tool:
        return None
    return _GOLDEN_TOOL_MAP.get(tool, tool)


def record_trace(
    *,
    trace_id: str,
    mode: str,
    intent: str | None,
    tools: list[str],
    answer_text: str = "",
    input_text: str = "",
    error: str | None = None,
    latency_ms: int = 0,
    learner_id: str | None = None,
) -> dict:
    tokens_out = estimate_tokens(answer_text)
    tokens_in = estimate_tokens(input_text)
    cost_usd = round(
        tokens_in * _COST_IN_PER_TOKEN + tokens_out * _COST_OUT_PER_TOKEN,
        6,
    )
    primary_tool = tools[0] if tools else None
    payload = {
        "trace_id": trace_id,
        "ts": time.time(),
        "mode": mode,
        "intent": intent,
        "tools": tools,
        "tool": golden_tool_alias(primary_tool),  # gate tool-match đọc key này
        "tool_match": golden_tool_alias(primary_tool),
        "latency_ms": latency_ms,
        "tokens_in_est": tokens_in,
        "tokens_out_est": tokens_out,
        "cost_usd_est": cost_usd,
        "error": error,
        "learner_id": learner_id,  # A-10: gắn learner cho analytics (additive)
    }
    _append(_trace_path(), payload)
    return payload


def record_feedback(trace_id: str, rating: int, comment: str = "") -> bool:
    """Lưu rating 👍(1)/👎(-1) gắn trace_id. False khi dữ liệu không hợp lệ."""
    if trace_id not in {None, ""} and not isinstance(trace_id, str):
        return False
    if rating not in (1, -1):
        return False
    _append(
        _feedback_path(),
        {
            "trace_id": trace_id or "",
            "rating": rating,
            "comment": (comment or "")[:500],
            "ts": time.time(),
        },
    )
    return True


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return records


def traces_for(learner_id: str) -> list[dict]:
    """A-10 — mọi trace của learner (lọc theo learner_id trong payload)."""
    if not learner_id:
        return []
    return [
        record
        for record in _read_jsonl(_trace_path())
        if record.get("learner_id") == learner_id
    ]


def feedback_ratings(trace_ids: list[str]) -> dict[str, int]:
    """A-10 — trace_id → rating gần nhất (cho analytics gaps)."""
    ratings: dict[str, int] = {}
    for record in _read_jsonl(_feedback_path()):
        trace_id = record.get("trace_id")
        if trace_id in trace_ids:
            ratings[trace_id] = int(record.get("rating", 0))
    return ratings


# ── P0-5: admin metrics (mini-dashboard /admin) ──────────────────────────────

WINDOW_HOURS = {"1h": 1.0, "24h": 24.0, "7d": 168.0}

_STOPWORDS = frozenset({
    "bạn", "mình", "cho", "giúp", "có", "không", "một", "này", "nào", "thì",
    "với", "của", "trong", "trên", "slide", "trang", "bài", "giảng", "về",
    "gì", "thế", "như", "là", "các", "được", "hãy", "tôi", "em", "thầy",
    "hỏi", "giải", "thích", "tóm", "tắt", "tại", "sao", "giữa", "khác", "hay",
    "theo", "phần", "nội", "dung", "chính", "đang", "xem",
})
_TECH_HINTS = re.compile(
    r"rag|llm|token|embed|retriev|agent|react|prompt|vector|arxiv|paper|graph|"
    r"api|model|openai|gemini|langchain|summary|ocr|multiview|transform",
    re.IGNORECASE,
)


def _concepts_from_questions(texts: list[str], top_n: int = 5) -> list[dict]:
    """P0-5 — trích khái niệm thường gặp từ câu hỏi (heuristic deterministic).

    Chỉ tính từ in hoa (React, RAG, LLM…) hoặc từ kỹ thuật (embedding, retrieval…)
    để tránh nhiễu từ thường; đếm tần suất, trả top_n.
    """
    counts: dict[str, int] = {}
    for text in texts:
        for token in re.findall(r"[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9_\-]{1,}", text or ""):
            key = token.lower()
            if len(key) < 3 or key in _STOPWORDS or key.isdigit():
                continue
            if not (token.isupper() or _TECH_HINTS.search(key)):
                continue
            counts[key] = counts.get(key, 0) + 1
    return [
        {"concept": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    ]


def admin_metrics(window_hours: float = 24.0, top_n: int = 5) -> dict:
    """P0-5 — tổng hợp metrics từ traces.jsonl + feedback.jsonl trong cửa sổ thời gian.

    window_hours: 1.0 (1h) · 24.0 (24h) · 168.0 (7d). Không gọi LLM, không chặn lỗi.
    """
    now = time.time()
    since = now - window_hours * 3600
    traces = [r for r in _read_jsonl(_trace_path()) if r.get("ts", 0) >= since]
    feedback = [r for r in _read_jsonl(_feedback_path()) if r.get("ts", 0) >= since]

    turns = len(traces)
    latencies = sorted(int(r.get("latency_ms", 0) or 0) for r in traces)
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0
    # nearest-rank P90: ceil(0.9 * n) - 1 (vd n=4 → index 3 = giá trị cao thứ 4)
    p90_latency = (
        latencies[math.ceil(len(latencies) * 0.9) - 1] if latencies else 0
    )

    total_cost = round(sum(float(r.get("cost_usd_est", 0) or 0) for r in traces), 6)
    avg_cost = round(total_cost / turns, 6) if turns else 0.0
    tokens_in = sum(int(r.get("tokens_in_est", 0) or 0) for r in traces)
    tokens_out = sum(int(r.get("tokens_out_est", 0) or 0) for r in traces)
    errors = sum(1 for r in traces if r.get("error"))
    success_rate = round((turns - errors) / turns, 4) if turns else 0.0

    tool_counts: dict[str, int] = {}
    for r in traces:
        tool = r.get("tool_match") or r.get("tool") or "unknown"
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
    tool_usage = [
        {"tool": tool, "count": count}
        for tool, count in sorted(tool_counts.items(), key=lambda kv: -kv[1])
    ]

    top_concepts = _concepts_from_questions(
        [r.get("input_text", "") for r in traces], top_n
    )

    up = sum(1 for f in feedback if f.get("rating") == 1)
    down = sum(1 for f in feedback if f.get("rating") == -1)

    return {
        "window_hours": window_hours,
        "since_ts": round(since, 3),
        "turns": turns,
        "success_rate": success_rate,
        "errors": errors,
        "avg_latency_ms": avg_latency,
        "p90_latency_ms": p90_latency,
        "total_cost_usd": total_cost,
        "avg_cost_usd": avg_cost,
        "tokens_in_est": tokens_in,
        "tokens_out_est": tokens_out,
        "tool_usage": tool_usage,
        "top_concepts": top_concepts,
        "ratings": {"up": up, "down": down, "total": len(feedback)},
    }