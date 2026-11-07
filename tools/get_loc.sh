#!/data/data/com.termux/files/usr/bin/bash
# get_loc.sh - Hanya Koordinat & Waktu. Selesai.

echo "📡 Mengaktifkan GPS..." >&2
CURRENT=$(termux-location -p gps -r once 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$CURRENT" ]; then
    echo " Gagal mendapatkan lokasi." >&2
    exit 1
fi

CURR_LAT=$(echo "$CURRENT" | grep '"latitude"' | awk '{print $2}' | tr -d ',')
CURR_LON=$(echo "$CURRENT" | grep '"longitude"' | awk '{print $2}' | tr -d ',')

# Ambil waktu lokal sistem
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Output bersih: hanya koordinat & waktu
echo "${CURR_LAT},${CURR_LON} | ${TIMESTAMP}"

echo " GPS nonaktif." >&2
