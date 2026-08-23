#!/usr/bin/env python3
"""
VLearn Eval Gate — golden set tool-routing (A-07).

MẶC ĐỊNH: golden mới `golden_vlearn_ux.json` (20 case hệ vlearn-ux — REBASE PO 24/08,
validation/A-07-Gate-analysis.md §5). Gate bar: 18/20 (90%).

LEGACY: `--golden legacy` = 24 case Lab Coach cũ (embedded dưới, tương đương
benchmark_result_slide_tools_v1_20260731.md) — chỉ làm SMOKE tool-match, KHÔNG chặn
release (9 case skill không tồn tại + 2 policy + 2 fallback chủ đích → trần ~6-7/24).

Cách dùng:
  python3 gate_run.py --dry                        # KHÔNG gọi LLM (mặc định)
  python3 gate_run.py --real --api http://localhost:8002   # gọi backend /api/chat
  python3 gate_run.py --golden legacy --real --api http://localhost:8002  # smoke cũ
  python3 gate_run.py --dry --json out.json        # ghi JSON

REAL mode so khớp (khi A-07 trace expose trong response):
  - trace.tool / tool_calls / tools  → map alias (golden_vlearn_ux.json#alias_map hoặc map dưới)
  - trace.intent                     → so expected_intent (alias intent_alias, so sánh lenient)
  - policy_ok=false                  → kỳ vọng tool none (no_tool/refuse_off_topic)
  - case có flexible_ok              → chấp nhận bất kỳ tool nào trong danh sách

GIỚI HẠN (xem thêm golden_vlearn_ux.json#meta và validation/A-07-Gate-analysis.md):
  1. REAL cần KEY LLM THẬT + backend expose trace (A-07 infra — Dev2 đang làm t14/t18).
  2. Một số case summary phụ thuộc A-03 Summary Agent (t15) — trước đó tool match
     summarize có thể chưa đạt (case này sẽ FAIL trung thực, không phải regression).
  3. Multi-turn case gửi history theo case.history (1 turn trước).
  4. Chạy on-demand sau mỗi thay đổi graph (chi phí 20 × LLM call).
"""

import argparse
import datetime
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_API = "http://localhost:8001"
DEFAULT_GOLDEN = HERE / "golden_vlearn_ux.json"

# ---- LEGACY golden 24 case (Lab Coach) — chỉ smoke ----
LEGACY_GOLDEN = [
    dict(id="TC01", slide="D1 p25", question="Tra xu huong gia API model 2026", expected=["lookup"], baseline=True),
    dict(id="TC02", slide="D1 p8,15", question="Tim paper ve attention interpretability", expected=["papers"], baseline=True),
    dict(id="TC03", slide="D2 p16", question="Doc URL Building effective agents", expected=["fetch"], baseline=True),
    dict(id="TC04", slide="D1 p23", question="Tim social Latest ve tools + memory", expected=["social_search"], baseline=True),
    dict(id="TC05", slide="D1 p20", question="Lay ba bai gan day cua SamAltman", expected=["timeline"], baseline=True),
    dict(id="TC06", slide="D1 p20", question="Tra policy noi bo ve trich nguon", expected=["policy"], baseline=True),
    dict(id="TC07", slide="D2 p11-28", question="Hoi lua chon khi chu de con mo ho", expected=["clarify"], baseline=True),
    dict(id="TC08", slide="D1 p27", question="Format du lieu token thanh brief", expected=["format"], baseline=True),
    dict(id="TC09", slide="D2 p24", question="Chi soan nhap, tuyet doi chua gui", expected=["no_tool"], baseline=False),
    dict(id="TC10", slide="D1 p20", question="Tim tin model moi trong tuan", expected=["lookup"], baseline=True),
    dict(id="TC11", slide="D1 p14", question="Tim paper Lost in the Middle", expected=["papers"], baseline=True),
    dict(id="TC12", slide="D1 p22", question="Doc paper CoT tu URL arXiv cu the", expected=["paper_text"], baseline=False),
    dict(id="TC13", slide="D1 p7", question="Fact-check con so ImageNet", expected=["lookup"], baseline=True),
    dict(id="TC14", slide="D1 p28", question="Tim social Top ve 4 lop prompt", expected=["social_search"], baseline=True),
    dict(id="TC15", slide="D2 p18", question="Lay timeline AndrewYNg", expected=["timeline"], baseline=False),
    dict(id="TC16", slide="D2 p17", question="Tra policy du lieu hoc vien", expected=["policy"], baseline=True),
    dict(id="TC17", slide="D1 p18-19", question="Tim paper so sanh RLHF va DPO", expected=["papers"], baseline=True),
    dict(id="TC18", slide="D1 p27", question="Tim cap nhat gia token trong thang", expected=["lookup"], baseline=True),
    dict(id="TC19", slide="D2 p9-10,28", question="Hoi actor va workflow truoc khi danh gia", expected=["clarify"], baseline=True),
    dict(id="TC20", slide="D1 p20,23-27", question="Format digest AI tieng Viet", expected=["format"], baseline=True),
    dict(id="TC21", slide="D2 p23", question="[multi-turn] Tim vi du precision/recall moi", expected=["lookup"], baseline=True),
    dict(id="TC22", slide="D2 p25-26", question="[multi-turn] Tim paper benchmark agent", expected=["papers"], baseline=True),
    dict(id="TC23", slide="D1 p14", question="[multi-turn] Doc full text Lost in the Middle", expected=["paper_text"], baseline=True),
    dict(id="TC24", slide="D2 p24", question="[multi-turn] Da duyet, gui canh bao metric", expected=["send(confirmed=true)"], baseline=True),
]

