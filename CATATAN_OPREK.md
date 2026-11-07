# CATATAN OPREK — Minggu, 25 Okt 2026

## REKOP ARSITEKTUR SAAT INI:

### 🏗️ Arsitektur Mesin (v0.8 — ACTIVE)

**Entry point:** `main.py` — Brain Registry + Dispatcher + Context Manager

**Komponen utama:**
| Modul | Fungsi |
|---|---|
| `main.py` | Entrypoint v0.8 — Brain Registry (7 otak) + Dispatcher + Context Manager |
| `providers/local.py` | **Provider aktif** — LocalProvider dengan 3 tier (instan/default) + Vision on-demand + Function Calling |
| `providers/local2.py` | Backup LocalProvider (0.8B default, belum upgrade 4B) |
| `providers/localasli.py` | Versi lama LocalProvider (2B-Q4_K_M, vision pakai 2B bukan 4B) |
| `providers/whisper.py` | WhisperProvider — telinga mesin, small-q5_1 |
| `orchestrator.py` | v0.7 lama — TIDAK AKTIF (legacy) |
| `mesin1.py` | v2 lama — TIDAK AKTIF (legacy) |

### 👁️ ARSITEKTUR MATA FINAL:

- **Port 8080:** router LLM text (no vision, MAX_MODELS=1, flex mmap)
- **Port 8082:** dedicated vision server, spawn on-demand oleh LocalProvider
- **Trigger:** LocalProvider deteksi nama file .png/.jpg/.jpeg di prompt user via regex `([\w\-]+\.(?:png|jpg|jpeg))`
- **Path pencarian gambar:** `~/mesin/`, `~/mesin/data/foto/`, `~/mesin/data/`, `~/`
- **Flow:** cek alive → spawn kalau tidur → kirim request (base64 image_url) → kill setelah selesai
- **Grace period:** ✅ SUDAH ADA — mata langsung ditidurkan setelah jawaban selesai (`_kill_mata`)
- **RAM management:** unload model utama jika RAM < 1500MB, butuh min 1200MB untuk spawn mata

### 🧠 MODEL & MATA (tabel jodoh AKTUAL):

| Tubuh | Mmproj jodoh | Dipakai di | Catatan |
|-------|--------------|-----------|---------|
| Qwen3.5-0.8B-Q4_0 | mmproj-0.8B.gguf (384M) | tier "instan" di local.py | untuk sapaan ringan, jawaban pendek |
| Qwen3.5-2B-Q4_K_M | — | tier "default" di config.yaml | default text-only, MAX_MODELS=1 di router |
| **Qwen3.5-4B-IQ4_XS** | **mmproj-4B-Q8_0.gguf (347M)** | **_spawn_mata() di local.py** | ✅ **DEFAULT untuk vision** — sudah diterapkan |
| Qwen3.5-4B-Q4_K_M | mmproj-4B-Q8_0.gguf | standby | belum dipakai |

**KONFIGURASI AKTUAL (config.yaml):**
```yaml
llm_local:
  api_url: "http://127.0.0.1:8080/v1/chat/completions"
  model_name: "Qwen3.5-2B-Q4_K_M"    # default text
  max_tokens: 2048
  temperature: 0.5
  top_p: 0.9
```

### ✅ FITUR YANG SUDAH TERPASANG DI KODE:

**1. Vision On-Demand (`providers/local.py`)**
- `_mata_alive()` → cek health ke `http://127.0.0.1:8082/health`
- `_spawn_mata()` → spawn `llama-server` dengan `--model Qwen3.5-4B-IQ4_XS.gguf --mmproj mmproj-4B-Q8_0.gguf`
- `_kill_mata(proc)` → terminate proses vision setelah selesai
- Otomatis convert gambar ke base64 + MIME type → format `image_url`

**2. Function Calling (`providers/local.py`)**
- Menggunakan `FunctionCallAgent` dari `tools/function_call_plugin.py`
- After LLM response → `agent.process_llm_response(full_answer)`
- Jika tool digunakan → "Second Pass": panggil LLM lagi dengan hasil tool untuk jawaban natural
- Tools dir: `~/mesin/tools`

