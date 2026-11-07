from core.colors import DIM, R
import re
import requests
import os

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def search_web(query: str) -> list:
    if not SERPER_API_KEY or SERPER_API_KEY == "MASUKKAN_API_KEY_SERPER_ANDA":
        return []
    try:
        q_lower = query.lower()
        is_historical = bool(re.search(r'ke-\d+|ke \d+|tahun \d{4}|sejarah|masa lalu|dahulu|lalu', q_lower))
        is_current_event = (not is_historical) and any(k in q_lower for k in ['siapa', 'terkini', 'hari ini', 'presiden', 'harga', 'berita', '2024', '2025', '2026'])
        
        search_params = {"q": query, "num": 15}
        
        if is_historical:
            print(f"   {DIM}📜 [Search Router] Mode Historis Aktif (Tanpa Filter Waktu){R}")
        elif is_current_event:
            search_params["tbs"] = "qdr:y"
            print(f"   {DIM}📅 [Search Router] Mode Fakta Terkini Aktif (Filter: 1 Tahun Terakhir){R}")

        res = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json=search_params,
            timeout=10
        )
        return res.json().get('organic', [])
    except Exception as e:
        print(f"[Serper Error]: {e}")
        return []

def search_github(query: str) -> list:
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        res = requests.get(
            f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=3",
            headers=headers,
            timeout=5
        )
        if res.status_code == 403:
            print("[GitHub] Rate limited. Fallback ke web search.")
            return []
        
        items = res.json().get('items', [])
        return [{"title": i['full_name'], "link": i['html_url'],
                 "snippet": i.get('description', '')} for i in items]
    except Exception as e:
        print(f"[GitHub Error]: {e}")
        return []

def route_search(query: str) -> tuple:
    q_lower = query.lower()
    is_github_query = any(kw in q_lower for kw in ["github", "repo", "repository", "kode", "library", "npm", "pip"])
    
    if is_github_query:
        results = search_github(query)
        if not results:
            print("   ⚠️ GitHub API gagal, fallback ke Serper + site:github.com")
            results = search_web(f"{query} site:github.com")
        return results, "github"
    else:
        results = search_web(query)
        return results, "web"
