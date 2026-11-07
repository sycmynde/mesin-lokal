import requests
from bs4 import BeautifulSoup
import re
import time

# Cache sederhana agar tidak download ulang URL yang sama dalam 30 menit
CACHE = {}
CACHE_TTL = 1800 

def fetch_and_clean(url: str) -> str:
    """
    Mengunduh halaman web, membersihkan HTML, dan mengembalikan teks murni.
    Adaptasi dari browser_service.js ke Python.
    """
    # Cek cache dulu
    if url in CACHE:
        timestamp, content = CACHE[url]
        if time.time() - timestamp < CACHE_TTL:
            return content

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "id,en-US;q=0.9,en;q=0.8"
        }
        res = requests.get(url, headers=headers, timeout=12)
        
        # Bersihkan HTML menggunakan BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Hapus elemen sampah (script, style, nav, footer, iklan)
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "[class*='ad']", "[class*='cookie']"]):
            element.decompose()
            
        # Ekstrak teks dan bersihkan spasi berlebih
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = '\n'.join(lines)[:8000] # Batasi 8000 karakter agar muat di context window
        
        # Simpan ke cache
        CACHE[url] = (time.time(), clean_text)
        return clean_text
        
    except Exception as e:
        return f"[Error fetching {url}: {str(e)}]"

def browse_top_results(search_results: str) -> str:
    """
    Menerima output dari pencari (berisi URL), lalu mengunjungi 5 URL teratas.
    """
    urls = []
    for line in search_results.split('\n'):
        if 'http' in line.lower():
            # Ekstrak URL mentah dari baris hasil pencarian
            match = re.search(r'(https?://[^\s]+)', line)
            if match:
                urls.append(match.group(1))
        if len(urls) >= 2: break
            
    if not urls:
        return "[Browser] Tidak ditemukan URL valid untuk dikunjungi."
        
    full_content = ""
    for i, url in enumerate(urls, 1):
        print(f"   📖 Membaca sumber {i}...")
        content = fetch_and_clean(url)
        full_content += f"\n[SUMBER {i} - {url}]:\n{content}\n"
        
    return full_content[:5000] # Batasi total konten gabungan
