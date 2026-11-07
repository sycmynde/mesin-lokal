#!/data/data/com.termux/files/usr/bin/bash

# Ambil koordinat dari cache jika tersedia
OUT="$HOME/mesin/nav/gps_bg.out"
LAT="-6.24"
LON="106.99"

if [ -f "$OUT" ]; then
    COORD=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    lat = d.get("latitude")
    lon = d.get("longitude")
    if lat and lon:
        print(f"{lat},{lon}")
except Exception:
    pass
' "$OUT" 2>/dev/null)
    if [ -n "$COORD" ]; then
        LAT="${COORD%,*}"
        LON="${COORD#*,}"
    fi
fi

# Panggil API Open-Meteo Air Quality
URL="https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${LAT}&longitude=${LON}&current=pm2_5,pm10,ozone,us_aqi"

if command -v jq >/dev/null 2>&1; then
    curl -s "$URL" | jq .current
else
    curl -s "$URL"
fi
