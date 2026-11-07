#!/usr/bin/env python3
"""TTS tools: Text-to-Speech via Termux TTS."""
import os
import subprocess

TERMUX_PREFIX = "/data/data/com.termux/files/usr"

def tts_speak(text, engine=None, pitch=1.0, rate=1.0):
    """Ucapkan teks menggunakan Termux TTS."""
    cmd = [f"{TERMUX_PREFIX}/bin/termux-tts-speak"]
    if engine:
        cmd.extend(["-e", engine])
    cmd.extend(["-p", str(pitch), "-r", str(rate)])
    cmd.append(text)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            env={**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX}
        )
        if result.returncode == 0:
            return f"[TTS] Berhasil ucapkan: {text[:50]}..."
        return f"[Error TTS] {result.stderr.strip()}"
    except Exception as e:
        return f"[Error TTS] {str(e)}"

def tts_engines():
    """List semua TTS engine yang tersedia."""
    try:
        result = subprocess.run(
            [f"{TERMUX_PREFIX}/bin/termux-tts-engines"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX}
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"[Error] {str(e)}"

HANDS = {
    "tts_speak": tts_speak,
    "tts_engines": tts_engines,
}
