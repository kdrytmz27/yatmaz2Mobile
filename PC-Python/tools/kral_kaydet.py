# -*- coding: utf-8 -*-
"""
KRALI YAKALA paket kaydı — oyunu oynarken TÜM trafiği kaydeder, sonra çözmek
için okunur döküm çıkarır.

Kralı Yakala'nın hangi paketlerle çalıştığını bilmiyoruz; bu yüzden her şeyi
kaydedip GÜRÜLTÜYÜ (hareket/konum/ping) eleyip geri kalan paketleri ham bayt +
metin olarak dökeriz. Sen bir oyun oynarsın, ben dökümden mekaniği çözerim.

KULLANIM
--------
    python tools/kral_kaydet.py --sure 180
      1) Enter'a bas (kayıt başlar)
      2) Kralı Yakala oyununu AÇ ve BİR TAM OYUN oyna:
         - desteyi/oyunu başlat
         - birkaç hamle yap (kart seç, aç)
         - kralı yakala / oyunu bitir, ödülü al
      3) Kayıt bitince döküm ekrana + log/kral_XXXX.txt dosyasına yazılır

    python tools/kral_kaydet.py --dosya log/kral_XXXX.pcap   # var olanı çöz
    python tools/kral_kaydet.py --dosya ... --ham            # HİÇBİR başlığı eleme

Not: Şifre/kişisel veri oyun paketlerinde geçmez; yalnız oyun paketleri gösterilir.
Çıktıdaki 'C>S' senden sunucuya (tıklama/seçim), 'S>C' sunucudan sana (kart/sonuç).
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

import kanal_bul as kb                                  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'metin_izleyici', os.path.join(_BURASI, 'metin_izleyici.py'))
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)

UZAK_YOL = '/sdcard/r2_kral.pcap'
OYUN_ALT, OYUN_UST = 30000, 30100

# Oyunu oynarken sürekli akan, kart oyunuyla ilgisiz paketler — eleyeceğiz.
# (Kalanı kart oyunudur; bunlar hareket/konum/ping/varlık/isim/vuruş.)
GURULTU = {0x01, 0x02, 0x03, 0x05, 0x0D, 0x0E, 0x11, 0x2C, 0x3E,
           0x88, 0xFC, 0xFD, 0xFE, 0x07}


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
    pcap = os.path.join(_KOK, 'log', 'kral_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s' % arayuz)
    print('-' * 68)
    print('  1. Enter -> kayıt başlar')
    print('  2. Kralı Yakala oyununu aç, BİR TAM OYUN oyna (başlat, hamleler, bitir)')
    print('  3. Kayıt bitince döküm gelir')
    print('-' * 68)
    input('Hazırsan Enter...')
    kb.kabuk(adb, "su -c 'pkill -f r2_kral.pcap'")
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    print('>>> KAYIT BAŞLADI (%d sn) — şimdi Kralı Yakala oyna <<<' % sure)
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


def _metin(yuk):
    """Pakette geçen okunur ASCII parçası (kart adı/etiket olabilir)."""
    p = ''.join(chr(b) if 32 <= b < 127 else '.' for b in yuk)
    return p if any(c != '.' for c in p) else ''


def _kral_coz(paketler):
    """Kralı Yakala paketlerini (0xe2 / 0xee / ödül) hamle hamle çöz."""
    sat = []
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        y = _yon(kport, hport)
        if not yuk or not y:
            continue
        b = bytes(yuk)
        # SEN -> sunucu: e2 <mod> <arg>
        if y == 'C>S' and b[0] == 0xE2 and len(b) >= 3:
            mod, arg = b[1], b[2]
            ad = {0: 'BAŞLAT (oyunu aç)', 1: 'sıradaki eldeki kart',
                  2: 'AÇ  masa[%d]' % arg, 3: 'BİTİR / ödül al'}.get(
                      mod, 'e2 %02x %02x' % (mod, arg))
            sat.append((z, 'SEN   ' + ad))
        # Sunucu -> SEN: segment içindeki tüm ee çerçevelerini tara
        if y == 'S>C':
            i = 0
            while i + 4 <= len(b):
                if b[i] == 0xEE:
                    L = b[i + 1]
                    if L >= 4 and b[i + 2] == 0x00 and i + L <= len(b):
                        p = b[i:i + L]
                        sub = p[3]
                        if sub == 3 and L >= 11:
                            puan = int.from_bytes(p[4:8], 'little')
                            pos, deger = p[9], p[10]
                            aldi = p[11] if L >= 12 else '?'
                            bitti = p[12] if L >= 13 else '?'
                            kafa = p[14] if L >= 15 else '?'
                            sat.append((z, 'OYUN  masa[%d] = %d  PUAN %d  '
                                        '[aldı=%s bitti=%s KURU-KAFA(5)=%s]'
                                        % (pos, deger, puan, aldi, bitti, kafa)))
                        elif sub == 4 and L >= 6:
                            sat.append((z, 'OYUN    board[%d] = %d' % (p[4], p[5])))
                        elif sub == 2 and L >= 5:
                            sat.append((z, 'OYUN  el/tur = %d' % p[4]))
                        else:
                            sat.append((z, 'OYUN  ee sub=%d  %s' % (sub, p.hex(' '))))
                        i += L
                        continue
                i += 1
        # Ödül / sistem mesajı (0x04 tür 01/02 = sistem)
        if y == 'S>C' and b[0] == 0x04 and len(b) >= 9 and b[3] in (1, 2):
            try:
                t = b[8:].split(b'\x00', 1)[0]
                if t and t[0] == 3:
                    t = t[1:]
                metin = t.decode('cp1254', 'replace')
            except Exception:                          # noqa: BLE001
                metin = ''
            if metin and ('animet' in metin or 'Kazand' in metin or 'puan' in metin.lower()
                          or 'Kral' in metin):
                sat.append((z, '>>> SİSTEM: %s' % metin))
    sat.sort(key=lambda s: s[0])
    return sat


def analiz(yol, ham=False):
    baslik = 'KRALI YAKALA — %s%s' % (os.path.basename(yol), ' (HAM)' if ham else '')
    cikti = ['=' * 78, baslik, '=' * 78]
    paketler = kb.pcap_tcp(yol)
    if not paketler:
        print('X paket okunamadı')
        return
    t0 = paketler[0][0]

    # 1) Başlık histogramı: hangi paket türü kaç kez, hangi yönde.
    hist = {}
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        y = _yon(kport, hport)
        if not yuk or not y:
            continue
        hist[(y, yuk[0])] = hist.get((y, yuk[0]), 0) + 1
    cikti.append('\n1) PAKET BAŞLIKLARI (yön / 0xNN / adet) — çoktan aza')
    for (y, h), n in sorted(hist.items(), key=lambda kv: -kv[1]):
        isaret = '' if (h in GURULTU and not ham) else '  <-- KART OYUNU olabilir'
        cikti.append('   %s  0x%02x  x%-5d%s' % (y, h, n, isaret))

    # 2) Kronolojik döküm — gürültüyü ele, kalanı ham + metin yaz.
    cikti.append('\n2) PAKETLER (gürültü elendi%s) — +sn  yön  0xNN  boy  ham | metin'
                 % ('' if not ham else ': KAPALI'))
    onceki = None
    tekrar = 0
    yazilan = 0
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        y = _yon(kport, hport)
        if not yuk or not y:
            continue
        h = yuk[0]
        if h in GURULTU and not ham:
            continue
        imza = (y, bytes(yuk[:48]))
        if imza == onceki:                              # aynı paket art arda
            tekrar += 1
            continue
        if tekrar:
            cikti.append('        (önceki ×%d tekrar)' % (tekrar + 1))
            tekrar = 0
        onceki = imza
        hexs = bytes(yuk[:64]).hex(' ')
        cikti.append('   +%7.2f  %s  0x%02x  %-4d  %s | %s'
                     % ((z - t0) / 1e6, y, h, len(yuk), hexs, _metin(yuk[:64])))
        yazilan += 1
    if tekrar:
        cikti.append('        (önceki ×%d tekrar)' % (tekrar + 1))
    if not yazilan:
        cikti.append('   (kart oyunu paketi görülmedi — --ham ile tekrar dene, ya da '
                     'oyunu kayıt sırasında oynadığından emin ol)')

    # 3) Kralı Yakala oyun akışı — sohbet gürültüsü olmadan, hamle hamle.
    cikti.append('\n3) KRALI YAKALA OYUN AKIŞI (0xe2 sen / 0xee sunucu)')
    akis = _kral_coz(paketler)
    if akis:
        for z, s in akis:
            cikti.append('   +%7.2f  %s' % ((z - t0) / 1e6, s))
    else:
        cikti.append('   (kart oyunu paketi bulunamadı)')

    metin_ozet = '\n'.join(cikti)
    print(metin_ozet)
    # Dosyaya da yaz (uzun döküm ekranda kaybolmasın).
    txt = os.path.splitext(yol)[0] + '.txt'
    try:
        with open(txt, 'w', encoding='utf-8') as f:
            f.write(metin_ozet + '\n')
        print('\n>>> Döküm dosyaya da yazıldı: %s' % txt)
        print('    Bu dosyayı bana yapıştır — kart oyununun paketlerini çözerim.')
    except Exception as e:                              # noqa: BLE001
        print('döküm dosyaya yazılamadı: %s' % e)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kralı Yakala paket kaydı')
    ap.add_argument('--sure', type=int, default=180)
    ap.add_argument('--dosya')
    ap.add_argument('--ham', action='store_true', help='hiçbir başlığı eleme')
    a = ap.parse_args(argv)
    yol = a.dosya or kaydet(a.sure)
    if yol:
        analiz(yol, ham=a.ham)


if __name__ == '__main__':
    main()
