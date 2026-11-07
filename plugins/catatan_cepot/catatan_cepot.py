#!/usr/bin/env python3
"""Plugin contoh: catatan cepat lokal."""
import os
import json
from datetime import datetime

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(PLUGIN_DIR, "notes.json")

def _load_notes():
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_notes(notes):
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[Error] Gagal simpan catatan: {e}"
    return "[OK]"

def catat(teks):
    """Tambah catatan cepat."""
    if not teks or not teks.strip():
        return "[Error] Catatan kosong."
    notes = _load_notes()
    notes.append({
        "time": datetime.now().isoformat(),
        "text": teks.strip()
    })
    _save_notes(notes)
    return f"[OK] Catatan tersimpan ({len(notes)} total)"

def baca_catatan(limit=10):
    """Baca catatan terakhir."""
    notes = _load_notes()
    if not notes:
        return "Belum ada catatan."
    items = notes[-limit:]
    lines = [f"{i+1}. [{n.get('time','')}] {n.get('text','')}" for i, n in enumerate(items)]
    return "\n".join(lines)

def hapus_catatan(index=None):
    """Hapus catatan terakhir atau by index."""
    notes = _load_notes()
    if not notes:
        return "Tidak ada catatan untuk dihapus."
    if index is None:
        notes.pop()
        _save_notes(notes)
        return "[OK] Catatan terakhir dihapus."
    try:
        idx = int(index)
        if idx < 1 or idx > len(notes):
            return f"[Error] Index 1..{len(notes)}"
        notes.pop(idx - 1)
        _save_notes(notes)
        return f"[OK] Catatan #{idx} dihapus."
    except Exception as e:
        return f"[Error] {e}"

HANDS = {
    "catat": catat,
    "baca_catatan": baca_catatan,
    "hapus_catatan": hapus_catatan,
}
