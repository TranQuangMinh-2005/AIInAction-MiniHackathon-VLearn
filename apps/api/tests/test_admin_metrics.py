"""P0-5 — tests cho admin metrics (mini-dashboard /admin). Offline, không LLM."""

import json
import time

import server
from agent.observability import trace as trace_module
from agent.observability.trace import WINDOW_HOURS, admin_metrics, _concepts_from_questions

FIXED_NOW = 1_800_000_000.0


def _seed(tmp_path, traces: list[dict], feedback: list[dict] | None = None):
    """Ghi sẵn traces.jsonl + feedback.jsonl vào OBS_DIR tạm."""
    obs = tmp_path
    with (obs / "traces.jsonl").open("w", encoding="utf-8") as fh:
        for record in traces:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    if feedback:
        with (obs / "feedback.jsonl").open("w", encoding="utf-8") as fh:
            for record in feedback:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return obs


def test_admin_metrics_aggregates_window(monkeypatch, tmp_path):
    """Tổng hợp đúng: turns, latency avg/P90, cost, success rate, tool usage,
    top concepts, ratings — và loại trace/feedback ngoài cửa sổ."""
    monkeypatch.setattr(trace_module, "OBS_DIR", tmp_path)
    monkeypatch.setattr(trace_module.time, "time", lambda: FIXED_NOW)

    hour = 3600.0
    _seed(
        tmp_path,
        traces=[
            # trong 24h
            {"trace_id": "t1", "ts": FIXED_NOW - 0.5 * hour, "latency_ms": 1000,
             "cost_usd_est": 0.001, "error": None, "tool": "lookup",
             "tool_match": "lookup", "input_text": "RAG là gì?",
             "tokens_in_est": 100, "tokens_out_est": 200},
            {"trace_id": "t2", "ts": FIXED_NOW - 2 * hour, "latency_ms": 2000,
             "cost_usd_est": 0.002, "error": None, "tool": "lookup",
             "tool_match": "lookup", "input_text": "RAG là gì?",
             "tokens_in_est": 100, "tokens_out_est": 200},
            {"trace_id": "t3", "ts": FIXED_NOW - 5 * hour, "latency_ms": 3000,
             "cost_usd_est": 0.003, "error": None, "tool": "summarize_doc",
             "tool_match": "format", "input_text": "Tóm tắt embedding trong slides",
             "tokens_in_est": 150, "tokens_out_est": 800},
            {"trace_id": "t4", "ts": FIXED_NOW - 6 * hour, "latency_ms": 4000,
             "cost_usd_est": 0.004, "error": "LLM timeout", "tool": "web_search_arxiv",
             "tool_match": "papers", "input_text": "React vs ReAct pattern",
             "tokens_in_est": 120, "tokens_out_est": 60},
            # ngoài 24h → phải bị loại
            {"trace_id": "t5", "ts": FIXED_NOW - 30 * hour, "latency_ms": 99999,
             "cost_usd_est": 9.9, "error": None, "tool": "lookup",
             "tool_match": "lookup", "input_text": "cũ",
             "tokens_in_est": 9999, "tokens_out_est": 9999},
        ],
        feedback=[
            {"trace_id": "t1", "rating": 1, "ts": FIXED_NOW - 1 * hour},
            {"trace_id": "t2", "rating": -1, "ts": FIXED_NOW - 2 * hour},
            {"trace_id": "t5", "rating": 1, "ts": FIXED_NOW - 30 * hour},  # ngoài cửa sổ
        ],
    )

    metrics = admin_metrics(window_hours=24.0)
    assert metrics["turns"] == 4
    assert metrics["avg_latency_ms"] == 2500            # (1000+2000+3000+4000)/4
    assert metrics["p90_latency_ms"] == 4000            # nearest-rank: ceil(0.9*4)-1 = 3
    assert metrics["total_cost_usd"] == 0.01            # 0.001+0.002+0.003+0.004
    assert round(metrics["avg_cost_usd"], 4) == 0.0025
    assert metrics["errors"] == 1
    assert metrics["success_rate"] == 0.75
    assert metrics["tokens_in_est"] >= 4                # 4 input_text có token ước lượng
    assert metrics["tool_usage"][0] == {"tool": "lookup", "count": 2}
    assert all(item["count"] > 0 for item in metrics["tool_usage"])
    concepts = {c["concept"]: c["count"] for c in metrics["top_concepts"]}
    assert concepts["rag"] == 2                          # 2 lần "RAG là gì?"
    assert metrics["ratings"] == {"up": 1, "down": 1, "total": 2}


def test_admin_metrics_endpoint_and_window_validation(monkeypatch, tmp_path):
    """GET /api/admin/metrics trả shape đúng; window lạ → 422 (FastAPI TestClient)."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(trace_module, "OBS_DIR", tmp_path)
    monkeypatch.setattr(trace_module.time, "time", lambda: FIXED_NOW)
    _seed(
        tmp_path,
        traces=[
            {"trace_id": "a1", "ts": FIXED_NOW - 600, "latency_ms": 500,
             "cost_usd_est": 0.0005, "error": None, "tool": "slide_search",
             "tool_match": "lookup", "input_text": "LLM là gì?"},
        ],
        feedback=[{"trace_id": "a1", "rating": 1, "ts": FIXED_NOW - 500}],
    )

    client = TestClient(server.app)
    response = client.get("/api/admin/metrics?window=1h")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "window_hours", "turns", "success_rate", "errors", "avg_latency_ms",
        "p90_latency_ms", "total_cost_usd", "avg_cost_usd", "tool_usage",
        "top_concepts", "ratings",
    ):
        assert key in body
    assert body["turns"] == 1
    assert body["ratings"]["up"] == 1

    # 7d hợp lệ, 1h/24h trong WINDOW_HOURS
    assert WINDOW_HOURS == {"1h": 1.0, "24h": 24.0, "7d": 168.0}
    assert client.get("/api/admin/metrics?window=7d").status_code == 200
    # window không hợp lệ
    assert client.get("/api/admin/metrics?window=1month").status_code == 422


def test_concepts_extractor_filters_noise():
    """Chỉ giữ từ in hoa/từ kỹ thuật, bỏ stopwords."""
    concepts = _concepts_from_questions(
        ["RAG là gì?", "Giải thích RAG và embedding", "react pattern LLM agent"]
    )
    names = {c["concept"]: c["count"] for c in concepts}
    assert names["rag"] == 2
    assert names["embedding"] == 1
    assert all(name not in names for name in ("gì", "và", "giải"))