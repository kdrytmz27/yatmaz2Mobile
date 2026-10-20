# -*- coding: utf-8 -*-
"""
Kendi vid'imizi KANITLA — istemcinin kendi gönderdiği paketlerden.

NEDEN
-----
İstemci hizalama paketi (0x05 SYNC_POSITION) bizim vid'imizle gönderilmezse
istemci başka bir varlığı sürükler. Sahada tam olarak bu görüldü: karakter
yerine bir canavar taşındı.

APK kendi vid'ini 0x11'den okuyordu. tools/kendi_vid_dogrula.py bunun
yanlış olduğunu gösterdi (64 farklı vid, saldırdığımız canavarlarla
çakışıyor).

YÖNTEM — çakışmayan tek kanıt
-----------------------------
İstemci hareket ederken iki şey gönderir:

  0x07  CG_MOVE          16 bayt: 07 bFunc bArg bRot x(4) y(4) tik(4)
        VID YOK — sunucu bizi bağlantıdan tanır. Ama X,Y BİZİM konumumuz.

  0x08  CG_SYNC_POSITION  08 wSize(2) [ vid(4) x(4) y(4) ] x N
        Burada VID VAR. İstemci kendi konumunu senkronlarken kendi
        vid'ini yazar.

Yani: bir 0x08 girdisinin (x,y)'si, yakın zamandaki bir 0x07'nin (x,y)'sine
çok yakınsa, o girdinin vid'i BİZİZ. Başka hiçbir varlığın konumu bizim
0x07'lerimizle bu kadar tutarlı olamaz.

Sonra çapraz doğrulama: bulunan vid, saldırdığımız (0x02/0x3D) vid'lerin
arasında OLMAMALI.

KULLANIM
--------
    python tools/kendi_vid_bul.py log/r2_20260829_070117.pcap
    python tools/kendi_vid_bul.py           # log/ içindeki en büyüğü
"""

import glob
import os
import struct
import sys
from collections import Counter, defaultdict

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from kendi_vid_dogrula import pcap_oku, akis_birlestir, u32, u16  # noqa: E402

MAKUL_MIN = 10000        # ham koordinat alt sınırı
MAKUL_MAX = 1000000


def makul(v):
    return MAKUL_MIN <= v <= MAKUL_MAX


def giden_cerceve(veri):
    """
    GİDEN akışı çerçeveler. Giden yön dardır: sadece birkaç opcode var,
    bu yüzden gelen akıştaki gibi karmaşık bir tablo gerekmez.

    Döner: (ofset, opcode, boy) listesi
    """
    boylar = {0x02: 6, 0x03: 5, 0x07: 16, 0x09: 2, 0x0F: 5,
              0x3D: 5, 0x1A: 5, 0x32: 4, 0x33: 2, 0x34: 2}
    i = 0
    n = len(veri)
    cikti = []
    while i < n:
        op = veri[i]
        if op == 0x08:                       # uzunluk önekli
            if i + 3 > n:
                break
            boy = u16(veri, i + 1)
            if boy < 3 or boy > 2000 or i + boy > n:
                i += 1
                continue
            cikti.append((i, op, boy))
            i += boy
            continue
        boy = boylar.get(op)
        if boy is None or i + boy > n:
            i += 1
            continue
        if op == 0x07 and not (makul(u32(veri, i + 4))
                               and makul(u32(veri, i + 8))):
            i += 1
            continue
        cikti.append((i, op, boy))
        i += boy
    return cikti


