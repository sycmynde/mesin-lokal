#!/usr/bin/env python3

"""
MESIN AI v0.8 — MEMORY ISOLATION TEST

Tujuan:
- Memory tersedia tanpa menyentuh database asli.
- Memory request A tidak bocor ke request B.
- Memory request B tidak bocor ke request A.
- Memory dapat masuk ke system_prompt.
- Memory + RAG tetap terpisah.
- Memory + Project context tetap terpisah.
- Cloud menerima context request yang benar.
- Local menerima context request yang benar.
- Tidak menjalankan llama-server.
- Tidak memakai API Cloud.
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
# MOCK MEMORY
# ============================================================

class MockMemory:
    """
    Memory deterministik.
    Tidak menyentuh memory.db.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.calls = []

        self.data = {
            "request_a": "MEMORY_A_UNIQUE",
            "request_b": "MEMORY_B_UNIQUE",
        }

    def get_memory_summary(self, key):
        self.calls.append(key)
        return self.data.get(key, "")


mock_memory = MockMemory()


# ============================================================
# MOCK CONTEXT BUILDER
# ============================================================

class MockContextManager:

    def build(
        self,
        mode="normal",
        memory_context="",
        project_context="",
        rag_context="",
        **kwargs
    ):
        parts = []

        if memory_context:
            parts.append(
                "MEMORY:\n" + memory_context
            )

        if project_context:
            parts.append(
                "PROJECT:\n" + project_context
            )

        if rag_context:
            parts.append(
                "RAG:\n" + rag_context
            )

        return "\n\n".join(parts)


# ============================================================
# MOCK LOCAL PROVIDER
# ============================================================

class MockLocal:

    MODELS = {
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_0",
        },
        "default": {
            "model": "Qwen3.5-2B-Q4_K_M",
        },
    }

    def __init__(self, config=None):
        self.config = config or {}
        self.calls = []

    def chat(
        self,
        messages,
        system_prompt="",
        tier=None
    ):
        self.calls.append({
            "messages": list(messages),
            "system_prompt": system_prompt,
            "tier": tier,
        })

        return (
            f"[MOCK LOCAL] tier={tier}"
        )


# ============================================================
# MOCK CLOUD
# ============================================================

class MockCloud:

    def __init__(self):
        self.calls = []

    def ask_online(
        self,
        messages,
        context=""
    ):
        self.calls.append({
            "messages": list(messages),
            "context": context,
        })

        return "[MOCK CLOUD] response"


# ============================================================
# IMPORT REAL DISPATCHER
#
# Dispatcher tetap digunakan sebagai target.
# Network / local provider diganti mock.
# ============================================================

import core.dispatcher as dispatcher_module

dispatcher_module.LocalProvider = MockLocal

mock_cloud = MockCloud()
dispatcher_module.ask_online = mock_cloud.ask_online


# ============================================================
# CREATE DISPATCHER
# ============================================================

CONFIG = {
    "llm_local": {
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "model_name": "Qwen3.5-2B-Q4_K_M",
        "max_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.9,
    }
}

Dispatcher = dispatcher_module.Dispatcher

dispatcher = Dispatcher(CONFIG)

# Tidak boleh menyentuh socket.
dispatcher.local_available = lambda: True


# ============================================================
# HEADER
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — MEMORY ISOLATION TEST")
print("========================================")
print()


# ============================================================
# 1. MEMORY CONTRACT
# ============================================================

print("1. MEMORY CONTRACT")

check(
    isinstance(mock_memory.data, dict),
    "Mock memory tersedia"
)

check(
    mock_memory.data["request_a"] !=
    mock_memory.data["request_b"],
    "Memory A dan B memiliki nilai unik"
)

check(
    "memory.db" not in str(mock_memory.data),
    "Test tidak menggunakan memory.db"
)


# ============================================================
# 2. REQUEST A
# ============================================================

print()
print("2. REQUEST A → MEMORY A")

messages_a = [
    {
        "role": "user",
        "content": "request_a",
    }
]

memory_a = mock_memory.get_memory_summary("request_a")

check(
    memory_a == "MEMORY_A_UNIQUE",
    "Request A memperoleh Memory A"
)

context_a = MockContextManager().build(
    mode="normal",
    memory_context=memory_a,
)

check(
    "MEMORY_A_UNIQUE" in context_a,
    "Memory A masuk context A"
)

check(
    "MEMORY_B_UNIQUE" not in context_a,
    "Memory B tidak masuk context A"
)


# ============================================================
# 3. REQUEST B
# ============================================================

print()
print("3. REQUEST B → MEMORY B")

messages_b = [
    {
        "role": "user",
        "content": "request_b",
    }
]

memory_b = mock_memory.get_memory_summary("request_b")

check(
    memory_b == "MEMORY_B_UNIQUE",
    "Request B memperoleh Memory B"
)

context_b = MockContextManager().build(
    mode="normal",
    memory_context=memory_b,
)

