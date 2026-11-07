#!/usr/bin/env python3
"""STT tools: Speech-to-Text via Termux STT."""
import os
import subprocess

TERMUX_PREFIX = "/data/data/com.termux/files/usr"

def stt_listen(language="id-ID", timeout=10):
    """Rekam suara dan konversi ke teks."""
    cmd = [
        f"{TERMUX_PREFIX}/bin/termux-speech-to-text"
    ]
    env = {**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX, "LANG": language}
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 2,
            env=env
        )
        if result.returncode == 0:
            return result.stdout.strip() or "[STT] Tidak ada teks terdeteksi."
        return f"[Error STT] {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "[Error STT] Timeout: tidak ada suara terdeteksi dalam batas waktu."
    except Exception as e:
        return f"[Error STT] {str(e)}"

def stt_languages():
    """List bahasa yang tersedia untuk STT."""
    try:
        result = subprocess.run(
            [f"{TERMUX_PREFIX}/bin/termux-speech-to-text", "--languages"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX}
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"[Error] {str(e)}"

HANDS = {
    "stt_listen": stt_listen,
    "stt_languages": stt_languages,
}
