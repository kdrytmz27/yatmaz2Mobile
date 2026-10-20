# -*- coding: utf-8 -*-
"""
Bulunduğun haritayı GEZEREK hizalar — rota kaydetmeye gerek yok.

NEDEN AYRI BİR ARAÇ
-------------------
tools/harita_hizala.py kayıtlı rotalardan ölçüyor. Ama yeni bir haritaya
girdiğinde elinde henüz rota yok: önce rota kaydet, kaydet düğmesine bas,
sonra hizala — üç adım, üçü de unutulabilir. Oysa gereken şey rota
DEĞİL, sadece "buradan geçtim" diyen bir avuç nokta.

Bu araç onu doğrudan topluyor: sen oyunda yürürken panelin konumunu
okuyor. Yürüdüğün her nokta tanım gereği geçilebilir olduğu için ölçüt
aynı kalıyor.

NASIL KARAR VERİYOR
-------------------
Toplanan noktalar hem haritayı hem tabanı veriyor:

  1. Noktaların kapladığı sektör sayısı haritayı daraltır
  2. Taban, noktaları ızgaraya oturtan sektör hizası
  3. Doğru harita, noktaların HEPSİNİ açık hücreye düşürendir

Ölçüt KAZANÇ: noktaların serbestlik oranı eksi haritanın kendi
serbestlik oranı. Yalnızca "%100 serbest"e bakmak yanıltıcı olurdu —
engel bitinin hiç set olmadığı bir harita da onu alır.

DAR ALANDA GEZME
----------------
Tek bir sektörde dolaşırsan birçok harita aynı skoru alır ve araç
KARARSIZ der. Ayrışması için köşeleri gez: harita ne kadar çok
sektörüne değersen o kadar kesin ayrışır.

KULLANIM
--------
    python tools/harita_hizala_canli.py            # 90 saniye
    python tools/harita_hizala_canli.py --sure 150
"""
import io
import json
import os
import sys
import time

try:
    from urllib.request import urlopen
except ImportError:                                   # py2
    from urllib2 import urlopen                       # noqa

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
_HARITA = os.path.join(_KOK, 'harita')
sys.path.insert(0, _BURASI)

from harita_hizala import dizin_oku, hizala           # noqa: E402

ADRES = os.environ.get('R2_ADRES', '127.0.0.1:30200')
# İki nokta arasında en az bu kadar ham fark olsun; aynı yerde durunca
# aynı nokta yüzlerce kez toplanmasın.
EN_AZ_FARK = 300

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def konum_oku():
    """Panelden ham konum. Okunamazsa None."""
    try:
        ham = urlopen('http://%s/api/durum' % ADRES, timeout=3).read()
    except Exception:
        return None
    try:
        d = json.loads(ham.decode('utf-8-sig', 'replace'))
    except Exception:
        return None
    k = d.get('konum') or {}
    if not k.get('bilinir'):
        return None
    try:
        return int(k['x']), int(k['y'])
    except (KeyError, TypeError, ValueError):
        return None


def topla(sure):
    """Sen yürürken konumları toplar."""
    nokta = []
    son = None
    bitis = time.time() + sure
    yazildi = 0
    print('  >>> ŞİMDİ OYUNDA GEZ — %d saniye <<<' % sure)
    print('      Haritanın farklı köşelerine git; dar alanda dolaşırsan')
    print('      birden çok harita aynı skoru alır ve karar çıkmaz.')
    print()
    while time.time() < bitis:
        p = konum_oku()
        if p and (son is None
                  or abs(p[0] - son[0]) + abs(p[1] - son[1]) >= EN_AZ_FARK):
            nokta.append(list(p))
            son = p
        kalan = int(bitis - time.time())
        if kalan != yazildi:
            yazildi = kalan
            sys.stdout.write('\r      %3d sn kaldı   %4d nokta   '
                             % (kalan, len(nokta)))
            sys.stdout.flush()
        time.sleep(0.4)
    print('\r      toplandı: %d nokta%s' % (len(nokta), ' ' * 20))
    return nokta