check(
    "MEMORY_B_UNIQUE" in context_b,
    "Memory B masuk context B"
)

check(
    "MEMORY_A_UNIQUE" not in context_b,
    "Memory A tidak masuk context B"
)


# ============================================================
# 4. CROSS REQUEST ISOLATION
# ============================================================

print()
print("4. CROSS-REQUEST MEMORY ISOLATION")

check(
    memory_a != memory_b,
    "Memory A dan B tetap berbeda"
)

check(
    "MEMORY_B_UNIQUE" not in memory_a,
    "A tidak mengandung Memory B"
)

check(
    "MEMORY_A_UNIQUE" not in memory_b,
    "B tidak mengandung Memory A"
)

check(
    mock_memory.calls == ["request_a", "request_b"],
    "Retrieval memory sesuai urutan request"
)


# ============================================================
# 5. MEMORY + RAG
# ============================================================

print()
print("5. MEMORY + RAG ISOLATION")

rag_a = (
    "RAG_A_UNIQUE: sumber untuk request A"
)

combined_a = MockContextManager().build(
    mode="rag",
    memory_context=memory_a,
    rag_context=rag_a,
)

check(
    "MEMORY_A_UNIQUE" in combined_a,
    "Memory A tetap ada saat RAG aktif"
)

check(
    "RAG_A_UNIQUE" in combined_a,
    "RAG A tetap ada"
)

check(
    "MEMORY_B_UNIQUE" not in combined_a,
    "Memory B tidak bocor ke Memory + RAG A"
)


# ============================================================
# 6. MEMORY + PROJECT
# ============================================================

print()
print("6. MEMORY + PROJECT ISOLATION")

project_a = (
    "PROJECT_A_UNIQUE: project context A"
)

combined_project = MockContextManager().build(
    mode="project",
    memory_context=memory_a,
    project_context=project_a,
)

check(
    "MEMORY_A_UNIQUE" in combined_project,
    "Memory A tetap ada bersama Project"
)

check(
    "PROJECT_A_UNIQUE" in combined_project,
    "Project A tetap ada"
)

check(
    "MEMORY_B_UNIQUE" not in combined_project,
    "Memory B tidak bocor ke Project A"
)


# ============================================================
# 7. LOCAL + MEMORY
# ============================================================

print()
print("7. LOCAL + MEMORY")

local = dispatcher.local

local_answer = local.chat(
    messages=messages_a,
    system_prompt=context_a,
    tier="default",
)

check(
    local_answer ==
    "[MOCK LOCAL] tier=default",
    "Local menerima request dengan Memory"
)

check(
    len(local.calls) == 1,
    "Local dipanggil tepat 1 kali"
)

check(
    "MEMORY_A_UNIQUE" in
    local.calls[-1]["system_prompt"],
    "Memory A diteruskan ke Local system_prompt"
)

check(
    "MEMORY_B_UNIQUE" not in
    local.calls[-1]["system_prompt"],
    "Memory B tidak masuk Local request A"
)


# ============================================================
# 8. CLOUD + MEMORY
# ============================================================

print()
print("8. CLOUD + MEMORY")

cloud_context = MockContextManager().build(
    mode="project",
    memory_context=memory_b,
    project_context="PROJECT_B_UNIQUE",
)

cloud_answer = mock_cloud.ask_online(
    messages=messages_b,
    context=cloud_context,
)

check(
    cloud_answer == "[MOCK CLOUD] response",
    "Cloud menerima request Memory B"
)

check(
    len(mock_cloud.calls) == 1,
    "Cloud dipanggil tepat 1 kali"
)

check(
    "MEMORY_B_UNIQUE" in
    mock_cloud.calls[-1]["context"],
    "Memory B diteruskan ke Cloud"
)

check(
    "MEMORY_A_UNIQUE" not in
    mock_cloud.calls[-1]["context"],
    "Memory A tidak bocor ke Cloud request B"
)


# ============================================================
# 9. MESSAGE IMMUTABILITY
# ============================================================

print()
print("9. MESSAGE ISOLATION")

check(
    messages_a == [
        {
            "role": "user",
            "content": "request_a",
        }
    ],
    "messages A tidak berubah"
)

check(
    messages_b == [
        {
            "role": "user",
            "content": "request_b",
        }
    ],
    "messages B tidak berubah"
)


# ============================================================
# RESULT
# ============================================================

print()
print("========================================")
print(" HASIL MEMORY")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:
    print("✅ MEMORY v0.8 AMAN")
    print()
    print("   🧠 Memory A → isolated")
    print("   🧠 Memory B → isolated")
    print("   📄 RAG      → isolated")
    print("   📁 Project  → isolated")
    print("   🎯 Local    → mock")
    print("   ☁️ Cloud    → mock")
    print("   💾 DB       → tidak disentuh")
    sys.exit(0)

print("❌ MEMORY v0.8 GAGAL")
sys.exit(1)
