"""A-06 — Memory Agent: hồ sơ phiên học anonymous per-browser.

- learner_id do CLIENT sinh (random token, localStorage) — KHÔNG lưu PII.
- Store: 1 file JSON/learner tại agent/memory/data/{learner_id}.json (thread-safe).
- Dữ liệu có cấu trúc: doc đang học · trang · khái niệm đã hỏi (kèm số lần) ·
  misconception đã sửa · notes · câu hỏi lặp (count ≥ 2).
- Mọi hàm an toàn với learner_id rỗng/lạ → trả state rỗng, không crash.
"""

from __future__ import annotations

import json
import re
import os
import threading
import time
from pathlib import Path

# Render/deploy: có thể trỏ ra persistent disk qua VLEARN_MEMORY_DIR
_MEMORY_DIR_DEFAULT = Path(__file__).resolve().parent / "data"
MEMORY_DIR = Path(os.getenv("VLEARN_MEMORY_DIR", _MEMORY_DIR_DEFAULT)).expanduser()
_lock = threading.Lock()

_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]+")

EMPTY_STATE: dict = {
    "doc_id": None,
    "page": None,
    "concepts": [],        # [{"name": str, "count": int, "last_asked": float}]
    "misconceptions": [],  # [str]
    "questions": [],       # [{"text": str, "count": int, "last_asked": float}]
    "notes": [],           # [str] legacy
    "page_notes": [],      # P0-4: [{"doc_id", "page", "text", "updated_at"}]
    "paper_source": None,  # t27: paper arXiv gần nhất Research trả về (source filename)
    "updated_at": None,
}


def _safe_learner_id(learner_id: str | None) -> str:
    if not learner_id:
        return ""
    return _SAFE_ID.sub("", learner_id).strip()[:64]


def _path(learner_id: str) -> Path:
    return MEMORY_DIR / f"{_safe_learner_id(learner_id)}.json"


