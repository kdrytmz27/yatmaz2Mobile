# -*- coding: utf-8 -*-
"""
Çözülmemiş küçük opcode'ların alanlarını döker.

AMAÇ
----
İstemcinin KENDİ karakterini animasyonla yürütecek bir paket arıyoruz.
0x03 GC_MOVE kendi vid'imizle gönderilince istemci onu YOK SAYIYOR (canlı
denendi, 29 Ağu 2026). Metin2 istemcisi kendi karakterinin hareket durumunu
kendisi yönetir; sunucudan gelen MOVE yalnızca BAŞKA varlıklara uygulanır.

Geriye bir ihtimal kalıyor: karakterin ANİMASYONUNU/hareketini ayrı bir
paket taşıyor olabilir (Metin2'de GC_MOTION gibi). Elimizde çözülmemiş
küçük paketler var:

    0x0D, 0x0E  (5 bayt)     0x6F, 0x72  (6 bayt)
    0x3E (9)    0x87 (10)    0x47 (17)   0x13 (43)

Bu betik her birinin alanlarını, bilinen vid'lerle karşılaştırarak döker:
+1'deki 4 bayt bir varlık kimliği mi? Öyleyse kalan baytlar ne?

KULLANIM
--------
    python tools/bilinmeyen_incele.py log/r2_20260829_070117.pcap
    python tools/bilinmeyen_incele.py log/... --op 0x72
"""

import glob
import os
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

INCELE = [0x0D, 0x0E, 0x6F, 0x72, 0x3E, 0x87, 0x47]


def analiz(yol, sadece=None):
    print('=' * 74)
    print('BİLİNMEYEN PAKET İNCELEMESİ — %s' % os.path.basename(yol))
    print('=' * 74)
    cerc, akis = cerceveler(yol)

    # Bilinen varlık kimlikleri: 0x01 ve 0x03'ten
    bilinen = set()
    for op, i, boy in cerc:
        if op == 0x01 and boy >= 5:
            bilinen.add(pd.i32le(akis, i + 1))
        elif op == 0x03 and boy >= 8:
            bilinen.add(pd.i32le(akis, i + 4))
    onbir = Counter()
    for op, i, boy in cerc:
        if op == 0x11 and boy >= 5:
            onbir[pd.i32le(akis, i + 1)] += 1
    benim = onbir.most_common(1)[0][0] if onbir else 0
    print('bilinen varlık kimliği: %d    kendi vid: %d' % (len(bilinen), benim))
    print()

    hedefler = sadece if sadece else INCELE
    for op in hedefler:
        ornekler = [(i, boy) for o, i, boy in cerc if o == op]
        if not ornekler:
            continue
        boy = ornekler[0][1]
        print('-' * 74)
        print('0x%02X — %d paket, %d bayt' % (op, len(ornekler), boy))

        # +1'deki 4 bayt varlık kimliği mi?
        if boy >= 5:
            vidler = [pd.i32le(akis, i + 1) for i, _ in ornekler]
            tanidik = sum(1 for v in vidler if v in bilinen)
            bizimki = sum(1 for v in vidler if v == benim)
            print('   +1 u32: %d farklı değer, %d/%d bilinen varlık, '
                  '%d kez KENDİ vid\'imiz'
                  % (len(set(vidler)), tanidik, len(vidler), bizimki))
            if tanidik > len(vidler) * 0.5:
                print('   >> +1 bir VARLIK KİMLİĞİ (vid)')
            elif bizimki > len(vidler) * 0.5:
                print('   >> +1 HEP BİZİZ — kendimize özel paket')

        # kalan baytların dağılımı
        for ofs in range(5, min(boy, 12)):
            degerler = Counter(akis[i + ofs] for i, _ in ornekler)
            if len(degerler) <= 8:
                print('   +%-2d u8 : %s' % (ofs, dict(degerler.most_common(8))))
            else:
                print('   +%-2d u8 : %d farklı değer (%d..%d)'
                      % (ofs, len(degerler), min(degerler), max(degerler)))

        # ilk 5 örnek hex
        print('   örnekler:')
        for i, b in ornekler[:5]:
            print('      %s' % ' '.join('%02X' % x for x in akis[i:i + b]))
        print()


def main():
    args = [a for a in sys.argv[1:]]
    sadece = None
    if '--op' in args:
        k = args.index('--op')
        sadece = [int(args[k + 1], 0)]
        del args[k:k + 2]
    if args:
        yollar = args
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 10000]
        yollar = [max(adaylar, key=os.path.getsize)] if adaylar else []
    for y in yollar:
        analiz(y, sadece)


if __name__ == '__main__':
    main()
