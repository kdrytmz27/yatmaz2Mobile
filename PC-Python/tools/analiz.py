# -*- coding: utf-8 -*-
"""
Romia2 pcap cozumleyici (PC tarafi).

Kullanim:
    python tools/analiz.py log/r2.pcap
    python tools/analiz.py log/r2.pcap --vnum 8005      # belirli vnum ara

Yapdigi:
  1. pcap -> IN / OUT bayt akislari
  2. bilinen cerceveleme ile mesajlari ayirir (opcode + uzunluk)
  3. bilinmeyen opcode'lari ve cozulemeyen bolgeleri raporlar
  4. imza taramasi ile varlik kayitlarini cikarir ve entities_tr.txt ile adlandirir
"""
import struct, sys, os, collections, io

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OYUN_IP = '185.128.114.87'

# --- dogrulanmis cerceveleme ---
# sabit boylu opcode'lar: {opcode: toplam bayt}
SABIT = {0x03: 24, 0x11: 14}
# uzunluk onekli opcode'lar: opcode(1) + u16le boy  (boy = TOPLAM mesaj boyu)
DINAMIK = {0x04}


def pcap_oku(yol):
    f = open(yol, 'rb').read()
    magic = f[:4]
    le = magic in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    gelen, giden = bytearray(), bytearray()
    n_in = n_out = 0
    while o + 16 <= len(f):
        _, _, cap, _ = struct.unpack_from(end + 'IIII', f, o)
        o += 16
        pkt = f[o:o + cap]
        o += cap
        if len(pkt) < lh + 40:
            continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6:
            continue
        ihl = (pkt[ip] & 0xF) * 4
        tcp = ip + ihl
        thl = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        yuk = pkt[tcp + thl:cap]
        if not yuk:
            continue
        src = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if src == OYUN_IP:
            gelen += yuk; n_in += 1
        else:
            giden += yuk; n_out += 1
    return bytes(gelen), bytes(giden), n_in, n_out, link


def katalog_yukle():
    yol = os.path.join(os.path.dirname(__file__), '..', 'app', 'src', 'main',
                       'assets', 'entities_tr.txt')
    tablo = {}
    if not os.path.exists(yol):
        return tablo
    for satir in open(yol, encoding='utf-8'):
        p = satir.rstrip('\n\r').split('\t')
        if len(p) < 5:
            continue
        try:
            tablo[int(p[0])] = (int(p[1]), int(p[2]), int(p[3]), p[4])
        except ValueError:
            pass
    return tablo


TIP_ADI = {0: 'CANAVAR', 1: 'NPC', 2: 'METIN', 3: 'GECIS', 4: 'KAPI',
           5: 'BINA', 6: 'OYUNCU', 8: 'AT', 9: 'ISARET'}


def cerceveler(d):
    """Akisi mesajlara boler. (ofset, opcode, boy) listesi + cozulemeyen bolgeler."""
    o = 0
    mesajlar = []
    bosluklar = []
    while o < len(d):
        op = d[o]
        boy = None
        if op in SABIT:
            boy = SABIT[op]
        elif op in DINAMIK and o + 3 <= len(d):
            boy = struct.unpack_from('<H', d, o + 1)[0]
        if boy is None or boy < 2 or o + boy > len(d):
            # senkron kayboldu: bilinen bir opcode gorene kadar ilerle
            basla = o
            o += 1
            while o < len(d) and d[o] not in SABIT and d[o] not in DINAMIK:
                o += 1
            bosluklar.append((basla, o - basla))
            continue
        mesajlar.append((o, op, boy))
        o += boy
    return mesajlar, bosluklar


