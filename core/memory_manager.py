import json
import os
import sqlite3
import time

def cek_saringan(teks):
    """Cek apakah teks mengandung kata sampah dari saringan.txt"""
    try:
        # Trik sakti: Cari file saringan.txt di folder yang SAMA dengan file ini (folder core/)
        core_dir = os.path.dirname(os.path.abspath(__file__))
        path_saringan = os.path.join(core_dir, "saringan.txt")
        
        with open(path_saringan, "r", encoding="utf-8") as f:
            kata_sampah = f.read().lower().split(",")
        
        teks_lower = teks.lower()
        # Kalau ada SATU SAJA kata sampah yang ketemu, langsung tolak!
        return any(kata.strip() in teks_lower for kata in kata_sampah if kata.strip())
    except Exception:
        return False # Kalau file nggak ketemu, anggap aman aja (fallback)

MEMORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)
DB_PATH = os.path.join(MEMORY_DIR, "memory.db")


def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


def _get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS identity (
        key TEXT PRIMARY KEY, value TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT, value TEXT, time TEXT, source TEXT DEFAULT 'user')""")
    return conn


def load_memory():
    """Backward compat: return dict seperti schema lama."""
    conn = _get_conn()
    c = conn.cursor()
    mem = {"identity": {}, "facts": [], "preferences": [], "notes": []}

    c.execute("SELECT key, value FROM identity")
    for k, v in c.fetchall():
        mem["identity"][k] = v

    for cat in ["facts", "preferences", "notes", "jurnal"]:
        c.execute("SELECT value, time FROM memories WHERE category=?", (cat,))
        for val, t in c.fetchall():
            mem[cat].append({"value": val, "time": t})

    conn.close()
    return mem


def save_memory(mem):
    """Backward compat: tulis dari dict ke DB."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM identity")
    c.execute("DELETE FROM memories")

    for k, v in mem.get("identity", {}).items():
        c.execute("INSERT OR REPLACE INTO identity (key,value) VALUES (?,?)", (k, v))

    for cat in ["facts", "preferences", "notes", "jurnal"]:
        for item in mem.get(cat, []):
            if isinstance(item, dict):
                val, t = item.get("value", ""), item.get("time", "")
            else:
                val, t = str(item), ""
            if val:
                c.execute("INSERT INTO memories (category,value,time) VALUES (?,?,?)",
                          (cat, val, t))
    conn.commit()
    conn.close()



def _normalize_perspective(value):
    """Ubah sudut pandang orang pertama -> orang ketiga.
    Robust: handle spasi bervariasi + typo umum."""
    import re as _re
    v = value

    # 1. Koreksi typo umum dulu
    for typo, fix in [("pavorit", "favorit"), ("faporit", "favorit"), ("favotit", "favorit")]:
        v = v.replace(typo, fix)

    # 2. Frasa kepemilikan -ku (nempel ATAU terpisah spasi)
    patterns = [
        (r"\bfavorit\s*ku\b",   "favorit pengguna"),
        (r"\bkesukaan\s*ku\b",  "kesukaan pengguna"),
        (r"\bkucing\s*ku\b",    "kucing pengguna"),
        (r"\bnama\s*ku\b",      "nama pengguna"),
        (r"\bmakanan\s*ku\b",   "makanan pengguna"),
        (r"\bhobi\s*ku\b",      "hobi pengguna"),
        (r"\bwarna\s*ku\b",     "warna pengguna"),
        (r"\brumah\s*ku\b",     "rumah pengguna"),
        (r"\bpunya\s*ku\b",     "punya pengguna"),
        (r"\b(?:aku|saya)\b",    "pengguna"),
        # Orang kedua → Mesin (AI)
        (r"\bkamu\b",            "Mesin"),
        (r"\bkau\b",             "Mesin"),
    ]
    # Normalisasi kata informal
    v = v.replace(" ga ", " tidak ").replace(" gak ", " tidak ")

    for pat, rep in patterns:
        v = _re.sub(pat, rep, v, flags=_re.IGNORECASE)

    return v



