"""DJ Plugin - Gothic Metal Offline Player via cmus"""
import os, subprocess, random

MUSIC_DIR = os.path.expanduser("~/mesin/data/musik/gothic_metal")

def putar_musik(keyword=None):
    try:
        check = subprocess.run(["cmus-remote", "-Q"], capture_output=True, timeout=3)
        if check.returncode != 0:
            return "️ cmus belum aktif! Buka terminal & ketik 'cmus' dulu."
    except FileNotFoundError:
        return "❌ cmus-remote tidak ditemukan. Install: pkg install cmus"
    
    if not os.path.isdir(MUSIC_DIR):
        return f"📂 Folder {MUSIC_DIR} tidak ditemukan!"
    
    files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.mp3')]
    if not files:
        return "📂 Folder gothic_metal kosong. Download lagu dulu!"
    
    chosen = None
    if keyword:
        matched = [f for f in files if keyword.lower() in f.lower()]
        if matched: chosen = random.choice(matched)
        else: return f"🔍 Lagu '{keyword}' tidak ditemukan."
    else:
        chosen = random.choice(files)
    
    filepath = os.path.join(MUSIC_DIR, chosen)
    try:
        result = subprocess.run(["cmus-remote", "-f", filepath], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return f"🎵 CMUS putar: {chosen.replace('.mp3','')}"
        return "❌ Gagal kirim perintah ke cmus."
    except subprocess.TimeoutExpired:
        return "️ Timeout: cmus tidak merespon."

def kontrol_cmus(action=None):
    commands = {"pause": ["-u"], "next": ["-n"], "prev": ["-r"], 
                "stop": ["-s"], "shuffle": ["-S"], "repeat": ["-R"]}
    if action not in commands:
        return f"Perintah tidak valid. Gunakan: {', '.join(commands.keys())}"
    try:
        subprocess.run(["cmus-remote"] + commands[action], capture_output=True, timeout=3)
        return f"✅ Perintah '{action}' terkirim ke cmus."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"
