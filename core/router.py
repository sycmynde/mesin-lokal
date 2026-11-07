from tools.file_manager import extract_path_from_text
import re
import os
import json


class Router:

    PATTERNS_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "router_patterns.json"
    )

    def __init__(self):
        self.learned_patterns = self._load_patterns()

    def _load_patterns(self):
        """Muat kata-kata yang udah pernah diajarin dari memory."""
        try:
            with open(self.PATTERNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("rag_triggers", [])
        except Exception:
            return []

    def _save_patterns(self):
        try:
            os.makedirs(os.path.dirname(self.PATTERNS_FILE), exist_ok=True)
            with open(self.PATTERNS_FILE, "w", encoding="utf-8") as f:
                json.dump({"rag_triggers": self.learned_patterns}, f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   ⚠️ Gagal simpan pola router: {e}")

    def learn_pattern(self, phrase):
        """Ajarin kata/frasa baru → simpen ke memory router."""
        import datetime
        phrase = phrase.lower().strip()
        if not phrase:
            return "empty"
        if any(p.get("pattern") == phrase for p in self.learned_patterns):
            return "duplicate"
        self.learned_patterns.append({
            "pattern": phrase,
            "learned": datetime.date.today().isoformat()
        })
        self._save_patterns()
        return "saved"

    def forget_pattern(self, phrase):
        """Hapus kata yang pernah diajarin."""
        phrase = phrase.lower().strip()
        before = len(self.learned_patterns)
        self.learned_patterns = [p for p in self.learned_patterns
                                 if p.get("pattern") != phrase]
        if len(self.learned_patterns) < before:
            self._save_patterns()
            return "forgotten"
        return "not_found"

    def is_math_query(self, text):
        return bool(
            re.search(
                r'(?<![\w.])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*[\+\-\*\/xX×]\s*[-+]?(?:\d+(?:\.\d+)?|\.\d+))+',
                text
            )
        )

    def is_system_command(self, text):
        t = text.lower().strip()

        # Deteksi jarak & perbandingan jarak
        if "jarak" in t and ("ke" in t or "dari" in t):
            return True
        if any(k in t for k in ["lebih dekat", "lebih jauh", "paling dekat", "paling jauh", "dekat mana", "jauh mana"]):
            return True

        # Deteksi lokasi/GPS (dengan dan tanpa spasi)
        location_keywords = [
            "gps", "koordinat", "lokasi",
            "dimana saya", "di mana saya",
            "dimana aku", "di mana aku",
            "dimana sekarang", "di mana sekarang",
            "posisi saya", "posisi aku",
            "aku di mana", "saya di mana",
            "lagi di mana", "sedang di mana",
            # 🆕 Reverse geocoding keywords
            "di daerah mana", "daerah mana",
            "nama daerah", "nama tempat",
            "di mana ini", "ini di mana",
            "daerah apa", "ini daerah",
            "saya di daerah", "aku di daerah",
            "saya ada di", "aku ada di",
        ]
        return any(k in t for k in location_keywords)
    def detect_file_action(self, text):
        """Deteksi aksi file/folder dengan extract_path yang lebih pintar."""
        import re
        t = text.lower()
        path, line_spec = extract_path_from_text(text)
        if not path:
            return None
        # Jika path adalah folder, anggap aksi list_dir
        if os.path.isdir(os.path.expanduser(path)):
            return {'action': 'list_dir', 'path': path}
        action = None
        if re.search(r'\b(?:baca|tampilkan|lihat|read|open|cari file|cari)\b', t):
            action = 'read'
        elif re.search(r'\b(?:simpan ke|buat|catat di|tulis ke|write|save)\b', t):
            action = 'write'
        # Kalau permintaan analisis file, tetap anggap read agar
        # logic penjelasan di main.py/web bisa membaca isinya.
        elif re.search(r'\b(?:jelaskan|ringkas|fungsi|apa isi|toelang|terangkan|kepo|kepoin|tujuan|perintah)\b', t):
            action = 'read'
        if not action:
            return None
        result = {'action': action, 'path': path}
        if action == 'read' and line_spec:
            result['line_spec'] = line_spec
        elif action == 'write':
            idx = text.find(path)
            if idx >= 0:
                result['content'] = text[idx + len(path):].strip()
            else:
                result['content'] = ''
        return result


    def detect_memory_action(self, text):
        t = text.lower()
        # Normalisasi singkatan + varian ejaan
        _ab = {"yg":"yang","gk":"nggak","ga":"nggak","gak":"nggak",
               "dgn":"dengan","utk":"untuk","sy":"saya","aq":"aku",
               "km":"kamu","kmu":"kamu","gw":"aku","gue":"aku",
               "inget":"ingat","ingt":"ingat"}
        t = " ".join(_ab.get(w, w) for w in t.split())

        # ── INGAT / INGET ──
        if t.startswith("ingat ") or t.startswith("inget "):
            prefix_len = 6
            # Ekstrak dari TEKS ASLI (preserve case), deteksi pakai lowercase
            content_orig = text[prefix_len:].strip()
            content_low = content_orig.lower()

            # "ingat ga/nggak/kah..." = PERTANYAAN
            question_words = ["nggak", "ga", "gak", "tidak", "kah", "apa"]
            first_word = content_low.split()[0] if content_low.split() else ""
            if first_word in question_words:
                return {"action": "recall", "query": text}

            # Buang filler di AWAL kalimat (case-insensitive check, preserve original)
            fillers = ["yah","ya","dong","oke","ok","please","tolong",
                       "nih","juga","ini","itu","deh","sih"]
            words = content_orig.split()
            while words and words[0].lower() in fillers:
                words.pop(0)
            # Buang filler yang nyelip di TENGAH (cuma kata sambung lemah)
            mid_fillers = {"juga","nih","deh","sih","ya"}
            words = [w for w in words if w.lower() not in mid_fillers]
            content = " ".join(words).strip()

            low = content.lower()
            if low.startswith("proyek"):
                return {"action": "remember", "category": "projects",
                        "key": "utama", "value": content[7:].strip()}
            if any(k in low for k in ["preferensi","suka","kesukaan","favorit"]):
                return {"action": "remember", "category": "preferences",
                        "key": "favorit", "value": content}
            return {"action": "remember", "category": "facts",
                    "key": "catatan", "value": content}

        # ── RECALL EKSPLISIT ──
        recall_triggers = [
            "apa yang kamu ingat", "kamu ingat", "ingatkah",
            "coba ingat", "masih ingat", "ingat nggak",
            "apa yang kamu tau", "kamu tau tentang aku",
            "apa aja yang kamu ingat", "sebutkan ingatanmu",
            "ingatan tentang aku", "kamu masih ingat",
        ]
        if any(s in t for s in recall_triggers):
            # Buang trigger + filler → sisakan inti pertanyaan
            _q = t
            for _s in recall_triggers:
                _q = _q.replace(_s, " ")
            _filler = ["soal", "tentang", "mengenai", "yang", "aku", "saya",
                       "kamu", "mesin", "dong", "ga", "gak", "nggak", "kah",
                       "coba", "masih", "tolong", "apa", "aja", "saja", "nih",
                       "itu", "ya", "dan", "atau", "sama"]
            _kata = [w for w in _q.replace("?", " ").replace("!", " ")
                        .replace(".", " ").replace(",", " ").split()
                     if w not in _filler]
            _q = " ".join(_kata)
            if _q:
                return {"action": "recall", "query": _q}
            return {"action": "recall"}

        # ── RECALL IMPLISIT ──
        is_question = "?" in text or t.startswith("apa ") or t.startswith("siapa ")
        memory_topics = [
            "favorit", "kesukaan", "suka", "nama kucing",
            "makanan", "warna", "hobi", "nama saya", "namaku",
        ]
        self_refs = ["ku", "saya", "aku", "kamu"]
        has_topic = any(k in t for k in memory_topics)
        has_self = any(r in t for r in self_refs)
        if is_question and has_topic and has_self:
            return {"action": "recall", "query": text}

        return None

    def is_web_query(self, text):
        t = text.lower().strip()
        signals = [
            "cari web", "cari informasi", "search", "googling",
            "info terbaru", "berita hari ini", "terkini",
            "cari tahu", "carikan info", "browse",
        ]
        return any(k in t for k in signals)

    def is_code_query(self, text):
        t = text.lower().strip()
        signals = [
            "jalankan python", "run python", "execute code",
            "kode python", "code python", "py_run", "py_eval",
            "tulis kode", "buat kode", "generate code",
        ]
        return any(k in t for k in signals)

    def is_termux_query(self, text):
        t = text.lower().strip()
        signals = [
            "baterai", "clipboard", "kontak", "call log",
            "aplikasi apa", "info hp", "status hp",
            "brightness", "cahaya layar", "fingerprint",
            "termux ", "hp ku",
        ]
        return any(k in t for k in signals)

    def is_shell_query(self, text):
        t = text.lower().strip()
        signals = [
            "jalankan ", "eksekusi ", "run ", "execute ",
            "ls ", "cat ", "pwd", "shell ", "terminal ",
            "cek folder", "cek file",
            "lihat folder", "lihat file",
            "list folder", "list file",
        ]
        return any(k in t for k in signals)

    def is_tts_query(self, text):
        t = text.lower().strip()
        signals = [
            "ucapkan", "katakan", "bicara", "speak",
            "tts", "suara ai", "ai bicara",
        ]
        return any(k in t for k in signals)

    def is_stt_query(self, text):
        t = text.lower().strip()
        signals = [
            "dengar", "rekam suara", "speech to text",
            "stt", "what did i say", "transkrip",
        ]
        return any(k in t for k in signals)

    def is_plugin_query(self, text):
        t = text.lower().strip()
        signals = [
            "plugin", "daftar plugin", "list plugin",
            "skill", "daftar skill", "modul tambahan",
        ]
        return any(k in t for k in signals)

    def is_musik_query(self, text):
        t = text.lower().strip()
        signals = [
            "playlist", "putar playlist", "musik", "lagu",
            "gothic only", "hiphop only", "olahraga mix",
            "scan music", "list playlist", "stop", "play ",
        ]
        return any(k in t for k in signals)

    def is_project_query(self, text):
        t = text.lower()
        keywords = ["lanjutkan proyek", "lanjut proyek", "status proyek", "perkembangan proyek", "proyek saya"]
        return any(k in t for k in keywords)

    def is_rag_query(self, text):
        t = text.lower()

        # 🎓 Cek dulu kata yang UDAH DIAJARIN (dari memory)
        if any(p.get("pattern", "") in t for p in self.learned_patterns):
            return True

        # ── SINYAL KUAT: pasti butuh web ──
        strong_signals = [
           # "berita", "hari ini", "terkini", "update terbaru",
          #  "versi terbaru", "rilis terbaru", "perkembangan",
          #  "harga saham", "hasil pertandingan", "skor",
           # "siapa presiden", "siapa menteri", "siapa gubernur",
          #  "siapa walikota", "siapa bupati", "siapa camat",
            "carikan", "cari info", "cari informasi", "informasi tentang", "info tentang", "search",
        ]
        if any(k in t for k in strong_signals):
            return True

        # ── SINYAL LEMAH: mungkin butuh web, tapi cek dulu ──
        weak_signals = ["terbaru", "update", "rilis"]
        has_weak = any(k in t for k in weak_signals)

        # ── PENYARING: jangan RAG kalau ini pertanyaan pribadi/umum ──
        personal_markers = [
            "namamu", "nama kamu", "nama mu",
            "kamu siapa", "siapa kamu", "siapa kamu",
            "apa itu cinta", "apa itu hidup",
            "cara kerja", "bagaimana cara",
            "jelaskan tentang", "jelaskan cara",
            "for loop", "while loop", "fungsi",
            "di mana kamu", "dimana kamu",
        ]
        is_personal = any(k in t for k in personal_markers)

        if is_personal:
            return False

        # ── Istilah teknis yang memang perlu definisi/penjelasan ──
        # RAG dalam proyek Mesin = Retrieval-Augmented Generation.
        technical_entities = [
            "rag", "llm", "llama.cpp", "gguf",
            "embedding", "vector database", "vector db",
            "retrieval", "machine learning", "artificial intelligence",
        ]
        if "apa itu" in t and any(e in t for e in technical_entities):
            return True

        # ── "siapa" dan "apa itu" hanya RAG kalau ada konteks publik ──
        public_entities = [
         #   "presiden", "menteri", "gubernur", "walikota",
          #  "bupati", "camat", "artis", "penyanyi", "pemain",
         #   "tokoh", "pemimpin", "ceo", "founder", "pendiri",
           # "perusahaan", "negara", "kota", "partai",
        ]
        if "siapa" in t and not any(e in t for e in public_entities):
            return False

        if "apa itu" in t and not any(e in t for e in public_entities):
            return False

        if has_weak:
            return True

        return False

    def is_nav_command(self, text):
        """Deteksi perintah navigasi/lokasi (ditangani MathBrain)."""
        t = text.lower().strip()
        nav_keywords = [
            "jangkar", "tujuan",
            "di mana", "dimana", "kita di mana",
            "jarak ke titik awal", "jarak dari titik awal",
            "berapa jauh dari awal", "berapa jauh lagi",
            "jarak tujuan", "jarak ke tujuan",
            "status nav", "status navigasi",
            "mulai perjalanan", "mulai trip",
            "start perjalanan", "start trip",
            "stop perjalanan", "stop trip",
            "berhenti perjalanan", "selesai perjalanan",
            "status perjalanan", "status trip",
            "reset perjalanan", "reset trip",
            "total perjalanan", "hitung total perjalanan",
            "berapa total perjalanan", "jarak total perjalanan",
            "total jarak perjalanan", "sudah berapa km perjalanan",
            "sudah berapa kilometer perjalanan",
            "reset perjalanan", "reset total perjalanan",
            "hapus total perjalanan", "nolkan perjalanan",
            "sisa berapa",
        ]
        if t == "gps" or "gps" in t:
            return True
        return any(k in t for k in nav_keywords)

    def route(self, text):
        # PRIORITAS 0: Navigasi/Lokasi (ditangani MathBrain)
        if self.is_nav_command(text):
            return {
                "type": "math",
                "confidence": 1.0,
                "data": {"text": text}
            }

        # PRIORITAS 1: Perintah Sistem/GPS/Jarak
        if self.is_system_command(text):
            return {
                "type": "math",
                "confidence": 1.0,
                "data": {"text": text}
            }

        # PRIORITAS 2: Matematika
        if self.is_math_query(text):
            return {"type": "math", "confidence": 1.0}

        # PRIORITAS 3: File
        file_action = self.detect_file_action(text)
        if file_action:
            return {"type": "file", "confidence": 0.95, "data": file_action}

        # PRIORITAS 4: Memory
        memory_action = self.detect_memory_action(text)
        if memory_action:
            return {"type": "memory", "confidence": 0.95, "data": memory_action}

        # PRIORITAS 5: Project
        #if self.is_project_query(text):
            #return {"type": "project", "confidence": 0.9}

        # PRIORITAS 6: RAG
        if self.is_rag_query(text):
            return {"type": "rag", "confidence": 0.8}

        # PRIORITAS 7: Web search
        if self.is_web_query(text):
            return {"type": "web", "confidence": 0.7}

        # PRIORITAS 8: Code execution
        if self.is_code_query(text):
            return {"type": "code", "confidence": 0.7}

        # PRIORITAS 9: Termux / sistem
        if self.is_termux_query(text):
            return {"type": "termux", "confidence": 0.7}

        # PRIORITAS 10: Shell execution
        if self.is_shell_query(text):
            return {
                "type": "shell",
                "confidence": 0.6,
                "data": {"tool": "shell", "args": {"command": text}},
            }

        # PRIORITAS 11: TTS
        if self.is_tts_query(text):
            # Extract teks setelah kata trigger
            t = text.strip()
            for trigger in ["ucapkan", "katakan", "bicara", "speak", "tts", "suara ai", "ai bicara"]:
                if t.lower().startswith(trigger):
                    t = t[len(trigger):].strip()
                    break
            return {
                "type": "tts",
                "confidence": 0.8,
                "data": {"tool": "tts_speak", "args": {"text": t}}
            }

        # PRIORITAS 12: STT
        if self.is_stt_query(text):
            return {
                "type": "stt",
                "confidence": 0.8,
                "data": {"tool": "stt_listen", "args": {"timeout": 10}}
            }

        # PRIORITAS 13: Plugin
        if self.is_plugin_query(text):
            t = text.strip()
            if any(k in t.lower() for k in ["daftar plugin", "list plugin", "daftar skill", "list skill"]):
                return {
                    "type": "plugin",
                    "confidence": 0.8,
                    "data": {"tool": "list_plugins", "args": {}}
                }
            # Try parse "plugin call <tool> <json_args>"
            m = re.match(r'plugin\s+call\s+(\S+)(?:\s+(.*))?', t, re.I)
            if m:
                tool_name = m.group(1)
                args_text = (m.group(2) or "").strip()
                args = {}
                if args_text:
                    try:
                        args = json.loads(args_text)
                    except Exception:
                        args = {"raw": args_text}
                return {
                    "type": "plugin",
                    "confidence": 0.9,
                    "data": {"tool": "plugin_call", "args": {"plugin_tool": tool_name, "plugin_args": args}}
                }
            return {
                "type": "plugin",
                "confidence": 0.6,
                "data": {"tool": "plugin_call", "args": {"plugin_tool": "", "plugin_args": {}}}
            }

        # PRIORITAS 14: Musik / Playlist + query by title/artist
        if self.is_musik_query(text):
            t = text.strip()
            tl = t.lower()
            if any(k in tl for k in ["stop", "stop musik", "matikan musik", "hentikan musik"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "stop_music", "args": {}}}
            if any(k in tl for k in ["next", "next track", "lagu selanjutnya"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "next_track", "args": {}}}
            if any(k in tl for k in ["prev", "previous", "lagu sebelumnya"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "prev_track", "args": {}}}
            if any(k in tl for k in ["pause", "jeda"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "toggle_pause", "args": {}}}
            if any(k in tl for k in ["shuffle", "acak"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "shuffle_on", "args": {}}}
            if any(k in tl for k in ["repeat", "ulang"]):
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "repeat_on", "args": {}}}
            if any(k in tl for k in ["list", "list playlist", "daftar lagu", "daftar playlist"]):
                return {"type": "musik", "confidence": 0.8, "data": {"tool": "list_playlists", "args": {}}}
            if tl in ["musik", "play musik", "putar musik", "play"]:
                return {"type": "musik", "confidence": 0.7, "data": {"tool": "play_query", "args": {"query": ""}}}
            if tl.startswith("musik ") or tl.startswith("play "):
                query = t[6:].strip() if tl.startswith("musik ") else t[5:].strip()
                if query:
                    return {"type": "musik", "confidence": 0.9, "data": {"tool": "play_query", "args": {"query": query}}}
                return {"type": "musik", "confidence": 0.7, "data": {"tool": "play_query", "args": {"query": ""}}}
            return {"type": "musik", "confidence": 0.7, "data": {"tool": "play_query", "args": {"query": t}}}

        # DEFAULT: LLM
        return {"type": "llm", "confidence": 0.5}

    def route_natural_tool(self, text):
        """Alias natural ke tool call langsung."""
        t = text.strip()
        tl = t.lower()

        # musik control: exact/short forms only
        musik_controls = {
            "stop musik": "stop_music",
            "hentikan musik": "stop_music",
            "matikan musik": "stop_music",
            "next": "next_track",
            "prev": "prev_track",
            "pause": "toggle_pause",
            "musik": "_musik_query",
        }
        if tl in musik_controls:
            tool = musik_controls[tl]
            if tool == "_musik_query":
                return {"type": "musik", "confidence": 0.9, "data": self.route(text)["data"]}
            return {"type": "musik", "confidence": 0.95, "data": {"tool": tool, "args": {}}}

        # musik query with keyword
        if tl.startswith("musik ") or tl.startswith("play "):
            query = t[6:].strip() if tl.startswith("musik ") else t[5:].strip()
            # natural controls inside musik/play prefix
            ql = query.lower()
            if ql in ["stop", "stop musik", "hentikan musik", "matikan musik"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "stop_music", "args": {}}}
            if ql in ["next", "next track", "lagu selanjutnya"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "next_track", "args": {}}}
            if ql in ["prev", "previous", "lagu sebelumnya"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "prev_track", "args": {}}}
            if ql in ["pause", "jeda"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "toggle_pause", "args": {}}}
            if ql in ["shuffle", "acak"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "shuffle_on", "args": {}}}
            if ql in ["repeat", "ulang"]:
                return {"type": "musik", "confidence": 0.95, "data": {"tool": "repeat_on", "args": {}}}
            if ql in ["list", "list playlist", "daftar lagu", "daftar playlist", "playlist"]:
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "list_playlists", "args": {}}}
            if ql in ["folder", "isi folder", "scan", "scan music", "scan musik", "daftar file"]:
                return {"type": "musik", "confidence": 0.9, "data": {"tool": "scan_music", "args": {}}}
            return {"type": "musik", "confidence": 0.9, "data": {"tool": "play_query", "args": {"query": query}}}

        # exact tool words that match tool names
        if tl in ["aqi", "waktu", "jam", "tanggal", "gps", "lokasi", "baterai"]:
            tool_map = {
                "aqi": "aqi",
                "waktu": "waktu",
                "jam": "waktu",
                "tanggal": "waktu",
                "gps": "gps_now",
                "lokasi": "gps_now",
                "baterai": "baterai",
            }
            return {"type": "tool", "confidence": 0.95, "data": {"tool": tool_map[tl], "args": {}}}

        # file musik search by title/artist
        if tl.startswith("cari file musik ") or tl.startswith("musik "):
            query = t.split(" ", 3)[-1].strip() if tl.startswith("cari file musik ") else t[6:].strip()
            return {"type": "musik", "confidence": 0.9, "data": {"tool": "play_query", "args": {"query": query}}}
        # file search disabled: biarkan LLM menangani (model kecil di HP)
        pass

        # baca/tulis file alias
        file_read_signals = ["baca ", "bacs ", "bca ", "bac ", "tampilkan ", "lihat ", "read ", "open "]
        file_write_signals = ["tulis ", "tls ", "simpan ", "save ", "write ", "catat "]
        for sig in file_read_signals:
            if tl.startswith(sig):
                path = t[len(sig):].strip()
                return {"type": "file", "confidence": 0.95, "data": {"action": "read", "path": path}}
        for sig in file_write_signals:
            if tl.startswith(sig):
                path = t[len(sig):].strip()
                return {"type": "file", "confidence": 0.95, "data": {"action": "write", "path": path, "content": ""}}

        # ringkasan/jelaskan file: route ke read + explain
        explain_prefixes = [
            "ringkasan isi dari ", "ringkaskan ", "ringkasan ", "jelaskan ", "jelasin ",
            "summarize ", "summary ", "fungsi ", "apa isi ", "toelang ", "terangkan ",
            "kepoin ", "kepo ", "apa itu ", "bagaimana ", "tujuan ", "perintah ",
            "kasih saya ringkasan ", "kasih ringkasan ", "beri saya ringkasan ", "beri ringkasan ",
        ]
        matched = None
        for sig in explain_prefixes:
            if tl.startswith(sig):
                matched = sig
                break
        if matched is None and tl.startswith("apa "):
            rest = t[4:].strip()
            for sig in explain_prefixes:
                if rest.startswith(sig):
                    matched = sig
                    break
        if matched is not None:
            if tl.startswith("apa "):
                rest = text[4:].strip()
                matched = None
                for sig in explain_prefixes:
                    if rest.startswith(sig):
                        matched = sig
                        break
                if matched is not None:
                    rest = rest[len(matched):].strip()
            else:
                rest = t[len(matched):].strip()
            for stop in ["isi ", "isi", "dari ", "dari", "file ", "file"]:
                if rest.startswith(stop):
                    rest = rest[len(stop):].strip()
            path = rest
            line_spec = None
            m = re.search(r'^(?:no\.?|baris|line)\s*(\d+)', path, re.IGNORECASE)
            if m:
                line_spec = {"type": "line", "n": int(m.group(1))}
                path = re.sub(r'^(?:no\.?|baris|line)\s*\d+\s*(?:dari\s+|of\s+)?', '', path, flags=re.IGNORECASE).strip()
            if path:
                return {"type": "file", "confidence": 0.9, "data": {"action": "read_explain", "path": path, "line_spec": line_spec}}

        # gambar/video prefix handled via router so they don't collide with musik
        if tl.startswith("gambar ") or tl.startswith("draw ") or tl.startswith("buat gambar "):
            prompt = t.split(" ", 2)[-1].strip() if " " in t else ""
            return {"type": "tool", "confidence": 0.9, "data": {"tool": "gambar", "args": {"name": "gambar.sh", "prompt": prompt}}}
        if tl.startswith("video ") or tl.startswith("rekam "):
            prompt = t.split(" ", 1)[1].strip() if " " in t else ""
            return {"type": "tool", "confidence": 0.9, "data": {"tool": "video", "args": {"name": "video.sh", "prompt": prompt}}}

        return None
