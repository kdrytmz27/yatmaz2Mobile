# -*- coding: utf-8 -*-
"""
GELEN 0x03 MOVE paketlerinin ALANLARINI inceler.

NEDEN
-----
İstemciyi 0x05 SYNC_POSITION ile taşıyoruz. O paket bir "konum düzeltmesi";
istemci karakteri oraya oturtuyor ama hareket durum makinesini hiç
çalıştırmıyor — sonuç: karakter koşmadan SÜRÜKLENİYOR.

Başka oyuncular/canavarlar yürürken ekranda düzgün animasyonla koşuyorlar.
Onları çizdiren paket 0x03 GC_MOVE. Yani doğru şablon elimizde: bu betik
gerçek 0x03'lerin alanlarını döküp hangi değerlerin animasyonu tetiklediğini
gösterir.

YAPI (parser'dan)
-----------------
    +0  u8   header = 0x03
    +1  u8   bFunc     hareket işlevi (0=bekle, 1=yürü, ...)
    +2  u8   bArg
    +3  u8   bRot      yön (derece/5)
    +4  u32  dwVID
    +8  i32  lX
    +12 i32  lY
    +16 u32  dwTime    sunucu tiki
    +20 u32  dwDuration  hareketin KAÇ MS süreceği  <-- animasyonun anahtarı

KULLANIM
--------
    python tools/hareket_paketi_incele.py log/r2_20260823_012800.pcap
"""

import glob
import os
import struct
import sys
from collections import Counter

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import parser_dogrula as pd  # noqa: E402
from kendi_vid_cerceve import cerceveler  # noqa: E402


def u32(b, i):
    return struct.unpack_from('<I', b, i)[0]


def analiz(yol):
    print('=' * 74)
    print('0x03 MOVE ALAN İNCELEMESİ — %s' % os.path.basename(yol))
    print('=' * 74)
    cerc, akis = cerceveler(yol)
    hareketler = [(i, boy) for op, i, boy in cerc if op == 0x03]
    print('%d adet 0x03 MOVE' % len(hareketler))
    if not hareketler:
        return
    print()

    bfunc = Counter()
    barg = Counter()
    sureler = Counter()
    onceki = {}          # vid -> (x, y, time)

    satir = 0
    print('%-6s %-5s %-5s %-5s %-11s %-9s %-9s %-11s %-9s %s'
          % ('#', 'func', 'arg', 'rot', 'vid', 'x', 'y', 'time',
             'süre', 'hesap'))
    print('-' * 96)
    for i, boy in hareketler:
        f = akis[i + 1]
        a = akis[i + 2]
        r = akis[i + 3]
        vid = pd.i32le(akis, i + 4)
        x = pd.i32le(akis, i + 8)
        y = pd.i32le(akis, i + 12)
        t = u32(akis, i + 16)
        sure = u32(akis, i + 20)
        bfunc[f] += 1
        barg[a] += 1
        sureler[sure] += 1

        hesap = ''
        if vid in onceki:
            px, py, pt = onceki[vid]
            d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if sure > 0:
                hesap = '%.0f ham / %d ms = %.2f ham/ms' % (d, sure, d / sure)
            else:
                hesap = '%.0f ham, süre 0' % d
        onceki[vid] = (x, y, t)

        if satir < 25:
            print('%-6d %-5d %-5d %-5d %-11d %-9d %-9d %-11d %-9d %s'
                  % (satir, f, a, r, vid, x, y, t, sure, hesap))
        satir += 1

    print()
    print('-' * 74)
    print('bFunc dağılımı : %s' % dict(bfunc.most_common()))
    print('bArg  dağılımı : %s' % dict(barg.most_common(8)))
    print('süre  dağılımı : %s' % dict(sureler.most_common(10)))
    sifir = sureler.get(0, 0)
    print()
    print('süre = 0 olan   : %d / %d  (%.0f%%)'
          % (sifir, satir, 100.0 * sifir / max(1, satir)))
    print('süre > 0 olan   : %d  <- animasyonlu hareket bunlar'
          % (satir - sifir))


def main():
    if len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 10000]
        yollar = [max(adaylar, key=os.path.getsize)] if adaylar else []
    for y in yollar:
        analiz(y)
        print()


if __name__ == '__main__':
    main()
