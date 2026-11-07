import json
import math
import re
import subprocess
import os
import time


def hitung_matematika(ekspresi: str) -> str:
    """
    Menghitung ekspresi matematika.
    Return None jika bukan kalkulasi murni (lempar ke LLM).
    """
    kata_nalar = ["jika", "maka", "kalau", "misal",
                  "pola", "rumus", "tentukan", "buktikan"]
    if any(k in ekspresi.lower() for k in kata_nalar):
        return None

    parts = re.split(r'\bdan\b|,', ekspresi)
    if len(parts) > 1:
        hasil_list = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            h = hitung_matematika(p)
            if h is None:
                return None
            hasil_list.append(h)
        return " dan ".join(hasil_list) if hasil_list else None

    if '=' in ekspresi:
        ekspresi = ekspresi.split('=')[0]

    cleaned = ekspresi.lower().replace('x', '*').replace('×', '*')
    cleaned = re.sub(r'[^0-9+\-*/().\s]', '', cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        return None

    try:
        hasil = eval(cleaned)
        if isinstance(hasil, float) and hasil.is_integer():
            hasil = int(hasil)
        return f"{hasil}"
    except Exception:
        return None

def hitung_jarak_gps(lat1, lon1, lat2, lon2):
    """Menghitung jarak antara dua titik koordinat (Haversine Formula) dalam KM."""
    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    distance = R * c
    return round(distance, 2)


# ============================================================
# GPS / LOCATION PROVIDER
# ============================================================

_last_location_cache = None
_last_location_time = 0.0

LOCATION_CACHE_FRESH = 60
LOCATION_CACHE_MAX = 3600

TERMUX_LOCATION_PATHS = [
    'termux-location',
    '/data/data/com.termux/files/usr/bin/termux-location',
]

TERMUX_BIN = "/data/data/com.termux/files/usr/bin"

GPS_TIMEOUT = 20
NETWORK_TIMEOUT = 3

# Persistent navigation fix.
# Format:
# latitude longitude accuracy epoch
LASTFIX_FILE = os.path.expanduser("~/mesin/nav/.lastfix")


def _parse_location_output(output):
    """Parse JSON termux-location -> (lat, lon) atau None."""
    if not output or not output.strip():
        return None

    try:
        data = json.loads(output)
        lat = data.get("latitude")
        lon = data.get("longitude")

        if lat is not None and lon is not None:
            return float(lat), float(lon)
    except Exception:
        pass

    return None


def _save_location_cache(lat, lon):
    """Simpan fix baru ke RAM + .lastfix."""
    global _last_location_cache, _last_location_time

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    _last_location_cache = f"{lat},{lon} | {timestamp}"
    _last_location_time = time.time()

    # Persistent cache untuk kondisi GPS berikutnya.
    try:
        os.makedirs(os.path.dirname(LASTFIX_FILE), exist_ok=True)

        # Accuracy tidak tersedia dari pemanggil ini.
        # Pakai 0 sebagai placeholder.
        epoch = int(time.time())

        with open(LASTFIX_FILE, "w") as f:
            f.write(f"{lat} {lon} 0 {epoch}\n")

    except Exception as e:
        print(f"   ⚠️ [GPS] Gagal menyimpan .lastfix: {e}")

    return _last_location_cache


def _read_lastfix():
    """
    Baca ~/mesin/nav/.lastfix.

    Format:
        lat lon accuracy epoch

    Return:
        (lat, lon, accuracy, age_seconds)
    """
    if not os.path.exists(LASTFIX_FILE):
        return None

    try:
        with open(LASTFIX_FILE, "r") as f:
            parts = f.read().strip().split()

        if len(parts) < 4:
            return None

        lat = float(parts[0])
        lon = float(parts[1])
        accuracy = float(parts[2])
        epoch = float(parts[3])

        age = max(0, time.time() - epoch)

        return lat, lon, accuracy, age

    except Exception as e:
        print(f"   ⚠️ [GPS] .lastfix rusak: {e}")
        return None


def _get_persistent_cache():
    """Ambil fix terakhir dari .lastfix."""
    global _last_location_cache, _last_location_time

    data = _read_lastfix()

    if not data:
        return None

    lat, lon, accuracy, age = data

    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(time.time() - age)
    )

    _last_location_cache = f"{lat},{lon} | {timestamp}"
    _last_location_time = time.time() - age

    if age <= LOCATION_CACHE_FRESH:
        print(f"   📡 [GPS] Pakai .lastfix ({age:.0f} dtk)")
    elif age <= LOCATION_CACHE_MAX:
        print(f"   📡 [GPS] Pakai .lastfix lama ({age:.0f} dtk)")
    else:
        print(f"   ⚠️ [GPS] .lastfix terlalu lama ({age:.0f} dtk)")

    # Untuk navigasi, tetap boleh dikembalikan.
    # Pemanggil dapat mengetahui bahwa ini bukan fix baru
    # dari pesan debug di atas.
    return _last_location_cache


