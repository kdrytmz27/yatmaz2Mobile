# -*- coding: utf-8 -*-
"""
Botun trafiği gerçek oyuncununkine benziyor mu? — kaydeder ve KIYASLAR.

NE YAPAR
--------
1. Telefonda tcpdump'ı başlatır (bot çalışmaya devam eder, kapatma!)
2. Kaydı PC'ye çeker
3. Botun GİDEN 0x07 desenini çıkarır
4. Gerçek oyuncunun kaydıyla YAN YANA koyar ve farkları söyler

Kıyas ölçütleri — hepsi 21 Ağu 2026 kaydındaki gerçek oyuncudan:

    paketler arası süre    ortanca 155 ms
    paketler arası mesafe  ortanca  70 ham
    bFunc                  yürürken 1, dururken 0
    bRot                   yol boyunca kararlı (yön değişince değişir)

KULLANIM
--------
    python tools/bot_trafik_kiyas.py            # 60 saniye kaydet
    python tools/bot_trafik_kiyas.py 120        # 120 saniye
    python tools/bot_trafik_kiyas.py --dosya log/x.pcap    # kaydetme, çözümle

ÖNEMLİ
------
Kayıt sırasında BOT ÇALIŞSIN ve rotada gezsin. Sen ekrana DOKUNMA —
yoksa senin hareketin de kayda karışır ve kıyas bozulur.
"""

import os
import re
import subprocess
import sys
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from giden_hareket_deseni import pcap_giden  # noqa: E402
import struct  # noqa: E402

OYUN_IP = '185.128.114.87'
UZAK_YOL = '/sdcard/r2_bot.pcap'
# Gerçek oyuncunun ölçüldüğü kayıt — kıyas ölçütü
OLCUT = os.path.join(_KOK, 'log', 'r2_20260821_230523.pcap')


