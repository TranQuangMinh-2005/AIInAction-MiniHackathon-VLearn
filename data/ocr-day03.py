"""A-11 — OCR day03-design-pattern-react.pdf (66/71 trang scan) → sidecar text.

Phương án (ghi CHANGELOG): KHÔNG viết lại PDF (giữ nguyên bản gốc cho viewer
react-pdf — tránh rủi ro render), sinh sidecar text `apps/web/public/day03-ocr/`
mà SlideIndex đọc ưu tiên thay vì extract_text rỗng.

Kỹ thuật: pypdf/fitz xác nhận chỉ 8/71 trang có text layer → tesseract 5.5.2
(hệ thống có sẵn, thiếu vie) + `vie.traineddata` (tessdata_fast, repo-local tại
data/ocr-tessdata/ — không đụng /opt/homebrew). Render 250dpi qua PyMuPDF,
psm 3, tiếng Việt.
"""

import subprocess
import sys
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[1]
PDF = REPO / "apps" / "web" / "public" / "day03-design-pattern-react.pdf"
OUT_DIR = REPO / "apps" / "web" / "public" / "day03-ocr"
TESSDATA = REPO / "data" / "ocr-tessdata"
DOC_ID = "d5"
MIN_TEXT = 20
ZOOM = 250 / 72


def ocr_image(pix: fitz.Pixmap) -> str:
    png = pix.tobytes("png")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", "vie", "--psm", "3"],
        input=png,
        capture_output=True,
        timeout=120,
        env={"TESSDATA_PREFIX": str(TESSDATA), "PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace")[:300])
    return result.stdout.decode("utf-8", errors="replace").strip()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    ocr_count = kept_count = 0
    for i, page in enumerate(doc, 1):
        text = (page.get_text() or "").strip()
        if len(text) >= MIN_TEXT:
            kept_count += 1
            (OUT_DIR / f"{DOC_ID}-p{i}.txt").write_text(text, encoding="utf-8")
            continue
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        try:
            text = ocr_image(pix)
        except Exception as exc:  # OCR lỗi từng trang → giữ trống, không chặn
            print(f"  [warn] page {i} OCR failed: {exc}", flush=True)
            text = ""
        (OUT_DIR / f"{DOC_ID}-p{i}.txt").write_text(text, encoding="utf-8")
        ocr_count += 1
        if i % 10 == 0:
            print(f"  ...{i}/{len(doc)} (ocr={ocr_count}, kept={kept_count})", flush=True)
    print(f"DONE: {len(doc)} pages, OCR {ocr_count}, giữ nguyên text {kept_count}")


if __name__ == "__main__":
    main()