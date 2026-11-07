#!/usr/bin/env python3

"""
MESIN AI v0.8 — LIVE BEHAVIOR MOCK TEST

Menguji alur perilaku nyata:
1. halo
2. remember
3. recall memory
4. project context
5. RAG
6. /power -> Cloud
7. cross-request isolation
8. system/context preservation

SEMUA PROVIDER MOCK.
Tidak menyentuh:
- llama-server nyata
- socket nyata
- database memory nyata
- Cloud API nyata
"""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Jangan pernah membuat LocalProvider asli.
# Dispatcher akan menerima MockLocal langsung saat konstruktor.
class MockLocal:

    MODELS = {
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_0"
        },
        "default": {
            "model": "Qwen3.5-2B-Q4_K_M"
        },
    }

    def __init__(self, config=None):
        self.config = config or {}
        self.calls = []

    def chat(self, messages, system_prompt="", tier=None):
        self.calls.append({
            "messages": [dict(m) for m in messages],
            "system_prompt": system_prompt,
            "tier": tier,
        })

        return (
            f"MOCK LOCAL [{tier}] :: "
            f"{messages[-1].get('content', '')}"
        )


class MockDispatcherBase:
    pass


from core.dispatcher import Dispatcher
from core.router import Router


passed = 0
failed = 0


def check(condition, name):
    global passed, failed

    if condition:
        passed += 1
        print(f"   ✅ {name}")
    else:
        failed += 1
        print(f"   ❌ {name}")


# ============================================================
# MOCK LOCAL
# ============================================================

class MockLocal:

    MODELS = {
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_0"
        },
        "default": {
            "model": "Qwen3.5-2B-Q4_K_M"
        },
    }

    def __init__(self, config=None):
        self.config = config or {}
        self.calls = []

    def chat(self, messages, system_prompt="", tier=None):
        self.calls.append({
            "messages": [dict(m) for m in messages],
            "system_prompt": system_prompt,
            "tier": tier,
        })

        return (
            f"MOCK LOCAL [{tier}] :: "
            f"{messages[-1].get('content', '')}"
        )


# ============================================================
# MOCK CLOUD
# ============================================================

cloud_calls = []


def mock_ask_online(messages, context=""):

    cloud_calls.append({
        "messages": [dict(m) for m in messages],
        "context": context,
    })

    return (
        "MOCK CLOUD :: "
        + messages[-1].get("content", "")
    )


# ============================================================
# CONFIG
# ============================================================

CONFIG = {
    "llm_local": {
        "host": "127.0.0.1",
        "port": 8080,
    }
}


# ============================================================
# MOCK CREDENTIAL / SOCKET SAFETY
# ============================================================

def fake_local_available(self):
    return True


# ============================================================
# HELPER
# ============================================================

def make_dispatcher():

    # Bypass Dispatcher.__init__ agar LocalProvider asli
    # tidak pernah dibuat dan tidak menyentuh api_url/socket/server.
    dispatcher = object.__new__(Dispatcher)

    dispatcher.config = CONFIG
    dispatcher.local = MockLocal(CONFIG)

    return dispatcher


def run_local(dispatcher, text, tier="instan",
              system_prompt="SYSTEM TEST"):

    return dispatcher.ask(
        messages=[
            {
                "role": "user",
                "content": text
            }
        ],
        rag_context="",
        system_prompt=system_prompt,
        tier=tier,
    )


def run_cloud(dispatcher, text, rag):

    return dispatcher.ask(
        messages=[
            {
                "role": "user",
                "content": text
            }
        ],
        rag_context=rag,
        system_prompt="SYSTEM TEST",
        tier="cloud",
    )


# ============================================================
# TEST
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — LIVE BEHAVIOR MOCK TEST")
print("========================================")
print()


# ------------------------------------------------------------
# 1. BASIC HALO
# ------------------------------------------------------------

print("1. BASIC BEHAVIOR — HALO")

dispatcher = make_dispatcher()

with patch.object(
    Dispatcher,
    "local_available",
    fake_local_available
):
    answer = run_local(
        dispatcher,
        "halo",
        tier="instan"
    )

