# -*- coding: utf-8 -*-
"""
Kendi vid'imiz — GERÇEK ÇERÇEVELEME ile (imza taraması değil).

tools/kendi_vid_dogrula.py imza taraması yapıyordu ve 0x11 için 64 farklı
vid buldu. Bunların çoğu hizasız okumadan doğan hayalet. Doğru soru şu:
akış DOĞRU çerçevelendiğinde 0x11 kaç farklı vid taşıyor?

Bu betik tools/parser_dogrula.py'nin doğrulanmış uzunluk tablosunu
kullanarak gelen akışı gerçek paketlere böler, sonra:

  • 0x11 vid'lerini sayar          (aday: kendi vid'imiz)
  • 0x01 CHARACTER_ADD vid'lerini  (kesin: BAŞKA varlıklar)
  • 0x03 MOVE vid'lerini           (kesin: BAŞKA varlıklar)
  • 0x88 isim paketlerini          (vid -> isim)

Kendi vid'imiz 0x01/0x03 listelerinde OLMAMALI: sunucu bize kendimizi
eklemez ve kendi hareketimizi geri yollamaz (859 MOVE'un sıfırı bizdi).

KULLANIM
--------
    python tools/kendi_vid_cerceve.py log/r2_20260829_070117.pcap
    python tools/kendi_vid_cerceve.py --hepsi
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


def cerceveler(yol):
    """
    Gelen akışı doğrulanmış tabloyla çerçeveler.
    Döner: (opcode, ofset, boy, akış) listesi
    """
    akis = b''.join(pd.pcap_segmentler(yol))
    i = 0
    n = len(akis)
    cikti = []
    while i < n:
        boy = pd.boy_yeni(akis, i, n, False)
        if boy == -1:
            break
        if boy == 0:
            i += 1
            continue
        cikti.append((akis[i], i, boy))
        i += boy
    return cikti, akis


def isim_coz(akis, i, boy):
    """0x88: +1 vid, +5 isim (CP1254, NUL sonlu)."""
    vid = pd.i32le(akis, i + 1)
    ham = akis[i + 5:i + boy]
    kes = ham.find(b'\x00')
    if kes >= 0:
        ham = ham[:kes]
    try:
        ad = ham.decode('cp1254', 'replace').strip()
    except Exception:
        ad = ''
    return vid, ad


def analiz(yol):
    print('=' * 70)
    print('%s' % os.path.basename(yol))
    print('=' * 70)
    try:
        cerc, akis = cerceveler(yol)
    except Exception as e:
        print('X çerçeveleme hatası: %s' % e)
        return
    if not cerc:
        print('X çerçeve yok')
        return

    dagilim = Counter(op for op, _, _ in cerc)
    print('gelen akış %d bayt, %d paket' % (len(akis), len(cerc)))
    print('opcode dağılımı: %s'
          % {hex(k): v for k, v in dagilim.most_common(12)})
    print()

    onbir = Counter()
    ekle = {}
    hareket = Counter()
    isimler = {}
    for op, i, boy in cerc:
        if op == 0x11 and boy >= 5:
            onbir[pd.i32le(akis, i + 1)] += 1
        elif op == 0x01 and boy >= 22:
            ekle[pd.i32le(akis, i + 1)] = akis[i + 21]
        elif op == 0x03 and boy >= 8:
            hareket[pd.i32le(akis, i + 4)] += 1
        elif op == 0x88 and boy >= 6:
            v, a = isim_coz(akis, i, boy)
            if a:
                isimler[v] = a

    print('-' * 70)
    print('0x11 KENDİ DURUM — %d farklı vid (çerçevelenmiş)' % len(onbir))
    for vid, adet in onbir.most_common(8):
        etiket = []
        if vid in ekle:
            etiket.append('0x01 ile EKLENDİ bType=%d' % ekle[vid])
        if vid in hareket:
            etiket.append('0x03 MOVE x%d' % hareket[vid])
        if vid in isimler:
            etiket.append('isim=%r' % isimler[vid])
        print('   %-12d x%-5d %s'
              % (vid, adet, '  |  '.join(etiket) if etiket
                 else '(başka pakette geçmiyor)'))
    print()
    print('0x01 ile eklenen varlık : %d' % len(ekle))
    print('0x03 MOVE alan varlık   : %d' % len(hareket))
    print('0x88 ile isimlenen      : %d' % len(isimler))
    if isimler:
        ornek = list(isimler.items())[:10]
        print('   örnek isimler: %s'
              % ', '.join('%d=%r' % (v, a) for v, a in ornek))
    print()

    temiz = [v for v in onbir
             if v not in ekle and v not in hareket]
    print('-' * 70)
    if len(onbir) == 1:
        v = list(onbir)[0]
        if v in ekle or v in hareket:
            print('SONUÇ: 0x11 tek vid taşıyor (%d) ama o vid BAŞKA bir' % v)
            print('       varlık olarak da geçiyor — BİZ DEĞİL.')
        else:
            print('SONUÇ: 0x11 tek vid taşıyor (%d), başka hiçbir varlık' % v)
            print('       paketinde geçmiyor — KENDİ VID\'İMİZ olabilir.')
    else:
        print('SONUÇ: 0x11 hâlâ %d farklı vid taşıyor.' % len(onbir))
        print('       Temiz adaylar (0x01/0x03\'te geçmeyen): %s'
              % (sorted(temiz)[:10] if temiz else 'YOK'))
    print()


def main():
    if '--hepsi' in sys.argv:
        yollar = sorted(y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                        if os.path.getsize(y) > 5000)
    elif len(sys.argv) > 1:
        yollar = [sys.argv[1]]
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 10000]
        yollar = [max(adaylar, key=os.path.getsize)] if adaylar else []
    for y in yollar:
        analiz(y)


if __name__ == '__main__':
    main()
