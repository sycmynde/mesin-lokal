#!/usr/bin/env python3
"""Playlist manager untuk koleksi musik olahraga + cmus controller."""
import os
import re
import json
import random
import subprocess

BASE = "/data/data/com.termux/files/home/gothic_metal"
PLAYLIST_DIR = os.path.join(BASE, "playlists")
CMUS_SOCK = os.path.expanduser("~/.config/cmus/socket")

SUPPORTED_EXTS = ('.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus')

# Genre detection based on filename patterns
GENRE_PATTERNS = {
    "gothic": ["gothic", "black metal", "dark", "symphony hitam", "queen of darkness", "mendiang", "eling", "semesta", "mati suri", "cahaya bidadari", "habis gelap"],
    "hiphop": ["hip hop", "hiphop", "rap", "jawa", "ndugal", "racing", "wasap mamen", "cintamu", "topi miring", "suwung"],
}

def detect_genre(filename):
    name = filename.lower()
    for genre, patterns in GENRE_PATTERNS.items():
        if any(p in name for p in patterns):
            return genre
    return "unknown"

def scan_collection():
    files = []
    for f in os.listdir(BASE):
        if f.endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')) and os.path.isfile(os.path.join(BASE, f)):
            genre = detect_genre(f)
            files.append({"name": f, "genre": genre, "path": os.path.join(BASE, f)})
    return files

def save_playlist(name, files):
    os.makedirs(PLAYLIST_DIR, exist_ok=True)
    path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
    with open(path, "w", encoding="utf-8") as f:
        for item in files:
            f.write(item["path"] + "\n")
    return path

def create_default_playlists():
    files = scan_collection()
    gothic = [f for f in files if f["genre"] == "gothic"]
    hiphop = [f for f in files if f["genre"] == "hiphop"]
    olahraga = files  # semua untuk olahraga

    save_playlist("gothic_only", gothic)
    save_playlist("hiphop_only", hiphop)
    save_playlist("olahraga_all", olahraga)
    save_playlist("olahraga_mix", random.sample(olahraga, min(5, len(olahraga))))
    
    return {
        "gothic_only": len(gothic),
        "hiphop_only": len(hiphop),
        "olahraga_all": len(olahraga),
        "olahraga_mix": min(5, len(olahraga)),
    }

def list_playlists():
    if not os.path.isdir(PLAYLIST_DIR):
        return "Tidak ada playlist."
    playlists = []
    for f in os.listdir(PLAYLIST_DIR):
        if f.endswith(".m3u"):
            playlists.append(f.replace(".m3u", ""))
    return "\n".join(playlists) if playlists else "Tidak ada playlist."

# ── cmus helpers ──

