"""Coding Inspector v0.1 — inspeksi Python baca-saja."""

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    ".git", ".autohand", "__pycache__", "mesin",
    "node_modules", ".venv", "venv",
}
EXCLUDED_FILES = {
    ".env", ".env.local", "settings.local.json",
}
MAX_FILE_BYTES = 512_000


def resolve_source(path):
    """Terima path relatif/absolut hanya jika berada di root yang diizinkan."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate

    resolved = candidate.resolve(strict=True)

    if not resolved.is_relative_to(ROOT):
        raise ValueError("Path berada di luar root proyek.")

    relative = resolved.relative_to(ROOT)

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        raise ValueError("Path berada di direktori yang dikecualikan.")

    if resolved.name in EXCLUDED_FILES:
        raise ValueError("File dikecualikan dari inspeksi.")

    if not resolved.is_file():
        raise ValueError("Path bukan file biasa.")

    if resolved.suffix != ".py":
        raise ValueError("Versi awal hanya menerima file Python (.py).")

    if resolved.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("File terlalu besar untuk batas inspeksi v0.1.")

    return resolved


def inspect_python(path=None, **_opts):
    """Periksa sintaks tanpa mengeksekusi file sumber."""
    if path is None:
        return {"ok": False, "error": "parameter path wajib disediakan"}
    try:
        source = resolve_source(path)
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    try:
        ast.parse(text, filename=str(source))
    except SyntaxError as exc:
        return {
            "ok": True,
            "path": str(source.relative_to(ROOT)),
            "syntax_ok": False,
            "line": exc.lineno,
            "column": exc.offset,
            "message": exc.msg,
        }

    return {
        "ok": True,
        "path": str(source.relative_to(ROOT)),
        "syntax_ok": True,
        "lines": len(text.splitlines()),
        "message": "Sintaks Python valid; ini bukan jaminan bebas bug.",
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspeksi sintaks Python secara baca-saja."
    )
    parser.add_argument("path", help="Path file Python relatif atau absolut")
    args = parser.parse_args()

    result = inspect_python(args.path)

    print("=== CODING INSPECTOR v0.1 ===")
    for key, value in result.items():
        print(f"{key}: {value}")

    if not result.get("ok") or not result.get("syntax_ok", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
