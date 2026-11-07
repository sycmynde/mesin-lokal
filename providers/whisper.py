"""WhisperProvider — telinga mesin. small-q5_1, ~1 detik per 5 detik audio."""
import subprocess, os

WHISPER_BIN = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
# Pilih model terbesar yang tersedia: base > tiny
for _m in ["ggml-small-q5_1.bin", "ggml-small.bin", "ggml-base.bin", "ggml-tiny-q8_0.bin"]:
    _p = os.path.expanduser(f"~/models/whisper/{_m}")
    if os.path.exists(_p):
        MODEL = _p
        break
PROMPT_BIAS = "Halo mesin,  catatan harian"

# Kamus koreksi: whisper salah dengar → yang bener
KOREKSI = {
    "mekasih": "Bekasi", "berkasih": "Bekasi", "bekas i": "Bekasi",
    "masian": "Mesin", "mesil": "Mesin",
    "semarang raya": "Sepakat Raya",
    "tapan": "berapa",
    "kek": "cek",
    "kualita": "kualitas",
    "sudara": "udara",
}

class WhisperProvider:
    name = "whisper-small"

    def koreksi(self, teks):
        low = teks.lower()
        for salah, bener in KOREKSI.items():
            if salah in low:
                import re
                teks = re.sub(re.escape(salah), bener, teks, flags=re.I)
        return teks

    def transcribe(self, wav_path, lang="id", timeout=120):
        if not os.path.exists(wav_path):
            return None
        try:
            out = subprocess.run(
                [WHISPER_BIN, "-m", MODEL, "-l", lang,
                 "-f", wav_path, "-nt", "-np", "--prompt", PROMPT_BIAS],
                capture_output=True, text=True, timeout=timeout
            )
            text = out.stdout.strip()
            return self.koreksi(text) if text else None
        except Exception:
            return None

whisper_provider = WhisperProvider()