def _cmus_remote(args):
    try:
        result = subprocess.run(
            ["cmus-remote"] + args,
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def _cmus_clear_and_load(path):
    if not os.path.isfile(path):
        return False, f"[Error] Playlist tidak ditemukan: {path}"
    # Clear and load in one remote call, then play separately to avoid argument parsing issues
    ok1 = _cmus_remote(["-c", "-l", path])
    ok2 = _cmus_remote(["-p"])
    if ok1 and ok2:
        return True, f"[OK] Memutar playlist: {os.path.splitext(os.path.basename(path))[0]}"
    return False, "[Error] Gagal komunikasi dengan cmus. Buka cmus dulu."

def _ensure_cmus_running():
    if not _cmus_remote(["-Q"]):
        try:
            subprocess.Popen(
                ["cmus"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return "⚠️ cmus belum aktif. Mencoba menjalankan cmus..."
        except Exception:
            return "❌ cmus tidak terinstal atau gagal dijalankan."
    return None

# ── Musik tools ──

def play_playlist(name):
    if not name:
        return "[Error] Nama playlist kosong."
    path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
    ok, msg = _cmus_clear_and_load(path)
    if not ok and "Gagal komunikasi" in msg:
        pre = _ensure_cmus_running()
        if pre:
            return pre
        ok, msg = _cmus_clear_and_load(path)
    if ok:
        return msg
    return msg

def find_music(query):
    if not query:
        return "[Error] Query kosong."
    files = []
    for root, _, filenames in os.walk(BASE):
        for f in filenames:
            if f.lower().endswith(SUPPORTED_EXTS):
                files.append(os.path.join(root, f))
    if not files:
        return "[Error] Folder musik kosong."
    q = query.lower()
    matched = [f for f in files if q in os.path.basename(f).lower()]
    if not matched:
        return f"[Error] Lagu '{query}' tidak ditemukan."
    return "\n".join(matched)


def play_query(query):
    if not query:
        return "[Error] Query lagu kosong. Contoh: musik habis gelap"
    files = []
    for root, _, filenames in os.walk(BASE):
        for f in filenames:
            if f.lower().endswith(SUPPORTED_EXTS):
                files.append(os.path.join(root, f))
    if not files:
        return "[Error] Folder musik kosong."
    q = query.lower()
    matched = [f for f in files if q in os.path.basename(f).lower()]
    if not matched:
        return f"[Error] Lagu '{query}' tidak ditemukan. Coba kata kunci lain."
    target = random.choice(matched)
    name = os.path.splitext(os.path.basename(target))[0]
    ok = _cmus_remote(["-c", "-f", target])
    if ok:
        return f"[OK] Memutar: {name}\n[Path] {target}"
    pre = _ensure_cmus_running()
    if pre:
        return pre
    if _cmus_remote(["-c", "-f", target]):
        return f"[OK] Memutar: {name}\n[Path] {target}"
    return "[Error] Gagal komunikasi dengan cmus. Buka cmus dulu."

def stop_music():
    if _cmus_remote(["-s"]):
        return "[OK] Musik dihentikan."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[OK] Musik dihentikan."

def next_track():
    if _cmus_remote(["-n"]):
        return "[OK] Next track."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[Error] Gagal kirim perintah next."

def prev_track():
    if _cmus_remote(["-r"]):
        return "[OK] Previous track."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[Error] Gagal kirim perintah prev."

def toggle_pause():
    if _cmus_remote(["-u"]):
        return "[OK] Toggle pause/play."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[Error] Gagal toggle pause."

def shuffle_on():
    if _cmus_remote(["-S"]):
        return "[OK] Shuffle on."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[Error] Gagal set shuffle."

def repeat_on():
    if _cmus_remote(["-R"]):
        return "[OK] Repeat on."
    if _ensure_cmus_running():
        return "⚠️ cmus belum aktif."
    return "[Error] Gagal set repeat."

def scan_music():
    return json.dumps(scan_collection(), ensure_ascii=False, indent=2)

def create_playlists():
    return json.dumps(create_default_playlists(), ensure_ascii=False, indent=2)

HANDS = {
    "scan_music": scan_music,
    "create_playlists": create_playlists,
    "list_playlists": list_playlists,
    "play_playlist": play_playlist,
    "play_query": play_query,
    "stop_music": stop_music,
    "next_track": next_track,
    "prev_track": prev_track,
    "toggle_pause": toggle_pause,
    "shuffle_on": shuffle_on,
    "repeat_on": repeat_on,
}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Gunakan: python3 musik_manager.py <command> [args]")
        print("Commands: scan, create, list, play <nama>, next, prev, pause, shuffle, repeat, stop")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "scan":
        print(HANDS["scan_music"]())
    elif cmd == "create":
        print(HANDS["create_playlists"]())
    elif cmd == "list":
        print(HANDS["list_playlists"]())
    elif cmd == "play" and len(sys.argv) > 2:
        print(HANDS["play_playlist"](sys.argv[2]))
    elif cmd == "query" and len(sys.argv) > 1:
        print(HANDS["play_query"](" ".join(sys.argv[2:])))
    elif cmd == "stop":
        print(HANDS["stop_music"]())
    elif cmd == "next":
        print(HANDS["next_track"]())
    elif cmd == "prev":
        print(HANDS["prev_track"]())
    elif cmd == "pause":
        print(HANDS["toggle_pause"]())
    elif cmd == "shuffle":
        print(HANDS["shuffle_on"]())
    elif cmd == "repeat":
        print(HANDS["repeat_on"]())
    else:
        print("Command tidak dikenali")
