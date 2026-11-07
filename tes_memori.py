import sys, os
sys.path.insert(0, os.path.expanduser("~/mesin"))

from core.router import Router
from core.memory_manager import _normalize_perspective

try:
    router = Router()
except Exception as e:
    print(f"❌ Router() gagal: {e}")
    print("   Cek __init__ Router butuh argumen apa, paste di sini.")
    sys.exit(1)

PASS = FAIL = 0

def test_router(inp, expect_action, value_has=None, value_not_has=None):
    global PASS, FAIL
    r = router.detect_memory_action(inp)
    action = r.get("action") if r else None
    value = r.get("value", "") if r else ""

    ok = action == expect_action
    if ok and value_has:
        ok = value_has in value
    if ok and value_not_has:
        ok = value_not_has not in value

    status = "✅" if ok else "❌"
    if ok: PASS += 1
    else: FAIL += 1
    print(f"{status} [{inp}] -> {action} | value='{value}'")

def test_norm(inp, expected):
    global PASS, FAIL
    out = _normalize_perspective(inp)
    ok = out == expected
    if ok: PASS += 1
    else: FAIL += 1
    print(f"{'✅' if ok else '❌'} norm: '{inp}' -> '{out}' (harusnya '{expected}')")

print("=== ROUTER: RECALL (harus nanya, bukan nyimpen) ===")
test_router("apa yang kamu ingat", "recall")
test_router("apa yg kamu ingat", "recall")
test_router("apa yg kamu inget", "recall")
test_router("ingat ga warna kesukaan ku", "recall")
test_router("ingat nggak aku suka apa", "recall")
test_router("kamu masih ingat aku?", "recall")
test_router("siapa nama kucingku?", "recall")
test_router("apa warna favoritku?", "recall")
test_router("apa makanan kesukaanku?", "recall")

print("\n=== ROUTER: REMEMBER (harus nyimpen, buang filler) ===")
test_router("ingat warna favoritku biru", "remember", value_has="biru")
test_router("ingat yah hobi ku main catur", "remember", value_has="catur", value_not_has="yah")
test_router("ingat nih warna kesukaan ku ungu", "remember", value_has="ungu", value_not_has="nih")
test_router("ingat juga hewan peliharaan ku ikan", "remember", value_has="ikan", value_not_has="juga")
test_router("ingat nama kucingku Mochi", "remember", value_has="Mochi")
test_router("inget aku suka kopi", "remember", value_has="kopi")

print("\n=== NORMALIZE: sudut pandang + typo + spasi ===")
test_norm("warna pavoritku biru", "warna favorit pengguna biru")
test_norm("makanan kesukaan ku bakso", "makanan kesukaan pengguna bakso")
test_norm("kucingku namanya Mochi", "kucing pengguna namanya Mochi")
test_norm("aku ga suka merah", "pengguna tidak suka merah")

print(f"\n{'='*40}")
print(f"HASIL: {PASS} PASS, {FAIL} FAIL")
