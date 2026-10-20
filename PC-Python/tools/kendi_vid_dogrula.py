# -*- coding: utf-8 -*-
"""
"Kendi vid'imiz" gerçekten 0x11'den mi geliyor? — kayıttan DOĞRULAR.

SORUN
-----
İstemci hizalama paketi (0x05 SYNC_POSITION) bizim vid'imizle gönderilmeli.
Yanlış vid gönderilirse istemci BAŞKA bir varlığı — bir canavarı — oraya
sürükler. Sahada tam olarak bu görüldü.

APK şu an kendi vid'ini 0x11 (14 baytlık "kendi puan/durum tiki")
paketinin +1 alanından okuyor. Dokümanda bunun "HEP kendi vid'in" olduğu
yazıyor ama aynı satırda "alan anlamı henüz kesin değil" notu da var.
Bu betik iddiayı kayıttan sınar.

YÖNTEM
------
1. 0x11 paketlerindeki vid'leri topla. Gerçekten bizsek TEK bir değer
   olmalı; birden fazla çıkarsa iddia yanlıştır.
2. Bu vid'leri, GİDEN 0x02 (saldırı) ve 0x3D (hedef seç) paketlerindeki
   vid'lerle karşılaştır. Saldırdığımız şey canavardır; kendi vid'imiz
   orada görünemez. Görünüyorsa 0x11 bize ait değildir.
3. GELEN 0x01 (CHARACTER_ADD) ve 0x03 (MOVE) vid'leriyle karşılaştır.
   Sunucu bizim hareketimizi bize yollamıyor, ama BAŞKA varlıkları
   yolluyor. 0x11 vid'i bunların arasındaysa o bir başkasıdır.
4. Aday: GELEN 0x01'de bType=6 (oyuncu) olup 0x03 MOVE'u hiç gelmeyen vid.

KULLANIM
--------
    python tools/kendi_vid_dogrula.py log/r2_20260829_070117.pcap
    python tools/kendi_vid_dogrula.py            # log/ içindeki en büyüğü
"""

import glob
import os
import struct
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OYUN_IP = '185.128.114.87'


def u32(b, i):
    return struct.unpack_from('<I', b, i)[0]


def u16(b, i):
    return struct.unpack_from('<H', b, i)[0]


def pcap_oku(yol):
    """(yon, veri) çiftleri döndürür. yon: 'gelen' | 'giden'."""
    ham = open(yol, 'rb').read()
    if len(ham) < 24:
        return []
    sihir = ham[:4]
    if sihir in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1'):
        en = '<'
    elif sihir in (b'\xa1\xb2\xc3\xd4', b'\xa1\xb2\x3c\x4d'):
        en = '>'
    else:
        print('X pcap imzası tanınmadı: %s' % sihir.hex())
        return []
    baglanti = struct.unpack_from(en + 'I', ham, 20)[0]
    i = 24
    cikti = []
    while i + 16 <= len(ham):
        _, _, kapsanan, _ = struct.unpack_from(en + 'IIII', ham, i)
        i += 16
        cerceve = ham[i:i + kapsanan]
        i += kapsanan
        if len(cerceve) < 20:
            continue
        # bağlantı tipi 101 = RAW IP, 1 = Ethernet, 113 = Linux SLL
        if baglanti == 1:
            ip = cerceve[14:]
        elif baglanti == 113:
            ip = cerceve[16:]
        else:
            ip = cerceve
        if not ip or (ip[0] >> 4) != 4:
            continue
        ihl = (ip[0] & 0x0F) * 4
        if ip[9] != 6 or len(ip) < ihl + 20:
            continue
        kaynak = '.'.join(str(x) for x in ip[12:16])
        tcp = ip[ihl:]
        veri_ofset = (tcp[12] >> 4) * 4
        yuk = tcp[veri_ofset:]
        if not yuk:
            continue
        cikti.append(('gelen' if kaynak == OYUN_IP else 'giden', yuk))
    return cikti


def akis_birlestir(paketler, yon):
    return b''.join(v for y, v in paketler if y == yon)


