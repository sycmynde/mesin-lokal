import requests
import json

url = "http://127.0.0.1:8080/v1/chat/completions"
payload = {
    "model": "Qwen3.5-0.8B-Q4_0",
    "messages": [
        {"role": "system", "content": "Jawab singkat."},
        {"role": "user", "content": "Halo, apa kabar?"}
    ],
    "max_tokens": 50,
    "temperature": 0.7,
    "stream": False  # Kita matikan stream dulu untuk tes dasar
}

print(f"📡 Mengirim request ke: {url}")
try:
    response = requests.post(url, json=payload, timeout=15)
    print(f"✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        jawaban = data["choices"][0]["message"]["content"]
        print(f"\n🤖 JAWABAN AI:\n{jawaban}")
    else:
        print(f"\n❌ Gagal! Server mengembalikan:\n{response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Koneksi ditolak! Pastikan llama-server berjalan di port 8080.")
except requests.exceptions.Timeout:
    print("\n❌ ERROR: Timeout! Server terlalu lambat merespons.")
except Exception as e:
    print(f"\n❌ ERROR TAK TERDUGA: {e}")
