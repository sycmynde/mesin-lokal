import sqlite3
import threading
import os
import time
import datetime
import platform
import subprocess
import json
import re

from core.config import load_config
from core.router import Router
from core.brain_router import BrainRouter
from core.dispatcher import Dispatcher
from core.brain_registry import BrainRegistry
from core.session import Session
from core.memory import Memory
from core.project import ProjectState
from core.context_manager import ContextManager

from brains.math_brain import MathBrain
from brains.file_brain import FileBrain
from brains.memory_brain import MemoryBrain
from brains.llm_brain import LLMBrain
from brains.rag_brain import RAGBrain
from brains.project_brain import ProjectBrain
from brains.nav_brain import NavBrain
from agents.a2a_brain import A2ABrain
from brains.code_brain import CodeBrain
from brains.shell_brain import ShellBrain
from brains.stt_brain import STTBrain
from brains.tts_brain import TTSBrain
from brains.termux_brain import TermuxBrain
from brains.musik_brain import MusikBrain
from brains.plugin_brain import PluginBrain
from brains.web_brain import WebBrain

try:
    from main import choose_llm_tier
except Exception:
    def choose_llm_tier(text):
        return "default", text

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")
TERMUX_HOME = "/data/data/com.termux/files/home"
MODELS_DIR = os.path.join(TERMUX_HOME, "models")

LOCATION_KEYWORDS = [
    "di mana", "dimana", "lokasi", "koordinat", "gps",
    "jarak", "posisi", "ke mana", "kemana",
    "dari sini", "ke sini", "berada",
    "aku lagi di", "saya di", "keberadaan"
]

