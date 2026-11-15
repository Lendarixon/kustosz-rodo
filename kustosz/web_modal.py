"""FastAPI aplikacja dla publicznego demo na Modal."""
import base64
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

import kustosz.pipeline as pl
from kustosz.doc_redact import redact_docx_bytes, redact_pdf_bytes, render_docx_html, render_pdf_previews
from kustosz.extract import extract_bytes


class AnonReq(BaseModel):
    text: str = ""
    mode: str = "irreversible"
    use_slm: bool = True
    doc_id: str | None = None
    mask_style: str = "label"
    custom_text: str = ""
    enabled_kinds: list[str] | None = None
    custom_mask: list[str] = []
    custom_keep: list[str] = []
    kind_replacements: dict[str, str] = {}


class RestoreReq(BaseModel):
    masked_text: str = ""
    vault: dict[str, str] = {}


def build_app(classify_fn, model_file: str) -> FastAPI:
    pl.classify_chunk = classify_fn
    api = FastAPI(title="Linda Kustosz RODO")
    ui_html = Path("/root/ui/index.html").read_text(encoding="utf-8")
    uploads: dict[str, dict] = {}
    results: dict[str, dict] = {}

    @api.get("/", response_class=HTMLResponse)
    def index():
        return ui_html

    @api.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    @api.get("/prezentacja.pdf")
    def prezentacja_pdf():
        pdf_path = Path("/root/Kustosz_RODO_Prezentacja.pdf")
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Brak pliku prezentacji")
        return Response(
            content=pdf_path.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="Kustosz_RODO_Prezentacja.pdf"'},
        )

    @api.get("/api/status")
    def status():
        return {"ok": True, "model": model_file, "device": "Modal T4 GPU"}

    @api.get("/api/sample/{fname}")
    def sample(fname: str):
        fpath = Path("/root/samples") / Path(fname).name
        if not fpath.is_file():
            raise HTTPException(404, "Brak przykładu")
        raw = fpath.read_bytes()
        txt, meta = extract_bytes(fpath.name, raw)
        doc_id = uuid.uuid4().hex[:12]
        ext = fpath.suffix.lower()
        uploads[doc_id] = {"filename": fpath.name, "ext": ext, "bytes": raw}
        out = {"doc_id": doc_id, "filename": fpath.name, "ext": ext, "text": txt, "meta": meta}
        if ext == ".pdf":
            out["pages_b64"] = render_pdf_previews(raw)
        elif ext == ".docx":
            out["doc_html"] = render_docx_html(raw)
        return out

    @api.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        raw = await file.read()
        if len(raw) > 8_000_000:
            raise HTTPException(400, "Maksymalny rozmiar pliku to 8 MB")
        fname = Path(file.filename or "plik.txt").name
        txt, meta = extract_bytes(fname, raw)
        doc_id = uuid.uuid4().hex[:12]
        ext = Path(fname).suffix.lower()
        uploads[doc_id] = {"filename": fname, "ext": ext, "bytes": raw}
        out = {"doc_id": doc_id, "filename": fname, "ext": ext, "text": txt, "meta": meta}
        if ext == ".pdf":
            out["pages_b64"] = render_pdf_previews(raw)
        elif ext == ".docx":
            out["doc_html"] = render_docx_html(raw)
        elif ext in (".png", ".jpg", ".jpeg"):
            out["pages_b64"] = [base64.b64encode(raw).decode("ascii")]
        return out

    @api.post("/api/anonymize")
    def anonymize(req: AnonReq):
        rep = pl.run_pipeline(
            req.text,
            mode=req.mode,
            use_slm=req.use_slm,
            mask_style=req.mask_style,
            custom_text=req.custom_text,
            enabled_kinds=req.enabled_kinds,
            custom_mask=req.custom_mask,
            custom_keep=req.custom_keep,
            kind_replacements=req.kind_replacements,
        )
        res_id = uuid.uuid4().hex[:12]
        out_pages_b64 = None
        out_doc_html = None
        out_filename = "zanonimizowany.txt"
        doc_redactions = 0

        up = uploads.get(req.doc_id) if req.doc_id else None
        if up and up["ext"] == ".pdf":
            pdf_out, out_pages_b64, doc_redactions = redact_pdf_bytes(up["bytes"], rep.redactions, mode=req.mode)
            out_filename = f"{Path(up['filename']).stem}_RODO.pdf"
            results[res_id] = {"bytes": pdf_out, "filename": out_filename, "mime": "application/pdf"}
        elif up and up["ext"] == ".docx":
            docx_out, out_doc_html, doc_redactions = redact_docx_bytes(up["bytes"], rep.redactions)
            out_filename = f"{Path(up['filename']).stem}_RODO.docx"
            results[res_id] = {
                "bytes": docx_out,
                "filename": out_filename,
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        else:
            results[res_id] = {"bytes": rep.masked_text.encode("utf-8"), "filename": out_filename, "mime": "text/plain"}

        return {
            "masked_text": rep.masked_text,
            "highlighted_html": rep.highlighted_html,
            "counts": rep.counts,
            "canon_counts": rep.canon_counts,
            "redactions": [asdict(r) for r in rep.redactions],
            "kept": [asdict(k) for k in rep.kept],
            "vault": rep.vault,
            "doc_sha256": rep.doc_sha256,
            "masked_sha256": rep.masked_sha256,
            "slm_latency_ms": rep.slm_latency_ms,
            "out_pages_b64": out_pages_b64,
            "out_doc_html": out_doc_html,
            "doc_redactions": doc_redactions,
            "download_url": f"/api/download/{res_id}",
            "download_name": out_filename,
        }

    @api.post("/api/restore")
    def restore(req: RestoreReq):
        return {"restored_text": pl.restore_text(req.masked_text, req.vault)}

    @api.get("/api/download/{rid}")
    def download(rid: str):
        item = results.get(rid)
        if not item:
            raise HTTPException(404, "Brak pliku do pobrania")
        return Response(
            content=item["bytes"],
            media_type=item["mime"],
            headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'},
        )

    return api
