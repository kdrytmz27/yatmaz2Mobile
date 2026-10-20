# -*- coding: utf-8 -*-
"""
GERÇEK istemci yürürken 0x07'yi NASIL gönderiyor? — desen çıkarır.

NEDEN
-----
Bot bir hareket paketi yollayıp yolun bitmesini bekliyor. Sunucu bizi
oraya yürütüyor, VARIYORUZ ve DURUYORUZ; sonra bot bir sonrakini yolluyor.
Dışarıdan bakan "durup durup yürüyor" diyor — bot gibi.

Gerçek oyuncu yürürken istemci ne yapıyor? Tek bir "şuraya git" paketi mi
yolluyor, yoksa sürekli akan bir paket dizisi mi? Cevabı kayıttan alalım:
bu betik GİDEN 0x07'leri zaman damgasıyla sırayla döküp

  • paketler arası süreyi
  • paketler arası mesafeyi
  • bFunc/bArg/bRot dağılımını
  • hedefin sabit mi yoksa her pakette ilerliyor mu olduğunu

gösterir. Bot da aynı ritmi taklit etmeli.

YAPI (giden 0x07, 16 bayt)
    +0  u8   header = 0x07
    +1  u8   bFunc
    +2  u8   bArg
    +3  u8   bRot
    +4  i32  lX
    +8  i32  lY
    +12 u32  dwTime

KULLANIM
--------
    python tools/giden_hareket_deseni.py log/r2_20260821_230523.pcap
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

OYUN_IP = '185.128.114.87'


def pcap_giden(yol):
    """(zaman_us, yuk) — istemciden sunucuya giden TCP yükleri."""
    ham = open(yol, 'rb').read()
    if ham[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1'):
        en = '<'
    else:
        en = '>'
    baglanti = struct.unpack_from(en + 'I', ham, 20)[0]
    lh = 16 if baglanti == 113 else (14 if baglanti == 1 else 0)
    i = 24
    cikti = []
    while i + 16 <= len(ham):
        sn, us, cap, _ = struct.unpack_from(en + 'IIII', ham, i)
        i += 16
        pkt = ham[i:i + cap]
        i += cap
        if len(pkt) < lh + 40:
            continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6:
            continue
        kaynak = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if kaynak == OYUN_IP:
            continue
        tcp = ip + (pkt[ip] & 0xF) * 4
        yuk = pkt[tcp + (((pkt[tcp + 12] >> 4) & 0xF) * 4):cap]
        if yuk:
            cikti.append((sn * 1000000 + us, yuk))
    return cikti


def analiz(yol):
    print('=' * 78)
    print('GİDEN HAREKET DESENİ — %s' % os.path.basename(yol))
    print('=' * 78)
    parcalar = pcap_giden(yol)
    if not parcalar:
        print('X giden veri yok')
        return

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
            hareketler.append((zaman, yuk[i + 1], yuk[i + 2], yuk[i + 3],
                               x, y, struct.unpack_from('<I', yuk, i + 12)[0]))
            i += 16
    if not hareketler:
        print('X 0x07 yok — bu kayıtta yürünmemiş')
        return

    print('%d adet GİDEN 0x07' % len(hareketler))
    print()
    print('%-4s %-9s %-5s %-4s %-5s %-9s %-9s %-8s %s'
          % ('#', 'Δt(ms)', 'func', 'arg', 'rot', 'x', 'y', 'Δmesafe',
             'hız(ham/s)'))
    print('-' * 78)

    araliklar = []
    mesafeler = []
    fdag = Counter()
    adag = Counter()
    t0 = hareketler[0][0]
    for k, (z, f, a, r, x, y, tk) in enumerate(hareketler):
        fdag[f] += 1
        adag[a] += 1
        if k == 0:
            print('%-4d %-9s %-5d %-4d %-5d %-9d %-9d %-8s %s'
                  % (k, '-', f, a, r, x, y, '-', '-'))
            continue
        pz, _, _, _, px, py, _ = hareketler[k - 1]
        dt = (z - pz) / 1000.0
        d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        araliklar.append(dt)
        mesafeler.append(d)
        hiz = (d / dt * 1000.0) if dt > 0 else 0
        if k < 30:
            print('%-4d %-9.0f %-5d %-4d %-5d %-9d %-9d %-8.0f %.0f'
                  % (k, dt, f, a, r, x, y, d, hiz))

    araliklar.sort()
    mesafeler.sort()
    n = len(araliklar)
    if n == 0:
        print()
        print('Tek paket var — desen çıkarmak için en az iki 0x07 gerekiyor.')
        print('Bu kayıtta yürünmemiş (ör. yalnızca satış/tıklama kaydı).')
        print('Yürüdüğün bir kayıt kullan: log/r2_20260821_230523.pcap gibi.')
        return
    print()
    print('-' * 78)
    print('bFunc dağılımı : %s' % dict(fdag.most_common()))
    print('bArg  dağılımı : %s' % dict(adag.most_common(6)))
    print()
    print('PAKETLER ARASI SÜRE (ms)')
    print('   en küçük %.0f | %%25 %.0f | ORTANCA %.0f | %%75 %.0f | en büyük %.0f'
          % (araliklar[0], araliklar[n // 4], araliklar[n // 2],
             araliklar[3 * n // 4], araliklar[-1]))
    print('PAKETLER ARASI MESAFE (ham)')
    print('   en küçük %.0f | %%25 %.0f | ORTANCA %.0f | %%75 %.0f | en büyük %.0f'
          % (mesafeler[0], mesafeler[n // 4], mesafeler[n // 2],
             mesafeler[3 * n // 4], mesafeler[-1]))
    print()
    kisa = sum(1 for d in araliklar if d < 1000)
    print('1 saniyeden kısa aralık: %d / %d  (%%%.0f)'
          % (kisa, n, 100.0 * kisa / n))
    print()
    if araliklar[n // 2] < 800:
        print('>> DESEN: istemci SÜREKLİ AKAN paket yolluyor.')
        print('   Yürürken her ~%.0f ms\'de bir, ~%.0f ham ilerlemiş yeni'
              % (araliklar[n // 2], mesafeler[n // 2]))
        print('   bir hedefle. Tek bir "şuraya git" paketi DEĞİL.')
        print('   Bot da aynı ritmi tutturmalı: uzun yolu bu boyda')
        print('   adımlara bölüp aynı sıklıkta göndermeli.')
    else:
        print('>> DESEN: seyrek paket — tek hedefli hareket.')


def main():
    if len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        adaylar = [y for y in glob.glob(os.path.join(_KOK, 'log', '*.pcap'))
                   if os.path.getsize(y) > 5000]
        yollar = adaylar
    for y in yollar:
        analiz(y)
        print()


if __name__ == '__main__':
    main()
