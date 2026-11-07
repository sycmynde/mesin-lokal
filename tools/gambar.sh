#!/data/data/com.termux/files/usr/bin/bash

MODEL_PATH="/data/data/com.termux/files/home/models/sd_turbo-f16-q8_0.gguf"
VAE_PATH="/data/data/com.termux/files/home/models/vae-ft-mse-840000-ema-pruned.safetensors"
PROMPT=""
NEG="lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
WIDTH=512
HEIGHT=512
STEPS=2
CFG=7.0
SEED=-12345
THREADS=2
SAMPLING_METHOD="dpm++2mv2"
PREVIEW_METHOD="none"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) MODEL_PATH="$2"; shift 2 ;;
    -p) PROMPT="$2"; shift 2 ;;
    -n) NEG="$2"; shift 2 ;;
    -W) WIDTH="$2"; shift 2 ;;
    -H) HEIGHT="$2"; shift 2 ;;
    --steps) STEPS="$2"; shift 2 ;;
    --cfg-scale) CFG="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --sampling-method) SAMPLING_METHOD="$2"; shift 2 ;;
    --preview) PREVIEW_METHOD="$2"; shift 2 ;;
    *) 
      if [ -z "$PROMPT" ]; then
        PROMPT="$1"
      elif [ -z "$MODEL_PATH" ]; then
        MODEL_PATH="$1"
      fi
      shift
      ;;
  esac
done

if [ -z "$PROMPT" ]; then
    echo "❌ ERROR: Prompt kosong!"
    echo "Cara pakai: $0 -p 'deskripsi gambar dalam bahasa inggris' [-m path/to/model.gguf]"
    exit 1
fi

SD_DIR="/data/data/com.termux/files/home/stable-diffusion.cpp/build/bin"
cd "$SD_DIR" || { echo "❌ Folder SD-CPP tidak ditemukan di $SD_DIR!"; exit 1; }

LOG="/data/data/com.termux/files/home/mesin/logs/gambar.log"
mkdir -p /data/data/com.termux/files/home/mesin/logs
OUTPUT_FILE="/data/data/com.termux/files/home/mesin/karya_$(date +%s).png"

echo "🎨 [START] Generating: $PROMPT" >> "$LOG"
echo "-------------------------------------------------------" >> "$LOG"

./sd-cli \
    -m "$MODEL_PATH" \
    -p "$PROMPT" \
    -n "$NEG" \
    --vae "$VAE_PATH" \
    -H "$HEIGHT" -W "$WIDTH" \
    --sampling-method "$SAMPLING_METHOD" \
    --steps "$STEPS" \
    --cfg-scale "$CFG" \
    --threads "$THREADS" \
    --seed "$SEED" \
    --preview "$PREVIEW_METHOD" \
    -o "$OUTPUT_FILE" >> "$LOG" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS: Gambar tersimpan di $OUTPUT_FILE" | tee -a "$LOG"
else
    echo "❌ FAILED: Error code $EXIT_CODE. Cek log di $LOG" | tee -a "$LOG"
fi

exit $EXIT_CODE
