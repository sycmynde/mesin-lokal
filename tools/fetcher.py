import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE = {}
CACHE_TTL = 1800 

def fetch_single(url: str) -> dict:
    """Mengambil satu URL dengan timeout dan user-agent realistis."""
    if url in CACHE:
        ts, content = CACHE[url]
        if time.time() - ts < CACHE_TTL:
            return {"url": url, "html": content, "cached": True}
            
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "id,en-US;q=0.9,en;q=0.8"
        }
        res = requests.get(url, headers=headers, timeout=12)
        res.raise_for_status()
        
        CACHE[url] = (time.time(), res.text)
        return {"url": url, "html": res.text, "cached": False}
    except Exception as e:
        return {"url": url, "html": None, "error": str(e)}

def fetch_parallel(urls: list, max_workers: int = 3) -> list:
    """
    Mengambil multiple URL secara paralel.
    Porting logika parallel fetching dari rag.js
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single, url): url for url in urls[:3]}
        for future in as_completed(futures):
            results.append(future.result())
    return results
