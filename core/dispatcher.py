from providers.local import LocalProvider
from tools.llm_online import ask_online
import socket
from tools.reset_memori import jalankan_reset
import datetime
import re
import os
from core.colors import CYAN, YELLOW, GREEN, RED, DIM, R

class Dispatcher:

    MAX_RAG_CHARS = 1500
    CERMIN_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cermin.txt"
    )

    def __init__(self, config):
        self.config = config
        self.local = LocalProvider(config)
        self.cermin_text = self.baca_cermin()
        self.last_found_file = None

    def baca_cermin(self):
        """Baca identitas diri dari cermin.txt. Kalau tidak ada, lanjut tanpa drama."""
        try:
            with open(self.CERMIN_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""

    def local_available(self):
        try:
            host = self.config["llm_local"].get("host", "localhost")
            port = self.config["llm_local"].get("port", 8080)
            sock = socket.create_connection((host, port), timeout=1)
            sock.close()
            return True
        except Exception:
            return False

    def cek_racun_berita(self, teks):
        """Cek apakah teks mengandung topik yang bikin stres."""
        try:
            saringan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saringan.txt")
            if not os.path.exists(saringan_file):
                saringan_file = "saringan.txt"
            with open(saringan_file, "r", encoding="utf-8") as f:
                kata_racun = f.read().lower().split(",")
            teks_lower = teks.lower()
            return any(kata.strip() in teks_lower for kata in kata_racun if kata.strip())
        except Exception:
            return False

    def ask(
        self,
        messages,
        rag_context="",
        system_prompt="",
        fast=False,
        tier=None
    ):
        # ===============================
        # RESET MEMORI: perintah /reset
        # ===============================
        try:
            teks_user = ""

            if messages:
                last = messages[-1]

                if isinstance(last, dict):
                    content = last.get("content", "")

                    # Kalau content berupa list, ambil bagian text saja
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                parts.append(str(part.get("text", "")))
                            elif isinstance(part, str):
                                parts.append(part)
                        teks_user = " ".join(parts)
                    else:
                        teks_user = str(content)

                else:
                    teks_user = str(last)

            if teks_user.strip().lower() == "/reset":
                print("[RESET] Perintah /reset diterima. Membersihkan memori...")
                hasil = jalankan_reset()
                for log in hasil:
                    print(f"[RESET] {log}")
                return "✅ Memori, cache, dan sesi percakapan sudah dibersihkan. Kita mulai dari awal ya."

            # 👇 TARUH SATPAM DI SINI, BANG 👇
            if self.cek_racun_berita(teks_user):
                return "Waduh Bang, topik ini kayaknya bikin stres deh."
            # 👆 SAMPAI SINI 👆

        except Exception as e:
            print(f"[RESET ERROR] {e}")

        # 📄 Penanganan khusus: "baris ke-N dari file X" — deterministik, tidak bergantung LLM
        try:
            low = teks_user.lower()
            # Cari file: "cari file X" / "cari X"
            if "cari" in low:
                fm = re.search(r"([\w\-]+\.[\w]+)", low)
                if fm:
                    fname = fm.group(1)
                    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    found = []
                    for root, dirs, files in os.walk(base):
                        if fname in files:
                            found.append(os.path.join(root, fname))
                    if found:
                        self.last_found_file = found[0]
                        return "Ditemukan:\n" + "\n".join(found)
            # Isi file: hanya jika ada nama file dengan ekstensi, atau kata "cermin"/"file"
            fm = re.search(r"([\w\-]+\.[\w]+)", low)
            has_file_word = "file" in low or "cermin" in low or "catatan" in low or "oprek" in low
            wants_search = "cari" in low
            content_intent = "isi" in low or "ringkas" in low or "baca" in low or "bacain" in low or "bacakan" in low or "tentang" in low
            if (not wants_search) and (fm or has_file_word or (self.last_found_file and content_intent)) and (content_intent or "file" in low or has_file_word):
                fname = fm.group(1) if fm else (os.path.basename(self.last_found_file) if self.last_found_file else "cermin.txt")
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                target = self.last_found_file if (not fm and self.last_found_file) else os.path.join(base, fname)
                if not os.path.exists(target):
                    for root, dirs, files in os.walk(base):
                        if fname in files:
                            target = os.path.join(root, fname)
                            break
                if target and os.path.exists(target):
                    try:
                        with open(target, encoding="utf-8") as f:
                            content = f.read()
                        return f"Isi {fname}:\n{content}"
                    except Exception as e:
                        return f"Gagal baca {fname}: {e}"
            m = re.search(r"(?:baris|nomer|nomor)\s+(\d+)", low)
            if m:
                nums = re.findall(r"(?:baris|nomer|nomor)\s+(\d+)", low)
                # cari nama file yang disebut (default cermin.txt)
                fname_match = re.search(r"([\w\-]+\.[\w]+)", low)
                fname = fname_match.group(1) if fname_match else "cermin.txt"
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                # cari file di tree
                target = None
                direct = os.path.join(base, fname)
                if os.path.exists(direct):
                    target = direct
                else:
                    for root, dirs, files in os.walk(base):
                        if fname in files:
                            target = os.path.join(root, fname)
                            break
                if target:
                    with open(target, encoding="utf-8") as f:
                        lines = f.read().splitlines()
                    results = []
                    for num in nums:
                        i = int(num)
                        if 1 <= i <= len(lines):
                            results.append(f"Baris {i}: \"{lines[i-1]}\"")
                    if results:
                        return " | ".join(results) + f"  (file: {fname})"
        except Exception as e:
            print(f"[FILE LINE ERROR] {e}")
        # cermin sudah dibaca di __init__ lewat self.cermin_text
        # (hindari duplikasi di full_system_prompt di bawah)

        if rag_context and len(rag_context) > self.MAX_RAG_CHARS:
            rag_context = rag_context[: self.MAX_RAG_CHARS] + "\n...[konteks dipotong agar muat]"

        # 📅 Tanggal hidup — mesin tahu hari ini tanggal berapa
        try:
            import datetime
            HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                     "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            now = datetime.datetime.now()
            tanggal = f"{HARI[now.weekday()]}, {now.day} {BULAN[now.month - 1]} {now.year}"
            system_prompt += f"\n\n📅 Hari ini: {tanggal}."
        except Exception:
            pass

       

        # 💉 BOOSTER MODEL KECIL: konteks web ditempel NEMPEL di pesan user
        if rag_context:
            print(f"   {DIM}📄 [Debug] Konteks web: {rag_context[:300]}...{R}")
        # ☁️ Cloud-only: jangan sentuh model lokal.
        if tier == "cloud":
            print(f"\n{CYAN}☁️ [Cloud] Routing langsung ke Online AI...{R}\n")
            try:
                return ask_online(messages=messages, context=rag_context, system_prompt=system_prompt)
            except TypeError:
                return ask_online(messages=messages, context=rag_context)

        provider, label, is_up = self.local, "🧠 LLM Lokal", self.local_available()

        # 🧠 IDENTITAS MODEL AKTIF
        loaded = getattr(provider, "loaded_model", None)
        if loaded:
            # /load manual menang — ini model yang beneran aktif
            active_model = loaded
            active_tier = tier or "manual"
        elif tier in getattr(provider, "MODELS", {}):
            active_model = provider.MODELS[tier]["model"]
            active_tier = tier
        else:
            active_model = getattr(provider, "model", "unknown")
            active_tier = tier or getattr(provider, "default_tier", "default")

        system_prompt += (
            "\n\n🤖 SEBUAH MESIN:\n"
            f"- Tier aktif: {active_tier}\n"
            f"- Model aktif: {active_model}.\n"
            "- Jawab langsung, jujur, dan singkat. Jangan mengarang.\n"
        )

        # 🌐 RAG WEB → SYSTEM PROMPT
        # Simpan rag_context ke system_prompt agar messages tetap utuh dan murni
        if rag_context:
            system_prompt += f"\n\n[KONTEKS WEB TERKINI]:\n{rag_context}"

        local_messages = [dict(m) for m in messages]
        print(f"   {CYAN}{label} menjawab...{R}")
        if len(messages) > 1:
            local_messages = _budget_messages(local_messages)

        full_system_prompt = ((system_prompt or "") + DISIPLIN)

        answer = None
        if is_up:
            try:
                answer = provider.chat(
                    messages=local_messages,
                    system_prompt=full_system_prompt,
                    tier=tier
                )
            except Exception as e:
                answer = None

            # 🍱 DIET v2: LocalProvider menelan error jadi None,
            # jadi diet dipicu oleh jawaban kosong, bukan exception.
            if not answer:
                print(f"   {YELLOW}⚠️ [{label}] Porsi penuh gagal — coba porsi diet...{R}")
                diet = [dict(m) for m in messages]
                try:
                    answer = provider.chat(
                        messages=_budget_messages(diet, 500),
                        system_prompt=full_system_prompt,
                        tier=tier
                    )
                except Exception:
                    answer = None
                if answer:
                    print(f"   {GREEN}✅ [{label}] Versi diet berhasil!{R}")

        else:
            print(f"\n{YELLOW}⚠️ {label} tidak aktif — lokal dilewati, tanpa selingkuh ke cloud.{R}\n")

        if answer:
            return answer

        # 🛑 RETRY MIKRO: Potong konteks jadi 600 char sebelum menyerah
        if not answer:
            print(f"   {YELLOW}⚠️ [{label}] Fallback diet gagal — coba versi mikro...{R}")
            mikro = [dict(m) for m in messages]
            for m in mikro:
                c = m.get("content", "") or ""
                if m.get("role") == "user" and "KONTEKS WEB TERKINI" in c:
                    parts = c.split("️ Aturan:")
                    if len(parts) > 1:
                        short_ctx = parts[0][:300] + "\n...[dipotong ekstrem]\n"
                        m["content"] = short_ctx + "⚖️ Aturan:" + parts[1]
            try:
                answer = provider.chat(
                    messages=_budget_messages(mikro, 500),
                    system_prompt=full_system_prompt,
                    tier=tier
                )
            except Exception:
                answer = None

        if answer:
            return answer

        return (
            "[Error] LLM lokal tidak menjawab (model belum termuat / server mati). "
            "Ketik /load NamaModel untuk memuat, atau /power pertanyaan untuk cloud."
        )


DISIPLIN = (
    "\n\nATURAN MULUT: kemampuan yang tertulis di cermin.\n"
    "Jika ditanya isi file, kamu WAJIB membaca file itu terlebih dahulu melalui sistem, "
    "bukan menebak isinya. Jika file tidak ada atau tidak bisa diakses, katakan jujur.\n"
)


def _budget_messages(msgs, limit=500):
    """Pangkas riwayat tertua agar prompt muat konteks server.
    Pesan terakhir (pembawa lampiran RAG) wajib selamat."""
    total = sum(len(m.get("content", "") or "") for m in msgs)
    if total <= limit:
        return msgs
    last = msgs[-1]
    keep = [last]
    budget = limit - len(last.get("content", "") or "")
    for m in reversed(msgs[:-1]):
        c = len(m.get("content", "") or "")
        if c <= budget:
            keep.append(m)
            budget -= c
        else:
            break
    keep.reverse()
    return keep
