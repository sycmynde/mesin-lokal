#!/usr/bin/env python3

"""
MESIN AI v0.8
Tier Regression Test

Arsitektur resmi:
    /instan  -> local 0.8B
    /default -> local 2B
    /power   -> cloud

4B lokal = standby / non-tier.
"""

import sys

from main import choose_llm_tier
from providers.local import LocalProvider


# ============================================================
# EXPECTED ARCHITECTURE
# ============================================================

EXPECTED_MODELS = {
    "instan": "Qwen3.5-0.8B-Q4_0",
    "default": "Qwen3.5-2B-Q4_K_M",
}

EXPECTED_CLOUD_TIER = "cloud"

STANDBY_MODEL = "Qwen3.5-4B-Q4_K_M"


# ============================================================
# TEST HELPERS
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


def assert_equal(name, actual, expected):
    if actual == expected:
        ok(name)
    else:
        fail(
            name,
            f"expected={expected!r}, actual={actual!r}"
        )


# ============================================================
# TEST 1 — LOCAL PROVIDER TIERS
# ============================================================

print()
print("========================================")
print(" MESIN AI v0.8 — TIER REGRESSION TEST")
print("========================================")
print()

print("1. LOCAL PROVIDER")

actual_tiers = set(LocalProvider.MODELS.keys())
expected_tiers = set(EXPECTED_MODELS.keys())

assert_equal(
    "Tier lokal hanya instan + default",
    actual_tiers,
    expected_tiers
)

for tier, expected_model in EXPECTED_MODELS.items():

    cfg = LocalProvider.MODELS.get(tier)

    if cfg is None:
        fail(
            f"Tier {tier} tersedia"
        )
        continue

    assert_equal(
        f"{tier} → model benar",
        cfg.get("model"),
        expected_model
    )


# ============================================================
# TEST 2 — 4B MUST NOT BE LOCAL TIER
# ============================================================

print()
print("2. 4B STANDBY / NON-TIER")

if "power" not in LocalProvider.MODELS:
    ok("power tidak terdaftar sebagai LocalProvider tier")
else:
    fail(
        "power tidak terdaftar sebagai LocalProvider tier",
        "4B/power masih terdaftar sebagai model lokal"
    )

if STANDBY_MODEL not in [
    cfg.get("model")
    for cfg in LocalProvider.MODELS.values()
]:
    ok("Qwen3.5-4B-Q4_K_M tidak dipakai sebagai tier lokal")
else:
    fail(
        "Qwen3.5-4B-Q4_K_M tidak dipakai sebagai tier lokal"
    )


# ============================================================
# TEST 3 — COMMAND ROUTING
# ============================================================

print()
print("3. COMMAND ROUTING")


routing_tests = [
    (
        "/instan halo",
        "instan",
        "halo",
    ),
    (
        "/default jelaskan RAG",
        "default",
        "jelaskan RAG",
    ),
    (
        "/power jelaskan RAG",
        "cloud",
        "jelaskan RAG",
    ),
    (
        "/power apa itu fine-tuning?",
        "cloud",
        "apa itu fine-tuning?",
    ),
]


for query, expected_tier, expected_text in routing_tests:

    try:
        tier, text = choose_llm_tier(query)

        assert_equal(
            f"{query} → tier",
            tier,
            expected_tier
        )

        assert_equal(
            f"{query} → query bersih",
            text,
            expected_text
        )

    except Exception as e:
        fail(
            f"{query} → routing",
            repr(e)
        )


# ============================================================
# TEST 4 — NO POWER LOCAL ROUTE
# ============================================================

print()
print("4. POWER = CLOUD")

try:
    tier, text = choose_llm_tier("/power test")

    if tier == EXPECTED_CLOUD_TIER:
        ok("/power tidak diarahkan ke LocalProvider")
    else:
        fail(
            "/power tidak diarahkan ke LocalProvider",
            f"tier={tier!r}"
        )

except Exception as e:
    fail(
        "/power routing",
        repr(e)
    )


# ============================================================
# TEST 5 — DEFAULT FALLBACK
# ============================================================

print()
print("5. DEFAULT FALLBACK")

fallback_tests = [
    "halo",
    "jelaskan RAG",
    "apa itu AI",
]

for query in fallback_tests:

    try:
        tier, text = choose_llm_tier(query)

        # Pertanyaan ringan bisa masuk instan.
        # Pertanyaan normal minimal harus instan/default,
        # tetapi tidak boleh cloud secara tidak sengaja.
        if tier in ("instan", "default"):
            ok(f"{query!r} → local tier {tier}")
        else:
            fail(
                f"{query!r} → bukan cloud",
                f"tier={tier!r}"
            )

    except Exception as e:
        fail(
            f"{query!r} → fallback routing",
            repr(e)
        )


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("========================================")
print(" HASIL")
print("========================================")
print(f"   PASS : {passed}")
print(f"   FAIL : {failed}")
print()

if failed:
    print("❌ TIER v0.8 GAGAL")
    print()
    print("Arsitektur yang diharapkan:")
    print("   ⚡ instan  → Qwen3.5-0.8B-Q4_0")
    print("   🎯 default → Qwen3.5-2B-Q4_K_M")
    print("   ☁️ cloud   → Online AI")
    print("   💾 4B      → standby / non-tier")
    print()
    sys.exit(1)

print("✅ TIER v0.8 AMAN")
print()
print("   ⚡ instan  → Qwen3.5-0.8B-Q4_0")
print("   🎯 default → Qwen3.5-2B-Q4_K_M")
print("   ☁️ power   → Cloud")
print("   💾 4B      → standby / non-tier")
print()
sys.exit(0)
