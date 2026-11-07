#!/data/data/com.termux/files/usr/bin/bash

# 1. BAJAK VARIABEL DARI LUAR SEBELUM JANGKAR DIJALANKAN
export MODEL_PATH="$HOME/models/llama3.2-3b-instruct-q4_0.gguf"

# 2. PASTIKAN SYMLINK QWEN KE LLAMA SUDAH ADA (untuk startmesin.sh)
ln -sf ~/models/llama3.2-3b-instruct-q4_0.gguf ~/models/Qwen3.5-0.8B-Q4_0.gguf 2>/dev/null

# 3. JALANKAN JANGKAR ASLI (TIDAK DIUBAH SAMA SEKALI)
bash ~/mesin/start_mesin.sh