def tara(veri, opcode, boy, vid_ofset=1, ek=None):
    """
    Sabit boylu paketi imza taramasıyla bulur ve vid'leri sayar.
    ek(veri, i) verilirse ek doğrulama yapar.
    """
    from collections import Counter
    sayac = Counter()
    i = 0
    n = len(veri)
    while i + boy <= n:
        if veri[i] == opcode:
            vid = u32(veri, i + vid_ofset)
            if 1000 <= vid <= 0x7FFFFFFF and (ek is None or ek(veri, i)):
                sayac[vid] += 1
                i += boy
                continue
        i += 1
    return sayac


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
    print('KENDİ VID DOĞRULAMA — %s' % os.path.basename(yol))
    print('=' * 70)

    paketler = pcap_oku(yol)
    if not paketler:
        print('X paket okunamadı')
        return
    gelen = akis_birlestir(paketler, 'gelen')
    giden = akis_birlestir(paketler, 'giden')
    print('gelen %d bayt, giden %d bayt' % (len(gelen), len(giden)))
    print()

    # --- 1) 0x11 vid'leri ---
    onbir = tara(gelen, 0x11, 14)
    print('-' * 70)
    print('1) GELEN 0x11 (kendi durum tiki iddiası) — %d farklı vid'
          % len(onbir))
    for vid, adet in onbir.most_common(10):
        print('     %-12d  x%d' % (vid, adet))
    if len(onbir) > 1:
        print('   >> TEK vid değil. "0x11 hep kendi vid\'imiz" iddiası ZAYIF.')
    elif len(onbir) == 1:
        print('   >> tek vid — iddia bu kayıtta tutuyor')
    print()

    # --- 2) giden saldırı/hedef vid'leri = KESİNLİKLE başkası ---
    saldiri = tara(giden, 0x02, 6, vid_ofset=2)
    hedef = tara(giden, 0x3D, 5)
    baskasi = set(saldiri) | set(hedef)
    print('-' * 70)
    print('2) GİDEN 0x02 saldırı / 0x3D hedef — bunlar BAŞKASI (%d vid)'
          % len(baskasi))
    for vid, adet in (saldiri + hedef).most_common(8):
        print('     %-12d  x%d' % (vid, adet))
    cakisma = set(onbir) & baskasi
    if cakisma:
        print('   >> ÇAKIŞMA! 0x11 vid\'i saldırdığımız şeyle aynı: %s'
              % sorted(cakisma))
        print('   >> 0x11 BİZE AİT DEĞİL — hizalama yanlış varlığı taşır.')
    else:
        print('   >> çakışma yok')
    print()

    # --- 3) gelen 0x03 MOVE vid'leri = başka varlıklar ---
    def move_ok(v, i):
        return v[i + 1] == 0 and v[i + 2] == 0 and v[i + 3] == 0
    hareket = tara(gelen, 0x03, 24, vid_ofset=4, ek=move_ok)
    print('-' * 70)
    print('3) GELEN 0x03 MOVE — %d farklı vid (sunucu BİZİ yollamıyor)'
          % len(hareket))
    cakisma2 = set(onbir) & set(hareket)
    if cakisma2:
        print('   >> ÇAKIŞMA! 0x11 vid\'i hareket eden başka varlıkla aynı:')
        for v in sorted(cakisma2):
            print('        %-12d  0x03 x%d' % (v, hareket[v]))
        print('   >> 0x11 BİZE AİT DEĞİL.')
    else:
        print('   >> çakışma yok — 0x11 vid\'i hiç MOVE almıyor (bize uyar)')
    print()

    # --- 4) 0x01 CHARACTER_ADD: tip dağılımı ---
    from collections import Counter
    tipler = Counter()
    ekle_vid = {}
    i = 0
    while i + 38 <= len(gelen):
        if gelen[i] == 0x01:
            vid = u32(gelen, i + 1)
            btype = gelen[i + 21]
            if 1000 <= vid <= 0x7FFFFFFF and btype <= 12:
                tipler[btype] += 1
                ekle_vid.setdefault(vid, btype)
                i += 38
                continue
        i += 1
    print('-' * 70)
    print('4) GELEN 0x01 CHARACTER_ADD — %d varlık' % len(ekle_vid))
    print('   bType dağılımı: %s' % dict(tipler))
    for vid in onbir:
        if vid in ekle_vid:
            print('   >> 0x11 vid %d, 0x01 ile EKLENMİŞ (bType=%d)'
                  % (vid, ekle_vid[vid]))
            print('      Sunucu bize kendimizi 0x01 ile eklemez —')
            print('      bu vid büyük olasılıkla BAŞKA bir varlık.')
        else:
            print('   >> 0x11 vid %d, 0x01 ile HİÇ eklenmemiş — bize uyar'
                  % vid)
    print()

    # --- 5) sonuç ---
    print('=' * 70)
    if len(onbir) == 1 and not cakisma and not cakisma2 and \
            not (set(onbir) & set(ekle_vid)):
        print('SONUÇ: 0x11 vid\'i (%d) tüm sınavları geçti — BİZ olabilir.'
              % list(onbir)[0])
    else:
        print('SONUÇ: 0x11 GÜVENİLİR DEĞİL. Kendi vid\'imizi başka yoldan')
        print('       bulmalıyız (bkz. tools/kendi_vid_bul.py).')
    print('=' * 70)


if __name__ == '__main__':
    main()
