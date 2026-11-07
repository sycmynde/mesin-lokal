#!/usr/bin/env python3
"""
Dokter Mesin - Agen Diagnostik & Pemulihan Mandiri (Self-Healing & Auto-Repair)
Memeriksa kesehatan sistem, database, layanan latar belakang, memori, dan kode.
Bisa dipanggil standalone via CLI atau melalui perintah /dokter di main.py.
"""

import os
import sys
import glob
import time
import json
import socket
import shutil
import sqlite3
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()
MESIN_DIR = os.path.expanduser("~/mesin")

def cek_ram():
    """Membaca penggunaan RAM langsung dari /proc/meminfo."""
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = parts[1].strip()

        total_kb = int(meminfo.get("MemTotal", "0").split()[0])
        avail_kb = int(meminfo.get("MemAvailable", "0").split()[0])
        used_kb = total_kb - avail_kb
        used_pct = (used_kb / total_kb * 100) if total_kb > 0 else 0

        return {
            "total_mb": total_kb // 1024,
            "avail_mb": avail_kb // 1024,
            "used_mb": used_kb // 1024,
            "used_pct": used_pct,
            "status": "OK" if used_pct < 85 else "PERINGATAN (RAM hampir penuh)"
        }
    except Exception as e:
        return {"status": f"Gagal membaca RAM: {e}"}

def cek_storage():
    """Membaca sisa penyimpanan internal pengguna."""
    try:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        total_gb = usage.total / (1024**3)
        free_gb = usage.free / (1024**3)
        used_pct = (usage.used / usage.total) * 100

        return {
            "total_gb": round(total_gb, 1),
            "free_gb": round(free_gb, 1),
            "used_pct": round(used_pct, 1),
            "status": "OK" if free_gb > 2.0 else "KRITIS (Sisa storage < 2GB)"
        }
    except Exception as e:
        return {"status": f"Gagal membaca disk: {e}"}

def cek_baterai():
    """Membaca status baterai dan suhu via Termux API."""
    try:
        res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            d = json.loads(res.stdout.strip())
            pct = d.get("percentage", "?")
            temp = d.get("temperature", 0.0)
            status = d.get("status", "Unknown")
            
            suhu_str = f"{temp:.1f}°C" if isinstance(temp, (int, float)) else str(temp)
            kondisi = "OK"
            if isinstance(temp, (int, float)) and temp > 43.0:
                kondisi = "PANAS (Suhu tinggi, istirahatkan komputasi)"

            return {
                "persen": pct,
                "suhu": suhu_str,
                "status_daya": status,
                "kondisi": kondisi
            }
    except Exception:
        pass
    return None

