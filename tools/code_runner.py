#!/usr/bin/env python3
"""Code execution: jalankan Python snippets dengan timeout dan limit."""
import subprocess
import tempfile
import os
import json

SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum,
    "len": len, "range": range, "list": list, "dict": dict,
    "set": set, "tuple": tuple, "str": str, "int": int,
    "float": float, "bool": bool, "print": print,
    "sorted": sorted, "reversed": reversed, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "True": True, "False": False, "None": None,
}

def run_python(code, timeout=10):
    """Jalankan kode Python di subprocess terisolasi."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode == 0:
            return out if out else "[OK] Kode berhasil dijalankan"
        return f"[Error] {err}" if err else f"[Error] Exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return "[Error] Timeout: kode terlalu lama"
    except Exception as e:
        return f"[Error] {str(e)}"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def run_safe_eval(expr):
    """Evaluasi ekspresi Python sederhana dengan builtins aman."""
    try:
        result = eval(expr, {"__builtins__": SAFE_BUILTINS}, {})
        return str(result)
    except Exception as e:
        return f"[Error] {str(e)}"

HANDS = {
    "py_run": run_python,
    "py_eval": run_safe_eval,
}
