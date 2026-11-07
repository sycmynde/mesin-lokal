import requests

response = requests.post("http://127.0.0.1:8080/v1/chat/completions", json={
    "model": "Qwen3.5-0.8B-Q4_0",  # <--- PAKAI NAMA PERSIS DARI DAFTAR MODEL LU
    "messages": [
        {"role": "system", "content": "Jawab singkat dalam Bahasa Indonesia."},
        {"role": "user", "content": "Halo, siapa kamu?"}
    ],
    "temperature": 0.2,
    "max_tokens": 100
})

print("🔍 STATUS CODE:", response.status_code)
print("🔍 ISI RESPON SERVER:", response.json())