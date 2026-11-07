import os
import re
import json
import shlex
import subprocess

BASE_DIR = os.path.expanduser("/data/data/com.termux/files/home/mesin")
SEARCH_DIRS = (
    BASE_DIR,
    os.path.join(BASE_DIR, "web"),
    os.path.join(BASE_DIR, "tools"),
)
COMMON_EXTS = (
    ".txt", ".md", ".py", ".json", ".log", ".csv", ".yaml", ".sh",
    ".mp3", ".m4a", ".flac", ".wav", ".ogg",
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".gguf", ".safetensors", ".bin", ".onnx", ".pt", ".pth",
)

_write_consent = False

def _write_requires_consent():
    global _write_consent
    return not _write_consent

def set_write_consent(val):
    global _write_consent
    _write_consent = bool(val)

def _resolve_bare_name(name):
    hits = []
    seen = set()
    name_lower = name.lower()
    for base in SEARCH_DIRS:
        if not os.path.isdir(base):
            continue
        try:
            for fn in os.listdir(base):
                root, ext = os.path.splitext(fn)
                if fn.lower() == name_lower or root.lower() == name_lower:
                    full = os.path.join(base, fn)
                    abs_full = os.path.abspath(full)
                    if abs_full in seen:
                        continue
                    seen.add(abs_full)
                    hits.append(full)
        except PermissionError:
            continue
    return hits


def find_files(query):
    if not query:
        return "[Error] Query kosong."
    needle = os.path.basename(query).strip()
    if not needle:
        return "[Error] Query kosong."
    home = os.path.expanduser("/data/data/com.termux/files/home")
    likely_dirs = [
        os.path.join(home, d) for d in [
            "mesin", "web", "tools",
            "1rox.cpp", "llama.cpp", "koboldcpp", "ltx.cpp",
            "whisper.cpp", "piper-tts", "piper-env",
            "Agent", "WebSift", "output-ltx", "gothic_metal",
        ]
        if os.path.isdir(os.path.join(home, d))
    ]
    out_lines = []
    try:
        for d in likely_dirs:
            cmd = (
                f"find {shlex.quote(d)} -maxdepth 4 -type f "
                f"-iname '*{shlex.quote(needle)}*' 2>/dev/null | head -n 20"
            )
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            lines = [line for line in out.stdout.splitlines() if line]
            if lines:
                out_lines.extend(lines)
            if len(out_lines) >= 50:
                break
        if not out_lines:
            cmd = (
                f"find {shlex.quote(home)} -maxdepth 4 -type f "
                f"-iname '*{shlex.quote(needle)}*' "
                "! -path '*/models/*' "
                "! -path '*/llama.cpp/*' "
                "! -path '*/llamabackup.cpp/*' "
                "! -path '*/sherpa-onnx/*' "
                "! -path '*/stable-diffusion.cpp/*' "
                "! -path '*/koboldcpp/*' "
                "! -path '*/output/*' "
                "! -path '*/downloads/*' "
                "! -path '*/storage/*' "
                "! -path '*/go/*' "
                "2>/dev/null | head -n 20"
            )
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            lines = [line for line in out.stdout.splitlines() if line]
            if lines:
                out_lines.extend(lines)
    except Exception as e:
        return f"[Error] Gagal mencari file: {e}"
    if not out_lines:
        return f"[Error] File '{query}' tidak ditemukan."
    return "\n".join(sorted(set(out_lines))[:50])

def read_file(path, limit=None, line_spec=None):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"[Error] File tidak ditemukan: {path}"
    if os.path.isdir(path):
        return f"[Error] Bukan file: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        return f"[Error] Tidak ada akses: {path}"
    except Exception as e:
        return f"[Error] Gagal membaca file: {e}"

    total = len(lines)
    if line_spec is None:
        selected = lines
    elif line_spec.get("type") == "first":
        selected = lines[: line_spec.get("n", 1)]
    elif line_spec.get("type") == "first_n":
        selected = lines[: line_spec.get("n", total)]
    elif line_spec.get("type") == "line":
        n = line_spec.get("n", 1)
        if 1 <= n <= total:
            selected = [lines[n - 1]]
        else:
            selected = []
    else:
        selected = lines

    if limit is not None:
        selected = selected[:limit]
    text = "".join(selected)
    if not text.endswith("\n"):
        text += "\n"
    header = f"[File] {path} ({total} baris)\n"
    if line_spec:
        header += f"[LineSpec] {line_spec}\n"
    return header + text

