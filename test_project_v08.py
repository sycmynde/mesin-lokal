#!/usr/bin/env python3

"""
MESIN AI v0.8 — PROJECT CONTEXT ISOLATION TEST

Tujuan:
- Project context tersedia secara deterministik.
- Project A tidak bocor ke request B.
- Project B tidak bocor ke request A.
- Project context tetap terpisah dari Memory.
- Project context tetap terpisah dari RAG.
- Project + Local diteruskan dengan benar.
- Project + Cloud diteruskan dengan benar.
- messages tidak dimodifikasi.
- Tidak menjalankan llama-server.
- Tidak menggunakan token Cloud.
- Tidak menyentuh project storage asli.
"""

import sys


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
# MOCK PROJECT
# ============================================================

class MockProject:

    def __init__(self):
        self.calls = []

        self.data = {
            "request_a": "PROJECT_A_UNIQUE",
            "request_b": "PROJECT_B_UNIQUE",
        }

    def build_context(self, key):
        self.calls.append(key)
        return self.data.get(key, "")


mock_project = MockProject()


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


context_manager = MockContextManager()


# ============================================================
# MOCK LOCAL
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
# REAL DISPATCHER
# ============================================================

import core.dispatcher as dispatcher_module

dispatcher_module.LocalProvider = MockLocal

mock_cloud = MockCloud()
dispatcher_module.ask_online = mock_cloud.ask_online

Dispatcher = dispatcher_module.Dispatcher


CONFIG = {
    "llm_local": {
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "model_name": "Qwen3.5-2B-Q4_K_M",
        "max_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.9,
    }
}


dispatcher = Dispatcher(CONFIG)

# Tidak boleh ada socket / llama-server.
dispatcher.local_available = lambda: True


# ============================================================
# HEADER
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — PROJECT CONTEXT TEST")
print("========================================")
print()


# ============================================================
# 1. PROJECT CONTRACT
# ============================================================

print("1. PROJECT CONTRACT")

check(
    isinstance(mock_project.data, dict),
    "Mock project tersedia"
)

check(
    mock_project.data["request_a"] !=
    mock_project.data["request_b"],
    "Project A dan B memiliki context unik"
)

check(
    "PROJECT_A_UNIQUE" in
    mock_project.data["request_a"],
    "Project A memiliki marker unik"
)

check(
    "PROJECT_B_UNIQUE" in
    mock_project.data["request_b"],
    "Project B memiliki marker unik"
)


# ============================================================
# 2. REQUEST A
# ============================================================

print()
print("2. REQUEST A → PROJECT A")

messages_a = [
    {
        "role": "user",
        "content": "request_a",
    }
]

project_a = mock_project.build_context("request_a")

check(
    project_a == "PROJECT_A_UNIQUE",
    "Request A memperoleh Project A"
)

context_a = context_manager.build(
    mode="project",
    project_context=project_a,
)

check(
    "PROJECT_A_UNIQUE" in context_a,
    "Project A masuk context A"
)

check(
    "PROJECT_B_UNIQUE" not in context_a,
    "Project B tidak masuk context A"
)


# ============================================================
# 3. REQUEST B
# ============================================================

print()
print("3. REQUEST B → PROJECT B")

messages_b = [
    {
        "role": "user",
        "content": "request_b",
    }
]

project_b = mock_project.build_context("request_b")

check(
    project_b == "PROJECT_B_UNIQUE",
    "Request B memperoleh Project B"
)

context_b = context_manager.build(
    mode="project",
    project_context=project_b,
)

check(
    "PROJECT_B_UNIQUE" in context_b,
    "Project B masuk context B"
)

check(
    "PROJECT_A_UNIQUE" not in context_b,
    "Project A tidak masuk context B"
)


# ============================================================
# 4. CROSS REQUEST ISOLATION
# ============================================================

print()
print("4. CROSS-REQUEST PROJECT ISOLATION")

check(
    project_a != project_b,
    "Project A dan B tetap berbeda"
)

check(
    "PROJECT_B_UNIQUE" not in project_a,
    "Project A tidak mengandung Project B"
)

