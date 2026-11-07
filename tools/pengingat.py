#!/usr/bin/env python3
"""
Pengingat & Penjaga Sistem Latar Belakang (Mesin Background Daemon)
Memantau suhu termal HP, status baterai, laporan cuaca/AQI pagi hari,
serta menjalankan pembersihan sampah berkala secara otonom.
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime

MESIN_DIR = os.path.expanduser("~/mesin")
PID_FILE = os.path.join(MESIN_DIR, "logs", "pengingat.pid")
LOG_FILE = os.path.join(MESIN_DIR, "logs", "pengingat.log")

def _log(pesan):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baris = f"[{stamp}] {pesan}\n"
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(baris)

def bersuara(teks):
    """Kirim notifikasi Android dan ucapkan via TTS."""
    try:
        # 1. Notifikasi Termux
        subprocess.run([
            "termux-notification",
            "--title", "Mesin AI Penjaga",
            "--content", teks,
            "--id", "mesin_daemon"
        ], capture_output=True, timeout=5)
    except Exception:
        pass

    try:
        # 2. Ucapkan suara
        subprocess.run(["termux-tts-speak", "-l", "id", teks], capture_output=True, timeout=15)
    except Exception:
        pass

def loop_daemon():
    """Loop utama daemon pengingat latar belakang."""
    _log("🟢 Daemon Pengingat dimulai.")
    
    terakhir_suhu_alert = 0
    terakhir_baterai_alert = 0
    terakhir_pagi_hari = ""
    terakhir_auto_fix = 0

    while True:
        now = datetime.now()
        now_ts = time.time()
        hari_ini_str = now.strftime("%Y-%m-%d")

        # ── 1. PEMANTAUAN SUHU & BATERAI ──
        try:
            res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                d = json.loads(res.stdout.strip())
                temp = float(d.get("temperature", 0.0))
                pct = int(d.get("percentage", 100))
                status_daya = d.get("status", "DISCHARGING")

                # Peringatan Suhu Panas (> 43°C)
                if temp > 43.0 and (now_ts - terakhir_suhu_alert > 900):
                    pesan = f"Peringatan: Suhu baterai mencapai {temp:.1f} derajat celcius. Istirahatkan HP sejenak dari komputasi berat."
                    _log(f"⚠️ {pesan}")
                    bersuara(pesan)
                    terakhir_suhu_alert = now_ts

                # Peringatan Baterai Lemah (<= 15% saat tidak di-charge)
                if pct <= 15 and status_daya != "CHARGING" and (now_ts - terakhir_baterai_alert > 1200):
                    pesan = f"Baterai tersisa {pct} persen. Harap segera hubungkan pengisi daya."
                    _log(f"🔋 {pesan}")
                    bersuara(pesan)
                    terakhir_baterai_alert = now_ts
        except Exception as e:
            _log(f"Error cek baterai: {e}")

        # ── 2. PENGINGAT PAGI (BRIEFING AQI JAM 06:00 - 07:30) ──
        if 6 <= now.hour <= 7 and terakhir_pagi_hari != hari_ini_str:
            try:
                from tools.aqi_checker import cek_aqi_lokal
                data_aqi = cek_aqi_lokal()
                if data_aqi and str(data_aqi.get("aqi", "?")) != "?":
                    aqi = data_aqi.get("aqi")
                    kat = data_aqi.get("kategori", "")
                    saran = data_aqi.get("saran", "")
                    pesan = f"Selamat pagi! Kualitas udara saat ini bernilai {aqi}, kategori {kat}. {saran}"
                    _log(f"🌅 {pesan}")
                    bersuara(pesan)
                    terakhir_pagi_hari = hari_ini_str
            except Exception as e:
                _log(f"Error briefing pagi: {e}")

        # ── 3. PEMELIHARAAN SAMPAH OTOMATIS (TIAP 6 JAM) ──
        if now_ts - terakhir_auto_fix > 21600:
            try:
                from tools.dokter import diagnosa_sistem
                hasil = diagnosa_sistem(auto_fix=True)
                if hasil.get("tindakan"):
                    _log(f"🧹 Auto-Fix berkala: {', '.join(hasil['tindakan'])}")
                terakhir_auto_fix = now_ts
            except Exception as e:
                _log(f"Error auto-fix rutin: {e}")

        time.sleep(60)

def start():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"🟢 Daemon sudah berjalan dengan PID {pid}")
            return
        except (ValueError, OSError):
            pass

    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    # Jalankan background proses
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "run"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    print(f"✅ Daemon Pengingat Mesin berhasil dimulai (PID: {proc.pid})")

def stop():
    if not os.path.exists(PID_FILE):
        print("⚪ Daemon tidak sedang berjalan.")
        return
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 9)
        os.remove(PID_FILE)
        print(f"🛑 Daemon (PID {pid}) berhasil dihentikan.")
    except Exception as e:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print(f"⚪ Daemon telah dihentikan: {e}")

def status():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"🟢 Daemon Pengingat AKTIF (PID {pid})")
            return
        except Exception:
            pass
    print("⚪ Daemon Pengingat TIDAK AKTIF")

if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "status"
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "run":
        loop_daemon()
    else:
        print("Usage: python3 pengingat.py {start|stop|status}")
