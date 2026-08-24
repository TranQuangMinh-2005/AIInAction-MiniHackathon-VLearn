#!/bin/bash
# Entrypoint Docker thông minh — hỗ trợ 3 môi trường:
#
# 1) Hugging Face Spaces (VLEARN_HF=1 hoặc PORT=7860):
#    chạy API-ONLY trên ${PORT:-7860}, dữ liệu tại /data (persistent storage)
# 2) Render 1-container (mặc định): start.sh chạy backend 8000 + web ${PORT:-3000}
set -e

if [ -n "$VLEARN_HF" ] || [ "$PORT" = "7860" ]; then
  echo "🚀 HF Spaces mode — API only trên port ${PORT:-7860}, data tại /data"
  export RAG_INDEX_PATH="${RAG_INDEX_PATH:-/data/rag/index.sqlite3}"
  export RAG_PDF_DIR="${RAG_PDF_DIR:-/data/papers}"
  export VLEARN_MEMORY_DIR="${VLEARN_MEMORY_DIR:-/data/memory}"
  export VLEARN_OBS_DIR="${VLEARN_OBS_DIR:-/data/observability}"
  mkdir -p /data/rag /data/papers /data/memory /data/observability

  cd /app/apps/api
  exec python -m uvicorn server:app \
    --host 0.0.0.0 \
    --port "${PORT:-7860}" \
    --app-dir /app/apps/api \
    --workers 1
fi

echo "🚀 Single-container mode — backend 8000 + web ${PORT:-3000}"
exec ./start.sh