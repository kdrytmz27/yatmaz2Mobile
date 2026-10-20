# -*- coding: utf-8 -*-
"""
WH TEŞHİSİ — sunucu saldırıyı ne kadar uzaktan kabul ediyor?

NEDEN
-----
Wait-hack "ışınlan-vur-dön" olarak kurulmuştu ve bu sunucuda çalışmıyor:
sunucu hareketi kabul ediyor ama IŞINLAMIYOR, yürüterek götürüyor.
Arayüzdeki uyarı bunu söylüyor.

Ama asıl işe yarar soru bu değil. Işınlanma olmasa bile sunucunun
saldırı mesafe denetimi cömertse, hiç kımıldamadan uzaktakine vurmak
mümkün olur — WH'den beklenen şey zaten buydu.

Bu araç onu ÖLÇÜYOR: hareket paketi olmadan, bulunduğumuz yerden
artan mesafelerdeki canavarlara vurup hangi mesafede canın düştüğüne
bakıyor.

KONTROL DENEYİ
--------------
Ölçümün bir şey ölçtüğünü kanıtlamak için en yakın hedefe de vuruluyor.
Orada can düşmüyorsa sorun mesafede değil, kurulumda demektir
(enjeksiyon kapalı, yanlış vid, ölü hedef) — ve araç bunu söyler.

KULLANIM
    python tools/wh_teshis.py
    python tools/wh_teshis.py --vurus 5     (hedef başına vuruş)
"""
from __future__ import print_function

import argparse
import json
import sys
import time

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
except ImportError:                                     # py2
    from urllib2 import urlopen, Request                # noqa
    from urllib import urlencode                        # noqa

API = "127.0.0.1:30200"
TIP_MOB = 0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def api(yol, **p):
    u = "http://%s%s" % (API, yol)
    if p:
        u += "?" + urlencode(p)
    try:
        return json.loads(urlopen(u, timeout=5).read()
                          .decode("utf-8-sig", "replace"))
    except Exception as e:
        print("   API hata (%s): %s" % (yol, e))
        return None


def enjekte(baytlar):
    h = " ".join("%02X" % b for b in baytlar)
    try:
        r = Request("http://%s/api/enjekte" % API,
                    data=h.encode("utf-8"), method="POST")
        urlopen(r, timeout=5).read()
        return True
    except Exception as e:
        print("   enjekte hata: %s" % e)
        return False


def u32(v):
    return [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]


def paket_hedef(vid):
    return [0x3D] + u32(vid)


def paket_saldiri(vid):
    return [0x02, 0x00] + u32(vid)


def paket_toplu_konum(vid, x, y):
    govde = u32(vid) + u32(x & 0xFFFFFFFF) + u32(y & 0xFFFFFFFF)
    boy = 3 + len(govde)
    return [0x08, boy & 0xFF, (boy >> 8) & 0xFF] + govde


def varliklar():
    v = api("/api/varliklar", n=60)
    return v if isinstance(v, list) else []


def canavar(vid):
    for v in varliklar():
        if v.get("vid") == vid:
            return v
    return None


def vur(vid, x, y, adet, aralik=0.25):
    """Hareket paketi YOK — bulunduğumuz yerden vuruyoruz."""
    for _ in range(adet):
        enjekte(paket_hedef(vid) + paket_saldiri(vid)
                + paket_toplu_konum(vid, x, y))
        time.sleep(aralik)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vurus", type=int, default=4)
    a = ap.parse_args()

    print("=" * 76)
    print("WH TEŞHİSİ — sunucunun saldırı menzili")
    print("=" * 76)

    d = api("/api/durum")
    if not d:
        raise SystemExit("API'ye erişilemiyor. adb forward tcp:30200 tcp:30200")
    p = d.get("proxy") or {}
    print("enjeksiyon: %s" % p.get("enjeksiyon"))
    if not p.get("enjeksiyon"):
        raise SystemExit("Enjeksiyon KAPALI — bu deney paket gönderemez.")

    hepsi = [v for v in varliklar()
             if v.get("tip") == TIP_MOB and v.get("vnum", 0) > 0]
    if not hepsi:
        raise SystemExit("Yakında canavar yok.")
    hepsi.sort(key=lambda v: v.get("mesafe", 99999))
    print("yakında %d canavar, en yakın %s m, en uzak %s m"
          % (len(hepsi), hepsi[0].get("mesafe"), hepsi[-1].get("mesafe")))

    print("\n%-30s %-8s %-12s %s"
          % ("hedef", "mesafe", "can", "sonuç"))
    print("-" * 76)

    sonuclar = []
    for v in hepsi:
        vid = v["vid"]
        mesafe = v.get("mesafe", 0)
        # ÖNCE CANI ÖĞREN, SONRA VUR.
        #
        # "can -1'den 100'e çıktı" İSABET DEĞİLDİR: hedefi seçince
        # sunucu zaten canı bildiriyor. İlk ölçümde bunu isabet saymak
        # dört hedefte de yanlış "İSABET" üretmişti. Tek geçerli kanıt
        # canın DÜŞMESİ.
        enjekte(paket_hedef(vid))
        time.sleep(0.7)
        once_v = canavar(vid)
        if not once_v:
            continue
        once = once_v.get("can", -1)
        if once < 0:
            print("%-30s %-8s %-12s %s"
                  % ((v.get("ad", "?"))[:29], "%s m" % mesafe,
                     "bilinmiyor", "ATLANDI — can okunamıyor"))
            continue

        vur(vid, once_v.get("x", 0), once_v.get("y", 0), a.vurus)
        time.sleep(0.8)

        sonra_v = canavar(vid)
        if sonra_v is None:
            sonuc, isabet = "listeden düştü (öldü?)", True
            sonra = None
        else:
            sonra = sonra_v.get("can", -1)
            if sonra >= 0 and sonra < once:
                sonuc, isabet = "İSABET (can düştü)", True
            else:
                sonuc, isabet = "isabet YOK (can sabit)", False

        print("%-30s %-8s %-12s %s"
              % ((v.get("ad", "?"))[:29], "%s m" % mesafe,
                 "%s -> %s" % (once, sonra), sonuc))
        sonuclar.append((mesafe, isabet, v.get("ad", "?")))

    print("\n" + "=" * 76)
    isabetli = [m for m, ok, _ in sonuclar if ok]
    iskalar = [m for m, ok, _ in sonuclar if not ok]
    if not sonuclar:
        print("Hiç hedef denenemedi.")
        return 1
    if not isabetli:
        print("HİÇBİRİ İSABET ETMEDİ — en yakını bile (%s m)."
              % sonuclar[0][0])
        print("Sorun mesafe DEĞİL: kurulumda bir şey ters.")
        print("  - enjeksiyon açık mı, doğru kanala mı yazıyor")
        print("  - karakter ölü/oturuyor olabilir")
        return 1
    print("İSABET EDEN mesafeler : %s" % sorted(isabetli))
    print("İSKALAYAN mesafeler   : %s" % sorted(iskalar))
    print()
    print("En uzak İSABET  : %s m" % max(isabetli))
    if iskalar:
        print("En yakın İSKA   : %s m" % min(iskalar))
        if min(iskalar) > max(isabetli):
            print()
            print("SUNUCUNUN SALDIRI MENZİLİ %s ile %s m ARASINDA."
                  % (max(isabetli), min(iskalar)))
            print("Menzil ayarını bunun ALTINA çek; üstünde paket boşa gider.")
    else:
        print("Denenen mesafelerin HEPSİ isabet etti — menzil en az %s m."
              % max(isabetli))
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