def main():
    if len(sys.argv) > 1:
        yol = sys.argv[1]
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 10000]
        if not adaylar:
            print('X log/ içinde işe yarar pcap yok.')
            return
        yol = max(adaylar, key=os.path.getsize)

    print('=' * 70)
    print('KENDİ VID BUL — %s' % os.path.basename(yol))
    print('=' * 70)

    paketler = pcap_oku(yol)
    giden = akis_birlestir(paketler, 'giden')
    gelen = akis_birlestir(paketler, 'gelen')
    print('giden %d bayt, gelen %d bayt' % (len(giden), len(gelen)))

    cerceveler = giden_cerceve(giden)
    dagilim = Counter(op for _, op, _ in cerceveler)
    print('giden opcode dağılımı: %s'
          % {hex(k): v for k, v in dagilim.most_common()})
    print()

    # --- bizim konumlarımız (0x07) ---
    benim = []
    for ofs, op, boy in cerceveler:
        if op == 0x07:
            benim.append((ofs, u32(giden, ofs + 4), u32(giden, ofs + 8)))
    print('-' * 70)
    print('BİZİM 0x07 hareketlerimiz: %d adet' % len(benim))
    if benim:
        print('  ilk: %d,%d    son: %d,%d'
              % (benim[0][1], benim[0][2], benim[-1][1], benim[-1][2]))
    if not benim:
        print('X 0x07 yok — bu kayıtta yürümemişsin. Yürüdüğün bir kayıt gerek.')
        return
    print()

    # --- 0x08 girdileri ---
    girdiler = []
    for ofs, op, boy in cerceveler:
        if op != 0x08:
            continue
        adet = (boy - 3) // 12
        for k in range(adet):
            t = ofs + 3 + k * 12
            girdiler.append((ofs, u32(giden, t), u32(giden, t + 4),
                             u32(giden, t + 8)))
    print('-' * 70)
    print('İSTEMCİNİN 0x08 senkron girdileri: %d adet' % len(girdiler))
    if not girdiler:
        print('X 0x08 yok. Bu sunucuda istemci CG_SYNC_POSITION göndermiyor.')
        print('  Alternatif: giriş anını (login) kaydet, GC_MAIN_CHARACTER ara.')
        return

    # --- eşleştirme: 0x08 girdisi ile EN YAKIN 0x07 arasındaki mesafe ---
    puan = defaultdict(list)
    for ofs, vid, x, y in girdiler:
        if not (makul(x) and makul(y)):
            continue
        # akışta en yakın 0x07'yi bul (ofset olarak)
        en_iyi = None
        for bofs, bx, by in benim:
            d = abs(bofs - ofs)
            if en_iyi is None or d < en_iyi[0]:
                en_iyi = (d, bx, by)
        if en_iyi is None:
            continue
        _, bx, by = en_iyi
        uzak = ((x - bx) ** 2 + (y - by) ** 2) ** 0.5
        puan[vid].append(uzak)

    print()
    print('-' * 70)
    print('0x08 vid\'lerinin BİZİM konumumuza uzaklığı')
    print('%-14s %6s %10s %10s' % ('vid', 'adet', 'ortalama', 'en_yakin'))
    siralama = sorted(puan.items(),
                      key=lambda kv: sum(kv[1]) / len(kv[1]))
    for vid, uzaklar in siralama[:12]:
        print('%-14d %6d %9.0f %10.0f'
              % (vid, len(uzaklar), sum(uzaklar) / len(uzaklar), min(uzaklar)))

    # --- çapraz doğrulama ---
    from kendi_vid_dogrula import tara
    saldiri = tara(giden, 0x02, 6, vid_ofset=2)
    hedef = tara(giden, 0x3D, 5)
    baskasi = set(saldiri) | set(hedef)

    print()
    print('=' * 70)
    aday = None
    for vid, uzaklar in siralama:
        ort = sum(uzaklar) / len(uzaklar)
        if vid in baskasi:
            print('ELENDİ %d — saldırdığımız/hedeflediğimiz vid' % vid)
            continue
        if ort > 3000:
            print('ELENDİ %d — konumumuzdan ortalama %.0f ham uzak'
                  % (vid, ort))
            continue
        aday = (vid, ort, len(uzaklar))
        break

    if aday:
        print()
        print('KENDİ VID\'İMİZ: %d' % aday[0])
        print('  konumumuza ortalama uzaklık : %.0f ham (%.1f m)'
              % (aday[1], aday[1] / 100.0))
        print('  kaç 0x08 girdisinde geçti   : %d' % aday[2])
        print('  saldırdığımız vid mi        : hayır')
    else:
        print('Aday bulunamadı — 0x08 girdileri konumumuzla örtüşmüyor.')
    print('=' * 70)


if __name__ == '__main__':
    main()
