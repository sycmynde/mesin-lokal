from core.memory_manager import add_memory, get_all_memory, get_memory_summary, search_memory, sanity_check


class MemoryBrain:

    def run(self, data):
        action = data.get("action", "")

        # ── SIMPAN ──
        if action == "remember":
            category = data.get("category", "facts")
            key = data.get("key", "")
            value = data.get("value", "")

            if not value:
                return "Mau ingat apa? Kasih tahu aku ya."

            # Cek kewajaran dulu — TEGAS: halu ditolak, bukan cuma warning
            is_sane, warning = sanity_check(value)
            if not is_sane:
                return f"🤨 {warning} Yang bener aja... nggak kusimpen itu. 😄"

            result = add_memory(category, key, value)

            if isinstance(result, str) and result.startswith("identity:"):
                name = result.split(":", 1)[1]
                return f"🧠 Siap! Aku ingat namamu: **{name}**. Senang berkenalan! 🤝"

            return f"🧠 Oke, sudah kuingat: *\"{value}\""

        # ── RECALL ──
        if action == "recall":
            query = data.get("query", "")

            if query:
                # Cari yang relevan aja → CEPAT, tanpa LLM
                results = search_memory(query)
                if results:
                    answers = []
                    for r in results:
                        # Hapus prefix kategori [PREFERENCES] dll
                        text = r.split("] ", 1)[-1] if "] " in r else r
                        # Sudut pandang: "pengguna" → "kamu"
                        text = text.replace("pengguna", "kamu")
                        text = text.replace("Pengguna", "Kamu")
                        text = text.replace("Mesin", "aku")
                        answers.append(text)
                    return "🧠 " + "\n".join(answers)
                return "🧠 Hmm, aku belum ingat tentang itu. Coba bilang:\n• `ingat ...`"

            # Dump semua ingatan
            summary = get_memory_summary()
            summary = summary.replace("Data tentang pengguna (bukan tentang kamu):\n", "")
            if not summary:
                return "Aku belum punya ingatan apa-apa. Coba bilang:\n• `ingat namaku ...`\n• `ingat aku suka ...`"
            return f"🧠 Ini yang kuingat tentang kamu:\n\n{summary}"

        return "Perintah memory tidak dikenali."
