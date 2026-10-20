# -*- coding: utf-8 -*-
"""
Bir pcap yakalamasinin ANALIZ ICIN TEMIZ olup olmadigini soyler.

Kirli veriyle opcode cozumlemesi yapmak yanlis sonuc verir: cekirdek paket
dusurduyse akista delik olur, delikten sonraki baytlar yanlis hizalanir ve
"yeni paket bulduk" sandigimiz sey aslinda baska bir paketin ortasidir.

Kontroller:
  1) TCP sira surekliligi  -> delik / yeniden gonderim / sira disi var mi
  2) Cerceveleme kapsami   -> bilinen tabloyla akisin yuzde kaci cozuluyor
  3) Icerik zenginligi     -> dogus/olum/isinlanma var mi (analiz icin gerekli)

Kullanim:  python tools/yakalama_kalite.py log/r2_XXXX.pcap
"""
import struct, sys, os, collections

_BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BURASI)

from parser_dogrula import (pcap_segmentler, yer_gercegi, boy_yeni,
                            TABLO, DINAMIK, i32le, u16le)

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'


def akislari_oku(yol):
    """Her TCP akisi icin (zaman, seq, yuk) listesi."""
    f = open(yol, 'rb').read()
    if len(f) < 24:
        return {}, 0
    le = f[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1')
    end = '<' if le else '>'
    link = struct.unpack_from(end + 'I', f, 20)[0]
    lh = 16 if link == 113 else 14
    o = 24
    akislar = collections.defaultdict(list)
    sure = [None, None]
    while o + 16 <= len(f):
        ts, tus, cap, _ = struct.unpack_from(end + 'IIII', f, o); o += 16
        pkt = f[o:o + cap]; o += cap
        t = ts + tus / 1e6
        if sure[0] is None: sure[0] = t
        sure[1] = t
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
        akislar[(sp, dp)].append((t, seq, yuk))
    toplam_sure = (sure[1] - sure[0]) if sure[0] is not None else 0
    return akislar, toplam_sure


def surekliligi_olc(paketler):
    beklenen = None
    delik = 0; delik_bayt = 0; tekrar = 0; sira_disi = 0
    for _, seq, yuk in paketler:
        n = len(yuk)
        if beklenen is None:
            beklenen = (seq + n) & 0xFFFFFFFF
            continue
        fark = (seq - beklenen) & 0xFFFFFFFF
        if fark == 0:
            pass
        elif fark >= 0x80000000:
            tekrar += 1
            continue
        elif fark < 10_000_000:
            delik += 1; delik_bayt += fark
        else:
            sira_disi += 1
            continue
        beklenen = (seq + n) & 0xFFFFFFFF
    return delik, delik_bayt, tekrar, sira_disi


def rapor(yol):
    ad = os.path.basename(yol)
    boy = os.path.getsize(yol)
    print('=' * 74)
    print('KALITE RAPORU: %s  (%.1f KB)' % (ad, boy / 1024.0))
    print('=' * 74)

    if boy < 200:
        print('  X BOS KAYIT - tcpdump hic paket yakalamadi.')
        print('    Sebep: yanlis arayuz, root izni yok, ya da oyun kapaliydi.')
        return False

    akislar, sure = akislari_oku(yol)
    if not akislar:
        print('  X Oyun sunucusundan (%s) GELEN veri yok.' % OYUN_IP)
        print('    Oyun acik miydi? Dogru IP mi?')
        return False

    print('\n[1] TCP SUREKLILIGI')
    temiz = True
    toplam_bayt = 0
    for (sp, dp), pkts in sorted(akislar.items(), key=lambda x: -len(x[1])):
        if len(pkts) < 3: continue
        bayt = sum(len(y) for _, _, y in pkts)
        toplam_bayt += bayt
        delik, dbayt, tekrar, sd = surekliligi_olc(pkts)
        durum = 'TEMIZ'
        if delik:
            durum = 'DELIKLI'
            temiz = False
        print('    port %-6d %5d segment %7d bayt | delik %d (%d bayt) '
              'tekrar %d sira-disi %d  -> %s'
              % (sp, len(pkts), bayt, delik, dbayt, tekrar, sd, durum))
    if not temiz:
        print('    ! Delik = cekirdek paket dusurdu. -B tamponunu buyutun.')

    print('\n[2] CERCEVELEME KAPSAMI')
    segs = pcap_segmentler(yol)
    akis = b''.join(segs)
    n = len(akis); o = 0; cozulen = 0; atlanan = 0
    sayac = collections.Counter()
    while o < n:
        b = boy_yeni(akis, o, n, False)
        if b < 0: break
        if b == 0:
            atlanan += 1; o += 1; continue
        sayac[akis[o]] += 1
        cozulen += b; o += b
    kapsam = 100.0 * cozulen / n if n else 0
    print('    %d bayt, %.1f%% cozuldu, %d bayt atlandi' % (n, kapsam, atlanan))
    if kapsam < 95:
        print('    ! Kapsam dusuk - ya kayit kirli ya da YENI paket turleri var.')
        bilinmeyen = collections.Counter()
        o = 0
        while o < n:
            b = boy_yeni(akis, o, n, False)
            if b < 0: break
            if b == 0:
                bilinmeyen[akis[o]] += 1; o += 1; continue
            o += b
        print('      cozulemeyen opcode`lar:',
              {('0x%02X' % k): v for k, v in bilinmeyen.most_common(8)})

    print('\n[3] ICERIK (analiz icin gerekli olaylar)')
    gt = yer_gercegi(akis)
    d01 = [p for p, op, _ in gt if op == 0x01]
    d02 = [p for p, op, _ in gt if op == 0x02]
    d03 = [p for p, op, _ in gt if op == 0x03]
    vid01 = {i32le(akis, p + 1) for p in d01}
    print('    sure               : %.0f saniye' % sure)
    print('    dogus  (0x01)      : %d paket, %d benzersiz varlik' % (len(d01), len(vid01)))
    print('    olum   (0x02)      : %d paket' % len(d02))
    print('    hareket(0x03)      : %d paket' % len(d03))
    print('    opcode cesitliligi : %d farkli tur' % len(sayac))

    # toplu dogus var mi? (isinlanma sonrasi cok sayida 0x01 arka arkaya)
    kume = 0; enbuyuk = 0
    for i in range(1, len(d01)):
        if d01[i] - d01[i-1] < 200:
            kume += 1
            enbuyuk = max(enbuyuk, kume)
        else:
            kume = 0
    print('    en buyuk dogus kumesi: %d (isinlanma/harita yuklemesi isareti)' % (enbuyuk + 1 if d01 else 0))

    print('\n' + '-' * 74)
    eksikler = []
    if sure < 60:            eksikler.append('kayit kisa (60+ sn olmali)')
    if len(vid01) < 20:      eksikler.append('az dogus (kalabalik haritaya isinlanin)')
    if len(d02) < 10:        eksikler.append('az olum (canavar oldurun)')
    if enbuyuk < 5:          eksikler.append('toplu dogus yok (ISINLANMA yapin)')
    if not temiz:            eksikler.append('TCP delikleri var (tampon yetersiz)')
    if kapsam < 95:          eksikler.append('cerceve kapsami dusuk')

    if not eksikler:
        print('  SONUC: TEMIZ ve ZENGIN - analiz icin hazir.')
        return True
    print('  SONUC: kullanilabilir ama eksik:')
    for e in eksikler:
        print('    - ' + e)
    return False


def main():
    if len(sys.argv) > 1:
        yollar = sys.argv[1:]
    else:
        logd = os.path.join(os.path.dirname(_BURASI), 'log')
        yollar = [os.path.join(logd, a) for a in sorted(os.listdir(logd))
                  if a.endswith('.pcap')] if os.path.isdir(logd) else []
    if not yollar:
        print('Kullanim: python tools/yakalama_kalite.py <dosya.pcap>')
        return
    for y in yollar:
        if os.path.exists(y):
            rapor(y)
            print()


if __name__ == '__main__':
    main()
