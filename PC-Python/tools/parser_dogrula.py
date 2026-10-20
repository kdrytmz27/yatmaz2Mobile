# -*- coding: utf-8 -*-
"""
PAKET SEVIYESINDE kesinlik olcumu.
Yer gercegi = yeni tabloyla tam akis cerceveleme.
Her varyant icin: kac 0x01 yakalandi, kac 0x02 yakalandi, kac YANLIS silme.
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

def pcap_segmentler(yol):
    f = open(yol, 'rb').read()
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24; segs = []
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
        if src == OYUN_IP: segs.append(yuk)
    return segs

# ------- COZULMUS TAM TABLO -------
TABLO = {
    0x01: 38, 0x02: 5, 0x03: 24, 0x0D: 5, 0x0E: 5, 0x11: 14, 0x13: 43,
    0x1B: 5, 0x1F: 30, 0x3E: 9, 0x3F: 14, 0x46: 10, 0x47: 17,
    0x6F: 6, 0x72: 6, 0x87: 10, 0x88: 62, 0xB3: 8,
}
DINAMIK = {0x04: 2000, 0x26: 4096}
TOPLU_KONUM = 0x05   # 05 | u16 wSize | [vid|x|y]*N
YER_ESYA = 0x1A      # 1A | x|y|z|vid|vnum  (21 bayt, GELEN)

def alan_gecerli(d, i, op):
    if op == 0x01:
        return makulId(i32le(d,i+1)) and makulHam(i32le(d,i+9)) and makulHam(i32le(d,i+13))
    if op == 0x03:
        return makulId(i32le(d,i+4)) and makulHam(i32le(d,i+8)) and makulHam(i32le(d,i+12))
    if op in (0x02, 0x0D, 0x0E, 0x1B, 0x11, 0x3F, 0x87, 0x13, 0x6F):
        return makulId(i32le(d,i+1))
    if op == 0x3E:
        a = i32le(d,i+1)
        return (makulId(a) or a == 0) and makulId(i32le(d,i+5))
    if op == 0x46:
        return makulId(i32le(d,i+2)) and makulId(i32le(d,i+6))
    if op == 0x47:
        return makulId(i32le(d,i+1)) and makulId(i32le(d,i+5))
    if op == 0x88 or op == 0x1F:
        c = d[i+5]
        return makulId(i32le(d,i+1)) and 32 <= c <= 126
    return True

def boy_yeni(d, i, n, heuristik):
    kalan = n - i; op = d[i]
    if op in TABLO:
        b = TABLO[op]
        if kalan < b: return -1
        if not alan_gecerli(d, i, op): return 0
        return b
    if op == YER_ESYA:
        if kalan < 21: return -1
        if i32le(d, i+9) != 0: return 0
        if not (0 < i32le(d,i+1) < 30_000_000): return 0
        if not (0 < i32le(d,i+5) < 30_000_000): return 0
        if not makulId(i32le(d,i+13)): return 0
        vn = i32le(d,i+17)
        if vn <= 0 or vn > 100000: return 0
        return 21
    if op == TOPLU_KONUM:
        if kalan < 3: return -1
        b = u16le(d, i+1)
        govde = b - 3
        if govde <= 0 or govde % 12 != 0 or b > 1500: return 0
        if kalan < b: return -1
        for k in range(i+3, i+b, 12):
            if not makulId(i32le(d,k)): return 0
            if not (0 < i32le(d,k+4) < 30_000_000): return 0
            if not (0 < i32le(d,k+8) < 30_000_000): return 0
        return b
    if op in DINAMIK:
        if kalan < 4: return -1
        b = u16le(d, i+1)
        if not (4 <= b <= DINAMIK[op]): return 0
        # 0x26: alt baslik makul olmali (0=liste, 1/2=kapat). Gevsek kural
        # kilobaytlik bloklari yutuyordu.
        if op == 0x26 and d[i+3] > 0x0F: return 0
        if kalan < b: return -1
        return b
    if heuristik and kalan >= 3:
        t = u16le(d, i+1)
        if 4 <= t <= 2048:
            if kalan < t: return -1
            return t
    return 0

def boy_eski(d, i, n):
    """MEVCUT KOD: sadece 8 opcode + length-prefix heuristigi."""
    kalan = n - i; op = d[i]
    if op == 0x01:
        if kalan < 38: return -1
        if not alan_gecerli(d,i,op): return 0
        return 38
    if op == 0x02:
        if kalan < 5: return -1
        if not makulId(i32le(d,i+1)): return 0
        return 5
    if op == 0x03:
        if kalan < 24: return -1
        if not alan_gecerli(d,i,op): return 0
        return 24
    if op == 0x04:
        if kalan < 3: return -1
        b = u16le(d,i+1)
        if not (4 <= b <= 2000): return 0
        if kalan < b: return -1
        return b
    if op == 0x11:
        if kalan < 14: return -1
        if not makulId(i32le(d,i+1)): return 0
        return 14
    if op == 0x26:
        if kalan < 3: return -1
        b = u16le(d,i+1)
        if not (4 <= b <= 32000): return 0
        if kalan < b: return -1
        return b
    if op == 0x1A:
        if kalan < 5: return -1
        return 5
    if op == 0xB3:
        if kalan < 8: return -1
        return 8
    if kalan >= 3:
        t = u16le(d, i+1)
        if 4 <= t <= 2048 and kalan >= t: return t
    return 0


def yer_gercegi(akis):
    """Tam akisi yeni tabloyla cerceveler -> (pozisyon, opcode) olay listesi."""
    n = len(akis); o = 0; olaylar = []
    while o < n:
        b = boy_yeni(akis, o, n, False)
        if b < 0: break
        if b == 0: o += 1; continue
        olaylar.append((o, akis[o], b))
        o += b
    return olaylar


class Sim:
    def __init__(self, mod, tam_tarama, del_lookahead=False):
        self.mod = mod; self.tam_tarama = tam_tarama; self.del_la = del_lookahead
        self.kuyruk = b''; self.taban = 0
        self.olaylar = []          # (mutlak_pozisyon, opcode)
        self.tarama_dogus = []     # taramayla bulunan 0x01 pozisyonlari
        self.atlanan = 0
        self.heuristik_bayt = 0

    def boy(self, d, i, n):
        if self.mod == 'eski':  return boy_eski(d, i, n)
        if self.mod == 'yeni':  return boy_yeni(d, i, n, False)
        if self.mod == 'yeni_h': return boy_yeni(d, i, n, True)

    def tara(self, d, bas, son, mutlak):
        j = bas
        while j + 38 <= son:
            if d[j] == 0x01 and alan_gecerli(d, j, 0x01) and u16le(d, j+22) > 0:
                self.tarama_dogus.append(mutlak + j)
            j += 1

    def besle(self, b):
        d = self.kuyruk + b; n = len(d); i = 0; ab = -1
        mutlak = self.taban          # d[0]'in akistaki mutlak konumu
        while i < n:
            boy = self.boy(d, i, n)
            if boy < 0: break
            if boy == 0:
                if ab < 0: ab = i
                self.atlanan += 1; i += 1; continue
            if ab >= 0:
                self.tara(d, ab, i, mutlak); ab = -1
            op = d[i]
            if self.mod in ('eski', 'yeni_h') and op not in TABLO and op not in DINAMIK:
                self.heuristik_bayt += boy
            # 0x02 lookahead varyanti
            if self.del_la and op == 0x02:
                if i + 5 < n and d[i+5] not in TABLO and d[i+5] not in DINAMIK:
                    self.atlanan += 1; i += 1
                    if ab < 0: ab = i - 1
                    continue
            self.olaylar.append((mutlak + i, op))
            i += boy
        if ab >= 0: self.tara(d, ab, n, mutlak)
        if self.tam_tarama: self.tara(d, 0, n, mutlak)
        kalan = n - i
        if kalan > 8192: i = n - 8192; kalan = 8192
        self.taban = mutlak + i
        self.kuyruk = d[i:n] if kalan else b''


def main():
    kok = r'C:\Users\Abdulkadir\romia2BOT\log'
    for ad in ['r2_20260823_012800.pcap', 'r2_20260822_202956.pcap',
               'r2_20260821_230523.pcap', 'ornek_bekleme.pcap']:
        y = os.path.join(kok, ad)
        if not os.path.exists(y): continue
        segs = pcap_segmentler(y)
        if not segs: continue
        akis = b''.join(segs)
        gt = yer_gercegi(akis)
        gt_pos = {(p, op) for p, op, _ in gt}
        gt_01 = {p for p, op, _ in gt if op == 0x01}
        gt_02 = {p for p, op, _ in gt if op == 0x02}
        gt_03 = {p for p, op, _ in gt if op == 0x03}

        print('=' * 78)
        print('%s  %d bayt | YER GERCEGI: %d mesaj (0x01=%d, 0x02=%d, 0x03=%d)'
              % (ad, len(akis), len(gt), len(gt_01), len(gt_02), len(gt_03)))
        print('=' * 78)

        varyantlar = [
            ('MEVCUT KOD (eski tablo + heuristik + tam tarama)', 'eski',   True,  False),
            ('YENI tablo + heuristik + tam tarama',              'yeni_h', True,  False),
            ('YENI tablo, heuristik YOK, tam tarama',            'yeni',   True,  False),
            ('YENI tablo, heuristik YOK, tarama sadece atlanan', 'yeni',   False, False),
            ('YENI tablo, heuristik YOK, tam tarama + 0x02 LA',  'yeni',   True,  True),
        ]
        for etiket, mod, tam, la in varyantlar:
            s = Sim(mod, tam, la)
            for seg in segs: s.besle(seg)
            bulunan = set(s.olaylar)
            b01 = {p for p, op in s.olaylar if op == 0x01} | set(s.tarama_dogus)
            b02 = {p for p, op in s.olaylar if op == 0x02}
            b03 = {p for p, op in s.olaylar if op == 0x03}
            # hayalet = yer gercekliginde olmayan olay
            hayalet = bulunan - gt_pos
            h02 = {p for p, op in hayalet if op == 0x02}
            print('\n  --- %s ---' % etiket)
            print('    0x01 DOGUS  : %3d/%3d  (%%%.1f)  kacan: %d'
                  % (len(b01 & gt_01), len(gt_01), 100*len(b01 & gt_01)/max(1,len(gt_01)),
                     len(gt_01 - b01)))
            print('    0x02 OLUM   : %3d/%3d  (%%%.1f)  kacan: %d'
                  % (len(b02 & gt_02), len(gt_02), 100*len(b02 & gt_02)/max(1,len(gt_02)),
                     len(gt_02 - b02)))
            print('    0x03 HAREKET: %3d/%3d  (%%%.1f)'
                  % (len(b03 & gt_03), len(gt_03), 100*len(b03 & gt_03)/max(1,len(gt_03))))
            print('    HAYALET olay: %3d   (bunlarin %d tanesi SAHTE 0x02 = yanlis silme)'
                  % (len(hayalet), len(h02)))
            print('    atlanan bayt: %3d   heuristigin yuttugu: %d bayt'
                  % (s.atlanan, s.heuristik_bayt))
        print()

if __name__ == '__main__':
    main()

def pcap_akislar(yol):
    """
    Her TCP baglantisini AYRI dondurur: {(sport,dport): bayt_akisi}

    Kanal/harita degisiminde oyun YENI bir TCP baglantisi acar. Iki
    baglantinin baytlarini birlestirmek cerceveleme sinirlarini bozar,
    bu yuzden akislar ayri islenmelidir. Mukerrer (retransmit) segmentler
    de burada elenir.
    """
    import collections as _c
    f = open(yol, 'rb').read()
    if len(f) < 24: return {}
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    ham = _c.defaultdict(list)
    while o + 16 <= len(f):
        _, _, cap, _ = struct.unpack_from(end + 'IIII', f, o); o += 16
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
        ham[(sp, dp)].append((seq, yuk))
    akislar = {}
    for anahtar, paketler in ham.items():
        paketler.sort(key=lambda x: x[0])
        parcalar = []; beklenen = None
        for seq, yuk in paketler:
            if beklenen is not None:
                fark = (seq - beklenen) & 0xFFFFFFFF
                if fark >= 0x80000000:
                    ust = (beklenen - seq) & 0xFFFFFFFF
                    if ust >= len(yuk): continue
                    yuk = yuk[ust:]; seq = beklenen
            parcalar.append(yuk)
            beklenen = (seq + len(yuk)) & 0xFFFFFFFF
        akislar[anahtar] = b''.join(parcalar)
    return akislar