def sanity_check(value):
    """Cek kewajaran memori. Return (is_sane, warning_msg)."""
    v = value.lower()
    warnings = []

    # ── Pola absurd: benda mati / makanan jadi pelaku aksi ──
    absurd_subjects = [
        "pisang", "apel", "meja", "kursi", "batu", "komputer",
        "hp", "kulkas", "sepatu", "bantal", "sendok", "garpu",
        "kambing", "ayam", "bebek", "semut", "nyamuk", "kaki meja",
    ]
    actions = ["makan", "minum", "suka", "cinta", "benci", "marah"]

    words = v.split()
    if len(words) >= 3:
        subject = words[0]
        has_action = any(a in v for a in actions)
        if subject in absurd_subjects and has_action:
            warnings.append(f"🍌 Subjek '{subject}' kok bisa begitu?")

    # ── Pola absurd: user makan benda bukan makanan ──
    non_food = ["komputer", "hp", "batu", "meja", "kursi", "sepatu", "buku", "kaki meja", "kaca", "besi", "plastik"]
    if "makan" in v:
        for nf in non_food:
            if nf in v and "tidak" not in v and "bukan" not in v:
                warnings.append(f"💻 Makan {nf}? Yakin perut kuat?")
                break

    # ── Prompt Injection / Jailbreak Guard ──
    injection_triggers = [
        "ignore previous", "abaikan instruksi", "abaikan aturan",
        "system prompt", "kamu sekarang adalah dan", "jailbreak",
        "bypass", "hapus memori", "delete from", "drop table"
    ]
    if any(trig in v for trig in injection_triggers):
        warnings.append("🛡️ Percobaan manipulasi sistem atau injeksi prompt ditolak.")

    # ── Pola terlalu panjang (>200 char) ──
    if len(value) > 200:
        warnings.append("📝 Catatan panjang banget, yakin ini ingatan bukan novel?")

    if warnings:
        return False, " ".join(warnings)
    return True, ""


def add_memory(category, key, value):
    # Saring kata sampah/racun sebelum disimpan
    if cek_saringan(str(value)):
        print(f"   🛡️ [MEMORY] Ditolak: Teks mengandung kata saringan (sampah website).")
        return False

    conn = _get_conn()
    c = conn.cursor()

    # Deteksi nama
    low = value.lower()
    if any(k in low for k in ["namaku", "nama saya", "nama aku"]):
        for prefix in ["namaku adalah", "namaku", "nama saya", "nama aku"]:
            if prefix in low:
                name = low.split(prefix, 1)[1].strip().strip(".!?")
                c.execute("INSERT OR REPLACE INTO identity (key,value) VALUES (?,?)",
                          ("user_name", name.title()))
                conn.commit(); conn.close()
                return f"identity:{name.title()}"

    if category == "identity":
        c.execute("INSERT OR REPLACE INTO identity (key,value) VALUES (?,?)", (key, value))
    else:
        c.execute("SELECT value FROM memories WHERE category=?", (category,))
        existing = {r[0].lower() for r in c.fetchall()}
        if value.lower() in existing:
            conn.close()
            return "duplicate"
        value = _normalize_perspective(value)
        # Cegah duplikat
        c.execute("SELECT COUNT(*) FROM memories WHERE value=?", (value,))
        if c.fetchone()[0] > 0:
            conn.close()
            return f"🧠 Sudah pernah kuingat itu: \"{value}\""
        c.execute("INSERT INTO memories (category,value,time,source) VALUES (?,?,?,?)",
                  (category, value, time.strftime("%Y-%m-%d %H:%M"), "user"))

    conn.commit(); conn.close()
    return True


