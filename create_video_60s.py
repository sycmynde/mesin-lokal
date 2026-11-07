"""
Buat video 60 detik - alternatif ffmpeg direct
"""
import subprocess
import sys
import os

def check_ffmpeg():
    result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
    return result.returncode == 0

def create_video_direct():
    """Buat video 60 detik dengan ffmpeg"""
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', 'color=c=black:s=720x1280:r=24:d=60',
        '-vf', 'drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text=SILKHANNA$$$:fontsize=80:fontcolor=gold:x=(w-text_w)/2:y=(h-text_h)/4',
        '-vf', 'format=yuv420p',
        '/data/data/com.termux/files/home/mesin/silkhannass_60s.mp4'
    ]
    return ffmpeg_cmd

if __name__ == "__main__":
    if check_ffmpeg():
        print("ffmpeg ditemukan, jalankan perintah berikut:")
        cmd = create_video_direct()
        print(" ".join(cmd))
    else:
        print("ffmpeg tidak terpasang - install dulu: pkg install ffmpeg")