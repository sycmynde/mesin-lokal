#!/usr/bin/env python3
"""
mesin_tangan.py
==============
Tangan mesin AI: semua tools jadi satu dispatch yang bisa dipanggil via JSON tool-call
dari model (local 3B / 0.8B), supaya AI bukan cuma "ngomong" tapi bisa:
  - hitung, jarak, GPS, arah (turun ke lokasi, dukung & jalan)
  - baca / tulis / edit file (tangan menulis kode / catatan)
  - cek AQI, RAM, baterai, port (mata & telingya)
  - backup, git snapshot, reset memori (otak)
  - akses web bila online (mata jauh: internet), cek audio (telinga)
  - musik / video / gambar (tangan fisik tambahan)

Ringkasan alur:
    model -> {"tool": "nama_tool", "args": {...}}   (di main.py baca)
    hartossulu -> call_tool("nama_tool", args) -> hasil str
    hasil dikembalikan ke model, model jawab lanjut / selesai.

Dibuat modular supaya mudah tambah tool: cukup masukin dict HANDS[new_name].
"""

import os
import sys
import subprocess
import json
import importlib.util

# ── 1. Letakkan tools/ di paling depan di sys.path ──────────────────────────
BASE = os.path.expanduser("/data/data/com.termux/files/home/mesin")
TOOLS_DIR = os.path.join(BASE, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

# ── 2. Load setiap tool module dari file path (bukan paket 'tools') ──────────
#     Paket 'tools' dari hermes-agent kerap muncul di sys.path dan sibuk import.
#     Kita ambil tiap modul sendiri dari file, Paket yang gagal (dependensi
#     hilang seperti bs4, trafilatura) otomatis None dan dibuang dari HANDS.
def _load_tool_module(name):
    """Load modul Python tool dari file path. Return module atau None."""
    path = os.path.join(TOOLS_DIR, name + ".py")
    if not os.path.exists(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("tool_" + name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None

# Load semua tool modules (optional — yang gagal dimasukkan, TIDAK bikin crash)
_kalkulator    = _load_tool_module("kalkulator")
_file_manager   = _load_tool_module("file_manager")
_aqi_checker    = _load_tool_module("aqi_checker")
_check_system   = _load_tool_module("check_system")
_doctor         = _load_tool_module("dokter")
_reset_memori   = _load_tool_module("reset_memori")
_pengingat      = _load_tool_module("pengingat")
_search_router  = _load_tool_module("search_router")
_coding_inspector = _load_tool_module("coding_inspector")
_fetcher        = _load_tool_module("fetcher")
_web_cleaner    = _load_tool_module("web_cleaner")
_rag_coordinator = _load_tool_module("rag_coordinator")
_dj_cmus        = _load_tool_module("dj_cmus")
_git_keeper     = _load_tool_module("git_keeper")
_browser        = _load_tool_module("browser")
_mode_lari      = _load_tool_module("mode_lari")
_llm_online     = _load_tool_module("llm_online")
_termux_api     = _load_tool_module("termux_api")
_shell_exec     = _load_tool_module("shell_exec")
_web_search     = _load_tool_module("web_search")
_code_runner    = _load_tool_module("code_runner")
_musik_manager  = _load_tool_module("musik_manager")
_tts_tools      = _load_tool_module("tts_tools")
_stt_tools      = _load_tool_module("stt_tools")
_plugin_loader  = _load_tool_module("plugin_loader")

# ── Helper umum ──────────────────────────────────────────────────────────
def _trunc(s, n=700):
    """Potong teks panjang biar tidak bikin context penuh."""
    s = s or ""
    return s[:n] + ("…[dipotong]") if len(s) > n else s

def _run_sh(name, args=None):
    """Jalankan script *.sh di tools/."""
    try:
        r = subprocess.run(["bash", os.path.join(TOOLS_DIR, name)],
                           capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"[Error {name}] {e}"

# ── Daftar Tangan (HANDS) ─────────────────────────────────────────────────
# Tipis: module yang gagal di-load (missing deps) otomatis dipotong.
HANDS = {}

def _add_tool(name, fn, args=None):
    """Masukin tool ke HANDS kalau fn ada."""
    if fn is not None:
        HANDS[name] = {"fn": fn, "args": args or {}}

# ── 4. Isi HANDS dari module yang berhasil di-load ──────────────────────────
# ── Matematika & GPS (lari/gowes) ─────────────────────────────────────────────
_add_tool("hitung", lambda **kwargs: _kalkulator.hitung_matematika(kwargs.get('ekspresi', kwargs.get('expression', ''))) if _kalkulator else None)
_add_tool("jarak",   _kalkulator.hitung_jarak_gps    if _kalkulator else None)
_add_tool("lokasi",  _kalkulator.get_current_location if _kalkulator else None)
_add_tool("geocode", _kalkulator.cari_koordinat_tempat if _kalkulator else None)
_add_tool("reverse", _kalkulator.cari_nama_daerah    if _kalkulator else None)
_add_tool("bearing", _kalkulator.hitung_bearing      if _kalkulator else None)
_add_tool("fmt_jarak",_kalkulator.fmt_jarak          if _kalkulator else None)
_add_tool("trip",    _kalkulator.update_total_perjalanan if _kalkulator else None)
_add_tool("trips",   _kalkulator.get_total_perjalanan if _kalkulator else None)
_add_tool("reset_trip",_kalkulator.reset_total_perjalanan if _kalkulator else None)

# ── File & penyimpanan (tangan menulis) ─────────────────────────────────────
_add_tool("baca_file",    _file_manager.read_file      if _file_manager else None)
_add_tool("tulis_file",   _file_manager.write_file     if _file_manager else None)
_add_tool("carifile",     _file_manager.detect_file_action if _file_manager else None)
_add_tool("set_write",     _file_manager.set_write_consent if _file_manager else None)
_add_tool("handle_file_action", _file_manager.handle_file_action if _file_manager else None)

# ── Kualitas udara (AQI) ─────────────────────────────────────────────────────
_add_tool("aqi",   _aqi_checker.cek_aqi_lokal if _aqi_checker else None)
_add_tool("aqi_local", _aqi_checker.cek_aqi_lokal if _aqi_checker else None)

# ── Sistem & status ───────────────────────────────────────────────────────────
_add_tool("check_system", _check_system.check_system       if _check_system else None)
_add_tool("cek_ram",      _doctor.cek_ram                   if _doctor else None)
_add_tool("cek_storage",  _doctor.cek_storage               if _doctor else None)
_add_tool("cek_baterai",  _doctor.cek_baterai               if _doctor else None)
_add_tool("cek_port",     _doctor.cek_port                   if _doctor else None)
_add_tool("cek_db_integritas", _doctor.cek_database_integrity if _doctor else None)
_add_tool("cek_sintaks_kode", _doctor.cek_sintaks_kode      if _doctor else None)
_add_tool("diagnosa",     _doctor.diagnosa_sistem           if _doctor else None)

# ── Memory, catatan, ingatan ──────────────────────────────────────────────────
_add_tool("notes",  _pengingat.status        if _pengingat else None)
_add_tool("ingat",  _pengingat.start         if _pengingat else None)

# ── Internet & browsing ────────────────────────────────────────────────────────
_add_tool("cariweb",       _search_router.search_web      if _search_router else None)
_add_tool("search_github", _search_router.search_github   if _search_router else None)
_add_tool("baca_web",      _fetcher.fetch_parallel        if _fetcher else None)
_add_tool("rag_query",     _rag_coordinator.execute_rag   if _rag_coordinator else None)
_add_tool("memory_ctx",    _rag_coordinator.get_memory_context if _rag_coordinator else None)

# ── Kode / debugging ───────────────────────────────────────────────────────────
_add_tool("inspect_code",  _coding_inspector.inspect_python if _coding_inspector else None)
_add_tool("resolve_source", _coding_inspector.resolve_source if _coding_inspector else None)

# ── Backups & git ─────────────────────────────────────────────────────────────
_add_tool("backup",     _run_sh, {"name": "backup.sh"})
_add_tool("restore",    _run_sh, {"name": "restore.sh"})
_add_tool("git_snapshot", _git_keeper.buat_snapshot if _git_keeper else None)

# ── Musik & media ─────────────────────────────────────────────────────────────
_add_tool("musik",        _dj_cmus.cmus_control     if _dj_cmus else None)
_add_tool("putar_gothic", _dj_cmus.play_gothic_metal if _dj_cmus else None)
_add_tool("scan_music",   _musik_manager.scan_collection if _musik_manager else None)
_add_tool("create_playlists", _musik_manager.create_default_playlists if _musik_manager else None)
_add_tool("list_playlists", _musik_manager.list_playlists if _musik_manager else None)
_add_tool("play_playlist", _musik_manager.play_playlist if _musik_manager else None)
_add_tool("stop_music",   _musik_manager.stop_music if _musik_manager else None)

# ── Video / gambar (kaki/mata ekstra) ────────────────────────────────────────
_add_tool("video",         _run_sh, {"name": "video.sh"})
_add_tool("gambar",        _run_sh, {"name": "gambar.sh"})
_add_tool("video_manual",  _run_sh, {"name": "video_manual.sh"})

# ── Voice / audio (telinga) ───────────────────────────────────────────────────
_add_tool("rekam",    _run_sh, {"name": "rekam.sh"})
_add_tool("rekam_vad",_run_sh, {"name": "rekam_vad.py"})
_add_tool("waktu",    _run_sh, {"name": "waktu.sh"})
_add_tool("gps_now",  _run_sh, {"name": "gps_now.sh"})

# ── Termux API (tools wajib) ───────────────────────────────────────────────────
_add_tool("baterai",       _termux_api.cek_baterai if _termux_api else None)
_add_tool("clipboard_get", _termux_api.clipboard_get if _termux_api else None)
_add_tool("clipboard_set", _termux_api.clipboard_set if _termux_api else None)
_add_tool("kontak",        _termux_api.daftar_kontak if _termux_api else None)
_add_tool("call_log",      _termux_api.log_panggilan if _termux_api else None)
_add_tool("apps_info",     _termux_api.info_aplikasi if _termux_api else None)
_add_tool("brightness",    _termux_api.cek_brightness if _termux_api else None)
_add_tool("set_brightness", _termux_api.set_brightness if _termux_api else None)
_add_tool("fingerprint",   _termux_api.fingerprint if _termux_api else None)
_add_tool("colors",        _termux_api.cek_warna_layar if _termux_api else None)

# ── Shell execution (tools wajib) ─────────────────────────────────────────────
_add_tool("shell",    _shell_exec.shell_exec if _shell_exec else None)
_add_tool("ls",       _shell_exec.list_dir if _shell_exec else None)
_add_tool("cat",      _shell_exec.read_file if _shell_exec else None)
_add_tool("pwd",      _shell_exec.cwd if _shell_exec else None)
_add_tool("date",     _shell_exec.date_now if _shell_exec else None)

# ── Web search & extract (nilai tinggi) ───────────────────────────────────────
_add_tool("web_search",  _web_search.web_search if _web_search else None)
_add_tool("baca_web",    _web_search.web_extract if _web_search else None)

# ── Code execution (nilai tinggi) ─────────────────────────────────────────────
_add_tool("py_run",  _code_runner.run_python if _code_runner else None)
_add_tool("py_eval", _code_runner.run_safe_eval if _code_runner else None)

# ── TTS / STT (suara) ──────────────────────────────────────────────────────────
_add_tool("tts_speak",     _tts_tools.tts_speak if _tts_tools else None)
_add_tool("tts_engines",   _tts_tools.tts_engines if _tts_tools else None)
_add_tool("stt_listen",    _stt_tools.stt_listen if _stt_tools else None)
_add_tool("stt_languages", _stt_tools.stt_languages if _stt_tools else None)

# ── Plugin system ──────────────────────────────────────────────────────────────
_add_tool("list_plugins",  _plugin_loader.list_plugins if _plugin_loader else None)
_add_tool("reload_plugins", _plugin_loader.reload_plugins if _plugin_loader else None)

# ── Doctor (kesehatan sistem) ─────────────────────────────────────────────────
_add_tool("dokter", _doctor.diagnosa_sistem if _doctor else None)

# ── Online LLM / cloud (jika perlu) ───────────────────────────────────────────
_add_tool("llm_online", _llm_online.ask_online if _llm_online else None)

# ── Fungsi utama: dispatch tool ─────────────────────────────────────────────
def call_tool(name, args=None):
    """Ambil tool dari HANDS, jalankan, return hasil (str)."""
    t = HANDS.get(name)
    if not t:
        return f"[Error] tangan tidak ada: {name}"
    base = dict(t.get("args") or {})
    if args:
        base.update(args)
    try:
        return t["fn"](**base)
    except Exception as e:
        return f"[Error] dispatch: {e}"


# ── Loop tool-call (dipanggil kalau model output JSON tool call) ─────────────
def tool_call_loop(session, tool_name, tool_args):
    """Geser hasil tool ke session, return hasil ke model."""
    hasil = call_tool(tool_name, tool_args)
    session.add("tool_result", {"tool": tool_name, "result": str(hasil)})
    return hasil


# ── Tambah tool baru (satu baris) ────────────────────────────────────────────
def register_tool(name, fn, args=None):
    """
    Tambah tool baru ke HANDS.
    Contoh:
        register_tool("ubah_kalimat", lambda s="": s.upper())
    """
    if name in HANDS:
        return f"[Error] tool already exists: {name}"
    HANDS[name] = {"fn": fn, "args": args or {}}
    return f"[OK] tool baru ditambahkan: {name}"


# ── Testing (jalankan langsung dari CLI) ─────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gunakan: python3 mesin_tangan.py <tool_name> [json_args]")
        print("Contoh:")
        print('  python3 mesin_tangan.py hitung {"expression": "123*456"}')
        print('  python3 mesin_tangan.py jarak {"lat1":-6.2,"lon1":106.8,"lat2":13.7,"lon2":100.5}')
        print('  python3 mesin_tangan.py aqi {}')
        print('  python3 mesin_tangan.py cek_ram {}')
        print('  python3 mesin_tangan.py dokter {}')
        sys.exit(1)

    tool_name = sys.argv[1]
    tool_args = {}
    if len(sys.argv) > 2:
        try:
            tool_args = json.loads(sys.argv[2])
        except Exception:
            tool_args = {"query": sys.argv[2]}

    print(f"[Tangan] panggil: {tool_name} {tool_args}")
    hasil = call_tool(tool_name, tool_args)
    print("━━━━━━━━━━━━━━━━━━━")
    print(hasil)
