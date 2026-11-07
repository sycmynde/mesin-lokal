#!/usr/bin/env python3
"""WebBrain: wrapper untuk web search dan extract."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.web_search import HANDS as WEB_HANDS

class WebBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        fn = WEB_HANDS.get(tool)
        if not fn:
            return f"[Web] Tool '{tool}' tidak ada."
        try:
            return fn(**args)
        except Exception as e:
            return f"[Web] Error: {e}"
