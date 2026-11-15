"""Instalator Kustosz RODO: pobiera llama.cpp (Windows Vulkan/CPU) oraz model GGUF z weryfikacją SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GEMMA_REV = "bfc15c382204943c3a8fff0c750b94ae2364d7a3"
GEMMA_FILE = "gemma-4-E4B-it-Q6_K.gguf"
GEMMA_URL = f"https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/{GEMMA_REV}/{GEMMA_FILE}"
GEMMA_SHA = "fd83f3ef44d22e00ff0f638753dde9a66a83e8ccf79c11024f47d383c489531b"

BIELIK_FILE = "Bielik-4.5B-v3.0-Instruct.Q6_K.gguf"
BIELIK_URL = f"https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct-GGUF/resolve/main/{BIELIK_FILE}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_with_resume(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": "kustosz-rodo-installer/1.0"}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        if have and r.status != 206:
            have = 0
        total = have + int(r.headers.get("Content-Length", 0))
        with open(part, "ab" if have else "wb") as f:
            done, last = have, -1
            while True:
                buf = r.read(1 << 20)
                if not buf:
                    break
                f.write(buf)
                done += len(buf)
                pct = int(done * 100 / total) if total else 0
                if pct != last:
                    print(f"\r  {dst.name}: {pct}% ({done >> 20} / {total >> 20} MB)", end="", flush=True)
                    last = pct
    print()
    part.replace(dst)


def ensure_pip_deps() -> None:
    print("[1/3] Sprawdzam zależności Python...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)


def ensure_llama_windows(bin_dir: Path) -> None:
    if (bin_dir / "llama-server.exe").exists():
        print("[2/3] llama-server.exe już istnieje w", bin_dir)
        return
    if os.name != "nt":
        print("[2/3] System inny niż Windows — zainstaluj llama-server (llama.cpp) do PATH lub ./bin/llama-server")
        return

    print("[2/3] Pobieram llama.cpp (Windows Vulkan/CPU) z GitHub Releases...")
    req = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
        headers={"User-Agent": "kustosz-rodo-installer/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        rel = json.loads(r.read().decode("utf-8"))

    assets = rel.get("assets", [])
    # Preferuj Vulkan (działa na AMD, NVIDIA i Intel GPU) z fallbackiem na CPU x64
    chosen = None
    for pattern in ("win-vulkan-x64.zip", "win-cpu-x64.zip"):
        for a in assets:
            if a["name"].endswith(pattern):
                chosen = a
                break
        if chosen:
            break
    if not chosen:
        raise RuntimeError("Nie znaleziono paczki Windows w najnowszym wydaniu llama.cpp")

    zip_path = bin_dir / chosen["name"]
    download_with_resume(chosen["browser_download_url"], zip_path)
    print(f"  Rozpakowuję {chosen['name']}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            name = Path(member.filename).name
            if name.endswith((".exe", ".dll")) or name.startswith("LICENSE"):
                (bin_dir / name).write_bytes(zf.read(member))
    zip_path.unlink(missing_ok=True)
    print("  Gotowe:", bin_dir / "llama-server.exe")


def ensure_models(models_dir: Path, with_bielik: bool = False) -> None:
    print("[3/3] Sprawdzam model SLM...")
    gemma_dst = models_dir / GEMMA_FILE
    if gemma_dst.exists() and sha256(gemma_dst) == GEMMA_SHA:
        print("  OK:", gemma_dst)
    else:
        print(f"  Pobieram {GEMMA_FILE} (~6.7 GB, jednorazowo)...")
        download_with_resume(GEMMA_URL, gemma_dst)
        if sha256(gemma_dst) != GEMMA_SHA:
            gemma_dst.unlink(missing_ok=True)
            raise RuntimeError(f"Nieprawidłowa suma SHA-256 dla {GEMMA_FILE}")

    if with_bielik:
        bielik_dst = models_dir / BIELIK_FILE
        if not bielik_dst.exists():
            print(f"  Pobieram opcjonalny {BIELIK_FILE}...")
            download_with_resume(BIELIK_URL, bielik_dst)


def write_default_config(models_dir: Path, bin_dir: Path) -> None:
    cfg_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "KustoszRODO"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.json"
    if not cfg_path.exists():
        cfg = {
            "model": "gemma",
            "gpu": "auto",
            "threads": max(4, (os.cpu_count() or 8) // 2),
            "port": 8791,
            "models_dir": str(models_dir),
            "llama_bin": str(bin_dir / ("llama-server.exe" if os.name == "nt" else "llama-server")),
        }
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Zapisano konfigurację:", cfg_path)


def main():
    ap = argparse.ArgumentParser(description="Instalator Linda Kustosz RODO")
    ap.add_argument("--models-dir", type=Path, default=ROOT / "models")
    ap.add_argument("--bin-dir", type=Path, default=ROOT / "bin")
    ap.add_argument("--with-bielik", action="store_true", help="Pobierz dodatkowo Bielik-4.5B-v3 GGUF")
    ap.add_argument("--skip-deps", action="store_true")
    args = ap.parse_args()

    if not args.skip_deps:
        ensure_pip_deps()
    ensure_llama_windows(args.bin_dir)
    ensure_models(args.models_dir, with_bielik=args.with_bielik)
    write_default_config(args.models_dir, args.bin_dir)
    print("\nInstalacja zakończona! Uruchom program przez: python app.py (lub start.bat)")


if __name__ == "__main__":
    main()
