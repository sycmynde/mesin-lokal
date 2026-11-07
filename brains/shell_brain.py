#!/usr/bin/env python3
"""ShellBrain: wrapper untuk shell execution."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.shell_exec import HANDS as SHELL_HANDS

class ShellBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        if not tool:
            text = data.get("text", "")
            if text:
                from tools.shell_exec import shell_exec, _translate_indonesian_shell
                return shell_exec(_translate_indonesian_shell(text))
            return "[Shell] Tool tidak ada dan teks kosong."
        fn = SHELL_HANDS.get(tool)
        if not fn:
            return f"[Shell] Tool '{tool}' tidak ada."
        try:
            if tool == "shell":
                from tools.shell_exec import _translate_indonesian_shell
                cmd = args.get("command", "")
                if cmd:
                    args = {**args, "command": _translate_indonesian_shell(cmd)}
            return fn(**args)
        except Exception as e:
            return f"[Shell] Error: {e}"
