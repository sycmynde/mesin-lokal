import os, sys

SERVER = os.path.expanduser("~/mesin/web/server.py")
src = open(SERVER).read()

if "def kecilkan_bytes" in src:
    print("⏭️  sudah dipatch - skip"); sys.exit(0)

HELPERS = '''
def kecilkan_bytes(raw, max_sisi=800, kualitas=70):
    """Kecilkan JPEG di memori: PIL dulu, fallback ffmpeg. Kembalikan (bytes, ok)."""
    try:
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(raw))
        if im.width > max_sisi or im.height > max_sisi:
            im.thumbnail((max_sisi, max_sisi))
        if im.mode != "RGB":
            im = im.convert("RGB")
        buf = _io.BytesIO()
        im.save(buf, "JPEG", quality=kualitas)
        return buf.getvalue(), True
    except Exception:
        pass
    try:
        import subprocess as _sp, tempfile as _tf
        fin = _tf.NamedTemporaryFile(suffix=".jpg", delete=False)
        fin.write(raw); fin.close()
        fout = fin.name + ".kecil.jpg"
        vf = "scale=w='min(%d,iw)':h='min(%d,ih)':force_original_aspect_ratio=decrease" % (max_sisi, max_sisi)
        _sp.run(["ffmpeg", "-y", "-i", fin.name, "-vf", vf, "-q:v", "6", fout],
                capture_output=True, timeout=30, check=True)
        out = open(fout, "rb").read()
        os.remove(fin.name); os.remove(fout)
        return out, True
    except Exception:
        return raw, False


def kecilkan_dataurl(dataurl, max_sisi=800, kualitas=70):
    try:
        head, b64 = dataurl.split(",", 1)
        if "base64" not in head:
            return dataurl
        import base64 as _b64
        kecil, ok = kecilkan_bytes(_b64.b64decode(b64), max_sisi, kualitas)
        if not ok:
            return dataurl
        return "data:image/jpeg;base64," + _b64.b64encode(kecil).decode()
    except Exception:
        return dataurl

'''

anchor_h = 'HTML_DIR = os.path.dirname(os.path.abspath(__file__))'
if anchor_h not in src:
    sys.exit("❌ anchor HTML_DIR tidak ketemu")
src = src.replace(anchor_h, anchor_h + "\n" + HELPERS, 1)

anchor_c = '            image = data.get("image", "")\n            if image:\n                import urllib.request'
if anchor_c not in src:
    sys.exit("❌ anchor /chat image tidak ketemu")
src = src.replace(anchor_c,
    '            image = data.get("image", "")\n            if image:\n                image = kecilkan_dataurl(image)\n                import urllib.request', 1)

anchor_f = '                with open(foto_path, "rb") as f:\n                    b64 = base64.b64encode(f.read()).decode("ascii")'
if anchor_f not in src:
    sys.exit("❌ anchor /foto b64 tidak ketemu")
src = src.replace(anchor_f,
    '                with open(foto_path, "rb") as f:\n                    raw_foto = f.read()\n                raw_foto, _okk = kecilkan_bytes(raw_foto)\n                with open(foto_path, "wb") as f:\n                    f.write(raw_foto)\n                b64 = base64.b64encode(raw_foto).decode("ascii")', 1)

open(SERVER, "w").write(src)
print("✅ server.py dipatch: foto dikompres maks 800px q70 sebelum dikirim")

try:
    import PIL
    print("🔧 Backend kompresi: Pillow", PIL.__version__)
except Exception:
    import shutil
    if shutil.which("ffmpeg"):
        print("🔧 Backend kompresi: ffmpeg (opsional lebih cepat: pkg install -y python-pillow)")
    else:
        print("⚠️  Pillow & ffmpeg tidak ada! Jalankan dulu: pkg install -y python-pillow")
