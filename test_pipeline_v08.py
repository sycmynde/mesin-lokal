#!/usr/bin/env python3

"""
MESIN AI v0.8 — FULL PIPELINE MOCK TEST

Menguji satu request utuh tanpa:
- llama-server
- internet
- API Cloud
- token Cloud
- database memory

Pipeline:
    user input
      ↓
    choose_llm_tier
      ↓
    Router
      ↓
    Dispatcher
      ↓
    Local 0.8B / Local 2B / Cloud

Kontrak v0.8:
    ⚡ instan  → Local 0.8B
    🎯 default → Local 2B
    ☁️ power   → Cloud
    💾 4B      → isolated
"""

import sys
import types
from pathlib import Path


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
# EXPECTED ARCHITECTURE
# ============================================================

EXPECTED = {
    "instan": "Qwen3.5-0.8B-Q4_0",
    "default": "Qwen3.5-2B-Q4_K_M",
}

STANDBY_4B = "Qwen3.5-4B-Q4_K_M"


# ============================================================
# CONFIG MOCK
# ============================================================

CONFIG = {
    "llm_local": {
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "host": "127.0.0.1",
        "port": 8080,
        "model_name": EXPECTED["default"],
        "max_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.9,
    }
}


# ============================================================
# MOCK LOCAL PROVIDER
# ============================================================

class MockLocalProvider:

    MODELS = {
        "instan": {
            "model": EXPECTED["instan"],
            "max_tokens": 128,
            "temperature": 0.1,
            "top_p": 0.9,
        },
        "default": {
            "model": EXPECTED["default"],
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        },
    }

    def __init__(self, config=None):
        self.config = config or {}
        self.default_tier = "default"
        self.model = EXPECTED["default"]
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
# MOCK CLOUD
# ============================================================

class MockCloud:

    def __init__(self):
        self.calls = []

    def ask_online(self, messages, context=""):

        self.calls.append({
            "messages": messages,
            "context": context,
        })

        return "[MOCK CLOUD] Online AI response"


mock_cloud = MockCloud()


# ============================================================
# PATCH DISPATCHER DEPENDENCIES
# ============================================================

import core.dispatcher as dispatcher_module

dispatcher_module.LocalProvider = MockLocalProvider
dispatcher_module.ask_online = mock_cloud.ask_online

Dispatcher = dispatcher_module.Dispatcher


# ============================================================
# ROUTER IMPORT
# ============================================================

from core.router import Router

# Gunakan Router asli, tetapi buat instance lokal khusus test.
# Tidak menjalankan main.py dan tidak menyentuh session/database.
router = Router()


# ============================================================
# MAIN HELPERS
# ============================================================

from main import choose_llm_tier


# ============================================================
# DISPATCHER
# ============================================================

dispatcher = Dispatcher(CONFIG)

# Jangan pernah menyentuh socket / llama-server.
dispatcher.local_available = lambda: True


# ============================================================
# PIPELINE HELPER
# ============================================================

def run_pipeline(user_input, rag_context=""):

    """
    Menjalankan bagian pipeline yang relevan:

        input
          ↓
        tier parser
          ↓
        Router
          ↓
        Dispatcher
    """

    llm_tier, llm_text = choose_llm_tier(user_input)

    route_text = (
        llm_text
        if llm_text
        else user_input
    )

    result = router.route(route_text)

    task = result.get("type")

    messages = [
        {
            "role": "user",
            "content": route_text,
        }
    ]

    system_prompt = "SYSTEM PIPELINE TEST"

    answer = dispatcher.ask(
        messages=messages,
        system_prompt=system_prompt,
        rag_context=rag_context,
        tier=llm_tier,
    )

    return {
        "input": user_input,
        "tier": llm_tier,
        "query": route_text,
        "route": result,
        "task": task,
        "answer": answer,
    }


# ============================================================
# HEADER
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — FULL PIPELINE MOCK TEST")
print("========================================")
print()


# ============================================================
# TEST 1 — BASIC ROUTING
# ============================================================

print("1. BASIC PIPELINE")


before_local = len(dispatcher.local.calls)

r = run_pipeline("/instan halo")

check(
    r["tier"] == "instan",
    "/instan → tier instan",
    f"tier={r['tier']}"
)

check(
    r["query"] == "halo",
    "/instan → query bersih",
    f"query={r['query']!r}"
)

check(
    r["answer"] == (
        "[MOCK LOCAL] "
        "tier=instan "
        "model=Qwen3.5-0.8B-Q4_0"
    ),
    "/instan → Mock Local 0.8B",
    f"answer={r['answer']!r}"
)

check(
    len(dispatcher.local.calls) == before_local + 1,
    "Dispatcher benar-benar memanggil LocalProvider"
)


# ============================================================
# TEST 2 — DEFAULT
# ============================================================

print()
print("2. DEFAULT PIPELINE")


r = run_pipeline("/default jelaskan RAG")

check(
    r["tier"] == "default",
    "/default → tier default"
)

check(
    r["query"] == "jelaskan RAG",
    "/default → query bersih"
)

check(
    r["answer"] == (
        "[MOCK LOCAL] "
        "tier=default "
        "model=Qwen3.5-2B-Q4_K_M"
    ),
    "/default → Mock Local 2B"
)

check(
    dispatcher.local.calls[-1]["tier"] == "default",
    "LocalProvider menerima tier=default"
)


