#!/usr/bin/env python3

"""
MESIN AI v0.8 — CONTEXT BUDGET TEST

Tujuan:
- memastikan memory tidak otomatis diinjeksi untuk semua request
- memastikan ContextManager tetap menjadi pengatur context
- memastikan RAG tetap bisa diteruskan
- memastikan identity/system pipeline tetap hidup
- mencegah prompt kecil dibebani memory global
"""

from pathlib import Path

MAIN = Path("main.py").read_text(encoding="utf-8")
CTX = Path("core/context_manager.py").read_text(encoding="utf-8")
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
print(" MESIN AI v0.8 — CONTEXT BUDGET TEST")
print("========================================")
print()

print("1. CONTEXT MANAGER OWNERSHIP")

check(
    "def build(" in CTX,
    "ContextManager memiliki build()"
)

check(
    "_should_inject_memory" in CTX,
    "Memory memiliki gate relevansi"
)

check(
    "_should_inject_project" in CTX,
    "Project memiliki gate relevansi"
)

check(
    'if rag_context:' in DISPATCHER,
    "RAG hanya ditambahkan ketika tersedia (gate di dispatcher)"
)


print()
print("2. REQUEST CONTEXT RESET")

check(
    'memory_context = ""' in MAIN,
    "memory_context reset per request"
)

check(
    'project_context = ""' in MAIN,
    "project_context reset per request"
)

check(
    'rag_context = ""' in MAIN,
    "rag_context reset per request"
)


print()
print("3. MEMORY SHOULD NOT BE GLOBAL")

# Dispatcher lama melakukan:
# get_memory_summary() -> setiap request.
# Ini justru yang ingin kita hilangkan dari jalur global.

check(
    'get_memory_summary' not in DISPATCHER,
    "Dispatcher tidak menyuntikkan seluruh memory secara global"
)


print()
print("4. SYSTEM IDENTITY PRESERVATION")

check(
    "Cermin" in DISPATCHER or "cermin" in DISPATCHER,
    "Identity/cermin pipeline tetap tersedia"
)

check(
    "system_prompt" in DISPATCHER,
    "system_prompt tetap diteruskan"
)

check(
    "messages=messages" in DISPATCHER,
    "messages tetap diteruskan"
)


print()
print("5. RAG PRESERVATION")

check(
    "rag_context" in DISPATCHER,
    "Dispatcher tetap menerima rag_context"
)

check(
    'context=rag_context' in DISPATCHER,
    "Cloud tetap menerima rag_context"
)


print()
print("6. LOCAL / CLOUD SEPARATION")

check(
    'if tier == "cloud":' in DISPATCHER,
    "Cloud memiliki jalur eksplisit"
)

check(
    "provider.chat(" in DISPATCHER,
    "LocalProvider tetap memiliki jalur sendiri"
)


print()
print("========================================")
print(" HASIL CONTEXT BUDGET")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed == 0:
    print("✅ CONTEXT BUDGET v0.8 AMAN")
    print()
    print("   🧠 Memory → gated / relevan")
    print("   📁 Project → gated / relevan")
    print("   📄 RAG → preserved")
    print("   🪞 Identity → preserved")
    print("   🎯 Local → preserved")
    print("   ☁️ Cloud → preserved")
    raise SystemExit(0)

print("❌ CONTEXT BUDGET v0.8 GAGAL")
raise SystemExit(1)
