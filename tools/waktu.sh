#!/data/data/com.termux/files/usr/bin/bash

# Mengambil jam, menit, detik, dan tanggal saat ini
JAM=$(date "+%H:%M:%S")
TANGGAL=$(date "+%d-%m-%Y")
HARI=$(date "+%A")

# Terjemahan hari ke bahasa Indonesia
case "$HARI" in
    "Monday")    HARI_ID="Senin" ;;
    "Tuesday")   HARI_ID="Selasa" ;;
    "Wednesday") HARI_ID="Rabu" ;;
    "Thursday")  HARI_ID="Kamis" ;;
    "Friday")    HARI_ID="Jumat" ;;
    "Saturday")  HARI_ID="Sabtu" ;;
    "Sunday")    HARI_ID="Minggu" ;;
    *)           HARI_ID="$HARI" ;;
esac

echo "🕒 Waktu   : $JAM WIB"
echo "📅 Hari    : $HARI_ID"
echo "📆 Tanggal : $TANGGAL"
