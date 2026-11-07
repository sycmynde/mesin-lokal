#!/usr/bin/env python3

"""
MESIN AI v0.8
Dispatcher Regression Test — MOCK ONLY

Tidak:
- menjalankan llama-server
- membuka koneksi localhost
- memanggil API Cloud
- menggunakan API key
- menghabiskan token

Yang diuji:
- Dispatcher memilih jalur local/cloud dengan benar
- tier instan memakai 0.8B
- tier default memakai 2B
- tier cloud memanggil ask_online()
- 4B tidak menjadi tier lokal
- system_prompt / messages diteruskan
- rag_context diteruskan ke Cloud
"""

import sys
import types

from providers.local import LocalProvider


# ============================================================
# EXPECTED ARCHITECTURE
# ============================================================

EXPECTED = {
    "instan": "Qwen3.5-0.8B-Q4_0",
    "default": "Qwen3.5-2B-Q4_K_M",
}

CLOUD_TIER = "cloud"
STANDBY_4B = "Qwen3.5-4B-Q4_K_M"


# ============================================================
# TEST STATE
# ============================================================

passed = 0
failed = 0


def ok(name):
    global passed
    passed += 1
    print(f"   ✅ {name}")


def fail(name, detail=""):
    global failed
    failed += 1
    print(f"   ❌ {name}")
    if detail:
        print(f"      {detail}")


def check(condition, name, detail=""):
    if condition:
        ok(name)
    else:
        fail(name, detail)


# ============================================================
# MOCK CONFIG
# ============================================================

CONFIG = {
    "llm_local": {
        "host": "127.0.0.1",
        "port": 8080,
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "model_name": "Qwen3.5-2B-Q4_K_M",
    }
}


# ============================================================
# MOCK LOCAL PROVIDER
#
# Dispatcher membuat LocalProvider sendiri.
# Kita ganti class tersebut sebelum membuat Dispatcher.
# ============================================================

class MockLocalProvider:

    MODELS = {
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_0",
            "max_tokens": 128,
            "temperature": 0.1,
            "top_p": 0.9,
        },
        "default": {
            "model": "Qwen3.5-2B-Q4_K_M",
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        },
    }

    def __init__(self, config):
        self.default_tier = "default"
        self.model = "Qwen3.5-2B-Q4_K_M"

        self.calls = []

    def chat(self, messages, system_prompt="", tier=None):

        self.calls.append({
            "messages": messages,
            "system_prompt": system_prompt,
            "tier": tier,
        })

        cfg = self.MODELS.get(
            tier,
            self.MODELS["default"]
        )

        return (
            f"[MOCK LOCAL] "
            f"tier={tier} "
            f"model={cfg['model']}"
        )


# ============================================================
# MOCK ask_online
# ============================================================

class MockCloud:

    def __init__(self):
        self.calls = []

    def ask_online(self, messages, context="", system_prompt=None, **kwargs):

        self.calls.append({
            "messages": messages,
            "context": context,
            "system_prompt": system_prompt,
        })

        return (
            "[MOCK CLOUD] "
            "Online AI response"
        )


mock_cloud = MockCloud()


# ============================================================
# INJECT MOCK BEFORE IMPORTING DISPATCHER
# ============================================================

# Dispatcher melakukan:
#
# from providers.local import LocalProvider
#
# Jadi patch module attribute setelah import module.
#
# Cloud juga dipatch supaya tidak ada request internet.

import core.dispatcher as dispatcher_module

dispatcher_module.LocalProvider = MockLocalProvider
dispatcher_module.ask_online = mock_cloud.ask_online

Dispatcher = dispatcher_module.Dispatcher


# ============================================================
# CREATE DISPATCHER
# ============================================================

dispatcher = Dispatcher(CONFIG)


# Pastikan local_available tidak pernah menyentuh socket.
dispatcher.local_available = lambda: True


# ============================================================
# TEST 1 — LOCAL MODEL REGISTRY
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — DISPATCHER MOCK TEST")
print("========================================")
print()

print("1. LOCAL MODEL CONTRACT")

local_models = dispatcher.local.MODELS

check(
    set(local_models.keys()) == {"instan", "default"},
    "Dispatcher local registry hanya instan + default",
    f"tiers={list(local_models.keys())}"
)

check(
    local_models["instan"]["model"]
    == EXPECTED["instan"],
    "Dispatcher instan → 0.8B"
)

check(
    local_models["default"]["model"]
    == EXPECTED["default"],
    "Dispatcher default → 2B"
)

check(
    "power" not in local_models,
    "Dispatcher tidak memiliki local power tier"
)

check(
    STANDBY_4B not in [
        x["model"] for x in local_models.values()
    ],
    "4B tidak terdaftar sebagai local tier"
)


# ============================================================
# TEST 2 — INSTANT LOCAL
# ============================================================

print()
print("2. /INSTAN → LOCAL 0.8B")

