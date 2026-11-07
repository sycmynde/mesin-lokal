class Session:

    MAX_MESSAGES = 10

    def __init__(self):
        self.messages = []

    def add(self, role, content):
        self.messages.append({
            "role": role,
            "content": content
        })

        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]

    def get_messages(self):
        return list(self.messages)

    def clear(self):
        self.messages = []

# Alias Kompatibilitas untuk main.py

# --- Wrapper Functions untuk Kompatibilitas dengan main.py ---
# --- Wrapper Functions untuk Kompatibilitas dengan main.py ---
import json
import os

SESSION_DIR = "data/sessions"

def save_message_to_session(session_id, message_dict):
    """Menyimpan pesan ke file JSON"""
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
    
    file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
    
    # Load data lama jika ada
    history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                history = json.load(f)
        except:
            history = []

    # Tambah pesan baru
    history.append(message_dict)

    # Simpan kembali
    with open(file_path, 'w') as f:
        json.dump(history, f, indent=2)

def load_session_history(session_id):
    """Memuat riwayat dari file JSON dan masukkan ke class Session"""
    file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
    s = Session() # Buat objek Session baru
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                history = json.load(f)
            # Masukkan setiap pesan ke dalam objek Session menggunakan method .add()
            for msg in history:
                s.add(msg['role'], msg['content'])
        except:
            pass # Jika file rusak, mulai dari kosong
            
    return s.get_messages() # Kembalikan dalam format list yang dimengerti main.py
