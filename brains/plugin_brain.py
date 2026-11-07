#!/usr/bin/env python3
"""PluginBrain: wrapper untuk plugin system."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.plugin_loader import load_plugin_hands, HANDS as PLUGIN_HANDS

class PluginBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})

        # Jika tool spesifik ada di PLUGIN_HANDS, jalankan
        if tool in PLUGIN_HANDS:
            fn = PLUGIN_HANDS[tool]
            try:
                return fn(**args)
            except Exception as e:
                return f"[Plugin] Error: {e}"

        # Jika tool adalah "plugin_call", cari tool di plugin hands
        if tool == "plugin_call":
            plugin_tool = args.get("plugin_tool")
            plugin_args = args.get("plugin_args", {})
            hands = load_plugin_hands()
            fn = hands.get(plugin_tool)
            if not fn:
                return f"[Plugin] Tool '{plugin_tool}' tidak ditemukan di plugins."
            try:
                return fn(**plugin_args)
            except Exception as e:
                return f"[Plugin] Error: {e}"

        # Jika tool adalah "list_plugins"
        if tool == "list_plugins":
            return PLUGIN_HANDS.get("list_plugins", lambda: "Plugin loader tidak aktif")()

        return f"[Plugin] Tool '{tool}' tidak ada."
