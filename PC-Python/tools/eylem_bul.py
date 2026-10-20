# -*- coding: utf-8 -*-
"""
Bir EYLEMİN gönderdiği paketi bulur (pelerin bas, eşya kullan, buff aç...).

YÖNTEM
------
Oyun istemcisi her eylemi AYRI bir TCP segmentinde gönderir. 29 Ağu 2026
yakalamasında doğrulandı:

    0x3D /  5 bayt  x1619   hedef seç
    0x07 / 16 bayt  x736    hareket
    0x02 / 21 bayt  x1648   saldırı

Normal oyun bu üçüyle dolu. Dolayısıyla bir eylemi N kez yaparsan, o eyleme
ait (ilk bayt, uzunluk) çifti tam N kez görünen NADİR bir satır olarak
ortaya çıkar.

KULLANIM
--------
    python tools/eylem_bul.py <eylem.pcap>
    python tools/eylem_bul.py <eylem.pcap> --baz <bos.pcap>
    python tools/eylem_bul.py <eylem.pcap> --kez 5

  --baz  : boşta çekilmiş bir kayıt; onda da olan her şey elenir
  --kez  : eylemi kaç kez yaptığın; o sayıya yakın çıkanlar işaretlenir
"""

import struct
import sys
import os
import collections

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'

# Normal oyunda sürekli akan, eylem OLMAYAN paketler
GURULTU = {
    (0x02, 21): 'saldırı',
    (0x02, 6):  'saldırı (kısa)',
    (0x3D, 5):  'hedef seç',
    (0x07, 16): 'hareket',
    (0x07, 32): 'hareket (çift)',
    (0x0F, 5):  'eşya topla',
}


def giden_segmentler(yol):
    """Oyun sunucusuna GİDEN her TCP segmenti: (zaman, yük)."""
    f = open(yol, 'rb').read()
    if len(f) < 24:
        return []
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    segs = []
    while o + 16 <= len(f):
        ts, tus, cap, _ = struct.unpack_from(end + 'IIII', f, o); o += 16
        pkt = f[o:o + cap]; o += cap
        if len(pkt) < lh + 40: continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6: continue
        tcp = ip + (pkt[ip] & 0xF) * 4
        thl = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        yuk = pkt[tcp + thl:cap]
        if not yuk: continue
        dst = '.'.join(str(b) for b in pkt[ip + 16:ip + 20])
        if dst != OYUN_IP: continue
        segs.append((ts + tus / 1e6, bytes(yuk)))
    return segs


def hx(b, n=32):
    s = ' '.join('%02X' % x for x in b[:n])
    return s + (' ...' if len(b) > n else '')


def asc(b, n=32):
    return ''.join(chr(x) if 32 <= x < 127 else '.' for x in b[:n])


