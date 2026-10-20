# -*- coding: utf-8 -*-
"""
TOPLU KONUM paketini arar (GC_SYNC_POSITION / GC_NPC_POSITION adayi).

NEDEN ONEMLI
------------
Bir varlik yalnizca DOGDUGU anda 0x01 CHARACTER_ADD gonderir. Okuyucu oyun
basladiktan sonra aciliyorsa, o sirada sahada duran canavarlar icin 0x01 hic
gelmez; onlari yalnizca hareket ettiklerinde (0x03) gorebiliriz ve 0x03 vnum
tasimadigi icin haritada ISIMSIZ/GRI kalirlar.

Cozum, sunucunun periyodik gonderdigi TOPLU konum paketini cozmek:
    header | u16 wSize | [ dwVID(4) | lX(4) | lY(4) ] x N

NASIL BULUR
-----------
Once akistaki GERCEK varlik VID'lerini 0x01/0x03 paketlerinden ogrenir.
Sonra cozulemeyen bolgelerde, BILINEN VID'lerin sabit bir adimla (stride)
arka arkaya tekrarlandigi yerleri arar. Rastgele baytlarda birden fazla
gercek VID'in duzenli araliklarla art arda gelmesi neredeyse imkansizdir,
bu yuzden esiği gecen her aday guclu bir bulgudur.

Kullanim:  python tools/toplu_konum_ara.py [dosya.pcap ...]
"""
import struct, sys, os, collections

_BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BURASI)

from parser_dogrula import (pcap_segmentler, yer_gercegi, boy_yeni,
                            i32le, u16le, makulId)

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass


def makulHam(v):
    return 0 < v < 30_000_000


def bilinen_vidler(akis):
    """Akistaki gercek varlik VID'leri (0x01 dogus + 0x03 hareket)."""
    vidler = set()
    for p, op, _ in yer_gercegi(akis):
        if op == 0x01: vidler.add(i32le(akis, p + 1))
        elif op == 0x03: vidler.add(i32le(akis, p + 4))
        elif op == 0x02: vidler.add(i32le(akis, p + 1))
    return vidler


def cozulemeyen_bolgeler(akis):
    """Cerceveleme dongusunun atladigi (baslangic, bitis) araliklari."""
    n = len(akis); o = 0
    bolgeler = []; bas = None
    while o < n:
        b = boy_yeni(akis, o, n, False)
        if b < 0: break
        if b == 0:
            if bas is None: bas = o
            o += 1; continue
        if bas is not None:
            bolgeler.append((bas, o)); bas = None
        o += b
    if bas is not None: bolgeler.append((bas, n))
    return bolgeler


def dizi_ara(akis, vidler, bolgeler=None, en_az_eleman=2):
    """
    Sabit adimla tekrarlanan (VID, x, y) dizilerini arar.

    Adim adaylari: 12 (vid+x+y), 16, 20 — sunucuya gore ek alan olabilir.
    """
    n = len(akis)
    aday_araliklar = bolgeler if bolgeler else [(0, n)]
    bulgular = []
    for adim in (12, 16, 20, 8):
        for bas, son in aday_araliklar:
            j = bas
            while j + adim * en_az_eleman <= son:
                vid = i32le(akis, j)
                if vid not in vidler:
                    j += 1; continue
                # bu noktadan itibaren kac eleman zincirleniyor?
                say = 0; k = j
                elemanlar = []
                while k + adim <= son:
                    v = i32le(akis, k)
                    if v not in vidler: break
                    x = i32le(akis, k + 4); y = i32le(akis, k + 8)
                    if not (makulHam(x) and makulHam(y)): break
                    elemanlar.append((v, x, y))
                    say += 1; k += adim
                if say >= en_az_eleman:
                    bulgular.append((j, adim, say, elemanlar))
                    j = k
                else:
                    j += 1
    return bulgular


def hx(b):
    return ' '.join('%02X' % x for x in b)


def dosya_ara(yol):
    segs = pcap_segmentler(yol)
    if not segs:
        return 0
    akis = b''.join(segs)
    vidler = bilinen_vidler(akis)
    bolgeler = cozulemeyen_bolgeler(akis)
    atlanan = sum(s - b for b, s in bolgeler)

    print('=' * 76)
    print('%s  |  %d bayt, %d bilinen VID, %d bayt cozulemeyen'
          % (os.path.basename(yol), len(akis), len(vidler), atlanan))
    print('=' * 76)

    # 1) Once cozulemeyen bolgelerde ara (en olasi yer)
    bulgular = dizi_ara(akis, vidler, bolgeler, en_az_eleman=2)
    # 2) Hicbir sey yoksa TUM akista ara (paket bilinen bir opcode icine gomulmus olabilir)
    nerede = 'cozulemeyen bolgeler'
    if not bulgular:
        bulgular = dizi_ara(akis, vidler, None, en_az_eleman=3)
        nerede = 'tum akis'

    if not bulgular:
        print('  Toplu konum dizisi BULUNAMADI.')
        print('  -> Bu kayitta isinlanma/harita yuklemesi yok olabilir.')
        print('     Kalabalik bir haritaya isinlanarak yeniden kaydedin.')
        return 0

    bulgular.sort(key=lambda b: -b[2])
    print('  %d aday bulundu (%s):\n' % (len(bulgular), nerede))
    for j, adim, say, elemanlar in bulgular[:10]:
        # dizinin ONUNDEKI baytlar = paket basligi
        basla = max(0, j - 6)
        baslik = akis[basla:j]
        print('  @%-6d adim=%-2d eleman=%-2d' % (j, adim, say))
        print('     onceki 6 bayt (baslik adayi): %s' % hx(baslik))
        for v, x, y in elemanlar[:5]:
            print('        vid=%-10d x=%-9d y=%-9d  (%.0f, %.0f m)'
                  % (v, x, y, x / 100.0, -y / 100.0))
        if say > 5:
            print('        ... +%d eleman' % (say - 5))
        # baslik u16 uzunluk tasiyor mu?
        for geri in (3, 4, 5):
            if j - geri >= 0:
                op = akis[j - geri]
                if j - geri + 3 <= len(akis):
                    boy = u16le(akis, j - geri + 1)
                    beklenen = geri + adim * say
                    if abs(boy - beklenen) <= 2:
                        print('        >> UZUNLUK ONEKI UYUYOR: opcode=0x%02X wSize=%d '
                              '(beklenen %d)' % (op, boy, beklenen))
        print()
    return len(bulgular)


def main():
    if len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        logd = os.path.join(os.path.dirname(_BURASI), 'log')
        yollar = [os.path.join(logd, a) for a in sorted(os.listdir(logd))
                  if a.endswith('.pcap')] if os.path.isdir(logd) else []
    toplam = 0
    for y in yollar:
        if os.path.exists(y) and os.path.getsize(y) > 200:
            toplam += dosya_ara(y)
            print()
    if toplam == 0:
        print('Hicbir kayitta toplu konum paketi yok.')
        print('PC_YAKALA.bat ile ISINLANMA iceren yeni bir kayit alin.')


if __name__ == '__main__':
    main()
