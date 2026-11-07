import tools.rag_coordinator as rc


PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL

    if condition:
        print(f"   ✅ {name}")
        PASS += 1
    else:
        print(f"   ❌ {name}")
        FAIL += 1


# ============================================================
# MOCK MEMORY
# ============================================================

MEMORY = {
    "kopi": "[PREFERENCES] pengguna suka kopi",
    "poco": "[FACTS] pengguna menggunakan Poco F4",
}


def mock_memory(query):
    q = query.lower()

    for key, value in MEMORY.items():
        if key in q:
            return value

    return ""


# ============================================================
# MOCK WEB
# ============================================================

WEB_CALLS = []


def mock_search(query):
    WEB_CALLS.append(query)

    return (
        [
            {
                "title": "Mock Web Result",
                "snippet": "Informasi terbaru dari Web.",
                "link": "https://example.com/mock",
            }
        ],
        "mock",
    )


def mock_fetch(urls):
    return [
        {
            "url": url,
            "html": "<html>Mock Web Content terbaru.</html>",
        }
        for url in urls
    ]


def mock_clean(item):
    return "Konten Web Mock terbaru."


# ============================================================
# PATCH DEPENDENCIES
# ============================================================

rc.get_memory_context = mock_memory
rc.route_search = mock_search
rc.fetch_parallel = mock_fetch
rc.clean_web_content = mock_clean

# Pastikan domain mock tidak diblokir
rc.BLACKLIST_DOMAINS = []


print("=" * 40)
print(" MESIN AI v0.8 — RAG POLICY MOCK TEST")
print("=" * 40)


# ============================================================
# 1. MEMORY ONLY
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("apa kopi yang saya suka")

check(
    "Memory relevan tetap digunakan",
    "pengguna suka kopi" in result
)

check(
    "Query personal tidak memanggil Web",
    len(WEB_CALLS) == 0
)


# ============================================================
# 2. MEMORY + WEB
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("harga Poco F4 terbaru")

check(
    "Memory Poco tetap dipertahankan",
    "Poco F4" in result
)

check(
    "Query terbaru memanggil Web",
    len(WEB_CALLS) == 1
)

check(
    "Web context ikut masuk",
    "Informasi terbaru dari Web" in result
)


# ============================================================
# 3. WEB ONLY
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("berita terbaru AI")

check(
    "Query Web tanpa Memory tetap berjalan",
    len(WEB_CALLS) == 1
)

check(
    "Web context tersedia",
    "Informasi terbaru dari Web" in result
)


# ============================================================
# 4. NORMAL QUERY
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("halo")

check(
    "Query normal tidak memaksa Web",
    len(WEB_CALLS) == 0
)

check(
    "Query normal tanpa Memory menghasilkan context kosong",
    result == ""
)


# ============================================================
# 5. MEMORY + TECHNICAL WEB
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("apa itu RAG")

check(
    "Pertanyaan teknis RAG boleh memakai Web",
    len(WEB_CALLS) == 1
)

check(
    "Technical Web context tersedia",
    "Informasi terbaru dari Web" in result
)


# ============================================================
# 6. CONTEXT COMBINED
# ============================================================

WEB_CALLS.clear()

result = rc.execute_rag("harga kopi terbaru")

check(
    "Combined context memiliki struktur Memory/Web",
    "=== WEB TERKINI ===" in result
)


# ============================================================
# 7. WEB GAGAL + MEMORY
# ============================================================

original_search = rc.route_search


def failing_search(query):
    raise RuntimeError("MOCK WEB OFFLINE")


rc.route_search = failing_search
WEB_CALLS.clear()

result = rc.execute_rag("harga Poco terbaru")

check(
    "Memory tetap tersedia ketika Web gagal",
    "Poco F4" in result
)

rc.route_search = original_search


# ============================================================
# 8. 4B / MODEL ISOLATION
# ============================================================

check(
    "RAG tidak mengenal / memanggil model 4B",
    "4B" not in result
)


# ============================================================
# RESULT
# ============================================================

print()
print("=" * 40)
print(" HASIL RAG POLICY")
print("=" * 40)
print(f"   PASS : {PASS}")
print(f"   FAIL : {FAIL}")

if FAIL == 0:
    print()
    print("✅ RAG POLICY v0.8 AMAN")
    print()
    print("   🧠 Memory → tetap tersedia")
    print("   🌐 Web    → hanya saat diperlukan")
    print("   🧩 Combined → Memory + Web")
    print("   🔒 Offline → tidak memaksa Web")
    print("   💾 4B → tetap isolated")
else:
    print()
    print("❌ RAG POLICY v0.8 GAGAL")
    raise SystemExit(1)
