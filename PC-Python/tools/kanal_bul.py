# -*- coding: utf-8 -*-
"""
KANAL DEĞİŞTİRME paketini bulur — ve bunun mümkün olup olmadığını söyler.

ÖNEMLİ UYARI
------------
Metin2'de kanallar çoğu zaman AYRI SUNUCULARDIR (ch1/ch2 farklı TCP
portları). Öyleyse kanal değiştirmek tek bir paket enjekte etmekle
olmaz: istemcinin mevcut bağlantıyı kapatıp yenisini açması gerekir.
Bot bunu yapamaz — proxy yalnızca var olan bağlantıya paket yazabilir.

Bu betik önce bunu ÖLÇER: kayıt sırasında yeni bir TCP bağlantısı ya da
yeni bir port görülüyorsa cevap "yapılamaz"dır. Görülmüyorsa kanal
değişimi aynı bağlantı üzerinden bir paketle oluyor demektir ve o paket
bulunabilir.

NASIL ÇALIŞIR
-------------
1. Kayıt başlar
2. Sen oyunda ELLE kanal değiştirirsin (2-3 kez, farklı kanallara)
3. Betik:
   • yeni TCP bağlantısı/port açıldı mı bakar
   • açılmadıysa, giden paketlerde kanal değişimiyle örtüşen NADİR
     opcode'ları arar

KULLANIM
--------
    python tools/kanal_bul.py            # 60 saniye
    python tools/kanal_bul.py --sure 90
    python tools/kanal_bul.py --dosya log/x.pcap    # var olan kaydı çöz
"""

import os
import re
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OYUN_IP = '185.128.114.87'
UZAK_YOL = '/sdcard/r2_kanal.pcap'