def cek_port(host, port, timeout=1):
    """Cek apakah port socket merespon."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False

def cek_database_integrity(db_path):
    """Memeriksa integritas berkas SQLite dengan PRAGMA integrity_check."""
    if not os.path.exists(db_path):
        return "TIDAK ADA"
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == "ok":
            return "SEHAT"
        return f"RUSAK: {res}"
    except sqlite3.OperationalError as e:
        return f"TERKUNCI / SIBUK ({e})"
    except Exception as e:
        return f"ERROR ({e})"

def cek_sintaks_kode():
    """Memvalidasi kompilasi sintaks semua berkas Python utama."""
    broken = []
    folders = ["tools", "brains", "core", "providers"]
    for folder in folders:
        fpath = os.path.join(MESIN_DIR, folder)
        if not os.path.exists(fpath):
            continue
        for py_file in glob.glob(os.path.join(fpath, "*.py")):
            try:
                import py_compile
                py_compile.compile(py_file, doraise=True)
            except Exception as e:
                broken.append((os.path.basename(py_file), str(e)))
    return broken

def diagnosa_sistem(auto_fix=False):
    """
    Menjalankan pemeriksaan komprehensif sistem Mesin AI.
    Jika auto_fix=True, otomatis memulihkan masalah yang aman diperbaiki.
    """
    masalah = []
    tindakan = []

    # 1. RAM & Storage & Baterai
    ram = cek_ram()
    storage = cek_storage()
    baterai = cek_baterai()

    if isinstance(ram.get("used_pct"), (int, float)) and ram["used_pct"] > 88:
        masalah.append(f"RAM sangat padat ({ram['used_pct']:.1f}% terpakai)")

    if isinstance(storage.get("free_gb"), (int, float)) and storage["free_gb"] < 1.5:
        masalah.append(f"Sisa penyimpanan rendah ({storage['free_gb']} GB tersisa)")

    # 2. Servis & Komponen
    local_llm = cek_port("localhost", 8080)
    vision_llm = cek_port("localhost", 8082)

    # Cek cmus
    cmus_ok = False
    try:
        from tools.dj_cmus import cmus_remote
        cmus_ok = cmus_remote(["-Q"])
    except Exception:
        pass

    # Cek Whisper
    whisper_bin = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
    whisper_ok = os.path.exists(whisper_bin)

    # 3. Database Integrity
    dbs = {
        "memory.db": os.path.join(MESIN_DIR, "data", "memory.db"),
        "chat_history.db": os.path.join(MESIN_DIR, "data", "chat_history.db"),
        "pribadi.db": os.path.join(MESIN_DIR, "data", "pribadi.db")
    }
    db_status = {}
    for name, path in dbs.items():
        st = cek_database_integrity(path)
        db_status[name] = st
        if "RUSAK" in st or "TERKUNCI" in st:
            masalah.append(f"Database {name} {st}")

    # 4. Cek Sintaks Kode Python
    broken_code = cek_sintaks_kode()
    if broken_code:
        for fname, err in broken_code:
            masalah.append(f"Sintaks kode rusak pada {fname}")

    # 5. Cek Berkas Sampah (Orphan audio, video ppm, dead pid)
    audio_dir = os.path.join(MESIN_DIR, "data", "audio")
    now_ts = time.time()
    orphan_audios = []
    if os.path.exists(audio_dir):
        for f in glob.glob(os.path.join(audio_dir, "rek_*.wav")):
            try:
                # File rekaman berumur lebih dari 1 jam dianggap sampah
                if now_ts - os.path.getmtime(f) > 3600:
                    orphan_audios.append(f)
            except Exception:
                pass

    orphan_ppms = glob.glob(os.path.join(MESIN_DIR, "*.ppm")) + glob.glob(os.path.join(MESIN_DIR, "data", "video", "*.ppm"))

    # Cek dead PID tracker
    dead_pid = False
    pid_file = os.path.join(MESIN_DIR, "nav", ".trip_tracker.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as pf:
                pid = int(pf.read().strip())
            # Cek apakah proses masih hidup
            os.kill(pid, 0)
        except (ValueError, OSError):
            dead_pid = True
            masalah.append("File PID trip_tracker usang/mati ditemukan")

    # ── EKSEKUSI PENYEMBUHAN (AUTO-FIX) ──
    if auto_fix:
        # Bersihkan audio usang
        if orphan_audios:
            hapus_count = 0
            for f in orphan_audios:
                try:
                    os.remove(f)
                    hapus_count += 1
                except Exception:
                    pass
            tindakan.append(f"Menghapus {hapus_count} file rekaman audio lama di data/audio/")

        # Bersihkan PPM frame
        if orphan_ppms:
            for f in orphan_ppms:
                try:
                    os.remove(f)
                except Exception:
                    pass
            tindakan.append(f"Menghapus {len(orphan_ppms)} frame sisa PPM video")

        # Hapus dead PID
        if dead_pid and os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                tindakan.append("Membersihkan PID trip tracker mati")
            except Exception:
                pass

        # Vacuum database yang sehat untuk optimalisasi
        for name, path in dbs.items():
            if db_status.get(name) == "SEHAT":
                try:
                    conn = sqlite3.connect(path, timeout=5.0)
                    conn.execute("VACUUM;")
                    conn.close()
                except Exception:
                    pass
        tindakan.append("Mengoptimalkan indeks dan vacuum database SQLite")

        # Reset cache GPS kalkulator
        try:
            from tools import kalkulator
            kalkulator._last_location_cache = None
            tindakan.append("Membersihkan cache RAM koordinat GPS")
        except Exception:
            pass

    return {
        "ram": ram,
        "storage": storage,
        "baterai": baterai,
        "layanan": {
            "Router LLM (Port 8080)": "ONLINE" if local_llm else "OFFLINE",
            "Mata Vision (Port 8082)": "ONLINE (Aktif)" if vision_llm else "STANDBY (On-Demand)",
            "Pemutar Musik (cmus)": "AKTIF" if cmus_ok else "OFFLINE",
            "Telinga Whisper": "SIAP" if whisper_ok else "TIDAK DITEMUKAN"
        },
        "database": db_status,
        "broken_code": broken_code,
        "sampah": {
            "audio_lama": len(orphan_audios),
            "frame_ppm": len(orphan_ppms)
        },
        "masalah": masalah,
        "tindakan": tindakan
    }

def tampilkan_laporan(hasil, auto_fix=False):
    """Mencetak laporan diagnostik dengan UI yang rapi."""
    console.print(Panel(
        f"[bold cyan]🩺 DOKTER MESIN — LAPORAN KESEHATAN SISTEM[/bold cyan]\n"
        f"[dim]Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Mode: {'Auto-Repair' if auto_fix else 'Pemeriksaan Rutin'}[/dim]",
        border_style="cyan"
    ))

    # Tabel Sumber Daya
    t_res = Table(title="📊 Sumber Daya Perangkat", box=box.ROUNDED, show_header=True)
    t_res.add_column("Komponen", style="bold")
    t_res.add_column("Status / Kapasitas")
    t_res.add_column("Kondisi", style="cyan")

    ram = hasil["ram"]
    if "total_mb" in ram:
        t_res.add_row("RAM", f"{ram['used_mb']} MB / {ram['total_mb']} MB ({ram['used_pct']:.0f}%)", f"[green]{ram['status']}[/green]")
    else:
        t_res.add_row("RAM", str(ram.get("status")), "[red]Error[/red]")

    stg = hasil["storage"]
    if "total_gb" in stg:
        t_res.add_row("Storage (~/)", f"Sisa {stg['free_gb']} GB dari {stg['total_gb']} GB", f"[green]{stg['status']}[/green]")
    
    bat = hasil.get("baterai")
    if bat:
        t_res.add_row("Baterai & Suhu", f"{bat['persen']}% ({bat['status_daya']}) | {bat['suhu']}", f"[green]{bat['kondisi']}[/green]")

    console.print(t_res)

    # Tabel Layanan
    t_srv = Table(title="⚙️ Layanan & Proses", box=box.ROUNDED, show_header=True)
    t_srv.add_column("Layanan", style="bold")
    t_srv.add_column("Status")
    for srv, stat in hasil["layanan"].items():
        warna = "green" if "ONLINE" in stat or "SIAP" in stat or "Aktif" in stat else "yellow"
        t_srv.add_row(srv, f"[{warna}]{stat}[/{warna}]")
    console.print(t_srv)

    # Tabel Database
    t_db = Table(title="💾 Integritas Database", box=box.ROUNDED, show_header=True)
    t_db.add_column("Nama DB", style="bold")
    t_db.add_column("Integritas")
    for db_name, stat in hasil["database"].items():
        warna = "green" if stat == "SEHAT" else "red"
        t_db.add_row(db_name, f"[{warna}]{stat}[/{warna}]")
    console.print(t_db)

    # File Rusak
    if hasil["broken_code"]:
        console.print("\n[red]❌ Ditemukan Berkas Kode Rusak (Syntax Error):[/red]")
        for f, err in hasil["broken_code"]:
            console.print(f"  • [bold]{f}[/bold]: {err}")

    # Tindakan Auto-Fix
    if hasil["tindakan"]:
        console.print("\n[bold green]🛠️ Tindakan Pemulihan Berhasil Dilakukan:[/bold green]")
        for act in hasil["tindakan"]:
            console.print(f"  ✅ {act}")

    # Kesimpulan
    if not hasil["masalah"] and not hasil["broken_code"]:
        console.print("\n[bold green]✨ Diagnostik Selesai: Seluruh sistem dalam kondisi SEHAT & PRIMA![/bold green]")
    else:
        console.print(f"\n[yellow]⚠️ Ditemukan {len(hasil['masalah']) + len(hasil['broken_code'])} perhatian sistem.[/yellow]")
        if not auto_fix:
            console.print("[dim]Gunakan perintah '/dokter fix' atau 'python3 tools/dokter.py --fix' untuk pemulihan otomatis.[/dim]")

if __name__ == "__main__":
    auto_fix_flag = "--fix" in sys.argv or "fix" in sys.argv
    hasil_diag = diagnosa_sistem(auto_fix=auto_fix_flag)
    tampilkan_laporan(hasil_diag, auto_fix=auto_fix_flag)
