"""Lokalny serwer HTTP dla Linda Kustosz RODO (z obsługą ustawień i auto-pobierania)."""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
import webbrowser
from dataclasses import asdict
from email.parser import BytesParser
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from kustosz.doc_redact import redact_docx_bytes, redact_pdf_bytes, render_docx_html, render_pdf_previews
from kustosz.extract import extract_bytes
from kustosz.pipeline import restore_text, run_pipeline

HERE = Path(__file__).resolve().parent
UI_PATH = HERE / "ui" / "index.html"
SAMPLES_DIR = HERE / "samples"
DATA_DIR = Path(os.environ.get("KUSTOSZ_DATA", Path(os.environ.get("LOCALAPPDATA", Path.home())) / "KustoszRODO"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CFG_PATH = DATA_DIR / "config.json"

GEMMA_FILE = "gemma-4-E4B-it-Q6_K.gguf"
BIELIK_FILES = ("Bielik-4.5B-v3.0-Instruct.Q6_K.fix.gguf", "Bielik-4.5B-v3.0-Instruct.Q6_K.gguf")


def load_cfg() -> dict:
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8-sig")) if CFG_PATH.is_file() else {}
    except (OSError, ValueError):
        return {}


def save_cfg(cfg: dict) -> None:
    tmp = CFG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CFG_PATH)


def _find_llama() -> Path:
    cfg = load_cfg()
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    candidates = [
        os.environ.get("KUSTOSZ_LLAMA", ""),
        cfg.get("llama_bin", ""),
        str(HERE / "bin" / exe),
        str(DATA_DIR / "bin" / exe),
        str(Path.home() / "Desktop" / "LocalDocs" / "runtime" / "llama" / exe),
        shutil.which(exe) or "",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return HERE / "bin" / exe


def _find_gguf(model_choice: str) -> Path:
    cfg = load_cfg()
    if os.environ.get("KUSTOSZ_GGUF"):
        return Path(os.environ["KUSTOSZ_GGUF"])
    search_dirs = [
        Path(cfg["models_dir"]) if cfg.get("models_dir") else None,
        HERE / "models",
        DATA_DIR / "models",
        Path.home() / "Desktop" / "LocalDocs" / "models" / "sejf",
    ]
    names = BIELIK_FILES if model_choice == "bielik" else (GEMMA_FILE,)
    for d in search_dirs:
        if d and d.is_dir():
            for name in names:
                p = d / name
                if p.is_file():
                    return p
    return HERE / "models" / names[0]


def current_settings() -> dict:
    cfg = load_cfg()
    model = os.environ.get("KUSTOSZ_MODEL", cfg.get("model", "gemma")).lower()
    gpu = "cpu" if os.environ.get("KUSTOSZ_CPU") == "1" else cfg.get("gpu", "auto")
    threads = int(os.environ.get("KUSTOSZ_THREADS", cfg.get("threads", max(4, (os.cpu_count() or 8) // 2))))
    port = int(os.environ.get("KUSTOSZ_PORT", cfg.get("port", 8791)))
    default_rules = {
        "mask_style": "label",
        "custom_text": "",
        "enabled_kinds": ["PESEL", "NIP", "REGON", "IBAN", "DOWOD", "EMAIL", "TELEFON", "OSOBA", "ADRES", "WRAZLIWE"],
        "kind_replacements": {},
        "custom_mask": [],
        "custom_keep": [],
    }
    rules = {**default_rules, **(cfg.get("rules") or {})}
    return {
        "model": model if model in ("gemma", "bielik") else "gemma",
        "gpu": gpu if gpu in ("auto", "cpu") else "auto",
        "threads": threads,
        "port": port,
        "llama_bin": str(_find_llama()),
        "gguf_path": str(_find_gguf(model)),
        "rules": rules,
    }


HOST = "127.0.0.1"
LLAMA_PORT = int(os.environ.get("KUSTOSZ_LLAMA_PORT", "8792"))
LLAMA_URL = f"http://{HOST}:{LLAMA_PORT}"

_LLAMA_PROC: subprocess.Popen | None = None
_DEVICE_LABEL = "CPU"
_ACTIVE_MODEL = GEMMA_FILE
_UPLOADS: dict[str, dict] = {}
_RESULTS: dict[str, dict] = {}


def _detect_gpu(llama_bin: Path, gpu_pref: str) -> str | None:
    if gpu_pref == "cpu":
        return None
    try:
        out = subprocess.run(
            [str(llama_bin), "--list-devices"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for line in (out.stdout + out.stderr).splitlines():
            line = line.strip()
            if line.split(":")[0].startswith(("Vulkan", "CUDA", "ROCm", "Metal")) and ":" in line:
                return line.split(":", 1)[0].strip()
    except Exception:
        pass
    return None


def start_llama() -> None:
    global _LLAMA_PROC, _DEVICE_LABEL, _ACTIVE_MODEL
    if _LLAMA_PROC and _LLAMA_PROC.poll() is None:
        return
    st = current_settings()
    llama_bin = Path(st["llama_bin"])
    gguf_path = Path(st["gguf_path"])
    _ACTIVE_MODEL = gguf_path.name

    try:
        urllib.request.urlopen(f"{LLAMA_URL}/health", timeout=1)
        _DEVICE_LABEL = "zewnętrzny serwer"
        return
    except Exception:
        pass

    if not llama_bin.exists() or not gguf_path.exists():
        print("[Kustosz RODO] Brak llama-server lub modelu GGUF — uruchamiam instalator...")
        from tools.setup_kustosz import ensure_llama_windows, ensure_models, write_default_config
        ensure_llama_windows(HERE / "bin")
        ensure_models(HERE / "models", with_bielik=(st["model"] == "bielik"))
        write_default_config(HERE / "models", HERE / "bin")
        st = current_settings()
        llama_bin = Path(st["llama_bin"])
        gguf_path = Path(st["gguf_path"])
        _ACTIVE_MODEL = gguf_path.name

    threads = str(st["threads"])
    dev = _detect_gpu(llama_bin, st["gpu"])
    accel = ["-ngl", "999", "--device", dev, "-fa", "off"] if dev else ["-ngl", "0"]
    _DEVICE_LABEL = dev or f"CPU ({threads} wątki)"

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    log_path = DATA_DIR / "llama_kustosz.log"
    _LLAMA_PROC = subprocess.Popen(
        [
            str(llama_bin), "-m", str(gguf_path),
            "--host", HOST, "--port", str(LLAMA_PORT),
            "-c", "4096", "-t", threads, "-tb", threads,
            "--temp", "0", "-np", "1", "--jinja", "--no-webui", *accel,
        ],
        stdout=open(log_path, "ab"), stderr=subprocess.STDOUT, creationflags=flags,
    )
    for _ in range(180):
        try:
            urllib.request.urlopen(f"{LLAMA_URL}/health", timeout=2)
            return
        except Exception:
            if _LLAMA_PROC.poll() is not None:
                raise RuntimeError(f"llama-server zakończył działanie — sprawdź {log_path}")
            time.sleep(1)
    raise RuntimeError("Timeout uruchomienia modelu SLM")


def stop_llama() -> None:
    global _LLAMA_PROC
    if _LLAMA_PROC and _LLAMA_PROC.poll() is None:
        _LLAMA_PROC.terminate()
        _LLAMA_PROC = None


atexit.register(stop_llama)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html_bytes = UI_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path == "/api/status":
            self._send_json(200, {
                "ok": True,
                "model": _ACTIVE_MODEL,
                "device": _DEVICE_LABEL,
                "llama_url": LLAMA_URL,
                "settings": current_settings(),
            })
            return
        if self.path == "/api/settings":
            self._send_json(200, current_settings())
            return
        if self.path.startswith("/api/sample/"):
            fname = Path(self.path.split("/api/sample/", 1)[1]).name
            fpath = SAMPLES_DIR / fname
            if not fpath.is_file():
                self._send_json(404, {"error": f"Brak przykładu: {fname}"})
                return
            raw = fpath.read_bytes()
            txt, meta = extract_bytes(fname, raw)
            doc_id = uuid.uuid4().hex[:12]
            ext = fpath.suffix.lower()
            _UPLOADS[doc_id] = {"filename": fname, "ext": ext, "bytes": raw}
            resp_obj = {"doc_id": doc_id, "filename": fname, "ext": ext, "text": txt, "meta": meta}
            if ext == ".pdf":
                resp_obj["pages_b64"] = render_pdf_previews(raw)
            elif ext == ".docx":
                resp_obj["doc_html"] = render_docx_html(raw)
            self._send_json(200, resp_obj)
            return
        if self.path.startswith("/api/download/"):
            rid = self.path.split("/api/download/", 1)[1]
            item = _RESULTS.get(rid)
            if not item:
                self._send_json(404, {"error": "Brak pliku do pobrania"})
                return
            body = item["bytes"]
            self.send_response(200)
            self.send_header("Content-Type", item["mime"])
            self.send_header("Content-Disposition", f'attachment; filename="{item["filename"]}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if self.path == "/api/upload":
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                self._send_json(400, {"error": "Wymagany multipart/form-data"})
                return
            raw_body = self.rfile.read(length)
            msg = BytesParser(policy=email_default).parsebytes(
                f"Content-Type: {ctype}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii") + raw_body
            )
            file_part = next((p for p in msg.iter_parts() if p.get_filename()), None)
            if file_part is None:
                self._send_json(400, {"error": "Brak pliku"})
                return
            raw = file_part.get_payload(decode=True) or b""
            fname = Path(file_part.get_filename() or "plik.txt").name
            txt, meta = extract_bytes(fname, raw)
            doc_id = uuid.uuid4().hex[:12]
            ext = Path(fname).suffix.lower()
            _UPLOADS[doc_id] = {"filename": fname, "ext": ext, "bytes": raw}

            resp_obj = {"doc_id": doc_id, "filename": fname, "ext": ext, "text": txt, "meta": meta}
            if ext == ".pdf":
                resp_obj["pages_b64"] = render_pdf_previews(raw)
            elif ext == ".docx":
                resp_obj["doc_html"] = render_docx_html(raw)
            elif ext in (".png", ".jpg", ".jpeg"):
                import base64
                resp_obj["pages_b64"] = [base64.b64encode(raw).decode("ascii")]
            self._send_json(200, resp_obj)
            return

        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path == "/api/settings":
            cfg = load_cfg()
            engine_changed = False
            if data.get("model") in ("gemma", "bielik") and data["model"] != cfg.get("model"):
                cfg["model"] = data["model"]
                engine_changed = True
            if data.get("gpu") in ("auto", "cpu") and data["gpu"] != cfg.get("gpu"):
                cfg["gpu"] = data["gpu"]
                engine_changed = True
            if isinstance(data.get("threads"), int) and 1 <= data["threads"] <= 64 and data["threads"] != cfg.get("threads"):
                cfg["threads"] = data["threads"]
                engine_changed = True
            if isinstance(data.get("rules"), dict):
                cfg["rules"] = data["rules"]
            save_cfg(cfg)
            if engine_changed:
                stop_llama()
                start_llama()
            self._send_json(200, {"ok": True, "model": _ACTIVE_MODEL, "device": _DEVICE_LABEL, "settings": current_settings()})
            return

        if self.path == "/api/anonymize":
            rules = current_settings()["rules"]
            text = data.get("text", "")
            mode = data.get("mode", "irreversible")
            use_slm = bool(data.get("use_slm", True))
            doc_id = data.get("doc_id")
            rep = run_pipeline(
                text,
                mode=mode,
                use_slm=use_slm,
                llama_url=LLAMA_URL,
                mask_style=data.get("mask_style", rules["mask_style"]),
                custom_text=data.get("custom_text", rules["custom_text"]),
                enabled_kinds=data.get("enabled_kinds", rules["enabled_kinds"]),
                custom_mask=data.get("custom_mask", rules["custom_mask"]),
                custom_keep=data.get("custom_keep", rules["custom_keep"]),
                kind_replacements=data.get("kind_replacements", rules["kind_replacements"]),
            )

            res_id = uuid.uuid4().hex[:12]
            out_pages_b64 = None
            out_doc_html = None
            out_filename = "zanonimizowany.txt"
            doc_redactions = 0

            up = _UPLOADS.get(doc_id) if doc_id else None
            if up and up["ext"] == ".pdf":
                pdf_out, out_pages_b64, doc_redactions = redact_pdf_bytes(up["bytes"], rep.redactions, mode=mode)
                stem = Path(up["filename"]).stem
                out_filename = f"{stem}_RODO.pdf"
                _RESULTS[res_id] = {"bytes": pdf_out, "filename": out_filename, "mime": "application/pdf"}
            elif up and up["ext"] == ".docx":
                docx_out, out_doc_html, doc_redactions = redact_docx_bytes(up["bytes"], rep.redactions)
                stem = Path(up["filename"]).stem
                out_filename = f"{stem}_RODO.docx"
                _RESULTS[res_id] = {
                    "bytes": docx_out,
                    "filename": out_filename,
                    "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }
            else:
                _RESULTS[res_id] = {
                    "bytes": rep.masked_text.encode("utf-8"),
                    "filename": out_filename,
                    "mime": "text/plain; charset=utf-8",
                }

            self._send_json(200, {
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
            })
            return

        if self.path == "/api/restore":
            restored = restore_text(data.get("masked_text", ""), data.get("vault", {}))
            self._send_json(200, {"restored_text": restored})
            return

        self._send_json(404, {"error": "Not found"})


def main():
    st = current_settings()
    port = st["port"]
    print(f"[Kustosz RODO] Uruchamiam {_find_gguf(st['model']).name}...")
    start_llama()
    url = f"http://{HOST}:{port}/"
    print(f"[Kustosz RODO] Gotowe ({_DEVICE_LABEL}): {url}")
    if os.environ.get("KUSTOSZ_NO_BROWSER") != "1":
        webbrowser.open(url)
    srv = ThreadingHTTPServer((HOST, port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_llama()


if __name__ == "__main__":
    main()