def main():
    args = sys.argv[1:]
    sure = 90
    if '--sure' in args:
        try:
            sure = max(20, int(args[args.index('--sure') + 1]))
        except Exception:
            pass

    print('=' * 74)
    print('CANLI HARİTA HİZALAMA')
    print('=' * 74)

    d = dizin_oku()
    if not d:
        print('X harita/harita.json yok — önce:')
        print('    python tools/harita_cikar.py')
        return 1

    if konum_oku() is None:
        print('X panelden konum okunamadı (%s).' % ADRES)
        print('  Oyun açık, proxy açık ve şu yönlendirme kurulu olmalı:')
        print('    adb forward tcp:30200 tcp:30200')
        return 1

    nokta = topla(sure)
    if len(nokta) < 12:
        print()
        print('X yalnızca %d nokta toplandı — yeterli değil.' % len(nokta))
        print('  Kayıt sırasında gerçekten yürümen gerekiyor.')
        return 1

    xs = [p[0] for p in nokta]
    ys = [p[1] for p in nokta]
    sektor = d['sektor']
    gsx = max(xs) // sektor - min(xs) // sektor + 1
    gsy = max(ys) // sektor - min(ys) // sektor + 1
    print()
    print('  gezilen alan: x %d..%d   y %d..%d   (%dx%d sektör)'
          % (min(xs), max(xs), min(ys), max(ys), gsx, gsy))

    (tx, ty), adaylar = hizala(d, nokta)
    if not adaylar:
        print('  X uyan harita yok — gezilen alan hiçbir ızgaraya sığmadı.')
        return 1

    print('  taban konum : %d, %d' % (tx, ty))
    print()
    print('  %-30s %8s %9s %8s' % ('harita', 'gezilen', 'harita', 'kazanç'))
    for kazanc, rp, mp, h in adaylar[:5]:
        print('  %-30s %7.1f%% %8.1f%% %+7.1f' % (h, rp, mp, kazanc))

    en = adaylar[0]
    ikinci = adaylar[1] if len(adaylar) > 1 else (0, 0, 0, '')
    fark = en[0] - ikinci[0]
    print()
    if en[1] < 90.0:
        print('  ? KARARSIZ: en iyi adayda bile gezdiğin yerin %%%.1f\'i açık.'
              % en[1])
        # Sebebi ayır: dar alan mı, yoksa gerçekten uymayan harita mı?
        # İkisinin çaresi farklı ve tek bir mesaj kullanıcıyı yanlış
        # yöne gönderirdi.
        if gsx * gsy <= 2:
            print('    Yalnızca %dx%d sektör gezdin (%d x %d m). Bu kadar dar'
                  % (gsx, gsy, (max(xs) - min(xs)) // 100,
                     (max(ys) - min(ys)) // 100))
            print('    bir alan haritayı ayırt etmeye yetmiyor — köşelere git.')
        else:
            print('    Bu harita çıkarılan 18 haritadan biri olmayabilir.')
        print('    NOT: bot çalışırken ölçme. Bot karakteri duvarın')
        print('    içinden geçirebiliyor; o noktalar "geçilebilir" değil.')
        return 1
    if fark < 10.0 and ikinci[3]:
        print('  ? KARARSIZ: %s ile %s arasındaki fark %.1f puan.'
              % (en[3], ikinci[3], fark))
        print('    Daha geniş gez (farklı sektörlere değ) ve tekrar dene.')
        return 1

    print('  ✓ %s — gezilen %%%.1f serbest, harita %%%.1f  (kazanç %+.1f)'
          % (en[3], en[1], en[2], en[0]))

    taban_yolu = os.path.join(_HARITA, 'tabanlar.json')
    tabanlar = {}
    if os.path.exists(taban_yolu):
        try:
            with io.open(taban_yolu, encoding='utf-8') as f:
                tabanlar = json.load(f)
        except Exception:
            pass
    eski = tabanlar.get(en[3])
    if eski and tuple(eski) != (tx, ty):
        print('  ! %s daha önce %s olarak hizalanmıştı — yenisi yazılıyor'
              % (en[3], eski))
    tabanlar[en[3]] = [tx, ty]
    with io.open(taban_yolu, 'w', encoding='utf-8') as f:
        json.dump(tabanlar, f, ensure_ascii=False, indent=2, sort_keys=True)
    for ad, h in d['haritalar'].items():
        h['taban'] = tabanlar.get(ad)
    with io.open(os.path.join(_HARITA, 'harita.json'), 'w',
                 encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)

    try:
        from harita_cikar import assetlere_kopyala
        n = assetlere_kopyala()
        if n:
            print('  %d dosya APK assets dizinine kopyalandı' % n)
    except Exception as e:
        print('  ! assets kopyalanamadı: %s' % e)

    print()
    print('hizalı harita: %d / %d'
          % (sum(1 for v in d['haritalar'].values() if v.get('taban')),
             len(d['haritalar'])))
    print()
    print('Masaüstü bot için: tambot penceresini kapatıp aç.')
    print('Panel radarı için: APK yeniden derlenip kurulmalı ->')
    print('    gradlew assembleDebug')
    print('    adb install -r app/build/outputs/apk/debug/app-debug.apk')
    return 0


if __name__ == '__main__':
    sys.exit(main())
