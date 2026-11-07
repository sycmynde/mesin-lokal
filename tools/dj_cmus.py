import subprocess
import os
import random

MUSIC_DIR = os.path.expanduser("~/mesin/data/musik/gothic_metal")
SUPPORTED_EXTS = ('.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus')

def cmus_remote(args):
    """Helper function untuk mengirim perintah ke cmus"""
    try:
        result = subprocess.run(
            ["cmus-remote"] + args, 
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def play_gothic_metal(keyword=None):
    """Fungsi utama DJ Gothic Metal via cmus"""
    os.makedirs(MUSIC_DIR, exist_ok=True)
    
    # 1. Cek apakah cmus sedang berjalan
    if not cmus_remote(["-Q"]):
        return "⚠️ cmus belum aktif! Buka terminal & ketik 'cmus' dulu ya."
    
    # 2. Scan file musik
    files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(SUPPORTED_EXTS)]
    if not files:
        return "📁 Folder gothic_metal kosong. Simpan lagu di ~/mesin/data/musik/gothic_metal dulu!"
    
    # 3. Cari target lagu
    target_path = None
    display_name = ""
    
    if keyword:
        matched = [f for f in files if keyword.lower() in f.lower()]
        if matched:
            chosen = random.choice(matched)
        else:
            return f"🔍 Lagu '{keyword}' tidak ditemukan. Coba kata kunci lain."
    else:
        chosen = random.choice(files)
    
    target_path = os.path.join(MUSIC_DIR, chosen)
    display_name = os.path.splitext(chosen)[0]
    
    # 4. Kirim perintah ke cmus (-f = force play file ini sekarang juga)
    success = cmus_remote(["-f", target_path])
    
    if success:
        return f"▶️ CMUS memutar: {display_name}"
    else:
        return "❌ Gagal komunikasi dengan cmus. Coba restart cmus."

def cmus_control(action):
    """Fungsi kontrol dasar playback cmus saat lari"""
    controls = {
        "pause": ["-u"],      # Toggle pause/play
        "play": ["-p"],       # Play
        "next": ["-n"],       # Next track
        "prev": ["-r"],       # Previous track
        "stop": ["-s"],       # Stop total
        "shuffle": ["-S"],    # Toggle acak
        "repeat": ["-R"]      # Toggle ulang
    }
    
    if action in controls:
        if cmus_remote(controls[action]):
            return f"✅ Perintah '{action}' terkirim ke cmus."
        return "⚠️ cmus tidak merespon atau belum aktif."
    return "Perintah tidak dikenal. Gunakan: play, pause, next, prev, stop, shuffle, repeat"
