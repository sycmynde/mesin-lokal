import sqlite3
import os
from datetime import datetime

DB_PATH = "data/chat_history.db"

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  role TEXT,
                  content TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
              (session_id, role, content))
    conn.commit()
    conn.close()

def get_recent_history(session_id, limit=5):
    """Ambil hanya N pesan terakhir agar LLM tetap cepat"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
              (session_id, limit))
    rows = c.fetchall()
    conn.close()
    # Balik urutan agar dari lama ke baru
    return [{"role": row['role'], "content": row['content']} for row in reversed(rows)]

def get_all_sessions():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM messages ORDER BY timestamp DESC")
    sessions = [row[0] for row in c.fetchall()]
    conn.close()
    return sessions
