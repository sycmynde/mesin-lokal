import ast, sys, os, importlib

root = "/data/data/com.termux/files/home/mesin"
skip_dirs = {".git", "node_modules", "__pycache__", "venv", "logs", "data", "web"}
mods = set()

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            try:
                src = open(p, encoding="utf-8").read()
            except Exception:
                continue
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        mods.add(a.name.split("[")[0].split(" as ")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods.add(node.module.split("[")[0].split(" as ")[0])

missing = []
for m in sorted(mods):
    try:
        importlib.import_module(m)
    except Exception as e:
        if isinstance(e, ModuleNotFoundError):
            missing.append((m, str(e)))

print("TOTAL IMPORTS:", len(mods))
print("MISSING:", len(missing))
for m, e in missing:
    print("  MISSING:", m)
