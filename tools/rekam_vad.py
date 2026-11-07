#!/data/data/com.termux/files/usr/bin/python3
"""
Rekam suara dengan Energy-based VAD (Voice Activity Detection).
Auto-stop saat user diam 1.5 detik setelah mulai berbicara.
Usage: python rekam_vad.py [output_path]
"""
import sys
import os
import numpy as np
import sounddevice as sd
import wave
from datetime import datetime

# Konfigurasi VAD
SAMPLE_RATE = 16000
CHANNELS = 1
ENERGY_THRESHOLD = 450      # Ambang batas energi suara
SILENCE_DURATION = 1.5      # Detik hening sebelum rekaman otomatis berhenti
MAX_INITIAL_SILENCE = 5.0   # Batas tunggu pengguna mulai bicara (detik)
MAX_DURATION = 30.0         # Batas maksimal total rekaman (detik)

def calculate_energy(audio_chunk):
    """Hitung RMS energy dari audio chunk"""
    if len(audio_chunk) == 0:
        return 0.0
    audio_float = audio_chunk.astype(np.float32)
    rms = np.sqrt(np.mean(audio_float**2))
    return float(rms)

def record_with_vad(output_path):
    print("🎙️ Mulai mendengarkan... silakan bicara (auto-stop saat hening)", file=sys.stderr)
    
    audio_buffer = []
    has_speech_started = False
    silence_start = None
    total_duration = 0.0
    chunk_size = int(SAMPLE_RATE * 0.25)  # 0.25 detik per chunk untuk responsivitas lebih baik
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"⚠️ {status}", file=sys.stderr)
        audio_buffer.append(indata.copy())
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, 
                            dtype='int16', blocksize=chunk_size,
                            callback=audio_callback):
            
            while total_duration < MAX_DURATION:
                sd.sleep(250)  # tunggu 0.25 detik
                total_duration += 0.25
                
                if not audio_buffer:
                    continue
                
                # Evaluasi chunk audio terakhir
                chunk = audio_buffer[-1].flatten()
                energy = calculate_energy(chunk)
                
                if not has_speech_started:
                    # Menunggu pengguna mulai berbicara
                    if energy > ENERGY_THRESHOLD:
                        has_speech_started = True
                        silence_start = None
                        print(f"🗣️ Suara terdeteksi (energy: {energy:.0f})", file=sys.stderr)
                    else:
                        if total_duration >= MAX_INITIAL_SILENCE:
                            print("⏱️ Tidak ada ucapan dalam waktu tunggu.", file=sys.stderr)
                            break
                else:
                    # Pengguna sudah mulai bicara, pantau jeda diam
                    if energy > ENERGY_THRESHOLD:
                        silence_start = None  # Sedang bicara aktif
                    else:
                        if silence_start is None:
                            silence_start = total_duration
                        elif total_duration - silence_start >= SILENCE_DURATION:
                            print(f"✅ Hening {SILENCE_DURATION}s tercapai, selesai rekam.", file=sys.stderr)
                            break
                            
    except Exception as e:
        print(f"❌ Error perangkat audio: {e}", file=sys.stderr)
        return None

    if not has_speech_started or not audio_buffer:
        print("⚠️ Tidak ada suara pengguna yang terdeteksi.", file=sys.stderr)
        return None

    try:
        full_audio = np.concatenate(audio_buffer, axis=0).flatten()
        
        # Buat folder jika belum ada
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(full_audio.astype(np.int16).tobytes())
            
        print(f"💾 Tersimpan: {output_path} ({total_duration:.1f}s)", file=sys.stderr)
        return output_path
    except Exception as e:
        print(f"❌ Gagal menyimpan file WAV: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        out_path = sys.argv[1]
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.expanduser(f"~/mesin/data/audio/rek_{stamp}.wav")
    
    result = record_with_vad(out_path)
    if result:
        print(result)
    else:
        sys.exit(0)
