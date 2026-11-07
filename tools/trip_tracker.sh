#!/data/data/com.termux/files/usr/bin/bash

MESIN="$HOME/mesin"
LOG="$MESIN/nav/.trip_tracker.log"
PYTHON="$PREFIX/bin/python"
GPS="$PREFIX/bin/termux-location"

mkdir -p "$MESIN/nav"

log() {
    echo "$1" >> "$LOG"
}

log "🚴 Trip Tracker dimulai — $(date '+%Y-%m-%d %H:%M:%S')"

while true; do

    # Ambil GPS langsung.
    # Jangan pakai timeout command karena Termux:API sendiri
    # sudah mempunyai mekanisme timeout dari sisi API.
    FIX=$("$GPS" -p gps -r once 2>/dev/null || true)

    # Fallback network.
    if [ -z "$FIX" ]; then
        FIX=$("$GPS" -p network -r once 2>/dev/null || true)
    fi

    if [ -n "$FIX" ]; then
        printf "%s\n" "$FIX" > "$MESIN/nav/gps_bg.out"  # cache GPS buat /aqi

        RESULT=$(printf '%s\n' "$FIX" | "$PYTHON" -c '
import sys
import json

try:
    d = json.load(sys.stdin)
    lat = d.get("latitude")
    lon = d.get("longitude")

    if lat is not None and lon is not None:
        print(f"{float(lat)},{float(lon)}")
except Exception:
    pass
' 2>/dev/null)

        if [ -n "$RESULT" ]; then

            LAT="${RESULT%,*}"
            LON="${RESULT#*,}"

            "$PYTHON" - "$LAT" "$LON" <<'PY' >> "$LOG" 2>&1
import sys
from tools.kalkulator import update_total_perjalanan

lat = float(sys.argv[1])
lon = float(sys.argv[2])

total, delta = update_total_perjalanan(lat, lon)

print(
    f"📍 fix={lat:.7f},{lon:.7f} "
    f"| +{delta:.3f} km "
    f"| total={total:.3f} km"
)
PY

        else
            log "⚠️ JSON GPS tidak valid — $(date '+%H:%M:%S')"
        fi

    else
        log "⚠️ Tidak mendapat fix GPS/network — $(date '+%H:%M:%S')"
    fi

    sleep 10
done
