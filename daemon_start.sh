#!/bin/bash
# daemon_start.sh — start the mesin AI machine cleanly and persistently
DIR="/data/data/com.termux/files/home/mesin"
cd "$DIR" || { echo "cannot cd $DIR" >&2; exit 1; }
export HOME="/data/data/com.termux/files/home"
mkdir -p "$HOME/mesin/logs"

# stop any previous instance
pkill -9 -f llama-server 2>/dev/null
sleep 1

# 1) Router: llama-server (mmap, virtual RAM, port 8080)
nohup "$HOME"/llama.cpp/build/bin/llama-server \
  --models-dir "$HOME"/models \
  -c 2048 -b 512 -ctk q4_0 -ctv q4_0 \
  --repeat-penalty 1.15 --repeat-last-n 64 --load-mode mmap \
  --flash-attn auto --port 8080 --host 127.0.0.1 --threads 4 \
  --jinja --reasoning off > "$HOME/mesin/logs/llama_server.log" 2>&1 &
SRV=$!

# 2) wait for router ready (up to 30s)
READY=0
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8080/models 2>/dev/null | grep -q '"id"'; then READY=1; break; fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "router failed to start:" >&2
  tail -30 "$HOME/mesin/logs/llama_server.log" >&2
  kill "$SRV" 2>/dev/null; exit 1
fi
echo "router up on 8080 (pid $SRV)"

# 3) load the default model
curl -s -X POST http://127.0.0.1:8080/models/load -H "Content-Type: application/json" -d '{"model":"Qwen3.8-2B-Uncensored-Q4_K_M"}' > /dev/null 2>&1

# 4) REPL, kept-alive via a held-open stdin pipe
tail -f /dev/null | python3 main.py
