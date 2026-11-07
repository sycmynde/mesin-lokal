#!/usr/bin/env python3
"""TermuxBrain: wrapper untuk tools Termux API."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.termux_api import HANDS as TERMUX_HANDS

class TermuxBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        fn = TERMUX_HANDS.get(tool)
        if not fn:
            return f"[Termux] Tool '{tool}' tidak ada."
        try:
            return fn(**args)
        except Exception as e:
            return f"[Termux] Error: {e}"
