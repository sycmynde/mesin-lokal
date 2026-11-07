#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════
#  MESIN AI — RESTORE DARI BACKUP
#  Kembalikan seluruh Mesin AI dari file
# ══════════════════════════════════════════

if [ -z "$1" ]; then
    echo "Cara pakai:"
    echo "  bash ~/mesin/tools/restore.sh /sdcard/MesinAI/mesin_backup_XXXX.tar.gz"
    echo ""
    echo "File backup yang tersedia:"
    ls -lh /sdcard/MesinAI/mesin_backup_*.tar.gz 2>/dev/null || echo "  (belum ada)"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "❌ File tidak ditemukan: $FILE"
    exit 1
fi

echo "📦 [Restore] Mengembalikan Mesin AI dari backup..."
echo "   Sumber: $FILE"
echo ""

# Backup dulu yang lama kalau ada
if [ -d "$HOME/mesin" ]; then
    echo "⚠️  Folder ~/mesin sudah ada. Backup dulu yang lama..."
    tar -czf "/sdcard/MesinAI/mesin_OLD_$(date +%Y%m%d_%H%M).tar.gz" \
        -C "$HOME" --exclude='__pycache__' mesin 2>/dev/null
    rm -rf "$HOME/mesin"
fi

tar -xzf "$FILE" -C "$HOME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Restore berhasil! Mesin AI sudah kembali."
    echo "   🧠 Memory: $(cat ~/mesin/memory/memory.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("facts",[])), "facts,", len(d.get("preferences",[])), "prefs")' 2>/dev/null || echo 'cek manual')"
    echo ""
    echo "   Langkah selanjutnya:"
    echo "   1. Install Termux + Python di HP baru"
    echo "   2. pip install requests (jika perlu)"
    echo "   3. Install llama.cpp + model"
    echo "   4. python ~/mesin/mesin1"
    echo ""
    echo "   🧬 Mesin siap diwariskan!"
else
    echo "❌ Restore gagal!"
fi
