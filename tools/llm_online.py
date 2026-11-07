import os
import re
import requests
import json

# ═══════════ KEYS ═══════════
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
DASHSCOPE_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# ═══════════ KANDIDAT MODEL (auto-fallback kalau 404) ═══════════
def _build_candidates():
    global GROQ_MODELS, OR_MODELS, GEMINI_MODELS, DASHSCOPE_MODEL
    GROQ_MODELS = [m for m in [os.getenv("GROQ_MODEL", ""), "qwen3-32b"] if m]
    OR_MODELS = [m for m in [os.getenv("OPENROUTER_MODEL", ""), "openrouter/free", "qwen/qwen3.8-27b:free"] if m]
    GEMINI_MODELS = [m for m in [os.getenv("GEMINI_MODEL", ""), "gemini-3.6-flash", "gemini-3.5-flash-lite"] if m]
    DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

_build_candidates()

def clean_answer(text):
    """Buang blok <think>...</think> bocoran model reasoning."""
    if not text:
        return text
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "<think>" in t:
        t = t.split("<think>", 1)[0]
    return t.strip()

def _safe(res, name, kind="openai"):
    """Parse jawaban; kalau error, cetak status + body asli."""
    try:
        data = res.json()
    except Exception:
        print(f"   ❌ {name} HTTP {res.status_code} bukan JSON: {res.text[:150]}")
        return None
    if kind == "openai" and data.get("choices"):
        return clean_answer(data["choices"][0]["message"]["content"])
    if kind == "gemini" and data.get("candidates"):
        return clean_answer(data["candidates"][0]["content"]["parts"][0]["text"])
    print(f"   ❌ {name} HTTP {res.status_code}: {res.text[:250]}")
    return None

def chat_dashscope(messages, model=None):
    if not DASHSCOPE_KEY: return None
    model = model or DASHSCOPE_MODEL
    try:
        res = requests.post(
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {DASHSCOPE_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.5},
            timeout=20
        )
        return _safe(res, "QwenCloud")
    except Exception as e:
        print(f"   ❌ DashScope error: {type(e).__name__}: {e}")
        return None

def chat_groq(messages, model=None):
    if not GROQ_KEY: return None
    cands = [model] if model else GROQ_MODELS
    for m in cands:
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": m, "messages": messages, "temperature": 0.7},
                timeout=15
            )
            ans = _safe(res, f"Groq[{m}]")
            if ans: return ans
        except Exception as e:
            print(f"   ❌ Groq[{m}] error: {type(e).__name__}: {e}")
    return None

def chat_openrouter(messages, model=None):
    if not OR_KEY: return None
    cands = [model] if model else OR_MODELS
    for m in cands:
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "http://localhost", "X-Title": "MesinAI"},
                json={"model": m, "messages": messages, "temperature": 0.7},
                timeout=20
            )
            ans = _safe(res, f"OpenRouter[{m}]")
            if ans: return ans
        except Exception as e:
            print(f"   ❌ OpenRouter[{m}] error: {type(e).__name__}: {e}")
    return None

def chat_gemini(messages, model=None):
    if not GEMINI_KEY: return None
    cands = [model] if model else GEMINI_MODELS
    gemini_msgs = []
    for msg in messages:
        role = "model" if msg['role'] == 'assistant' else "user"
        gemini_msgs.append({"role": role, "parts": [{"text": msg['content']}]})
    for m in cands:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_KEY}"
            res = requests.post(url, json={"contents": gemini_msgs}, timeout=25)
            ans = _safe(res, f"Gemini[{m}]", kind="gemini")
            if ans: return ans
        except Exception as e:
            print(f"   ❌ Gemini[{m}] error: {type(e).__name__}: {e}")
    return None

def ask_online(messages, context="", system_prompt=""):
    print("\n🌐 [Otak Online] Menghubungkan ke Cloud AI...")
    print(f"   🔍 [DEBUG] Panjang context diterima: {len(context)} karakter")

    # Jangan modifikasi session messages asli saat fallback cloud.
    cloud_messages = [dict(m) for m in messages]

    # 🪞 Identitas Mesin ikut ke cloud — biar gak ngaku ChatGPT lagi
    if system_prompt:
        cloud_messages.insert(0, {"role": "system", "content": system_prompt})

    if context:
        system_msg = {
            "role": "system",
            "content": f"""Kamu adalah asisten cerdas. Gunakan KONTEKS berikut sebagai sumber utama fakta terkini.
Jika konteks menyebutkan hasil pemilu atau pelantikan terbaru, gunakan itu sebagai jawaban faktual.
Jangan menjawab 'Informasi tidak tersedia' jika kamu bisa menyimpulkan jawabannya dari konteks yang ada.

=== KONTEKS SUMBER TERKINI ===
{context}
=== AKHIR KONTEKS ===
"""
        }
        cloud_messages.insert(0, system_msg)

    if DASHSCOPE_KEY:
        print("   ☁️ Mencoba Qwen Cloud (DashScope)...")
        answer = chat_dashscope(cloud_messages)
        if answer: return f"[Via Qwen Cloud]\n{answer}"

    if GROQ_KEY:
        print("   ⚡ Mencoba Qwen via Groq...")
        answer = chat_groq(cloud_messages)
        if answer: return f"[Via Groq]\n{answer}"

    if OR_KEY:
        print("   🚀 Mencoba Qwen via OpenRouter...")
        answer = chat_openrouter(cloud_messages)
        if answer: return f"[Via OpenRouter]\n{answer}"

    if GEMINI_KEY:
        print("   💎 Mencoba Gemini...")
        answer = chat_gemini(cloud_messages)
        if answer: return f"[Via Gemini]\n{answer}"

    tried = []
    if DASHSCOPE_KEY: tried.append("QwenCloud")
    if GROQ_KEY: tried.append("Groq")
    if OR_KEY: tried.append("OpenRouter")
    if GEMINI_KEY: tried.append("Gemini")
    if not tried:
        return "[Error] Belum ada key API aktif. Isi lewat menu ＋ → 🔑 API Keys."
    return f"[Error] Semua cloud dicoba tapi gagal ({', '.join(tried)}). Cek key / koneksi."

# ═══ 🔑 HOT-RELOAD KEYS ═══
def refresh_keys():
    global GROQ_KEY, OR_KEY, GEMINI_KEY, DASHSCOPE_KEY
    GROQ_KEY = os.getenv("GROQ_API_KEY", "")
    OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
    DASHSCOPE_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    generic = os.getenv("API_KEY", "")
    model_id = os.getenv("MODEL_ID", "")
    if generic:
        if not OR_KEY and generic.startswith("sk-or-"):
            OR_KEY = generic
        elif not DASHSCOPE_KEY and generic.startswith("sk-"):
            DASHSCOPE_KEY = generic
    if model_id:
        if "/" in model_id:
            os.environ["OPENROUTER_MODEL"] = model_id
        else:
            os.environ["DASHSCOPE_MODEL"] = model_id
    _build_candidates()

def key_status():
    return {
        "GROQ_API_KEY": bool(GROQ_KEY),
        "OPENROUTER_API_KEY": bool(OR_KEY),
        "DASHSCOPE_API_KEY": bool(DASHSCOPE_KEY),
        "GEMINI_API_KEY": bool(GEMINI_KEY),
    }

refresh_keys()
