import requests
import json

url = "http://127.0.0.1:8080/v1/chat/completions"

# Kita coba TANPA kunci "model" dulu, atau gunakan nama file persis
payload = {
    "messages": [
        {"role": "user", "content": "Halo, tulis angka 1 sampai 5."}
    ],
    "max_tokens": 50,
    "temperature": 0.7,
    "stream": False
}

print(f"📡 Mengirim request ke: {url}")
try:
    response = requests.post(url, json=payload, timeout=15)
    print(f"✅ Status Code: {response.status_code}")
    
    # CETAK SELURUH RESPON JSON UNTUK DIANALISIS
    print(f"\n📦 RAW RESPONSE DARI SERVER:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
