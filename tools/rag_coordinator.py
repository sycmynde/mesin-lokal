import json
import os
import re
from tools.search_router import route_search
from tools.fetcher import fetch_parallel
from tools.web_cleaner import clean_web_content

FRESH_WORDS = (
    "terbaru", "hari ini", "sekarang", "latest", "today",
    "harga", "price", "kurs", "update", "jadwal", "berita", "cuaca"
)

CASUAL_WORDS = (
    "halo", "hai", "hei", "pagi", "siang", "sore", "malam",
    "apa kabar", "terima kasih", "makasih", "siapa kamu", "tes", "test"
)

def get_memory_context(query: str) -> str:
    """Cari ingatan relevan dari SQLite via memory_manager."""
    from core.memory_manager import search_memory
    results = search_memory(query)
    return "\n".join(results) if results else ""

def execute_rag(query=None, text=None, max_sources: int = 8) -> str:
    """
    Alur RAG Cerdas:
    - Personal/Memory only -> Memory
    - Fresh/Pricing/Temporal with Memory -> Memory + Web
    - Technical/Fresh without Memory -> Web only
    - Casual/Normal query -> Empty (no web call)
    """
    if query is None and text is not None:
        query = text
    if query is None:
        return "[CATATAN SISTEM: parameter query/text wajib disediakan]"
    q_lower = query.lower().strip()
    wants_fresh = any(w in q_lower for w in FRESH_WORDS)
    is_technical = any(q_lower.startswith(w) or f" {w} " in f" {q_lower} " for w in ("apa itu", "jelaskan", "definisi", "bagaimana", "cara", "mengapa", "kenapa"))
    is_casual = any(q_lower == w or q_lower.startswith(w + " ") for w in CASUAL_WORDS)

    # 1. Cek Memory Internal Dulu
    print("   🧠 Mengecek Memory Internal...")
    memory_context = get_memory_context(query)

    if memory_context:
        print("   ✅ Ditemukan memori relevan.")
        print(f"   ✅ Konteks Memory siap ({len(memory_context)} karakter)")
        if not wants_fresh:
            return memory_context[:5000]

    # Casual query tanpa trigger fresh / technical tidak perlu cari web
    if not memory_context and is_casual and not wants_fresh and not is_technical:
        return ""

    # 2. Cari ke Web jika diperlukan
    print(f"   🔍 {'Mencari data web terkini' if memory_context else 'Memory kosong, routing pencarian Web'} untuk: '{query}'")
    q_search = re.sub(r'\bbrapa\b', 'berapa', query, flags=re.I)

    try:
        results, source_type = route_search(q_search)
    except Exception as e:
        print(f"   ⚠️ [Web Search Error] {e}")
        if memory_context:
            return memory_context[:5000]
        return ""

    if not results:
        if memory_context:
            return memory_context[:5000]
        return ("[CATATAN SISTEM: pencarian web gagal atau tidak menemukan hasil. Jawab jujur bahwa kamu tidak memiliki data terkini untuk pertanyaan ini; jangan mengarang angka atau fakta; jangan menyebut angka harga dari ingatan lama; tawarkan mencari ulang saat online.]")

    print(f"   📡 Sumber: {str(source_type).upper()} | Ditemukan {len(results)} hasil")

    urls = [r.get('link', r.get('html_url', '')) for r in results if r.get('link') or r.get('html_url')]
    urls = [u for u in urls if u.startswith('http')][:max_sources]

    context_parts = []
    if not urls:
        for i, r in enumerate(results[:max_sources], 1):
            title = r.get('title', '')
            snip = r.get('snippet', r.get('description', ''))
            context_parts.append(f"[SUMBER {i}] {title}: {snip}")
    else:
        print(f"   📖 Mengunduh & membersihkan {len(urls)} halaman...")
        try:
            fetched = fetch_parallel(urls)
        except Exception:
            fetched = []

        # Snippet hasil cari
        snippet_parts = []
        for i, r in enumerate(results[:max_sources], 1):
            title = r.get('title', '')
            snip = r.get('snippet', r.get('description', ''))
            if title or snip:
                snippet_parts.append(f"[RINGKASAN {i}] {title} — {snip}")
        if snippet_parts:
            context_parts.append("RINGKASAN HASIL CARI:\n" + "\n".join(snippet_parts))

        for i, item in enumerate(fetched[:4], 1):
            if item.get('html'):
                try:
                    cleaned = clean_web_content(item)
                except Exception:
                    cleaned = ""
                if cleaned:
                    context_parts.append(cleaned[:1000])

    web_context = "\n\n".join(context_parts) if context_parts else ""
    if web_context:
        print(f"   ✅ Konteks RAG Web siap ({len(web_context)} karakter)")

    if memory_context and web_context:
        combined = f"{memory_context}\n\n=== WEB TERKINI ===\n{web_context}"
        return combined[:5000]

    if web_context:
        return web_context[:5000]

    if memory_context:
        return memory_context[:5000]

    return ""
