# -*- coding: utf-8 -*-
"""
Parser'i CANLI ag kosullari altinda test eder.

tcpdump ham TCP gorur: yeniden gonderim (retransmit) ayni baytlari ikinci kez,
kernel buffer tasmasi ise akista DELIK birakir. Cerceveleme tek fazla/eksik
bayta tahammul etmez, bu yuzden PaketServisi.gelenAkisaVer TCP sira numarasina
gore suzer. Bu betik o suzgecin birebir kopyasini calistirip olcer.

Kullanim:
    python tools/parser_canli_test.py
    python tools/parser_canli_test.py log/kendi_yakalamam.pcap
"""
import sys, os, random, struct, collections

_BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BURASI)

from parser_dogrula import (pcap_segmentler, yer_gercegi, boy_yeni,
                            alan_gecerli, u16le)

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

SEQ0 = 500000


class Ayristirici:
    """PaketAyristirici.besle birebir kopyasi (cozulmus opcode tablosu)."""

    def __init__(self):
        self.kuyruk = b''
        self.taban = 0
        self.olaylar = []
        self.tarama = []
        self.atlanan = 0

    def _tara(self, d, bas, son, mutlak):
        j = bas
        while j + 38 <= son:
            if d[j] == 0x01 and alan_gecerli(d, j, 0x01) and u16le(d, j + 22) > 0:
                self.tarama.append(mutlak + j)
            j += 1

    def besle(self, b):
        d = self.kuyruk + b
        n = len(d); i = 0; ab = -1
        mutlak = self.taban
        while i < n:
            boy = boy_yeni(d, i, n, False)
            if boy < 0: break
            if boy == 0:
                if ab < 0: ab = i
                self.atlanan += 1; i += 1; continue
            if ab >= 0:
                self._tara(d, ab, i, mutlak); ab = -1
            self.olaylar.append((mutlak + i, d[i]))
            i += boy
        if ab >= 0:
            self._tara(d, ab, n, mutlak)
        kalan = n - i
        if kalan > 8192:
            i = n - 8192; kalan = 8192
        self.taban = mutlak + i
        self.kuyruk = d[i:n] if kalan else b''

    def besleSifirla(self):
        self.kuyruk = b''


class Servis(Ayristirici):
    """PaketServisi.gelenAkisaVer birebir kopyasi."""

    def __init__(self, seq_takibi=True):
        super().__init__()
        self.seq_takibi = seq_takibi
        self.beklenen = -1
        self.mukerrer_bayt = 0
        self.delik_sayisi = 0

    def ver(self, sira, yuk):
        if not self.seq_takibi:
            self.besle(yuk); return
        n = len(yuk)
        son = (sira + n) & 0xFFFFFFFF
        if self.beklenen < 0:
            self.beklenen = son
            self.taban = sira - SEQ0
            self.besle(yuk); return
        fark = (sira - self.beklenen) & 0xFFFFFFFF
        if fark == 0:
            self.beklenen = son
            self.besle(yuk); return
        if fark >= 0x80000000:                      # sira < beklenen: mukerrer
            ustuste = (self.beklenen - sira) & 0xFFFFFFFF
            if ustuste >= n:
                self.mukerrer_bayt += n; return     # tamamen gorulmus
            self.mukerrer_bayt += ustuste
            self.beklenen = son
            self.besle(yuk[ustuste:]); return
        # fark > 0: akista delik. Kuyruktaki yarim mesaj tamamlanamaz.
        self.delik_sayisi += 1
        self.besleSifirla()
        self.taban = sira - SEQ0
        self.beklenen = son
        self.besle(yuk)


def olc(p, g1, g2, g3):
    b1 = {q for q, op in p.olaylar if op == 0x01} | set(p.tarama)
    b2 = {q for q, op in p.olaylar if op == 0x02}
    b3 = {q for q, op in p.olaylar if op == 0x03}
    return len(b1 & g1), len(b2 & g2), len(b3 & g3)


def kosul_calistir(segs, g1, g2, g3, seq_takibi, retr, dus, tohum=11):
    random.seed(tohum)
    p = Servis(seq_takibi)
    seq = SEQ0; dusen = 0
    for s in segs:
        if retr and random.random() < retr:
            p.ver(seq, s)                            # yeniden gonderim
        if dus and random.random() < dus:
            dusen += len(s)                          # tcpdump dusurdu
        else:
            p.ver(seq, s)
        seq = (seq + len(s)) & 0xFFFFFFFF
    a, b, c = olc(p, g1, g2, g3)
    return a, b, c, dusen, p


def dosya_test(yol):
    segs = pcap_segmentler(yol)
    if not segs:
        print('  %s: gelen segment yok' % os.path.basename(yol)); return
    akis = b''.join(segs)
    gt = yer_gercegi(akis)
    g1 = {q for q, op, _ in gt if op == 0x01}
    g2 = {q for q, op, _ in gt if op == 0x02}
    g3 = {q for q, op, _ in gt if op == 0x03}

    print('=' * 84)
    print('%s  |  %d bayt, %d segment' % (os.path.basename(yol), len(akis), len(segs)))
    print('  yer gercegi: dogus(0x01)=%d  olum(0x02)=%d  hareket(0x03)=%d'
          % (len(g1), len(g2), len(g3)))
    print('=' * 84)

    kosullar = [
        ('temiz akis',            0.00, 0.00),
        ('%1 retransmit',         0.01, 0.00),
        ('%5 retransmit',         0.05, 0.00),
        ('%15 retransmit',        0.15, 0.00),
        ('%2 segment kaybi',      0.00, 0.02),
        ('%5 retr + %2 kayip',    0.05, 0.02),
    ]
    print('  %-20s | %-28s | %s' % ('kosul', 'SEQ TAKIBI YOK (eski)', 'SEQ TAKIPLI (simdiki)'))
    print('  ' + '-' * 80)
    for etiket, retr, dus in kosullar:
        a1, b1, c1, dsn, _ = kosul_calistir(segs, g1, g2, g3, False, retr, dus)
        a2, b2, c2, _, p2 = kosul_calistir(segs, g1, g2, g3, True, retr, dus)
        print('  %-20s | dogus %3d olum %3d hrkt %3d | dogus %3d olum %3d hrkt %3d%s'
              % (etiket, a1, b1, c1, a2, b2, c2,
                 ('  (dusen %dB, delik %d)' % (dsn, p2.delik_sayisi)) if dsn else ''))
    print()


def main():
    kok = os.path.dirname(_BURASI)
    if len(sys.argv) > 1:
        dosyalar = sys.argv[1:]
    else:
        logd = os.path.join(kok, 'log')
        dosyalar = [os.path.join(logd, a) for a in sorted(os.listdir(logd))
                    if a.endswith('.pcap')] if os.path.isdir(logd) else []
    if not dosyalar:
        print('pcap bulunamadi. Kullanim: python tools/parser_canli_test.py <dosya.pcap>')
        return
    for y in dosyalar:
        if os.path.exists(y) and os.path.getsize(y) > 100:
            dosya_test(y)
    print('BEKLENEN: retransmit satirlarinda SEQ TAKIPLI sutunu temiz akisla AYNI olmali.')
    print('Segment kaybi satirlarinda yalnizca gercekten dusen baytlardaki paketler eksilir.')


if __name__ == '__main__':
    main()
