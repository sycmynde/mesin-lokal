import json
import sys
import os
import base64
import time
import re
import shlex
import subprocess
import mimetypes
import urllib.request
from urllib.parse import urlparse, parse_qs, quote
from http.server import BaseHTTPRequestHandler, HTTPServer

# Pastikan PATH Termux tersedia
TERMUX_BIN = "/data/data/com.termux/files/usr/bin"
if TERMUX_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = TERMUX_BIN + ":" + os.environ.get("PATH", "")

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Load cloud API keys
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    print("☁️ Cloud API environment: loaded (web)")

from web.app_core import WebAppCore

app = WebAppCore()
HTML_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data/data/com.termux/files/home/mesin/data"
TERMUX_HOME = "/data/data/com.termux/files/home"
MODELS_DIR = "/data/data/com.termux/files/home/models"
SETTINGS_PATH = os.path.join(DATA_DIR, "web_settings.json")


def _load_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_settings(obj):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _abs_models():
    return MODELS_DIR


def kecilkan_bytes(raw, max_sisi=800, kualitas=70):
    try:
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(raw))
        if im.width > max_sisi or im.height > max_sisi:
            im.thumbnail((max_sisi, max_sisi))
        if im.mode != "RGB":
            im = im.convert("RGB")
        buf = _io.BytesIO()
        im.save(buf, "JPEG", quality=kualitas)
        return buf.getvalue(), True
    except Exception:
        pass
    try:
        import subprocess as _sp, tempfile as _tf
        fin = _tf.NamedTemporaryFile(suffix=".jpg", delete=False)
        fin.write(raw); fin.close()
        fout = fin.name + ".kecil.jpg"
        vf = "scale=w='min(%d,iw)':h='min(%d,ih)':force_original_aspect_ratio=decrease" % (max_sisi, max_sisi)
        _sp.run(["ffmpeg", "-y", "-i", fin.name, "-vf", vf, "-q:v", "6", fout], capture_output=True, timeout=30, check=True)
        out = open(fout, "rb").read()
        os.remove(fin.name); os.remove(fout)
        return out, True
    except Exception:
        return raw, False


def kecilkan_dataurl(dataurl, max_sisi=800, kualitas=70):
    try:
        head, b64 = dataurl.split(",", 1)
        if "base64" not in head:
            return dataurl
        kecil, ok = kecilkan_bytes(base64.b64decode(b64), max_sisi, kualitas)
        if not ok:
            return dataurl
        return "data:image/jpeg;base64," + base64.b64encode(kecil).decode()
    except Exception:
        return dataurl


def simpan_base64(dataurl, subdir, ext, keep=10):
    d = os.path.join(DATA_DIR, subdir)
    os.makedirs(d, exist_ok=True)
    head, b64 = dataurl.split(",", 1) if "," in dataurl else ("", dataurl)
    raw = base64.b64decode(b64)
    path = os.path.join(d, "%s_%d.%s" % (subdir, int(time.time()), ext))
    with open(path, "wb") as f:
        f.write(raw)
    try:
        files = sorted([os.path.join(d, fn) for fn in os.listdir(d)], key=os.path.getmtime)
        for old in files[:-keep]: os.remove(old)
    except Exception:
        pass
    return path