messages = [
    {
        "role": "user",
        "content": "halo",
    }
]

answer = dispatcher.ask(
    messages=messages,
    system_prompt="SYSTEM TEST",
    rag_context="",
    tier="instan",
)

check(
    answer == "[MOCK LOCAL] tier=instan model=Qwen3.5-0.8B-Q4_0",
    "/instan menghasilkan response local"
)

check(
    len(dispatcher.local.calls) == 1,
    "LocalProvider dipanggil tepat 1 kali"
)

if dispatcher.local.calls:

    call = dispatcher.local.calls[-1]

    check(
        call["tier"] == "instan",
        "LocalProvider menerima tier=instan"
    )

    check(
        "SYSTEM TEST" in call["system_prompt"],
        "system_prompt diteruskan"
    )


# ============================================================
# TEST 3 — DEFAULT LOCAL
# ============================================================

print()
print("3. /DEFAULT → LOCAL 2B")

messages = [
    {
        "role": "user",
        "content": "jelaskan RAG",
    }
]

answer = dispatcher.ask(
    messages=messages,
    system_prompt="SYSTEM DEFAULT TEST",
    rag_context="",
    tier="default",
)

check(
    answer == "[MOCK LOCAL] tier=default model=Qwen3.5-2B-Q4_K_M",
    "/default menghasilkan response local"
)

check(
    dispatcher.local.calls[-1]["tier"] == "default",
    "LocalProvider menerima tier=default"
)


# ============================================================
# TEST 4 — CLOUD
# ============================================================

print()
print("4. /POWER → CLOUD")

cloud_messages = [
    {
        "role": "user",
        "content": "jelaskan perbedaan RAG dan fine-tuning",
    }
]

cloud_context = (
    "KONTEKS WEB TERKINI:\n"
    "RAG adalah Retrieval-Augmented Generation."
)

before_local_calls = len(dispatcher.local.calls)
before_cloud_calls = len(mock_cloud.calls)

answer = dispatcher.ask(
    messages=cloud_messages,
    system_prompt="SYSTEM CLOUD TEST",
    rag_context=cloud_context,
    tier="cloud",
)

check(
    answer == "[MOCK CLOUD] Online AI response",
    "/power menghasilkan response Cloud"
)

check(
    len(mock_cloud.calls) == before_cloud_calls + 1,
    "ask_online dipanggil tepat 1 kali"
)

check(
    len(dispatcher.local.calls) == before_local_calls,
    "Cloud TIDAK memanggil LocalProvider"
)

if mock_cloud.calls:

    call = mock_cloud.calls[-1]

    check(
        call["context"] == cloud_context,
        "RAG context diteruskan ke Cloud"
    )

    check(
        call["messages"] == cloud_messages,
        "messages diteruskan ke Cloud"
    )


# ============================================================
# TEST 5 — CLOUD MUST NOT BECOME LOCAL
# ============================================================

print()
print("5. CLOUD ISOLATION")

local_tiers_seen = [
    call["tier"]
    for call in dispatcher.local.calls
]

check(
    "cloud" not in local_tiers_seen,
    "tier cloud tidak pernah masuk LocalProvider"
)

check(
    all(
        tier in ("instan", "default")
        for tier in local_tiers_seen
    ),
    "Semua pemanggilan LocalProvider valid"
)


# ============================================================
# TEST 6 — NO 4B
# ============================================================

print()
print("6. 4B ISOLATION")

local_model_names = [
    cfg["model"]
    for cfg in dispatcher.local.MODELS.values()
]

check(
    STANDBY_4B not in local_model_names,
    "Qwen3.5-4B-Q4_K_M tidak dipanggil sebagai local tier"
)

check(
    "power" not in dispatcher.local.MODELS,
    "power tidak tersedia sebagai local model"
)


# ============================================================
# TEST 7 — FALLBACK MODEL
# ============================================================

print()
print("7. DEFAULT FALLBACK")

cfg = dispatcher.local.MODELS.get("default")

check(
    cfg is not None,
    "Default tier tersedia"
)

if cfg:
    check(
        cfg["model"] == "Qwen3.5-2B-Q4_K_M",
        "Fallback default → 2B"
    )


# ============================================================
# FINAL
# ============================================================

print()
print("========================================")
print(" HASIL DISPATCHER")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed:
    print("❌ DISPATCHER v0.8 GAGAL")
    print()
    print("Target:")
    print("   ⚡ instan  → Local 0.8B")
    print("   🎯 default → Local 2B")
    print("   ☁️ cloud   → Online AI")
    print("   💾 4B      → standby / non-tier")
    print()
    sys.exit(1)

print("✅ DISPATCHER v0.8 AMAN")
print()
print("   ⚡ instan  → Mock Local 0.8B")
print("   🎯 default → Mock Local 2B")
print("   ☁️ cloud   → Mock Online AI")
print("   💾 4B      → isolated")
print()
sys.exit(0)
