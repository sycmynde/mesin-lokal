import os


class ContextManager:

    def __init__(self, memory=None):
        self.memory = memory

    def _should_inject_memory(self, user_input):
        if not user_input:
            return False
        triggers = (
            "ingat", "lupa", 
        )
        return any(w in user_input.lower() for w in triggers)

    def _should_inject_project(self, user_input):
        if not user_input:
            return False
        triggers = (
            "proyek", "project", 
        )
        return any(w in user_input.lower() for w in triggers)

    def _is_file_query(self, user_input):
        if not user_input:
            return False
        low = user_input.lower()
        triggers = ("file", "isi", "ringkas", "baca", "cari", "cermin", "catatan", "oprek")
        return any(w in low for w in triggers)

    def build(
        self,
        mode="normal",
        memory_context="",
        project_context="",
        rag_context="",
        user_input=""
    ):
        # Pastikan path absolut ke folder core
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # folder root proyek, bukan core/
        cermin_path = os.path.join(current_dir, "cermin.txt")
        
        system_prompt = "Kamu adalah Mesin, AI lokal di Termux/Android. Jawab singkat, jujur, tanpa drama. Jangan mengarang isi file atau path."
        
        # Inject aturan cermin.txt HANYA jika user menanyakan file/isi
        if self._is_file_query(user_input):
            try:
                if os.path.exists(cermin_path):
                    with open(cermin_path, "r", encoding="utf-8") as f:
                        cermin_text = f.read().strip()
                    print(f"   ✅ [ContextManager] Berhasil baca cermin.txt ({len(cermin_text)} karakter)")
                    system_prompt = cermin_text
                else:
                    print(f"   ❌ [ContextManager] File cermin.txt TIDAK DITEMUKAN di: {cermin_path}")
            except Exception as e:
                print(f"   ❌ [ContextManager] GAGAL baca cermin.txt: {e}")

        # Inject memori jika perlu
        if self._should_inject_memory(user_input) and self.memory:
            relevant = self.memory.search_relevant(user_input, limit=5)
            if relevant:
                memory_text = "\n".join(
                    f"{item.get('category', 'memori')}.{item.get('key', 'item')}: {item.get('value', '')}"
                    for item in relevant
                )
                system_prompt += f"\n\n[KONTEKS MEMORI TERKAIT]:\n{memory_text}"

        # Inject proyek jika perlu
        if self._should_inject_project(user_input) and project_context:
            system_prompt += f"\n\n[KONTEKS PROYEK]:\n{project_context}"

        return system_prompt
