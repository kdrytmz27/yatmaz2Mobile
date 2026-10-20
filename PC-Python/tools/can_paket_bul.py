# -*- coding: utf-8 -*-
"""
KENDİ CANIMIZIN geldiği paketi bulur.

0x3F CAN paketi hedef/canavar can barı içindir; kendi HP'miz ordan gelmiyor.
Kendi HP büyük ihtimalle 0x87 PUAN (87|vid|tip|değer) ya da 0x11 kendi-durum
paketiyle geliyor ama parser bunları decode etmiyor. Bu araç GELEN akışı
yakalayıp, HP'nin hangi pakette/alanda olduğunu bulur.

KULLANIM
--------
    python tools/can_paket_bul.py 2223         # 2223 = azami canın (HP bar sağ)
    python tools/can_paket_bul.py 2223 --sure 30
    python tools/can_paket_bul.py 2223 --pcap log/xxx.pcap   # mevcut kaydı analiz

KAYIT SIRASINDA (yakalarken)
----------------------------
  • Botu KAPAT, hareketsiz dur.
  • Bir-iki canavarın seni DÖVMESİNE izin ver (HP düşsün), sonra beklet (HP dolsun).
  • Amaç: HP'nin DEĞİŞMESİ — böylece HP taşıyan alan ayırt edilir.
"""

import os
import re
import struct
import subprocess
import sys
import time

OYUN_IP = '185.128.114.87'
UZAK = '/sdcard/r2_can.pcap'
_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass


