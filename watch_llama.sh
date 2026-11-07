#!/bin/bash
# Watchdog untuk auto-revive llama-server kalau pingsan
echo "👁️ Watchdog aktif: Memantau llama-server setiap 10 detik..."

while true; do
    # Cek health endpoint
    if ! curl -s http://127.0.0.1:8080/health > /dev/null 2>&1; then
        echo "⚠️ llama-server mati! Restart otomatis..."
        pkill -9 -f llama-server 2>/dev/null
        sleep 2
        
        # Restart dengan parameter default
        ~/llama.cpp/build/bin/llama-server \
          --models-dir ~/models \
          --models-max 1 \
          --no-models-autoload \
          -c 4096 \
          -b 256 \
          --flash-attn auto \
          --port 8080 \
          --host 127.0.0.1 \
          --threads 4 \
          --jinja \
          --reasoning off \
          > ~/mesin/logs/router.log 2>&1 &
        
        echo "✅ llama-server restart berhasil (PID: $!)"
        sleep 5  # Tunggu server siap
    fi
    sleep 10
done
