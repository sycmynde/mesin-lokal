import sqlite3
import shutil
import sys
from pathlib import Path

# Tentukan path dasar
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"

# Pastikan BASE_DIR ada di sys.path agar bisa import modul project
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def cari_file_db(nama_file):
    """Mencari file DB secara otomatis jika path default tidak ditemukan."""
    target_default = DATA_DIR / "memory" / nama_file
    if target_default.exists():
        return target_default
        
    if (BASE_DIR / nama_file).exists():
        return BASE_DIR / nama_file
        
    # Cari rekursif di folder data
    hasil_cari = list(DATA_DIR.rglob(nama_file))
    if hasil_cari:
        return hasil_cari[0]
        
    return None

def bersihkan_database(db_path):
    if not db_path or not db_path.exists():
        return f"⚠️ DB tidak ditemukan: {db_path.name if db_path else 'Unknown'}"
        
    try:
        # timeout=10 agar aman jika DB sedang dipakai AI
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            cursor.execute(f"DELETE FROM {table_name};")
            
        conn.commit()
        
        try:
            cursor.execute("VACUUM;")
        except Exception:
            pass
            
        conn.close()
        return f"✅ DB berhasil dibersihkan: {db_path.name} (di {db_path.parent.name})"
        
    except sqlite3.OperationalError as e:
        return f"❌ DB dikunci proses lain: {db_path.name} - {e}"
    except Exception as e:
        return f"❌ Error pada {db_path.name}: {e}"

def bersihkan_folder(folder_path):
    if not folder_path.exists() or not folder_path.is_dir():
        return f"⚠️ Folder tidak ditemukan: {folder_path.name}"
        
    count = 0
    for item in folder_path.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
                count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                count += 1
        except Exception:
            pass
            
    return f"✅ Folder dibersihkan ({count} item): {folder_path.name}"

def reset_cache_gps():
    try:
        from tools import kalkulator
        kalkulator._last_location_cache = None
        kalkulator._last_location_time = 0
        return "✅ RAM cache GPS dibersihkan"
    except Exception as e:
        # Menampilkan detail error aslinya
        return f"⚠️ Gagal reset GPS: {type(e).__name__} - {e}"

def jalankan_reset():
    hasil = []
    
    # 1. Chat History
    hasil.append(bersihkan_database(DATA_DIR / "chat_history.db"))
    hasil.append(bersihkan_database(WEB_DIR / "chat_history.db"))
    
    # 2. Memory DB (Pencarian Otomatis)
    memory_db_path = cari_file_db("memory.db")
    hasil.append(bersihkan_database(memory_db_path))
    
    # 3. Folder
    hasil.append(bersihkan_folder(DATA_DIR / "cache"))
    hasil.append(bersihkan_folder(DATA_DIR / "sessions"))
    
    # 4. RAM Cache
    hasil.append(reset_cache_gps())
        
    return hasil

if __name__ == "__main__":
    print("🔄 Memulai proses reset memori...")
    for pesan in jalankan_reset():
        print(pesan)
    print("✨ Reset selesai!")