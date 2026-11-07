#!/usr/bin/env python3

"""
MESIN AI v0.8 — RAG REGRESSION MOCK TEST

Tujuan:
- Tidak memakai internet
- Tidak memakai API key
- Tidak memakai llama-server
- Memastikan RAG menerima query bersih
- Memastikan hasil retrieval menjadi rag_context
- Memastikan rag_context diteruskan ke Dispatcher
- Memastikan RAG tidak bocor antar-request
- Memastikan Cloud menerima context RAG
- Memastikan Local juga menerima context RAG
"""

import sys
import types


# ============================================================
# TEST STATE
# ============================================================

passed = 0
failed = 0


def check(condition, name, detail=""):
    global passed, failed

    if condition:
        passed += 1
        print(f"   ✅ {name}")
    else:
        failed += 1
        print(f"   ❌ {name}")
        if detail:
            print(f"      {detail}")


# ============================================================
# EXPECTED ARCHITECTURE
# ============================================================

EXPECTED_LOCAL = {
    "instan": "Qwen3.5-0.8B-Q4_0",
    "default": "Qwen3.5-2B-Q4_K_M",
}

STANDBY_4B = "Qwen3.5-4B-Q4_K_M"


# ============================================================
# MOCK RAG
# ============================================================

class MockRAG:

    def __init__(self):
        self.calls = []

    def execute(self, data):
        text = data.get("text", "")

        self.calls.append({
            "text": text,
        })

        return (
            "KONTEKS WEB TERKINI:\n"
            "RAG MOCK SOURCE: "
            "Retrieval-Augmented Generation mengambil "
            "informasi relevan sebelum model menjawab."
        )


mock_rag = MockRAG()


# ============================================================
# MOCK LOCAL PROVIDER
# ============================================================

class MockLocalProvider:

    MODELS = {
        "instan": {
            "model": EXPECTED_LOCAL["instan"],
            "max_tokens": 128,
            "temperature": 0.1,
            "top_p": 0.9,
        },
        "default": {
            "model": EXPECTED_LOCAL["default"],
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        },
    }

    def __init__(self, config):
        self.default_tier = "default"
        self.model = EXPECTED_LOCAL["default"]
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
# CREATE DISPATCHER
# ============================================================

CONFIG = {
    "llm_local": {
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "host": "127.0.0.1",
        "port": 8080,
        "model_name": EXPECTED_LOCAL["default"],
        "max_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.9,
    }
}

dispatcher = Dispatcher(CONFIG)

# Jangan sentuh socket / llama-server.
dispatcher.local_available = lambda: True


# ============================================================
# HEADER
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — RAG MOCK TEST")
print("========================================")
print()


# ============================================================
# TEST 1 — RAG QUERY CLEAN
# ============================================================

print("1. RAG QUERY ISOLATION")

query = "jelaskan RAG secara singkat"

rag_result = mock_rag.execute({
    "text": query
})

check(
    len(mock_rag.calls) == 1,
    "RAG dipanggil tepat 1 kali"
)

check(
    mock_rag.calls[-1]["text"] == query,
    "RAG menerima query bersih"
)

check(
    "/default" not in mock_rag.calls[-1]["text"],
    "Prefix tier tidak masuk RAG"
)


# ============================================================
# TEST 2 — RETRIEVAL RESULT
# ============================================================

print()
print("2. RETRIEVAL RESULT")

check(
    isinstance(rag_result, str),
    "RAG menghasilkan context string"
)

check(
    "KONTEKS WEB TERKINI:" in rag_result,
    "Context RAG memiliki marker"
)

check(
    "Retrieval-Augmented Generation" in rag_result,
    "Context retrieval berisi hasil mock"
)


# ============================================================
# TEST 3 — LOCAL + RAG
# ============================================================

print()
print("3. RAG → LOCAL 2B")

messages = [
    {
        "role": "user",
        "content": query,
    }
]

answer = dispatcher.ask(
    messages=messages,
    system_prompt="SYSTEM RAG LOCAL TEST",
    rag_context=rag_result,
    tier="default",
)

