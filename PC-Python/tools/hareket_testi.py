# -*- coding: utf-8 -*-
"""
Sunucu ENJEKTE EDİLEN hareketi kabul ediyor mu? Bağımsız ölçüm.

NEDEN BAĞIMSIZ ÖLÇÜM GEREKİYOR
------------------------------
/api/konum'a bakmak YETMEZ. Panel, bizim gönderdiğimiz konumu da
gösterebiliyor; yani "gittim" demesi sunucunun kabul ettiği anlamına
gelmiyor.

Güvenilir sinyal ÇEVREDİR: sunucu bizi gerçekten taşırsa yeni bölgedeki
varlıklar için CHARACTER_ADD (0x01) gönderir, geride kalanlar için
CHARACTER_DEL (0x02). Çevre değişmiyorsa taşınmamışızdır.

29 Ağu 2026'da 150 m'lik ışınlanma böyle ölçüldü: 7 saniye boyunca
çevredeki 45 varlığın hiçbiri değişmedi → sunucu ışınlanmayı yok sayıyor.
Bu betik aynı ölçümü İSTEDİĞİN MESAFEDE tekrarlar.

KULLANIM
--------
    python tools/hareket_testi.py            # 30 m dener
    python tools/hareket_testi.py 10         # 10 m dener
    python tools/hareket_testi.py 10 30 80   # sırayla dener

ÖNCE: uygulamada proxy açık ve oyuna BAĞLI olmalı, enjeksiyon açık,
kanal Proxy. Karakteri elle oynatma.
"""

import http.client
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

ADRES = "127.0.0.1:30200"


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
    c = http.client.HTTPConnection(ADRES, timeout=3)
    c.request("GET", yol)
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def post(yol, govde):
    c = http.client.HTTPConnection(ADRES, timeout=3)
    c.request("POST", yol, body=govde.encode("utf-8"))
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def u32(v):
    return list((int(v) & 0xFFFFFFFF).to_bytes(4, "little"))


def dene(metre, bekle=10):
    d = get("/api/durum")
    p = d.get("proxy") or {}
    if not p.get("bagli"):
        print("  X proxy oyuna BAĞLI değil — enjeksiyon imkânsız.")
        return None
    if not p.get("enjeksiyon"):
        print("  X enjeksiyon kapalı.")
        return None

    k = get("/api/konum")
    bx, by = k["x"], k["y"]
    once = {m["vid"] for m in get("/api/varliklar?n=80")}

    print("\n--- %d metre denemesi ---" % metre)
    print("  başlangıç: %d,%d   çevre: %d varlık" % (bx, by, len(once)))

    hx = bx + metre * 100          # 1 m = 100 ham birim
    hy = by
    tik = d.get("tik", 0)
    paket = bytes([0x07, 1, 0, 0] + u32(hx) + u32(hy) + u32(tik))
    c = post("/api/enjekte", " ".join("%02X" % b for b in paket))
    if not (isinstance(c, dict) and c.get("ok")):
        print("  X gönderilemedi: %s" % c)
        return None

    for i in range(bekle):
        time.sleep(1.0)
        sonra = {m["vid"] for m in get("/api/varliklar?n=80")}
        print("    t=%2ds  çevre %2d  yeni %2d  kaybolan %2d"
              % (i + 1, len(sonra), len(sonra - once), len(once - sonra)))

    sonra = {m["vid"] for m in get("/api/varliklar?n=80")}
    yeni = len(sonra - once)
    if yeni >= 4:
        print("  >>> KABUL EDİLDİ (%d yeni varlık) — sunucu bizi taşıdı." % yeni)
        return True
    print("  >>> KABUL EDİLMEDİ (%d yeni varlık) — çevre aynı kaldı." % yeni)
    return False


def main():
    adb_forward()
    mesafeler = [int(a) for a in sys.argv[1:] if a.isdigit()] or [30]
    print("=" * 66)
    print("ENJEKTE EDİLEN HAREKET TESTİ")
    print("=" * 66)
    print("Karakteri ELLE OYNATMA — istemcinin kendi paketi sonucu bozar.")

    sonuc = {}
    for m in mesafeler:
        sonuc[m] = dene(m)
        time.sleep(2)

    print("\n" + "=" * 66)
    print("ÖZET")
    print("=" * 66)
    for m, s in sonuc.items():
        durum = "kabul edildi" if s else ("KABUL EDİLMEDİ" if s is False else "ölçülemedi")
        print("  %3d m : %s" % (m, durum))
    kabul = [m for m, s in sonuc.items() if s]
    if kabul:
        print("\n  En büyük kabul edilen mesafe: %d m" % max(kabul))
        print("  Bot bu mesafenin ALTINDA adımlarla yol alabilir.")
    else:
        print("\n  Hiçbir mesafe kabul edilmedi.")
        print("  Enjekte edilen hareket bu sunucuda çalışmıyor;")
        print("  karakteri elle götürmek gerekir.")


if __name__ == '__main__':
    main()
