#!/usr/bin/env python3
"""CodeBrain: wrapper untuk eksekusi kode Python."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.code_runner import HANDS as CODE_HANDS

class CodeBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        fn = CODE_HANDS.get(tool)
        if not fn:
            return f"[Code] Tool '{tool}' tidak ada."
        try:
            return fn(**args)
        except Exception as e:
            return f"[Code] Error: {e}"
