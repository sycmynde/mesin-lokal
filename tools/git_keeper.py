#!/usr/bin/env python3
"""
Git Keeper - Jaring Pengaman Otomatis (Auto-Snapshot & Safe Rollback)
Menjaga kode Mesin AI agar bisa di-snapshot kapan saja dan dipulihkan dalam 1 detik
jika terjadi eksperimen atau kesalahan kode.
"""

import os
import sys
import subprocess
from datetime import datetime

MESIN_DIR = os.path.expanduser("~/mesin")

def _run_git(args):
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=MESIN_DIR,
            capture_output=True,
            text=True,
            timeout=15
        )
        return res.returncode == 0, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def buat_snapshot(pesan="auto-snapshot"):
    """Membuat snapshot commit otomatis jika ada perubahan kode."""
    ok, status, _ = _run_git(["status", "--porcelain"])
    if not ok:
        return False, "Gagal membaca status git."
    
    if not status:
        return True, "Tidak ada perubahan berkas untuk disimpan."

    # Tambahkan file yang aman di-track (hindari commit video/audio besar)
    _run_git(["add", "tools/", "core/", "brains/", "plugins/", "providers/", "main.py", "config.yaml", "cermin.txt"])
    
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"🛡️ Snapshot [{stamp}] - {pesan}"
    
    ok, out, err = _run_git(["commit", "-m", commit_msg])
    if ok:
        # Ambil commit ID pendek
        _, cid, _ = _run_git(["rev-parse", "--short", "HEAD"])
        return True, f"Snapshot tersimpan ({cid}): {pesan}"
    else:
        return False, f"Gagal membuat snapshot: {err or out}"

def daftar_snapshot(limit=5):
    """Menampilkan daftar snapshot terakhir."""
    ok, out, err = _run_git(["log", f"-n{limit}", "--oneline", "--decorate"])
    if ok:
        return out
    return f"Gagal membaca riwayat: {err}"

def kembalikan_snapshot():
    """Membatalkan perubahan yang belum di-commit dan mengembalikan ke snapshot terakhir."""
    ok, out, err = _run_git(["checkout", "--", "tools/", "core/", "brains/", "main.py"])
    if ok:
        return True, "Berhasil memulihkan berkas kode ke snapshot terakhir."
    return False, f"Gagal rollback: {err}"

if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "snapshot"
    
    if cmd == "snapshot":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "manual check"
        ok, res = buat_snapshot(msg)
        print(("✅ " if ok else "❌ ") + res)
    elif cmd in ("list", "daftar"):
        print(daftar_snapshot())
    elif cmd in ("rollback", "pulihkan"):
        ok, res = kembalikan_snapshot()
        print(("✅ " if ok else "❌ ") + res)
    else:
        print("Usage: python3 git_keeper.py [snapshot|list|rollback] [pesan]")
