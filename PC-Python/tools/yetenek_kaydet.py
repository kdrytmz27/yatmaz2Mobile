# -*- coding: utf-8 -*-
"""
YETENEK (skill) vnum kaydı — buff'çının basacağı yeteneklerin vnum'unu bulur.

Emülatörde oynarken kısa bir trafik kaydı alır, sonra GİDEN (istemci->sunucu)
CG_USE_SKILL (0x34 | vnum | vid) paketlerini çözer. Yani hangi yeteneği
bastıysan onun vnum'unu ekrana yazar.

KULLANIM
--------
    python tools/yetenek_kaydet.py --sure 60
      1) Enter'a bas
      2) Oyunda önce EJDERHA YARDIMI'nı bas
      3) Sonra EJDERHA GÜCÜ'nü bas
      4) Kayıt bitince ilk basılan = Ejderha Yardımı vnum'u,
         ikinci = Ejderha Gücü vnum'u olarak listelenir

    python tools/yetenek_kaydet.py --dosya log/yetenek_XXXX.pcap   # var olanı çöz

Bu vnum'ları panelde "Buff'çı" kutusundaki ilgili alanlara yaz.

NOT: Şifre/kişisel veri EKRANA yazılmaz; yalnızca yetenek vnum'ları ve hedef
vid'leri gösterilir.
"""

import argparse
import importlib.util
import os
import struct
import subprocess
import sys
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                   # noqa: BLE001
        pass

import kanal_bul as kb                                  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'metin_izleyici', os.path.join(_BURASI, 'metin_izleyici.py'))
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)

UZAK_YOL = '/sdcard/r2_yetenek.pcap'
OYUN_ALT, OYUN_UST = 30000, 30100
VNUM_TAVAN = 2000        # yetenek vnum'u küçük (indeks) — yanlış eşleşmeyi eler


def kaydet(sure):
    adb = kb.adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        return None
    dev = subprocess.run([adb, 'devices'], capture_output=True,
                         timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in dev:
        print('X Cihaz bağlı değil.')
        return None
    if 'uid=0' not in kb.kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor.')
        return None
    arayuz = kb.arayuz_bul(adb)
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    pcap = os.path.join(_KOK, 'log', 'yetenek_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s' % arayuz)
    print('-' * 68)
    print('  1. Enter -> kayıt başlar')
    print('  2. Oyunda önce EJDERHA YARDIMI, sonra EJDERHA GÜCÜ bas')
    print('  (istersen her yeteneği birkaç kez bas — hepsi listelenir)')
    print('-' * 68)
    input('Hazırsan Enter...')
    kb.kabuk(adb, "su -c 'pkill -f r2_yetenek.pcap'")
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    print('>>> KAYIT BAŞLADI (%d sn) — şimdi yetenekleri bas <<<' % sure)
    kb.kabuk(adb, "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s tcp'"
             % (sure, arayuz, UZAK_YOL), sure=sure + 30)
    print('>>> KAYIT BİTTİ <<<')
    subprocess.run([adb, 'pull', UZAK_YOL, pcap], capture_output=True, timeout=120)
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        print('X Kayıt alınamadı ya da boş.')
        return None
    print('kayıt : %s  (%.1f KB)' % (pcap, os.path.getsize(pcap) / 1024.0))
    return pcap


def _giden_mi(kport, hport):
    """İstemci -> sunucu (hedef portu oyun aralığında)."""
    return OYUN_ALT <= hport <= OYUN_UST and not (OYUN_ALT <= kport <= OYUN_UST)


def _yetenekleri_bul(tampon):
    """Giden akışta 0x34 | vnum | vid örüntülerini tara. Döner: [(vnum, vid, ham)]."""
    bulunan = []
    n = len(tampon)
    i = 0
    while i + 9 <= n:
        if tampon[i] == mi.H_YETENEK:
            vnum, vid = struct.unpack_from('<II', tampon, i + 1)
            if 0 < vnum <= VNUM_TAVAN and (vid == 0 or mi._makul_id(vid)):
                ham = bytes(tampon[i:i + 16])       # sonraki baytlar (biçim kontrolü)
                bulunan.append((vnum, vid, ham))
                i += 9
                continue
        i += 1
    return bulunan


def analiz(yol):
    print('\n' + '=' * 70)
    print('YETENEK vnum kaydı — %s' % os.path.basename(yol))
    print('=' * 70)
    paketler = kb.pcap_tcp(yol)
    if not paketler:
        print('X paket okunamadı')
        return
    t0 = paketler[0][0]

    # Giden akışı bağlantı bazında birleştir, sonra 0x34'leri tara.
    akis = {}
    zaman = {}
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        if not yuk or not _giden_mi(kport, hport):
            continue
        anahtar = (kip, kport)
        akis.setdefault(anahtar, bytearray()).extend(yuk)
        zaman.setdefault(anahtar, z)

    sirali = []       # (ilk_zaman, vnum, vid, ham)
    sayim = {}
    for anahtar, tampon in akis.items():
        for vnum, vid, ham in _yetenekleri_bul(tampon):
            sirali.append((zaman[anahtar], vnum, vid, ham))
            sayim[vnum] = sayim.get(vnum, 0) + 1
    sirali.sort()

    print('\n1) BASILAN YETENEKLER (zaman sırasıyla)')
    if not sirali:
        print('   0x34 CG_USE_SKILL görülmedi.')
        print('   • Yetenekleri kayıt sırasında bas.  • Enjeksiyon/proxy açık olmasın,')
        print('     normal oyna — kayıt cihazın kendi trafiğini dinliyor.')
        return
    for z, vnum, vid, ham in sirali:
        hed = 'kendine' if vid == 0 else 'hedef vid %d' % vid
        print('   +%6.1f sn   vnum %-5d   %s   ham: %s' % ((z - t0) / 1e6, vnum, hed, ham.hex(' ')))
    print('   (biçim kontrolü: 34 vnum(4) vid(4) = 9 bayt. 10. bayt yeni bir paket başlığıysa')
    print('    biçim doğru; değilse pakette ek alan var — bana bu satırları gönder.)')

    # İlk görülme sırasına göre benzersiz vnum listesi.
    ilk = {}
    for z, vnum, vid, ham in sirali:
        if vnum not in ilk:
            ilk[vnum] = z
    benzersiz = sorted(ilk, key=lambda v: ilk[v])
    print('\n2) BENZERSİZ vnum (ilk basılma sırasıyla)')
    for n, vnum in enumerate(benzersiz, 1):
        print('   %d. vnum %-5d  (%d kez)' % (n, vnum, sayim[vnum]))
    print('\n3) PANELE YAZ')
    if len(benzersiz) >= 2:
        print('   Ejderha Yardımı vnum = %d' % benzersiz[0])
        print('   Ejderha Gücü     vnum = %d' % benzersiz[1])
    elif len(benzersiz) == 1:
        print('   Tek yetenek görüldü: vnum = %d  (ikincisini de bas ve tekrar dene)'
              % benzersiz[0])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Yetenek vnum kaydı')
    ap.add_argument('--sure', type=int, default=60)
    ap.add_argument('--dosya')
    a = ap.parse_args(argv)
    yol = a.dosya or kaydet(a.sure)
    if yol:
        analiz(yol)


if __name__ == '__main__':
    main()
