"""
Mode Lari - Hands-free assistant untuk lari / olahraga.
Terpisah dari main.py agar modular dan tidak mengganggu alur sistem utama.
"""
import os
import re
import sys
import time
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

console = Console()

def _bersihkan_lisan(teks):
    """
    Membersihkan tag, formatting markdown, dan emoji dari teks
    agar ucapan TTS alami dan tidak membaca simbol kode.
    """
    if not teks:
        return ""
    t = re.sub(r"\[(PEMBUKA|INTI|DETAIL|KESIMPULAN|PENUTUP|SISTEM|CATATAN)\]", "", teks, flags=re.I)
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`.*?`", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[#*_>|~]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Batasi maksimal 2-3 kalimat pertama agar tidak kepanjangan saat lari
    parts = re.split(r"(?<=[.!?])\s+", t)
    return " ".join(parts[:2]).strip()

def bicara(teks):
    """
    Mengucapkan teks menggunakan termux-tts-speak dalam bahasa Indonesia.
    Aman dari error dan timeout.
    """
    t = _bersihkan_lisan(teks)
    if not t:
        return

    ringkas = t[:45] + ("..." if len(t) > 45 else "")
    console.print(f"[yellow]🔊 Mengucapkan: {ringkas}[/yellow]")
    
    try:
        res = subprocess.run(
            ["termux-tts-speak", "-l", "id", t],
            capture_output=True,
            text=True,
            timeout=20
        )
        if res.returncode != 0 and res.stderr:
            console.print(f"[dim red]⚠️ TTS warning: {res.stderr.strip()}[/dim red]")
    except FileNotFoundError:
        console.print("[dim red]⚠️ termux-tts-speak tidak ditemukan. Pastikan Termux:API terpasang.[/dim red]")
    except subprocess.TimeoutExpired:
        console.print("[dim red]⚠️ TTS timeout.[/dim red]")
    except Exception as e:
        console.print(f"[dim red]⚠️ TTS error: {e}[/dim red]")

