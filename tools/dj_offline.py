import os
import random
import subprocess

MUSIC_DIR = os.path.expanduser("~/mesin/data/musik/gothic_metal")
SUPPORTED_EXTS = ('.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus')

def play_gothic_metal(keyword=None):
    """Memutar lagu gothic metal dari folder lokal via ffplay"""
    os.makedirs(MUSIC_DIR, exist_ok=True)
    
    # Cari semua file audio yang didukung
    files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(SUPPORTED_EXTS)]
    
    if not files:
        return "📁 Folder musik kosong. Download atau simpan lagu di ~/mesin/data/musik/gothic_metal dulu!"
    
    # Filter berdasarkan keyword jika ada
    if keyword:
        matched = [f for f in files if keyword.lower() in f.lower()]
        if matched:
            chosen = random.choice(matched)
        else:
            return f"🔍 Lagu '{keyword}' tidak ditemukan. Coba kata kunci lain."
    else:
        chosen = random.choice(files)
    
    filepath = os.path.join(MUSIC_DIR, chosen)
    display_name = os.path.splitext(chosen)[0]
    
    # Putar via ffplay (ringan & support audio-only)
    try:
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"🎵 Memutar: {display_name}"
    except FileNotFoundError:
        return "⚠️ ffplay belum terinstall. Ketik: pkg install ffmpeg"
    except Exception as e:
        return f"❌ Gagal memutar musik: {e}"
