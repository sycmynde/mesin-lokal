#!/data/data/com.termux/files/usr/bin/bash
# Anti-macet: cache segar langsung dipakai (nol rebutan GPS),
# cache basi → fix baru dengan timeout paksa.
OUT="$HOME/mesin/nav/gps_bg.out"

emit() {
    python3 - "$OUT" << 'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print("{},{}".format(d["latitude"], d["longitude"]))
except Exception as e:
    print("parse gagal:", e, file=sys.stderr)
    sys.exit(2)
PY
}

# 1) Cache < 10 menit? Pakai — jangan sentuh GPS sama sekali.
if [ -f "$OUT" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$OUT" 2>/dev/null || echo 0) ))
    if [ "$AGE" -lt 600 ]; then
        emit && exit 0
    fi
fi

# 2) Cache basi → fix baru, dipaksa timeout.
FIX=$(timeout 15 termux-location -p gps -r once 2>/dev/null)
if [ -z "$FIX" ]; then
    FIX=$(timeout 10 termux-location -p network -r once 2>/dev/null)
fi
if [ -z "$FIX" ]; then
    echo "❌ GPS gagal/timeout — cache lama dipertahankan" >&2
    exit 1
fi
echo "$FIX" > "$OUT"
emit
