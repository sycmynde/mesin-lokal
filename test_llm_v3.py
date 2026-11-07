import requests
import json

url = "http://127.0.0.1:8080/v1/chat/completions"
payload = {
    "messages": [{"role": "user", "content": "Halo, tulis angka 1 sampai 5."}],
    "max_tokens": 512,               # Ruang napas yang cukup
    "temperature": 0.7,
    "reasoning_format": "none",      # Paksa langsung jawab
    "stream": False
}

print("📡 Mengirim request...")
response = requests.post(url, json=payload, timeout=15)
data = response.json()

content = data["choices"][0]["message"].get("content", "")
reasoning = data["choices"][0]["message"].get("reasoning_content", "")

print(f"\n🧠 Reasoning: {reasoning[:100]}...")
print(f"\n✅ JAWABAN AKHIR:\n{content}")
