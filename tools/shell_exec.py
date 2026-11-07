#!/usr/bin/env python3
"""Shell execution tools: jalankan perintah Termux/Android dengan aman."""
import os
import subprocess
import shlex

TERMUX_PREFIX = "/data/data/com.termux/files/usr"

ALLOWED_COMMANDS = [
    "ls", "cat", "pwd", "whoami", "date", "echo", "find",
    "grep", "wc", "head", "tail", "mkdir", "touch",
    "cp", "mv", "rm", "chmod", "stat",
    "python3", "python",
    "termux-*",
]

BLOCKED_COMMANDS = [
    "rm -rf /", "mkfs", "dd if=", "sudo", "su",
]

def _is_safe(cmd):
    cmd_lower = cmd.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return False
    return True

def shell_exec(command):
    """Eksekusi perintah shell dengan safety check."""
    if not _is_safe(command):
        return "[Error] Perintah diblokir untuk keamanan"
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "TERMUX_PREFIX": TERMUX_PREFIX}
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out:
            return out
        if err:
            return f"[Error] {err}"
        return "[OK] Perintah berhasil (tanpa output)"
    except subprocess.TimeoutExpired:
        return "[Error] Timeout: perintah terlalu lama"
    except Exception as e:
        return f"[Error] {str(e)}"

def _translate_indonesian_shell(text):
    """Terjemahkan perintah shell ala Indonesia menjadi perintah shell sunguhan."""
    t = text.lower().strip()
    prefix = None
    if t.startswith("cek folder ") or t.startswith("cek dir "):
        prefix = "cek folder " if "cek folder " in t else "cek dir "
    elif t.startswith("lihat folder ") or t.startswith("lihat dir "):
        prefix = "lihat folder " if "lihat folder " in t else "lihat dir "
    elif t.startswith("list folder ") or t.startswith("list dir "):
        prefix = "list folder " if "list folder " in t else "list dir "
    
    if prefix:
        target = text[len(prefix):].strip()
        if not target:
            return "ls -la ."
        # Resolve shorthand
        low = target.lower()
        if low == "home":
            target = "~"
        elif low == "mesin":
            target = "~/mesin"
        elif not target.startswith("/") and not target.startswith("~"):
            target = "~/" + target
        return f"ls -la {target}"
    
    if t.startswith("cek file ") or t.startswith("lihat file "):
        prefix = "cek file " if "cek file " in t else "lihat file "
        target = text[len(prefix):].strip()
        if not target:
            return "ls -la ."
        low = target.lower()
        if low == "home":
            target = "~"
        elif low == "mesin":
            target = "~/mesin"
        elif not target.startswith("/") and not target.startswith("~"):
            target = "~/" + target
        return f"ls -la {target}"
    
    return text

def list_dir(path="."):
    return shell_exec(f"ls -la {shlex.quote(path)}")

def read_file(path, limit=100):
    return shell_exec(f"head -n {limit} {shlex.quote(path)}")

def cwd():
    return shell_exec("pwd")

def hostname():
    return shell_exec("hostname")

def date_now():
    return shell_exec("date '+%H:%M WIB, %A %d %B %Y'")

HANDS = {
    "shell": shell_exec,
    "ls": list_dir,
    "cat": read_file,
    "pwd": cwd,
    "hostname": hostname,
    "date": date_now,
}
