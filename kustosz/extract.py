"""Ekstrakcja tekstu z TXT, DOCX, PDF (z opcjonalnym OCR dla skanów)."""
from __future__ import annotations

import io
import os
from pathlib import Path

_CANDIDATE_TESS = [
    os.environ.get("TESSDATA_PREFIX", ""),
    str(Path(__file__).resolve().parents[1] / "tessdata"),
    str(Path.home() / "Desktop" / "LocalDocs" / "tessdata"),
]
TESSDATA_DIR = next((Path(p) for p in _CANDIDATE_TESS if p and Path(p).is_dir()), None)


def _ocr_image(img) -> str:
    try:
        import pytesseract
        cfg = f'--tessdata-dir "{TESSDATA_DIR}"' if TESSDATA_DIR else ""
        return pytesseract.image_to_string(img, lang="pol+eng", config=cfg)
    except Exception:
        return ""


def extract_bytes(filename: str, data: bytes) -> tuple[str, dict]:
    """Zwraca (tekst, metadane_ekstrakcji)."""
    ext = Path(filename).suffix.lower()
    meta = {"filename": filename, "ext": ext, "ocr_pages": 0, "pages": 1}

    if ext in (".txt", ".md", ".csv", ".log", ".json"):
        for enc in ("utf-8-sig", "utf-8", "cp1250"):
            try:
                return data.decode(enc), meta
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace"), meta

    if ext == ".docx":
        import docx
        doc = docx.Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text]
        for t in doc.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return "\n".join(parts), meta

    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            meta["pages"] = len(doc)
            pages_txt = []
            for page in doc:
                txt = (page.get_text("text") or "").strip()
                if len(txt) < 30:
                    pix = page.get_pixmap(dpi=200)
                    from PIL import Image
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_txt = _ocr_image(img).strip()
                    if ocr_txt:
                        txt = ocr_txt
                        meta["ocr_pages"] += 1
                pages_txt.append(txt)
            return "\n\n".join(pages_txt), meta
        except ImportError:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            meta["pages"] = len(reader.pages)
            return "\n\n".join((p.extract_text() or "") for p in reader.pages), meta

    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        txt = _ocr_image(img)
        meta["ocr_pages"] = 1 if txt.strip() else 0
        return txt, meta

    raise ValueError(f"Nieobsługiwany format pliku: {ext}")