def get_system_context(include_gps=False):
    now = datetime.datetime.now()
    current_time = now.strftime("%A, %d %B %Y, %H:%M WIB")
    location_str = ""
    if include_gps:
        try:
            result = subprocess.run(['termux-location'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                loc_data = json.loads(result.stdout)
                lat = loc_data.get('latitude', 'N/A')
                lon = loc_data.get('longitude', 'N/A')
                location_str = f"GPS: {lat}, {lon}"
            else:
                location_str = "GPS: Izin ditolak/Error"
        except Exception:
            location_str = "GPS: Tidak tersedia"
    
    device_info = f"Device: {platform.machine()} (Android/Termux)"
    context = f"[SYSTEM CONTEXT]\nCurrent Date & Time: {current_time}\n"
    if location_str:
        context += f"{location_str}\n"
    context += device_info
    return context

class WebAppCore:
    def __init__(self):
        config = load_config()
        self.router = Router()
        self.brain_router = BrainRouter()
        self.dispatcher = Dispatcher(config)
        self.session = Session()
        try:
            _conn = sqlite3.connect(DB_PATH)
            _rows = _conn.execute("SELECT role, message FROM chats ORDER BY id DESC LIMIT 20").fetchall()
            _conn.close()
            for _r, _m in reversed(_rows):
                self.session.add(_r, _m)
        except Exception:
            pass
        self.memory = Memory()
        self.project = ProjectState()
        self.registry = BrainRegistry()
        self.context_manager = ContextManager()
        self.tier = "default"

        self.registry.register("math", MathBrain())
        self.registry.register("file", FileBrain())
        self.registry.register("memory", MemoryBrain())
        self.registry.register("llm", LLMBrain(self.dispatcher))
        self.registry.register("rag", RAGBrain())
        self.registry.register("project", ProjectBrain(self.project))
        self.registry.register("nav", NavBrain())
        self.registry.register("a2a", A2ABrain(self.dispatcher))
        self.registry.register("code", CodeBrain())
        self.registry.register("shell", ShellBrain())
        self.registry.register("stt", STTBrain())
        self.registry.register("tts", TTSBrain())
        self.registry.register("termux", TermuxBrain())
        self.registry.register("musik", MusikBrain())
        self.registry.register("plugin", PluginBrain())
        self.registry.register("web", WebBrain())

        self._init_db()
        self._prewarm_gps()
        self._autoload_default()

    def _prewarm_gps(self):
        def _warmup():
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                from tools.kalkulator import get_current_location
                result = get_current_location()
                if result and "Gagal" not in str(result) and "Error" not in str(result):
                    print(f"   🌡️ [GPS Pre-warm] Sukses: {result}")
                else:
                    print(f"   ⚠️ [GPS Pre-warm] Belum tersedia: {result}")
            except Exception as e:
                print(f"   ⚠️ [GPS Pre-warm] Error: {e}")
        t = threading.Thread(target=_warmup, daemon=True)
        t.start()
        print("   🌡️ [GPS Pre-warm] Memulai pemanasan GPS di background...")

    def _local_provider(self):
        for name in ("provider", "local_provider", "local"):
            obj = getattr(self.dispatcher, name, None)
            if obj is not None and hasattr(obj, "loaded_model"):
                return obj
        for val in vars(self.dispatcher).values():
            if hasattr(val, "loaded_model"):
                return val
        return None

    def set_tier(self, tier):
        self.tier = tier

    def status(self):
        prov = self._local_provider()
        model = "unknown"
        if prov is not None:
            model = getattr(prov, "loaded_model", None) or getattr(prov, "model", "unknown")
        models = []
        try:
            mdir = "/data/data/com.termux/files/home/models"
            if not os.path.isdir(mdir):
                mdir = MODELS_DIR
            models = sorted(f[:-5] for f in os.listdir(mdir) if f.endswith(".gguf") and not f.startswith("mmproj"))
        except Exception:
            pass
        return {"tier": self.tier, "model": model, "models": models}

    def load_model(self, model_id):
        prov = self._local_provider()
        if prov is None:
            return False, "Provider lokal tidak ditemukan"
        fn = getattr(prov, "load", None) or getattr(prov, "load_model", None)
        if fn is None:
            return False, "Metode load tidak ditemukan"
        try:
            fn(model_id)
            return True, model_id
        except Exception as e:
            return False, str(e)

    def _autoload_default(self):
        """Auto-load model default di background — dengan retry."""
        prov = self._local_provider()
        if prov is None:
            print("   ⚠️ Provider lokal tidak ditemukan")
            return
        
        import re
        cfg_m = getattr(prov, "get_config", lambda t: {"model": "Qwen3.8-2B-Uncensored-Q4_K_M"})("default").get("model", "Qwen3.8-2B-Uncensored-Q4_K_M")
        default_model = re.sub(r'\.gguf$', '', cfg_m)
        
        def _load_with_retry():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    import requests
                    base = prov.api_url.split("/v1/")[0]
                    # Coba endpoint load model jika tersedia
                    r = requests.post(f"{base}/models/load", json={"model": default_model}, timeout=10)
                    if r.status_code == 200 and r.json().get("success", False):
                        prov.loaded_model = default_model
                        print(f"   ✅ [Web] Auto-load {default_model} sukses (percobaan {attempt+1})")
                        return True
                    elif r.status_code == 404:
                        # Endpoint /models/load tidak ada di server ini, anggap model sudah active
                        print(f"   ℹ️ [Web] Server tidak support /models/load, skip auto-load")
                        prov.loaded_model = default_model
                        return True
                    else:
                        print(f"   ⚠️ [Web] Auto-load gagal: {r.status_code} {r.text[:100]}")
                except Exception as e:
                    print(f"   ⚠️ [Web] Auto-load error: {e}")
                
                import time
                time.sleep(2)
            
            print(f"   ❌ [Web] Auto-load {default_model} gagal setelah {max_retries} percobaan")
            return False
        
        threading.Thread(target=_load_with_retry, daemon=True).start()
        print(f"   🧠 [Web] Mencoba auto-load {default_model} di background...")

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp REAL NOT NULL
        )""")
        conn.commit()
        conn.close()

    def _save_chat(self, role, message):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chats (role, message, timestamp) VALUES (?, ?, ?)", (role, message, time.time()))
        conn.commit()
        conn.close()

    def get_history(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT role, message, timestamp FROM chats ORDER BY id ASC").fetchall()
        conn.close()
        history = []
        for r, m, ts in rows:
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            history.append({"role": r, "message": m, "time": time_str})
        return history

    def clear_history(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM chats")
        conn.commit()
        conn.close()
        self.session = Session()

    def ask(self, text):
        tier, clean_text = choose_llm_tier(text)
        if clean_text == text:
            tier = self.tier
        if tier == "online":
            tier = "cloud"
        route_text = clean_text if clean_text else text

        # /load NamaModel — parity dengan terminal
        if text.strip().lower().startswith("/load"):
            parts = text.strip().split(maxsplit=1)
            if len(parts) > 1:
                ok_load, info = self.load_model(parts[1].strip())
                answer = f"✅ Model '{parts[1].strip()}' loaded." if ok_load else f"❌ Gagal load: {info}"
            else:
                answer = "❌ Format: /load NamaModel"
            self._save_chat("user", text)
            self._save_chat("assistant", answer)
            return answer

        # /dokter & /periksa — pemulihan mandiri & diagnostik
        if text.strip().lower().startswith(("/dokter", "/periksa")):
            from tools.dokter import diagnosa_sistem
            auto_fix = "fix" in text.lower() or "--fix" in text.lower()
            hasil = diagnosa_sistem(auto_fix=auto_fix)
            ram = hasil["ram"]
            stg = hasil["storage"]
            bat = hasil.get("baterai")
            status_lines = [
                f"🩺 **Laporan Dokter Mesin** ({'Auto-Repair' if auto_fix else 'Diagnosa Rutin'}):",
                f"• **RAM**: {ram.get('used_mb', '?')} MB / {ram.get('total_mb', '?')} MB ({ram.get('used_pct', 0):.0f}%) — {ram.get('status', 'OK')}",
                f"• **Storage**: Sisa {stg.get('free_gb', '?')} GB ({stg.get('status', 'OK')})",
            ]
            if bat:
                status_lines.append(f"• **Baterai/Suhu**: {bat['persen']}% | {bat['suhu']} ({bat['kondisi']})")
            for srv_n, srv_s in hasil["layanan"].items():
                status_lines.append(f"• **{srv_n}**: {srv_s}")
            for db_n, db_s in hasil["database"].items():
                status_lines.append(f"• **Database {db_n}**: {db_s}")
            if hasil["tindakan"]:
                status_lines.append("\n**Tindakan Pemulihan Berhasil Dilakukan:**")
                for act in hasil["tindakan"]:
                    status_lines.append(f"✅ {act}")
            if not hasil["masalah"] and not hasil["broken_code"]:
                status_lines.append("\n✨ *Seluruh sistem dalam kondisi sehat dan prima!*")
            else:
                status_lines.append(f"\n⚠️ Perhatian: Ditemukan {len(hasil['masalah']) + len(hasil['broken_code'])} catatan.")
            answer = "\n".join(status_lines)
            self._save_chat("user", text)
            self._save_chat("assistant", answer)
            return answer

        # /aqi & /cuaca — cek kualitas udara
        if text.strip().lower() in ("/aqi", "/cuaca", "cek aqi", "cek cuaca"):
            from tools.aqi_checker import cek_aqi_lokal
            data_aqi = cek_aqi_lokal()
            if data_aqi and str(data_aqi.get("aqi", "?")) != "?":
                answer = f"{data_aqi.get('emoji', '🌬️')} **Kualitas Udara (AQI)**: {data_aqi.get('aqi')} ({data_aqi.get('kategori')})\n• **Rekomendasi**: {data_aqi.get('saran')}\n• **Koordinat**: {data_aqi.get('lat')}, {data_aqi.get('lon')}"
            else:
                answer = "⚠️ Tidak dapat mengambil data AQI saat ini."
            self._save_chat("user", text)
            self._save_chat("assistant", answer)
            return answer

        result = self.router.route(route_text)
        
        # Navigasi offline — tangani langsung, AI tidak disentuh
        if result.get("type") == "nav":
            answer = str(self.registry.execute("nav", {"text": text}))
            self.session.add("user", text)
            self.session.add("assistant", answer)
            self._save_chat("user", text)
            self._save_chat("assistant", answer)
            return answer

        task = self.brain_router.choose(result)
        project_keywords = (
            "proyek mesin", "context proyek", "status proyek",
            "tujuan sekarang", "yang sudah selesai",
            "sudah selesai dalam proyek", "langkah berikutnya",
            "project context",
        )
        if any(k in text.lower() for k in project_keywords):
            task = "project"

        need_gps = any(kw in text.lower() for kw in LOCATION_KEYWORDS)

        # Brain langsung (math, file, memory)
        memory_context = ""
        if task == "memory" and result.get("data", {}).get("action") == "search":
            memory_result = self.registry.execute(
                "memory", {**result.get("data", {}), "text": text}
            )
            memory_context = "MEMORY RELEVAN PROYEK:\n" + "\n".join(
                [f"{x['category']}.{x['key']}: {x['value']}" for x in memory_result]
            )
            task = "llm"
        elif task in ("math", "file", "memory"):
            if task == "file":
                explain_signals = [
                    "jelaskan", "jelasin", "ringkasan", "ringkaskan", "summary", "fungsi", "apa isi",
                    "toelang", "terangkan", "kepo", "kepoin",
                    "apa itu", "bagaimana", "tujuan", "perintah",
                ]
                if any(re.search(r'\b' + re.escape(k) + r'\b', text.lower()) for k in explain_signals):
                    try:
                        from tools.file_manager import handle_file_action
                        file_content = handle_file_action("read", result.get("data", {}).get("path", ""), line_spec=result.get("data", {}).get("line_spec"))
                        if file_content and not file_content.startswith("[Error]"):
                            if len(file_content) > 2000:
                                file_content = file_content[:2000] + "\n\n... [file terpotong karena terlalu panjang] ..."
                            explanation_prompt = f"Baca dan jelaskan file berikut dalam 2 kalimat singkat. Jangan keluar dari format JSON.\n\n{file_content}"
                            task = "llm"
                            route_text = explanation_prompt
                        else:
                            answer = file_content or "[Error] Gagal membaca file."
                            self.session.add("user", text)
                            self.session.add("assistant", answer)
                            self._save_chat("user", text)
                            self._save_chat("assistant", answer)
                            return answer
                    except Exception as e:
                        answer = f"[Error] Gagal membaca file: {e}"
                        self.session.add("user", text)
                        self.session.add("assistant", answer)
                        self._save_chat("user", text)
                        self._save_chat("assistant", answer)
                        return answer
            data = result.get("data", {"text": route_text})
            if task != "llm":
                brain_result = self.registry.execute(task, data)
                answer = str(brain_result)
                self.session.add("user", text)
                self.session.add("assistant", answer)
                self._save_chat("user", text)
                self._save_chat("assistant", answer)
                return answer

        # Handler untuk brain langsung: shell, code, termux, tts, stt, musik, plugin, web
        if task in ("shell", "code", "termux", "tts", "stt", "musik", "plugin", "web"):
            data = result.get("data", {"text": route_text})
            if not data:
                data = {"text": route_text}
            brain_result = self.registry.execute(task, data)
            answer = str(brain_result)
            self.session.add("user", text)
            self.session.add("assistant", answer)
            self._save_chat("user", text)
            self._save_chat("assistant", answer)
            return answer

        project_context = ""
        if task == "project":
            project_result = self.registry.execute("project", {"text": text})
            project_context = str(project_result)
            task = "llm"

        rag_context = ""
        if task == "rag":
            rag_result = self.registry.execute("rag", {"text": text})
            rag_context = str(rag_result) if rag_result else ""
            task = "llm"

        if not project_context:
            project_context = self.project.build_context()

        # System context: waktu + GPS (kalau perlu)
        system_context = get_system_context(include_gps=need_gps)

        self.session.add("user", text)
        context_messages = self.session.get_messages()
        
        if task == "rag":
            mode = "rag"
        elif memory_context or project_context:
            mode = "project"
        else:
            mode = "normal"

        system_prompt = self.context_manager.build(
            mode=mode,
            memory_context=memory_context,
            project_context=project_context,
            rag_context=rag_context,
            user_input=text
        )

        final_system_prompt = f"{system_context}\n\n{system_prompt}"

        # === JAMINAN MODEL TER-LOAD SEBELUM LLM DIPANGGIL ===
        prov = self._local_provider()
        if prov and tier != "cloud" and not getattr(prov, "loaded_model", None):
            # Ambil nama default, lalu HAPUS .gguf biar sesuai aturan "nama aja"
            default_m = getattr(prov, "get_config", lambda t: {"model": "Qwen3.5-2B-Q4_K_M"})("default").get("model", "Qwen3.5-2B-Q4_K_M")
            clean_model = re.sub(r'\.gguf$', '', default_m)
        
            print(f"   🔄 [Web] Model belum loaded, memaksa load: {clean_model}...")
            self.load_model(clean_model)
            import time; time.sleep(2)  # Beri waktu 2 detik biar llama-server benar-benar siap
        # ========================================================

        answer = self.registry.execute(
            "llm",
            {
                "messages": context_messages,
                "system_prompt": final_system_prompt,
                "rag_context": rag_context,
                "tier": tier
            }
        )
        answer = str(answer)

        self.session.add("assistant", answer)
        self._save_chat("user", text)
        self._save_chat("assistant", answer)
        return answer