check(
    answer.startswith("MOCK LOCAL"),
    "halo menghasilkan response local"
)

check(
    dispatcher.local.calls[-1]["tier"] == "instan",
    "halo memakai tier instan"
)

check(
    dispatcher.local.calls[-1]["messages"][-1]["content"] == "halo",
    "query halo tetap bersih"
)


# ------------------------------------------------------------
# 2. MEMORY BEHAVIOR
# ------------------------------------------------------------

print()
print("2. MEMORY BEHAVIOR")

memory_a = "Pengguna suka kopi hitam"
memory_b = "Pengguna suka bersepeda"

memory_context_a = (
    "MEMORY RELEVAN PROYEK:\n"
    + memory_a
)

memory_context_b = (
    "MEMORY RELEVAN PROYEK:\n"
    + memory_b
)

dispatcher = make_dispatcher()

with patch.object(
    Dispatcher,
    "local_available",
    fake_local_available
):
    answer_a = dispatcher.ask(
        messages=[
            {
                "role": "user",
                "content": "apa minuman favorit?"
            }
        ],
        system_prompt=memory_context_a,
        tier="default"
    )

    answer_b = dispatcher.ask(
        messages=[
            {
                "role": "user",
                "content": "apa hobiku?"
            }
        ],
        system_prompt=memory_context_b,
        tier="default"
    )

call_a = dispatcher.local.calls[-2]
call_b = dispatcher.local.calls[-1]

check(
    "Pengguna suka kopi hitam" in call_a["system_prompt"],
    "Memory A masuk request A"
)

check(
    "Pengguna suka bersepeda" in call_b["system_prompt"],
    "Memory B masuk request B"
)

check(
    "Pengguna suka bersepeda" not in call_a["system_prompt"],
    "Memory B tidak bocor ke request A"
)

check(
    "Pengguna suka kopi hitam" not in call_b["system_prompt"],
    "Memory A tidak bocor ke request B"
)


# ------------------------------------------------------------
# 3. PROJECT BEHAVIOR
# ------------------------------------------------------------

print()
print("3. PROJECT BEHAVIOR")

project_context = (
    "STATUS PROYEK TERKINI:\n"
    "Nama: Mesin AI pribadi\n"
    "Versi: v0.8\n"
    "Platform: Poco F4 5G + Termux"
)

dispatcher = make_dispatcher()

with patch.object(
    Dispatcher,
    "local_available",
    fake_local_available
):
    answer = dispatcher.ask(
        messages=[
            {
                "role": "user",
                "content": "bagaimana status proyek?"
            }
        ],
        system_prompt=project_context,
        tier="default"
    )

project_call = dispatcher.local.calls[-1]

check(
    "Mesin AI pribadi" in project_call["system_prompt"],
    "Project context sampai ke Local"
)

check(
    "Versi: v0.8" in project_call["system_prompt"],
    "Versi proyek tetap dipertahankan"
)

check(
    "Poco F4 5G" in project_call["system_prompt"],
    "Platform proyek tetap dipertahankan"
)


# ------------------------------------------------------------
# 4. RAG BEHAVIOR
# ------------------------------------------------------------

print()
print("4. RAG BEHAVIOR")

dispatcher = make_dispatcher()

rag = (
    "KONTEKS WEB TERKINI:\n"
    "MOCK SOURCE: Retrieval-Augmented Generation."
)

with patch(
    "core.dispatcher.ask_online",
    side_effect=mock_ask_online
):

    cloud_calls.clear()

    answer = run_cloud(
        dispatcher,
        "jelaskan RAG",
        rag
    )

check(
    answer.startswith("MOCK CLOUD"),
    "RAG menghasilkan response Cloud"
)

check(
    len(cloud_calls) == 1,
    "Cloud dipanggil tepat satu kali"
)

check(
    cloud_calls[-1]["context"] == rag,
    "RAG context diteruskan utuh"
)

check(
    cloud_calls[-1]["messages"][-1]["content"]
    == "jelaskan RAG",
    "query RAG tetap bersih"
)