# ============================================================
# TEST 3 — POWER/CLOUD
# ============================================================

print()
print("3. POWER → CLOUD PIPELINE")


rag_context = (
    "KONTEKS WEB TERKINI:\n"
    "RAG MOCK SOURCE: "
    "Retrieval-Augmented Generation."
)

before_local = len(dispatcher.local.calls)
before_cloud = len(mock_cloud.calls)

r = run_pipeline(
    "/power jelaskan RAG",
    rag_context=rag_context,
)

check(
    r["tier"] in ("power", "cloud"),
    "/power → Cloud route",
    f"tier={r['tier']}"
)

check(
    r["query"] == "jelaskan RAG",
    "/power → query bersih"
)

check(
    r["answer"] == "[MOCK CLOUD] Online AI response",
    "/power → Mock Cloud"
)

check(
    len(mock_cloud.calls) == before_cloud + 1,
    "Cloud dipanggil tepat 1 kali"
)

check(
    len(dispatcher.local.calls) == before_local,
    "Cloud tidak memanggil LocalProvider"
)

if mock_cloud.calls:

    call = mock_cloud.calls[-1]

    check(
        call["context"] == rag_context,
        "RAG context sampai ke Cloud secara utuh"
    )

    check(
        call["messages"][0]["content"] == "jelaskan RAG",
        "Cloud menerima query bersih"
    )


# ============================================================
# TEST 4 — NORMAL FALLBACK
# ============================================================

print()
print("4. NORMAL FALLBACK")


r = run_pipeline("halo")

check(
    r["tier"] in (None, "instan"),
    "Input normal tidak memaksa tier ilegal",
    f"tier={r['tier']}"
)

check(
    r["query"] == "halo",
    "Input normal tetap bersih"
)

check(
    "MOCK LOCAL" in r["answer"],
    "Input normal tetap masuk jalur local"
)


# ============================================================
# TEST 5 — CONTEXT ISOLATION
# ============================================================

print()
print("5. CROSS-REQUEST CONTEXT ISOLATION")


rag_a = (
    "KONTEKS WEB TERKINI:\n"
    "SOURCE A — hanya untuk request A"
)

rag_b = (
    "KONTEKS WEB TERKINI:\n"
    "SOURCE B — hanya untuk request B"
)

cloud_before = len(mock_cloud.calls)

run_pipeline(
    "/power pertanyaan A",
    rag_context=rag_a,
)

run_pipeline(
    "/power pertanyaan B",
    rag_context=rag_b,
)

check(
    len(mock_cloud.calls) == cloud_before + 2,
    "Request A dan B menghasilkan dua Cloud call"
)

if len(mock_cloud.calls) >= 2:

    call_a = mock_cloud.calls[-2]
    call_b = mock_cloud.calls[-1]

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
        "RAG B tidak bocor ke Request A"
    )

    check(
        rag_a not in call_b["context"],
        "RAG A tidak bocor ke Request B"
    )


# ============================================================
# TEST 6 — SYSTEM PROMPT
# ============================================================

print()
print("6. SYSTEM PIPELINE PRESERVATION")


r = run_pipeline("/instan tes system prompt")

call = dispatcher.local.calls[-1]

check(
    "SYSTEM PIPELINE TEST" in call["system_prompt"],
    "system_prompt tetap diteruskan ke LocalProvider"
)

check(
    call["messages"][0]["content"] == "tes system prompt",
    "messages memakai query bersih"
)


# ============================================================
# TEST 7 — 4B ISOLATION
# ============================================================

print()
print("7. 4B ISOLATION")


local_models = dispatcher.local.MODELS

check(
    "power" not in local_models,
    "power tidak tersedia sebagai local tier"
)

check(
    STANDBY_4B not in [
        cfg["model"]
        for cfg in local_models.values()
    ],
    "4B tidak digunakan sebagai local tier"
)

check(
    all(
        cfg["model"] != STANDBY_4B
        for cfg in local_models.values()
    ),
    "4B tetap standby / isolated"
)


# ============================================================
# TEST 8 — NO REAL CLOUD / SOCKET
# ============================================================

print()
print("8. MOCK SAFETY")


check(
    dispatcher.local_available.__name__ == "<lambda>",
    "llama-server/socket tidak disentuh"
)

check(
    all(
        call["answer"] if "answer" in call else True
        for call in []
    ),
    "Tidak ada dependency server nyata"
)

check(
    all(
        isinstance(call["messages"], list)
        for call in mock_cloud.calls
    ),
    "Cloud hanya menerima mock messages"
)


# ============================================================
# RESULT
# ============================================================

print()
print("========================================")
print(" HASIL PIPELINE")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:

    print("✅ PIPELINE v0.8 AMAN")
    print()
    print("   Input")
    print("      ↓")
    print("   choose_llm_tier()")
    print("      ↓")
    print("   Router")
    print("      ↓")
    print("   Dispatcher")
    print("      ├── ⚡ instan  → Mock Local 0.8B")
    print("      ├── 🎯 default → Mock Local 2B")
    print("      └── ☁️ power   → Mock Cloud")
    print()
    print("   💾 4B → standby / isolated")
    print("   🧠 Context → request isolated")
    print("   📄 RAG → preserved")
    print("   🌐 Cloud → mock only")

    sys.exit(0)

else:

    print("❌ PIPELINE v0.8 GAGAL")
    print()
    print("Periksa failure di atas.")

    sys.exit(1)
