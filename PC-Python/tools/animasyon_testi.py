# -*- coding: utf-8 -*-
"""
İstemci ANİMASYONLU yürüyor mu? — canlı test.

SORUN
-----
İstemciyi 0x05 SYNC_POSITION ile taşıyoruz. O paket bir konum DÜZELTMESİ:
karakter oraya oturur, hareket durum makinesi hiç çalışmaz. Arka arkaya
gönderince karakter koşmadan SÜRÜKLENİR. Sahada görülen buydu.

ÇÖZÜM ADAYI
-----------
Başkalarının yürüyüşünü çizen paket: GC_MOVE (0x03). 23 Ağu 2026 kaydındaki
163 gerçek paketten alanları ölçüldü (tools/hareket_paketi_incele.py):

    +1  bFunc  = 0     (155/176 böyle — "hedefe yürü")
    +2  bArg   = 0     (hepsinde)
    +3  bRot   yön
    +20 dwDuration > 0   <-- ÖNEMLİ: mesafe/süre oranı hep 0.43 ham/ms

Daha önce tools/istemci_hizala.py bu paketi denemiş ve "kımıldamadı"
demişti — ama dwTime ve dwDuration'ı SIFIR gönderiyordu. Süresi sıfır olan
hareketin gidecek zamanı yok. Bu betik alanları DOĞRU doldurur.

KULLANIM
--------
    python tools/animasyon_testi.py           # 15 m yana
    python tools/animasyon_testi.py 30        # 30 m yana

ÖNCE: proxy açık ve oyuna BAĞLI, enjeksiyon açık. Karakteri elle oynatma,
ekranı izle: KOŞMA ANİMASYONU var mı, yoksa kayıyor mu?
"""

import http.client
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ADRES = "127.0.0.1:30200"
HAM_MS = 0.43            # kayıttan ölçülen istemci animasyon hızı


def adb_forward():
    for aday in ['adb',
                 os.path.expanduser(
                     r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe')]:
        try:
            subprocess.run([aday, 'forward', 'tcp:30200', 'tcp:30200'],
                           capture_output=True, timeout=10)
            return
        except Exception:
            continue


def get(yol):
    c = http.client.HTTPConnection(ADRES, timeout=4)
    c.request("GET", yol)
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def post(yol, govde):
    c = http.client.HTTPConnection(ADRES, timeout=4)
    c.request("POST", yol, body=govde.encode("utf-8"))
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def u32(v):
    return list((int(v) & 0xFFFFFFFF).to_bytes(4, "little"))


def hareket_paketi(vid, x, y, tik, sure_ms, brot=0):
    return bytes([0x03, 0, 0, brot & 0xFF]
                 + u32(vid) + u32(x) + u32(y)
                 + u32(tik) + u32(max(1, int(sure_ms))))


def senkron_paketi(vid, x, y):
    govde = u32(vid) + u32(x) + u32(y)
    boy = 3 + len(govde)
    return bytes([0x05, boy & 0xFF, (boy >> 8) & 0xFF] + govde)


def gonder(ad, paket):
    hexstr = " ".join("%02X" % b for b in paket)
    print("    %s" % hexstr)
    try:
        c = post("/api/enjekte_istemci", hexstr)
    except Exception as e:
        print("    X gönderilemedi: %s" % e)
        return False
    if not (isinstance(c, dict) and c.get("ok")):
        print("    X %s" % c)
        return False
    return True


def main():
    adb_forward()
    try:
        metre = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    except Exception:
        metre = 15

    print("=" * 70)
    print("İSTEMCİ ANİMASYON TESTİ")
    print("=" * 70)

    try:
        d = get("/api/durum")
    except Exception as e:
        print("X API'ye ulaşılamadı: %s" % e)
        input("\nEnter..."); return

    p = d.get("proxy") or {}
    if not p.get("bagli"):
        print("X Proxy oyuna BAĞLI değil.")
        input("\nEnter..."); return
    if not p.get("enjeksiyon"):
        print("X Enjeksiyon kapalı.")
        input("\nEnter..."); return

    k = get("/api/konum")
    vid = int(k.get("kendiVid", 0) or 0)
    oy = k.get("kendiVidOyu", "?")
    aday = k.get("kendiVidAday", "?")
    if not vid:
        print("X kendi vid bilinmiyor. Oyunda biraz bekle, tekrar dene.")
        input("\nEnter..."); return

    bx, by = int(k["x"]), int(k["y"])
    tik = int(d.get("tik", 0) or 0)
    print("kendi vid : %d   (%s oy, %s aday)" % (vid, oy, aday))
    print("konum     : %d, %d" % (bx, by))
    print("tik       : %d" % tik)
    if isinstance(oy, int) and oy < 3:
        print()
        print("!! UYARI: vid yalnızca %d oy aldı. Yanlış olabilir —" % oy)
        print("   test başka bir varlığı oynatabilir.")

    ham = metre * 100
    sure = int(ham / HAM_MS)
    print()
    print("-" * 70)
    print("Karakteri %d m yana götüreceğiz, iki farklı yöntemle." % metre)
    print("EKRANA BAK ve şunu ayırt et:")
    print("   ANİMASYONLU = bacaklar oynuyor, koşuyor")
    print("   SÜRÜKLENME  = duruş pozunda kayarak gidiyor")
    print("-" * 70)

    # 1) GC_MOVE — animasyon beklenen
    print()
    print(">>> 1. GC_MOVE 0x03  (bFunc=0, süre=%d ms)" % sure)
    input("    Enter'a bas...")
    if gonder("move", hareket_paketi(vid, bx + ham, by, tik, sure, 18)):
        time.sleep(sure / 1000.0 + 0.5)
        c1 = input("    KOŞMA ANİMASYONU gördün mü? (e/h): ").strip().lower()
    else:
        c1 = "h"

    # 2) geri dön, aynı yöntemle
    print()
    print(">>> 2. Aynı paketle GERİ")
    input("    Enter'a bas...")
    gonder("move-geri", hareket_paketi(vid, bx, by, tik + sure, sure, 54))
    time.sleep(sure / 1000.0 + 0.5)

    # 3) SYNC — sürüklenme beklenen (karşılaştırma)
    print()
    print(">>> 3. Karşılaştırma: 0x05 SYNC_POSITION, 10 küçük adım")
    input("    Enter'a bas...")
    for i in range(1, 11):
        gonder("sync", senkron_paketi(vid, bx + ham * i // 10, by))
        time.sleep(sure / 10000.0)
    c3 = input("    Bu sefer animasyon VAR mıydı? (e/h): ").strip().lower()

    print()
    print("=" * 70)
    if c1.startswith("e") and not c3.startswith("e"):
        print("SONUÇ: GC_MOVE (0x03) animasyonlu yürütüyor, SYNC (0x05)")
        print("       sürüklüyor. tambot'ta 'Animasyonlu (0x03)' modunu kullan.")
    elif c1.startswith("e"):
        print("SONUÇ: GC_MOVE animasyonlu. (SYNC de animasyonlu görünmüş,")
        print("       muhtemelen adımlar çok sıktı.)")
    else:
        print("SONUÇ: GC_MOVE animasyon vermedi.")
        print("  Denenecekler:")
        print("   • bFunc = 1 (kayıtta 8 pakette böyleydi)")
        print("   • dwTime alanına sunucunun GERÇEK tikini koymak")
        print("     (/api/durum -> tik alanı doğru mu?)")
        print("   • süreyi 0.43 ham/ms oranına tam uydurmak")
    print("=" * 70)
    input("\nEnter...")


if __name__ == '__main__':
    main()
