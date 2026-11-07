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
            "model": "Qwen3.8-2B-Uncensored-Q4_K_M",  # default model
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        "instan": {
            "model": "Qwen3.5-0.8B-Q4_K_M",  # model ringan untuk sapaan/olahraga
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        },
    }

    def __init__(self, config):
        local = config["llm_local"]
        self.api_url = local["api_url"]
        self.default_tier = "default"
        self.config_model = local.get("model_name", self.MODELS["default"]["model"])
        self.config_max_tokens = local.get("max_tokens", 2048)
        self.config_temperature = local.get("temperature", 0.5)
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
        return len(sw & ew) / max(len(sw), 1) > threshold

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
                    return int(file_mb + 80)
                if "q3" in name_lower:
                    return int(file_mb + 120)
                return int(file_mb + 180)
        name_lower = model_id.lower()
        size_map = {
            "0.5b": 500, "0.6b": 600, "0.8b": 700,
            "1b": 1000, "2b": 1600, "3b": 2200,
            "4b": 2800, "7b": 4500, "8b": 5000,
        }
        for key, mb in size_map.items():
            if key in name_lower:
                if "iq4" in name_lower or "iq3" in name_lower or "q3" in name_lower:
                    return mb + 120
                return mb + 180
        return 3000

    def load_model(self, model_id: str) -> bool:
        try:
            available = self._get_available_ram_mb()
            if self.loaded_model and self.loaded_model != model_id:
                available += self._estimate_model_ram_mb(self.loaded_model)
            needed = self._estimate_model_ram_mb(model_id)
            deficit = needed - available if available > 0 else 0
            if deficit > 300:
                print(f"   {YELLOW}⚠️ RAM tidak cukup untuk '{model_id}'.{R}")
                print(f"   {DIM}   Perlu ~{needed}MB, tersedia ~{available}MB.{R}")
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
        proc = subprocess.Popen(
            [
                os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
                "--model", os.path.expanduser("~/models/qwen2.5-0.5b-instruct-q4_k_m"),
                "--mmproj", os.path.expanduser("~/models/mmproj-0.8B"),
                "--host", "127.0.0.1", "--port", "8082",
                "-c", "4096", "-t", "4", "-ngl", "0",
                "--jinja", "--reasoning", "off",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(timeout):
            if self._mata_alive():
                return proc
            if proc.poll() is not None:
                return None
            time.sleep(1)
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

        IDENTITAS_MATA = "Kamu adalah AI Lokal. Mode teks: jangan ngarang gambar atau kemampuan visual."
        if system_prompt:
            if "tidak bisa melihat" in system_prompt or "batas kemampuan" in system_prompt:
                system_prompt = IDENTITAS_MATA
        else:
            system_prompt = IDENTITAS_MATA

        final_messages.insert(0, {"role": "system", "content": system_prompt})

        model_to_use = self.loaded_model if self.loaded_model else cfg["model"]

        mata_proc = None
        chat_url = self.api_url
        chat_model = model_to_use

        if image_data:
            chat_url = "http://127.0.0.1:8082/v1/chat/completions"
            chat_model = "qwen2.5-0.5b-instruct-q4_k_m"
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
            "repeat_last_n": 64,
            "stream": True
        }

        max_continues = 2
        full_answer = ""

        for attempt in range(1 + max_continues):
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
                    except Exception:
                        continue
                if attempt > 0 and self._is_repetitive(full_answer, answer):
                    print(f"   {DIM}🔁 Model mengulang — dihentikan.{R}")
                    break
                full_answer += answer
                if finish_reason == "length" and attempt < max_continues:
                    print(f"   {DIM}… lanjutkan {attempt + 1}/{max_continues}{R}")
                    final_messages.append({"role": "assistant", "content": full_answer})
                    _tail = " ".join(full_answer.split()[-25:])
                    final_messages.append({"role": "user", "content": f"Terpotong di: '...{_tail}'. Lanjutkan langsung, jangan ulang."})
                    payload["messages"] = final_messages
                    continue
                break
            except Exception as e:
                print(f"   {RED}❌ Error: {e}{R}")
                try:
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"   {DIM}   Response: {e.response.text[:500]}{R}")
                except Exception:
                    pass
                break

        if mata_proc is not None:
            self._kill_mata(mata_proc)
            print(f"   😴 Mata ditidurkan lagi.")

        return full_answer.strip() or "Belum bisa menjawab saat ini."
