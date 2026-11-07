#!/data/data/com.termux/files/usr/bin/bash
DUR=${1:-10}
DIR=~/mesin/data/audio
mkdir -p "$DIR"
# sapu perekam nyangkut sebelum mulai
for p in /proc/[0-9]*; do
  c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
  case "$c" in *termux-microphone-record*) kill -9 "${p#/proc/}" 2>/dev/null ;; esac
done
STAMP=$(date +%Y%m%d_%H%M%S)
TMP="/sdcard/Download/rek_$STAMP.m4a"
WAV="$DIR/rek_$STAMP.wav"

echo "🎙️ Rekam $DUR detik... bicara sekarang:" >&2
timeout $((DUR + 15)) termux-microphone-record -f "$TMP" -r 16000 -c 1 -b 32000 -l "$DUR" -e aac 1>&2
sleep $((DUR + 2))
termux-microphone-record -q >/dev/null 2>&1
sleep 1

if [ ! -s "$TMP" ]; then
    echo "❌ Rekaman kosong" >&2; rm -f "$TMP"; exit 1
fi
# loudnorm = normalisasi volume otomatis, anti-halusinasi-karena-pelan
ffmpeg -y -i "$TMP" -af "loudnorm=I=-16:TP=-1.5" \
    -ar 16000 -ac 1 -c:a pcm_s16le "$WAV" -loglevel error || exit 1
rm -f "$TMP"
echo "$WAV" | tail -1
