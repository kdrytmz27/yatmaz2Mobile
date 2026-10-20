# -*- coding: utf-8 -*-
"""
Bilinmeyen opcode uzunluklarini VERIDEN cozer.

Yontem: 0x01/0x02/0x03/0x04/0x11 paketleri guclu alan dogrulamasi sayesinde
"capa" (anchor) olarak guvenilir. Iki capa arasinda kalan bilinmeyen bolgeyi,
o bolgenin basindaki opcode'un uzunlugu olarak aday toplariz. Cok sayida
ornek uzerinde ayni opcode hep ayni uzunluga cikiyorsa -> o uzunluk dogrudur.
"""
import struct, sys, os, collections

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'

def i32le(b, o): return struct.unpack_from('<i', b, o)[0]
def u16le(b, o): return b[o] | (b[o+1] << 8)
def makulId(i):  return 0 < i < 100_000_000
def makulHam(v): return 0 < v < 30_000_000

def pcap_akis(yol):
    f = open(yol, 'rb').read()
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    gelen = bytearray()
    while o + 16 <= len(f):
        _, _, cap, _ = struct.unpack_from(end + 'IIII', f, o); o += 16
        pkt = f[o:o + cap]; o += cap
        if len(pkt) < lh + 40: continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6: continue
        tcp = ip + (pkt[ip] & 0xF) * 4
        yuk = pkt[tcp + (((pkt[tcp + 12] >> 4) & 0xF) * 4):cap]
        if not yuk: continue
        src = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if src == OYUN_IP:
            gelen += yuk
    return bytes(gelen)


def capa_mi(d, o):
    """o konumunda GUCLU dogrulanmis bir capa paketi var mi? (boy, ad) doner."""
    n = len(d)
    if o >= n: return None
    op = d[o]
    if op == 0x01 and o + 38 <= n:
        vid = i32le(d, o+1); x = i32le(d, o+9); y = i32le(d, o+13)
        vnum = u16le(d, o+22); z = i32le(d, o+17)
        # cok siki: vnum makul aralikta, z=0, tip<16
        if makulId(vid) and makulHam(x) and makulHam(y) and 0 < vnum < 60000 \
           and z == 0 and d[o+21] < 16:
            return (38, '0x01 ADD')
    if op == 0x03 and o + 24 <= n:
        vid = i32le(d, o+4); x = i32le(d, o+8); y = i32le(d, o+12)
        if makulId(vid) and makulHam(x) and makulHam(y) and d[o+1] == 0 and d[o+2] == 0:
            return (24, '0x03 MOVE')
    if op == 0x04 and o + 3 <= n:
        boy = u16le(d, o+1)
        if 4 <= boy <= 2000 and o + boy <= n and d[o+3] < 32:
            return (boy, '0x04 CHAT')
    if op == 0x11 and o + 14 <= n:
        vid = i32le(d, o+1)
        if makulId(vid):
            return (14, '0x11 TICK')
    if op == 0x02 and o + 5 <= n:
        vid = i32le(d, o+1)
        if makulId(vid):
            return (5, '0x02 DEL')
    return None


def bosluk_topla(d):
    """
    Akisi capalarla yuru. Capa bulunamayan her noktada:
    - o noktadaki opcode'u kaydet
    - bir sonraki GUVENLI capaya kadar olan mesafeyi aday uzunluk say
    """
    n = len(d)
    o = 0
    adaylar = collections.defaultdict(collections.Counter)
    capa_say = collections.Counter()
    bosluk_bayt = 0
    while o < n:
        c = capa_mi(d, o)
        if c:
            capa_say[c[1]] += 1
            o += c[0]
            continue
        # bilinmeyen: bir sonraki capayi ara
        op = d[o]
        ileri = o + 1
        while ileri < n and not capa_mi(d, ileri):
            ileri += 1
        mesafe = ileri - o
        if ileri < n and 2 <= mesafe <= 300:
            adaylar[op][mesafe] += 1
        bosluk_bayt += mesafe
        o = ileri
    return adaylar, capa_say, bosluk_bayt


def main():
    kok = r'C:\Users\Abdulkadir\romia2BOT\log'
    dosyalar = [
        'r2_20260823_012800.pcap',
        'r2_20260822_202956.pcap',
        'r2_20260821_230523.pcap',
        'ornek_bekleme.pcap',
        'ornek_hareket.pcap',
    ]
    birlesik = collections.defaultdict(collections.Counter)
    toplam_capa = collections.Counter()
    toplam_bayt = 0
    toplam_bosluk = 0
    for ad in dosyalar:
        y = os.path.join(kok, ad)
        if not os.path.exists(y): continue
        d = pcap_akis(y)
        if not d: continue
        toplam_bayt += len(d)
        adaylar, capalar, bosluk = bosluk_topla(d)
        toplam_bosluk += bosluk
        for op, c in adaylar.items():
            birlesik[op].update(c)
        toplam_capa.update(capalar)
        print('%-28s %6d bayt, bosluk %5d (%.1f%%)' % (ad, len(d), bosluk, 100*bosluk/len(d)))

    print('\n=== CAPA SAYILARI ===')
    for k, v in toplam_capa.most_common():
        print('  %-12s %d' % (k, v))
    print('\n  toplam %d bayt, %d bosluk baytı (%.1f%%)' % (toplam_bayt, toplam_bosluk, 100*toplam_bosluk/toplam_bayt))

    print('\n=== BILINMEYEN OPCODE UZUNLUK ADAYLARI ===')
    print('(opcode: en sik mesafe -> kac kez / toplam ornek)')
    kesin = {}
    for op in sorted(birlesik, key=lambda k: -sum(birlesik[k].values())):
        c = birlesik[op]
        toplam = sum(c.values())
        if toplam < 3: continue
        enler = c.most_common(4)
        bas, sayi = enler[0]
        oran = sayi / toplam
        isaret = ''
        if oran >= 0.75 and toplam >= 5:
            kesin[op] = bas
            isaret = '  <== KESIN'
        elif oran >= 0.55 and toplam >= 8:
            kesin[op] = bas
            isaret = '  <== GUCLU'
        print('  0x%02X: toplam %3d | %s%s' % (
            op, toplam,
            ', '.join('%d bayt x%d' % (m, s) for m, s in enler),
            isaret))

    print('\n=== COZULEN TABLO ===')
    print('BILINEN_BOY = {')
    for op in sorted(kesin):
        print('    0x%02X: %d,' % (op, kesin[op]))
    print('}')
    return kesin


if __name__ == '__main__':
    main()
