"""Publiczne demo Linda Kustosz RODO na Modal (T4 GPU + Gemma-4-E4B / Bielik-4.5B)."""

import base64
import uuid
from dataclasses import asdict
from pathlib import Path

import modal

app = modal.App("kustosz-rodo-demo")
vol = modal.Volume.from_name("kustosz-rodo-models", create_if_missing=True)

MODEL_REPO = "unsloth/gemma-4-E4B-it-GGUF"
MODEL_FILE = "gemma-4-E4B-it-Q6_K.gguf"
MODEL_DIR = Path("/models")

image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-runtime-ubuntu22.04", add_python="3.12")
    .pip_install(
        "fastapi[standard]",
        "python-multipart",
        "pymupdf",
        "python-docx",
        "huggingface_hub",
    )
    .pip_install(
        "llama-cpp-python",
        extra_index_url="https://abetlen.github.io/llama-cpp-python/whl/cu124",
    )
    .add_local_dir("kustosz", "/root/kustosz", ignore=["__pycache__", "*.pyc"])
    .add_local_dir("ui", "/root/ui")
    .add_local_dir("samples", "/root/samples")
    .add_local_file("Kustosz_RODO_Prezentacja.pdf", "/root/Kustosz_RODO_Prezentacja.pdf")
)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": vol},
    scaledown_window=300,
    timeout=300,
)
@modal.concurrent(max_inputs=8)
class KustoszService:
    @modal.enter()
    def load(self):
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        gguf_path = MODEL_DIR / MODEL_FILE
        if not gguf_path.exists():
            hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                local_dir=str(MODEL_DIR),
            )
            vol.commit()

        self.llm = Llama(
            model_path=str(gguf_path),
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
        self.uploads: dict[str, dict] = {}
        self.results: dict[str, dict] = {}

    def _classify_fn(self, text: str, llama_url: str = "") -> "SlmResult":
        import time
        from kustosz.slm_ner import SYSTEM_PROMPT, SlmResult, _parse_slm_output

        t0 = time.perf_counter()
        resp = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Tekst:\n{text}\nWynik:"},
            ],
            temperature=0.0,
            max_tokens=550,
        )
        content = resp["choices"][0]["message"]["content"]
        redacts, keeps = _parse_slm_output(content)
        ms = int((time.perf_counter() - t0) * 1000)
        return SlmResult(redact=redacts, keep=keeps, raw_json=content, latency_ms=ms)

    @modal.asgi_app()
    def web(self):
        import sys
        sys.path.insert(0, "/root")
        from kustosz.web_modal import build_app
        return build_app(self._classify_fn, MODEL_FILE)
