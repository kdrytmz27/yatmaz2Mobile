# -*- coding: utf-8 -*-
"""
CANLI AKIŞ TESTİ — dükkân paketleri anında geliyor mu?

    python tools/pazar_akis_testi.py
      - Pazarda dur, çalıştır
      - 15 sn boyunca oyunda birkaç dükkâna TIKLA
      - Her dükkân zaman damgasıyla yazılır
"""

import os
import sys
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                   # noqa: BLE001
        pass

import pazar_canli as pc                                # noqa: E402


def main():
    t0 = time.time()
    dukkanlar = []
    ilk = [None]

    def geldi(d):
        if ilk[0] is None:
            ilk[0] = time.time() - t0
        dukkanlar.append(d)
        print('  +%6.2f sn  DÜKKÂN vid=%-9s %3d eşya'
              % (time.time() - t0, d['sahip_vid'], len(d['esyalar'])))

    o = pc.CanliOkuyucu(geldi, print)
    if not o.basla():
        return
    print('\n15 sn dinliyorum — OYUNDA DÜKKÂNLARA TIKLA\n')
    for k in range(15):
        time.sleep(1.0)
        print('\r  %2d sn   paket %6d   dükkân %3d'
              % (k + 1, o.paket_say, len(dukkanlar)), end='')
    print('\n')
    o.dur()

    print('=' * 60)
    print('okunan paket : %d' % o.paket_say)
    print('dükkân       : %d' % len(dukkanlar))
    if ilk[0] is not None:
        print('ilk dükkân   : %.2f sn sonra geldi' % ilk[0])
    print()
    if not o.paket_say:
        print('SONUÇ: akıştan HİÇ paket gelmedi — tcpdump yazmıyor olabilir.')
    elif not dukkanlar:
        print('SONUÇ: paket akıyor (%d) ama dükkân paketi görülmedi.' % o.paket_say)
        print('  Test sırasında bir dükkâna tıkladın mı?')
    else:
        print('SONUÇ: AKIŞ ÇALIŞIYOR — dükkânlar anında geliyor.')


if __name__ == '__main__':
    main()
