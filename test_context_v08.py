#!/usr/bin/env python3

"""
MESIN AI v0.8 — CONTEXT ISOLATION TEST

Tujuan:
- memastikan context request tidak bocor
- memastikan memory_context di-reset
- memastikan project_context di-reset
- memastikan rag_context di-reset
- memastikan route_text tidak membawa prefix tier
"""

from pathlib import Path

MAIN = Path("main.py").read_text(encoding="utf-8")
DISPATCHER = Path("core/dispatcher.py").read_text(encoding="utf-8")

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


print()
print("========================================")
print(" MESIN AI v0.8 — CONTEXT ISOLATION TEST")
print("========================================")
print()

print("1. REQUEST CONTEXT RESET")

check(
    'memory_context = ""' in MAIN,
    "memory_context di-reset setiap request"
)

check(
    'project_context = ""' in MAIN,
    "project_context di-reset setiap request"
)

check(
    'rag_context = ""' in MAIN,
    "rag_context di-reset setiap request"
)


print()
print("2. ROUTE TEXT ISOLATION")

check(
    'llm_tier, llm_text = choose_llm_tier(user_input)' in MAIN,
    "tier command diparse sekali"
)

check(
    'route_text = llm_text if llm_text else user_input' in MAIN,
    "route_text menggunakan query bersih"
)

check(
    'router.route(route_text)' in MAIN,
    "Router menerima route_text, bukan command mentah"
)


print()
print("3. RAG QUERY ISOLATION")

check(
    '"text": route_text' in MAIN,
    "RAG menerima query bersih"
)


print()
print("4. CLOUD / LOCAL SEPARATION")

check(
    'if tier == "cloud":' in MAIN or 'tier == "cloud"' in MAIN,
    "Cloud memiliki jalur eksplisit"
)

check(
    'ask_online(messages=messages, context=rag_context' in DISPATCHER,
    "Dispatcher Cloud menerima rag_context request saat ini"
)


print()
print("========================================")
print(" HASIL")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:
    print("✅ CONTEXT v0.8 AMAN")
    raise SystemExit(0)
else:
    print("❌ CONTEXT v0.8 GAGAL")
    raise SystemExit(1)
