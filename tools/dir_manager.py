import os

def list_dir(path):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"[Error] Path tidak ditemukan: {path}"
    if not os.path.isdir(path):
        return f"[Error] Bukan folder: {path}"
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return f"[Error] Tidak ada akses: {path}"
    if not entries:
        return f"[Info] Folder kosong: {path}"
    out = [f"[Folder] {path}", "Isi:"]
    for name in entries:
        full = os.path.join(path, name)
        kind = "[DIR]" if os.path.isdir(full) else "[FILE]"
        out.append(f"  {kind} {name}")
    return "\n".join(out)
