import trafilatura
import requests
from bs4 import BeautifulSoup
from typing import Optional

def clean_web_content(url: str, max_chars: int = 1200) -> Optional[str]:
    """
    Ekstrak konten utama dari URL. 
    Prioritas: Trafilatura -> Fallback BS4 jika gagal/redirect.
    """
    
    # --- Langkah 1: Coba Trafilatura ---
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(
                downloaded,
                include_links=False,
                include_images=False,
                include_tables=False,
                no_fallback=True
            )
            if content and len(content) > 50:  # Minimal 50 char agar bukan error page
                return _truncate(content, max_chars)
    except Exception as e:
        print(f"⚠️ [Trafilatura] Gagal: {e}")

    # --- Langkah 2: Fallback ke Requests + BS4 ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Buang elemen sampah secara agresif
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            tag.decompose()
            
        # Ambil teks dari elemen konten utama
        texts = []
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'code']):
            text = tag.get_text(strip=True)
            if len(text) > 15:  # Filter kalimat terlalu pendek
                texts.append(text)
                
        if texts:
            return _truncate("\n".join(texts), max_chars)
            
    except Exception as e:
        print(f"⚠️ [BS4 Fallback] Gagal: {e}")

    return None

def _truncate(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
    return cleaned.strip()
