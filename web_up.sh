#!/data/data/com.termux/files/usr/bin/bash
# ═══ MESIN WEB COCKPIT | satu perintah, semua hidup ═══
TERMUX_HOME="/data/data/com.termux/files/home"
cd "$TERMUX_HOME/mesin" || exit 1
mkdir -p logs

# 1) ☁️ Cloud env
if [ -f .env ]; then set -a; . .env; set +a; echo "☁️  Cloud loaded"; fi

# 2) 🧠 llama-server (Auto-detect: 'llama-server' atau 'server')
LLAMA_BIN="/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server"
if [ ! -f "$LLAMA_BIN" ]; then
    LLAMA_BIN="/data/data/com.termux/files/home/llama.cpp/build/bin/server"
fi

if curl -s http://127.0.0.1:8080/models 2>/dev/null | grep -q '"id"'; then
  echo "✅ llama-server sudah jalan"
else
  echo "⏳ Menyalakan llama-server ($LLAMA_BIN)..."
  nohup "$LLAMA_BIN" \
    --models-dir /data/data/com.termux/files/home/models --models-max 1 --no-models-autoload \
    -ngl 0 -c 4096 --port 8080 --host 127.0.0.1 \
    --threads 4 --jinja --reasoning off \
    > logs/router.log 2>&1 &
  
  for i in $(seq 1 30); do
    curl -s http://127.0.0.1:8080/models 2>/dev/null | grep -q '"id"' && break
    sleep 1
  done
  echo "✅ llama-server siap"
  DEFAULT_MODEL="${DEFAULT_MODEL:-Qwen3.8-2B-Uncensored-Q4_K_M.gguf}"
  CLEAN_DEFAULT=$(echo "$DEFAULT_MODEL" | sed 's/\.gguf$//')
  echo "⏳ Auto-load model default: $CLEAN_DEFAULT..."
  curl -s -X POST http://127.0.0.1:8080/models/load -H "Content-Type: application/json" -d "{\"model\":\"$CLEAN_DEFAULT\"}" >/dev/null 2>&1
  echo "✅ Model $CLEAN_DEFAULT siap"
fi

# 3) 🌐 Web server
if curl -s http://127.0.0.1:5000/ >/dev/null 2>&1; then
  echo "✅ Web sudah jalan"
else
  echo "⏳ Menyalakan web..."
  nohup python3 web/server.py > logs/web.log 2>&1 &
  for i in $(seq 1 30); do
    curl -s http://127.0.0.1:5000/ >/dev/null 2>&1 && break
    sleep 1
  done
  if curl -s http://127.0.0.1:5000/ >/dev/null 2>&1; then
    echo "✅ Web siap"
  else
    echo "❌ Web gagal, cek logs/web.log"
  fi
fi

# 4) 👁️ Mata (Vision)
if curl -s http://127.0.0.1:8082/health 2>/dev/null | grep -q '"ok"'; then
  echo "✅ Mata sudah jalan"
else
  echo "⏳ Menyalakan mata..."
  nohup "$LLAMA_BIN" \
    --model "$TERMUX_HOME/models/Qwen3.5-4B-IQ4_XS.gguf" \
    --mmproj "$TERMUX_HOME/models/mmproj-4B-Q8_0.gguf" \
    --host 127.0.0.1 --port 8082 \
    -c 2048 -t 4 -ngl 0 --jinja --reasoning off \
    > logs/vision.log 2>&1 &
  echo "✅ Mata dinyalakan"
fi

# 5) 🔒 Cegah Android membunuh proses
termux-wake-lock 2>/dev/null

echo ""
echo "🚀 Buka browser: http://localhost:5000"
echo "   Termux boleh ditutup/diminimize."
echo "   Matikan: bash ~/mesin/web_down.sh"