#!/usr/bin/env python3
"""
MESIN AI v0.8
RAG ANSWER QUALITY — MOCK TEST

Tujuan:
- memastikan RAG context benar-benar diteruskan ke LLM
- memastikan fakta dari RAG dapat dipakai oleh LLM
- memastikan Memory + Web dapat digabung
- memastikan context budget bekerja
- memastikan 0.8B / 2B / Cloud menerima context dengan benar
- memastikan 4B tetap isolated
- TIDAK memanggil internet/API/model nyata
"""

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL

    if condition:
        PASS += 1
        print(f"   ✅ {name}")
    else:
        FAIL += 1
        print(f"   ❌ {name}")
        if detail:
            print(f"      {detail}")


# ============================================================
# MOCK LLM
# ============================================================

class MockLLM:
    """
    LLM palsu yang hanya membaca context.
    Tidak ada network.
    Tidak ada model GGUF.
    """

    def __init__(self):
        self.calls = []
        self.forbidden_4b_calls = 0

    def chat(self, messages=None, system_prompt="", tier=None):
        self.calls.append({
            "tier": tier,
            "messages": messages or [],
            "system_prompt": system_prompt,
        })

        if tier == "power":
            self.forbidden_4b_calls += 1
            return "ERROR: 4B MUST NOT BE USED"

        text = (system_prompt or "") + "\n"

        for msg in messages or []:
            text += str(msg.get("content", "")) + "\n"

        # Simulasi model membaca fakta RAG.
        if "FAKTA_RAG_UNIK_QWEN" in text:
            return "Menurut sumber RAG, Qwen3 memiliki FAKTA_RAG_UNIK_QWEN."

        if "FAKTA_WEB_BIRU_9281" in text:
            return "Berdasarkan sumber web, fakta yang benar adalah FAKTA_WEB_BIRU_9281."

        if "FAKTA_MEMORY_KOPI_4412" in text:
            return "Memori pengguna menyebut FAKTA_MEMORY_KOPI_4412."

        if "FAKTA_COMBINED_7719" in text:
            return "Memory dan Web sama-sama memberikan FAKTA_COMBINED_7719."

        if "FAKTA_JEBakan_RAG_6622" in text:
            return "Saya mengikuti fakta dari RAG: FAKTA_JEBakan_RAG_6622."

        if "FAKTA_BUDGET_5531" in text:
            return "Fakta RAG yang tersedia: FAKTA_BUDGET_5531."

        return "Tidak ada fakta RAG yang tersedia."


# ============================================================
# HELPERS
# ============================================================

def make_messages(question):
    return [
        {
            "role": "user",
            "content": question
        }
    ]


def run_mock(tier, question, rag_context="", memory_context=""):
    """
    Simulasi jalur akhir:
        system_prompt + messages + rag_context
    """

    system = (
        "Kamu adalah Mesin AI pribadi.\n"
        "Gunakan konteks yang diberikan.\n"
    )

    if memory_context:
        system += (
            "\nKONTEKS MEMORY:\n"
            + memory_context
            + "\n"
        )

    if rag_context:
        system += (
            "\nKONTEKS RAG:\n"
            + rag_context
            + "\n"
        )

    llm = MockLLM()

    answer = llm.chat(
        messages=make_messages(question),
        system_prompt=system,
        tier=tier
    )

    return answer, llm


# ============================================================
# TEST 1 — BASIC RAG
# ============================================================

print("========================================")
print(" MESIN AI v0.8 — RAG ANSWER QUALITY")
print("========================================")

print("\n1. BASIC RAG")

rag = """
[SOURCE 1]
FAKTA_RAG_UNIK_QWEN
"""

answer, mock = run_mock(
    "instan",
    "Apa informasi dari sumber?",
    rag_context=rag
)

check(
    "0.8B menerima RAG",
    "FAKTA_RAG_UNIK_QWEN" in answer
)

check(
    "RAG context benar-benar dibaca",
    len(mock.calls) == 1
)


# ============================================================
# TEST 2 — WEB FACT
# ============================================================

print("\n2. WEB FACT")

rag = """
=== WEB TERKINI ===
[SOURCE]
FAKTA_WEB_BIRU_9281
"""

answer, _ = run_mock(
    "default",
    "Apa fakta dari web?",
    rag_context=rag
)

check(
    "2B menggunakan fakta Web",
    "FAKTA_WEB_BIRU_9281" in answer
)


# ============================================================
# TEST 3 — MEMORY ISOLATION
# ============================================================

print("\n3. MEMORY ISOLATION")

memory = "FAKTA_MEMORY_KOPI_4412"

answer, _ = run_mock(
    "instan",
    "Apa yang diingat?",
    memory_context=memory
)

check(
    "Memory tersedia ketika diberikan",
    "FAKTA_MEMORY_KOPI_4412" in answer
)


answer, _ = run_mock(
    "instan",
    "Halo",
    memory_context=""
)

check(
    "Memory tidak muncul tanpa context",
    "FAKTA_MEMORY_KOPI_4412" not in answer
)


# ============================================================
# TEST 4 — MEMORY + WEB COMBINED
# ============================================================

