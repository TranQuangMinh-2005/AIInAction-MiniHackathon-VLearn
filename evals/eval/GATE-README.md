# VLearn Eval Gate — README (A-07)

1. **Mục đích**: regression gate tool-routing — so intent/tool agent với golden set sau mỗi thay đổi graph (A-07 "XONG KHI": gate ≥ bar).
2. **Golden mới (mặc định)**: `evals/eval/golden_vlearn_ux.json` — 20 case hệ vlearn-ux (REBASE PO 24/08, xem `validation/A-07-Gate-analysis.md` §5); bar **18/20 (90%)**; case là câu hỏi thật từ chatlog + lớp khó (teencode, off-topic/jailbreak, typo domain, multi-turn, focus paper).
3. **Golden cũ**: `--golden legacy` = 24 case Lab Coach — chỉ làm **smoke tool-match, KHÔNG chặn release** (trần trung thực ~6-7/24 do khác taxonomy).
4. **Chạy DRY (không cần key, mặc định)**: `python3 evals/eval/gate_run.py --dry` — parse golden, liệt kê expected intent/tool từng case, KHÔNG gọi LLM, ghi "cần key để chạy thật".
5. **Chạy REAL (cần key LLM thật + backend chạy)**: `python3 evals/eval/gate_run.py --real --api http://localhost:8002` (Dev2 chạy stack mới ở 8002); `--limit N` smoke; `--golden legacy --real …` cho smoke cũ.
6. **So khớp REAL**: đọc `trace.tool`/`trace.tools`/`trace.intent` trong response (A-07 expose); map alias theo `alias_map` trong golden JSON (slide_lookup→lookup/slide_search, research_papers→papers/web_search_arxiv, web→fetch, summarize→format/summarize_doc, none→no_tool); case `policy_ok=false` PASS khi KHÔNG gọi tool; case `flexible_ok` chấp nhận nhiều tool.
7. **Đọc kết quả**: `evals/eval/gate_results_<ts>.md` — bảng ID/Expected intent/Expected tool/Trạng thái/Ghi chú + dòng tổng (PASS/FAIL/NOT_RUN/TOOL_INFO_MISSING + intent matched) + phân bố intent/tool; exit code 1 khi REAL dưới bar.
8. **TRẠNG THÁI — literal cho từng case**: `PASS`/`FAIL` (chỉ khi REAL + có trace), `NOT_RUN` (DRY — cần key), `TOOL_INFO_MISSING` (backend chưa expose trace), `ERROR` (backend lỗi, vd HTTP 500 thiếu key).
9. **Giới hạn**: REAL cần key thật; case summary phụ thuộc A-03 (t15) — trước đó `summarize` match có thể FAIL trung thực; multi-turn gửi `history` theo case; chi phí 20 × LLM call → chạy on-demand/CI, không chạy mỗi turn.
10. **Quy ước**: không sửa code app — chỉ file trong `evals/eval/`; khi A-07 trace ổn định, REAL mode dùng ngay không cần đổi script.