def _load(learner_id: str) -> dict:
    path = _path(learner_id)
    if not path.exists():
        return dict(EMPTY_STATE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(EMPTY_STATE)
    merged = dict(EMPTY_STATE)
    merged.update({key: data[key] for key in merged if key in data})
    return merged


def _save(learner_id: str, state: dict) -> dict:
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = time.time()
        _path(learner_id).write_text(
            json.dumps(state, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    except OSError:
        pass  # lỗi ghi không ảnh hưởng luồng trả lời
    return state


def get_state(learner_id: str) -> dict:
    """State hiện tại; learner_id lạ/rỗng → state rỗng (không crash)."""
    if not _safe_learner_id(learner_id):
        return dict(EMPTY_STATE)
    with _lock:
        return _load(learner_id)


def update_state(learner_id: str, **changes) -> dict:
    """Upsert nhẹ: merge list với dedupe theo tên; doc/page thay thế."""
    if not _safe_learner_id(learner_id):
        return dict(EMPTY_STATE)
    with _lock:
        state = _load(learner_id)
        for key, value in changes.items():
            if key in {"doc_id", "page"}:
                state[key] = value
            elif key in {"concepts", "questions"}:
                state[key] = _bump_list(state.get(key, []), value)
            elif key in {"misconceptions", "notes"}:
                state[key] = _extend_unique(state.get(key, []), value)
            elif key in {"paper_source"}:
                state[key] = value  # t27: thay thế paper gần nhất
            elif key in {"page_notes"}:
                state[key] = _merge_page_notes(state.get("page_notes", []), value)  # P0-4
        return _save(learner_id, state)


def _merge_page_notes(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """P0-4 — hợp notes theo (doc_id, page); dữ liệu mới thay cũ cùng khoá."""
    merged: dict[tuple[str, int], dict] = {}
    for note in existing:
        try:
            merged[(str(note["doc_id"]), int(note["page"]))] = dict(note)
        except (KeyError, TypeError, ValueError):
            continue
    for note in incoming or []:
        try:
            merged[(str(note["doc_id"]), int(note["page"]))] = dict(note)
        except (KeyError, TypeError, ValueError):
            continue
    return list(merged.values())


def set_page_note(
    learner_id: str, doc_id: str, page: int, text: str
) -> dict:
    """P0-4 — upsert note cho (doc, trang); text rỗng = xoá."""
    if not _safe_learner_id(learner_id):
        return dict(EMPTY_STATE)
    with _lock:
        state = _load(learner_id)
        state["page_notes"] = [
            note
            for note in state.get("page_notes", [])
            if not (str(note.get("doc_id")) == str(doc_id) and int(note.get("page", -1)) == int(page))
        ]
        if text.strip():
            state["page_notes"].append({
                "doc_id": str(doc_id),
                "page": int(page),
                "text": text.strip(),
                "updated_at": time.time(),
            })
        return _save(learner_id, state)


def get_page_notes(learner_id: str, doc_id: str | None = None) -> list[dict]:
    """P0-4 — danh sách note (lọc theo doc nếu có)."""
    state = get_state(learner_id)
    notes = state.get("page_notes", []) or []
    if doc_id:
        notes = [n for n in notes if str(n.get("doc_id")) == str(doc_id)]
    return sorted(notes, key=lambda n: int(n.get("page", 0)))


def _bump_list(items: list[dict], names: list[str]) -> list[dict]:
    result = list(items)
    existing = {item["name"] for item in result}
    for name in names or []:
        name = (name or "").strip()
        if not name:
            continue
        if name in existing:
            for item in result:
                if item["name"] == name:
                    item["count"] = item.get("count", 1) + 1
                    item["last_asked"] = time.time()
                    break
        else:
            result.append({"name": name, "count": 1, "last_asked": time.time()})
            existing.add(name)
    return result


def _extend_unique(items: list[str], values: list[str]) -> list[str]:
    result = list(items)
    for value in values or []:
        value = (value or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def record_turn(
    learner_id: str,
    question: str,
    doc_id: str | None = None,
    page: int | None = None,
    concepts: list[str] | None = None,
    misconceptions: list[str] | None = None,
) -> dict:
    """Ghi 1 turn vào memory (được gọi cuối mỗi turn có learner_id)."""
    if not _safe_learner_id(learner_id):
        return dict(EMPTY_STATE)
    with _lock:
        state = _load(learner_id)
        if doc_id:
            state["doc_id"] = doc_id
        if page is not None:
            state["page"] = page
        state["questions"] = _bump_list(state.get("questions", []), [question])
        state["concepts"] = _bump_list(state.get("concepts", []), concepts or [])
        state["misconceptions"] = _extend_unique(
            state.get("misconceptions", []), misconceptions or []
        )
        return _save(learner_id, state)


def repeated_questions(learner_id: str, min_count: int = 2) -> list[str]:
    """Câu hỏi lặp (count ≥ min_count) — dấu hiệu khó cho Tutor Coach."""
    state = get_state(learner_id)
    return [
        item["name"]
        for item in state.get("questions", [])
        if item.get("count", 0) >= min_count
    ]


def known_concepts(learner_id: str, top: int = 3) -> list[str]:
    """Khái niệm đã hỏi (nhiều lần nhất) — dùng khi hội thoại mới (reload)."""
    state = get_state(learner_id)
    items = sorted(
        state.get("concepts", []),
        key=lambda item: item.get("count", 0),
        reverse=True,
    )
    return [item["name"] for item in items[:top]]


def build_context(learner_id: str) -> str:
    """Context ngắn cho câu trả lời (không đổi hành vi khi memory rỗng)."""
    if not _safe_learner_id(learner_id):
        return ""
    state = get_state(learner_id)
    lines: list[str] = []
    concepts = known_concepts(learner_id)
    if concepts:
        lines.append("Khái niệm đã hỏi trước đây: " + ", ".join(concepts) + ".")
    repeated = repeated_questions(learner_id)
    if repeated:
        lines.append("Học viên đã hỏi lặp: " + ", ".join(repeated[:2]) + ".")
    if state.get("misconceptions"):
        lines.append(
            "Đã làm rõ nhầm lẫn: " + ", ".join(state["misconceptions"][:2]) + "."
        )
    return "\n".join(lines)