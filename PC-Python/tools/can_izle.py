# -*- coding: utf-8 -*-
"""
Hedeflerin CANINI canlı izler — saldırı sunucuya işliyor mu?

Bot çalışırken bunu ayrı bir pencerede çalıştır. Her varlığın canını takip
eder ve DEĞİŞTİĞİ anı yazar. Can düşüyorsa saldırı işliyor, düşmüyorsa
sunucu saymıyor demektir.

Neden gerekli: bot'un logu "saldırdım" der ama bu yalnızca paketin
gönderildiğini gösterir. Sunucunun onu SAYIP saymadığı ancak canın
düşmesinden anlaşılır.

Kullanım:
    python tools/can_izle.py            # 60 saniye izle
    python tools/can_izle.py 180        # 180 saniye izle
"""

import http.client
import json
import sys
import time
import subprocess
import os

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


def main():
    sure = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    adb_forward()
    conn = http.client.HTTPConnection(ADRES, timeout=2)

    def get(yol):
        conn.request("GET", yol, headers={"Connection": "keep-alive"})
        return json.loads(conn.getresponse().read().decode("utf-8", "replace"))

    print("=" * 70)
    print("CAN İZLEME — %d saniye" % sure)
    print("=" * 70)
    print("Bot'u ŞİMDİ başlat. Can düşerse saldırı işliyor demektir.\n")

    onceki = {}          # vid -> can
    ilk_gorulme = {}     # vid -> (ad, ilk can, ilk zaman)
    dusus = 0
    olum = 0
    t0 = time.time()

    try:
        while time.time() - t0 < sure:
            try:
                varliklar = get("/api/varliklar?n=60")
            except Exception as e:
                print("  API hatası: %s" % type(e).__name__)
                time.sleep(1)
                continue
            if not isinstance(varliklar, list):
                time.sleep(0.2)
                continue

            simdiki = {}
            for v in varliklar:
                vid = v.get("vid")
                can = v.get("can", -1)
                ad = v.get("ad", "?")
                simdiki[vid] = can
                if can < 0:
                    continue
                if vid not in ilk_gorulme:
                    ilk_gorulme[vid] = (ad, can, time.time())
                eski = onceki.get(vid)
                if eski is not None and eski >= 0 and can != eski:
                    t = time.time() - t0
                    ok = "DÜŞTÜ" if can < eski else "arttı"
                    if can < eski:
                        dusus += 1
                    print("  t=%5.1fs  %-26s  %3d%% → %3d%%   %s"
                          % (t, ad[:26], eski, can, ok))
                    if can == 0:
                        olum += 1
                        print("  t=%5.1fs  %-26s  ÖLDÜ" % (t, ad[:26]))
            # listeden düşenler = öldü ya da uzaklaştı
            for vid, can in onceki.items():
                if vid in simdiki:
                    continue
                ad = ilk_gorulme.get(vid, ("?", 0, 0))[0]
                if can >= 0:
                    print("  t=%5.1fs  %-26s  listeden düştü (can %d%% iken)"
                          % (time.time() - t0, ad[:26], can))
            onceki = simdiki
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n  (durduruldu)")

    print("\n" + "=" * 70)
    print("SONUÇ")
    print("=" * 70)
    canli = [(a, c) for a, c, _ in ilk_gorulme.values()]
    print("  can bilgisi görülen varlık : %d" % len(ilk_gorulme))
    print("  can DÜŞÜŞÜ sayısı          : %d" % dusus)
    print("  can 0'a inen (ölen)        : %d" % olum)
    print()
    if dusus == 0:
        print("  >>> HİÇ CAN DÜŞMEDİ.")
        print("      Saldırı paketleri gidiyor ama sunucu SAYMIYOR.")
        print("      Olası sebepler:")
        print("        • saldırı hızı sınırı (bot çok hızlı vuruyor)")
        print("        • sunucu mesafe denetimi (ışınlanmayı kabul etmiyor)")
        print("        • saldırı paketinde eksik/yanlış alan")
    elif olum == 0:
        print("  >>> Can düşüyor ama hiçbir şey ölmedi.")
        print("      Saldırı İŞLİYOR, sadece yavaş. Vuruş aralığını")
        print("      düşürmeyi ya da yetenek kullanmayı dene.")
    else:
        print("  >>> ÇALIŞIYOR: can düşüyor ve hedefler ölüyor.")


if __name__ == '__main__':
    main()
