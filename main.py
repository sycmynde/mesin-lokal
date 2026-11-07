import os
import re
from core.db_session import save_message, get_recent_history, init_db
from core.colors import CYAN, YELLOW, GREEN, RED, DIM, BOLD, BLUE, R, SOFT_GREEN, SOFT_BLUE
import uuid
from core.config import load_config
from core.router import Router
from core.dispatcher import Dispatcher
from core.session import Session
from core.memory import Memory
from core.project import ProjectState
from core.brain_router import BrainRouter
from core.brain_registry import BrainRegistry
from core.context_manager import ContextManager
from brains.math_brain import MathBrain
from brains.file_brain import FileBrain
from brains.memory_brain import MemoryBrain
from brains.llm_brain import LLMBrain
from brains.rag_brain import RAGBrain
from brains.project_brain import ProjectBrain
from brains.nav_brain import NavBrain
from brains.termux_brain import TermuxBrain
from brains.shell_brain import ShellBrain
from brains.web_brain import WebBrain
from brains.code_brain import CodeBrain
from brains.tts_brain import TTSBrain
from brains.stt_brain import STTBrain
from brains.plugin_brain import PluginBrain
from brains.musik_brain import MusikBrain
from agents.a2a_brain import A2ABrain
from tools.kalkulator import hitung_matematika
from tools.file_manager import handle_file_action
from tools.mesin_tangan import HANDS as TOOL_HANDS
import re
import threading
from rich.console import Console as _RichConsole
from rich.panel import Panel as _RichPanel
from rich.markdown import Markdown as _RichMarkdown
from rich.text import Text as _RichText
from rich.table import Table as _RichTable
from rich.prompt import Prompt as _RichPrompt
from rich import box as _rich_box
console = _RichConsole()

# ── COLOR RENDERER ──
def render_colored_answer(text):
    import re as _re
    KUNING = "\033[33m"
    HIJAU_MUDA = "\033[1;92m"
    BIRU = "\033[34m"
    HIJAU = "\033[32m"
    RESET = "\033[0m"
    tag_colors = {
        "[PEMBUKA]": KUNING,
        "[INTI]": HIJAU_MUDA,
        "[DETAIL]": BIRU,
        "[KESIMPULAN]": HIJAU,
    }
    lines = text.split("\n")
    output_lines = []
    current_color = RESET
    for line in lines:
        stripped = line.strip()
        matched = False
        for tag, color in tag_colors.items():
            if stripped.startswith(tag):
                clean = stripped[len(tag):].strip()
                current_color = color
                output_lines.append(f"{color}{clean}{RESET}")
                matched = True
                break
        if not matched:
            if stripped:
                output_lines.append(f"{current_color}{line}{RESET}")
            else:
                output_lines.append("")
    return "\n".join(output_lines)

def render_rich_answer(text, tier="default"):
    tag_style = {
        "[PEMBUKA]": "yellow",
        "[INTI]": "bold green",
        "[DETAIL]": "cyan",
        "[KESIMPULAN]": "green",
    }
    judul = "☁️ LLM Cloud" if tier == "cloud" else "🧠 LLM Lokal"
    gaya = "bright_cyan" if tier == "cloud" else "bright_green"
    if any(tg in text for tg in tag_style):
        body = _RichText()
        cur = None
        for line in text.split("\n"):
            s = line.strip()
            hit = next(((tg, st) for tg, st in tag_style.items() if s.startswith(tg)), None)
            if hit:
                tg, st = hit
                cur = st
                body.append(s[len(tg):].strip() + "\n", style=st)
            else:
                body.append((s or " ") + "\n", style=cur)
        console.print(body)
    else:
        console.print(text)

import json
_LAST_AQI = {"aqi": None, "emoji": ""}
KNOWN_CMDS = ["/aqi", "/status", "/model", "/models", "/load", "/unload",
 "/catat", "/dengar", "/instan", "/default", "/power", "/gambar",
 "/lari", "/help", "/a2a", "/tools"]

