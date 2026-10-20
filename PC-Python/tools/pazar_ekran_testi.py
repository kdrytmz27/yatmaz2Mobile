# -*- coding: utf-8 -*-
"""
TEK TIKLAMA TESTİ — enjekte ettiğimiz dükkân tıklaması GERÇEKTEN çalışıyor mu?

Neden gerekli: paket "gitti" görünüyor (/api/enjekte ok, log'da giden 0x1A) ama
sunucudan içerik (0x26) gelmiyor. İki ihtimal var ve ayırt etmek için gözle
bakmak yeterli:

    a) Ekranda dükkân AÇILIYOR  → enjeksiyon çalışıyor, sorun OKUMADA
    b) Ekranda hiçbir şey olmuyor → sunucu paketimizi yok sayıyor

Bu ayrım her şeyi belirliyor, o yüzden tahmin etmek yerine bakıyoruz.

KULLANIM
--------
    python tools/pazar_ekran_testi.py
      - Pazarda dur, oyun ekranı görünür olsun
      - Enter'a bas, EKRANA BAK
      - Dükkân penceresi açıldı mı, açılmadı mı söyle
"""

import importlib.util
import math
import os
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

import pazar_paket as pp                                # noqa: E402

_sp = importlib.util.spec_from_file_location(
    'tambot', os.path.join(_KOK, 'tambot.py'))
tb = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(tb)


def main():
    api = tb.Api()
    d = api.get('/api/durum')
    if not isinstance(d, dict):
        print('X APK\'ye ulaşılamıyor.')
        return
    p = d.get('proxy') or {}
    print('kapılar: açık=%s bağlı=%s enjeksiyon=%s'
          % (p.get('acik'), p.get('bagli'), p.get('enjeksiyon')))
    if not (p.get('acik') and p.get('bagli') and p.get('enjeksiyon')):
        print('X Üç kapı da açık olmalı.')
        return

    k = d.get('konum') or {}
    bx, by = int(k.get('x', 0) or 0), int(k.get('y', 0) or 0)
    tik = int(d.get('tik', 0) or 0)
    if not (bx and by):
        print('X Konum bilinmiyor.')
        return

    vs = api.get('/api/varliklar', n=200) or []
    dukkanlar = []
    for v in vs:
        if pp.dukkan_mi(v) and v.get('vid') and v.get('x') is not None:
            dukkanlar.append((math.hypot(int(v['x']) - bx, int(v['y']) - by),
                              int(v['vid']), v.get('ad') or '?',
                              int(v['x']), int(v['y'])))
    if not dukkanlar:
        print('X Yakında dükkân yok — pazarda mısın?')
        return
    dukkanlar.sort()
    m, vid, ad, hx, hy = dukkanlar[0]
    brot = tb.yon_bayti(hx - bx, hy - by)

    print('-' * 68)
    print('  En yakın dükkân : %s' % ad)
    print('  Mesafe          : %.1f m' % (m / 100.0))
    print('  Yön (bRot)      : %d' % brot)
    print('-' * 68)
    print('  ŞİMDİ OYUN EKRANINA BAK. Enter\'a basınca tıklama gönderilecek.')
    input('  Hazırsan Enter...')

    paket = tb.paket_tikla_tam(vid, bx, by, tik, brot=brot)
    print('\n  gönderiliyor: %s' % paket.hex(' '))
    cevap = api.enjekte(paket)
    print('  /api/enjekte  : %r' % (cevap,))

    # gelen 0x26 var mı (boy alanıyla birlikte)
    t0 = time.time()
    gorulen = set()
    while time.time() - t0 < 5.0:
        time.sleep(0.25)
        for r in (api.get('/api/log', n=400) or []):
            if r.get('opcode') != pp.BASLIK or r.get('giden'):
                continue
            anah = (r.get('zaman'), r.get('boy'))
            if anah in gorulen:
                continue
            gorulen.add(anah)
            hexs = (r.get('hex') or '').split()
            kirp = (r.get('boy') and len(hexs) < r['boy'])
            print('  ← 0x26  boy=%s  hex=%d bayt  %s'
                  % (r.get('boy'), len(hexs), 'KIRPILMIŞ' if kirp else 'tam'))

    print('\n' + '=' * 68)
    if gorulen:
        print('  Sunucudan 0x26 GELDİ — okuma tarafına bakacağız.')
    else:
        print('  Sunucudan 0x26 GELMEDİ.')
    print()
    print('  ŞİMDİ SÖYLE: ekranda dükkân penceresi AÇILDI MI?')
    print()
    print('    AÇILDIYSA  → enjeksiyon çalışıyor, sorun paketi OKUMADA;')
    print('                 içeriği başka yoldan (ekran/tcpdump) alırız.')
    print('    AÇILMADIYSA→ sunucu enjekte paketimizi yok sayıyor;')
    print('                 tıklamayı gerçek dokunuşla (input tap) yaparız.')
    print('=' * 68)
    # açık kaldıysa kapat
    api.enjekte(tb.paket_dukkan_kapat())


if __name__ == '__main__':
    main()
