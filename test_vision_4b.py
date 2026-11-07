#!/usr/bin/env python3
"""👁️ Vision PoC: model 4B + mmproj-4B-Q8_0."""
import subprocess, requests, time, sys, os, base64

MODEL = os.path.expanduser("~/models/Qwen3.5-4B-IQ4_XS.gguf")
MMPROJ = os.path.expanduser("~/models/mmproj-4B-Q8_0.gguf")
IMAGE = os.path.expanduser("~/mesin/karya_pertama.png")
PORT = 9998

print(f"🚀 Spawning llama-server (port {PORT})...")
print(f"   Model: {os.path.basename(MODEL)}")
print(f"   Mmproj: {os.path.basename(MMPROJ)}")

proc = subprocess.Popen([
    os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
    "--model", MODEL,
    "--mmproj", MMPROJ,
    "--port", str(PORT),
    "--host", "127.0.0.1",
    "-c", "2048",
    "--threads", "4",
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print("⏳ Waiting for server...")
for i in range(30):
    try:
        r = requests.get(f"http://127.0.0.1:{PORT}/health", timeout=2)
        if r.status_code == 200:
            print("✅ Server ready!")
            break
    except:
        pass
    time.sleep(1)
else:
    print("❌ Server timeout")
    proc.terminate()
    sys.exit(1)

print(f"📷 Loading image: {os.path.basename(IMAGE)}")
with open(IMAGE, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

print("👁️ Sending vision request (4B)...")
payload = {
    "model": "Qwen3.5-4B-IQ4_XS",
    "messages": [
        {"role": "user", "content": [
            {"type": "text", "text": "Deskripsikan gambar ini dalam 2-3 kalimat bahasa Indonesia."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}
    ],
    "max_tokens": 300,
    "temperature": 0.5,
}

try:
    r = requests.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", json=payload, timeout=120)
    if r.status_code == 200:
        answer = r.json()["choices"][0]["message"]["content"]
        if answer.strip():
            print(f"\n✅ SUKSES! Jawaban:\n{answer}")
        else:
            print(f"\n⚠️ Jawaban kosong (model terima gambar tapi nggak generate teks)")
    else:
        print(f"\n❌ HTTP {r.status_code}: {r.text[:500]}")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    print("\n🛑 Stopping server...")
    proc.terminate()
    proc.wait()