def run_lari_mode(registry, session):
    """
    Loop utama mode lari hands-free:
    dengar -> transkrip -> eksekusi aksi / LLM -> TTS -> ulang
    """
    from providers.whisper import whisper_provider

    console.print(Panel(
        "[bold green]🏃 MODE LARI AKTIF[/bold green]\n"
        "• Bilang [yellow]cukup / stop / berhenti[/yellow] untuk keluar.\n"
        "• Bilang [cyan]jam berapa / jarak / aqi / putar musik[/cyan] untuk kontrol instan.\n"
        "• Pertanyaan lain akan dijawab singkat oleh asisten lari.",
        border_style="green"
    ))

    bicara("Mode lari aktif. Katakan stop atau cukup kapan saja untuk selesai.")

    # Daftar filter halusinasi audio kosong Whisper
    halusinasi_mic = [
        "terima kasih kerana menonton",
        "terima kasih telah menonton",
        "terima kasih sudah menonton",
        "selamat menonton",
        "jangan lupa subscribe",
        "terima kasih banyak",
        "terima kasih",
        "subtitles by",
        "diterjemahkan oleh",
        "see you next time",
        "thank you for watching",
        "bye bye",
        "sampai jumpa"
    ]

    stop_words_exact = {"cukup", "sudah", "udah", "stop", "berhenti", "selesai", "keluar"}
    stop_phrases = (
        "udah dulu", "sudah dulu", "stop lari", "cukup dulu",
        "selesai lari", "keluar mode lari", "matikan mode lari",
        "berhenti lari", "udahan dulu"
    )

    rekam_script = os.path.expanduser("~/mesin/tools/rekam_vad.py")

    try:
        while True:
            console.print("\n[cyan]🎧 Mendengarkan...[/cyan]")
            
            # 1. Rekam suara via VAD
            wav_path = None
            try:
                result = subprocess.run(
                    ["python3", rekam_script],
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                wav_path = result.stdout.strip()
            except subprocess.TimeoutExpired:
                console.print("[dim]⏱️ Waktu dengar habis, mencoba lagi...[/dim]")
                continue
            except Exception as e:
                console.print(f"[red]❌ Error rekam: {e}[/red]")
                time.sleep(1)
                continue

            # Jika tidak ada suara terdeteksi dalam jendela waktu
            if not wav_path or not os.path.exists(wav_path):
                continue

            # 2. Transkripsi dengan Whisper
            try:
                teks = whisper_provider.transcribe(wav_path)
            except Exception as e:
                console.print(f"[dim red]⚠️ Gagal transkripsi: {e}[/dim red]")
                teks = None
            finally:
                # Bersihkan file rekaman audio sementara agar memori HP tidak penuh
                if wav_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except Exception:
                        pass

            if not teks or not teks.strip():
                continue

            teks_bersih = teks.strip()
            low = teks_bersih.lower()

            # Normalisasi tanda baca untuk pencocokan perintah yang akurat
            clean_cmd = re.sub(r"[^\w\s]", "", low).strip()

            console.print(f"[bold cyan]🗣️ Anda:[/bold cyan] {teks_bersih}")

            # ── 1. CEK PERINTAH STOP ──
            if clean_cmd in stop_words_exact or any(phrase in clean_cmd for phrase in stop_phrases):
                bicara("Oke, mode lari selesai. Istirahat yang cukup dan tetap semangat, Bro!")
                console.print("[yellow]🏁 Mode lari selesai.[/yellow]")
                break

            # ── 2. CEK WAKTU / JAM ──
            if any(w in clean_cmd for w in ["jam berapa", "pukul berapa", "waktu sekarang", "sekarang jam", "cek jam", "cek waktu"]):
                now = datetime.now()
                menit_str = f"lewat {now.minute} menit" if now.minute > 0 else "tepat"
                bicara(f"Sekarang jam {now.hour} {menit_str}.")
                continue

            # ── 3. CEK JARAK / TRACKING ──
            if any(w in clean_cmd for w in ["jarak", "berapa km", "berapa kilo", "total perjalanan", "jarak tempuh", "sudah jalan berapa"]):
                try:
                    from tools.kalkulator import _load_trip_total
                    total = _load_trip_total()
                    if total > 0.01:
                        total_text = f"{total:.2f}".replace(".", " koma ")
                        bicara(f"Total jarak perjalanan saat ini {total_text} kilometer.")
                    else:
                        bicara("Jarak tempuh saat ini masih di bawah 0 koma 1 kilometer.")
                except Exception:
                    bicara("Belum ada data jarak perjalanan yang tercatat.")
                continue

            # ── 4. CEK AQI / KUALITAS UDARA ──
            if any(w in clean_cmd for w in ["aqi", "kualitas udara", "polusi", "kondisi udara", "cuaca udara"]):
                try:
                    from tools.aqi_checker import cek_aqi_lokal
                    data_aqi = cek_aqi_lokal()
                    if data_aqi and str(data_aqi.get("aqi", "?")) != "?":
                        aqi_val = data_aqi.get("aqi")
                        kategori = data_aqi.get("kategori", "")
                        saran = data_aqi.get("saran", "")
                        bicara(f"AQI saat ini {aqi_val}, kategori {kategori}. {saran}")
                    else:
                        bicara("Gagal mengambil data kualitas udara saat ini.")
                except Exception as e:
                    bicara("Gagal memeriksa kualitas udara.")
                continue

            # ── 4b. CEK JURNAL / CATAT ──
            if any(w in clean_cmd for w in ["catat", "jurnal", "ingat"]):
                try:
                    from core.memory_manager import add_memory
                    import datetime as _dt
                    add_memory("jurnal", _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), teks_bersih)
                    console.print("[green]📓 Tercatat.[/green]")
                    bicara("Tercatat.")
                except Exception:
                    bicara("Gagal mencatat.")
                continue

            # ── 5. KONTROL MUSIK (CMUS DENGAN FALLBACK FFPLAY) ──
            musik_keywords = (
                "putar musik", "mainkan lagu", "putar lagu", "mainkan musik",
                "next", "pause", "jeda", "prev", "stop musik", "shuffle",
                "ganti lagu", "lagu berikutnya", "lagu"
            )
            if any(w in clean_cmd for w in musik_keywords):
                try:
                    from tools.dj_cmus import play_gothic_metal as cmus_play, cmus_control
                    
                    if "next" in clean_cmd or "ganti lagu" in clean_cmd or "lagu berikutnya" in clean_cmd:
                        res = cmus_control("next")
                        bicara("Lagu berikutnya.")
                    elif "pause" in clean_cmd or "jeda" in clean_cmd:
                        res = cmus_control("pause")
                        bicara("Musik dijeda.")
                    elif "prev" in clean_cmd or "lagu sebelumnya" in clean_cmd:
                        res = cmus_control("prev")
                        bicara("Kembali ke lagu sebelumnya.")
                    elif "stop musik" in clean_cmd or "matikan lagu" in clean_cmd:
                        res = cmus_control("stop")
                        bicara("Musik dihentikan.")
                    elif "shuffle" in clean_cmd or "acak lagu" in clean_cmd:
                        res = cmus_control("shuffle")
                        bicara("Mode acak lagu diaktifkan.")
                    else:
                        # Putar lagu baru dengan keyword jika ada
                        clean_keyword = clean_cmd
                        for prefix in ["putar musik", "mainkan lagu", "putar lagu", "mainkan musik", "musik", "lagu"]:
                            clean_keyword = clean_keyword.replace(prefix, "")
                        clean_keyword = clean_keyword.strip()

                        hasil_cmus = cmus_play(keyword=clean_keyword if clean_keyword else None)
                        if "belum aktif" in hasil_cmus:
                            # Fallback ke ffplay jika cmus belum dinyalakan
                            from tools.dj_offline import play_gothic_metal as ffplay_play
                            hasil_ffplay = ffplay_play(keyword=clean_keyword if clean_keyword else None)
                            if "Memutar" in hasil_ffplay:
                                bicara(f"Memutar musik {clean_keyword if clean_keyword else ''}.")
                            else:
                                bicara("Folder musik masih kosong.")
                        elif "tidak ditemukan" in hasil_cmus:
                            bicara(f"Lagu {clean_keyword} tidak ditemukan.")
                        elif "kosong" in hasil_cmus:
                            bicara("Folder musik masih kosong.")
                        else:
                            bicara("Oke, memutar musik.")
                except Exception as e:
                    bicara(f"Gagal memutar musik: {e}")
                continue

            # ── 6. CEK LOKASI SAAT INI ──
            if any(w in clean_cmd for w in ["lokasi saya", "di mana saya", "dimana saya", "posisi sekarang", "posisi saya", "lagi dimana"]):
                try:
                    from tools.kalkulator import get_current_location, cari_nama_daerah
                    loc = get_current_location()
                    if loc and "latitude" in loc and "longitude" in loc:
                        lat, lon = float(loc["latitude"]), float(loc["longitude"])
                        nama = cari_nama_daerah(lat, lon)
                        if nama and not nama.startswith("Error"):
                            bicara(f"Kamu sedang berada di sekitar {nama}.")
                        else:
                            bicara(f"Posisi koordinat saat ini di {lat:.3f}, {lon:.3f}.")
                    else:
                        bicara("Sinyal lokasi belum terkunci.")
                except Exception:
                    bicara("Belum dapat menentukan lokasi saat ini.")
                continue

            # ── 7. ASISTEN & TEMAN LARI (LLM) ──
            try:
                session.add("user", teks_bersih)
                recent_messages = session.get_messages()[-6:]

                answer = registry.execute(
                    "llm",
                    {
                        "messages": recent_messages,
                        "system_prompt": (
                            "Kamu adalah asisten dan teman lari cerdas yang menemani pengguna berolahraga. "
                            "Jawab santai, ramah, memotivasi, dan sangat ringkas (maksimal 1 kalimat). "

                            "Jangan menggunakan format markdown, tanda bintang, atau bullet points karena "
                            "jawabanmu akan dibacakan langsung lewat audio suara."
                        ),
                        "rag_context": ""
                    }
                )

                if answer:
                    console.print(f"[green]💬 Asisten:[/green] {answer}")
                    bicara(answer)
                    session.add("assistant", answer)

            except Exception as e:
                console.print(f"[red]❌ Error asisten: {e}[/red]")
                bicara("Maaf, terjadi gangguan saat memproses ucapanmu.")

    except KeyboardInterrupt:
        bicara("Mode lari dihentikan. Sampai jumpa!")
        console.print("\n[yellow]🏁 Mode lari dihentikan pengguna.[/yellow]")