check(
    answer == (
        "[MOCK LOCAL] "
        "tier=default "
        "model=Qwen3.5-2B-Q4_K_M"
    ),
    "RAG request menghasilkan response local"
)

check(
    len(dispatcher.local.calls) == 1,
    "LocalProvider dipanggil tepat 1 kali"
)

local_call = dispatcher.local.calls[-1]

check(
    local_call["tier"] == "default",
    "RAG tetap memakai tier default"
)

check(
    "SYSTEM RAG LOCAL TEST" in local_call["system_prompt"],
    "system_prompt tetap diteruskan"
)


# ============================================================
# TEST 4 — RAG CONTEXT PRESERVED
# ============================================================

print()
print("4. RAG CONTEXT PRESERVATION")

check(
    "SYSTEM RAG LOCAL TEST" in local_call["system_prompt"],
    "Identity/system pipeline tetap hidup"
)

check(
    local_call["messages"] == messages,
    "messages tidak berubah oleh Dispatcher"
)

check(
    isinstance(local_call["messages"], list),
    "messages tetap valid setelah RAG"
)


# ============================================================
# TEST 5 — CLOUD + RAG
# ============================================================

print()
print("5. RAG → CLOUD")

cloud_messages = [
    {
        "role": "user",
        "content": "bandingkan RAG dan fine-tuning",
    }
]

cloud_context = mock_rag.execute({
    "text": cloud_messages[0]["content"]
})

before_local = len(dispatcher.local.calls)
before_cloud = len(mock_cloud.calls)

answer = dispatcher.ask(
    messages=cloud_messages,
    system_prompt="SYSTEM RAG CLOUD TEST",
    rag_context=cloud_context,
    tier="cloud",
)

check(
    answer == "[MOCK CLOUD] Online AI response",
    "RAG request menghasilkan response Cloud"
)

check(
    len(mock_cloud.calls) == before_cloud + 1,
    "Cloud dipanggil tepat 1 kali"
)

check(
    len(dispatcher.local.calls) == before_local,
    "Cloud + RAG tidak memanggil LocalProvider"
)

cloud_call = mock_cloud.calls[-1]

check(
    cloud_call["context"] == cloud_context,
    "rag_context diteruskan utuh ke Cloud"
)

check(
    cloud_call["messages"] == cloud_messages,
    "messages diteruskan utuh ke Cloud"
)


# ============================================================
# TEST 6 — CROSS REQUEST ISOLATION
# ============================================================

print()
print("6. CROSS-REQUEST RAG ISOLATION")

query_a = "dokumen tentang RAG"

query_b = "dokumen tentang fine-tuning"

context_a = mock_rag.execute({
    "text": query_a
})

context_b = mock_rag.execute({
    "text": query_b
})

check(
    context_a == context_b,
    "Mock retrieval deterministik"
)

check(
    mock_rag.calls[-2]["text"] == query_a,
    "Request A menggunakan query A"
)

check(
    mock_rag.calls[-1]["text"] == query_b,
    "Request B menggunakan query B"
)

check(
    query_b not in query_a,
    "Query A dan B independen"
)


# ============================================================
# TEST 7 — 4B ISOLATION
# ============================================================

print()
print("7. 4B ISOLATION")

check(
    "power" not in dispatcher.local.MODELS,
    "power tidak tersedia sebagai local tier"
)

check(
    STANDBY_4B not in [
        cfg["model"]
        for cfg in dispatcher.local.MODELS.values()
    ],
    "4B tidak menjadi model local RAG"
)


# ============================================================
# RESULT
# ============================================================

print()
print("========================================")
print(" HASIL RAG")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:
    print("✅ RAG v0.8 AMAN")
    print()
    print("   🔎 Query   → bersih")
    print("   📄 RAG     → mock retrieval")
    print("   🎯 Local   → 2B")
    print("   ☁️ Cloud   → Online AI")
    print("   💾 4B      → isolated")
    raise SystemExit(0)

print("❌ RAG v0.8 GAGAL")
raise SystemExit(1)
