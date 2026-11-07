#!/usr/bin/env python3
"""AQI Report — penerjemah JSON jadi bahasa manusia.
RIP plugins/aqi.sh (2026): otak brilian, nama salah. 🪦"""
import json, sys, subprocess, os
try:
    from urllib.request import urlopen
    from urllib.parse import urlencode
except ImportError:
    sys.exit("urllib tidak tersedia")

# --- AQI per polutan: gunakan indeks resmi dari Open-Meteo, bukan
# interpolasi lokal dari konsentrasi sesaat. Breakpoint US EPA berubah
# dan beberapa polutan memerlukan periode rata-rata khusus.
AQI_KEYS = {
    "pm2_5": "us_aqi_pm2_5",
    "pm10": "us_aqi_pm10",
    "o3": "us_aqi_ozone",
    "no2": "us_aqi_nitrogen_dioxide",
    "so2": "us_aqi_sulphur_dioxide",
    "co": "us_aqi_carbon_monoxide",
}
FLAG = {
    "pm2_5": "🚬 partikel halus",
    "pm10": "🌋 debu kasar/abu",
    "o3": "☀️ smog fotokimia",
    "no2": "🚗 nitrogen dioksida",
    "so2": "🏭 sulfur dioksida",
    "co": "🔥 karbon monoksida",
}

