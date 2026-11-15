"""Prawdziwa anonimizacja plików PDF (PyMuPDF redactions) i DOCX (in-place)."""
from __future__ import annotations

import base64
import html
import io

from .pipeline import RedactionItem


def render_pdf_previews(pdf_bytes: bytes, max_pages: int = 10, dpi: int = 130) -> list[str]:
    """Renderuje strony PDF jako base64 PNG do podglądu dokumentu."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=dpi)
        pages.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
    return pages


def redact_pdf_bytes(pdf_bytes: bytes, redactions: list[RedactionItem], mode: str = "irreversible") -> tuple[bytes, list[str], int]:
    """Nakłada prawdziwe redakcje PDF (usuwa tekst ze strumienia PDF) i zwraca (pdf_bytes, png_previews, hits)."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    hits = 0
    # Unikalne pary (original, token), najdłuższe najpierw
    pairs = sorted({(r.original, r.token) for r in redactions}, key=lambda x: -len(x[0]))
    for page in doc:
        page_hits = 0
        for orig, tok in pairs:
            rects = page.search_for(orig)
            for rect in rects:
                label = tok if mode == "reversible" else ""
                page.add_redact_annot(rect, text=label, fill=(0.08, 0.08, 0.10), text_color=(1, 1, 1), fontsize=8)
                page_hits += 1
        if page_hits:
            page.apply_redactions()
            hits += page_hits

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    previews = render_pdf_previews(out_bytes)
    return out_bytes, previews, hits


def _replace_in_paragraph(para, pairs: list[tuple[str, str]]) -> int:
    """Podmienia frazy w akapicie DOCX, zachowując formatowanie pierwszego runu jeśli trzeba."""
    full = para.text
    if not full:
        return 0
    changed = 0
    new_text = full
    for orig, tok in pairs:
        if orig in new_text:
            new_text = new_text.replace(orig, tok)
            changed += 1
    if not changed:
        return 0
    # Najpierw spróbuj podmienić wewnątrz pojedynczych runów (zachowuje style 1:1)
    run_replaced = False
    for run in para.runs:
        rt = run.text
        for orig, tok in pairs:
            if orig in rt:
                run.text = rt.replace(orig, tok)
                rt = run.text
                run_replaced = True
    # Jeśli fraza była rozbita na wiele runów, scal do pierwszego runu
    if para.text != new_text:
        if para.runs:
            para.runs[0].text = new_text
            for r in para.runs[1:]:
                r.text = ""
        else:
            para.text = new_text
    return changed


def render_docx_html(docx_bytes: bytes) -> str:
    """Renderuje DOCX jako sformatowany podgląd HTML (nagłówki, akapity, tabele)."""
    import docx
    doc = docx.Document(io.BytesIO(docx_bytes))
    parts = ['<div class="doc-sheet">']
    for p in doc.paragraphs:
        if not p.text.strip():
            parts.append("<br>")
            continue
        style = (p.style.name or "").lower() if p.style else ""
        txt = html.escape(p.text)
        if "heading 1" in style or "title" in style:
            parts.append(f"<h3>{txt}</h3>")
        elif "heading" in style:
            parts.append(f"<h4>{txt}</h4>")
        else:
            parts.append(f"<p>{txt}</p>")
    for t in doc.tables:
        parts.append('<table class="doc-tbl">')
        for row in t.rows:
            parts.append("<tr>" + "".join(f"<td>{html.escape(c.text.strip())}</td>" for c in row.cells) + "</tr>")
        parts.append("</table>")
    parts.append("</div>")
    return "".join(parts)


def redact_docx_bytes(docx_bytes: bytes, redactions: list[RedactionItem]) -> tuple[bytes, str, int]:
    """Podmienia dane bezpośrednio w pliku DOCX (akapity + tabele) i zwraca (docx_bytes, html_preview, hits)."""
    import docx
    doc = docx.Document(io.BytesIO(docx_bytes))
    pairs = sorted({(r.original, r.token) for r in redactions}, key=lambda x: -len(x[0]))
    hits = 0
    for p in doc.paragraphs:
        hits += _replace_in_paragraph(p, pairs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    hits += _replace_in_paragraph(p, pairs)
    buf = io.BytesIO()
    doc.save(buf)
    out_bytes = buf.getvalue()
    return out_bytes, render_docx_html(out_bytes), hits
