# -*- coding: utf-8 -*-
"""AKIS BAZLI analiz: her TCP baglantisi ayri cerceveleme."""
import struct, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser_dogrula import boy_yeni, alan_gecerli, i32le, u16le, makulId, TABLO, DINAMIK

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'

def makulHam(v): return 0 < v < 30_000_000


def akislar_oku(yol):
    """(sport,dport) -> seq'e gore SIRALI birlestirilmis bayt akisi."""
    f = open(yol, 'rb').read()
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    ham = collections.defaultdict(list)
    while o + 16 <= len(f):
        ts, tus, cap, _ = struct.unpack_from(end + 'IIII', f, o); o += 16
        pkt = f[o:o + cap]; o += cap
        if len(pkt) < lh + 40: continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6: continue
        tcp = ip + (pkt[ip] & 0xF) * 4
        thl = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        yuk = pkt[tcp + thl:cap]
        src = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if src != OYUN_IP or not yuk: continue
        sp = struct.unpack_from('>H', pkt, tcp)[0]
        dp = struct.unpack_from('>H', pkt, tcp + 2)[0]
        seq = struct.unpack_from('>I', pkt, tcp + 4)[0]
        ham[(sp, dp)].append((seq, ts + tus / 1e6, yuk))

    akislar = {}
    for anahtar, paketler in ham.items():
        paketler.sort(key=lambda x: x[0])          # seq'e gore sirala
        parcalar = []
        beklenen = None
        zamanlar = []
        for seq, t, yuk in paketler:
            if beklenen is not None:
                fark = (seq - beklenen) & 0xFFFFFFFF
                if fark >= 0x80000000:              # mukerrer
                    ust = (beklenen - seq) & 0xFFFFFFFF
                    if ust >= len(yuk): continue
                    yuk = yuk[ust:]
                    seq = beklenen
            parcalar.append(yuk)
            zamanlar.extend([t] * len(yuk))
            beklenen = (seq + len(yuk)) & 0xFFFFFFFF
        akislar[anahtar] = (b''.join(parcalar), zamanlar)
    return akislar


def cerceve(d):
    n = len(d); o = 0
    mesajlar = []; bolgeler = []; bas = None
    while o < n:
        b = boy_yeni(d, o, n, False)
        if b < 0: break
        if b == 0:
            if bas is None: bas = o
            o += 1; continue
        if bas is not None:
            bolgeler.append((bas, o)); bas = None
        mesajlar.append((o, d[o], b))
        o += b
    if bas is not None: bolgeler.append((bas, n))
    return mesajlar, bolgeler


def vidleri_topla(d, mesajlar):
    v = set()
    for p, op, _ in mesajlar:
        if op == 0x01: v.add(i32le(d, p + 1))
        elif op == 0x03: v.add(i32le(d, p + 4))
        elif op == 0x02: v.add(i32le(d, p + 1))
    return v


def toplu_konum_ara(d, vidler, bolgeler):
    """Sabit adimla tekrarlanan (VID,x,y) dizileri."""
    bulgular = []
    for adim in (12, 16, 20, 8):
        for bas, son in bolgeler:
            j = bas
            while j + adim * 2 <= son:
                if i32le(d, j) not in vidler:
                    j += 1; continue
                elemanlar = []; k = j
                while k + adim <= son:
                    v = i32le(d, k)
                    if v not in vidler: break
                    x = i32le(d, k + 4); y = i32le(d, k + 8)
                    if not (makulHam(x) and makulHam(y)): break
                    elemanlar.append((v, x, y)); k += adim
                if len(elemanlar) >= 2:
                    bulgular.append((j, adim, elemanlar)); j = k
                else:
                    j += 1
    return bulgular


def hx(b): return ' '.join('%02X' % x for x in b)


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else \
        r'C:\Users\Abdulkadir\romia2BOT\log\r2_20260829_070117.pcap'
    akislar = akislar_oku(yol)
    print('=' * 78)
    print(os.path.basename(yol))
    print('=' * 78)

    for (sp, dp), (d, zamanlar) in sorted(akislar.items(), key=lambda x: -len(x[1][0])):
        mesajlar, bolgeler = cerceve(d)
        cozulen = sum(m[2] for m in mesajlar)
        atlanan = sum(s - b for b, s in bolgeler)
        sayac = collections.Counter(op for _, op, _ in mesajlar)
        print('\n--- AKIS port %d -> %d : %d bayt ---' % (sp, dp, len(d)))
        print('    cozulen %.1f%%, atlanan %d bayt, %d bolge'
              % (100.0 * cozulen / len(d), atlanan, len(bolgeler)))
        print('    opcode:', {('0x%02X' % k): v for k, v in sayac.most_common()})

        vidler = vidleri_topla(d, mesajlar)
        print('    bilinen VID: %d' % len(vidler))

        # cozulemeyen bolgelerdeki opcode dagilimi
        bas_op = collections.Counter(d[b] for b, s in bolgeler)
        print('    cozulemeyen bolge basi opcode:',
              {('0x%02X' % k): v for k, v in bas_op.most_common(10)})

        # TOPLU KONUM ARAMASI
        bulgular = toplu_konum_ara(d, vidler, bolgeler)
        if bulgular:
            bulgular.sort(key=lambda b: -len(b[2]))
            print('\n    >>> TOPLU KONUM ADAYI: %d bulgu' % len(bulgular))
            for j, adim, elemanlar in bulgular[:6]:
                print('      @%-6d adim=%d eleman=%d' % (j, adim, len(elemanlar)))
                print('        onceki 8 bayt: %s' % hx(d[max(0, j - 8):j]))
                for v, x, y in elemanlar[:4]:
                    print('           vid=%-10d x=%-9d y=%-9d (%.0f,%.0f m)'
                          % (v, x, y, x / 100.0, -y / 100.0))
                for geri in (3, 4, 5, 6):
                    if j - geri >= 0:
                        boy = u16le(d, j - geri + 1)
                        bekle = geri + adim * len(elemanlar)
                        if abs(boy - bekle) <= 3:
                            print('           >> UZUNLUK UYUYOR: op=0x%02X wSize=%d (bekl %d)'
                                  % (d[j - geri], boy, bekle))
        else:
            print('    toplu konum dizisi bulunamadi')

        # en buyuk cozulemeyen bolgeleri dok
        bolgeler.sort(key=lambda x: -(x[1] - x[0]))
        print('\n    en buyuk cozulemeyen bolgeler:')
        for b, s in bolgeler[:6]:
            print('      @%-6d %3d bayt: %s' % (b, s - b, hx(d[b:b + 40])))


if __name__ == '__main__':
    main()