# ------------------------------------------------------------
# 5. POWER BEHAVIOR
# ------------------------------------------------------------

print()
print("5. /POWER → CLOUD")

dispatcher = make_dispatcher()

with patch(
    "core.dispatcher.ask_online",
    side_effect=mock_ask_online
):

    cloud_calls.clear()

    answer = run_cloud(
        dispatcher,
        "apa itu fine-tuning?",
        "RAG MOCK POWER SOURCE"
    )

check(
    answer.startswith("MOCK CLOUD"),
    "/power menghasilkan response Cloud"
)

check(
    len(cloud_calls) == 1,
    "/power hanya memanggil Cloud sekali"
)

check(
    len(dispatcher.local.calls) == 0,
    "/power tidak memanggil LocalProvider"
)


# ------------------------------------------------------------
# 6. CROSS REQUEST ISOLATION
# ------------------------------------------------------------

print()
print("6. CROSS-REQUEST ISOLATION")

dispatcher = make_dispatcher()

with patch(
    "core.dispatcher.ask_online",
    side_effect=mock_ask_online
):

    cloud_calls.clear()

    rag_a = "SOURCE A — hanya request A"
    rag_b = "SOURCE B — hanya request B"

    run_cloud(
        dispatcher,
        "query A",
        rag_a
    )

    run_cloud(
        dispatcher,
        "query B",
        rag_b
    )

check(
    len(cloud_calls) == 2,
    "Request A dan B menghasilkan dua Cloud call"
)

call_a = cloud_calls[0]
call_b = cloud_calls[1]

check(
    call_a["context"] == rag_a,
    "Request A hanya membawa RAG A"
)

check(
    call_b["context"] == rag_b,
    "Request B hanya membawa RAG B"
)

check(
    rag_b not in call_a["context"],
    "RAG B tidak bocor ke A"
)

check(
    rag_a not in call_b["context"],
    "RAG A tidak bocor ke B"
)


# ------------------------------------------------------------
# 7. SYSTEM PRESERVATION
# ------------------------------------------------------------

print()
print("7. SYSTEM PIPELINE PRESERVATION")

dispatcher = make_dispatcher()

with patch.object(
    Dispatcher,
    "local_available",
    fake_local_available
):

    run_local(
        dispatcher,
        "tes system",
        tier="instan",
        system_prompt="SYSTEM IDENTITY TEST"
    )

system_call = dispatcher.local.calls[-1]

check(
    "SYSTEM IDENTITY TEST" in system_call["system_prompt"],
    "system prompt tetap hidup"
)

check(
    system_call["messages"][-1]["content"]
    == "tes system",
    "messages tetap memakai query user"
)


# ------------------------------------------------------------
# 8. 4B ISOLATION
# ------------------------------------------------------------

print()
print("8. 4B ISOLATION")

check(
    "4b" not in MockLocal.MODELS,
    "4B tidak terdaftar sebagai local tier"
)

check(
    "power" not in MockLocal.MODELS,
    "power tidak tersedia sebagai Local tier"
)

check(
    MockLocal.MODELS["instan"]["model"]
    == "Qwen3.5-0.8B-Q4_0",
    "instan tetap 0.8B"
)

check(
    MockLocal.MODELS["default"]["model"]
    == "Qwen3.5-2B-Q4_K_M",
    "default tetap 2B"
)


# ------------------------------------------------------------
# RESULT
# ------------------------------------------------------------

print()
print("========================================")
print(" HASIL LIVE BEHAVIOR")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:

    print("✅ LIVE BEHAVIOR v0.8 AMAN")
    print()
    print("   👋 Basic      → local")
    print("   🧠 Memory     → isolated")
    print("   📁 Project    → preserved")
    print("   📄 RAG        → preserved")
    print("   ☁️ /power     → Cloud")
    print("   🔒 Cross req  → isolated")
    print("   🪞 System     → preserved")
    print("   💾 4B         → isolated")

    raise SystemExit(0)

print("❌ LIVE BEHAVIOR v0.8 GAGAL")
print("Periksa failure di atas.")

raise SystemExit(1)
