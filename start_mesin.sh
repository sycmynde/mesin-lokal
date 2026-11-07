#!/bin/bash

#export LD_LIBRARY_PATH="$HOME/llama.cpp/build/bin"

# ============================================
#  LOAD CLOUD API KEYS
# ============================================
if [ -f "$HOME/mesin/.env" ]; then
    set -a
    . "$HOME/mesin/.env"
    set +a
    echo "☁️ Cloud API environment: loaded"
else
    echo "⚠️ .env tidak ditemukan — Cloud fallback mungkin tidak aktif"
fi


export LLAMA_SERVER="/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server"
export LD_LIBRARY_PATH=""
export MODELS_DIR="/data/data/com.termux/files/home/models"
export DEFAULT_MODEL="Qwen3.8-2B-Uncensored-Q4_K_M.gguf"
export MODEL_PATH="$MODELS_DIR/$DEFAULT_MODEL"
export PORT="8080"
export LOG_DIR="/data/data/com.termux/files/home/mesin/logs"
export LOG_FILE="$LOG_DIR/llama_server.log"


echo "⚙️ MAX_MODELS=${MAX_MODELS:-1} | Mode: fleksibel"
echo "   💾 Tanpa penguncian RAM — hemat ruang, muat lebih banyak"

mkdir -p "$LOG_DIR"

echo "╔══════════════════════════════════════╗"
echo "║   🚀 MESIN AI 3-TIER | Router Mode                                             ║"
echo "╠══════════════════════════════════════╣"
echo "║  ⚡ Instan  : 🙈                                                                                  ║"
echo "║  🎯 Default :     $DEFAULT_MODEL                                              ║"
echo "║  ☁️ Cloud    : Online AI                                                                     ║"
echo "╚══════════════════════════════════════╝"
echo ""

pkill -9 -f llama-server 2>/dev/null
sleep 2

"$LLAMA_SERVER" \
  --models-dir "$MODELS_DIR" \
  -c 65534 \
  -b 1024 \
  -ctk q4_0 \
  -ctv q4_0 \
  --repeat-penalty 1.15 \
  --repeat-last-n 64 \
  --load-mode mmap \
  --flash-attn on \
  --port "$PORT" \
  --host 127.0.0.1 \
  --threads 4 \
  --jinja \
  --reasoning off \
  > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo "⏳ Loading router (PID: $SERVER_PID)..."

READY=0
for i in {1..30}; do
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server mati. Log:"
    tail -20 "$LOG_FILE"
    exit 1
  fi
  if curl -s http://127.0.0.1:$PORT/models 2>/dev/null | grep -q '"id"'; then
    READY=1
    break
  fi
  sleep 1
done

if [ $READY -eq 0 ]; then
  echo "❌ Timeout. Log:"
  tail -20 "$LOG_FILE"
  exit 1
fi

echo "✅ Router Siap! http://127.0.0.1:$PORT"
echo ""
echo "📋 Model terdeteksi:"
curl -s http://127.0.0.1:$PORT/models | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for m in data.get('data', []):
        print(f'   ✅ {m[\"id\"]}')
except: pass
" 2>/dev/null
echo ""
CLEAN_DEFAULT=$(echo "$DEFAULT_MODEL" | sed 's/\.gguf$//')
echo "⏳ Auto-load model default: $CLEAN_DEFAULT..."
curl -s -X POST "http://127.0.0.1:$PORT/models/load" -H "Content-Type: application/json" -d "{\"model\":\"$CLEAN_DEFAULT\"}" >/dev/null 2>&1
echo "✅ Model $CLEAN_DEFAULT siap!"
echo ""

cd /data/data/com.termux/files/home/mesin
PYTHONPATH=/data/data/com.termux/files/home/mesin /data/data/com.termux/files/usr/bin/python3.14 -c "import yaml" 2>/dev/null || PYTHONPATH=/data/data/com.termux/files/home/mesin /data/data/com.termux/files/usr/bin/python3.14 -m pip install --user pyyaml >/dev/null 2>&1 || true
PYTHONPATH=/data/data/com.termux/files/home/mesin /data/data/com.termux/files/usr/bin/python3.14 main.py

echo "🛑 Menghentikan llama-server..."
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

echo "✅ Selesai."