def ambil_frame(vpath):
    out = vpath + ".frame.jpg"
    for ts in ("1", "0"):
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-ss", ts, "-i", vpath, "-frames:v", "1",
                 "-vf", "scale=w='min(800,iw)':h='min(800,ih)':force_original_aspect_ratio=decrease", "-q:v", "6", out],
                capture_output=True, timeout=30, check=True)
            if os.path.exists(out) and os.path.getsize(out) > 1000:
                with open(out, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                os.remove(out)
                return "data:image/jpeg;base64," + b64
        except Exception:
            continue
    try:
        os.remove(out)
    except Exception:
        pass
    return ""


def mata_lokal(image_dataurl, teks, max_tokens=150):
    payload = {"messages": [{"role": "user", "content": [{"type": "text", "text": teks}, {"type": "image_url", "image_url": {"url": image_dataurl}}]}]}
    payload["max_tokens"] = max_tokens
    req = urllib.request.Request("http://127.0.0.1:8082/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        vj = json.loads(r.read().decode("utf-8"))
    return vj["choices"][0]["message"]["content"]


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html_path = os.path.join(HTML_DIR, "index.html")
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(app.get_history(), ensure_ascii=False).encode("utf-8"))

        elif self.path == "/config":
            from tools import llm_online
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                status = llm_online.key_status()
            except Exception:
                status = {}
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
            if os.path.exists(env_path):
                try:
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            if line.startswith("export "):
                                line = line[7:]
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            status.setdefault(k, bool(v))
                except Exception:
                    pass
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode())

        elif self.path == "/settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(_load_settings(), ensure_ascii=False).encode())

        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(app.status(), ensure_ascii=False).encode("utf-8"))

        elif self.path.startswith("/models/delete"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            name = params.get("name", [""])[0].strip()
            rel = params.get("path", [""])[0].strip()
            if rel.startswith("~/"):
                rel = rel[2:]
            full_path = os.path.join(MODELS_DIR, name) if name else (rel if os.path.isabs(rel) else os.path.join(TERMUX_HOME, rel))
            if not full_path.startswith(MODELS_DIR) or not os.path.isfile(full_path):
                self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error":"File tidak valid"}, ensure_ascii=False).encode("utf-8")); return
            try:
                os.remove(full_path)
                self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps({"ok":True}).encode())
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(json.dumps({"error":str(e)}, ensure_ascii=False).encode("utf-8"))

        elif self.path.startswith("/models/download"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            rel = params.get("path", [""])[0].strip()
            if rel.startswith("~/"):
                rel = rel[2:]
            full_path = rel if os.path.isabs(rel) else os.path.join(TERMUX_HOME, rel)
            if not full_path.startswith(MODELS_DIR) or not os.path.isfile(full_path):
                self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error":"File tidak valid"}, ensure_ascii=False).encode("utf-8")); return
            try:
                with open(full_path, "rb") as f: data = f.read()
                self.send_response(200)
                self.send_header("Content-Type","application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename=\"{os.path.basename(full_path)}\"")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())

        elif self.path == "/search":
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            q = (params.get("q", [""])[0] or "").strip().lower()
            if not q:
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self.wfile.write(json.dumps({"results":[]}, ensure_ascii=False).encode("utf-8")); return
            results = []
            try:
                models = []
                for name in os.listdir(MODELS_DIR):
                    if not name.endswith(".gguf"): continue
                    models.append({"name": name, "path": os.path.join(MODELS_DIR, name)})
                matches = [m for m in models if q in m["name"].lower()]
                for m in matches[:20]:
                    size = os.path.getsize(m["path"])
                    results.append({"title": m["name"], "type":"model", "size": f"{size/(1024*1024):.0f} MB", "path": m["path"]})
            except Exception:
                pass
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self.wfile.write(json.dumps({"results":results}, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/api/models":
            try:
                mdir = MODELS_DIR
                models = []
                for name in sorted(os.listdir(mdir)):
                    if not name.endswith(".gguf") or name.startswith("mmproj"):
                        continue
                    fpath = os.path.join(mdir, name)
                    size = os.path.getsize(fpath)
                    size_str = f"{size/(1024*1024):.0f} MB" if size < 1024*1024*1024 else f"{size/(1024*1024*1024):.1f} GB"
                    cat = "llm"
                    nl = name.lower()
                    if any(k in nl for k in ["sd", "stable-diffusion", "stable_diffusion"]):
                        cat = "image"
                    elif any(k in nl for k in ["ltx", "video", "ltxv"]):
                        cat = "video"
                    elif any(k in nl for k in ["asr", "whisper", "qwen3-asr"]):
                        cat = "ars"
                    elif any(k in nl for k in ["tts", "piper", "vits"]):
                        cat = "tts"
                    elif "vae" in nl:
                        cat = "vae"
                    models.append({
                        "name": name,
                        "display_name": name.replace(".gguf", ""),
                        "path": f"/data/data/com.termux/files/home/models/{name}",
                        "size": size_str,
                        "category": cat,
                        "params": "-"
                    })
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"models": models}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path.startswith("/files/list"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            req_path = params.get("path", [TERMUX_HOME + "/mesin"])[0]
            if req_path.startswith("~/"):
                full_path = os.path.join(TERMUX_HOME, req_path[2:])
            elif os.path.isabs(req_path):
                full_path = req_path
            else:
                full_path = os.path.join(TERMUX_HOME, req_path)
            allowed_roots = [TERMUX_HOME + "/mesin", MODELS_DIR]

            if ".." in full_path or not any(full_path.startswith(root) for root in allowed_roots):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Akses ditolak"}).encode("utf-8"))
                return

            try:
                items = []
                for name in sorted(os.listdir(full_path)):
                    fpath = os.path.join(full_path, name)
                    is_dir = os.path.isdir(fpath)
                    try: size = os.path.getsize(fpath) if not is_dir else 0
                    except: size = 0

                    if size > 1024*1024*1024: size_str = f"{size/(1024**3):.1f} GB"
                    elif size > 1024*1024: size_str = f"{size/(1024**2):.1f} MB"
                    elif size > 1024: size_str = f"{size/1024:.1f} KB"
                    else: size_str = f"{size} B"

                    items.append({"name": name, "is_dir": is_dir, "size": size_str, "path": fpath.replace(TERMUX_HOME + "/", "~/")})

                items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"path": full_path.replace(TERMUX_HOME + "/", "~/"), "items": items}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path.startswith("/files/read"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            req_path = params.get("path", [""])[0]
            if not req_path:
                self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error": "Path kosong"}).encode("utf-8")); return

            if req_path.startswith("~/"):
                full_path = os.path.join(TERMUX_HOME, req_path[2:])
            elif os.path.isabs(req_path):
                full_path = req_path
            else:
                full_path = os.path.join(TERMUX_HOME, req_path)
            allowed_roots = [TERMUX_HOME + "/mesin", MODELS_DIR]
            if ".." in full_path or not any(full_path.startswith(root) for root in allowed_roots):
                self.send_response(403); self.end_headers(); self.wfile.write(json.dumps({"error": "Akses ditolak"}).encode("utf-8")); return

            allowed_ext = ['.txt', '.md', '.py', '.json', '.yaml', '.yml', '.log', '.sh', '.csv', '.ini', '.cfg', '.env']
            ext = os.path.splitext(full_path)[1].lower()
            if ext not in allowed_ext:
                self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error": f"Format file tidak didukung: {ext}"}).encode("utf-8")); return

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if len(content) > 100000: content = content[:100000] + "\n\n... [dipotong]"
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
                self.wfile.write(json.dumps({"path": full_path.replace(TERMUX_HOME + "/", "~/"), "name": os.path.basename(full_path), "content": content}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/api/models":
            try:
                mdir = MODELS_DIR
                models = []
                for name in sorted(os.listdir(mdir)):
                    if not name.endswith(".gguf") or name.startswith("mmproj"):
                        continue
                    fpath = os.path.join(mdir, name)
                    size = os.path.getsize(fpath)
                    size_str = f"{size/(1024*1024):.0f} MB" if size < 1024*1024*1024 else f"{size/(1024*1024*1024):.1f} GB"
                    cat = "llm"
                    nl = name.lower()
                    if any(k in nl for k in ["sd", "stable-diffusion", "stable_diffusion"]):
                        cat = "image"
                    elif any(k in nl for k in ["ltx", "video", "ltxv"]):
                        cat = "video"
                    elif any(k in nl for k in ["asr", "whisper", "qwen3-asr"]):
                        cat = "ars"
                    elif any(k in nl for k in ["tts", "piper", "vits"]):
                        cat = "tts"
                    elif "vae" in nl:
                        cat = "vae"
                    models.append({
                        "name": name,
                        "display_name": name.replace(".gguf", ""),
                        "path": f"/data/data/com.termux/files/home/models/{name}",
                        "size": size_str,
                        "category": cat,
                        "params": "-"
                    })
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"models": models}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path.startswith("/files/serve"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            req_path = params.get("path", [""])[0]

            if req_path.startswith("~/"):
                full_path = os.path.join(TERMUX_HOME, req_path[2:])
            elif os.path.isabs(req_path):
                full_path = req_path
            else:
                full_path = os.path.join(TERMUX_HOME, req_path)

            allowed_roots = [TERMUX_HOME + "/mesin", MODELS_DIR]
            if ".." in full_path or not any(full_path.startswith(root) for root in allowed_roots):
                self.send_response(403); self.end_headers(); self.wfile.write(b"Akses ditolak"); return

            if not os.path.isfile(full_path):
                self.send_response(404); self.end_headers(); self.wfile.write(b"File tidak ditemukan"); return

            mime_type, _ = mimetypes.guess_type(full_path)
            if not mime_type: mime_type = 'application/octet-stream'

            try:
                with open(full_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
        else:
            self.send_response(404); self.end_headers()


    def do_POST(self):
        # ── /stt  — Speech-to-Text via whisper-cli ──────────────────────
        if self.path == "/stt":
            import tempfile, wave, struct
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            # Simpan audio ke file WAV sementara
            try:
                content = body
                try:
                    data = json.loads(body.decode("utf-8"))
                    audio_field = data.get("audio") or ""
                    if isinstance(audio_field, str) and audio_field.startswith("data:"):
                        audio_field = audio_field.split(",", 1)[1]
                    if audio_field:
                        content = base64.b64decode(audio_field)
                except Exception:
                    pass
                tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
                tmp.write(content)
                tmp.close()
                webm_path = tmp.name

                # Konversi webm/opus → wav agar whisper-cli bisa baca
                wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                subprocess.run(
                    ["ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
                    capture_output=True, timeout=30
                )
                os.unlink(webm_path)

                WHISPER = "/data/data/com.termux/files/home/whisper.cpp/build/bin/whisper-cli"
                MODELS_WHISPER = "/data/data/com.termux/files/home/models/whisper"
                # Pilih model: small > base > tiny
                model_path = None
                for m in ("ggml-small-q5_1.bin", "ggml-base.bin", "ggml-tiny-q8_0.bin"):
                    p = os.path.join(MODELS_WHISPER, m)
                    if os.path.exists(p):
                        model_path = p
                        break

                if not model_path or not os.path.exists(WHISPER):
                    raise RuntimeError("whisper-cli atau model tidak ditemukan")

                result = subprocess.run(
                    [WHISPER, "-m", model_path, "-l", "id", "-f", wav_path, "--output-txt", "--no-timestamps", "-t", "4"],
                    capture_output=True, text=True, timeout=60
                )
                os.unlink(wav_path)
                # whisper-cli output teks ke stdout
                transcript = result.stdout.strip()
                # Bersihkan tag [BLANK_AUDIO] dan noise
                transcript = "\n".join(
                    l for l in transcript.splitlines()
                    if l.strip() and not l.strip().startswith("[") and "BLANK_AUDIO" not in l
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "text": transcript.strip()}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
            return

        # ── /tts  — Text-to-Speech via termux-tts-speak ─────────────────
        if self.path == "/tts":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if length else {}
            text = data.get("text", "").strip()
            pitch = float(data.get("pitch", 1.0))
            rate = float(data.get("rate", 1.0))
            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Teks kosong"}).encode())
                return
            try:
                TERMUX_TTS = "/data/data/com.termux/files/usr/bin/termux-tts-speak"
                cmd = [TERMUX_TTS, "-p", str(pitch), "-r", str(rate), text]
                subprocess.Popen(cmd)  # non-blocking: langsung balas, suara keluar di background
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "text": text[:80]}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
            return

        if self.path == "/chat":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            message = data.get("message", "")
            image = data.get("image", "")
            if image: image = kecilkan_dataurl(image)

            attachments = data.get("attachments") or []
            notes = []
            for att in attachments:
                typ = att.get("type")
                name = att.get("name") or "lampiran"
                ext = os.path.splitext(name)[1].lstrip(".").lower()
                dataurl = att.get("data") or ""
                try:
                    if typ == "video" and dataurl:
                        vpath = simpan_base64(dataurl, "video", ext or "mp4")
                        notes.append(f"📁 Video '{name}' disimpan di {vpath}.")
                        frame = ambil_frame(vpath)
                        if frame and not image:
                            image = kecilkan_dataurl(frame)
                            if not message.strip(): message = "Apa yang terjadi di video ini?"
                    elif typ == "image" and dataurl:
                        ipath = simpan_base64(dataurl, "foto", ext or "jpg")
                        notes.append(f"📁 Foto '{name}' disimpan di {ipath}.")
                    elif typ == "file" and dataurl:
                        fpath = simpan_base64(dataurl, "file", ext or "bin")
                        notes.append(f"📁 File '{name}' disimpan di {fpath}.")
                except Exception as e:
                    notes.append(f"⚠️ Gagal simpan '{name}': {e}")

            message_ctx = (message + "\n" + "\n".join(notes)).strip() if message.strip() else "\n".join(notes)

            if image:
                try:
                    vtxt = mata_lokal(image, (message or "Apa yang terlihat di gambar ini? Jawab singkat.") + " Jawab 2-3 kalimat.")
                    result = "[Via Mata Lokal] " + vtxt
                    app._save_chat("user", (message_ctx or "(foto)") + " [dengan gambar]")
                    app._save_chat("assistant", result)
                except Exception as e:
                    result = f"[Mata gagal: {e}] {app.ask(message_ctx)}"
            else:
                result = app.ask(message_ctx)

            result = re.sub(r"\[(PEMBUKA|INTI|KESIMPULAN|KEKESIMPULAN|PENUTUP)\]\s*", "", str(result)).strip()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
            self.wfile.write(json.dumps({"answer": str(result)}, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/upload":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if length else {}

            file_data = data.get("data", "")
            file_name = data.get("name", "file")
            file_type = data.get("type", "application/octet-stream")

            if not file_data:
                self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error": "No file data"}).encode()); return

            upload_dir = os.path.join(DATA_DIR, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            file_name = re.sub(r'[^\w\-_.]', '_', file_name)
            file_path = os.path.join(upload_dir, f"{int(time.time())}_{file_name}")

            try:
                if "," in file_data: file_data = file_data.split(",", 1)[1]
                raw = base64.b64decode(file_data)
                with open(file_path, "wb") as f: f.write(raw)

                file_size = os.path.getsize(file_path)
                rel_path = file_path.replace(TERMUX_HOME, "~")
                file_url = f"/files/serve?path={quote(rel_path)}"

                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "path": rel_path, "name": os.path.basename(file_path), "size": file_size, "type": file_type, "url": file_url}).encode())
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/foto":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            kamera = str(data.get("kamera", "0"))
            if kamera not in ("0", "1"): kamera = "0"

            foto_dir = os.path.join(DATA_DIR, "foto")
            os.makedirs(foto_dir, exist_ok=True)
            foto_path = os.path.join(foto_dir, f"foto_{int(time.time())}.jpg")
            error = ""

            try:
                proc = subprocess.run(["termux-camera-photo", "-c", kamera, foto_path], capture_output=True, text=True, timeout=25)
                if proc.returncode != 0: error = f"termux-camera-photo exit {proc.returncode}: {proc.stderr.strip()}"
            except subprocess.TimeoutExpired: error = "Kamera timeout"
            except FileNotFoundError: error = "termux-camera-photo tidak ditemukan"

            if not error:
                for _ in range(10):
                    if os.path.exists(foto_path) and os.path.getsize(foto_path) > 1000: break
                    time.sleep(0.3)
                else: error = "Foto tidak tersimpan / file kosong"

            if error:
                response = {"ok": False, "error": error}
            else:
                with open(foto_path, "rb") as f: raw_foto = f.read()
                raw_foto, _okk = kecilkan_bytes(raw_foto)
                with open(foto_path, "wb") as f: f.write(raw_foto)
                b64 = base64.b64encode(raw_foto).decode("ascii")
                response = {"ok": True, "image": "data:image/jpeg;base64," + b64, "file": os.path.basename(foto_path), "size": os.path.getsize(foto_path)}
                try:
                    files = sorted([os.path.join(foto_dir, fn) for fn in os.listdir(foto_dir) if fn.startswith("foto_")], key=os.path.getmtime)
                    for old in files[:-5]: os.remove(old)
                except Exception: pass

            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/clear":
            app.clear_history()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"status":"cleared"}')

        elif self.path == "/tier":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            app.set_tier(data.get("tier", "default"))
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        elif self.path == "/load":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            ok_load, info = app.load_model(data.get("model", ""))
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": ok_load, "error": "" if ok_load else str(info)}, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/config":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
            lines = []
            if os.path.exists(env_path):
                with open(env_path) as f: lines = f.read().splitlines()
            saved = []
            for k, v in data.items():
                if not v: continue
                os.environ[k] = v
                saved.append(k)
                hit = False
                for i, ln in enumerate(lines):
                    if ln.startswith(k + "="):
                        lines[i] = f"{k}={v}"
                        hit = True
                        break
                if not hit: lines.append(f"{k}={v}")
            with open(env_path, "w") as f: f.write("\n".join(lines) + "\n")
            from tools import llm_online
            llm_online.refresh_keys()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"saved": saved, "status": llm_online.key_status()}, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/settings":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            cur = _load_settings()
            cur.update(data)
            _save_settings(cur)
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"saved": list(data.keys())}, ensure_ascii=False).encode())
        elif self.path == "/generate_image":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if length else {}
            prompt = data.get("prompt", "").strip()
            steps = int(data.get("steps", 18))
            cfg = float(data.get("cfg", 7.0))
            width = int(data.get("width", 640))
            height = int(data.get("height", 640))
            _raw_seed = int(data.get("seed", -12345))
            import random as _rand
            seed = _rand.randint(1, 2147483647) if _raw_seed == -12345 else _raw_seed
            model_id = data.get("model", "sd-v1-5-q4_0")

            if not prompt:
                self.send_response(400); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Prompt kosong"}).encode())
                return

            # Auto-scan model SD dari folder models
            _models_dir = _abs_models()
            _sd_keywords = ["sd", "stable-diffusion", "stable_diffusion", "sdxl", "sdturbo"]
            _ltx_keywords = ["ltx", "ltxv", "whisper", "mmproj", "vits", "t5-"]
            model_map = {}
            if os.path.isdir(_models_dir):
                for _f in os.listdir(_models_dir):
                    if _f.endswith(".gguf"):
                        _nl = _f.lower()
                        # Exclude model LLM dan video
                        if any(k in _nl for k in _ltx_keywords):
                            continue
                        if any(k in _nl for k in _sd_keywords):
                            model_map[_f[:-5]] = os.path.join(_models_dir, _f)
            # Fallback hardcode jika scan kosong
            if not model_map:
                model_map = {
                    "sd-v1-5-q4_0": os.path.join(_models_dir, "sd-v1-5-q4_0.gguf"),
                    "sd_turbo-f16-q8_0": os.path.join(_models_dir, "sd_turbo-f16-q8_0.gguf"),
                }
            _default_sd = next(
                (k for k in ("sd_turbo-f16-q8_0", "sd-v1-5-q4_0") if k in model_map),
                next(iter(model_map))
            )
            model_path = model_map.get(model_id, model_map[_default_sd])
            neg_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
            cmd = (
                f"/data/data/com.termux/files/home/mesin/tools/gambar.sh "
                f"-m {shlex.quote(model_path)} "
                f"-p {shlex.quote(prompt)} "
                f"-n {shlex.quote(neg_prompt)} "
                f"-H {height} -W {width} "
                f"--sampling-method dpm++2mv2 "
                f"--steps {steps} "
                f"--cfg-scale {cfg} "
                f"--threads 2 "
                f"--seed {seed} "
                f"--preview none"
            )
            try:
                proc = subprocess.run(["/data/data/com.termux/files/usr/bin/bash", "-lc", cmd], capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    err = proc.stderr.strip() or proc.stdout.strip() or "Unknown error"
                    self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": err}, ensure_ascii=False).encode())
                    return
                out_dir = "/data/data/com.termux/files/home/mesin"
                files = sorted(
                    [f for f in os.listdir(out_dir) if f.startswith("karya_") and f.endswith(".png")],
                    key=lambda f: os.path.getmtime(os.path.join(out_dir, f)),
                    reverse=True
                )
                if not files:
                    self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Output gambar tidak ditemukan"}, ensure_ascii=False).encode())
                    return
                img_path = os.path.join(out_dir, files[0])
                with open(img_path, "rb") as f: raw = f.read()
                b64 = base64.b64encode(raw).decode("ascii")
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "image": "data:image/png;base64," + b64, "path": img_path}, ensure_ascii=False).encode())
            except subprocess.TimeoutExpired:
                self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Timeout generating image"}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False).encode())
        elif self.path == "/generate_video":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if length else {}
            prompt = data.get("prompt", "").strip()
            duration = int(data.get("duration", 2))
            width = int(data.get("width", 256))
            height = int(data.get("height", 256))
            # Frames: ~9fps * durasi, pilihan aman: 9, 25, 49
            frames_map = {1: 9, 2: 25, 3: 49, 4: 49}
            frames = frames_map.get(duration, 25)

            if not prompt:
                self.send_response(400); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Prompt kosong"}).encode())
                return

            VIDEO_SH = "/data/data/com.termux/files/home/mesin/tools/video.sh"
            VIDEO_DIR = os.path.join(DATA_DIR, "video")

            if not os.path.exists(VIDEO_SH):
                self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "video.sh tidak ditemukan"}, ensure_ascii=False).encode())
                return

            cmd = f"{VIDEO_SH} {shlex.quote(prompt)} {frames} {width} {height} 4"
            try:
                before = set(os.listdir(VIDEO_DIR)) if os.path.isdir(VIDEO_DIR) else set()
                proc = subprocess.run(
                    ["/data/data/com.termux/files/usr/bin/bash", "-lc", cmd],
                    capture_output=True, text=True, timeout=600
                )
                if proc.returncode != 0:
                    err = proc.stderr.strip() or proc.stdout.strip() or "Unknown error"
                    self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": err}, ensure_ascii=False).encode())
                    return
                # Cari file video baru yang muncul setelah generate
                after = set(os.listdir(VIDEO_DIR)) if os.path.isdir(VIDEO_DIR) else set()
                new_files = [f for f in (after - before) if f.endswith(".mp4")]
                if not new_files:
                    # fallback: ambil yang terbaru
                    all_mp4 = sorted(
                        [f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")],
                        key=lambda f: os.path.getmtime(os.path.join(VIDEO_DIR, f)),
                        reverse=True
                    )
                    new_files = all_mp4[:1]
                if not new_files:
                    self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Output video tidak ditemukan"}, ensure_ascii=False).encode())
                    return
                vid_path = os.path.join(VIDEO_DIR, new_files[0])
                with open(vid_path, "rb") as f:
                    raw = f.read()
                b64 = base64.b64encode(raw).decode("ascii")
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "video": "data:video/mp4;base64," + b64, "path": vid_path}, ensure_ascii=False).encode())
            except subprocess.TimeoutExpired:
                self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Timeout generating video (>10 menit)"}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False).encode())
        else:
            self.send_response(404); self.end_headers()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

class ThreadedHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        from threading import Thread
        t = Thread(target=self._handle, args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

if __name__ == "__main__":
    server = ThreadedHTTPServer(("127.0.0.1", 5000), Handler)
    print("🌐 Web Interface aktif: http://localhost:5000")
    print("🔒 Localhost only — tidak bisa diakses HP lain")
    server.serve_forever()