def analiz(yol, baz_yol=None, kez=None):
    segs = giden_segmentler(yol)
    if not segs:
        print('  Bu kayıtta oyun sunucusuna GİDEN veri yok.')
        print('  Oyun açık mıydı? Doğru IP mi? (%s)' % OYUN_IP)
        return

    t0 = segs[0][0]
    sure = segs[-1][0] - t0

    print('=' * 74)
    print('EYLEM ANALİZİ: %s' % os.path.basename(yol))
    print('=' * 74)
    print('  %d giden segment, %.0f saniye' % (len(segs), sure))

    # baz kayıttaki çiftler elenecek
    baz_cift = set()
    if baz_yol:
        for _, y in giden_segmentler(baz_yol):
            baz_cift.add((y[0], len(y)))
        print('  baz kayıt: %s (%d farklı çift elenecek)'
              % (os.path.basename(baz_yol), len(baz_cift)))

    gruplar = collections.defaultdict(list)
    for t, y in segs:
        gruplar[(y[0], len(y))].append((t - t0, y))

    # --- gürültü ---
    print('\n[1] BİLİNEN TRAFİK (elendi)')
    for anahtar in sorted(gruplar, key=lambda k: -len(gruplar[k])):
        if anahtar in GURULTU:
            print('    0x%02X / %-4d bayt  x%-5d  %s'
                  % (anahtar[0], anahtar[1], len(gruplar[anahtar]),
                     GURULTU[anahtar]))

    # --- adaylar ---
    adaylar = []
    for anahtar, olaylar in gruplar.items():
        if anahtar in GURULTU:
            continue
        if anahtar in baz_cift:
            continue
        adaylar.append((anahtar, olaylar))

    if not adaylar:
        print('\n[2] ADAY YOK')
        print('    Eylem sırasında yeni bir paket türü görülmedi.')
        print('    • Eylemi kayıt SÜRESİ İÇİNDE yaptığından emin ol')
        print('    • --baz verdiysen, eylem baz kayıtta da olmuş olabilir')
        return

    # eylem sayısına yakınlık puanı
    def puan(item):
        (_, _), olaylar = item[0], item[1]
        n = len(olaylar)
        if kez:
            return (abs(n - kez), n)
        return (0 if n <= 20 else 1, n)

    adaylar.sort(key=puan)

    print('\n[2] ADAY PAKETLER  (eylemin gönderdiği bunlardan biri)')
    if kez:
        print('    "%d kez yaptım" dedin — o sayıya en yakınlar üstte.\n' % kez)
    for (op, boy), olaylar in adaylar[:12]:
        n = len(olaylar)
        isaret = ''
        if kez and n == kez:
            isaret = '   <<< TAM EŞLEŞME'
        elif kez and abs(n - kez) <= 1:
            isaret = '   <<< yakın'
        print('  ┌─ opcode 0x%02X, %d bayt, %d kez%s' % (op, boy, n, isaret))
        for zaman, y in olaylar[:6]:
            print('  │  t=%6.1fs  %s' % (zaman, hx(y)))
            metin = asc(y)
            if sum(1 for c in metin if c != '.') >= 3:
                print('  │             %s' % metin)
        if n > 6:
            print('  │  ... +%d tekrar' % (n - 6))
        # aynı mı, değişken mi?
        govdeler = {bytes(y) for _, y in olaylar}
        if len(govdeler) == 1:
            print('  │  → gövde HER SEFERİNDE AYNI (sabit paket)')
        else:
            print('  │  → %d farklı gövde (içinde değişen alan var)' % len(govdeler))
            # hangi baytlar değişiyor?
            if boy <= 64 and len(govdeler) > 1:
                ilk = olaylar[0][1]
                degisen = [i for i in range(boy)
                           if any(y[i] != ilk[i] for _, y in olaylar)]
                if degisen:
                    print('  │     değişen ofsetler: %s'
                          % ', '.join('+%d' % i for i in degisen[:16]))
        print('  └─')

    print('\n[3] SONRAKİ ADIM')
    print('    Doğru adayı seçmek için: eylemi FARKLI SAYIDA yapıp tekrar')
    print('    kaydet. İki kayıtta da eylem sayısıyla eşleşen tek çift kalır.')


def main():
    args = [a for a in sys.argv[1:]]
    baz = None
    kez = None
    if '--baz' in args:
        i = args.index('--baz')
        baz = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if '--kez' in args:
        i = args.index('--kez')
        try: kez = int(args[i + 1])
        except Exception: kez = None
        del args[i:i + 2]

    if not args:
        kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logd = os.path.join(kok, 'log')
        if os.path.isdir(logd):
            pcaps = sorted((os.path.join(logd, a) for a in os.listdir(logd)
                            if a.endswith('.pcap')),
                           key=os.path.getmtime, reverse=True)
            if pcaps:
                print('(dosya verilmedi — en yeni kayıt kullanılıyor)\n')
                args = [pcaps[0]]
    if not args:
        print(__doc__)
        return
    for y in args:
        if os.path.exists(y):
            analiz(y, baz, kez)
            print()
        else:
            print('bulunamadı: %s' % y)


if __name__ == '__main__':
    main()
