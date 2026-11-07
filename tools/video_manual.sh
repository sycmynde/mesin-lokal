#!/data/data/com.termux/files/usr/bin/bash

PROMPT="$1"
FRAMES=${2:-9}
WIDTH=${3:-256}
HEIGHT=${4:-256}
STEPS=${5:-4}

if [ -z "$PROMPT" ]; then
    echo "Usage: ./video_manual.sh 'prompt' [frames=9] [width=256] [height=256] [steps=4]"
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
OUT_PREFIX="$HOME/mesin/data/video/manual_${STAMP}"
OUT_MP4="$HOME/mesin/data/video/manual_${STAMP}.mp4"

mkdir -p "$HOME/mesin/data/video"

if [ ! -d "$HOME/ltx.cpp/build" ]; then
    echo "❌ Folder build ltx.cpp tidak ditemukan di ~/ltx.cpp/build"
    exit 1
fi

cd "$HOME/ltx.cpp/build" || exit 1

echo "🎬 START VIDEO GEN: $PROMPT"

sd-cli -M vid_gen \
-m ~/models/toonyou_beta6_q4_1.gguf \
--motion-module ~/models/animatediff/mm_sd15_v3.safetensors \         
-p "a cat playing piano" \                                            
--video-frames 4 \                                                    
--height 256 --width 256 \                                            
--steps 25 \                                                          
--cfg-scale 7.0 \                                                     
--sampling-method dpm++2mv2 \                                         
--scheduler karras \                                                  
--threads 4 \                                                         
--backend diffusion=cuda0 \
--offload-to-cpu \                                                    
-o ~/mesin/data/video/ad_karras_%03d.png

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎞️ Menggabungkan frame..."
    ffmpeg -y -framerate 24 -i "${OUT_PREFIX}_%04d.ppm" \
        -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT_MP4"
    rm -f "${OUT_PREFIX}"_*.ppm
    
    if [ -f "$OUT_MP4" ]; then
        echo "✅ SUCCESS: Video tersimpan di $OUT_MP4"
        if command -v termux-open >/dev/null 2>&1; then
            termux-open "$OUT_MP4"
        fi
    fi
else
    echo "❌ FAILED: Error code $EXIT_CODE."
    rm -f "${OUT_PREFIX}"_*.ppm
fi

exit $EXIT_CODE