def write_file(path, content):
    path = os.path.expanduser(path)
    if _write_requires_consent():
        return f"[🔒 Tulis diblokir: tidak ada persetujuan pengguna. (jalankan /set_write true)]"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        return f"[OK] Tulis file: {path}"
    except PermissionError:
        return f"[Error] Tidak ada akses menulis: {path}"
    except Exception as e:
        return f"[Error] Gagal menulis file: {e}"

def edit_file(path, old, new):
    path = os.path.expanduser(path)
    if _write_requires_consent():
        return f"[🔒 Tulis diblokir: tidak ada persetujuan pengguna. (jalankan /set_write true)]"
    if not os.path.exists(path):
        return f"[Error] File tidak ditemukan: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if old not in text:
            return "[Error] Teks lama tidak ditemukan dalam file."
        text = text.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return f"[OK] Edit file: {path}"
    except PermissionError:
        return f"[Error] Tidak ada akses menulis: {path}"
    except Exception as e:
        return f"[Error] Gagal edit file: {e}"

def extract_path_from_text(text, mode="read"):
    line_spec = None
    m = re.search(r"baris\s+(pertama|ke[-\\s]?(\\d+))", text, re.I)
    if m:
        if m.group(1).lower() == "pertama":
            line_spec = {"type": "first", "n": 1}
        else:
            line_spec = {"type": "line", "n": int(m.group(2))}
    m2 = re.search(r"(\\d+)\\s+baris\\s+pertama", text, re.I)
    if m2:
        line_spec = {"type": "first_n", "n": int(m2.group(1))}

    path = None
    for tok in text.split():
        tc = tok.strip(",.;:!?\"'()[]{}")
        if tc.startswith("~/") or tc.startswith("/"):
            path = tc
            break
        if re.match(r"^[\\w\\-\\./]+\\.(?:txt|md|py|js|json|yaml|csv|log|sh|db|gguf|safetensors)$", tc, re.I):
            path = tc
            break
    if not path:
        # Fallback: coba bare name tanpa ekstensi
        for tok in text.split():
            tc = tok.strip(",.;:!?\"'()[]{}")
            if not tc or tc.startswith("~/") or tc.startswith("/"):
                continue
            if re.match(r"^[\\w\\-\\.]+$", tc, re.I):
                hits = _resolve_bare_name(tc)
                if len(hits) == 1:
                    return hits[0], line_spec
                if len(hits) > 1:
                    return "AMBIGU:" + " | ".join(hits), line_spec
                # 0 hits: jangan break, lanjut ke token berikutnya
                continue
        return None, line_spec
    path = os.path.expanduser(path)

    if mode == "read" and os.path.dirname(path) == "":
        hits = _resolve_bare_name(path)
        if len(hits) == 1:
            return hits[0], line_spec
        if len(hits) > 1:
            return "AMBIGU:" + " | ".join(hits), line_spec
    return path, line_spec


def detect_file_action(text):
    t = text.lower()
    if re.search(r"\\b(?:simpan ke|buat|catat di|tulis ke|write|save)\\b", t):
        action = "write"
    elif re.search(r"\\b(?:baca|tampilkan|lihat|read|open|cari file|cari|cari folder)\\b", t):
        action = "read"
    else:
        return None
    path, line_spec = extract_path_from_text(text, mode=action)
    if not path:
        return None
    result = {"action": action, "path": path}
    if action == "read" and line_spec:
        result["line_spec"] = line_spec
    elif action == "write":
        idx = text.find(path)
        if idx >= 0:
            result["content"] = text[idx + len(path):].strip()
        else:
            result["content"] = ""
    return result


def handle_file_action(action, path, content="", line_spec=None):
    if action == "read":
        if not path or not os.path.exists(path):
            found = find_files(path)
            if found and not found.startswith("[Error]") and "\n" not in found:
                path = found.splitlines()[0].strip()
        return read_file(path, line_spec=line_spec)
    if action == "write":
        return write_file(path, content)
    if action == "edit":
        if _write_requires_consent():
            return f"[🔒 Tulis diblokir: tidak ada persetujuan pengguna. (jalankan /set_write true)]"
        return write_file(path, content)
    if action == "set_write":
        val = (content or "").strip().lower()
        if val in ("true", "1", "yes"):
            set_write_consent(True)
            return "🔒 Tulis diaktifkan (setuju terus)."
        elif val in ("false", "0", "no"):
            set_write_consent(False)
            return "🔒 Tulis diblokir (setuju terus dimatikan)."
        else:
            return "[⚠️] /set_write pakai true atau false."
    if action == "list_dir":
        try:
            from tools.dir_manager import list_dir as _list_dir
            return _list_dir(path)
        except Exception as e:
            return f"[Error] Gagal membaca folder: {e}"
    return f"[Error] Aksi tidak dikenal: {action}"
