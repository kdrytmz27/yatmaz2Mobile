# -*- coding: utf-8 -*-
"""
Kendi vid'imizi SAVAŞ paketlerinden bulur — 0x11 gelmediğinde bile.

SORUN
-----
APK kendi vid'ini `0x11` paketinden öğreniyor. Ama 29 Ağu 2026 21:46
kaydında (179 saniye, 5771 gelen paket) **0x11 HİÇ GELMEDİ**. Önceki
kayıtlarda 87-535 arası geliyordu. Yani bu paket güvenilir bir kaynak
değil: bazı oturumlarda hiç gönderilmiyor.

Vid bilinmeyince istemci hizalaması hiç çalışmıyor.

YÖNTEM — savaş eşleşmesi
------------------------
`0x3E` (9 bayt) savaş vuruşu İKİ vid taşıyor:

    +0  u8   header = 0x3E
    +1  u32  vid1     vuran
    +5  u32  vid2     vurulan

Biz saldırdığımızda vuran BİZİZ, vurulan da GİDEN `0x02`/`0x3D` ile
hedeflediğimiz canavar. Yani:

  • giden 0x02/0x3D'den HEDEF LİSTEMİZİ çıkar
  • gelen 0x3E'de her vuran adayı için, vurduğu şeylerin ne kadarının
    bizim hedef listemizde olduğuna bak
  • örtüşmesi en yüksek olan aday BİZİZ

Doğrulama: kendi vid'imiz asla kendi hedef listemizde olamaz (kendimize
saldırmayız) ve `0x01 CHARACTER_ADD` ile eklenen canavarlar arasında
olmamalıdır.

KULLANIM
--------
    python tools/kendi_vid_savastan.py log/r2_20260829_214639.pcap
    python tools/kendi_vid_savastan.py --hepsi
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

import parser_dogrula as pd  # noqa: E402
from kendi_vid_cerceve import cerceveler, isim_coz  # noqa: E402
from giden_hareket_deseni import pcap_giden  # noqa: E402


def giden_hedefler(yol):
    """GİDEN 0x02 (saldırı) ve 0x3D (hedef seç) vid'leri."""
    hedefler = Counter()
    for _, yuk in pcap_giden(yol):
        i = 0
        n = len(yuk)
        while i < n:
            op = yuk[i]
            if op == 0x02 and i + 6 <= n:
                v = struct.unpack_from('<I', yuk, i + 2)[0]
                if 1000 < v < 100000000:
                    hedefler[v] += 1
                    i += 6
                    continue
            if op == 0x3D and i + 5 <= n:
                v = struct.unpack_from('<I', yuk, i + 1)[0]
                if 1000 < v < 100000000:
                    hedefler[v] += 1
                    i += 5
                    continue
            if op == 0x07 and i + 16 <= n:
                i += 16
                continue
            if op == 0x08 and i + 3 <= n:
                boy = yuk[i + 1] | (yuk[i + 2] << 8)
                if 3 <= boy <= 2000 and i + boy <= n:
                    i += boy
                    continue
            i += 1
    return hedefler


def analiz(yol):
    print('=' * 74)
    print('KENDİ VID — SAVAŞTAN — %s' % os.path.basename(yol))
    print('=' * 74)

    cerc, akis = cerceveler(yol)
    vuruslar = []
    eklenen = {}
    isimler = {}
    onbir = Counter()
    for op, i, boy in cerc:
        if op == 0x3E and boy >= 9:
            vuruslar.append((pd.i32le(akis, i + 1), pd.i32le(akis, i + 5)))
        elif op == 0x01 and boy >= 22:
            eklenen[pd.i32le(akis, i + 1)] = akis[i + 21]
        elif op == 0x88 and boy >= 6:
            v, a = isim_coz(akis, i, boy)
            if a:
                isimler[v] = a
        elif op == 0x11 and boy >= 5:
            onbir[pd.i32le(akis, i + 1)] += 1

    hedefler = giden_hedefler(yol)
    print('gelen 0x3E savaş vuruşu : %d' % len(vuruslar))
    print('giden hedeflerimiz      : %d farklı vid' % len(hedefler))
    print('0x11 paketi             : %d adet %s'
          % (sum(onbir.values()),
             '(HİÇ GELMEDİ — eski yöntem çalışmaz)' if not onbir else ''))
    print()

    if not vuruslar or not hedefler:
        print('X Yeterli veri yok. Botun SALDIRDIĞI bir kayıt gerekiyor.')
        return

    # Her "vuran" adayı için: vurdukları bizim hedeflerimizle örtüşüyor mu?
    vurduklari = defaultdict(Counter)
    for vuran, vurulan in vuruslar:
        vurduklari[vuran][vurulan] += 1

    puanlar = []
    for aday, kurbanlar in vurduklari.items():
        toplam = sum(kurbanlar.values())
        if toplam < 5:
            continue
        ortusen = sum(a for k, a in kurbanlar.items() if k in hedefler)
        oran = ortusen / float(toplam)
        puanlar.append((oran, toplam, aday, len(kurbanlar)))
    puanlar.sort(reverse=True)

    print('-' * 74)
    print('%-12s %-8s %-8s %-9s %s'
          % ('vuran vid', 'vuruş', 'kurban', 'örtüşme', 'not'))
    print('-' * 74)
    for oran, toplam, aday, kurban in puanlar[:10]:
        notlar = []
        if aday in hedefler:
            notlar.append('BİZ SALDIRDIK -> canavar')
        if aday in eklenen:
            notlar.append('0x01 bType=%d' % eklenen[aday])
        if aday in isimler:
            notlar.append('isim=%r' % isimler[aday])
        print('%-12d %-8d %-8d %-9s %s'
              % (aday, toplam, kurban, '%%%d' % (oran * 100),
                 '  |  '.join(notlar) if notlar else ''))

    print()
    print('=' * 74)
    aday = None
    for oran, toplam, v, kurban in puanlar:
        if v in hedefler:
            continue                       # kendimize saldırmayız
        if oran < 0.5:
            continue
        aday = (v, oran, toplam, kurban)
        break

    if aday:
        v, oran, toplam, kurban = aday
        print('KENDİ VID\'İMİZ: %d' % v)
        print('   %d vuruş, %d farklı kurban' % (toplam, kurban))
        print('   kurbanların %%%d\'i bizim hedef listemizde' % (oran * 100))
        print('   kendi hedef listemizde DEĞİL : evet')
        print('   0x01 ile eklenmiş mi         : %s'
              % ('EVET (bType=%d)' % eklenen[v] if v in eklenen else 'hayır'))
        print('   ismi                         : %s'
              % isimler.get(v, '(isim paketi gelmemiş)'))
        if onbir:
            en = onbir.most_common(1)[0]
            print()
            print('   0x11\'in dediği: %d (%d oy) — %s'
                  % (en[0], en[1],
                     'AYNI, doğrulandı' if en[0] == v else 'FARKLI!'))
    else:
        print('Aday bulunamadı.')
        print('Bot bu kayıtta saldırmamış olabilir — savaşlı bir kayıt gerek.')
    print('=' * 74)


def main():
    if '--hepsi' in sys.argv:
        yollar = sorted(y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                        if os.path.getsize(y) > 10000)
    elif len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 10000]
        yollar = [max(adaylar, key=os.path.getmtime)] if adaylar else []
    for y in yollar:
        analiz(y)
        print()


if __name__ == '__main__':
    main()