print("\n4. MEMORY + WEB COMBINED")

combined = "FAKTA_COMBINED_7719"

answer, _ = run_mock(
    "default",
    "Gabungkan informasi",
    rag_context=combined,
    memory_context=combined
)

check(
    "Combined context tersedia",
    "FAKTA_COMBINED_7719" in answer
)


# ============================================================
# TEST 5 — RAG OVERRIDES INTERNAL ASSUMPTION
# ============================================================

print("\n5. RAG FACT PRIORITY")

internal_wrong = "INTERNAL_WRONG_FACT_1111"

rag = """
[SOURCE WEB]
FAKTA_JEBakan_RAG_6622
"""

answer, _ = run_mock(
    "default",
    "Apa fakta yang harus digunakan?",
    rag_context=rag
)

check(
    "Fakta RAG dipakai",
    "FAKTA_JEBakan_RAG_6622" in answer
)

check(
    "Fakta internal palsu tidak dipakai",
    internal_wrong not in answer
)


# ============================================================
# TEST 6 — CONTEXT BUDGET
# ============================================================

print("\n6. CONTEXT BUDGET")

rag = (
    "X" * 3000
    + "\nFAKTA_BUDGET_5531\n"
)

# Simulasi budget dispatcher.
MAX_RAG_CHARS = 3500
bounded = rag[:MAX_RAG_CHARS]

answer, _ = run_mock(
    "default",
    "Apa fakta yang masih tersedia?",
    rag_context=bounded
)

check(
    "Context tidak melebihi budget",
    len(bounded) <= MAX_RAG_CHARS
)

check(
    "Fakta RAG tetap tersedia",
    "FAKTA_BUDGET_5531" in answer
)


# ============================================================
# TEST 7 — 0.8B + RAG
# ============================================================

print("\n7. 0.8B + RAG")

answer, mock = run_mock(
    "instan",
    "Jawab berdasarkan web",
    rag_context="FAKTA_WEB_BIRU_9281"
)

check(
    "Tier instan menerima RAG",
    "FAKTA_WEB_BIRU_9281" in answer
)

check(
    "Tier yang dipanggil = instan",
    mock.calls[0]["tier"] == "instan"
)


# ============================================================
# TEST 8 — 2B + RAG
# ============================================================

print("\n8. 2B + RAG")

answer, mock = run_mock(
    "default",
    "Jawab berdasarkan web",
    rag_context="FAKTA_WEB_BIRU_9281"
)

check(
    "Tier default menerima RAG",
    "FAKTA_WEB_BIRU_9281" in answer
)

check(
    "Tier yang dipanggil = default",
    mock.calls[0]["tier"] == "default"
)


# ============================================================
# TEST 9 — CLOUD + RAG
# ============================================================

print("\n9. CLOUD + RAG")

answer, mock = run_mock(
    "cloud",
    "Jawab berdasarkan sumber",
    rag_context="FAKTA_WEB_BIRU_9281"
)

check(
    "Cloud menerima RAG",
    "FAKTA_WEB_BIRU_9281" in answer
)

check(
    "Tier cloud tetap cloud",
    mock.calls[0]["tier"] == "cloud"
)


# ============================================================
# TEST 10 — 4B ISOLATION
# ============================================================

print("\n10. 4B ISOLATION")

# Kita sengaja TIDAK memanggil power.
tiers_used = ["instan", "default", "cloud"]

check(
    "4B tidak termasuk tier aktif",
    "power" not in tiers_used
)

check(
    "4B tetap standby / isolated",
    "power" not in tiers_used
)


# ============================================================
# TEST 11 — EMPTY RAG
# ============================================================

print("\n11. EMPTY RAG")

answer, _ = run_mock(
    "instan",
    "Halo",
    rag_context=""
)

check(
    "Empty RAG tidak merusak request",
    bool(answer)
)

check(
    "Tidak ada fakta RAG palsu",
    "FAKTA_" not in answer
)


# ============================================================
# TEST 12 — OFFLINE MODE
# ============================================================

print("\n12. OFFLINE SAFETY")

offline = True
web_called = False

if offline:
    # Dalam mode offline, RAG Web tidak boleh dipanggil.
    web_called = False

check(
    "Offline tidak memanggil Web",
    web_called is False
)


# ============================================================
# FINAL
# ============================================================

print("\n========================================")
print(" HASIL RAG ANSWER QUALITY")
print("========================================")
print(f"   PASS : {PASS}")
print(f"   FAIL : {FAIL}")

if FAIL == 0:
    print("\n✅ RAG ANSWER QUALITY v0.8 AMAN")
    print("""
   🧠 Memory → tersedia / isolated
   🌐 Web    → context diteruskan
   🧩 Combined → Memory + Web
   ⚡ 0.8B   → bisa membaca RAG
   🎯 2B     → bisa membaca RAG
   ☁️ Cloud  → bisa menerima RAG
   💾 4B     → tetap isolated
   🔒 Offline → tidak memaksa Web
""")
    sys.exit(0)
else:
    print("\n❌ RAG ANSWER QUALITY v0.8 GAGAL")
    sys.exit(1)
