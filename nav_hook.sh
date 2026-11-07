#!/data/data/com.termux/files/usr/bin/bash
# nav_hook.sh — jembatan antara router mesin dan nav.sh
# Return 0 = ditangani nav (jangan kirim ke AI)
# Return 1 = bukan urusan nav (lanjut ke AI)

NAV="$HOME/mesin/nav.sh"
input="$1"

case "$input" in
    gps|GPS|"nyalain gps"|"nyalakan gps")
        "$NAV" gps; exit 0 ;;
    jangkar|"pasang jangkar"|"titik awal")
        "$NAV" jangkar; exit 0 ;;
    tujuan|"set tujuan"|"tujuan di sini")
        "$NAV" tujuan; exit 0 ;;
    "di mana"|"dimana"|"kita di mana"|"posisi")
        "$NAV" dimana; exit 0 ;;
    "jarak ke titik awal"|"jarak dari titik awal"|"berapa jauh dari awal")
        "$NAV" jarak; exit 0 ;;
    "berapa jauh lagi"|"jarak tujuan"|"jarak ke tujuan"|"sisa berapa")
        "$NAV" jarak tujuan; exit 0 ;;
    "status nav"|"status navigasi")
        "$NAV" status; exit 0 ;;
    *)
        exit 1 ;;  # bukan nav → lanjut ke AI
esac