def adb_bul():
    for a in ('adb', os.path.expanduser(r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe')):
        try:
            subprocess.run([a, 'version'], capture_output=True, timeout=10)
            return a
        except Exception:
            continue
    return None


def kabuk(adb, komut, sure=20):
    try:
        r = subprocess.run([adb, 'shell', komut], capture_output=True, timeout=sure)
        return r.stdout.decode('utf-8', 'replace')
    except Exception:
        return ''


def arayuz_bul(adb):
    cikti = kabuk(adb, "ip -o addr")
    for aday in ('wlan0', 'wlan1', 'eth0', 'rmnet_data0'):
        if re.search(r'\s%s\b.*inet\s' % re.escape(aday), cikti):
            return aday
    return 'wlan0'


def gelen_segmentler(yol):
    """Oyun sunucusundan GELEN her TCP segmenti: (zaman, yük)."""
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
        if len(pkt) < lh + 40:
            continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6:
            continue
        tcp = ip + (pkt[ip] & 0xF) * 4
        thl = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        yuk = pkt[tcp + thl:cap]
        if not yuk:
            continue
        src = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        if src != OYUN_IP:
            continue
        segs.append((ts + tus / 1e6, bytes(yuk)))
    return segs


def u32(b, o):
    return b[o] | b[o + 1] << 8 | b[o + 2] << 16 | b[o + 3] << 24


def kendi_vid_bul(akis):
    """0x05 GC_SYNC_POSITION: 05 | u16 boy | vid | x | y → ilk vid bizim.
    En sık görülen makul vid'i aday döndürür."""
    from collections import Counter
    say = Counter()
    for p in range(len(akis) - 11):
        if akis[p] != 0x05:
            continue
        vid = u32(akis, p + 3)
        if 0 < vid < 0x3FFFFFFF:
            say[vid] += 1
    return [v for v, _ in say.most_common(5)]


def analiz(pcap, maks_can):
    segs = gelen_segmentler(pcap)
    if not segs:
        print('  GELEN segment yok. IP/arayüz doğru mu? (%s)' % OYUN_IP)
        return
    akis = b''.join(y for _, y in segs)
    print('  %d gelen segment, %d bayt akış' % (len(segs), len(akis)))

    kendi = kendi_vid_bul(akis)
    print('\n[0] KENDİ VİD adayları (0x05 sync): %s' % kendi)
    kset = set(kendi)
    # Kendi vid'imize ait TÜM paketler (0x3F/0x87/0x11) — HP burada olmalı
    print('\n[0b] Kendi vid\'ine ait paketler:')
    bulundu0 = False
    for p in range(len(akis) - 1):
        op = akis[p]
        if op == 0x3F and p + 14 <= len(akis):
            vid = u32(akis, p + 1)
            if vid in kset:
                print('  0x3F vid=%d  can%%=%d can=%d maks=%d'
                      % (vid, akis[p + 5], u32(akis, p + 6), u32(akis, p + 10)))
                bulundu0 = True
        elif op == 0x87 and p + 10 <= len(akis):
            vid = u32(akis, p + 1)
            if vid in kset:
                print('  0x87 vid=%d  tip=%d değer=%d'
                      % (vid, akis[p + 5], u32(akis, p + 6)))
                bulundu0 = True
        elif op == 0x11 and p + 14 <= len(akis):
            vid = u32(akis, p + 1)
            if vid in kset:
                gov = ' '.join('%02X' % x for x in akis[p:p + 14])
                print('  0x11 vid=%d  [%s]' % (vid, gov))
                bulundu0 = True
    if not bulundu0:
        print('  (kendi vid\'ine ait 0x3F/0x87/0x11 bulunamadı — HP az değişmiş olabilir)')

    # 1) 0x87 PUAN taraması: 87 | vid(4) | tip(1) | değer(4)  → (vid,tip) grupla
    print('\n[1] 0x87 PUAN paketleri  (kendi HP en olası burada)')
    gruplar = {}
    for p in range(len(akis) - 9):
        if akis[p] != 0x87:
            continue
        vid = u32(akis, p + 1)
        tip = akis[p + 5]
        deger = u32(akis, p + 6)
        if vid <= 0 or vid > 0x3FFFFFFF or deger > 0x0FFFFFFF:
            continue
        gruplar.setdefault((vid, tip), []).append(deger)
    # HP adayı: değer aralığı azami cana yakın seyreden (vid,tip)
    adaylar = []
    for (vid, tip), ds in gruplar.items():
        enb, enk = max(ds), min(ds)
        yakin = maks_can and enb <= maks_can * 1.2 and enb >= maks_can * 0.5
        adaylar.append((yakin, len(ds), vid, tip, enk, enb, ds))
    adaylar.sort(reverse=True)
    for yakin, n, vid, tip, enk, enb, ds in adaylar[:12]:
        isaret = '  <<< HP ADAYI (azami~%d)' % maks_can if yakin else ''
        ornek = ','.join(str(x) for x in ds[:6])
        print('  vid=%d tip=%d  %d kez  değer %d..%d  [%s]%s'
              % (vid, tip, n, enk, enb, ornek, isaret))

    # 2) maks_can değerini akışta ara (LE u32 / u16) → taşıyan paketi göster
    if maks_can:
        print('\n[2] azami can (%d) baytları akışta nerede geçiyor' % maks_can)
        hedefler = [struct.pack('<I', maks_can), struct.pack('<H', maks_can & 0xFFFF)]
        bulundu = 0
        for hh in hedefler:
            start = 0
            while True:
                q = akis.find(hh, start)
                if q < 0:
                    break
                start = q + 1
                bulundu += 1
                a = max(0, q - 12)
                onc = ' '.join('%02X' % x for x in akis[a:q])
                srs = ' '.join('%02X' % x for x in akis[q:q + 8])
                print('  @%d  ...%s [%s]...' % (q, onc, srs))
                if bulundu > 20:
                    break
            if bulundu > 20:
                break
        if not bulundu:
            print('  bulunamadı — azami can değişmiş olabilir ya da farklı kodlama.')

    # 3) 0x3F kendi vid için var mı (referans)
    print('\n[3] 0x3F CAN paketleri  (maks~azami olan = kendimiz olabilir)')
    say = 0
    for p in range(len(akis) - 13):
        if akis[p] != 0x3F:
            continue
        vid = u32(akis, p + 1); can = u32(akis, p + 6); maks = u32(akis, p + 10)
        if maks <= 0 or can > maks or maks > 100000:
            continue
        if maks_can and abs(maks - maks_can) <= 3:
            print('  vid=%d  can=%d/%d  (%%%d)  <<< AZAMİ EŞLEŞİYOR'
                  % (vid, can, maks, akis[p + 5]))
            say += 1
            if say > 8:
                break


def main():
    args = sys.argv[1:]
    sure = 25
    pcap = None
    if '--sure' in args:
        i = args.index('--sure'); sure = int(args[i + 1]); del args[i:i + 2]
    if '--pcap' in args:
        i = args.index('--pcap'); pcap = args[i + 1]; del args[i:i + 2]
    maks_can = int(args[0]) if args and args[0].isdigit() else 0
    if not maks_can:
        try:
            maks_can = int(input('Azami canın (HP barının sağındaki büyük sayı): ').strip() or '0')
        except Exception:
            maks_can = 0

    if pcap:
        analiz(pcap, maks_can); return

    adb = adb_bul()
    if not adb:
        print('X adb yok'); return
    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor — tcpdump gerek'); return
    arayuz = arayuz_bul(adb)
    logd = os.path.join(_KOK, 'log'); os.makedirs(logd, exist_ok=True)
    pcap = os.path.join(logd, 'can_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s | azami can: %d' % (arayuz, maks_can))
    print('\n>>> Enter: kayıt başlasın. Sonra canavarların seni DÖVSÜN (HP düşsün), sonra beklet (dolsun).')
    input('Hazırsan Enter...')
    kabuk(adb, "su -c 'pkill -f r2_can.pcap'")
    kabuk(adb, "su -c 'rm -f %s'" % UZAK)
    print('>>> KAYIT (%d sn) — canını DÜŞÜR/DOLDUR <<<' % sure)
    kabuk(adb, "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s host %s'"
          % (sure, arayuz, UZAK, OYUN_IP), sure=sure + 30)
    print('>>> BİTTİ <<<')
    subprocess.run([adb, 'pull', UZAK, pcap], capture_output=True, timeout=60)
    kabuk(adb, "su -c 'rm -f %s'" % UZAK)
    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        print('X kayıt boş'); return
    print('kayıt: %s (%.1f KB)\n' % (pcap, os.path.getsize(pcap) / 1024.0))
    print('=' * 66)
    analiz(pcap, maks_can)
    print('=' * 66)
    input('\nKapatmak için Enter...')


if __name__ == '__main__':
    main()
