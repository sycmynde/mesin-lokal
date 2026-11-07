"""
AQI Checker - Helper modul untuk memeriksa kualitas udara lokal.
Digunakan oleh mode_lari.py dan modul lainnya.
"""
import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse

def cek_aqi_lokal():
    """
    Mengambil data kualitas udara lokal.
    Mengembalikan dict dengan kunci:
    - aqi: nilai US AQI (int)
    - kategori: Baik / Sedang / Tidak Sehat / dsb (str)
    - emoji: emoji indikator (str)
    - saran: rekomendasi aktivitas / lari (str)
    - saran_sepeda: rekomendasi sepeda (str)
    - lat, lon, sumber: informasi lokasi
    """
    mesin_dir = os.path.expanduser("~/mesin")
    plugin_path = os.path.join(mesin_dir, "plugins", "aqi_report.py")

    # 1. Coba panggil plugins/aqi_report.py --json
    if os.path.exists(plugin_path):
        try:
            res = subprocess.run(
                ["python3", plugin_path, "--json"],
                capture_output=True,
                text=True,
                timeout=12
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                return data
        except Exception:
            pass

    # 2. Fallback mandiri langsung ke Open-Meteo
    lat, lon = "-6.24", "106.99" # Default Jakarta
    gps_cache = os.path.join(mesin_dir, "nav", "gps_bg.out")
    if os.path.exists(gps_cache):
        try:
            with open(gps_cache, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "latitude" in d and "longitude" in d:
                    lat, lon = str(d["latitude"]), str(d["longitude"])
        except Exception:
            pass

    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "pm2_5,pm10,ozone,us_aqi"
    })
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MesinAI-AQI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            current = raw.get("current", {})
            aqi = int(current.get("us_aqi", 0) or 0)

            if aqi <= 50:
                emoji, kat, saran = "🟢", "Baik", "Aman buat lari! Gaskeun 🏃‍♂️"
            elif aqi <= 100:
                emoji, kat, saran = "🟡", "Sedang", "Lari santai masih OK"
            elif aqi <= 150:
                emoji, kat, saran = "🟠", "Tidak Sehat (Sensitif)", "Kurangi intensitas lari"
            elif aqi <= 200:
                emoji, kat, saran = "🔴", "TIDAK SEHAT", "Tunda lari / wajib masker"
            elif aqi <= 300:
                emoji, kat, saran = "🟣", "Sangat Tidak Sehat", "Di dalam ruangan saja"
            else:
                emoji, kat, saran = "⛔", "BERBAHAYA", "Hindari aktivitas di luar ruangan"

            return {
                "aqi": aqi,
                "kategori": kat,
                "emoji": emoji,
                "saran": saran,
                "lat": lat,
                "lon": lon,
                "pm2_5": current.get("pm2_5"),
                "pm10": current.get("pm10"),
                "sumber": "direct Open-Meteo"
            }
    except Exception as e:
        return {
            "aqi": "?",
            "kategori": "Tidak Diketahui",
            "emoji": "⚠️",
            "saran": f"Gagal mengambil data cuaca: {e}",
            "lat": lat,
            "lon": lon,
            "error": str(e)
        }

if __name__ == "__main__":
    hasil = cek_aqi_lokal()
    print(json.dumps(hasil, indent=2, ensure_ascii=False))
