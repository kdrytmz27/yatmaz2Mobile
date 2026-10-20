# -*- coding: utf-8 -*-
"""
SALDIRI DÜĞMESİNİN yerini kaydeder.

NEDEN
-----
Metine tıklamak için ekranda doğru pikseli bulmaya çalıştık: kalibrasyon,
OCR, etiket bulma. Hepsi çalışıyor ama hepsi DEĞİŞKEN bir hedefe nişan
alıyor — metin ekranda her karede başka yerde.

2 Eyl 2026'da uçtan uca ölçüldü: dokunma boru hattı sağlam ve bir isme
dokununca oyunun seçili hedefi gerçekten değişiyor. Öyleyse daha basit
bir yol var:

    1. Metini SEÇ  (ekrandan tek dokunuş ya da hedefleme paketi)
    2. Sağ alttaki SALDIRI DÜĞMESİNE bas

Düğme SABİT yerde. Bir kez kaydedilir, bir daha değişmez — nişan alma
sorunu tamamen ortadan kalkar.

KULLANIM
--------
    python tools/saldiri_dugmesi.py

Betik "şimdi bas" dediğinde oyunda saldırı düğmesine dokun. Koordinat
yakalanıp tambot_ayar.json'a yazılır.
"""
import io
import json
import os
import re
import subprocess
import sys
import threading
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
_AYAR = os.path.join(_KOK, 'tambot_ayar.json')

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
        p = subprocess.run([adb, 'shell', komut], capture_output=True,
                           timeout=sure)
        return ((p.stdout or b'') + (p.stderr or b'')).decode('utf-8',
                                                              'replace')
    except Exception as e:
        return '<hata: %s>' % e


def dokunma_aygiti(adb):
    """ABS_MT_POSITION_X taşıyan aygıt dokunmatik ekrandır."""
    cikti = kabuk(adb, "su -c 'getevent -pl'", 30)
    aygit = None
    for satir in cikti.splitlines():
        m = re.search(r'add device \d+:\s*(\S+)', satir)
        if m:
            aygit = m.group(1)
        if 'ABS_MT_POSITION_X' in satir and aygit:
            return aygit
    return None


def dokunusu_yakala(adb, aygit, sure=25):
    """Tek bir dokunuş yakalar: (x, y) ya da None."""
    komut = [adb, 'shell', "su -c 'getevent -lt %s'" % aygit]
    try:
        # stdin=DEVNULL şart: yoksa adb shell konsolun stdin'ini yutuyor
        # ve sonraki input() EOFError veriyor.
        p = subprocess.Popen(komut, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL)
    except Exception as e:
        print('X getevent başlatılamadı: %s' % e)
        return None

    olaylar = []
    dur = threading.Event()

    def oku():
        for ham in p.stdout:
            if dur.is_set():
                break
            olaylar.append(ham.decode('utf-8', 'replace').strip())

    t = threading.Thread(target=oku, daemon=True)
    t.start()
    print('    >>> ŞİMDİ SALDIRI DÜĞMESİNE BAS (%d sn) <<<' % sure)
    for kalan in range(sure, 0, -5):
        time.sleep(5)
        if any('ABS_MT_POSITION' in o for o in olaylar):
            break
        print('        %d sn kaldı' % (kalan - 5))
    dur.set()
    try:
        p.kill()
    except Exception:
        pass

    x = y = None
    for satir in olaylar:
        m = re.search(r'ABS_MT_POSITION_X\s+([0-9a-fA-F]+)', satir)
        if m:
            x = int(m.group(1), 16)
        m = re.search(r'ABS_MT_POSITION_Y\s+([0-9a-fA-F]+)', satir)
        if m:
            y = int(m.group(1), 16)
        if x is not None and y is not None:
            return x, y
    return None


def main():
    print('=' * 70)
    print('SALDIRI DÜĞMESİ — KONUM KAYDI')
    print('=' * 70)
    print('Metini SEÇTİKTEN sonra bu düğmeye basılacak. Düğme sabit')
    print('yerde olduğu için bir kez kaydetmek yeterli.')
    print()

    adb = adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        return 1
    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor — getevent okunamaz.')
        return 1
    aygit = dokunma_aygiti(adb)
    if not aygit:
        print('X dokunmatik aygıt bulunamadı.')
        return 1
    print('aygıt: %s' % aygit)
    print()

    nokta = dokunusu_yakala(adb, aygit)
    if not nokta:
        print()
        print('X dokunuş yakalanamadı.')
        return 1
    x, y = nokta
    print()
    print('YAKALANAN DOKUNUŞ: %d, %d' % (x, y))

    d = {}
    if os.path.exists(_AYAR):
        try:
            with io.open(_AYAR, encoding='utf-8') as f:
                d = json.load(f)
        except Exception:
            d = {}
    d['saldiri_dugme_x_var'] = x
    d['saldiri_dugme_y_var'] = y
    with io.open(_AYAR, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)
    print('tambot_ayar.json güncellendi.')
    print()
    print('Not: tambot açıksa KAPATIP AÇ — yoksa açık pencere kendi')
    print('eski değerlerini geri yazar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
