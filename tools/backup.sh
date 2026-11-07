#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════
#  MESIN AI — BACKUP TOTAL
#  Simpan semua ke /sdcard/MesinAI/
# ══════════════════════════════════════════

TIMESTAMP=$(date +%Y%m%d_%H%M)
BACKUP_DIR="/sdcard/MesinAI"
BACKUP_FILE="$BACKUP_DIR/mesin_backup_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "📦 [Backup] Membungkus seluruh Mesin AI..."
echo "   Source code + Memory + Config + Cermin"
echo ""

tar -czf "$BACKUP_FILE" \
    -C "$HOME" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    mesin

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup berhasil!"
    echo "   📁 $BACKUP_FILE"
    echo "   📏 Ukuran: $SIZE"
    echo ""
    echo "   Untuk restore di HP baru:"
    echo "   1. Copy file ini ke HP baru"
    echo "   2. Jalankan: bash ~/mesin/tools/restore.sh <file>"
else
    echo "❌ Backup gagal!"
fi
