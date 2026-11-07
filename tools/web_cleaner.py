try:
    import trafilatura
    HAS_TRAFILATURA = True
except Exception:
    HAS_TRAFILATURA = False
try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

if not HAS_BS4:
    class BeautifulSoup:
        def __init__(self, *a, **k):
            pass
        def get_text(self, *a, **k):
            return ""
from typing import Optional, Union

def clean_web_content(source: Union[str, dict], max_chars: int = 2000) -> Optional[str]:
    """
    Ekstrak konten utama. 
    Bisa menerima URL (string) atau Dict hasil fetcher {'html': '...', 'url': '...'}
    """
    html_content = None
    url = None

    # Deteksi tipe input
    if isinstance(source, dict):
        html_content = source.get('html')
        url = source.get('url')
    elif isinstance(source, str):
        if source.startswith('http'):
            url = source
        else:
            html_content = source

    # --- Langkah 1: Jika ada HTML mentah, pakai BS4 (Cepat) ---
    if html_content:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buang elemen sampah dan UI yang tidak relevan
            for tag in soup.find_all([
                'script', 'style', 'nav', 'footer',
                'header', 'aside', 'iframe', 'svg'
            ]):
                tag.decompose()

            noise = [
                'There was an error while loading.',
                'Please reload this page.',
                'Notifications',
                'You must be signed in',
                'Sorry, something went wrong.',
                'No results found',
                'Skip to content',
                'Search this repository',
            ]

            texts = []
            seen = set()

            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'code', 'table']):
                # 🆕 EKSTRAK TABEL: data penting sering hidup di tabel
                if tag.name == 'table':
                    for row in tag.find_all('tr'):
                        cells = [c.get_text(' ', strip=True) for c in row.find_all(['th', 'td'])]
                        line = ' | '.join(c for c in cells if c)
                        line = ' '.join(line.split())
                        if len(line) > 15 and line not in seen:
                            seen.add(line)
                            texts.append(line)
                    continue
                text = tag.get_text(' ', strip=True)

                if len(text) <= 15:
                    continue

                if any(x.lower() in text.lower() for x in noise):
                    continue

                normalized = ' '.join(text.split())

                if normalized in seen:
                    continue

                seen.add(normalized)
                texts.append(normalized)
            
            if texts:
                return _truncate("\n".join(texts), max_chars)
        except Exception as e:
            print(f"⚠️ [BS4] Error parsing HTML: {e}")

    # --- Langkah 2: Jika hanya URL, pakai Trafilatura ---
    if url and HAS_TRAFILATURA:
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded, include_links=False, no_fallback=True)
                if content and len(content) > 50:
                    return _truncate(content, max_chars)
        except Exception as e:
            print(f"⚠️ [Trafilatura] Error fetching {url}: {e}")

    return None

def _truncate(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
    return cleaned.strip()
