# -*- coding: utf-8 -*-
"""
Kanal değiştirme DOKUNUŞLARINI kaydeder.

NEDEN
-----
Kanal değişimi ağ üzerinden yapılamıyor: 29 Ağu 2026 ölçümü
(tools/kanal_bul.py) gösterdi ki kanallar AYRI SUNUCULAR
(port = 30000 + 4 x kanal) ve geçiş yeni bir TCP bağlantısı açıyor.
Proxy yalnızca var olan bağlantıya yazabildiği için paket enjekte
ederek kanal değiştirilemez.

Geriye tek yol: oyunun KENDİ menüsüne basmak. Cihazda root var
(tcpdump onunla çalışıyor), dolayısıyla `input tap` ile istemcinin
arayüzüne dokunabiliyoruz. Ama koordinatları bilmemiz gerek.

NASIL ÇALIŞIR
-------------
Android'in `getevent` çıktısı dinlenir. Sen oyunda ELLE kanal
değiştirirsin; betik parmağının değdiği noktaları yakalar ve tambot'a
yapıştırabileceğin bir dizi üretir:

    tap 540 1180
    bekle 800
    tap 320 760
    bekle 3000

KULLANIM
--------
    python tools/dokunma_kaydet.py            # 40 saniye
    python tools/dokunma_kaydet.py --sure 60

UYARI
-----
Koordinatlar BU CİHAZA ve BU ARAYÜZE özeldir. Çözünürlük, oyun sürümü
ya da menü düzeni değişirse yeniden kaydetmen gerekir.
"""

import os
import re
import subprocess
import sys
import threading
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


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


def ekran_boyutu(adb):
    cikti = kabuk(adb, 'wm size')
    m = re.search(r'(\d+)x(\d+)', cikti)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def dokunma_aygiti(adb):
    """
    Hangi /dev/input/eventN dokunmatik ekran?

    `getevent -pl` çıktısında ABS_MT_POSITION_X taşıyan aygıt odur.
    """
    cikti = kabuk(adb, "su -c 'getevent -pl'", 30)
    aygit = None
    for satir in cikti.splitlines():
        m = re.search(r'add device \d+:\s*(\S+)', satir)
        if m:
            aygit = m.group(1)
        if 'ABS_MT_POSITION_X' in satir and aygit:
            return aygit
    return None


def olaylari_topla(adb, aygit, sure, etiket):
    """getevent'i `sure` saniye dinler, ham olayları döndürür."""
    komut = [adb, 'shell', "su -c 'getevent -lt %s'" % aygit]
    try:
        # stdin=DEVNULL ŞART.
        #
        # Verilmezse `adb shell` konsolun stdin'ini miras alıyor ve
        # okuyor. Kayıt bitince bir sonraki input() EOF alıp EOFError
        # fırlatıyordu: ilk kanal kaydediliyor, ikinciyi sorarken betik
        # çöküyordu.
        p = subprocess.Popen(komut, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL)
    except Exception as e:
        print('X getevent başlatılamadı: %s' % e)
        return []

    olaylar = []
    dur = threading.Event()

    def oku():
        for ham in p.stdout:
            if dur.is_set():
                break
            olaylar.append((time.time(),
                            ham.decode('utf-8', 'replace').strip()))

    t = threading.Thread(target=oku, daemon=True)
    t.start()
    print('    >>> KAYIT (%d sn) — %s <<<' % (sure, etiket))
    for kalan in range(sure, 0, -5):
        time.sleep(5)
        print('        %d sn kaldı  (%d olay)' % (kalan - 5, len(olaylar)))
    dur.set()
    try:
        p.kill()
    except Exception:
        pass
    return olaylar


def dokunuslari_coz(olaylar):
    """
    Ham getevent olaylarından (zaman, x, y) dokunuşları çıkarır.

    Desen: ABS_MT_POSITION_X/Y ile koordinat gelir, parmak kalkışı
    BTN_TOUCH UP ya da TRACKING_ID ffffffff ile belli olur.
    """
    dokunuslar = []
    x = y = None
    basildi = None
    for zaman, satir in olaylar:
        if 'ABS_MT_POSITION_X' in satir:
            m = re.search(r'([0-9a-fA-F]+)\s*$', satir)
            if m:
                x = int(m.group(1), 16)
                if basildi is None:
                    basildi = zaman
        elif 'ABS_MT_POSITION_Y' in satir:
            m = re.search(r'([0-9a-fA-F]+)\s*$', satir)
            if m:
                y = int(m.group(1), 16)
                if basildi is None:
                    basildi = zaman
        elif ('BTN_TOUCH' in satir and 'UP' in satir) or \
             ('TRACKING_ID' in satir and 'ffffffff' in satir.lower()):
            if x is not None and y is not None:
                dokunuslar.append((basildi or zaman, x, y))
            x = y = None
            basildi = None
    return dokunuslar


