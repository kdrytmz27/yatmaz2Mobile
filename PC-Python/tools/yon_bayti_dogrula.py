# -*- coding: utf-8 -*-
"""
`yon_bayti()` doğru mu? — gerçek 0x07 paketlerine karşı sınar.

NEDEN
-----
Bot akan hareket paketleri göndermeye başlayınca karakter dışarıdan
"kendi etrafında dönüyor" göründü. Hareket paketinin +3 baytı yön (bRot).
Yanlış hesaplanıyorsa karakter gittiği yöne bakmaz.

YÖNTEM
------
Kayıttaki ardışık 0x07 paketlerinden GERÇEK yön çıkarılabilir: karakter
(px,py)'den (x,y)'ye gitmiş, paket de o anki bRot'u taşıyor. Yani
"konum farkından hesaplanan yön" ile "pakette yazan yön" karşılaştırılır.

Birkaç aday formül denenir; hangisi kayıtla örtüşüyorsa doğrusu odur.

KULLANIM
--------
    python tools/yon_bayti_dogrula.py log/r2_20260821_230523.pcap
"""

import glob
import math
import os
import struct
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from giden_hareket_deseni import pcap_giden  # noqa: E402


def aday_mevcut(dx, dy):
    """tambot.py'deki mevcut yon_bayti — doğrulanacak olan."""
    if dx == 0 and dy == 0:
        return 0
    derece = math.degrees(math.atan2(-dy, dx)) % 360
    return int(round(((90 - derece) % 360) / 5)) % 72


def aday_atan_dx_dy(dx, dy):
    """rot = atan2(dx, dy) / 5"""
    if dx == 0 and dy == 0:
        return 0
    return int(round((math.degrees(math.atan2(dx, dy)) % 360) / 5)) % 72


def aday_atan_dx_negdy(dx, dy):
    if dx == 0 and dy == 0:
        return 0
    return int(round((math.degrees(math.atan2(dx, -dy)) % 360) / 5)) % 72


def aday_atan_negdx_dy(dx, dy):
    if dx == 0 and dy == 0:
        return 0
    return int(round((math.degrees(math.atan2(-dx, dy)) % 360) / 5)) % 72


def aday_atan_dy_dx(dx, dy):
    if dx == 0 and dy == 0:
        return 0
    return int(round((math.degrees(math.atan2(dy, dx)) % 360) / 5)) % 72


ADAYLAR = [
    ('MEVCUT  (90-atan2(-dy,dx))', aday_mevcut),
    ('atan2(dx,  dy)', aday_atan_dx_dy),
    ('atan2(dx, -dy)', aday_atan_dx_negdy),
    ('atan2(-dx, dy)', aday_atan_negdx_dy),
    ('atan2(dy,  dx)', aday_atan_dy_dx),
]


def hareketleri_al(yol):
    parcalar = pcap_giden(yol)
    hareketler = []
    for zaman, yuk in parcalar:
        i = 0
        while i + 16 <= len(yuk):
            if yuk[i] != 0x07:
                i += 1
                continue
            x = struct.unpack_from('<i', yuk, i + 4)[0]
            y = struct.unpack_from('<i', yuk, i + 8)[0]
            if not (10000 < x < 2000000 and 10000 < y < 2000000):
                i += 1
                continue
            hareketler.append((zaman, yuk[i + 1], yuk[i + 3], x, y))
            i += 16
    return hareketler


def fark(a, b):
    """72'lik halkada iki yön arası en kısa uzaklık."""
    d = abs(a - b) % 72
    return min(d, 72 - d)


def analiz(yol):
    hareketler = hareketleri_al(yol)
    ciftler = []
    for k in range(1, len(hareketler)):
        _, f, rot, x, y = hareketler[k]
        _, _, _, px, py = hareketler[k - 1]
        dx, dy = x - px, y - py
        if f != 1 or (dx == 0 and dy == 0):
            continue                      # yalnızca YÜRÜME paketleri
        ciftler.append((dx, dy, rot))
    if len(ciftler) < 5:
        return None, len(ciftler)

    sonuc = []
    for ad, fn in ADAYLAR:
        sapmalar = [fark(fn(dx, dy), rot) for dx, dy, rot in ciftler]
        ort = sum(sapmalar) / len(sapmalar)
        tam = sum(1 for s in sapmalar if s <= 1)
        sonuc.append((ort, tam, ad))
    return sonuc, len(ciftler)


def main():
    if len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        yollar = sorted(glob.glob(os.path.join(_KOK, 'log', '*.pcap')))

    print('=' * 74)
    print('YÖN BAYTI (bRot) DOĞRULAMA')
    print('=' * 74)
    print('Ölçüt: konum farkından hesaplanan yön, pakette yazan yöne')
    print('ne kadar yakın? Sapma 72\'lik halkada birim cinsinden (1 birim=5°).')
    print()

    toplam = {}
    for y in yollar:
        sonuc, n = analiz(y)
        if not sonuc:
            continue
        print('-' * 74)
        print('%s — %d yürüme çifti' % (os.path.basename(y), n))
        for ort, tam, ad in sorted(sonuc):
            print('   %-28s ortalama sapma %5.1f birim   ±1 içinde %d/%d (%%%d)'
                  % (ad, ort, tam, n, 100 * tam // n))
        for ort, tam, ad in sonuc:
            g = toplam.setdefault(ad, [0.0, 0, 0])
            g[0] += ort * n
            g[1] += tam
            g[2] += n

    if not toplam:
        print('X yeterli yürüme paketi olan kayıt yok')
        return
    print()
    print('=' * 74)
    print('TOPLAM')
    sirali = sorted(toplam.items(), key=lambda kv: kv[1][0] / max(1, kv[1][2]))
    for ad, (agirlik, tam, n) in sirali:
        print('   %-28s ortalama sapma %5.1f   ±1 içinde %%%d'
              % (ad, agirlik / n, 100 * tam // n))
    print()
    kazanan = sirali[0]
    print('DOĞRU FORMÜL: %s' % kazanan[0])
    if 'MEVCUT' in sirali[0][0]:
        print('   Mevcut formül doğru.')
    else:
        mevcut = [x for x in sirali if 'MEVCUT' in x[0]][0]
        print('   MEVCUT formül YANLIŞ — ortalama %.1f birim (%.0f derece) sapıyor.'
              % (mevcut[1][0] / mevcut[1][2], 5 * mevcut[1][0] / mevcut[1][2]))
    print('=' * 74)


if __name__ == '__main__':
    main()