def adb_bul():
    for a in (os.environ.get('ADB_YOLU'), 'adb',
              os.path.expanduser(
                  r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe'),
              r'C:\Program Files\platform-tools\adb.exe'):
        if not a:
            continue
        try:
            if subprocess.run([a, 'version'], capture_output=True,
                              timeout=10).returncode == 0:
                return a
        except Exception:
            continue
    return None


def kabuk(adb, komut, sure=20):
    try:
        p = subprocess.run([adb, 'shell', komut],
                           capture_output=True, timeout=sure)
        return ((p.stdout or b'') + (p.stderr or b'')).decode('utf-8', 'replace')
    except Exception as e:
        return '<hata: %s>' % e


def arayuz_bul(adb):
    m = re.search(r'\bdev\s+(\S+)',
                  kabuk(adb, "su -c 'ip route get %s'" % OYUN_IP))
    if m:
        return m.group(1)
    cikti = kabuk(adb, "su -c 'ip -o addr show'")
    for aday in ('wlan0', 'wlan1', 'eth0', 'rmnet_data0'):
        if re.search(r'\s%s\b.*inet\s' % re.escape(aday), cikti):
            return aday
    return 'wlan0'


def kaydet(sure):
    adb = adb_bul()
    if not adb:
        print('X adb bulunamadı. ADB_YOLU ortam değişkenini ayarla.')
        return None
    cikti = subprocess.run([adb, 'devices'], capture_output=True,
                           timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in cikti:
        print('X Cihaz bağlı değil:\n%s' % cikti.strip())
        return None
    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor — tcpdump başlatılamaz.')
        return None

    arayuz = arayuz_bul(adb)
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    pcap = os.path.join(_KOK, 'log',
                        'bot_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))

    print('adb    : %s' % adb)
    print('arayüz : %s' % arayuz)
    print()
    print('-' * 70)
    print('  BOT ÇALIŞIYOR OLMALI ve rotada gezmeli.')
    print('  Kayıt boyunca EKRANA DOKUNMA — senin hareketin kıyası bozar.')
    print('-' * 70)
    input('Hazırsan Enter...')

    kabuk(adb, "su -c 'pkill -f r2_bot.pcap'")
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    print()
    print('>>> KAYIT BAŞLADI — %d saniye <<<' % sure)
    # -U şart: onsuz tcpdump tamponda biriktirir, timeout öldürünce kaybolur
    kabuk(adb,
          "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s host %s'"
          % (sure, arayuz, UZAK_YOL, OYUN_IP), sure=sure + 30)
    print('>>> KAYIT BİTTİ <<<')

    subprocess.run([adb, 'pull', UZAK_YOL, pcap],
                   capture_output=True, timeout=90)
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        print('X Kayıt alınamadı ya da boş.')
        return None
    print('kayıt  : %s  (%.1f KB)' % (pcap, os.path.getsize(pcap) / 1024.0))
    return pcap


def desen(yol):
    """(süre_ortanca, mesafe_ortanca, bfunc_dagilim, rot_savrulma, adet)"""
    hareketler = []
    for zaman, yuk in pcap_giden(yol):
        i = 0
        while i + 16 <= len(yuk):
            if yuk[i] != 0x07:
                i += 1
                continue
            x = struct.unpack_from('<i', yuk, i + 4)[0]
            y = struct.unpack_from('<i', yuk, i + 8)[0]
            if not (10000 < x < 2000000 and 10000 < y < 2000000):
                i += 1
                continue
            hareketler.append((zaman, yuk[i + 1], yuk[i + 3], x, y))
            i += 16
    if len(hareketler) < 3:
        return None

    sureler, mesafeler, savrulma = [], [], []
    fdag = {}
    for k, (z, f, r, x, y) in enumerate(hareketler):
        fdag[f] = fdag.get(f, 0) + 1
        if k == 0:
            continue
        pz, _, pr, px, py = hareketler[k - 1]
        dt = (z - pz) / 1000.0
        if dt > 3000:            # yürüyüş arası mola — desene dahil etme
            continue
        sureler.append(dt)
        mesafeler.append(((x - px) ** 2 + (y - py) ** 2) ** 0.5)
        d = abs(r - pr) % 72
        savrulma.append(min(d, 72 - d))

    if not sureler:
        return None
    sureler.sort()
    mesafeler.sort()
    savrulma.sort()
    return (sureler[len(sureler) // 2],
            mesafeler[len(mesafeler) // 2],
            fdag,
            savrulma[len(savrulma) // 2],
            sum(savrulma) / len(savrulma),
            len(hareketler))


def main():
    args = sys.argv[1:]
    if '--dosya' in args:
        pcap = args[args.index('--dosya') + 1]
    else:
        try:
            sure = int(args[0]) if args else 60
        except Exception:
            sure = 60
        print('=' * 70)
        print('BOT TRAFİK KIYASI')
        print('=' * 70)
        pcap = kaydet(sure)
        if not pcap:
            input('\nEnter...')
            return

    bot = desen(pcap)
    if not bot:
        print()
        print('X Kayıtta yeterli GİDEN 0x07 yok.')
        print('  Bot gerçekten yürüyor muydu? "Kuru çalışma" kapalı olmalı,')
        print('  rota gezme açık olmalı.')
        input('\nEnter...')
        return

    olcut = desen(OLCUT) if os.path.exists(OLCUT) else None

    print()
    print('=' * 70)
    print('KIYAS')
    print('=' * 70)
    print('%-26s %-14s %-14s' % ('', 'BOT', 'GERÇEK OYUNCU'))
    print('-' * 70)

    def satir(ad, a, b, bicim='%.0f'):
        print('%-26s %-14s %-14s'
              % (ad, bicim % a, (bicim % b) if b is not None else '-'))

    satir('paket sayısı', bot[5], olcut[5] if olcut else None)
    satir('paketler arası süre (ms)', bot[0], olcut[0] if olcut else None)
    satir('paketler arası mesafe', bot[1], olcut[1] if olcut else None)
    satir('yön savrulması (ortanca)', bot[3], olcut[3] if olcut else None)
    satir('yön savrulması (ortalama)', bot[4], olcut[4] if olcut else None,
          '%.1f')
    print('%-26s %-14s %-14s'
          % ('bFunc dağılımı', str(bot[2]),
             str(olcut[2]) if olcut else '-'))

    print()
    print('-' * 70)
    print('DEĞERLENDİRME')
    sorun = []
    if bot[0] > 400:
        sorun.append('Paketler ÇOK SEYREK (%.0f ms). Gerçek istemci ~155 ms.\n'
                     '   -> Hareket sekmesi "Paket aralığı" değerini düşür.'
                     % bot[0])
    elif bot[0] < 80:
        sorun.append('Paketler ÇOK SIK (%.0f ms). Gereksiz trafik.' % bot[0])
    if bot[1] > 200:
        sorun.append('Adım başına mesafe çok büyük (%.0f ham). Gerçek ~70.\n'
                     '   -> "Yürüme hızı" değerini düşür.' % bot[1])
    if bot[4] > 6:
        sorun.append('YÖN SAVRULUYOR (ortalama %.1f birim = %.0f derece).\n'
                     '   Karakter dışarıdan dönüyor gibi görünür.\n'
                     '   -> tools/yon_bayti_dogrula.py çalıştır.'
                     % (bot[4], bot[4] * 5))
    if 1 not in bot[2]:
        sorun.append('Hiç bFunc=1 (YÜRÜ) paketi yok — gerçek istemcide %95 bu.')

    if sorun:
        for s in sorun:
            print(' ! %s' % s)
    else:
        print(' Bot trafiği gerçek oyuncu desenine uyuyor.')
        print(' Süre, mesafe ve yön kararlılığı ölçüt aralığında.')
    print('=' * 70)
    if '--dosya' not in args:
        input('\nEnter...')


if __name__ == '__main__':
    main()