def diziye_cevir(dokunuslar, son_bekleme=8000):
    """Dokunuşları 'tap/bekle' satırlarına çevirir."""
    satirlar = []
    for i, (z, dx, dy) in enumerate(dokunuslar):
        if i > 0:
            ms = int((z - dokunuslar[i - 1][0]) * 1000)
            satirlar.append('bekle %d' % max(200, ms))
        satirlar.append('tap %d %d' % (dx, dy))
    if satirlar:
        satirlar.append('bekle %d' % son_bekleme)
    return satirlar


def main():
    args = sys.argv[1:]
    sure = 25
    if '--sure' in args:
        try:
            sure = int(args[args.index('--sure') + 1])
        except Exception:
            pass
    kanallar = [1, 2, 3, 4, 5, 6, 7, 8]
    if '--kanallar' in args:
        try:
            ham = args[args.index('--kanallar') + 1]
            kanallar = [int(x) for x in ham.replace(';', ',').split(',')
                        if x.strip().isdigit()]
        except Exception:
            pass

    print('=' * 70)
    print('KANAL DEĞİŞTİRME — DOKUNUŞ KAYDI (kanal kanal)')
    print('=' * 70)

    adb = adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        input('\nEnter...'); return
    if '\tdevice' not in subprocess.run(
            [adb, 'devices'], capture_output=True,
            timeout=20).stdout.decode('utf-8', 'replace'):
        print('X Cihaz bağlı değil.')
        input('\nEnter...'); return
    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor — getevent okunamaz.')
        input('\nEnter...'); return

    gen, yuk = ekran_boyutu(adb)
    print('ekran : %dx%d' % (gen, yuk))
    aygit = dokunma_aygiti(adb)
    if not aygit:
        print('X dokunmatik aygıt bulunamadı.')
        print('  Elle bakmak için: adb shell su -c "getevent -pl"')
        input('\nEnter...'); return
    print('aygıt : %s' % aygit)
    print()
    print('-' * 70)
    print('  NASIL ÇALIŞIR')
    print('-' * 70)
    print('  Her kanal için ayrı kayıt alınır:')
    print('    1. Betik "simdi chN icin" der')
    print('    2. Enter tusuna basarsin, kayit baslar')
    print('    3. Oyunda O KANALA geçersin')
    print('    4. Kayıt biter, sıradaki kanala geçilir')
    print()
    print('  Menü konumu her kanal için farklı olabileceğinden hepsi')
    print('  ayrı ayrı kaydedilir. Bir kanalı atlamak için "a" yaz.')
    print('  Çıkmak için "q".')
    print()
    print('  Kanallar: %s   (her biri %d sn)'
          % (', '.join('ch%d' % k for k in kanallar), sure))
    print()

    diziler = {}
    for kanal in kanallar:
        print('=' * 70)
        print("  SIMDI ch%d'E GEC" % kanal)
        print('=' * 70)
        try:
            cevap = input(
                '  Enter = kaydet | a = atla | q = bitir : ').strip().lower()
        except EOFError:
            # stdin kapanmışsa (bir alt süreç yuttuysa) kaydı bitir,
            # o ana kadar toplananları kaybetme.
            print('')
            print('  ! girdi okunamadi - kayit burada bitiriliyor')
            break
        if cevap == 'q':
            break
        if cevap == 'a':
            print('  ch%d atlandı.' % kanal)
            continue

        olaylar = olaylari_topla(adb, aygit, sure, "ch%d'e gec" % kanal)
        dokunuslar = dokunuslari_coz(olaylar)
        if not dokunuslar:
            print('  X ch%d için dokunuş yakalanamadı — atlandı.' % kanal)
            continue
        satirlar = diziye_cevir(dokunuslar)
        diziler[kanal] = satirlar
        print('  ch%d: %d dokunuş' % (kanal, len(dokunuslar)))
        for satir in satirlar:
            print('      ' + satir)
        print()

    if not diziler:
        print('Hiçbir kanal kaydedilmedi.')
        input('\nEnter...'); return

    # --- tambot biçimi: [chN] başlıklı bölümler ---
    ciktilar = []
    for kanal in sorted(diziler):
        ciktilar.append('[ch%d]' % kanal)
        ciktilar.extend(diziler[kanal])
        ciktilar.append('')
    metin = '\n'.join(ciktilar).strip()

    print()
    print('=' * 70)
    print("TAMBOT'A YAPISTIR  (Rota > Kanal menusu dokunma dizisi)")
    print('=' * 70)
    print(metin)

    yol = os.path.join(_KOK, 'log', 'kanal_dokunuslar.txt')
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, 'w', encoding='utf-8') as f:
        f.write(metin)
    print()
    print('Dosyaya da yazıldı: %s' % yol)
    print('%d kanal kaydedildi: %s'
          % (len(diziler), ', '.join('ch%d' % k for k in sorted(diziler))))
    input('\nEnter...')


if __name__ == '__main__':
    main()
