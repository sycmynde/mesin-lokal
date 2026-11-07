import os, sys

SERVER = os.path.expanduser("~/mesin/web/server.py")
INDEX  = os.path.expanduser("~/mesin/web/index.html")

FOTO_BLOCK = '''        elif self.path == "/foto":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            kamera = str(data.get("kamera", "0"))
            if kamera not in ("0", "1"):
                kamera = "0"

            import subprocess, base64, time as _t
            foto_dir = os.path.expanduser("~/mesin/data")
            os.makedirs(foto_dir, exist_ok=True)
            foto_path = os.path.join(foto_dir, "foto_%d.jpg" % int(_t.time()))

            error = ""
            try:
                proc = subprocess.run(
                    ["termux-camera-photo", "-c", kamera, foto_path],
                    capture_output=True, text=True, timeout=25
                )
                if proc.returncode != 0:
                    error = "termux-camera-photo exit %d: %s" % (proc.returncode, proc.stderr.strip())
            except subprocess.TimeoutExpired:
                error = "Kamera timeout - cek izin aplikasi Termux:API"
            except FileNotFoundError:
                error = "termux-camera-photo tidak ditemukan di PATH"

            if not error:
                for _ in range(10):
                    if os.path.exists(foto_path) and os.path.getsize(foto_path) > 1000:
                        break
                    _t.sleep(0.3)
                else:
                    error = "Foto tidak tersimpan / file kosong"

            if error:
                response = {"ok": False, "error": error}
            else:
                with open(foto_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                response = {
                    "ok": True,
                    "image": "data:image/jpeg;base64," + b64,
                    "file": os.path.basename(foto_path),
                    "size": os.path.getsize(foto_path)
                }
                try:
                    files = sorted(
                        [os.path.join(foto_dir, fn) for fn in os.listdir(foto_dir) if fn.startswith("foto_")],
                        key=os.path.getmtime
                    )
                    for old in files[:-5]:
                        os.remove(old)
                except Exception:
                    pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

'''

JS_BLOCK = '''
<div id="kameraBar" style="position:fixed;top:8px;right:8px;z-index:9999">
  <button id="btnKamera" onclick="jepretKamera('0')" style="font-size:20px">📷</button>
  <button onclick="jepretKamera('1')" style="font-size:20px">🤳</button>
</div>
<script>
function tampilkanFotoJawaban(answer){
  if (typeof tambahPesan === "function") { tambahPesan("assistant", answer); return; }
  if (typeof addMessage === "function") { addMessage("assistant", answer); return; }
  var box = document.getElementById("chat") || document.getElementById("chatBox") || document.querySelector(".chat, #messages");
  if (box){
    var d = document.createElement("div");
    d.textContent = "🤖 " + answer;
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
    return;
  }
  alert(answer);
}
async function jepretKamera(kamera){
  var btn = document.getElementById("btnKamera");
  btn.textContent = "⏳";
  try {
    var res = await fetch("/foto", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({kamera: kamera})
    });
    var data = await res.json();
    if (!data.ok){ alert("❌ " + data.error); return; }
    var res2 = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: "", image: data.image})
    });
    var hasil = await res2.json();
    tampilkanFotoJawaban(hasil.answer);
  } catch(e){
    alert("❌ Gagal: " + e);
  }
  btn.textContent = "📷";
}
</script>
'''

# ---- Patch server.py ----
src = open(SERVER).read()
if '"/foto"' in src:
    print("⏭️  server.py sudah punya /foto - skip")
else:
    anchor = '        elif self.path == "/clear":'
    if anchor not in src:
        sys.exit("❌ ANCHOR /clear tidak ditemukan di server.py - jangan lanjut, cek manual")
    src = src.replace(anchor, FOTO_BLOCK + anchor, 1)
    open(SERVER, "w").write(src)
    print("✅ server.py dipatch - endpoint /foto ditambahkan")

# ---- Patch index.html ----
html = open(INDEX).read()
if "jepretKamera" in html:
    print("⏭️  index.html sudah punya tombol kamera - skip")
else:
    if "</body>" in html:
        html = html.replace("</body>", JS_BLOCK + "\n</body>", 1)
    else:
        html = html + JS_BLOCK
    open(INDEX, "w").write(html)
    print("✅ index.html dipatch - tombol 📷 🤳 ditambahkan")

print("🎉 Patch selesai")
