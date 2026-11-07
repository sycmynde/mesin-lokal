import requests
from urllib.parse import quote

# Masukkan API Key Serper Anda di sini (Gratis 2500x)
SERPER_API_KEY = "102b95555164758c1ebb630ea1892ce83f906b31" 

def cari_serper(query):
    """
    Mencari menggunakan Serper.dev (Google Search Wrapper)
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "MASUKKAN_API_KEY_SERPER_ANDA":
        return None
        
    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": 5}
        
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        data = res.json()
        
        results = data.get('organic', [])
        if results:
            snippet = ""
            for r in results[:5]: # Ambil 5 hasil teratas
                title = r.get('title', '')
                desc = r.get('snippet', '')
                snippet += f"- {title}: {desc}\n"
            return snippet.strip()
    except Exception as e:
        print(f"[Debug] Serper Error: {e}")
        pass
    return None

def cari_wikipedia(query):
    """Fallback ke Wikipedia jika Serper gagal/kosong"""
    try:
        url = f"https://id.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&exintro&explaintext&titles={quote(query)}"
        res = requests.get(url, headers={"User-Agent": "MesinAI-Termux"}, timeout=5)
        pages = res.json()['query']['pages']
        page_id = next(iter(pages))
        if page_id != '-1':
            extract = pages[page_id].get('extract', '')
            if len(extract) > 100: return extract[:1200]
    except: pass
    return None

def cari_web(query: str) -> str:
    """
    Sistem Pencarian Bertingkat: Serper (Real-time) -> Wikipedia (Fakta)
    """
    # 1. Coba Serper dulu untuk data terkini (Presiden, Harga Emas, dll)
    result = cari_serper(query)
    if result: return f"[Serper/Google]:\n{result}"

    # 2. Fallback ke Wikipedia untuk definisi/fakta umum
    result = cari_wikipedia(query)
    if result: return f"[Wikipedia]: {result}"

    return "Maaf, tidak ditemukan informasi dari sumber manapun."
