#!/usr/bin/env python3
import requests
import sys
import time
import socket

SERVER = "http://127.0.0.1:8080"
CHAT_URL = f"{SERVER}/v1/chat/completions"
MODELS_URL = f"{SERVER}/models"

# ============================================================
# MESIN AI v2
# CPU-only / llama-server multi-model on-demand
#
# Local:
#   instan  -> Qwen3-0.6B-Q4_0
#   default -> Qwen3.5-2B-Q4_K_M
#
# Power 4B sengaja TIDAK masuk auto-router.
# Cloud disiapkan sebagai fallback, tetapi belum aktif.
# ============================================================

MODELS = {
    "instan": {
        "model": "Qwen3-0.6B-Q4_0",
        "temp": 0.1,
        "max_tokens": 128,
        "label": "⚡ Instan",
    },
    "default": {
        "model": "Qwen3.5-2B-Q4_K_M",
        "temp": 0.5,
        "max_tokens": 512,
        "label": "🎯 Default",
    },
}

CLOUD_ENABLED = False

TIER1_KW = [
    "halo", "hai", "hi", "hello", "hei",
    "siapa kamu", "siapa saya", "siapa lo",
    "terima kasih", "makasih", "thanks",
    "lokasi", "jangkar", "jam berapa",
    "tanggal", "hari ini", "siapa nama",
]

HEAVY_KW = [
    "jelaskan secara mendalam",
    "analisis",
    "bandingkan",
    "debug",
    "debugging",
    "arsitektur",
    "kode",
    "program",
    "programming",
    "buatkan script",
    "buatkan kode",
    "kenapa error",
    "analisa",
]


def server_models():
    try:
        r = requests.get(MODELS_URL, timeout=3)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


def model_status(model_id):
    for m in server_models():
        if m.get("id") == model_id:
            return m.get("status", {}).get("value", "unknown")
    return "not_found"


def wait_model_loaded(model_id, timeout=120):
    """Tunggu sampai model yang diminta selesai loading."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        status = model_status(model_id)

        if status == "loaded":
            return True

        # Beberapa build bisa memakai status loading/loading:
        # selama model masih terdaftar, tunggu.
        if status == "not_found":
            return False

        time.sleep(1)

    return False


def local_chat(query, tier):
    cfg = MODELS[tier]
    model_id = cfg["model"]

    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": query}
        ],
        "temperature": cfg["temp"],
        "max_tokens": cfg["max_tokens"],
        "top_k": 40,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "stream": False,
    }

    try:
        r = requests.post(CHAT_URL, json=payload, timeout=180)
        r.raise_for_status()

        data = r.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return answer, None

    except requests.exceptions.Timeout:
        return None, "timeout"

    except requests.exceptions.ConnectionError:
        return None, "connection"

    except Exception as e:
        return None, str(e)


def cloud_available():
    # Placeholder.
    # Nanti diganti dengan health check provider cloud.
    return False


def cloud_chat(query):
    # Jangan aktifkan sampai provider/API dikonfigurasi.
    return None, "cloud_not_configured"


def route(query):
    q = query.lower().strip()

    if any(kw in q for kw in TIER1_KW) and len(q) < 40:
        return "instan"

    # Heavy tidak langsung ke 4B.
    # Untuk sekarang tetap lokal 2B.
    # Tahap berikutnya: heavy + internet -> cloud.
    return "default"


def ask(query, forced_tier=None):
    tier = forced_tier or route(query)

    # LOCAL
    cfg = MODELS[tier]
    print(f"   → {cfg['label']} [{cfg['model']}]...", end=" ", flush=True)

    answer, error = local_chat(query, tier)

    if answer is not None:
        print()
        return answer, cfg["label"]

    print(f"\n   ⚠️ Local error: {error}")

    # CLOUD FALLBACK
    if CLOUD_ENABLED and cloud_available():
        print("   ☁️ Mencoba Cloud...", end=" ", flush=True)
        answer, cloud_error = cloud_chat(query)

        if answer is not None:
            print()
            return answer, "☁️ Cloud"

        print(f"\n   ⚠️ Cloud error: {cloud_error}")

    # Jangan pindah ke 4B otomatis.
    return (
        "❌ Model lokal gagal merespons. "
        "Cloud fallback belum aktif.",
        "⚠️ Error",
    )


def print_models():
    print("\n📋 Model registry:")
    models = server_models()

    if not models:
        print("   ❌ llama-server tidak bisa dihubungi")
        return

    for m in models:
        mid = m.get("id", "?")
        status = m.get("status", {}).get("value", "?")

        if mid == MODELS["instan"]["model"]:
            role = "⚡ Instan"
        elif mid == MODELS["default"]["model"]:
            role = "🎯 Default"
        elif mid == "Qwen3.5-4B-Q4_K_M":
            role = "🧠 Standby / tidak auto-route"
        else:
            role = ""

        print(f"   {status:10} {mid} {role}")

    print()


def main():
    print("=== Mesin AI Modular v2 ===")
    print("⚡ Instan | 🎯 Default | ☁️ Cloud fallback (OFF)")
    print("🧠 4B: standby, tidak dipakai router otomatis")
    print()
    print("Override:")
    print("  /instan <pertanyaan>")
    print("  /default <pertanyaan>")
    print("  /models")
    print("  /status")
    print("  exit")
    print()

    if not server_models():
        print("❌ llama-server tidak aktif di", SERVER)
        print("   Jalankan dulu: bash ~/mesin/start_mesin.sh")
        sys.exit(1)

    while True:
        try:
            user_input = input(" Anda: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        low = user_input.lower()

        if low in ("exit", "quit", "keluar"):
            break

        if low in ("/models", "/status"):
            print_models()
            continue

        forced_tier = None

        for tier in MODELS:
            prefix = f"/{tier}"
            if low == prefix:
                print("   ⚠️ Beri pertanyaan setelah override.")
                forced_tier = tier
                user_input = ""
                break

            if low.startswith(prefix + " "):
                forced_tier = tier
                user_input = user_input[len(prefix):].strip()
                break

        if not user_input:
            continue

        answer, source = ask(user_input, forced_tier)

        print(f"\n{source}:")
        print(answer)
        print()

    print("✅ Selesai.")


if __name__ == "__main__":
    main()
