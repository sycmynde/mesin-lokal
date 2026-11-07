#!/usr/bin/env python3
"""Plugin loader: modular skills/fungsi tambahan tanpa edit core."""
import os
import sys
import json
import importlib.util

BASE = os.path.expanduser("/data/data/com.termux/files/home/mesin")
PLUGINS_DIR = os.path.join(BASE, "plugins")

def _load_module(name, path):
    """Load Python module dari file path."""
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None

def discover_plugins():
    """Scan folder plugins/ dan kembalikan daftar plugin metadata."""
    plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return plugins
    for entry in os.listdir(PLUGINS_DIR):
        plugin_dir = os.path.join(PLUGINS_DIR, entry)
        manifest = os.path.join(plugin_dir, "plugin.json")
        if not os.path.isfile(manifest):
            continue
        try:
            with open(manifest, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta.setdefault("name", entry)
            meta.setdefault("dir", plugin_dir)
            plugins.append(meta)
        except Exception:
            continue
    return plugins

def load_plugin_hands():
    """Muat semua tools dari plugins aktif ke dict HANDS."""
    hands = {}
    for meta in discover_plugins():
        if not meta.get("enabled", True):
            continue
        name = meta.get("name", "unnamed")
        module_path = meta.get("module")
        if not module_path:
            continue
        abs_path = os.path.join(meta.get("dir", ""), module_path)
        if not os.path.isfile(abs_path):
            continue
        mod = _load_module(f"plugin_{name}", abs_path)
        if mod is None:
            continue
        tools = getattr(mod, "HANDS", None)
        if isinstance(tools, dict):
            for tool_name, fn in tools.items():
                if callable(fn):
                    hands[tool_name] = fn
    return hands

# Alias untuk kompatibilitas
reload_plugins = load_plugin_hands

def list_plugins():
    """List semua plugin yang terdaftar."""
    plugins = discover_plugins()
    if not plugins:
        return "Tidak ada plugin terdaftar."
    lines = ["Plugins:"]
    for p in plugins:
        status = "ON" if p.get("enabled", True) else "OFF"
        lines.append(f" - {p.get('name')}: {p.get('description', '')} [{status}]")
    return "\n".join(lines)

HANDS = {
    "list_plugins": list_plugins,
    "reload_plugins": load_plugin_hands,
}
