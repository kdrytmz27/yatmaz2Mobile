# -*- coding: utf-8 -*-
"""
ÖLÜM + CANLANMA + HAREKET kaydı — yerinde canlanma ve kısa yürüyüş paketlerini
çıkarmak için.

Emülatörde (normal oynarken) kısa bir trafik kaydı alır, sonra çözer:
  • kendi karakterinin vid'i (gelen 0x11 "hep kendi vid" paketinden)
  • ÖLÜM anı (gelen 0x46: kurban == kendi vid)
  • ölümden sonra GİDEN sohbet komutları (0x03) — "/restart_here" gibi
  • GİDEN hareket paketleri (0x07) — kısa yürüyüş için biçim + zaman alanı

KULLANIM
--------
    python tools/olum_kaydet.py --sure 120
      1) Enter'a bas
      2) Oyunda ÖL (bir canavara/oyuncuya öldürt)
      3) Açılan ekranda "yerinde canlan / burada" seç
      4) Birkaç adım YÜRÜ
      5) Kayıt bitince çözümleme ekrana yazılır

    python tools/olum_kaydet.py --dosya log/olum_XXXX.pcap   # var olan kaydı çöz

NOT: Şifre/kişisel veri EKRANA yazılmaz; yalnızca oyun paketlerinin başlıkları,
sohbet komutları (/restart_here vb.) ve koordinatlar gösterilir.
"""

import argparse
import importlib.util
import os
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

import kanal_bul as kb                                  # noqa: E402  (adb + pcap yardımcıları)

_spec = importlib.util.spec_from_file_location(
    'metin_izleyici', os.path.join(_BURASI, 'metin_izleyici.py'))
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)

UZAK_YOL = '/sdcard/r2_olum.pcap'
OYUN_ALT, OYUN_UST = 30000, 30100


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
    pcap = os.path.join(_KOK, 'log', 'olum_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s' % arayuz)
    print('-' * 68)
    print('  1. Enter -> kayıt başlar')
    print('  2. Oyunda ÖL')
    print('  3. "yerinde canlan / burada" seç')
    print('  4. Birkaç adım yürü')
    print('-' * 68)
    input('Hazırsan Enter...')
    kb.kabuk(adb, "su -c 'pkill -f r2_olum.pcap'")
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    print('>>> KAYIT BAŞLADI (%d sn) — şimdi öl, yerinde canlan, yürü <<<' % sure)
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


def _yon(kport, hport):
    if OYUN_ALT <= hport <= OYUN_UST:
        return 'C>S'
    if OYUN_ALT <= kport <= OYUN_UST:
        return 'S>C'
    return None


def _sohbet_coz(yuk):
    """C>S 0x03 sohbet: 03 | u16 boy | u8 tür | metin. Döner metin ya da None."""
    if len(yuk) < 5 or yuk[0] != 0x03:
        return None
    boy = yuk[1] | (yuk[2] << 8)
    if boy < 5 or boy > 200 or boy > len(yuk):
        return None
    try:
        return yuk[4:boy].split(b'\x00')[0].decode('cp1254', 'replace')
    except Exception:                                   # noqa: BLE001
        return None


def analiz(yol):
    print('\n' + '=' * 70)
    print('ÖLÜM / CANLANMA / HAREKET — %s' % os.path.basename(yol))
    print('=' * 70)
    paketler = kb.pcap_tcp(yol)
    if not paketler:
        print('X paket okunamadı')
        return
    t0 = paketler[0][0]

    # S>C akışlarını bağlantı bazında çerçevele: kendi vid (0x11) ve ölüm (0x46)
    sc = {}
    cs = []
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        yon = _yon(kport, hport)
        if not yuk or yon is None:
            continue
        if yon == 'S>C':
            sc.setdefault((kip, kport), bytearray()).extend(yuk)
        else:
            cs.append((z, kport, yuk))

    vid_say = {}
    olumler = []
    for _, tampon in sc.items():
        i = 0
        while i < len(tampon):
            boy = mi.oyun_mesaj_boyu(tampon, i, None)
            if boy < 0:
                break
            if boy == 0:
                i += 1
                continue
            h = tampon[i]
            if h == 0x11:                                # hep kendi vid
                v = mi._i32(tampon, i + 1)
                vid_say[v] = vid_say.get(v, 0) + 1
            elif h == 0x46 and boy == 10:                # ölüm: alt|kurban|öldüren
                olumler.append((mi._i32(tampon, i + 2), mi._i32(tampon, i + 6)))
            i += boy

    kendi = max(vid_say, key=vid_say.get) if vid_say else None
    print('\n1) KENDİ VİD')
    if kendi:
        print('   kendi vid = %d  (0x11 sayısı %d)' % (kendi, vid_say[kendi]))
    else:
        print('   0x11 bulunamadı — kendi vid çıkarılamadı')

    print('\n2) ÖLÜM (0x46 kurban == kendi vid)')
    olum_var = [(k, o) for k, o in olumler if kendi and k == kendi]
    if olum_var:
        print('   ÖLDÜN — öldüren vid: %s' % ', '.join(str(o) for _, o in olum_var))
    elif olumler:
        print('   0x46 var ama kurban kendi vid değil (ilk 3): %s' % olumler[:3])
    else:
        print('   0x46 ölüm paketi görülmedi')

    print('\n3) GİDEN SOHBET KOMUTLARI (0x03) — canlanma komutu burada olmalı')
    bulundu = False
    for z, kport, yuk in cs:
        metin = _sohbet_coz(yuk)
        if metin and metin.startswith('/'):
            bulundu = True
            print('   +%6.1f sn   %r' % ((z - t0) / 1e6, metin))
    if not bulundu:
        print('   / ile başlayan sohbet komutu görülmedi '
              '(canlanma sohbetle değil, ayrı paketle olabilir — 4. bölüme bak)')

    print('\n4) GİDEN PAKET BAŞLIKLARI (ölüm çevresi) — canlanma paketi + ilk hareketler')
    for z, kport, yuk in cs:
        if not yuk:
            continue
        h = yuk[0]
        ek = ''
        if h == 0x07 and len(yuk) >= 16:                 # CG_MOVE
            func, rot = yuk[1], yuk[3]
            x = mi._i32(yuk, 4)
            y = mi._i32(yuk, 8)
            tik = mi._i32(yuk, 12) if len(yuk) >= 16 else 0
            ek = 'HAREKET func=%d rot=%d x=%d y=%d tik=%d' % (func, rot, x, y, tik)
        elif h == 0x03:
            ek = 'sohbet %r' % _sohbet_coz(yuk)
        print('   +%6.1f sn  0x%02x  %-3d bayt  %s  %s'
              % ((z - t0) / 1e6, h, len(yuk), yuk[:16].hex(' '), ek))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ölüm/canlanma/hareket kaydı')
    ap.add_argument('--sure', type=int, default=120)
    ap.add_argument('--dosya')
    a = ap.parse_args(argv)
    yol = a.dosya or kaydet(a.sure)
    if yol:
        analiz(yol)


if __name__ == '__main__':
    main()
