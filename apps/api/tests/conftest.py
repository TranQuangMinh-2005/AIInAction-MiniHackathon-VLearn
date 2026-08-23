import os
import sys
from pathlib import Path

# ── CI-safe provider defaults ─────────────────────────────────────────────
# CI (GitHub Actions) không có file .env → nếu không set, Settings.from_env()
# chọn provider "gemini" và GeminiChat ném RuntimeError ngay lúc import
# (llm = build_chat_model() chạy ở module level), làm vỡ toàn bộ collection.
# setdefault: khi chạy local với .env thật, giá trị từ .env vẫn được giữ.
os.environ.setdefault("RAG_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key-for-collection")

AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))