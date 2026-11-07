#!/data/data/com.termux/files/usr/bin/bash

# Script generator video LTX-Video
# Rumus aman RAM 8GB (Poco F4):
# - frames: 9 atau 25 atau 49
# - resolusi: kelipatan 32 (256x256, 384x256, 512x320)
# - distilled: steps 4-6, cfg 2.0
# - threads: 4

TERMUX_HOME="/data/data/com.termux/files/home"
PROMPT="${1:-ocean waves rolling slowly toward the shore, static camera, fixed shot}"
NEG_PROMPT="blurry, static, camera pan, camera zoom, watermark"
FRAMES=${2:-9}
WIDTH=${3:-256}
HEIGHT=${4:-256}
STEPS=${5:-4}

STAMP=$(date +%Y%m%d_%H%M%S)
OUT_PREFIX="$TERMUX_HOME/mesin/data/video/vid_${STAMP}"
OUT_MP4="$TERMUX_HOME/mesin/data/video/video_${STAMP}.mp4"

mkdir -p "$TERMUX_HOME/mesin/data/video"

if [ ! -d "$TERMUX_HOME/ltx.cpp/build" ]; then
    echo "❌ Folder build ltx.cpp tidak ditemukan di $TERMUX_HOME/ltx.cpp/build"
    exit 1
fi

cd "$TERMUX_HOME/ltx.cpp/build" || exit 1

echo "🎬 [LTX-Video] Memulai generate video..."
echo "   Prompt: $PROMPT"
echo "   Frames: $FRAMES | Resolusi: ${WIDTH}x${HEIGHT} | Steps: $STEPS"

./ltx-generate \
    --dit "$TERMUX_HOME/models/ltxv-2b-0.9.6-distilled-04-25-Q4_0.gguf" \
    --vae "$TERMUX_HOME/models/ltxv-vae-3d.gguf" \
    --t5 "$TERMUX_HOME/models/t5-v1_1-xl-q4_k_m.gguf" \
    --prompt "$PROMPT" \
    --neg "$NEG_PROMPT" \
    --frames "$FRAMES" \
    --width "$WIDTH" \
    --height "$HEIGHT" \
    --steps "$STEPS" \
    --cfg 2.0 \
    --seed 42 \
    --out "$OUT_PREFIX" \
    --threads 4 \
    --perf

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎞️ Menggabungkan frame PPM menjadi MP4..."
    ffmpeg -y -framerate 24 -i "${OUT_PREFIX}_%04d.ppm" \
        -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT_MP4"

    # Bersihkan file PPM sementara
    rm -f "${OUT_PREFIX}"_*.ppm

    if [ -f "$OUT_MP4" ]; then
        echo "✅ Video berhasil dibuat: $OUT_MP4"
        if command -v termux-open >/dev/null 2>&1; then
            termux-open "$OUT_MP4"
        fi
    fi
else
    echo "❌ Gagal menghasilkan frame video (exit code: $EXIT_CODE)"
    rm -f "${OUT_PREFIX}"_*.ppm
fi

exit $EXIT_CODE
