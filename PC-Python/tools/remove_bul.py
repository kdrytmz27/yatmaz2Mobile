# -*- coding: utf-8 -*-
"""
Entity-remove (varlik-sil) paketi bulucu — offline pcap analizi (v2).

YONTEM (v1'den daha ayirt edici):
  Bir varlik olunce/gorusten cikinca sunucu son bir kez onun VID'ini gecirir
  (remove paketi) ve o VID akista BIR DAHA gecmez. Yani:
    1. bilinen VID'leri topla (0x01 dogus, 0x03 hareket)
    2. her VID'in akistaki TUM gecislerini bul
    3. "kaybolan" VID = son gecisi, akisin sonundan cok once olan VID
       (sonrasinda uzun sure hic anilmamis -> gitti/oldu)
    4. kaybolan VID'lerin SON anildigi yerdeki opcode = remove adayi
    5. bu opcode'lari say; baskin olan remove'dur

Kullanim:
    python tools/remove_bul.py log/r2_xxx.pcap

Temiz yakalama:
    - moba yaklas (spawn), sonra UZAKLAS (gorusten ciksin) ya da OLDUR
    - kaybolan VID'ler o an remove paketiyle gecer
"""
import struct, sys, os, collections

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'
BILINEN = {0x01, 0x03, 0x3F, 0x68, 0x07}   # govdesi cozulmus gelen opcode'lar

# Bir VID'in "kaybolmus" sayilmasi icin son gecisinden sonra en az bu kadar
# bayt akis, o VID'i hic anmadan devam etmis olmali.
KAYIP_PENCERE = 1200


def pcap_gelen(yol):
    f = open(yol, 'rb').read()
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    gelen = bytearray()
    while o + 16 <= len(f):
        _, _, cap, _ = struct.unpack_from(end + 'IIII', f, o)
        o += 16
        pkt = f[o:o + cap]; o += cap
        if len(pkt) < lh + 40: continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6: continue
        ihl = (pkt[ip] & 0xF) * 4
        tcp = ip + ihl
        thl = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        yuk = pkt[tcp + thl:cap]
        if not yuk: continue
        src = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if src == OYUN_IP:
            gelen += yuk
    return bytes(gelen)


def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def makul_id(v): return 1000 < v < 100000000
def hexs(b): return ' '.join('%02X' % x for x in b)


def main():
    if len(sys.argv) < 2:
        print("kullanim: python tools/remove_bul.py <pcap>"); return
    d = pcap_gelen(sys.argv[1]); n = len(d)
    print("gelen akis: %d bayt" % n)
    if n < 32: print("akis cok kisa"); return

    # 1) bilinen VID'ler
    vidler = set()
    for i in range(n - 26):
        if d[i] == 0x01:
            v = u32(d, i + 1);  vidler.add(v) if makul_id(v) else None
        elif d[i] == 0x03 and d[i+1] == 0 and d[i+2] == 0:
            v = u32(d, i + 4);  vidler.add(v) if makul_id(v) else None
    print("bilinen VID sayisi: %d" % len(vidler))
    if not vidler: return

    # 2) her VID'in tum gecis ofsetleri
    gecis = collections.defaultdict(list)
    for i in range(n - 3):
        v = u32(d, i)
        if v in vidler:
            gecis[v].append(i)

    # 3) kaybolan VID'ler: son gecisinden sonra >= KAYIP_PENCERE bayt sessizlik
    kayip = []
    for v, off in gecis.items():
        son = off[-1]
        if n - son >= KAYIP_PENCERE:
            kayip.append((son, v))
    kayip.sort()
    print("kaybolan VID sayisi: %d (bu yakalamada gorusten cikan/olen)" % len(kayip))
    if not kayip:
        print("\nKAYBOLAN VID YOK. Bu yakalamada varlik AYRILMAMIS (hep spawn).")
        print("Temiz test: moblara yaklas, sonra UZAKLAS ya da bir mob OLDUR;")
        print("boylece VID'ler kaybolur ve remove paketi gecer. Tekrar yakala.")
        return

    # 4) kaybolan VID'in SON anildigi yerdeki opcode (onceki 1-3 bayt)
    aday = collections.Counter()
    ornekler = collections.defaultdict(list)
    for son, v in kayip:
        for delta in (1, 2, 3):
            if son - delta < 0: continue
            op = d[son - delta]
            if op in BILINEN or op == 0x00: continue
            aday[(op, delta)] += 1
            if len(ornekler[(op, delta)]) < 3:
                bas = max(0, son - delta - 1); bit = min(n, son + 8)
                ornekler[(op, delta)].append("vid=%d  %s" % (v, hexs(d[bas:bit])))

    print("\n=== REMOVE ADAYLARI (kaybolan VID'lerin son anilma opcode'u) ===")
    print("opcode | ofset | kac_kayip_VID | ornekler")
    for (op, delta), adet in aday.most_common(12):
        print("  0x%02X  |  +%d   |  %3d  |  %s" % (op, delta, adet, ornekler[(op,delta)][0]))
        for e in ornekler[(op, delta)][1:]:
            print("        |      |       |  %s" % e)

    print("\nYORUM:")
    print("- En cok kaybolan VID'i 'son anan' opcode = remove'dur.")
    print("- 'ofset +1' (yani OP hemen VID'den once) ve delta baytindan sonra")
    print("  sadece birkac bayt kalan kucuk paket ideal remove desenidir.")
    print("- En ustteki 1-2 satiri Claude'a getir; parser'a ekleriz.")


if __name__ == '__main__':
    main()