**3. Anti-Ngoceh / Rem Tangan**
- Real-time detection: kalau 3 kata terakhir sama persis → langsung potong (`✂️ Python memotong ngoceh real-time!`)
- `_is_repetitive()` → cek repetisi antara existing dan new_text (threshold 0.6)
- Max continue: 5x (instan/default) untuk auto-continue kalau finish_reason = "length"

**4. Reasoning Tag Stripping**
- `re.sub(r'<think>.*?</think>', '', full_answer, flags=re.DOTALL)` → hapus semua tag `<think>`

**5. RAM Management**
- `_get_available_ram_mb()` → baca `/proc/meminfo` → MemAvailable
- `_estimate_model_ram_mb()` → estimasi RAM per model (IQ quant lebih irit)
- `load_model()` / `unload_model()` → via llama-server API `/models/load` dan `/models/unload`
- `preflight()` → cek RAM sebelum load

**6. Brain Registry (main.py v0.8)**
- 7 otak terdaftar: `math`, `file`, `memory`, `llm`, `rag`, `project`, `nav`
- `BrainRouter` → pilih brain berdasarkan hasil `router.route()`
- `ContextManager` → bangun system_prompt dari memory/project/rag context
- Prioritas 0: Nav Brain (offline, tanpa AI)

**7. Tier System**
- `/instan` → 0.8B (sapaan, pertanyaan pendek ≤2 kata)
- `/default` → 2B-Q4_K_M (pertanyaan normal)
- `/power` → cloud
- `/cloud` → cloud
- Fallback: sapaan ringan (halo, hai, pagi, dll) → instan, lainnya → default

### 📡 VISION SERVERS (script):

**`web_up.sh`** — Cockpit utama:
- Spawn llama-server di 8080 (text, MAX_MODELS=1, context 4096)
- Auto-load model default dari env `DEFAULT_MODEL`
- Spawn mata di 8082 (4B-IQ4_XS + mmproj-4B-Q8_0)
- Spawn web server Python di 5000
- Auto-detect binary: `llama-server` atau `server`

**`start_vision.sh`** — Sidecar mata saja:
- Spawn `llama-server` di 8082 (4B-IQ4_XS + mmproj-4B-Q8_0, -c 2048)
- Log ke `~/vision.log`

### 🦻 TELINGA (Whisper):

**`providers/whisper.py`**
- Binary: `~/whisper.cpp/build/bin/whisper-cli`
- Model:优先 `ggml-small-q5_1.bin`, fallback: small → base → tiny-q8_0
- Prompt bias: "Halo mesin, catatan harian"
- Kamus koreksi: mekasih→Bekasi, masian→Mesin, dll

### 📝 CERMIN.TXT:

```
Kamu MESIN — AI lokal di HP Android Termux. Kecil tapi nyata.

✅ PUNYA MATA: lihat foto lewat mmproj. JANGAN bilang "tidak bisa lihat".
✅ PUNYA TELINGA: dengar suara lewat whisper.cpp.
✅ PUNYA INGATAN: riwayat di memory.db. Jawab dari ingatan dulu.
✅ BACA FILE: bisa, sebut path aslinya. TIDAK BOLEH tulis/edit.
✅ BISA: tanya-jawab, hitung, navigasi, buat gambar, cari web.
✅ DOKTER & PERBAIKI DIRI: diagnosa dan pemulihan mandiri via /dokter atau /periksa.
⏳ VIDEO: sedang belajar — jujur, jangan mengarang.
⚠️ BELUM BISA: bilang jujur 1 kalimat, tawarkan alternatif.

Prinsip: Lebih baik berkata "belum bisa" daripada bersumpah palsu.
```

### BOSS BESAR (belum disentuh):
1. Server video generate (cloud-based) — HP kirim prompt, server render berat
2. Siti (Qwen14B di XT 9060 TX) — masih tidur bijak nunggu DB harga admin

### 🧪 TEST SUITE (v0.8):