def _is_online():
    """Cek koneksi internet cepat (2 detik)."""
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except Exception:
        return False


def _call_termux_location(provider, timeout):
    """Ambil lokasi dari Termux:API."""
    termux_loc = os.path.join(TERMUX_BIN, "termux-location")

    try:
        result = subprocess.run(
            [termux_loc, "-p", provider],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return None

        return _parse_location_output(result.stdout)

    except subprocess.TimeoutExpired:
        print(f"   ⏱️ [GPS] {provider} timeout ({timeout} dtk)")
        return None

    except Exception as e:
        print(f"   ⚠️ [GPS] {provider} gagal: {e}")
        return None


def get_current_location():
    """
    Strategi GPS offline-first:

        RAM cache (< 60 dtk) -> instan
          v
        GPS satelit (20 dtk)
          v
        .lastfix (instan, berapa pun umurnya)
          v
        Network (3 dtk, hanya kalau online)
          v
        gagal
    """

    # 1. RAM cache - instan
    if _last_location_cache and (time.time() - _last_location_time) < LOCATION_CACHE_FRESH:
        print("   📡 [GPS] Pakai RAM cache")
        return _last_location_cache

    # 2. GPS satelit - timeout panjang untuk cold fix
    pos = _call_termux_location("gps", GPS_TIMEOUT)

    if pos:
        lat, lon = pos
        return _save_location_cache(lat, lon)

    # 3. .lastfix - instan, sebelum buang waktu di network
    cached = _get_persistent_cache()

    if cached:
        return cached

    # 4. Network - hanya kalau online
    if _is_online():
        pos = _call_termux_location("network", NETWORK_TIMEOUT)
        if pos:
            lat, lon = pos
            return _save_location_cache(lat, lon)
    else:
        print("   📴 [GPS] Offline - network dilewati")

    return "Gagal mengambil data dari sensor."


# ============================================================
# FORWARD GEOCODING: nama tempat -> koordinat
# ============================================================

def _nominatim_search(query):
    """Satu kali pencarian ke Nominatim. Return (lat, lon, display_name)."""
    import urllib.request
    import urllib.parse
    import json

    try:
        encoded = urllib.parse.quote_plus(query)
        url = (
            f"https://nominatim.openstreetmap.org/search"
            f"?q={encoded}&format=json&limit=1&accept-language=id"
        )

        req = urllib.request.Request(url, headers={'User-Agent': 'MesinAI/1.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())

        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon, data[0].get('display_name', query)
        return None, None, None
    except Exception:
        return None, None, None


def _photon_search(query):
    """
    Satu kali pencarian ke Photon (komoot).
    ⚠️ PENTING: Photon return GeoJSON, coordinates = [LON, LAT] (terbalik!)
    Return (lat, lon, name) agar konsisten dengan Nominatim.
    """
    import urllib.request
    import urllib.parse
    import json

    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://photon.komoot.io/api/?q={encoded}&limit=1&lang=id"

        req = urllib.request.Request(url, headers={'User-Agent': 'MesinAI/1.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())

        features = data.get("features", [])
        if features:
            # ⚠️ Photon: coordinates = [lon, lat] — TERBALIK dari Nominatim!
            coords = features[0].get("geometry", {}).get("coordinates", [])
            if len(coords) == 2:
                lon = coords[0]  # Photon kasih LON dulu
                lat = coords[1]  # lalu LAT

                props = features[0].get("properties", {})
                name_parts = []
                if props.get("name"):
                    name_parts.append(props["name"])
                if props.get("city"):
                    name_parts.append(props["city"])
                if props.get("state"):
                    name_parts.append(props["state"])
                display_name = ", ".join(name_parts) if name_parts else query

                return lat, lon, display_name
        return None, None, None
    except Exception:
        return None, None, None


def cari_koordinat_tempat(nama_tempat):
    """
    Mencari koordinat via Photon dulu (lebih cepat, tanpa rate limit),
    fallback ke Nominatim dengan multi-strategi.
    """

    PREFIX_INSTITUSI = [
        "smpit", "sdit", "smait", "smp", "sma", "smk", "sd", "mi", "mts", "ma",
        "tk", "paud", "kb", "pesantren", "pondok", "universitas", "institut",
        "sekolah", "kampus", "masjid", "gereja", "vihara", "pura",
        "rs", "rumah sakit", "puskesmas", "klinik",
        "mall", "pasar", "stasiun", "terminal", "bandara",
    ]

    # Strategi 1: Photon dulu (cepat, tanpa rate limit)
    lat, lon, name = _photon_search(nama_tempat)
    if lat is not None:
        return lat, lon, name

    # Strategi 2: Nominatim query asli
    lat, lon, name = _nominatim_search(nama_tempat)
    if lat is not None:
        return lat, lon, name

    time.sleep(1.1)

    # Strategi 3: Hapus prefix institusi
    cleaned = nama_tempat.lower().strip()
    for prefix in PREFIX_INSTITUSI:
        if cleaned.startswith(prefix + " "):
            cleaned = cleaned[len(prefix):].strip()
            break

    if cleaned != nama_tempat.lower().strip():
        print(f"   🔄 [Geocoder] Retry tanpa prefix: '{cleaned}'")
        lat, lon, name = _nominatim_search(cleaned)
        if lat is not None:
            return lat, lon, name
        time.sleep(1.1)

    # Strategi 4: Hapus kata pertama
    words = nama_tempat.split()
    if len(words) > 2:
        fallback_query = " ".join(words[1:])
        print(f"   🔄 [Geocoder] Retry tanpa kata pertama: '{fallback_query}'")
        lat, lon, name = _nominatim_search(fallback_query)
        if lat is not None:
            return lat, lon, name

    return None, None, None


# ============================================================
# REVERSE GEOCODING: koordinat -> nama daerah
# ============================================================

def _nominatim_reverse(lat, lon):
    """
    Reverse geocoding via Nominatim.
    Nominatim pakai: ?lat=...&lon=...
    Return nama daerah atau None.
    """
    import urllib.request
    import json

    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json&accept-language=id&zoom=18"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'MesinAI/1.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())

        # Ambil bagian yang paling informatif
        address = data.get("address", {})
        parts = []
        if address.get("suburb") or address.get("neighbourhood"):
            parts.append(address.get("suburb") or address.get("neighbourhood"))
        if address.get("city") or address.get("town") or address.get("village"):
            parts.append(address.get("city") or address.get("town") or address.get("village"))
        if address.get("state"):
            parts.append(address.get("state"))

        if parts:
            return ", ".join(parts)

        # Fallback: pakai display_name
        display = data.get("display_name", "")
        if display:
            # Ambil 3 bagian pertama saja biar tidak kepanjangan
            return ", ".join(display.split(",")[:3]).strip()

        return None
    except Exception:
        return None


def _photon_reverse(lat, lon):
    """
    Reverse geocoding via Photon.
    ⚠️ Photon reverse pakai: ?lon=...&lat=... (lon dulu di URL!)
    Return nama daerah atau None.
    """
    import urllib.request
    import json

    try:
        # ⚠️ Photon: parameter URL-nya lon dulu, baru lat
        url = f"https://photon.komoot.io/reverse?lon={lon}&lat={lat}"

        req = urllib.request.Request(url, headers={'User-Agent': 'MesinAI/1.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())

        features = data.get("features", [])
        if features:
            props = features[0].get("properties", {})
            parts = []
            if props.get("name"):
                parts.append(props["name"])
            if props.get("street"):
                parts.append(props["street"])
            if props.get("city"):
                parts.append(props["city"])
            if props.get("state"):
                parts.append(props["state"])

            if parts:
                return ", ".join(parts)
        return None
    except Exception:
        return None


def cari_nama_daerah(lat, lon):
    """
    Reverse geocoding gabungan: Photon dulu, fallback Nominatim.
    Return string nama daerah atau pesan gagal.
    """
    # Coba Photon dulu (cepat, tanpa rate limit)
    print(f"   🌍 [Reverse Geo] Photon: lat={lat}, lon={lon}")
    nama = _photon_reverse(lat, lon)
    if nama:
        return nama

    # Fallback Nominatim
    print(f"   🌍 [Reverse Geo] Fallback Nominatim...")
    time.sleep(1.1)  # Rate limit Nominatim
    nama = _nominatim_reverse(lat, lon)
    if nama:
        return nama

    return None


def hitung_bearing(lat1, lon1, lat2, lon2):
    """Return (derajat, arah 8 penjuru)."""
    dlon = math.radians(lon2 - lon1)
    la1, la2 = math.radians(lat1), math.radians(lat2)
    y = math.sin(dlon) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlon)
    b = (math.degrees(math.atan2(y, x)) + 360) % 360
    arah = ['utara','timur laut','timur','tenggara','selatan','barat daya','barat','barat laut']
    return round(b), arah[int((b + 22.5) / 45) % 8]


def fmt_jarak(km):
    """Format jarak: <1 km jadi meter."""
    if km < 1:
        return f"{round(km * 1000)} m"
    return f"{km:.1f} km"

# ============================================================
# TOTAL PERJALANAN / TRACKING JARAK
# ============================================================

TRIP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nav")
TRIP_TOTAL_PATH = os.path.join(TRIP_DIR, ".trip_total")
TRIP_LAST_PATH = os.path.join(TRIP_DIR, ".trip_last")

os.makedirs(TRIP_DIR, exist_ok=True)


def _load_trip_total():
    try:
        with open(TRIP_TOTAL_PATH, "r") as f:
            return float(f.read().strip())
    except Exception:
        return 0.0


def _save_trip_total(total):
    try:
        tmp = TRIP_TOTAL_PATH + ".tmp"
        with open(tmp, "w") as f:
            f.write(f"{total:.6f}")
        os.replace(tmp, TRIP_TOTAL_PATH)
    except Exception as e:
        print(f"   ⚠️ [TRIP] Gagal menyimpan total: {e}")


def _load_trip_last():
    try:
        with open(TRIP_LAST_PATH, "r") as f:
            data = f.read().strip().split()
            if len(data) >= 2:
                return float(data[0]), float(data[1])
    except Exception:
        pass
    return None


def _save_trip_last(lat, lon):
    try:
        tmp = TRIP_LAST_PATH + ".tmp"
        with open(tmp, "w") as f:
            f.write(f"{lat:.8f} {lon:.8f}")
        os.replace(tmp, TRIP_LAST_PATH)
    except Exception as e:
        print(f"   ⚠️ [TRIP] Gagal menyimpan posisi: {e}")


def update_total_perjalanan(lat, lon):
    last = _load_trip_last()
    total = _load_trip_total()

    if last is None:
        _save_trip_last(lat, lon)
        return total, 0.0

    last_lat, last_lon = last

    delta = hitung_jarak_gps(
        last_lat,
        last_lon,
        lat,
        lon
    )

    # Abaikan lonjakan GPS > 1 km
    if delta > 1.0:
        print(f"   ⚠️ [TRIP] GPS jump diabaikan: {delta:.2f} km")
        _save_trip_last(lat, lon)
        return total, 0.0

    total += delta

    _save_trip_last(lat, lon)
    _save_trip_total(total)

    return total, delta


def get_total_perjalanan():
    """Baca total perjalanan tanpa mengubah state."""
    total = _load_trip_total()
    return f"🛣️ Total perjalanan: {total:.2f} km"


def hitung_total_perjalanan():
    """Kompatibilitas lama: baca total saja, TIDAK update GPS."""
    return get_total_perjalanan()


def reset_total_perjalanan():
    try:
        _save_trip_total(0.0)

        if os.path.exists(TRIP_LAST_PATH):
            os.remove(TRIP_LAST_PATH)

        return "🔄 Total perjalanan di-reset ke 0 km."

    except Exception as e:
        return f"Gagal reset perjalanan: {e}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: kalkulator.py <eval|haversine|update|total|reset|lokasi|daerah> [args...]")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "eval":
        expr = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(hitung_matematika(expr))
    elif cmd == "haversine":
        if len(sys.argv) >= 6:
            l1, o1, l2, o2 = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
            jarak = hitung_jarak_gps(l1, o1, l2, o2)
            print(f"{jarak:.3f} km")
        else:
            print("Error: haversine butuh 4 argumen (lat1 lon1 lat2 lon2)")
    elif cmd == "update":
        if len(sys.argv) >= 4:
            lat, lon = float(sys.argv[2]), float(sys.argv[3])
            total, delta = update_total_perjalanan(lat, lon)
            print(f"total={total:.3f} km, delta={delta:.3f} km")
        else:
            print("Error: update butuh lat dan lon")
    elif cmd == "total":
        print(get_total_perjalanan())
    elif cmd == "reset":
        print(reset_total_perjalanan())
    elif cmd in ("lokasi", "loc"):
        loc = get_current_location()
        print(json.dumps(loc, ensure_ascii=False) if loc else "Tidak ada lokasi")
    elif cmd == "daerah":
        if len(sys.argv) >= 4:
            print(cari_nama_daerah(float(sys.argv[2]), float(sys.argv[3])))
        else:
            print("Error: daerah butuh lat dan lon")
    else:
        # Default: hitung ekspresi matematika langsung
        expr = " ".join(sys.argv[1:])
        print(hitung_matematika(expr))