def get_memory_summary():
    """Ringkasan memory buat di-inject ke system prompt."""
    conn = _get_conn()
    c = conn.cursor()

    # ── Identitas ──
    c.execute("SELECT key, value FROM identity")
    identity = dict(c.fetchall())

    lines = []
    lines.append("IDENTITAS:")
    if identity.get("ai_name"):
        lines.append(f"- Kamu (AI) bernama: {identity['ai_name']}")
    if identity.get("user_name"):
        lines.append(f"- Pengguna bernama: {identity['user_name']}")
    if identity.get("ai_personality"):
        lines.append(f"- Kepribadianmu: {identity['ai_personality']}")

    # ── Pisahkan fakta user vs AI ──
    user_facts = []
    ai_facts = []
    for cat in ["facts", "preferences", "notes", "jurnal"]:
        c.execute("SELECT value FROM memories WHERE category=?", (cat,))
        for (val,) in c.fetchall():
            if val:
                vl = val.lower()
                if vl.startswith("mesin ") or vl.startswith("ai ") or "ai bernama" in vl:
                    ai_facts.append(f"- {val}")
                else:
                    user_facts.append(f"- {val.replace('Pengguna ','Dia ',1)}")

    if user_facts:
        lines.append("")
        lines.append("FAKTA TENTANG PENGGUNA:")
        lines.extend(user_facts)

    if ai_facts:
        lines.append("")
        lines.append("FAKTA TENTANG KAMU (AI):")
        lines.extend(ai_facts)

    conn.close()

    # Dedup
    seen = set()
    unique_lines = []
    for p in lines:
        if p not in seen:
            seen.add(p)
            unique_lines.append(p)

    if len(unique_lines) <= 1:
        return ""
    return "\n".join(unique_lines)


def search_memory(query, limit=5):
    """Cari ingatan relevan. Return list string buat RAG."""
    conn = _get_conn()
    c = conn.cursor()
    q = _normalize_perspective(query.lower())
    results = []

    c.execute("SELECT category, value FROM memories")
    for cat, val in c.fetchall():
        vl = val.lower()
        overlap = set(q.split()) & set(vl.split())
        if overlap or q in vl or vl in q:
            score = len(overlap) / max(len(q.split()), 1)
            results.append({"cat": cat, "val": val, "score": score})

    c.execute("SELECT key, value FROM identity")
    for k, v in c.fetchall():
        if q in v.lower() or k.lower() in q:
            results.append({"cat": "identity", "val": f"{k}: {v}", "score": 0.5})

    conn.close()
    results.sort(key=lambda x: x["score"], reverse=True)
    return [f"[{r['cat'].upper()}] {r['val']}" for r in results[:limit]]


def get_all_memory():
    return load_memory()


def clear_memory():
    conn = _get_conn()
    conn.execute("DELETE FROM identity")
    conn.execute("DELETE FROM memories")
    conn.commit(); conn.close()

def add_web_knowledge(topic, fact, source_url=""):
    """
    Menyimpan fakta dari web ke dalam memori agar tidak perlu search ulang.
    """
    if cek_saringan(str(fact)):
        return "rejected"

    conn = _get_conn()
    c = conn.cursor()
    
    # Cek apakah fakta ini sudah ada (hindari duplikasi)
    check_str = f"%{fact[:50]}%"
    c.execute("SELECT COUNT(*) FROM memories WHERE value LIKE ? AND source='web_rag'", (check_str,))
    if c.fetchone()[0] > 0:
        conn.close()
        return "duplicate"

    # Simpan dengan kategori 'facts' dan source 'web_rag'
    normalized_fact = _normalize_perspective(fact)
    c.execute("INSERT INTO memories (category, value, time, source) VALUES (?, ?, ?, ?)",
              ("facts", normalized_fact, time.strftime("%Y-%m-%d %H:%M"), "web_rag"))
    
    conn.commit()
    conn.close()
    return True


# ── [PATCH RAG-TTL] pencarian ber-metadata + lupa ────────────────────
def search_memory_meta(query, limit=5):
    """Seperti search_memory, tapi return dict dengan time & source."""
    conn = _get_conn()
    c = conn.cursor()
    q = _normalize_perspective(query.lower())
    results = []
    c.execute("SELECT id, category, value, time, source FROM memories")
    for rid, cat, val, t, src in c.fetchall():
        vl = val.lower()
        overlap = set(q.split()) & set(vl.split())
        if overlap or q in vl or vl in q:
            score = len(overlap) / max(len(q.split()), 1)
            results.append({"cat": cat, "val": val, "score": score,
                            "time": t or "", "source": src or "user", "id": rid})
    c.execute("SELECT key, value FROM identity")
    for k, v in c.fetchall():
        if q in v.lower() or k.lower() in q:
            results.append({"cat": "identity", "val": f"{k}: {v}", "score": 0.5,
                            "time": "", "source": "identity", "id": None})
    conn.close()
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def forget_memory(rid):
    """Hapus satu baris memori berdasarkan id."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE id=?", (rid,))
    conn.commit()
    conn.close()
