#!/usr/bin/env python3

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_CANDIDATES = [
    ROOT / "data" / "chat_history.db",
    ROOT / "web" / "chat_history.db",
    ROOT / "data" / "memory" / "memory.db",
    ROOT / "data" / "pribadi.db",
]

DIR_CANDIDATES = [
    ROOT / "data" / "cache",
    ROOT / "data" / "sessions",
    ROOT / "data" / "logs",
    ROOT / "data" / "memory",
    ROOT / "memory",
    ROOT / "logs",
]


def human_size(num):
    try:
        num = float(num)
    except Exception:
        return str(num)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024

    return f"{num:.1f}PB"


def collect_db_files():
    files = []

    for p in DB_CANDIDATES:
        if p.exists():
            files.append(p.resolve())

    for base in ["data", "web", "memory", "."]:
        root = ROOT if base == "." else ROOT / base
        if not root.exists():
            continue

        pattern = "*.db" if base == "." else "**/*.db"

        for p in root.glob(pattern):
            if p.is_file():
                rp = p.resolve()
                if rp not in files:
                    files.append(rp)

    return files


def scan_dir(d: Path):
    if not d.exists():
        print("  tidak ada")
        return

    if not d.is_dir():
        print("  bukan folder")
        return

    total_files = 0
    total_dirs = 0
    total_size = 0
    latest = []

    for p in d.rglob("*"):
        if p.is_file():
            total_files += 1
            try:
                size = p.stat().st_size
            except Exception:
                size = 0

            try:
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0

            total_size += size
            latest.append((mtime, size, p))

        elif p.is_dir():
            total_dirs += 1

    latest.sort(reverse=True)

    print(f"  files={total_files}, dirs={total_dirs}, size={human_size(total_size)}")

    for _, size, p in latest[:5]:
        try:
            rel = p.relative_to(ROOT)
        except Exception:
            rel = p
        print(f"    terbaru: {rel} ({human_size(size)})")


def scan_db(db: Path):
    print(f"\nDB: {db}")

    if not db.exists():
        print("  tidak ada")
        return

    try:
        size = db.stat().st_size
        print(f"  ukuran: {human_size(size)}")

        uri = f"file:{db}?mode=ro"
        con = sqlite3.connect(uri, uri=True)

        cur = con.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        rows = cur.fetchall()

        if not rows:
            print("  tidak ada table/view")

        for name, typ in rows:
            ident = name.replace('"', '""')

            try:
                count = con.execute(f'SELECT COUNT(*) FROM "{ident}"').fetchone()[0]
            except Exception as e:
                count = f"ERR: {e}"

            try:
                cols = [
                    r[1]
                    for r in con.execute(f'PRAGMA table_info("{ident}")').fetchall()
                ]
            except Exception:
                cols = []

            print(f"  {typ}: {name} rows={count}")
            if cols:
                print(f"    kolom: {', '.join(cols)}")

        con.close()

    except Exception as e:
        print(f"  error: {e}")


def main():
    print("ROOT project:", ROOT)

    dbs = collect_db_files()

    print("\n== Kandidat folder memori/cache ==")

    for d in DIR_CANDIDATES:
        try:
            rel = d.relative_to(ROOT)
        except Exception:
            rel = d

        print(f"\nDIR: {rel}")
        scan_dir(d)

    print("\n== Kandidat DB ==")

    for db in dbs:
        try:
            rel = db.relative_to(ROOT)
        except Exception:
            rel = db
        print(rel)

    print("\n== Detail DB ==")

    for db in dbs:
        scan_db(db)


if __name__ == "__main__":
    main()
