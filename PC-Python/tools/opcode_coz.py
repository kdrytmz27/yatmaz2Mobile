# -*- coding: utf-8 -*-
"""
Opcode uzunluk cozucu + tam cerceve dokumu.

Bilinen opcode'lardan yola cikip bilinmeyenlerin SABIT uzunlugunu
istatistiksel olarak cozer:
  - her opcode ondan sonra hangi baytin (sonraki opcode) geldigine bakariz.
  - bir opcode SABIT boyluysa, "sonraki opcode" hep gecerli bir opcode olur.
  - dogru L'yi bulmak icin: opcode X'in her gorunumunden L bayt sonrasindaki
    baytin BILINEN opcode olma oranini L=2..40 icin dener; en tutarli L kazanir.

Kullanim: python tools/opcode_coz.py log/xxx.pcap
"""
import struct, sys, os, collections

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'
SABIT = {0x03: 24, 0x11: 14, 0x02: 5}   # dogrulanmis sabit boylular
DINAMIK = {0x04}                          # opcode(1)+u16le toplamBoy


def pcap_oku(yol):
    f = open(yol, 'rb').read()
    magic = f[:4]
    le = magic in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    gelen, giden = bytearray(), bytearray()
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
        (gelen if src == OYUN_IP else giden).__iadd__(yuk)
    return bytes(gelen), bytes(giden), link


def coz_uzunluk(d, bilinen):
    """Bilinmeyen her opcode icin en olasi SABIT uzunlugu tahmin et."""
    yerler = collections.defaultdict(list)
    for i, b in enumerate(d):
        yerler[b].append(i)
    tahmin = {}
    for op, idx in sorted(yerler.items(), key=lambda kv: -len(kv[1])):
        if op in bilinen or len(idx) < 3:
            continue
        en_iyi = (0.0, None)
        for L in range(2, 48):
            uygun = topla = 0
            for i in idx:
                j = i + L
                if j >= len(d):
                    continue
                topla += 1
                if d[j] in bilinen or d[j] == op:  # sonraki gecerli opcode mu
                    uygun += 1
            if topla >= 3:
                oran = uygun / topla
                if oran > en_iyi[0]:
                    en_iyi = (oran, L)
        tahmin[op] = (len(idx), en_iyi[1], en_iyi[0])
    return tahmin


def dokum(d, ad, bilinen, sinir=1200):
    """Akisi cerceveleyip her mesaji tek satir hex ozetiyle bas."""
    print('\n===== %s tam cerceve dokumu (ilk %d bayt) =====' % (ad, sinir))
    o = 0
    while o < len(d) and o < sinir:
        op = d[o]
        boy = None
        if op in SABIT:
            boy = SABIT[op]
        elif op in DINAMIK and o + 3 <= len(d):
            boy = struct.unpack_from('<H', d, o + 1)[0]
        if boy is None or boy < 2 or o + boy > len(d):
            # bilinmeyen: 24 bayta kadar goster, sonraki bilinen opcode'a atla
            bit = o + 1
            while bit < len(d) and d[bit] not in SABIT and d[bit] not in DINAMIK:
                bit += 1
            govde = d[o:min(bit, o + 28)]
            print('  @%-5d 0x%02X  [?%3d]  %s' % (o, op, bit - o,
                  ' '.join('%02X' % x for x in govde)))
            o = bit
            continue
        govde = d[o:o + min(boy, 28)]
        print('  @%-5d 0x%02X  [%3d]  %s' % (o, op, boy,
              ' '.join('%02X' % x for x in govde)))
        o += boy


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else 'log/r2_20260823_012800.pcap'
    if not os.path.isabs(yol):
        yol = os.path.join(os.path.dirname(__file__), '..', yol)
    gelen, giden, link = pcap_oku(yol)
    print('pcap: %s  (link %d)' % (yol, link))
    print('IN %d bayt / OUT %d bayt' % (len(gelen), len(giden)))

    for ad, akis in (('IN', gelen), ('OUT', giden)):
        if not akis: continue
        print('\n##### %s opcode uzunluk tahmini #####' % ad)
        t = coz_uzunluk(akis, set(SABIT) | DINAMIK)
        for op, (adet, L, oran) in sorted(t.items(), key=lambda kv: -kv[1][0]):
            not_ = ''
            if oran >= 0.9: not_ = 'SABIT?'
            elif oran >= 0.6: not_ = 'belki'
            print('  0x%02X  %4d kez  ->  uzunluk %s  (tutarlilik %.0f%%) %s'
                  % (op, adet, L, 100 * oran, not_))

    dokum(gelen, 'IN', set(SABIT) | DINAMIK, 1400)
    dokum(giden, 'OUT', set(SABIT) | DINAMIK, 700)
    return 0


if __name__ == '__main__':
    sys.exit(main())