def _execute_tool_call(text):
    m = re.search(r"<call>(.*?)</call>", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = re.sub(r"```json", "", raw)
    raw = re.sub(r"```", "", raw).strip()
    try:
        data = json.loads(raw)
    except Exception:
        return "Error: Format tool call bukan JSON valid."
    tool = data.get("tool")
    args = data.get("args") or {}
    if not tool:
        return "Error: Tool call harus berisi 'tool'."
    if tool not in TOOL_HANDS:
        return f"Error: Tool '{tool}' tidak ditemukan. Ketik /tools untuk daftar."
    meta = TOOL_HANDS[tool]
    fn = meta.get("fn")
    if not callable(fn):
        return f"Error: Tool '{tool}' tidak aktif."
    default_args = meta.get("args") or {}
    if default_args:
        merged = dict(default_args)
        merged.update(args)
        args = merged
    try:
        return fn(**args)
    except Exception as e:
        return f"Error menjalankan '{tool}': {e}"

def _render_tool_help():
    lines = ["[bold]Tool Call di Chat[/bold]",
             "Format: <call>{\"tool\":\"nama\", \"args\":{...}}</call>",
             "",
             "[bold]Daftar Tool:[/bold]"]
    for name in sorted(TOOL_HANDS.keys()):
        meta = TOOL_HANDS[name]
        fn = meta.get("fn")
        doc = (getattr(fn, "__doc__", "") or "").strip()
        doc = doc.splitlines()[0] if doc else "(tanpa deskripsi)"
        lines.append(f"  {name}: {doc}")
    lines += ["", "[dim]Contoh: <call>{\"tool\":\"baterai\", \"args\":{}}</call>[/dim]"]
    return "\n".join(lines)

def render_bar(models=None, tier=None):
    t = _RichText()
    t.append("🧠 " + (", ".join(sorted(models)) if models else "model: belum ada"), style="cyan")
    t.append(" • 🎚 " + (tier or "auto"), style="magenta")
    try:
        import psutil
        ram = int(psutil.virtual_memory().available / (1024 * 1024))
        t.append(f" • 💾 {ram}MB", style="green")
    except Exception:
        pass
    if _LAST_AQI["aqi"]:
        t.append(f" • 🌫 AQI {_LAST_AQI['aqi']} {_LAST_AQI['emoji']}", style="yellow")
    console.print(t)

def _gaya_aqi(aqi):
    if aqi <= 50: return "green"
    if aqi <= 100: return "yellow"
    if aqi <= 150: return "dark_orange"
    if aqi <= 200: return "red"
    if aqi <= 300: return "magenta"
    return "bold red"

def render_aqi_card(d):
    from rich.console import Group as _RichGroup
    aqi = d.get("aqi", 0) or 0
    gaya = _gaya_aqi(aqi)
    head = _RichText()
    head.append(f"{d.get('emoji', '')} AQI {aqi} — {d.get('kategori', '?')}", style=f"bold {gaya}")
    info = _RichText(f"📍 {d.get('sumber', '')} ({d.get('lat', '')}, {d.get('lon', '')}) | ⏰ {d.get('time', '?')}", style="dim")
    t = _RichTable(box=_rich_box.SIMPLE, padding=(0, 1))
    t.add_column("Polutan", style="cyan")
    t.add_column("Kadar", justify="right")
    t.add_column("sub-AQI", justify="right")
    subs = d.get("subs", {})
    for nama, key in (("PM2.5", "pm2_5"), ("PM10", "pm10"), ("O3", "o3")):
        kadar = d.get(key)
        sa = subs.get(key)
        t.add_row(nama,
            f"{kadar} µg/m³" if kadar is not None else "?",
            f"[{_gaya_aqi(sa or 0)}]{sa}[/]" if sa is not None else "-")
    extra = _RichText()
    if d.get("pol"):
        extra.append(f"🎯 Biang kerok: {d.get('pol_flag', '')} (sub-AQI {d.get('pol_aqi')})\n", style="bold")
    extra.append(f"🏃 {d.get('saran', '')}\n", style=gaya)
    extra.append(f"🚴 {d.get('saran_sepeda', '')}", style=gaya)
    console.print(_RichPanel(_RichGroup(head, info, t, extra),
        title="[bold]🌐 Kualitas Udara[/bold]",
        border_style=gaya, padding=(0, 1)))

def _bersihkan_lisan(teks):
    import re as _r
    t = _r.sub(r"\[(PEMBUKA|INTI|DETAIL|KESIMPULAN|PENUTUP)\]", "", teks or "")
    t = _r.sub(r"[#*`_ >|]", "", t)
    t = " ".join(t.split())
    parts = _r.split(r"(?<=[.!?])\s+", t.strip())
    return " ".join(parts[:2])

def bicara(teks):
    t = _bersihkan_lisan(teks)
    if not t: return
    try:
        import subprocess as _sp
        _sp.run(["termux-tts-speak", "-l", "id", t], capture_output=True, timeout=30)
    except Exception:
        pass

AMBANG_SUARA = 350
_TEKS_SEBELUMNYA = None
_TEKS_SAMA = 0
HALU_SUARA = {
    "terima kasih kerana menonton", "terima kasih telah menonton",
    "terima kasih sudah menonton", "terima kasih untuk menonton",
    "selamat menonton", "jangan lupa subscribe",
}

def energi_wav(path):
    import wave, array
    try:
        w = wave.open(path, "rb")
        raw = w.readframes(w.getnframes())
        w.close()
        a = array.array("h")
        a.frombytes(raw)
        if not a: return 0
        return int((sum(x * x for x in a) / len(a)) ** 0.5)
    except Exception:
        return 10 ** 9

def _stop_suara(low):
    import difflib
    stops = ("cukup", "sudahi", "berhenti", "stop", "selesai", "sudah")
    if any(w in low for w in stops): return True
    toks = low.split()
    return any(difflib.get_close_matches(w, toks, 1, 0.72) for w in stops)

def transkrip_aman(wav, wp):
    global _TEKS_SEBELUMNYA, _TEKS_SAMA
    try:
        teks = wp.transcribe(wav, language="id")
    except TypeError:
        teks = wp.transcribe(wav)
    except Exception:
        return ""
    teks = (teks or "").strip()
    low = teks.lower()
    if not low: return ""
    if low in HALU_SUARA: return ""
    if low == _TEKS_SEBELUMNYA:
        _TEKS_SAMA += 1
    else:
        _TEKS_SAMA = 0
        _TEKS_SEBELUMNYA = low
    if _TEKS_SAMA >= 1: return ""
    return teks

def unload_aman(lp, model_id):
    for nama in ("unload_model", "unload", "release_model"):
        fn = getattr(lp, nama, None)
        if callable(fn):
            try: return bool(fn(model_id))
            except Exception: return False
    try:
        import requests as _rq
        r = _rq.post("http://127.0.0.1:8080/models/unload", json={"model": model_id}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def rem_repetisi(teks, max_ulang=3):
    lines = teks.split("\n")
    out, seen = [], {}
    for ln in lines:
        k = ln.strip()[:60]
        if k:
            seen[k] = seen.get(k, 0) + 1
            if seen[k] > max_ulang:
                out.append("   ⚠️ [model nyangkut di loop — output dipotong]")
                break
        out.append(ln)
    return "\n".join(out)

def choose_llm_tier(text):
    q = text.lower().strip()
    if q == "/instan": return "instan", ""
    if q.startswith("/instan "): return "default", text[len("/instan "):].strip()
    if q == "/default": return "default", ""
    if q.startswith("/default "): return "default", text[len("/default "):].strip()
    if q == "/power": return "cloud", ""
    if q.startswith("/power "): return "cloud", text[len("/power "):].strip()
    if q.startswith("/gambar "):
        prompt = text[len("/gambar "):].strip()
        import subprocess
        print("\n🎨 [Mesin Gambar] Diteruskan ke background...")
        script_path = "/data/data/com.termux/files/home/mesin/tools/gambar.sh"
        log_path = "/data/data/com.termux/files/home/mesin/logs/gambar.log"
        with open(log_path, "a") as lf:
            subprocess.Popen(["bash", script_path, prompt], stdout=lf, stderr=lf)
        return "local", "✅ Gambar jalan di background! Pantau: tail -f ~/mesin/logs/gambar.log"
    
    instant_keywords = ("halo", "hai", "hi", "hello", "hei", "makasih", "terima kasih", "thanks", "siapa kamu", "siapa saya", "jam berapa", "tanggal berapa")
    if len(q) < 40 and any(k in q for k in instant_keywords):
        return "default", text
    
    online_keywords = ("cari informasi terbaru", "informasi terbaru", "berita terbaru", "berita hari ini", "terbaru tentang", "update terbaru", "cek internet", "cari di internet", "cari di web", "di internet", "di web", "harga terbaru", "versi terbaru", "rilis terbaru", "update hari ini", "hari ini tentang", "sekarang tentang")
    if any(k in q for k in online_keywords):
        return "default", text
    
    factual_keywords = ("berapa", "siapa", "kapan", "di mana", "dimana", "apa itu", "jelaskan", "kenapa", "mengapa", "bagaimana", "gimana", "bandingkan", "hitung")
    if any(k in q for k in factual_keywords):
        return "default", text
    
    return "default", text

def main():
    config = load_config()
    router = Router()
    brain_router = BrainRouter()
    dispatcher = Dispatcher(config)
    session = Session()
    memory = Memory()
    project = ProjectState()
    registry = BrainRegistry()
    context_manager = ContextManager(memory)
    active_models = set()
    active_tier = None
    
    registry.register("math", MathBrain())
    registry.register("file", FileBrain())
    registry.register("memory", MemoryBrain())
    registry.register("llm", LLMBrain(dispatcher))
    registry.register("rag", RAGBrain())
    registry.register("project", ProjectBrain(project))
    registry.register("nav", NavBrain())
    registry.register("termux", TermuxBrain())
    registry.register("shell", ShellBrain())
    registry.register("web", WebBrain())
    registry.register("code", CodeBrain())
    registry.register("tts", TTSBrain())
    registry.register("stt", STTBrain())
    registry.register("plugin", PluginBrain())
    registry.register("musik", MusikBrain())
    registry.register("a2a", A2ABrain(dispatcher))
    
    console.print(_RichPanel.fit(
        "[bold green]🚀 MESIN AI MODULAR v0.8[/bold green]\n"
        "[dim]Router + Dispatcher + Local LLM + Cloud + Session[/dim]\n"
        "[dim]Ketik 'exit' untuk berhenti[/dim]",
        border_style="bright_blue", padding=(1, 2),
    ))
    render_bar()
    SESSION_ID = str(uuid.uuid4())[:8]
    init_db()
    messages = get_recent_history(SESSION_ID)
    if not any(m.get('role') == 'system' for m in messages):
        messages.insert(0, {'role': 'system', 'content': '[SYSTEM]: Jawab singkat, padat, jelas. Maksimal 3 kalimat. Jangan mengulang kata. Bahasa Indonesia natural.'})
    console.print(f"[dim]📂 Sesi {SESSION_ID} | Memuat {len(messages)} riwayat...[/dim]")
    
    while True:
        try:
            _pq = globals().pop("_suara_pending", None)
            user_input = _pq if _pq else _RichPrompt.ask("[bold cyan] Anda[/bold cyan]")
            if _pq: print(f" Anda: {_pq} 🎙️ (suara)")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input.strip(): continue
        if user_input.lower() in ["exit", "keluar"]: break
        
        cmd = user_input.strip().lower()
        if cmd.startswith("/"):
            tok = cmd.split()[0]
            if tok not in KNOWN_CMDS:
                matches = [c for c in KNOWN_CMDS if c.startswith(tok)]
                if len(matches) == 1:
                    user_input = matches[0] + user_input[len(tok):]
                    cmd = user_input.strip().lower()
                    console.print(f"[dim]↹ {user_input}[/dim]")
                elif len(matches) > 1 and cmd == tok:
                    console.print("[dim]Saran: " + ", ".join(matches) + " — atau /help[/dim]")
                    continue
        
        if cmd == "/dokter":
            try:
                from tools.dokter import diagnosa_sistem, tampilkan_laporan
                hasil = diagnosa_sistem(auto_fix=False)
                tampilkan_laporan(hasil, auto_fix=False)
            except Exception as e:
                console.print(f"[red]Dokter Mesin gagal berjalan: {e}[/red]")
            continue

        if cmd.startswith("/dokter fix"):
            try:
                from tools.dokter import diagnosa_sistem, tampilkan_laporan
                hasil = diagnosa_sistem(auto_fix=True)
                tampilkan_laporan(hasil, auto_fix=True)
            except Exception as e:
                console.print(f"[red]Dokter Mesin gagal berjalan: {e}[/red]")
            continue

        if cmd == "/tools":
            console.print(_RichPanel(
                _render_tool_help(),
                title="[bold]🛠 Tool Call[/bold]",
                border_style="bright_blue"))
            continue

        if cmd == "/help":
            console.print(_RichPanel(
                "[bold]Perintah:[/bold]\n"
                "  /aqi • /status • /model • /models\n"
                "  /load <model> • /unload <model>\n"
                "  /catat <isi> • /dengar\n"
                "  /instan • /default • /power • /gambar <prompt>\n"
                "  /dokter — pemeriksaan sistem\n"
                "  /dokter fix — pemulihan otomatis\n"
                "  /tools — daftar tool call\n"
                "  /a2a agents — daftar agent\n"
                "  /a2a ask [capability] \"tugas\" — minta bantuan agent\n"
                "  <call>{...}</call> — panggil tool dari chat\n"
                "  exit | keluar\n\n"
                "[dim]Ketik awalan perintah mis. /aq lalu Enter → otomatis dilengkapi.[/dim]",
                title="[bold]❓ Bantuan[/bold]", border_style="bright_blue"))
            continue
        
        if cmd.startswith("/a2a"):
            rest = user_input.strip()[5:].strip()
            if not rest or rest in ("agents", "list"):
                answer = registry.execute("a2a", {"action": "agents"})
                print(f" A2A: {answer}")
                session.add("user", user_input); session.add("assistant", str(answer))
                continue
            if rest.startswith("ask "):
                ask_text = rest[4:].strip()
                capability = "chat"
                task = ask_text
                if ask_text.startswith('"'):
                    end = ask_text.find('"', 1)
                    if end != -1:
                        capability = ask_text[1:end].strip()
                        task = ask_text[end+1:].strip()
                if not task:
                    print("   ⚠️ Format: /a2a ask [capability] \"tugas\"")
                    continue
                answer = registry.execute("a2a", {"action": "ask", "task": task, "capability": capability})
                print(f" A2A: {answer}")
                session.add("user", user_input); session.add("assistant", str(answer))
                continue
            print("   ⚠️ Format: /a2a agents | /a2a ask [capability] \"tugas\"")
            continue
        
        # Tool call umum via <call>...</call>
        if "<call>" in user_input:
            answer = _execute_tool_call(user_input)
            print(f" [Tool]: {answer}")
            session.add("user", user_input)
            session.add("assistant", str(answer))
            continue
        
        if cmd == "/lari":
            import threading
            import tools.mode_lari as _ml
            threading.Thread(target=_ml.run_lari_mode, args=(registry, session), daemon=True).start()
            console.print("[green]🏃 Mode lari dijalankan di latar belakang.[/green]")
        
        if cmd == "/aqi":
            import subprocess
            print("\n🌐 [AQI] Memeriksa kualitas udara...")
            try:
                gps = subprocess.run(["bash", os.path.expanduser("~/mesin/tools/gps_now.sh")], capture_output=True, text=True, timeout=45)
                if gps.returncode == 0 and gps.stdout.strip(): print(f"   📍 GPS segar: {gps.stdout.strip()}")
                else: print(f"   ⚠️ GPS segar gagal — pakai cache/fallback")
            except Exception: print("   ⚠️ GPS timeout")
            result = subprocess.run(["python3", os.path.expanduser("~/mesin/plugins/aqi_report.py"), "--json"], capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                try:
                    d = json.loads(result.stdout)
                    _LAST_AQI.update({"aqi": d.get("aqi"), "emoji": d.get("emoji", "")})
                    render_aqi_card(d)
                    render_bar(active_models, active_tier)
                    continue
                except Exception: pass
            print(result.stdout if result.returncode == 0 else f"Error: {result.stderr}")
            continue
        
        if cmd.startswith("/catat"):
            isi = user_input.strip()[len("/catat"):].strip()
            if not isi: print("❌ Format: /catat <isi catatan>")
            else:
                try:
                    from core.memory_manager import add_memory
                    import datetime as _dt
                    add_memory("jurnal", _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), isi)
                    print(f" Tercatat: {isi}")
                except Exception as e: print(f"❌ Gagal mencatat: {e}")
            continue
        
        if cmd == "/dengar":
            import subprocess
            print("\n🎙️ [DENGAR] Merekam 8 detik...")
            try:
                rec = subprocess.run(["bash", os.path.expanduser("~/mesin/tools/rekam.sh"), "8"], capture_output=True, text=True, timeout=60)
                if rec.returncode != 0 or not rec.stdout.strip():
                    print(" Rekaman gagal")
                    continue
                wav = rec.stdout.strip().splitlines()[-1]
                from providers.whisper import whisper_provider
                print("   👂 Mentranskrip...")
                teks = whisper_provider.transcribe(wav)
                if not teks:
                    print("❌ Whisper nggak dengar apa-apa")
                    continue
                print(f"   📝 Terdengar: \"{teks}\"")
                _t = teks.lower()
                def _posisi(keys):
                    hits = [_t.find(k) for k in keys if k in _t]
                    return min(hits) if hits else 10**9
                _p_catat = _posisi(["catat", "catatan", "jurnal", "ingat bahwa", "ingat kalo", "ingat kalau"])
                _p_udara = _posisi(["udara", "aqi", "polusi"])
                if _p_catat <= _p_udara and _p_catat < 10**9:
                    globals()["_suara_pending"] = "/catat " + teks
                elif _p_udara < 10**9:
                    globals()["_suara_pending"] = "/aqi"
                else:
                    globals()["_suara_pending"] = teks
            except subprocess.TimeoutExpired: print("❌ Timeout rekaman")
            except Exception as e: print(f"❌ /dengar error: {e}")
            continue
        
        if cmd == "/model":
            print("\n MODEL STATUS")
            requested_models = sorted(active_models) if active_models else []
            if requested_models: print(f"   Requested models: {', '.join(requested_models)}")
            else: print("   Requested models: belum ada")
            print("\n   llama-server:")
            try:
                import requests
                r = requests.get("http://127.0.0.1:8080/models", timeout=3)
                r.raise_for_status()
                models = r.json().get("data", [])
                loaded = [m.get("id", "?") for m in models if m.get("status", {}).get("value", "unknown") == "loaded"]
                if loaded:
                    for name in loaded: print(f"    loaded      {name}")
                else: print("   ⚪ Tidak ada model loaded.")
                tier_models = {"instan": "Qwen3.5-0.8B-Q4_0", "default": "Qwen2.5-3B-Instruct-Q4_K_M", "power": "CLOUD"}
                expected_model = tier_models.get(active_tier)
                if active_tier == "cloud":
                    print("\n   Mode: ️ ONLINE | Local model: tidak digunakan")
                elif expected_model and loaded:
                    if expected_model in loaded: print("\n   Match: ✅ OK")
                    else: print(f"\n   Match: ⚠️ MISMATCH | Expected: {expected_model}")
                elif expected_model and not loaded: print("\n   Match:  Belum ada model aktif")
                else: print("\n   Match: ⚪ Belum ada request LLM")
            except Exception as e: print(f"\n   ❌ llama-server error: {e}")
            print()
            continue
        
        if cmd == "/models":
            print("\n📋 Model registry:")
            try:
                import requests
                r = requests.get("http://127.0.0.1:8080/models", timeout=3)
                r.raise_for_status()
                data = r.json()
                models = data.get("data", [])
                if not models: print("   ⚠️ Tidak ada model terdeteksi.")
                else:
                    for m in models:
                        name = m.get("id", "?")
                        state = m.get("status", {}).get("value", "unknown")
                        label = "⚡ Instan" if "0.8B" in name else ("🎯 Default" if "3B" in name else "—")
                        print(f"   {state:10} {name:24} {label}")
            except Exception as e: print(f"   ❌ llama-server error: {e}")
            print()
            continue
        
        if cmd == "/set_write":
            parts = cmd.split()
            if len(parts) != 2:
                console.print("[yellow]/set_write <true|false> — // setuju terus// (global). /set_write:false // //blokir tulis/[/yellow]")
            else:
                val = parts[1].lower()
                if val in ("true", "1", "yes"):
                    from tools.file_manager import set_write_consent as sc
                    sc(True)
                elif val in ("false", "0", "no"):
                    from tools.file_manager import set_write_consent as sc
                    sc(False)
                else:
                    console.print("[yellow]⚠️  Nilai /set_write harus true atau false[/yellow]")
            continue
        
        if cmd.startswith("/load "):
            _lp = dispatcher.local
            model_id = user_input.strip()[6:].strip()
            if not model_id:
                print(f"   {YELLOW}⚠️ Gunakan: /load <nama_model>{R}")
                continue
            if model_id in active_models and getattr(_lp, "loaded_model", None) == model_id:
                print(f"   ℹ️ Model '{model_id}' sudah aktif.")
                continue
            print(f"   {CYAN}⏳ Loading {model_id}...{R}")
            try:
                import psutil
                ram_available = psutil.virtual_memory().available / (1024 * 1024)
                print(f"    RAM tersedia: {int(ram_available)}MB")
            except ImportError: pass
            # ⚠️ RAM-tight blocker disabled: models load on the 8080 router
            #    via mmap (virtual), so RAM preflight on this process is
            #    advisory only and must not block.
            # if not _lp.preflight(model_id):
            #     console.print(f"   [red]❌ Gagal load '{model_id}': RAM tidak cukup.[/red]")
            #     continue
            for _old in list(active_models):
                if _old != model_id:
                    console.print(f"   [dim]♻️ Coba auto-unload {_old}[/dim]")
                    if unload_aman(_lp, _old):
                        active_models.discard(_old)
                        try:
                            import time as _t, psutil as _ps
                            _sebelum = int(_ps.virtual_memory().available / (1024 * 1024))
                            for _i in range(10):
                                _t.sleep(1)
                                if int(_ps.virtual_memory().available / (1024 * 1024)) >= _sebelum + 300: break
                        except Exception: pass
                    else: console.print(f"   [yellow]⚠️ Provider nggak punya unload[/yellow]")
            if _lp.load_model(model_id):
                active_models.add(model_id)
                active_tier = None
                print(f"   {GREEN}✅ Model '{model_id}' loaded. Total aktif: {len(active_models)}{R}")
            else: print(f"   {RED}❌ Gagal load '{model_id}'.{R}")
            continue
        
        if cmd == "/unload" or cmd.startswith("/unload "):
            _lp = dispatcher.local
            model_id = user_input.strip()[8:].strip()
            if not model_id:
                if not active_models:
                    console.print("   [dim]⚪ Tidak ada model aktif.[/dim]")
                    continue
                for _old in list(active_models):
                    if unload_aman(_lp, _old):
                        active_models.discard(_old)
                        console.print(f"   [green]✅ {_old} di-unload.[/green]")
                    else: console.print(f"   [yellow]⚠️ {_old} gagal unload[/yellow]")
                console.print(f"   [green]🧹 Semua model di-unload.[/green]")
                continue
            if model_id not in active_models:
                print(f"   ⚠️ Model '{model_id}' tidak sedang aktif.")
                continue
            print(f"   {CYAN}Unloading {model_id}...{R}")
            if _lp.unload_model(model_id):
                active_models.discard(model_id)
                print(f"   {GREEN}✅ Model '{model_id}' di-unload.{R}")
            else: print(f"   {RED}❌ Gagal unload '{model_id}'.{R}")
            continue
        
        if cmd == "/clear":
            cleared = False
            for _nama in ("clear", "reset", "clear_history"):
                _fn = getattr(session, _nama, None)
                if callable(_fn):
                    try: _fn(); cleared = True; break
                    except Exception: pass
            if not cleared:
                try: session = Session(); cleared = True
                except Exception: pass
            console.print("[yellow]🗑 Sesi dibersihkan.[/yellow]" if cleared else "[red]❌ Gagal clear session[/red]")
            continue
        
        if cmd == "/status":
            local_ok = dispatcher.local_available()
            try:
                from tools import llm_online
                cloud_ok = any([bool(getattr(llm_online, "DASHSCOPE_KEY", None)), bool(getattr(llm_online, "GROQ_KEY", None)), bool(getattr(llm_online, "OR_KEY", None)), bool(getattr(llm_online, "GEMINI_KEY", None))])
            except Exception: cloud_ok = False
            t = _RichTable(box=_rich_box.SIMPLE_HEAD, show_header=False, padding=(0, 2))
            t.add_column(style="cyan"); t.add_column()
            t.add_row("Router", "OK")
            t.add_row("Local LLM", "OK" if local_ok else "OFF")
            t.add_row("Model aktif", ", ".join(sorted(active_models)) if active_models else "belum ada request")
            t.add_row("Memory", "OK")
            t.add_row("RAG", "OK")
            t.add_row("Cloud", ("ON" if cloud_ok else "OFF"))
            console.print(_RichPanel(t, title="[bold]⚙️ Mesin AI Status[/bold]", border_style="bright_blue"))
            continue
        
        llm_tier, llm_text = choose_llm_tier(user_input)
        route_text = llm_text if llm_text else user_input
        memory_context = ""; project_context = ""; rag_context = ""
        result = router.route(route_text)
        
        # Coba alias natural tool sebelum LLM
        natural = getattr(router, "route_natural_tool", lambda x: None)(route_text)
        if natural:
            result = natural
        
        if result.get("type") == "nav":
            answer = registry.execute("nav", {"text": user_input})
            print(f"[Nav Brain]: {answer}")
            session.add("user", user_input); session.add("assistant", str(answer))
            continue
        
        task = brain_router.choose(result)
        project_keywords = ("proyek mesin", "context proyek", "status proyek", "tujuan sekarang", "yang sudah selesai", "sudah selesai dalam proyek", "langkah berikutnya", "project context")
        if any(k in user_input.lower() for k in project_keywords): task = "project"
        
        if task in ["math", "file", "memory", "project", "termux", "shell", "web", "code", "tts", "stt", "plugin", "musik"]:
            if task == "memory" and result.get("data", {}).get("action") == "search":
                memory_result = registry.execute("memory", {**result.get("data", {}), "text": user_input})
                memory_context = "MEMORY RELEVAN PROYEK:\n" + "\n".join([f"{x['category']}.{x['key']}: {x['value']}" for x in memory_result])
                task = "llm"
            elif task == "project":
                project_result = registry.execute("project", {"text": user_input})
                project_context = "STATUS PROYEK TERKINI:\n" + project_result
                task = "llm"
            elif task == "file":
                # List folder tanpa lewat LLM
                if result.get("data", {}).get("action") == "list_dir":
                    try:
                        from tools.dir_manager import list_dir as _list_dir
                        answer = _list_dir(result.get("data", {}).get("path", ""))
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                    except Exception as e:
                        answer = f"[Error] Gagal membaca folder: {e}"
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                # Cari file by name/query tanpa lewat LLM
                if result.get("data", {}).get("action") == "find":
                    try:
                        from tools.file_manager import find_files as _find_files
                        answer = _find_files(result.get("data", {}).get("query", ""))
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                    except Exception as e:
                        answer = f"[Error] Gagal mencari file: {e}"
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                # Baca file isi tanpa lewat LLM
                if result.get("data", {}).get("action") == "read":
                    try:
                        from tools.file_manager import handle_file_action
                        answer = handle_file_action("read", result.get("data", {}).get("path", ""), line_spec=result.get("data", {}).get("line_spec"))
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                    except Exception as e:
                        answer = f"[Error] Gagal membaca file: {e}"
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                # Baca file untuk permintaan ringkasan/jelaskan dari router
                if result.get("data", {}).get("action") == "read_explain":
                    try:
                        from tools.file_manager import handle_file_action, read_file as _read_file
                        path = result.get("data", {}).get("path", "")
                        line_spec = result.get("data", {}).get("line_spec")
                        if not path or not os.path.exists(path):
                            found = find_files(path)
                            if found and not found.startswith("[Error]") and "\n" not in found:
                                path = found.splitlines()[0].strip()
                        file_content = handle_file_action("read", path, line_spec=line_spec)
                        if file_content and not file_content.startswith("[Error]"):
                            # For short files, return content directly to avoid LLM hallucination
                            lines = file_content.splitlines()
                            data_start = 1
                            if lines and lines[0].startswith("[File]"):
                                try:
                                    total = int(lines[0].split("(")[1].split(" ")[0])
                                except Exception:
                                    total = len(lines)
                                data_start = 1
                                if len(lines) > 1 and lines[1].startswith("[LineSpec]"):
                                    data_start = 2
                            actual_content = "\n".join(lines[data_start:]) if len(lines) > data_start else file_content
                            if len(actual_content.strip()) <= 2000:
                                answer = file_content
                                print(f" [File Brain]: {answer}")
                                session.add("user", user_input); session.add("assistant", str(answer))
                                continue
                            if len(file_content) > 2000:
                                file_content = file_content[:2000] + "\n\n... [file terpotong karena terlalu panjang] ..."
                            _file_explanation_context = file_content
                            task = "llm"
                        else:
                            answer = file_content or "[Error] Gagal membaca file."
                            print(f" [File Brain]: {answer}")
                            session.add("user", user_input); session.add("assistant", str(answer))
                            continue
                    except Exception as e:
                        answer = f"[Error] Gagal membaca file: {e}"
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                # Cek apakah ini permintaan "baca + jelaskan/ringkas/fungsi"
                explain_signals = [
                    "jelaskan", "jelasin", "ringkasan", "ringkaskan", "summary", "fungsi", "apa isi",
                    "toelang", "terangkan", "kepo", "kepoin",
                    "apa itu", "bagaimana", "tujuan", "perintah",
                ]
                if any(re.search(r'\b' + re.escape(k) + r'\b', user_input.lower()) for k in explain_signals):
                    # Baca dulu isi file, lalu kirim ke LLM untuk dijelaskan
                    try:
                        from tools.file_manager import handle_file_action
                        file_content = handle_file_action("read", result.get("data", {}).get("path", ""), line_spec=result.get("data", {}).get("line_spec"))
                        if file_content and not file_content.startswith("[Error]"):
                            # Truncate file content to fit context window
                            if len(file_content) > 2000:
                                file_content = file_content[:2000] + "\n\n... [file terpotong karena terlalu panjang] ..."
                            # Inject file content into the conversation
                            _file_explanation_context = file_content
                            task = "llm"
                        else:
                            answer = file_content or "[Error] Gagal membaca file."
                            print(f" [File Brain]: {answer}")
                            session.add("user", user_input); session.add("assistant", str(answer))
                            continue
                    except Exception as e:
                        answer = f"[Error] Gagal membaca file: {e}"
                        print(f" [File Brain]: {answer}")
                        session.add("user", user_input); session.add("assistant", str(answer))
                        continue
                else:
                    answer = registry.execute(task, {**result.get("data", {}), "text": route_text})
                    print(f" [{task} Brain]: {answer}")
                    session.add("user", user_input); session.add("assistant", str(answer))
                    continue
            else:
                answer = registry.execute(task, {**result.get("data", {}), "text": route_text})
                print(f" [{task} Brain]: {answer}")
                session.add("user", user_input); session.add("assistant", str(answer))
                continue
        
        if not project_context: project_context = project.build_context()
        if task == "rag":
            print(f"{DIM}🧪 RAG DEBUG AKTIF{R}")
            rag_context = registry.execute("rag", {"text": route_text})
        
        session.add("user", user_input)
        context_messages = session.get_messages()
        
        # Inject file content for explanation requests
        if task == "llm" and ("_file_explanation_context" in locals() or "_file_explanation_context" in dir()):
            try:
                _file_content = _file_explanation_context
                context_messages.append({
                    "role": "user",
                    "content": f"Baca dan jelaskan file berikut dalam 3 poin singkat. Jawab langsung sesuai isinya, jangan ngada-ada.\n\n{_file_content}"
                })
            except Exception:
                pass
        
        if task == "rag": mode = "rag"
        elif memory_context or project_context: mode = "project"
        else: mode = "normal"
        
        system_prompt = context_manager.build(mode, memory_context, project_context, rag_context, route_text)
        print(f"{DIM} ctx: project {len(project_context)} + web {len(locals().get('rag_context') or '')} karakter{R}")
        
        if llm_tier in ("instan", "default", "cloud"):
            active_tier = llm_tier
            if not active_models:
                model_map = {
                    "instan": "Qwen3.5-0.8B-Q4_0",
                    "default": "Qwen3.8-2B-Uncensored-Q4_K_M",
                    "cloud": "ONLINE",
                }
                first_model = model_map[llm_tier]
                active_models.add(first_model)
        
        if llm_tier == "cloud": print(f"   {DIM}🎚️ Tier: ☁️ ONLINE{R}")
        else: print(f"   {DIM}🎚️ Local tier: {llm_tier}{R}")
        
        with console.status("[bold green]🧠 Mesin berpikir…[/bold green]", spinner="dots"):
            answer = registry.execute("llm", {"messages": context_messages, "system_prompt": system_prompt, "rag_context": rag_context, "tier": llm_tier})
        
        if answer:
            _msgs = session.get_messages()
            _prev = ""
            for _m in reversed(_msgs):
                if _m.get("role") == "assistant":
                    _prev = str(_m.get("content", ""))
                    break
            if _prev.strip() and str(answer).strip() == _prev.strip() and len(_prev.strip()) > 40:
                console.print("[yellow]🔁 Jawaban sama persis dengan riwayat — sesi fosil. Ketik /clear.[/yellow]")
            if not str(answer).startswith("[Error]"):
                session.add("assistant", answer)
            render_rich_answer(rem_repetisi(answer), llm_tier)
            render_bar(active_models, active_tier)

if __name__ == "__main__":
    main()