def angka_aqi_valid(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0

def indeks_polutan(hourly, index):
    subs = {}
    for nama, key in AQI_KEYS.items():
        values = hourly.get(key, [])
        if index < len(values) and angka_aqi_valid(values[index]):
            subs[nama] = int(values[index])
    return subs

def dominan_subs(subs):
    if not subs:
        return None, None, ""
    top = max(subs, key=subs.get)
    return top, subs[top], FLAG.get(top, top)

# --- kategori US AQI ---
def kategori(aqi):
    if aqi <= 50:  return "🟢", "Baik", "Aman buat lari! Gaskeun 🏃‍♂️"
    if aqi <= 100: return "🟡", "Sedang", "Lari santai masih OK"
    if aqi <= 150: return "🟠", "Tidak Sehat (grup sensitif)", "Kurangi intensitas, pemanasan ekstra"
    if aqi <= 200: return "🔴", "TIDAK SEHAT", "Tunda lari / wajib masker"
    if aqi <= 300: return "🟣", "Sangat Tidak Sehat", "Di dalam ruangan aja bro"
    return "⛔", "BERBAHAYA", "JANGAN keluar!"

def saran_sepeda(aqi):
    if aqi <= 50:  return "Aman sepedahan, gaspol 🚴"
    if aqi <= 100: return "Sepedahan santai masih OK"
    if aqi <= 150: return "Sepedahan pendek aja, jangan ngebut"
    if aqi <= 200: return "Tunda sepedahan / masker wajib"
    if aqi <= 300: return "Sepeda statis dalam ruangan aja"
    return "Sepedanya parkir dulu!"

# --- GPS dinamis: cache nav dulu, live belakangan, Jakarta terakhir ---
def get_coord():
    import re, time
    # 1) Cache dari background tracker (fresh walau di bawah genteng)
    src = os.path.expanduser("~/mesin/nav/gps_bg.out")
    try:
        txt = open(src).read()
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            d = json.loads(m.group(0))
            lat, lon = d.get("latitude"), d.get("longitude")
            if lat is not None and lon is not None:
                acc = d.get("accuracy")
                age_min = (time.time() - os.path.getmtime(src)) / 60
                if age_min > 720:
                    raise ValueError(f"cache fosil ({age_min/1440:.0f} hari)")  # → coba live
                def _umur(m):
                    if m < 60:   return f"{m:.0f} mnt"
                    if m < 1440: return f"{m/60:.1f} jam"
                    return f"{m/1440:.0f} hari"
                label = "GPS nav 📍"
                if acc: label += f" ±{acc:.0f}m"
                if age_min > 5: label += f" (cache {_umur(age_min)} lalu)"
                return str(lat), str(lon), label
    except Exception:
        pass
    # 2) Coba live (butuh langit kelihatan)
    try:
        out = subprocess.run(["bash", os.path.expanduser("~/mesin/tools/get_loc.sh")],
                             capture_output=True, text=True, timeout=8)
        m = re.search(r"\{.*\}", out.stdout, re.S)
        if m:
            d = json.loads(m.group(0))
            if d.get("latitude") is not None:
                return str(d["latitude"]), str(d["longitude"]), "GPS live 📍"
    except Exception:
        pass
    # 3) Menyerah pada genteng
    return "-6.24", "106.99", "fallback Jakarta"

lat, lon, sumber = get_coord()
params = {
    "latitude": lat,
    "longitude": lon,
    "current": "pm2_5,pm10,ozone,us_aqi",
    "hourly": ",".join(["us_aqi"] + list(AQI_KEYS.values())),
    "past_hours": 2,
    "forecast_hours": 2,
    "timezone": "auto",
}
url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{urlencode(params)}"

try:
    payload = json.loads(urlopen(url, timeout=10).read())
    data = payload["current"]
    hourly = payload.get("hourly", {})
except Exception as e:
    print(f"❌ Gagal ambil data AQI: {e}")
    sys.exit(1)

aqi = data.get("us_aqi")
if not angka_aqi_valid(aqi):
    print("❌ AQI utama tidak tersedia atau tidak valid")
    sys.exit(1)
aqi = int(aqi)
emoji, kat, saran = kategori(aqi)

# Pilih indeks per polutan dari jam yang sama dengan waktu current jika tersedia.
# Jika tidak, jangan menyamarkan perbedaan timestamp sebagai hasil yang setara.
current_time = str(data.get("time", "?"))
hourly_times = hourly.get("time", [])
target_hour = current_time[:13] if len(current_time) >= 13 else None
hour_index = next(
    (i for i, t in enumerate(hourly_times)
     if target_hour and str(t)[:13] == target_hour),
    None
)
subs = indeks_polutan(hourly, hour_index) if hour_index is not None else {}
pol, pol_aqi, pol_flag = dominan_subs(subs)
hourly_aqi = (
    hourly.get("us_aqi", [])[hour_index]
    if hour_index is not None and hour_index < len(hourly.get("us_aqi", []))
    else None
)
same_hour_check = (
    isinstance(hourly_aqi, (int, float))
    and int(hourly_aqi) == aqi
    and bool(subs)
    and max(subs.values()) == int(hourly_aqi)
)

if "--json" in sys.argv:
    print(json.dumps({
        "aqi": aqi, "emoji": emoji, "kategori": kat, "saran": saran,
        "saran_sepeda": saran_sepeda(aqi),
        "pol": pol, "pol_aqi": pol_aqi, "pol_flag": pol_flag,
        "pm2_5": data.get("pm2_5"), "pm10": data.get("pm10"), "o3": data.get("ozone"),
        "subs": subs,
        "aqi_hourly": hourly_aqi,
        "aqi_consistency": (
            "cocok" if same_hour_check else
            "perlu_diperiksa: timestamp/cakupan indeks berbeda atau data tidak lengkap"
        ),
        "sub_aqi_time": hourly_times[hour_index] if hour_index is not None else None,
        "lat": lat, "lon": lon, "sumber": sumber, "time": data.get("time", "?"),
    }, ensure_ascii=False))
else:
    print(f"{emoji} AQI {aqi} — {kat}")
    print(f"   📍 {sumber} ({lat}, {lon}) | ⏰ {data.get('time','?')}")
    print(f"   PM2.5: {data.get('pm2_5','?')} µg/m³ | PM10: {data.get('pm10','?')} µg/m³ | O3: {data.get('ozone','?')}")
    if pol:
        print(f"   🎯 Polutan tertinggi (indeks sumber): {pol_flag} (sub-AQI {pol_aqi})")
    if same_hour_check:
        print("   ✅ Konsistensi indeks: cocok pada jam yang dibandingkan")
    else:
        print("   ⚠️ Konsistensi AQI belum terkonfirmasi; periksa timestamp/cakupan indeks")
    print(f"   💡 {saran}")
