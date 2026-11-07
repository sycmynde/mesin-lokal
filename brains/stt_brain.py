#!/usr/bin/env python3
"""STTBrain: wrapper untuk Speech-to-Text."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.stt_tools import HANDS as STT_HANDS

class STTBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        fn = STT_HANDS.get(tool)
        if not fn:
            return f"[STT] Tool '{tool}' tidak ada."
        try:
            return fn(**args)
        except Exception as e:
            return f"[STT] Error: {e}"