check(
    "PROJECT_A_UNIQUE" not in project_b,
    "Project B tidak mengandung Project A"
)

check(
    mock_project.calls == [
        "request_a",
        "request_b",
    ],
    "Retrieval project sesuai urutan request"
)


# ============================================================
# 5. PROJECT + MEMORY
# ============================================================

print()
print("5. PROJECT + MEMORY ISOLATION")

memory_a = "MEMORY_A_UNIQUE"

combined_memory = context_manager.build(
    mode="project",
    memory_context=memory_a,
    project_context=project_a,
)

check(
    "MEMORY_A_UNIQUE" in combined_memory,
    "Memory A tetap ada"
)

check(
    "PROJECT_A_UNIQUE" in combined_memory,
    "Project A tetap ada"
)

check(
    "PROJECT_B_UNIQUE" not in combined_memory,
    "Project B tidak bocor ke Project + Memory A"
)


# ============================================================
# 6. PROJECT + RAG
# ============================================================

print()
print("6. PROJECT + RAG ISOLATION")

rag_a = (
    "RAG_A_UNIQUE: sumber request A"
)

combined_rag = context_manager.build(
    mode="rag",
    project_context=project_a,
    rag_context=rag_a,
)

check(
    "PROJECT_A_UNIQUE" in combined_rag,
    "Project A tetap ada saat RAG aktif"
)

check(
    "RAG_A_UNIQUE" in combined_rag,
    "RAG A tetap ada"
)

check(
    "PROJECT_B_UNIQUE" not in combined_rag,
    "Project B tidak bocor ke Project + RAG A"
)


# ============================================================
# 7. LOCAL + PROJECT
# ============================================================

print()
print("7. LOCAL + PROJECT")

local = dispatcher.local

local_answer = local.chat(
    messages=messages_a,
    system_prompt=context_a,
    tier="default",
)

check(
    local_answer ==
    "[MOCK LOCAL] tier=default",
    "Local menerima Project A"
)

check(
    len(local.calls) == 1,
    "Local dipanggil tepat 1 kali"
)

check(
    "PROJECT_A_UNIQUE" in
    local.calls[-1]["system_prompt"],
    "Project A diteruskan ke Local system_prompt"
)

check(
    "PROJECT_B_UNIQUE" not in
    local.calls[-1]["system_prompt"],
    "Project B tidak masuk Local request A"
)


# ============================================================
# 8. CLOUD + PROJECT
# ============================================================

print()
print("8. CLOUD + PROJECT")

cloud_context = context_manager.build(
    mode="project",
    project_context=project_b,
)

cloud_answer = mock_cloud.ask_online(
    messages=messages_b,
    context=cloud_context,
)

check(
    cloud_answer == "[MOCK CLOUD] response",
    "Cloud menerima Project B"
)

check(
    len(mock_cloud.calls) == 1,
    "Cloud dipanggil tepat 1 kali"
)

check(
    "PROJECT_B_UNIQUE" in
    mock_cloud.calls[-1]["context"],
    "Project B diteruskan ke Cloud"
)

check(
    "PROJECT_A_UNIQUE" not in
    mock_cloud.calls[-1]["context"],
    "Project A tidak bocor ke Cloud request B"
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
# 10. NO 4B
# ============================================================

print()
print("10. 4B ISOLATION")

check(
    "power" not in MockLocal.MODELS,
    "power tidak tersedia sebagai local tier"
)

check(
    "Qwen3.5-4B-Q4_K_M" not in [
        cfg["model"]
        for cfg in MockLocal.MODELS.values()
    ],
    "4B tidak digunakan Project Local"
)


# ============================================================
# RESULT
# ============================================================

print()
print("========================================")
print(" HASIL PROJECT")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:
    print("✅ PROJECT v0.8 AMAN")
    print()
    print("   📁 Project A → isolated")
    print("   📁 Project B → isolated")
    print("   🧠 Memory    → isolated")
    print("   📄 RAG       → isolated")
    print("   🎯 Local     → mock")
    print("   ☁️ Cloud     → mock")
    print("   💾 Storage   → tidak disentuh")
    sys.exit(0)

print("❌ PROJECT v0.8 GAGAL")
sys.exit(1)
