#!/data/data/com.termux/files/usr/bin/bash
pkill -f "web/server.py" 2>/dev/null
pkill -f "llama-server" 2>/dev/null
termux-wake-unlock 2>/dev/null
echo "🛑 Web + llama-server dimatikan"