# ---- alias mặc định nếu golden JSON không có alias_map ----
DEFAULT_ALIAS = {
    "slide_lookup": ["lookup", "slide_search"],
    "research_papers": ["papers", "web_search_arxiv"],
    "web": ["fetch", "web_search_tavily"],
    "summarize": ["format", "summarize_doc"],
    "none": ["no_tool", "refuse_off_topic"],
}
DEFAULT_INTENT_ALIAS = {"deep": "research", "slide": "normal", "gen": "normal"}


def load_golden(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if "cases" not in data:
        raise SystemExit(f"Golden sai schema (thiếu 'cases'): {path}")
    bar = data.get("bar", {"pass_required": 18, "total": len(data["cases"]), "percent": 90.0})
    data["bar"] = bar
    data.setdefault("alias_map", DEFAULT_ALIAS)
    data.setdefault("intent_alias", DEFAULT_INTENT_ALIAS)
    data.setdefault("name", data.get("dataset", path.stem))
    return data


def load_response(req_data: dict, api: str) -> dict:
    body = json.dumps(req_data).encode("utf-8")
    request = urllib.request.Request(
        f"{api}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_tools(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and item.get("name"):
                out.append(item["name"])
        return out
    if isinstance(raw, dict):
        name = raw.get("name") or raw.get("tool")
        return [name] if name else []
    return []


def extract_trace(resp: dict) -> dict:
    """Trích trace từ response (A-07: trace.tool / trace.tools / trace.intent / trace_id)."""
    trace = resp.get("trace") if isinstance(resp.get("trace"), dict) else {}
    tools = extract_tools(trace.get("tool") or trace.get("tools") or resp.get("tools") or resp.get("tool_calls"))
    intent = trace.get("intent") or resp.get("intent")
    return {"tools": tools, "intent": intent, "trace_id": trace.get("trace_id") or resp.get("trace_id")}


def match_expected(expected_tool, actual_tools, alias_map) -> bool:
    if not actual_tools:
        return False
    expected_aliases = alias_map.get(expected_tool, [expected_tool])
    return any(a in expected_aliases for a in actual_tools)


# Taxonomy orchestrator (quan sát thực tế): deep = câu hỏi sâu HOẶC research;
# unclear = fallback chủ đích → xử lý như normal; off_topic/refuse đều là từ chối.
INTENT_ACCEPT = {
    "normal": {"normal", "deep", "slide", "unclear", "gen"},
    "research": {"research", "deep"},
    "summary": {"summary"},
    "off_topic": {"off_topic", "refuse"},
    "refuse": {"refuse", "off_topic"},
}


def match_intent(expected_intent, actual_intent, intent_alias) -> bool:
    if not actual_intent:
        return None  # không có intent trong trace → không tính
    a = str(actual_intent).strip().lower()
    e = str(expected_intent).strip().lower()
    if a in intent_alias:
        a = intent_alias[a]
    if e in intent_alias:
        e = intent_alias[e]
    return a in INTENT_ACCEPT.get(e, {a})


def run_real(api: str, golden: dict, cases: list[dict]) -> list[dict]:
    alias_map = golden.get("alias_map", DEFAULT_ALIAS)
    intent_alias = golden.get("intent_alias", DEFAULT_INTENT_ALIAS)
    results = []
    for i, case in enumerate(cases, 1):
        req = {
            "question": case["question"],
            "active_doc_id": "d1",
            "current_page": 1,
            "history": case.get("history", []),
            "mode": "research" if case.get("expected_intent") == "research" else "normal",
        }
        row = dict(
            id=case["id"],
            expected_intent=case.get("expected_intent", ""),
            expected_tool=case.get("expected_tool", ""),
            policy_ok=case.get("policy_ok", True),
            status="ERROR", detail="",
        )
        try:
            resp = load_response(req, api)
            row["answered"] = bool(resp.get("answer"))
            trace = extract_trace(resp)
            actual = trace["tools"]
            intent = trace["intent"]
            row["trace_id"] = trace["trace_id"]
            row["actual_tool"] = actual
            row["actual_intent"] = intent
            if not actual:
                row["status"] = "TOOL_INFO_MISSING"
                row["detail"] = "Backend trả lời được nhưng chưa expose tool routing (chờ A-07 trace) — không tính PASS/FAIL"
                results.append(row)
                print(f"  [{i:02d}/{len(cases)}] {row['id']} -> {row['status']}")
                continue
            tool_ok = match_expected(case["expected_tool"], actual, alias_map)
            if case.get("flexible_ok"):
                tool_ok = tool_ok or any(
                    match_expected(f, actual, alias_map) for f in case["flexible_ok"]
                )
            intent_ok = match_intent(case.get("expected_intent", ""), intent, intent_alias)
            policy_ok = case.get("policy_ok", True)
            if not policy_ok:
                # case chính sách: PASS khi KHÔNG gọi tool (none)
                tool_ok = all(a in alias_map.get("none", ["no_tool"]) for a in actual)
            row["tool_ok"] = tool_ok
            row["intent_ok"] = intent_ok
            row["status"] = "PASS" if tool_ok else "FAIL"
            row["detail"] = f"tool={actual} (expect {case['expected_tool']}) · intent={intent} (expect {case.get('expected_intent')})"
        except urllib.error.HTTPError as exc:
            row["detail"] = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            row["detail"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
        print(f"  [{i:02d}/{len(cases)}] {row['id']} -> {row['status']} {row['detail'][:90]}")
    return results


def run_dry(cases: list[dict]) -> list[dict]:
    results = []
    for case in cases:
        results.append(
            dict(
                id=case["id"],
                expected_intent=case.get("expected_intent", ""),
                expected_tool=case.get("expected_tool", ""),
                policy_ok=case.get("policy_ok", True),
                status="NOT_RUN — cần key LLM thật để chạy thật",
                detail="DRY mode: không gọi LLM",
            )
        )
    return results


def summarize(results: list[dict], golden: dict, mode: str) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    not_run = sum(1 for r in results if str(r["status"]).startswith("NOT_RUN"))
    no_info = sum(1 for r in results if r["status"] == "TOOL_INFO_MISSING")
    intent_ok = sum(1 for r in results if isinstance(r.get("intent_ok"), bool) and r["intent_ok"])
    intent_none = sum(1 for r in results if isinstance(r.get("intent_ok"), type(None)))
    bar = golden.get("bar", {"pass_required": 18, "total": total, "percent": 90.0})
    dist = {}
    for r in results:
        key = f"{r.get('expected_intent','?')}/{r.get('expected_tool','?')}"
        dist[key] = dist.get(key, 0) + 1
    summary = dict(
        golden=golden.get("name", "?"),
        mode=mode,
        total=total,
        passed=passed,
        failed=failed,
        not_run=not_run,
        tool_info_missing=no_info,
        intent_matched=intent_ok,
        intent_unavailable=intent_none,
        bar=f"{bar.get('pass_required')}/{bar.get('total')} ({bar.get('percent')}%)",
        gate_ok=(passed >= bar.get("pass_required", 18)),
        distribution=dist,
    )
    return summary


def write_report(results: list[dict], summary: dict, api: str) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = HERE / f"gate_results_{ts}.md"
    lines = [
        "# VLearn Eval Gate — golden tool-routing",
        "",
        f"* **Golden:** `{summary['golden']}` · **Mode:** `{summary['mode']}` · **API:** `{api}`",
        f"* **Gate bar:** {summary['bar']} → gate_ok = {summary['gate_ok']}",
        f"* **Tổng:** {summary['total']} · PASS: {summary['passed']} · FAIL: {summary['failed']} · "
        f"NOT_RUN: {summary['not_run']} · TOOL_INFO_MISSING: {summary['tool_info_missing']} · "
        f"intent matched: {summary['intent_matched']}/{summary['total'] - summary['intent_unavailable']}",
        f"* **Phân bố (intent/tool):** {json.dumps(summary['distribution'], ensure_ascii=False)}",
        "",
        "| ID | Expected intent | Expected tool | Trạng thái | Ghi chú |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r.get('expected_intent','')} | `{r.get('expected_tool','')}` | "
            f"**{r['status']}** | {r.get('detail','')} |"
        )
    lines += [
        "",
        "**Cách đọc:** PASS/FAIL có nghĩa khi mode `real` VÀ backend expose trace.tool.",
        "DRY mode = chưa verify thực tế (cần key LLM thật). Golden mới bar 18/20 (90%);",
        "golden legacy (smoke) không chặn release.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="VLearn eval gate — golden tool-routing (A-07)")
    parser.add_argument("--dry", action="store_true", help="DRY mode (mặc định): không gọi LLM")
    parser.add_argument("--real", action="store_true", help="REAL mode: gọi backend /api/chat")
    parser.add_argument("--api", default=DEFAULT_API, help=f"Base URL backend (mặc định {DEFAULT_API})")
    parser.add_argument("--golden", default=str(DEFAULT_GOLDEN), help="Path golden JSON, hoặc 'legacy' (24 case Lab Coach smoke)")
    parser.add_argument("--json", dest="json_out", help="Ghi kết quả JSON ra file")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N case đầu (smoke test)")
    parser.add_argument("--only", default="", help="Chỉ chạy các case theo ID (vd --only VX11,VX13,VX15)")
    args = parser.parse_args()

    if args.golden == "legacy":
        golden = {"name": "legacy_labcoach_24", "bar": {"pass_required": 21, "total": 24, "percent": 87.5},
                  "alias_map": DEFAULT_ALIAS, "intent_alias": DEFAULT_INTENT_ALIAS,
                  "cases": LEGACY_GOLDEN}
        for c in golden["cases"]:
            c["expected_tool"] = c["expected"][0]
            c["expected_intent"] = "normal"
            c["policy_ok"] = True
    else:
        golden = load_golden(Path(args.golden))

    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        cases = [c for c in golden["cases"] if c["id"] in wanted]
    else:
        cases = golden["cases"][: args.limit] if args.limit > 0 else golden["cases"]
    if args.real:
        print(f"[gate] REAL mode — golden {golden['name']} · API {args.api} ({len(cases)} case × LLM call)")
        results = run_real(args.api, golden, cases)
        summary = summarize(results, golden, "real")
    else:
        print(f"[gate] DRY mode — golden {golden['name']}, KHÔNG gọi LLM (cần key thật để chạy --real)")
        results = run_dry(cases)
        summary = summarize(results, golden, "dry")

    report = write_report(results, summary, args.api)
    print("\n===== SUMMARY =====")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report: {report}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "cases": results}, fh, ensure_ascii=False, indent=2)
        print(f"JSON: {args.json_out}")

    if args.real and summary["tool_info_missing"] == 0:
        return 0 if summary["gate_ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())