# ─────────────────────── kayıt ───────────────────────

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
        pr = subprocess.run([adb, 'shell', komut],
                            capture_output=True, timeout=sure)
        return ((pr.stdout or b'') + (pr.stderr or b'')).decode('utf-8', 'replace')
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
        print('X adb bulunamadı.')
        return None
    cikti = subprocess.run([adb, 'devices'], capture_output=True,
                           timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in cikti:
        print('X Cihaz bağlı değil.')
        return None
    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor.')
        return None

    arayuz = arayuz_bul(adb)
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    pcap = os.path.join(_KOK, 'log',
                        'kanal_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s' % arayuz)
    print()
    print('-' * 68)
    print('  NE YAPACAKSIN')
    print('-' * 68)
    print('  1. Enter\'a bas, kayıt başlasın')
    print('  2. İlk 8 saniye HİÇBİR ŞEY YAPMA')
    print('  3. Oyunda ELLE kanal değiştir — 2-3 kez, farklı kanallara')
    print('  4. Aralarda 5-6 saniye bekle')
    print('  5. Başka bir şey yapma: yürüme, saldırma')
    print('  6. Bot ÇALIŞIYORSA KAPAT')
    print()
    input('Hazırsan Enter...')

    kabuk(adb, "su -c 'pkill -f r2_kanal.pcap'")
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    print()
    print('>>> KAYIT BAŞLADI (%d sn) — şimdi kanal değiştir <<<' % sure)
    # 'host' filtresi YOK: yeni bir SUNUCUYA bağlanılıyorsa onu da görmeliyiz
    kabuk(adb, "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s tcp'"
          % (sure, arayuz, UZAK_YOL), sure=sure + 30)
    print('>>> KAYIT BİTTİ <<<')

    subprocess.run([adb, 'pull', UZAK_YOL, pcap],
                   capture_output=True, timeout=120)
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        print('X Kayıt alınamadı ya da boş.')
        return None
    print('kayıt : %s  (%.1f KB)' % (pcap, os.path.getsize(pcap) / 1024.0))
    return pcap


# ─────────────────────── çözümleme ───────────────────────

def pcap_tcp(yol):
    """(zaman_us, kaynak_ip, kaynak_port, hedef_ip, hedef_port, bayrak, yuk)"""
    ham = open(yol, 'rb').read()
    if len(ham) < 24:
        return []
    en = '<' if ham[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1') else '>'
    baglanti = struct.unpack_from(en + 'I', ham, 20)[0]
    lh = 16 if baglanti == 113 else (14 if baglanti == 1 else 0)
    i = 24
    cikti = []
    while i + 16 <= len(ham):
        sn, us, cap, _ = struct.unpack_from(en + 'IIII', ham, i)
        i += 16
        pkt = ham[i:i + cap]
        i += cap
        if len(pkt) < lh + 40:
            continue
        ip = lh
        if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6:
            continue
        ihl = (pkt[ip] & 0xF) * 4
        kip = '.'.join(str(b) for b in pkt[ip + 12:ip + 16])
        hip = '.'.join(str(b) for b in pkt[ip + 16:ip + 20])
        tcp = ip + ihl
        kport = (pkt[tcp] << 8) | pkt[tcp + 1]
        hport = (pkt[tcp + 2] << 8) | pkt[tcp + 3]
        bayrak = pkt[tcp + 13]
        veri = tcp + (((pkt[tcp + 12] >> 4) & 0xF) * 4)
        cikti.append((sn * 1000000 + us, kip, kport, hip, hport, bayrak,
                      pkt[veri:cap]))
    return cikti


def analiz(yol):
    print()
    print('=' * 70)
    print('KANAL DEĞİŞTİRME ÇÖZÜMLEMESİ — %s' % os.path.basename(yol))
    print('=' * 70)
    paketler = pcap_tcp(yol)
    if not paketler:
        print('X paket okunamadı')
        return

    # --- 1) Yeni bağlantı açıldı mı? SYN paketleri ---
    synler = []
    baglantilar = Counter()
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        if bayrak & 0x02 and not (bayrak & 0x10):      # SYN, ACK değil
            synler.append((z, kip, kport, hip, hport))
        baglantilar[(hip, hport) if kip != OYUN_IP else (kip, kport)] += 1

    print()
    print('-' * 70)
    print('1) YENİ BAĞLANTI AÇILDI MI')
    print('-' * 70)
    if synler:
        t0 = synler[0][0]
        print('   %d yeni TCP bağlantısı (SYN) görüldü:' % len(synler))
        for z, kip, kport, hip, hport in synler[:12]:
            print('      +%6.1f sn   %s:%d -> %s:%d'
                  % ((z - t0) / 1e6, kip, kport, hip, hport))
    else:
        print('   Yeni bağlantı YOK.')

    portlar = sorted({p for (ip, p), _ in baglantilar.items()
                      if ip == OYUN_IP or True})
    sunucu_portlari = sorted({hport for _, kip, _, hip, hport, _, _ in paketler
                              if hip == OYUN_IP})
    print()
    print('   Sunucuya giden portlar: %s' % (sunucu_portlari or 'yok'))

    if len(sunucu_portlari) > 1 or len(synler) > 1:
        print()
        print('   >> SONUÇ: kanal değişimi YENİ BAĞLANTI açıyor.')
        print('      Kanallar ayrı sunucular (farklı port). Tek paket')
        print('      enjekte ederek kanal değiştirilemez — istemcinin')
        print('      yeniden bağlanması gerekir, bunu bot yapamaz.')
        print()
        print('      Yapılabilecek: rota turu bitince botu DURDURUP')
        print('      kanalı elle değiştirmen için uyarmak.')
        return

    # --- 2) Aynı bağlantıysa: nadir giden opcode ara ---
    print()
    print('-' * 70)
    print('2) AYNI BAĞLANTI — kanal paketi aranıyor')
    print('-' * 70)
    giden = defaultdict(list)
    t0 = paketler[0][0]
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        if hip != OYUN_IP or not yuk:
            continue
        # Her eylem AYRI segmentte gelir; segmentin ilk baytı opcode'dur
        giden[(yuk[0], len(yuk))].append((z - t0) / 1e6)

    bilinen = {0x07, 0x02, 0x03, 0x08, 0x3D, 0x0F, 0x1A, 0x32, 0x34}
    adaylar = []
    for (op, boy), zamanlar in giden.items():
        if op in bilinen:
            continue
        if not (1 <= len(zamanlar) <= 8):
            continue
        adaylar.append((len(zamanlar), op, boy, zamanlar))
    adaylar.sort(reverse=True)

    if not adaylar:
        print('   Aday bulunamadı. Kanal değiştirdiğinden emin misin?')
        print('   Kayıt sırasında başka bir şey yapmadın, değil mi?')
        return

    print('   %-8s %-6s %-6s %s' % ('opcode', 'boy', 'adet', 'saniyeler'))
    for adet, op, boy, zamanlar in adaylar[:12]:
        print('   0x%02X     %-6d %-6d %s'
              % (op, boy, adet,
                 ', '.join('%.1f' % z for z in zamanlar[:6])))
    print()
    print('   Kanal kaç kez değiştirdiysen ADET o sayıya eşit olan satır')
    print('   kanal paketidir. Hex\'ini görmek için:')
    print('     python tools/eylem_bul.py %s' % os.path.basename(yol))
    print()
    print('   Bulduğun paketi tambot > Rota > "Kanal paketi" alanına yaz;')
    print('   kanal numarasının olduğu baytı {k:02X} ile değiştir.')


def main():
    args = sys.argv[1:]
    if '--dosya' in args:
        analiz(args[args.index('--dosya') + 1])
        input('\nEnter...')
        return
    sure = 60
    if '--sure' in args:
        try:
            sure = int(args[args.index('--sure') + 1])
        except Exception:
            pass
    print('=' * 70)
    print('KANAL DEĞİŞTİRME PAKETİ ARAYIŞI')
    print('=' * 70)
    pcap = kaydet(sure)
    if pcap:
        analiz(pcap)
    input('\nEnter...')


if __name__ == '__main__':
    main()