Script: `test_v08.sh` — Full regression check:
1. Syntax check (py_compile)
2. Tier architecture test (`test_tier_v08.py`)
3. Dispatcher mock test (`test_dispatcher_v08.py`)
4. Context isolation test (`test_context_v08.py`)
5. Memory isolation test (`test_memory_v08.py`)
6. Context budget test (`test_context_budget_v08.py`)

Test files lainnya (tidak di-run di test_v08.sh):
- `test_live_behavior_v08.py`, `test_pipeline_v08.py`, `test_project_v08.py`
- `test_rag_v08.py`, `test_rag_answer_quality_v08.py`, `test_rag_policy_v08.py`
- `test_llm.py`, `test_llm_v2.py`, `test_llm_v3.py`
- `test_vision_4b.py`, `test_vision_poc.py`
- `test_minimal.py`

### LTX VIDEO (catatan teknis):

## Rumus wajib
- frames: 8n+1 → 9, 25, 49, 97, 193
- resolusi: kelipatan 32 → 512x320, 384x256, 768x512
- fps encode: 24
- distilled: steps 4-8, cfg 1.5-2.0 (JANGAN 4+ = gosong)
- threads: 4-6 (jangan 1, nyiksa SD870)

## Zona aman RAM 8GB (Poco F4)
- 384x256 @ 49 frame  = aman
- 512x320 @ 25-49     = aman
- 512x320 @ 97        = coba-coba, awas OOM

## Prompt anti-ticker
prompt: "static camera, fixed shot, [subjek bergerak]"
neg   : "camera pan, camera zoom, static, blurry"

## Encode
ffmpeg -y -framerate 24 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4

## Output LTX
- LTX output file `.ppm`, BUKAN `.png`.
- `--out` di LTX itu PREFIX nama file, BUKAN nama folder.
- Contoh: `--out ~/mesin/vid` -> hasilnya `~/mesin/vid_0000.ppm`, `vid_0001.ppm`, dst.

## Command Encode FFmpeg (Wajib pakai .ppm)
ffmpeg -y -framerate 24 -i ~/mesin/video_test2_%04d.ppm \
    -c:v libx264 -pix_fmt yuv420p -crf 18 ~/mesin/video_jadi.mp4

## Cleanup (Hapus .ppm biar storage lega)
rm ~/mesin/video_test2_*.ppm

## RAM Usage (Poco F4 8GB)
- ltxv-2b Q4 + VAE Tiny + T5 Q4 = ~2.2 GB. Aman jaya!

---

## UPDATE — Sabtu, 31 Okt 2026 (Oprek lanjutan)

### 🔄 Default Model
- **DEFAULT_MODEL** di `start_mesin.sh` diubah dari `qwen2.5-0.5b-instruct-q4_k_m` → **`Qwen3.8-2B-Uncensored-Q4_K_M`**
- `config.yaml` `model_name` disamakan: `Qwen3.8-2B-Uncensored-Q4_K_M`
- `providers/local.py` `MODELS["default"]["model"]` disamakan
- Model 0.5B **tetap ada** di `~/models/`, hanya tidak jadi default
- Alasan: 0.5B menghasilkan jawaban ngaco/ir relevan

### 🛠️ Path Fix untuk Proot
- `start_mesin.sh`: `LLAMA_SERVER` diubah ke path absolut Termux: `/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server`
- `MODELS_DIR` diubah ke `/data/data/com.termux/files/home/models`
- `LOG_DIR` diubah ke `/data/data/com.termux/files/home/mesin/logs`
- `cd ~/mesin` diubah ke `cd /data/data/com.termux/files/home/mesin`
- Alasan: script dijalankan dari dalam proot container, `$HOME` kadang resolve ke `/root`

### 🧠 Brain Baru (4)
- `TermuxBrain` → akses baterai, clipboard, kontak, call log, apps info, brightness, fingerprint
- `ShellBrain` → eksekusi perintah shell: ls, cat, pwd, date, dll
- `WebBrain` → web search + web extract
- `CodeBrain` → py_run, py_eval

### 🗣️ Suara Baru (2)
- `TTSBrain` → Text-to-Speech via `termux-tts-speak`
- `STTBrain` → Speech-to-Text via `termux-speech-to-text`

