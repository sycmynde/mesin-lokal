"""
nav_brain.py — Otak Navigasi Offline
Nggak ngitung sendiri. Semua matematika di nav.sh.
Brain ini cuma: tangkap niat -> panggil bash -> kembalikan jawaban.
AI tidak pernah ngitung. Mesin yang ngitung.
"""

import subprocess
import os
import re

NAV_SH = os.path.expanduser("~/mesin/nav.sh")
NAV_DIR = os.path.expanduser("~/mesin/nav")
ORIGIN_FILE = os.path.join(NAV_DIR, ".origin")
TUJUAN_FILE = os.path.join(NAV_DIR, ".tujuan")
LASTFIX_FILE = os.path.join(NAV_DIR, ".lastfix")

from tools.kalkulator import (
    hitung_jarak_gps, hitung_bearing, fmt_jarak, get_current_location
)

NAV_PATTERNS = [
    (r'^gps$|nyalain\s+gps|nyalakan\s+gps|gps\s+on|gps\s+nyala', 'gps', []),
    (r'^jangkar$|pasang\s+jangkar|^titik\s+awal$|set\s+jangkar', 'jangkar', []),
    (r'^tujuan\s+(-?\d+\.?\d*)\s*,?\s+(-?\d+\.?\d*)\s*$', 'tujuan_manual', None),
    (r'^tujuan\s+(.+)$', 'tujuan', None),
    (r'^tujuan$|set\s+tujuan|tujuan\s+di\s+sini', 'tujuan', []),
    (r'di\s*mana|kita\s+di\s*mana|posisi\s+saya|dimana\s+saya|posisi\s+kita', 'dimana', []),
    (r'berapa\s+jarak.*tujuan|jarak.*dari\s+sini.*tujuan', 'jarak', ['tujuan']),
    (r'^jarak$|jarak\s+ke\s+titik\s+awal|jarak\s+dari\s+titik\s+awal|berapa\s+jauh\s+dari\s+awal', 'jarak', []),
    (r'berapa\s+jauh\s+lagi|jarak\s+tujuan|jarak\s+ke\s+tujuan|sisa\s+berapa', 'jarak', ['tujuan']),
    (r'status\s+nav|status\s+navigasi', 'status', []),
]


def can_handle(text):
    t = text.strip().lower()
    nav_kw = [
        "gps", "jangkar", "tujuan",
        "di mana", "dimana", "kita di mana",
        "posisi saya", "posisi aku",
        "jarak",
        "berapa jauh dari awal", "berapa jauh lagi",
        "status nav", "status navigasi",
        "sisa berapa",
    ]
    return any(k in t for k in nav_kw)


def _get_fix():
    loc = get_current_location()
    if not loc or loc.startswith("Gagal"):
        return None
    try:
        coord = loc.split("|")[0].strip()
        lat, lon = coord.split(",")
        return float(lat), float(lon)
    except Exception:
        return None


def _baca_titik(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            p = f.read().strip().split()
        return float(p[0]), float(p[1])
    except Exception:
        return None


class NavBrain:
    def run(self, data):
        text = data.get("text", "").strip().lower()

        for pattern, cmd, args in NAV_PATTERNS:
            m = re.search(pattern, text)
            if not m:
                continue

            # ── tujuan_manual: tulis langsung, bypass nav.sh ──
            if cmd == "tujuan_manual":
                lat, lon = m.group(1), m.group(2)
                os.makedirs(NAV_DIR, exist_ok=True)
                with open(TUJUAN_FILE, "w") as f:
                    f.write(f"{lat} {lon} manual\n")
                return f"🎯 Tujuan diset (manual): {lat}, {lon}"

            # ── jarak: hitung langsung via kalkulator ──
            if cmd == "jarak":
                target = args[0] if args else "origin"
                tfile = TUJUAN_FILE if target == "tujuan" else ORIGIN_FILE
                if not os.path.exists(tfile):
                    saran = "tujuan" if target == "tujuan" else "jangkar"
                    return f"⚠️ Belum diset. Ketik '{saran}' dulu."
                tlat, tlon = _baca_titik(tfile)
                fix = _get_fix()
                if fix is None:
                    return "⚠️ GPS belum fix. Ketik 'gps' dulu."
                flat, flon = fix
                km = hitung_jarak_gps(flat, flon, tlat, tlon)
                deg, arah = hitung_bearing(flat, flon, tlat, tlon)
                os.makedirs(NAV_DIR, exist_ok=True)
                with open(LASTFIX_FILE, "w") as f:
                    f.write(f"{flat} {flon}\n")
                label = "tujuan" if target == "tujuan" else "titik awal"
                return f"📏 Jarak ke {label}: {fmt_jarak(km)} ke {arah} ({deg}°)"

            full_cmd = ["bash", NAV_SH, cmd]

            if args is None and m.lastindex:
                for i in range(1, m.lastindex + 1):
                    full_cmd.append(m.group(i).strip())
            elif args:
                full_cmd.extend(args)

            try:
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = result.stdout.strip()
                if result.returncode != 0 and result.stderr.strip():
                    output += "\n" + result.stderr.strip()
                return output if output else "Nav diam. Cek nav.sh."

            except subprocess.TimeoutExpired:
                return "GPS timeout (120 dtk). Coba di tempat terbuka."
            except FileNotFoundError:
                return f"{NAV_SH} nggak ada. Cek path."
            except Exception as e:
                return f"Nav error: {e}"

        return "Perintah nav nggak dikenali."
