from tools.kalkulator import hitung_matematika, hitung_jarak_gps, get_current_location, cari_koordinat_tempat, cari_nama_daerah, hitung_bearing, fmt_jarak, hitung_total_perjalanan, reset_total_perjalanan, reset_total_perjalanan
import re
import os
import subprocess


class MathBrain:

    def _clean_target(self, text):
        """Bersihkan target lokasi dari kata tanya dan sampah."""
        text = re.sub(r'\b(berapa|km|kilometer|ya|yah|kah|sih|dong|jarak|dari|sini|saya|aku|ke|tolog|tolong)\b', '', text)
        text = text.replace('?', '').replace('!', '').replace('.', '').strip()
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_my_location(self):
        """Ambil GPS sendiri, return (lat, lon) atau None."""
        my_loc = get_current_location()
        if not my_loc or "Gagal" in str(my_loc) or "Error" in str(my_loc):
            return None
        try:
            coord_part = my_loc.split("|")[0].strip()
            lat, lon = map(float, coord_part.split(","))
            return lat, lon
        except Exception:
            return None

    def run(self, data):
        text = data.get("text", "").lower()

        # ============================================================
        # TOTAL PERJALANAN
        # ============================================================
        total_intent = [
            "total perjalanan",
            "hitung total perjalanan",
            "berapa total perjalanan",
            "jarak total perjalanan",
            "total jarak perjalanan",
            "sudah berapa km perjalanan",
            "sudah berapa kilometer perjalanan",
        ]

        if any(k in text for k in total_intent):
            return hitung_total_perjalanan()


        # ============================================================
        # TOTAL PERJALANAN
        # ============================================================
        reset_trip = [
            "reset perjalanan",
            "reset total perjalanan",
            "hapus total perjalanan",
            "nolkan perjalanan",
        ]

        if any(k in text for k in reset_trip):
            return reset_total_perjalanan()

        trip_query = [
            "total perjalanan",
            "hitung total perjalanan",
            "berapa total perjalanan",
            "jarak total perjalanan",
            "total jarak perjalanan",
            "sudah berapa km perjalanan",
            "sudah berapa kilometer perjalanan",
        ]

        if any(k in text for k in trip_query):
            return hitung_total_perjalanan()

        # ============================================================
        # 0. TRIP TRACKER
        # ============================================================
        trip_control = os.path.expanduser("~/mesin/tools/trip_control.sh")

        if any(k in text for k in [
            "mulai perjalanan", "mulai trip", "start perjalanan", "start trip"
        ]):
            try:
                result = subprocess.run(
                    [trip_control, "start"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip() or "⚠️ Gagal memulai Trip Tracker."
            except Exception as e:
                return f"⚠️ Gagal memulai Trip Tracker: {e}"

        if any(k in text for k in [
            "stop perjalanan", "stop trip",
            "berhenti perjalanan", "selesai perjalanan"
        ]):
            try:
                result = subprocess.run(
                    [trip_control, "stop"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip() or "⚠️ Gagal menghentikan Trip Tracker."
            except Exception as e:
                return f"⚠️ Gagal menghentikan Trip Tracker: {e}"

        if any(k in text for k in [
            "status perjalanan", "status trip"
        ]):
            try:
                result = subprocess.run(
                    [trip_control, "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip() or "⚪ Status Trip Tracker tidak diketahui."
            except Exception as e:
                return f"⚠️ Gagal membaca status perjalanan: {e}"

        if any(k in text for k in [
            "reset perjalanan", "reset trip"
        ]):
            try:
                return reset_total_perjalanan()
            except Exception as e:
                return f"⚠️ Gagal reset perjalanan: {e}"

        if any(k in text for k in [
            "total perjalanan",
            "hitung total perjalanan",
            "berapa total perjalanan",
            "jarak total perjalanan",
            "total jarak perjalanan",
            "sudah berapa km perjalanan",
            "sudah berapa kilometer perjalanan"
        ]):
            return hitung_total_perjalanan()

        # ============================================================
        # 0. NAV STATE: jangkar, tujuan, status (eks nav_brain)
        # ============================================================
        nav_dir = os.path.expanduser("~/mesin/nav")
        origin_file = os.path.join(nav_dir, ".origin")
        tujuan_file = os.path.join(nav_dir, ".tujuan")

        if "jangkar" in text:
            my_pos = self._get_my_location()
            if not my_pos:
                return "⚠️ GPS belum fix. Coba lagi di tempat terbuka."
            lat, lon = my_pos
            os.makedirs(nav_dir, exist_ok=True)
            with open(origin_file, "w") as f:
                f.write(f"{lat} {lon} jangkar\n")
            return f"⚓ Jangkar dipasang: {lat:.5f}, {lon:.5f}"

        if text.startswith("tujuan") or text.startswith("set tujuan"):
            # Cek koordinat manual dulu (misal: tujuan -6.31, 106.96)
            coord_match = re.search(r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)', text)
            if coord_match:
                lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
                os.makedirs(nav_dir, exist_ok=True)
                with open(tujuan_file, "w") as f:
                    f.write(f"{lat} {lon} manual\n")
                return f"🎯 Tujuan diset (manual): {lat}, {lon}"
            # Tidak ada koordinat → pakai GPS sekarang
            my_pos = self._get_my_location()
            if not my_pos:
                return "⚠️ GPS belum fix. Coba lagi di tempat terbuka."
            lat, lon = my_pos
            label = text.replace("set tujuan", "").replace("tujuan", "").strip() or "di sini"
            os.makedirs(nav_dir, exist_ok=True)
            with open(tujuan_file, "w") as f:
                f.write(f"{lat} {lon} {label}\n")
            return f"🎯 Tujuan diset: {label} ({lat:.5f}, {lon:.5f})"

        if "status nav" in text or "status navigasi" in text:
            lines = ["── STATUS NAV ──"]
            for lbl, path in [("⚓ Origin", origin_file), ("🎯 Tujuan", tujuan_file)]:
                if os.path.exists(path):
                    with open(path) as f:
                        lines.append(f"{lbl}: {f.read().strip()}")
                else:
                    lines.append(f"{lbl}: belum diset")
            return "\n".join(lines)

        # ============================================================
        # 0b. JARAK NAV STATE: jarak ke tujuan / titik awal
        # ============================================================
        _j_tujuan = any(k in text for k in ["jarak tujuan", "jarak ke tujuan", "ke tujuan", "berapa jauh lagi", "sisa berapa"])
        _j_origin = any(k in text for k in ["titik awal", "dari awal"])
        if _j_tujuan or _j_origin:
            is_tujuan = _j_tujuan
            target_file = tujuan_file if is_tujuan else origin_file
            label = "tujuan" if is_tujuan else "titik awal"

            if not os.path.exists(target_file):
                saran = "tujuan" if is_tujuan else "jangkar"
                return f"⚠️ {label.capitalize()} belum diset. Ketik '{saran}' dulu."

            my_pos = self._get_my_location()
            if not my_pos:
                return "⚠️ GPS belum fix. Coba lagi di tempat terbuka."
            lat1, lon1 = my_pos

            try:
                with open(target_file) as f:
                    parts = f.read().strip().split()
                lat2, lon2 = float(parts[0]), float(parts[1])
            except Exception:
                return f"⚠️ File {label} rusak. Set ulang dulu."

            km = hitung_jarak_gps(lat1, lon1, lat2, lon2)
            deg, arah = hitung_bearing(lat1, lon1, lat2, lon2)
            return f"📏 Jarak ke {label}: {fmt_jarak(km)} ke arah {arah} ({deg}°)"

        # ============================================================
        # 1. LOKASI: Reverse geocoding DULU (lebih spesifik)
        # ============================================================
        # Reset waypoint lokasi
        if text.strip() in ("reset lokasi", "reset jarak", "hapus waypoint"):
            _wp = os.path.join(os.path.expanduser("~/mesin/nav"), ".waypoints")
            if os.path.exists(_wp):
                os.remove(_wp)
            return "🔄 Waypoint lokasi di-reset. Ketik 'lokasi' untuk mulai lagi."

        reverse_intent = [
            "di daerah mana", "daerah mana", "di mana ini", "ini di mana",
            "nama tempat", "nama daerah", "saya di daerah", "aku di daerah",
            "lokasi ini di mana", "ini daerah apa", "di mana saya",
            "dimana saya", "di mana aku", "dimana aku", "aku di mana",
            "saya di mana", "lagi di mana", "sedang di mana",
            "di mana sekarang", "dimana sekarang", "posisi saya",
            "posisi aku", "lokasi saya", "lokasi aku", "saya ada di",
            "aku ada di", "di sini", "disini", "di sini di mana",
            "lokasi",
        ]

        if any(k in text for k in reverse_intent):
            my_pos = self._get_my_location()
            if not my_pos:
                return "Maaf, GPS tidak tersedia. Pastikan Termux:API terpasang dan izin lokasi aktif."
            lat, lon = my_pos

            # --- Waypoint tracking ---
            _wp_dir = os.path.expanduser("~/mesin/nav")
            _wp_file = os.path.join(_wp_dir, ".waypoints")
            os.makedirs(_wp_dir, exist_ok=True)

            _prev = None
            _total_km = 0.0
            _num_points = 0

            if os.path.exists(_wp_file):
                try:
                    with open(_wp_file) as _f:
                        _lines = [l.strip() for l in _f if l.strip()]
                    if _lines:
                        _last = _lines[-1].split()
                        _prev = (float(_last[0]), float(_last[1]))
                        _num_points = len(_lines)
                        for _i in range(1, len(_lines)):
                            _a = _lines[_i - 1].split()
                            _b = _lines[_i].split()
                            _total_km += hitung_jarak_gps(
                                float(_a[0]), float(_a[1]),
                                float(_b[0]), float(_b[1]))
                except Exception:
                    pass

            _seg_km = 0.0
            if _prev:
                _seg_km = hitung_jarak_gps(_prev[0], _prev[1], lat, lon)
                _total_km += _seg_km

            with open(_wp_file, "a") as _f:
                _f.write(f"{lat} {lon}\n")

            # --- Reverse geocoding ---
            print(f"   🌍 [MathBrain] Reverse geocoding: {lat}, {lon}")
            nama_daerah = cari_nama_daerah(lat, lon)

            # --- Output ---
            if not _prev:
                _wp_info = "\n🛣️ Titik awal tercatat."
            else:
                _wp_info = f"\n🛣️ Segmen: {fmt_jarak(_seg_km)} | Total: {fmt_jarak(_total_km)} ({_num_points + 1} titik)"

            if nama_daerah:
                return f"📍 Kamu sedang berada di sekitar **{nama_daerah}**\n(Koordinat: {lat:.5f}, {lon:.5f}){_wp_info}"
            else:
                return f"📍 Koordinatmu: {lat:.5f}, {lon:.5f}\nTapi maaf, saya tidak bisa menerjemahkannya ke nama daerah. Coba lagi nanti.{_wp_info}"

        # ============================================================
        # 2. GPS murni (hanya kalau eksplisit minta koordinat)
        # ============================================================
        pure_gps = ["gps", "koordinat"]
        if any(k in text for k in pure_gps):
            loc_data = get_current_location()
            if loc_data and "Gagal" not in str(loc_data) and "Error" not in str(loc_data):
                return f"📍 {loc_data}"
            return "Maaf, GPS tidak tersedia saat ini. Pastikan Termux:API terpasang dan izin lokasi aktif."

        # ============================================================
        # 3. Perbandingan jarak
        # ============================================================
        compare_match = re.search(r'lebih (dekat|jauh) ke (.+?) atau ke (.+)', text)
        if not compare_match:
            compare_match = re.search(r'(dekat|jauh) mana.*ke (.+?) atau (.+)', text)

        if compare_match:
            my_pos = self._get_my_location()
            if not my_pos:
                return "Maaf, saya tidak bisa mendeteksi lokasi Anda saat ini."

            lat1, lon1 = my_pos
            place_a = self._clean_target(compare_match.group(2))
            place_b = self._clean_target(compare_match.group(3))

            lat_a, lon_a, name_a = cari_koordinat_tempat(place_a)
            lat_b, lon_b, name_b = cari_koordinat_tempat(place_b)

            if not lat_a or not lat_b:
                gagal = []
                if not lat_a: gagal.append(place_a)
                if not lat_b: gagal.append(place_b)
                return f"Maaf, saya tidak menemukan lokasi: {', '.join(gagal)}. Coba nama yang lebih umum."

            dist_a = hitung_jarak_gps(lat1, lon1, lat_a, lon_a)
            dist_b = hitung_jarak_gps(lat1, lon1, lat_b, lon_b)

            if float(dist_a) < float(dist_b):
                return f"📍 **{name_a}** lebih dekat ({dist_a} km) dibanding **{name_b}** ({dist_b} km)."
            else:
                return f"📍 **{name_b}** lebih dekat ({dist_b} km) dibanding **{name_a}** ({dist_a} km)."

        # ============================================================
        # 4. Jarak biasa
        # ============================================================
        if "jarak" in text and ("ke" in text or "dari" in text):
            my_pos = self._get_my_location()
            if not my_pos:
                return "Maaf, saya tidak bisa mendeteksi lokasi Anda saat ini. Pastikan GPS aktif."

            lat1, lon1 = my_pos

            if "ke" in text:
                target = text.split("ke", 1)[-1].strip()
            else:
                target = text.split("dari", 1)[-1].strip()

            target = self._clean_target(target)

            if not target:
                return "Mau hitung jarak ke mana? Sebutkan nama tempatnya ya."

            print(f"🔍 [MathBrain] Mencari koordinat: '{target}'...")
            lat2, lon2, place_name = cari_koordinat_tempat(target)

            if lat2 and lon2:
                distance = hitung_jarak_gps(lat1, lon1, lat2, lon2)
                return f"Jarak dari sini ke **{place_name}** adalah sekitar **{distance} km**."
            else:
                return f"Saya tidak menemukan '{target}' di peta. Coba nama yang lebih umum atau tambahkan nama kota."

        # ============================================================
        # 5. Matematika biasa (dengan cermin)
        # ============================================================
        hasil = hitung_matematika(data.get("text", ""))
        if hasil is None:
            return None  # dispatcher harus tangkap → route ke LLM
        return hasil
