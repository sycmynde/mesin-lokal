import glob
import os
import json
import re
import time
import base64  # ✅ Ditambahkan
import requests
from core.colors import CYAN, RED, R, DIM, YELLOW


class LocalProvider:
    MODELS = {
        "default": {
            "model": "Qwen3.5-0.8B-Q4_0",
            "max_tokens": 4092,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        # ✅ TAMBAHKAN INI: Biar test v08 lulus, tapi tetap pakai 0.8B (Hemat RAM!)
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_0", 
            "max_tokens": 2048,           # Lebih pendek = lebih ngebut
            "temperature": 0.5,           # Lebih fokus, kurang ngawur
            "top_p": 0.9,
        }
    }

    def __init__(self, config):
        local = config["llm_local"]
        self.api_url = local["api_url"]
        self.default_tier = "default"
        self.config_model = local.get("model_name", self.MODELS["default"]["model"])
        self.config_max_tokens = local.get("max_tokens", 4192)
        self.config_temperature = local.get("temperature", 0.7)
        self.config_top_p = local.get("top_p", 0.9)
        self.loaded_model = None
        self.model = self.config_model
        self.max_tokens = self.config_max_tokens
        self.temperature = self.config_temperature
        self.top_p = self.config_top_p

    def get_config(self, tier=None):
        tier = tier or self.default_tier
        if tier not in self.MODELS:
            tier = self.default_tier
        return self.MODELS[tier]

    def _is_repetitive(self, existing, new_text, threshold=0.6):
        if not existing or not new_text:
            return False
        sample = new_text[:200].lower().strip()
        if len(sample) < 50:
            return False
        if sample in existing.lower():
            return True
        sw = set(sample.split())
        ew = set(existing.lower().split()[-200:])
        return len(sw & ew) / max(len(sw), 3) > threshold

    def _get_available_ram_mb(self) -> int:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable"):
                        return int(line.split()[1]) // 1024
        except Exception:
            pass
        return 0

    def _estimate_model_ram_mb(self, model_id: str) -> int:
        search_dirs = [
            os.path.expanduser("~/mesin/models"),
            os.path.expanduser("~/llama/models"),
            os.path.expanduser("~/models"),
        ]
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            matches = glob.glob(os.path.join(d, f"{model_id}*"))
            if matches:
                file_mb = os.path.getsize(matches[0]) / (1024 * 1024)
                name_lower = model_id.lower()
                if "iq4" in name_lower or "iq3" in name_lower:
                    return int(file_mb * 1.05 + 50)
                if "q3" in name_lower:
                    return int(file_mb * 1.10 + 100)
                return int(file_mb * 1.15 + 200)
        name_lower = model_id.lower()
        size_map = {
            "0.5b": 500, "0.6b": 600, "0.8b": 700,
            "1b": 1000, "2b": 1600, "3b": 2200,
            "4b": 2800, "7b": 4500, "8b": 5000,
        }
        for key, mb in size_map.items():
            if key in name_lower:
                if "iq4" in name_lower or "iq3" in name_lower or "q3" in name_lower:
                    return mb + 100
                return mb + 200
        return 3000

    def load_model(self, model_id: str) -> bool:
        try:
            # 🔥 HAPUS .gguf BIAR COCOK SAMA REGISTRY LLAMA-SERVER
            model_id = model_id.replace(".gguf", "")

            available = self._get_available_ram_mb()
            if self.loaded_model and self.loaded_model != model_id:
                available += self._estimate_model_ram_mb(self.loaded_model)
            
            needed = self._estimate_model_ram_mb(model_id)
            deficit = needed - available if available > 0 else 0
            
            if deficit > 300:
                print(f"   {YELLOW}️ RAM tidak cukup untuk '{model_id}'.{R}")
                print(f"   {DIM}   Perlu ~{needed}MB, tersedia ~{available}MB.{R}")
                return False
            elif deficit > 0:
                print(f"   {YELLOW}⚠️ RAM pas-pasan untuk '{model_id}' (kurang {deficit}MB), dicoba.{R}")
            
            if available > 0:
                print(f"   {DIM}🧠 RAM check: {available}MB tersedia, ~{needed}MB dibutuhkan{R}")
            
            base = self.api_url.split("/v1/")[0]
            r = requests.post(f"{base}/models/load", json={"model": model_id}, timeout=60)
            
            ok = r.status_code == 200 and r.json().get("success", False)
            if ok:
                self.loaded_model = model_id
            return ok
        except Exception as e:
            print(f"   ❌ Load gagal: {e}")
            return False

    def _wait_ready(self, model_id, timeout=30):
        base = self.api_url.split("/v1/")[0]
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                h = requests.get(f"{base}/health", timeout=3)
                if h.status_code == 200:
                    m = requests.get(f"{base}/models", timeout=3).json()
                    for item in m.get("data", []):
                        if item.get("id") == model_id and item.get("status", {}).get("value") == "loaded":
                            return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def preflight(self, model_id: str) -> bool:
        available = self._get_available_ram_mb()
        if self.loaded_model and self.loaded_model != model_id:
            available += self._estimate_model_ram_mb(self.loaded_model)
        needed = self._estimate_model_ram_mb(model_id)
        deficit = needed - available if available > 0 else 0
        if deficit > 300:
            print(f"   {YELLOW}⚠️ RAM tidak cukup untuk '{model_id}'.{R}")
            print(f"   {DIM}   Perlu ~{needed}MB, tersedia ~{available}MB (kurang {deficit}MB).{R}")
            return False
        elif deficit > 0:
            print(f"   {YELLOW}⚠️ RAM pas-pasan untuk '{model_id}' (kurang {deficit}MB), tapi tetap dicoba.{R}")
        return True

    def unload_model(self, model_id: str) -> bool:
        try:
            base = self.api_url.split("/v1/")[0]
            r = requests.post(f"{base}/models/unload", json={"model": model_id}, timeout=30)
            ok = r.status_code == 200
            if ok and self.loaded_model == model_id:
                self.loaded_model = None
            return ok
        except Exception as e:
            print(f"   ❌ Unload gagal: {e}")
            return False

    def _mata_alive(self):
        try:
            h = requests.get("http://127.0.0.1:8082/health", timeout=3)
            return h.status_code == 200
        except Exception:
            return False

    def _spawn_mata(self, timeout=60):
        import subprocess
        
        # ✅ PASTIKAN NAMA FILE LENGKAP DENGAN .gguf
        model_path = os.path.expanduser("~/models/Qwen3.5-0.8B-Q4_0.gguf")
        mmproj_path = os.path.expanduser("~/models/mmproj-0.8B.gguf") # Cek apakah nama filanya benar-benar segini
        
        # Cek keberadaan file sebelum eksekusi
        if not os.path.exists(model_path):
            print(f"   ❌ Model vision tidak ditemukan: {model_path}")
            return None
        if not os.path.exists(mmproj_path):
            print(f"   ❌ File mmproj tidak ditemukan: {mmproj_path}")
            print(f"   💡 Coba cek isi folder: ls ~/models/*mmproj*")
            return None

        print(f"   🛠️ Mencoba jalankan vision server...")
        
        proc = subprocess.Popen(
            [
                os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
                "--model", model_path,
                "--mmproj", mmproj_path,
                "--host", "127.0.0.1", "--port", "8082",
                "-c", "2048",          # ✅ Turunkan context size biar hemat RAM (vision makan RAM)
                "-t", "4", 
                "-ngl", "0",
                "--jinja", "--reasoning", "off",
            ],
            # ✅ HAPUS DEVNULL SEMENTARA BIAR KITA BISA BACA ERROR ASLINYA DI TERMINAL
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )
        
        for _ in range(timeout):
            if self._mata_alive():
                print(f"   ✅ Mata berhasil terbuka di port 8082!")
                return proc
            
            # Cek apakah proses mati mendadak (crash)
            if proc.poll() is not None:
                print(f"   ❌ Proses vision server mati mendadak (crash). Cek error di atas.")
                return None
                
            time.sleep(1)
            
        print(f"   ❌ Timeout: Mata gagal terbuka dalam {timeout} detik.")
        return None

    def _kill_mata(self, proc):
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def chat(self, messages, system_prompt="", tier=None):
        cfg = self.get_config(tier)
        last_msg = messages[-1] if messages else {}
        content = last_msg.get("content", "")
        image_data = None

        img_match = re.search(r'([\w\-]+\.(?:png|jpg|jpeg))', content, re.I)
        if img_match:
            img_name = img_match.group(1)
            search_paths = [
                os.path.expanduser(f"~/mesin/{img_name}"),
                os.path.expanduser(f"~/mesin/data/foto/{img_name}"),
                os.path.expanduser(f"~/mesin/data/{img_name}"),
                os.path.expanduser(f"~/{img_name}"),
            ]
            for path in search_paths:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode()
                    ext = img_name.split(".")[-1].lower()
                    mime = f"image/{'jpeg' if ext == 'jpg' else ext}"
                    last_msg["content"] = [
                        {"type": "text", "text": content.replace(img_name, "").strip() or "Deskripsikan gambar ini secara terperinci."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}
                    ]
                    print(f"   👁️ Vision: {img_name} dimuat ({len(image_data)//1024}KB)")
                    break

        final_messages = list(messages)

        # ✅ PERBAIKAN TOTAL: Gunakan string, bukan tuple ()
        identitas_mata = ""
        if image_data:
            identitas_mata = "Kamu memiliki kemampuan melihat gambar. Jawab berdasarkan gambar yang diberikan secara detail."

        # Gabungkan dengan aman
        if system_prompt:
            if identitas_mata:
                system_prompt += f"\n\n{identitas_mata}"
        else:
            system_prompt = identitas_mata

        final_messages.insert(0, {"role": "system", "content": system_prompt})

        model_to_use = self.loaded_model if self.loaded_model else cfg["model"]

        mata_proc = None
        chat_url = self.api_url
        chat_model = model_to_use

        if image_data:
            chat_url = "http://127.0.0.1:8082/v1/chat/completions"
            chat_model = "Qwen3.5-0.8B-Q4_0"
            _ram = self._get_available_ram_mb()

            if _ram < 1500 and self.loaded_model:
                print(f"   📤 Lepas model utama buat beri ruang mata...")
                self.unload_model(self.loaded_model)
                time.sleep(1)
                _ram = self._get_available_ram_mb()

            if self._mata_alive():
                print(f"   👁️ Mata sudah terbuka — dipakai langsung.")
            else:
                if _ram < 1200:
                    print(f"   ⚠️ RAM masih tidak cukup: {_ram}MB")
                    return "Memori tidak cukup untuk membuka mata. Coba lepas model dulu."
                print(f"   👁️ Mata tidur — dibangunkan sebentar (~15-30 detik)...")
                mata_proc = self._spawn_mata()
                if mata_proc is None:
                    print(f"   ❌ Mata gagal dibangunkan.")
                    return "Mata gagal menyala. Coba lagi nanti."

        print(f"   {DIM}🔎 [LocalProvider] Tier={tier or self.default_tier} | Model={chat_model}{R}")

        payload = {
            "model": chat_model,
            "messages": final_messages,
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"],
            "repeat_penalty": 1.2,  
            "frequency_penalty": 0.1,  
            "presence_penalty": 0.1,
            "repeat_last_n": 64,
            "stream": True
        }

        max_continues = 5
        full_answer = ""

        for attempt in range(3 + max_continues):
            try:
                response = requests.post(chat_url, json=payload, stream=True, timeout=(10, 300))
                response.raise_for_status()
                answer = ""
                finish_reason = None
                for line in response.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        if "error" in obj:
                            print(f"   {RED}❌ Stream error: {obj['error']}{R}")
                            break
                        choice = obj["choices"][0]
                        delta = choice.get("delta", {})
                        fr = choice.get("finish_reason")
                        if fr:
                            finish_reason = fr
                        text = delta.get("content") or ""
                        if text:
                            answer += text
                            
                            # ✨ TAMBAHKAN REM TANGAN DI SINI ✨
                            # Cek 50 karakter terakhir, kalau ada kata yang diulang 3x, potong!
                            if len(answer) > 100:
                                tail = answer[-100:].lower()
                                words = tail.split()
                                # Kalau 3 kata terakhir sama persis, langsung potong!
                                if len(words) >= 3 and len(set(words[-3:])) == 1:
                                    print(f"\n   {DIM}✂️ Python memotong ngoceh real-time!{R}")
                                    finish_reason = "stop" # Paksa berhenti
                                    break
                    except Exception:
                        continue
                if attempt > 0 and self._is_repetitive(full_answer, answer):
                    print(f"   {DIM}🔁 Model mengulang — dihentikan.{R}")
                    break
                full_answer += answer
                if finish_reason == "length" and attempt < max_continues:
                    print(f"   {DIM}… lanjutkan {attempt + 3}/{max_continues}{R}")
                    final_messages.append({"role": "assistant", "content": full_answer})
                    _tail = " ".join(full_answer.split()[-25:])
                    final_messages.append({"role": "user", "content": f"Terpotong di: '...{_tail}'. Lanjutkan langsung, jangan ulang."})
                    payload["messages"] = final_messages
                    continue
                break
            except Exception as e:
                if "400" in str(e) and attempt == 0 and not self.loaded_model:
                    print(f"   {DIM}🔄 Muat model otomatis…{R}")
                    if self.load_model(model_to_use):
                        continue
                print(f"   {RED}❌ Error: {e}{R}")
                try:
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"   {DIM}   Response: {e.response.text[:500]}{R}")
                except Exception:
                    pass
                break

        # ✅ SELALU muat kembali model utama
        if mata_proc is not None:
            self._kill_mata(mata_proc)
            print(f"   😴 Mata ditidurkan lagi.")
        
        if not self.loaded_model:
            print(f"   📥 Muat kembali model utama...")
            retry = 0
            while retry < 3:
                if self.load_model(self.MODELS["default"]["model"]):
                    print(f"   ✅ Model utama siap kembali!")
                    break
                retry += 1
                time.sleep(1)
            else:
                print(f"   ⚠️ Gagal muat ulang, ketik /load manual")

        return full_answer.strip() or "Belum bisa menjawab saat ini."
