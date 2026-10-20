# -*- coding: utf-8 -*-
"""
Telefondan EKRAN GÖRÜNTÜSÜ alır — ve istenirse tıklama noktasını işaretler.

NEDEN
-----
Tıklama sorunlarında ekran görüntüsü iki kez belirleyici oldu:

  • Metine paketle mi tıklandığı yoksa oyuncunun elle mi vurduğu ancak
    ekranda görülerek ayrıldı.
  • Ekranın YATAY (1920x1080) olduğu, dokunmatik aygıtın ise DİKEY
    (1080x1920) olduğu buradan anlaşıldı. Bot "aşağı kaydır" derken
    ekranda YANA kayıyordu.

DÖNÜŞ EŞLEMESİ (bu cihazda ölçüldü, rotation 90)
------------------------------------------------
    dokunma_x = 1080 - ekran_y
    dokunma_y = ekran_x

Panelin kendi sekmesine dokunularak canlı doğrulandı.

KULLANIM
--------
    python tools/ekran_al.py                  # görüntü al
    python tools/ekran_al.py --metin          # metinlerin hesaplanan
                                              # tıklama noktasını da yaz
"""

import os
import subprocess
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import http.client
import json
import time

from dokunma_kaydet import adb_bul

ADRES = "127.0.0.1:30200"


def get(yol):
    try:
        c = http.client.HTTPConnection(ADRES, timeout=5)
        c.request("GET", yol)
        r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
        c.close()
        return r
    except Exception as e:
        return {"_hata": str(e)}


def dokunma_ekrana(tx, ty, donus, gen=1080, yuk=1920):
    """Dokunma koordinatını EKRAN koordinatına çevirir."""
    if donus == 90:
        return ty, gen - tx
    if donus == 180:
        return gen - tx, yuk - ty
    if donus == 270:
        return yuk - ty, tx
    return tx, ty


def main():
    adb = adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        input('\nEnter...'); return

    ad = 'ekran_%s.png' % time.strftime('%Y%m%d_%H%M%S')
    yol = os.path.join(_KOK, 'log', ad)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    ortam = dict(os.environ, MSYS_NO_PATHCONV='1')
    subprocess.run([adb, 'shell', 'screencap -p /sdcard/r2_ss.png'],
                   capture_output=True, timeout=30, env=ortam)
    subprocess.run([adb, 'pull', '/sdcard/r2_ss.png', yol],
                   capture_output=True, timeout=30, env=ortam)
    subprocess.run([adb, 'shell', 'rm -f /sdcard/r2_ss.png'],
                   capture_output=True, timeout=20, env=ortam)
    if not os.path.exists(yol):
        print('X görüntü alınamadı.')
        input('\nEnter...'); return
    print('görüntü: %s  (%.1f KB)' % (yol, os.path.getsize(yol) / 1024.0))

    if '--metin' not in sys.argv:
        input('\nEnter...'); return

    d = get('/api/durum')
    if '_hata' in d:
        print('API yok: %s' % d['_hata'])
        input('\nEnter...'); return
    donus = int((d.get('proxy') or {}).get('donus', -1))
    print('ekran dönüşü: %s' % (donus if donus >= 0 else 'bilinmiyor'))

    k = get('/api/konum')
    bx, by = int(k.get('x', 0)), int(k.get('y', 0))
    v = get('/api/varliklar?n=200')
    if not isinstance(v, list):
        print('varlık listesi yok')
        input('\nEnter...'); return
    met = [x for x in v if x.get('tip') == 2]
    print('metin sayısı: %d' % len(met))
    if not met:
        print('Yakında metin yok — karşılaştırma yapılamıyor.')
        input('\nEnter...'); return

    yolk = os.path.join(_KOK, 'log', 'ekran_kalibrasyon.txt')
    if not os.path.exists(yolk):
        print('kalibrasyon dosyası yok: %s' % yolk)
        input('\nEnter...'); return
    with open(yolk, encoding='utf-8') as f:
        cx, cy, a, b, c, dd = [float(x) for x in f.read().strip().split(',')]

    print()
    print('%-26s %-12s %-16s %s' % ('metin', 'uzaklık', 'dokunma', 'EKRANDA'))
    for m in met:
        dx, dy = m['x'] - bx, m['y'] - by
        tx = cx + a * dx + b * dy
        ty = cy + c * dx + dd * dy
        ex, ey = dokunma_ekrana(tx, ty, donus)
        print('%-26s %-12s (%4.0f,%4.0f)   (%4.0f, %4.0f)'
              % ((m.get('ad') or '?')[:26],
                 '%.1f m' % ((dx * dx + dy * dy) ** 0.5 / 100.0),
                 tx, ty, ex, ey))
    print()
    print('Görüntüyü aç, metnin gerçekte nerede olduğuna bak ve EKRANDA')
    print('sütunuyla karşılaştır. Fark varsa Nişan kaydırma ile kapatılır')
    print('(değerler EKRAN eksenlerinde: + = sağa / aşağı).')
    input('\nEnter...')


if __name__ == '__main__':
    main()
