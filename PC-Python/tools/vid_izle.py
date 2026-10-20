# -*- coding: utf-8 -*-
"""
Kendi vid'imiz öğrenildi mi? — CANLI izler.

NE GÖSTERİR
-----------
    vid    : APK'nın şu an kendimiz sandığı varlık kimliği
    oy     : o vid kaç kez görüldü (3'ten az ise bot hizalama göndermez)
    aday   : kaç farklı aday görüldü (1'den büyükse akışta kayma olmuş)
    isim   : varlık listesinde o vid'in ismi — KENDİ KARAKTER ADIN olmalı
    uyarı  : vid bir canavara denk geliyorsa kırmızı bayrak

İKİ KAYNAK
----------
APK vid'i iki yerden öğrenir:

  1. 0x11 "kendi durum tiki" — ama bu paket bazı oturumlarda HİÇ gelmiyor
     (29 Ağu 21:46 kaydı: 179 saniye, 5771 paket, sıfır adet).

  2. 0x3E savaş vuruşu — iki vid taşır, vuran + vurulan. Bota
     SALDIRTIRSAN, vurduğumuz canavar "vurulan" olarak dönünce "vuran"
     biziz. Doğrulandı: gerçek kayıtta kendi vid'imiz %100 örtüştü,
     başka oyuncular %0.

Yani vid gelmiyorsa: BOTU SAVAŞTIR. Sadece rota modunda ne 0x11 gelir
ne saldırı olur; vid asla öğrenilemez.

KULLANIM
--------
    python tools/vid_izle.py
    python tools/vid_izle.py --sure 120     # 120 saniye izle
"""

import http.client
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ADRES = "127.0.0.1:30200"
TIP_MOB, TIP_METIN = 0, 1


def adb_forward():
    for aday in ['adb',
                 os.path.expanduser(
                     r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe')]:
        try:
            subprocess.run([aday, 'forward', 'tcp:30200', 'tcp:30200'],
                           capture_output=True, timeout=10)
            return
        except Exception:
            continue


def get(yol):
    try:
        c = http.client.HTTPConnection(ADRES, timeout=4)
        c.request("GET", yol)
        r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
        c.close()
        return r
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    sure = 90
    if '--sure' in args:
        try:
            sure = int(args[args.index('--sure') + 1])
        except Exception:
            pass

    adb_forward()
    print('=' * 72)
    print('KENDİ VID — CANLI İZLEME  (%d saniye)' % sure)
    print('=' * 72)
    print('Vid gelmiyorsa BOTU SAVAŞTIR — savaş paketi ikinci kaynak.')
    print('Sadece rota modunda vid asla öğrenilemez.')
    print()
    print('%-9s %-12s %-6s %-6s %-16s %s'
          % ('saat', 'vid', 'oy', 'aday', 'isim', 'durum'))
    print('-' * 72)

    bitis = time.time() + sure
    onceki = None
    eski_apk_uyarildi = False
    while time.time() < bitis:
        k = get("/api/konum")
        if not k:
            print('%-9s API\'ye ulaşılamıyor (proxy/okuyucu açık mı?)'
                  % time.strftime('%H:%M:%S'))
            time.sleep(2.0)
            continue

        vid = int(k.get("kendiVid", 0) or 0)
        oy = k.get("kendiVidOyu", None)
        aday = k.get("kendiVidAday", None)
        if oy is None and not eski_apk_uyarildi:
            eski_apk_uyarildi = True
            print('!! APK oy bilgisi vermiyor — ESKİ SÜRÜM kurulu.')
            print('   Yeni APK\'yı kur: app/build/outputs/apk/debug/app-debug.apk')

        isim = ''
        durum = ''
        if vid:
            varliklar = get("/api/varliklar?n=150") or []
            if isinstance(varliklar, list):
                for v in varliklar:
                    if int(v.get("vid", 0) or 0) == vid:
                        isim = v.get("ad") or ''
                        if v.get("tip") in (TIP_MOB, TIP_METIN):
                            durum = 'X CANAVAR! vid yanlış'
                        break
            if not durum:
                if oy is None:
                    durum = '? oy bilinmiyor'
                elif oy < 3:
                    durum = 'yetersiz oy — bot hizalama göndermez'
                else:
                    durum = 'HAZIR'
        else:
            durum = 'henüz öğrenilmedi — savaş gerekiyor'

        satir = (vid, oy, aday, isim, durum)
        if satir != onceki:
            print('%-9s %-12s %-6s %-6s %-16s %s'
                  % (time.strftime('%H:%M:%S'),
                     vid or '-', oy if oy is not None else '?',
                     aday if aday is not None else '?',
                     isim or '-', durum))
            onceki = satir
        time.sleep(1.5)

    print('-' * 72)
    k = get("/api/konum") or {}
    vid = int(k.get("kendiVid", 0) or 0)
    oy = k.get("kendiVidOyu", 0)
    print()
    if vid and isinstance(oy, int) and oy >= 3:
        print('SONUÇ: vid %d öğrenildi (%s oy). Hizalama çalışabilir.' % (vid, oy))
        print('Elle sabitlemek istersen tambot > Hareket > "Kendi vid" alanına')
        print('%d yaz. Ama vid her girişte değişir — kalıcı değildir.' % vid)
    else:
        print('SONUÇ: vid öğrenilemedi.')
        print('  • Bot savaştı mı? "Sadece rota" kapalı, hedefleme açık olmalı')
        print('  • Yeni APK kurulu mu? (oy sütunu "?" ise eski sürüm)')
        print('  • Proxy oyuna bağlı ve enjeksiyon açık mı?')
    input('\nEnter...')


if __name__ == '__main__':
    main()
