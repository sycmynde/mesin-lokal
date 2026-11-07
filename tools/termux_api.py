#!/usr/bin/env python3
"""Termux API tools: baterai, clipboard, kamera, kontak, log panggilan, dll."""
import os
import subprocess
import json

TERMUX_PREFIX = "/data/data/com.termux/files/usr"

def _run_termux(cmd, args=None):
    """Jalankan perintah termux-* dan return output."""
    args = args or []
    try:
        result = subprocess.run(
            [cmd] + [str(a) for a in args],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX}
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"[Error] {result.stderr.strip()}"
    except Exception as e:
        return f"[Error] {str(e)}"

def cek_baterai():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-battery-status")

def cek_brightness():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-brightness")

def set_brightness(level):
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-brightness", [level])

def clipboard_get():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-clipboard-get")

def clipboard_set(text):
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-clipboard-set", [text])

def daftar_kontak():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-contact-list")

def log_panggilan():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-call-log")

def info_aplikasi():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-apps-info")

def fingerprint():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-fingerprint")

def cek_warna_layar():
    return _run_termux(f"{TERMUX_PREFIX}/bin/termux-colors-list")

# Mapping untuk mesin_tangan.py
HANDS = {
    "baterai": cek_baterai,
    "clipboard_get": clipboard_get,
    "clipboard_set": clipboard_set,
    "kontak": daftar_kontak,
    "call_log": log_panggilan,
    "apps_info": info_aplikasi,
    "brightness": cek_brightness,
    "set_brightness": set_brightness,
    "fingerprint": fingerprint,
    "colors": cek_warna_layar,
}