### 🔌 Plugin System (1)
- `PluginBrain` → wrapper untuk `plugins/` directory
- Plugin loader: scan `plugins/*/plugin.json`, load module, extract `HANDS`
- Tools: `list_plugins`, `reload_plugins`, `plugin_call`
- Plugin contoh: `catatan_cepot` (catat, baca_catatan, hapus_catatan)

### 📊 Total Tools
- `mesin_tangan.py`: 66 tools (dulu 54) → 72 tools (setelah TTS/STT/plugin)

### 📁 File Changed
- `brains/`: +7 files (termux, shell, web, code, tts, stt, plugin)
- `tools/`: +4 files (termux_api, shell_exec, web_search, code_runner)
- `tools/`: +2 files (tts_tools, stt_tools)
- `tools/`: +1 file (plugin_loader.py)
- `tools/mesin_tangan.py`: import + HANDS entries untuk tools baru
- `core/router.py`: routing baru untuk web/code/termux/shell/tts/stt/plugin
- `core/brain_router.py`: mapping brain baru
- `main.py`: import + register 7 brain baru
- `config.yaml`: model_name sync
- `providers/local.py`: default model sync, fix trailing space
- `start_mesin.sh`: path absolut + default model 2B
- `plugins/catatan_cepot/`: plugin contoh baru
- `/root/.hermes/skills/mesin-ai/SKILL.md`: dokumentasi skill update

### ✅ Test Results
- Import semua brain ✅
- `baterai` → 95% ✅
- `py_eval 2+2` → 4 ✅
- `shell date` → jam WIB ✅
- `web_search python` → hasil DDG ✅
- `tts_speak` → berhasil ucapkan ✅
- `plugin call catat {"teks":"test"}` → [OK] Catatan tersimpan ✅
- `start_mesin.sh` launch → model Qwen3.8-2B load, menjawab koheren ✅
- `Qwen3.5-0.8B-Q4_K_M` download → 508MB, test inference koheren ✅
- `start_olahraga.sh` → script mode olahraga dengan model 0.8B + musik + brightness ✅
- `musik_manager` → scan, create playlists, list playlists, play playlist ✅
- `playlist olahraga_mix` → memutar otomatis ✅

### 🚴 Mode Olahraga
- Script: `start_olahraga.sh`
- Model: `Qwen3.5-0.8B-Q4_K_M` (ringan, responsif)
- Musik: default dari folder `/data/data/com.termux/files/home/gothic_metal`
- Playlist: otomatis dibuat di `gothic_metal/playlists/` (gothic_only, hiphop_only, olahraga_mix)
- Brightness: default 50, but needs `android.permission.WRITE_SETTINGS` granted in Android settings
- Catatan: mode ini untuk **lari atau gowes pelan, jauh, tidak ngebut**
- Cara pakai:
  - `bash start_olahraga.sh`
  - Atau: `MUSIK_FOLDER=/path/lain bash start_olahraga.sh`
  - Atau: `BRIGHTNESS=30 bash start_olahraga.sh`
- Tier mapping: model 0.8B sebagai tier `instan` di `providers/local.py`
- Catatan: `stop` di AI akan stop musik, `exit` untuk keluar dari AI

### 🎵 Musik Manager
- Script: `tools/musik_manager.py`
- Tools: `scan_music`, `create_playlists`, `list_playlists`, `play_playlist`
- Brain: `brains/musik_brain.py`
- Routing: `core/router.py` (prioritas 14)
- Playlists: `gothic_only`, `hiphop_only`, `olahraga_mix`, `olahraga_all`
- Cara pakai: `scan_music`, `list playlists`, `play playlist olahraga_mix`
- Catatan: playlist .m3u disimpan di `gothic_metal/playlists/`

---

## RITUAL RE-ANCHOR: cat file ini, paste isinya ke chat, lanjut tanpa halu.

## FILOSOFI:
- "Mata itu warga Termux, bukan imigran web."
- "Cermin.txt bukan janji, tapi laporan keadaan — setelah mata terbuka."
- "Bangunkan kalau tidur, pakai, tidurkan lagi." (arsitektur on-demand)