def varlik_tara(d, kat, aranan_vnum=None):
    i32 = lambda o: struct.unpack_from('<i', d, o)[0]
    f32 = lambda o: struct.unpack_from('<f', d, o)[0]
    mid = lambda v: 1000 < v < 100000000
    mham = lambda v: 1000 < v < 10000000

    print('\n--- 0x01 imza taramasi (dogus adayi: id,rot,x,y,vnum) ---')
    n = 0
    for i in range(len(d) - 26):
        if d[i] != 0x01:
            continue
        _id, rot, x, y, vnum = i32(i + 1), f32(i + 5), i32(i + 9), i32(i + 13), i32(i + 22)
        if not (mid(_id) and mham(x) and mham(y) and 0 < vnum < 100000):
            continue
        if not (0 <= rot <= 360):
            continue
        k = kat.get(vnum)
        ad = k[3] if k else 'vnum %d' % vnum
        tip = TIP_ADI.get(k[0], '?') if k else '?'
        print('  @%-6d %-8s %-28s #%-10d %5d,%-6d m' %
              (i, tip, ad, _id, round(x / 100), round(-y / 100)))
        n += 1
    if n == 0:
        print('  eslesme yok - bu yakalamada dogus paketi gecmemis.')
        print('  Ipucu: yakalamayi oyuna GIRMEDEN once baslat veya yeni bir')
        print('         alana yuru; dogus paketleri yalnizca varlik gorus')
        print('         alanina girdiginde gonderilir.')

    print('\n--- 0x03 hareket (id, x, y) ---')
    gorulen = collections.OrderedDict()
    for i in range(len(d) - 24):
        if d[i] != 0x03 or d[i + 1] or d[i + 2]:
            continue
        _id, x, y = i32(i + 4), i32(i + 8), i32(i + 12)
        if mid(_id) and mham(x) and mham(y):
            gorulen[_id] = (round(x / 100), round(-y / 100))
    for _id, (x, y) in list(gorulen.items())[:40]:
        print('  #%-10d %5d,%-6d m' % (_id, x, y))
    print('  toplam %d ayri varlik (vnum tasimiyor -> isim yok)' % len(gorulen))

    if aranan_vnum:
        print('\n--- vnum %d icin ham arama ---' % aranan_vnum)
        hedef = struct.pack('<i', aranan_vnum)
        yer = d.find(hedef)
        adet = 0
        while yer >= 0 and adet < 20:
            print('  @%d  onceki 24 bayt: %s' % (
                yer, ' '.join('%02X' % b for b in d[max(0, yer - 24):yer + 8])))
            yer = d.find(hedef, yer + 1)
            adet += 1
        if adet == 0:
            print('  bulunamadi')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    yol = sys.argv[1]
    aranan = None
    if '--vnum' in sys.argv:
        aranan = int(sys.argv[sys.argv.index('--vnum') + 1])

    gelen, giden, n_in, n_out, link = pcap_oku(yol)
    print('pcap: %s  (link tipi %d)' % (yol, link))
    print('IN  %d segment / %d bayt' % (n_in, len(gelen)))
    print('OUT %d segment / %d bayt' % (n_out, len(giden)))

    for ad, akis in (('IN', gelen), ('OUT', giden)):
        if not akis:
            continue
        mesajlar, bosluklar = cerceveler(akis)
        sayim = collections.Counter(op for _, op, _ in mesajlar)
        cozulen = sum(b for _, _, b in mesajlar)
        print('\n=== %s cerceveleme ===' % ad)
        print('  %d mesaj cozuldu, %d/%d bayt (%.0f%%)' %
              (len(mesajlar), cozulen, len(akis), 100.0 * cozulen / len(akis)))
        print('  opcode sayimlari: %s' %
              {('0x%02X' % k): v for k, v in sayim.most_common()})
        if bosluklar:
            toplam = sum(b for _, b in bosluklar)
            print('  cozulemeyen %d bolge / %d bayt - bilinmeyen opcode boylari'
                  % (len(bosluklar), toplam))
            for o, b in bosluklar[:5]:
                print('    @%-6d %3d bayt: %s' %
                      (o, b, ' '.join('%02X' % x for x in akis[o:o + min(b, 16)])))

    kat = katalog_yukle()
    print('\nkatalog: %d varlik' % len(kat))
    varlik_tara(gelen, kat, aranan)
    return 0


if __name__ == '__main__':
    sys.exit(main())
