#!/usr/bin/env python3
"""MusikBrain: wrapper untuk cmus + playlist manager."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.musik_manager import HANDS as MUSIK_HANDS

class MusikBrain:
    def run(self, data):
        tool = data.get("tool", "")
        args = data.get("args", {})
        alias = {
            "next": "next_track",
            "prev": "prev_track",
            "pause": "toggle_pause",
            "shuffle": "shuffle_on",
            "repeat": "repeat_on",
            "play": "play_playlist",
            "play_query": "play_query",
        }
        tool = alias.get(tool, tool)
        fn = MUSIK_HANDS.get(tool)
        if not fn:
            return f"[Musik] Tool '{tool}' tidak ada."
        try:
            return fn(**args)
        except Exception as e:
            return f"[Musik] Error: {e}"
