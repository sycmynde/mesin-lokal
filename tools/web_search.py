#!/usr/bin/env python3
"""Web search and extract: cari info terbaru dari internet."""
import requests
import json
import re
import urllib.parse

def web_search(query, limit=5):
    """Cari web via DuckDuckGo HTML (tanpa API key)."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=15)
        text = resp.text
        results = []
        # Parse hasil DDG
        for m in re.finditer(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', text):
            href = m.group(1)
            title = re.sub(r'<.*?>', '', m.group(2))
            results.append({"url": href, "title": title})
        return json.dumps(results[:limit], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def web_extract(url, limit=5000):
    """Ambil konten teks dari URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        # Bersihkan tag HTML dasar
        text = re.sub(r'<script.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:limit]
    except Exception as e:
        return f"[Error] {str(e)}"

def baca_web(url):
    return web_extract(url)

HANDS = {
    "web_search": web_search,
    "baca_web": web_extract,
}
