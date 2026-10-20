# -*- coding: utf-8 -*-
"""
Kaydedilmiş rotalardan HANGİ HARİTA olduğunu ve TABAN KONUMUNU ölçer.

SORUN
-----
tools/harita_cikar.py 18 haritanın engel ızgarasını çıkarıyor, ama bir
ızgara tek başına işe yaramaz: dünya konumu (935413, 237836) o ızgaranın
neresine düşüyor? Bunu bilmek için haritanın TABAN KONUMU gerekiyor ve o
bilgi paketlerde yok — orijinal Metin2'de Setting.txt'de duruyor,
oyunun Unity sürümü onu paketlemiyor.

ÇÖZÜM: KAYITLI ROTA
-------------------
Kullanıcının gezerek kaydettiği her nokta tanım gereği GEÇİLEBİLİR.
Bu, hem haritayı hem tabanı bulmaya yetiyor:

  1. Rotanın kapladığı sektör sayısı haritayı daraltır (4x5 = 20 sektör
     olan haritalar).
  2. Taban, rotayı ızgaraya oturtan sektör hizası.
  3. Doğru harita, 241 noktanın hepsini AÇIK hücreye düşürendir.

Ölçüt KAZANÇ: rotanın serbestlik oranı eksi haritanın kendi serbestlik
oranı. Yalnızca "rota %100 serbest" bakmak yanıltıcı — engel bitinin hiç
set olmadığı bir harita da %100 alır ve hiçbir şey öğretmez.

KULLANIM
--------
    python tools/harita_hizala.py           # kitaplıktaki tüm rotalar
    python tools/harita_hizala.py "1.köy"
"""
import io
import json
import os
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
_HARITA = os.path.join(_KOK, 'harita')

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def dizin_oku():
    yol = os.path.join(_HARITA, 'harita.json')
    if not os.path.exists(yol):
        return None
    with io.open(yol, encoding='utf-8') as f:
        return json.load(f)


def izgara_oku(d, ad):
    h = d['haritalar'][ad]
    with open(os.path.join(_HARITA, h['dosya']), 'rb') as f:
        return h, f.read()


def engel(paket, g, cx, cy):
    i = cy * g + cx
    return bool(paket[i >> 3] & (1 << (i & 7)))


def rotalari_oku():
    """Kitaplık + o an açık rota."""
    rotalar = {}
    y = os.path.join(_KOK, 'tambot_rotalar.json')
    if os.path.exists(y):
        try:
            with io.open(y, encoding='utf-8') as f:
                for ad, kayit in json.load(f).items():
                    n = kayit.get('noktalar') if isinstance(kayit, dict) \
                        else kayit
                    if n:
                        rotalar[ad] = n
        except Exception:
            pass
    y = os.path.join(_KOK, 'tambot_ayar.json')
    if os.path.exists(y):
        try:
            with io.open(y, encoding='utf-8') as f:
                n = json.load(f).get('_rota')
            if n and not any(n == v for v in rotalar.values()):
                rotalar['(açık rota)'] = n
        except Exception:
            pass
    return rotalar


def hizala(d, nokta):
    """
    En iyi (harita, taban) adayını döndürür.

    TABAN ARANIR, VARSAYILMAZ
    -------------------------
    İlk sürüm tabanı en küçük noktadan türetiyordu: "rotanın en sol-üst
    sektörü haritanın 0. sektörüdür". Bu ancak gezilen alan haritanın
    KÖŞESİNE değiyorsa doğru. 1.köy ve 2.köy rotaları haritanın tamamını
    gezdiği için tesadüfen tuttu; haritanın ortasında dolaşan bir kayıt
    sessizce yanlış taban üretirdi ve duvarlar kaymış çizilirdi.

    Doğrusu: gezilen alan haritanın herhangi bir yerine düşebilir, o
    yüzden bütün olası sektör kaymaları denenir. Gezilen alan gsx x gsy
    sektörse, sx x sy'lik bir haritada (sx-gsx+1) x (sy-gsy+1) yerleşim
    var; hepsi puanlanır.

    Dar alanda gezmek birçok yerleşimi eşit puanlı bırakır — o zaman
    çağıran taraf KARARSIZ deyip hiza yazmıyor. Doğru davranış bu:
    tahmin edilmiş bir taban, hiç taban olmamasından kötü.

    Döner: (taban, adaylar) — adaylar (kazanç, nokta%, harita%, ad) dizisi.
    """
    sektor = d['sektor']
    hucre = d['hucre']
    xs = [p[0] for p in nokta]
    ys = [p[1] for p in nokta]
    sx0, sy0 = min(xs) // sektor, min(ys) // sektor
    gsx = max(xs) // sektor - sx0 + 1
    gsy = max(ys) // sektor - sy0 + 1

    adaylar = []
    for ad, h in d['haritalar'].items():
        if h['sx'] < gsx or h['sy'] < gsy:
            continue
        _, paket = izgara_oku(d, ad)
        g, y = h['g'], h['y']
        kapali = sum(bin(b).count('1') for b in paket)
        harita_serbest = 100.0 * (1.0 - kapali / float(g * y))
        for ox in range(h['sx'] - gsx + 1):
            for oy in range(h['sy'] - gsy + 1):
                tx = (sx0 - ox) * sektor
                ty = (sy0 - oy) * sektor
                serbest = 0
                for px, py in nokta:
                    cx, cy = (px - tx) // hucre, (py - ty) // hucre
                    if cx < 0 or cy < 0 or cx >= g or cy >= y:
                        serbest = -1
                        break
                    if not engel(paket, g, cx, cy):
                        serbest += 1
                if serbest < 0:
                    continue
                oran = 100.0 * serbest / len(nokta)
                adaylar.append((oran - harita_serbest, oran, harita_serbest,
                                ad, (tx, ty)))
    adaylar.sort(reverse=True)
    if not adaylar:
        return (sx0 * sektor, sy0 * sektor), []
    # Aynı haritanın farklı kaymaları listeyi doldurmasın: harita başına
    # yalnızca en iyi yerleşim gösterilir, ama İKİNCİ EN İYİ karşılaştırma
    # aynı haritanın rakip kaymasını da görmeli — o yüzden en iyi ikisi
    # ham listeden alınır.
    en_iyi_taban = adaylar[0][4]
    gorulen = set()
    ozet = []
    for kazanc, rp, mp, ad, taban in adaylar:
        if ad in gorulen:
            continue
        gorulen.add(ad)
        ozet.append((kazanc, rp, mp, ad))
    # Aynı harita içindeki ikinci en iyi kayma da bir rakip: kazancı
    # yakınsa hangi yerleşim olduğu belirsiz demektir.
    for kazanc, rp, mp, ad, taban in adaylar[1:]:
        if ad == adaylar[0][3] and taban != en_iyi_taban:
            ozet.insert(1, (kazanc, rp, mp, '%s @%d,%d' % (ad, taban[0],
                                                           taban[1])))
            break
    return en_iyi_taban, ozet


def main():
    d = dizin_oku()
    if not d:
        print('X harita/harita.json yok — önce:')
        print('    python tools/harita_cikar.py')
        return 1

    rotalar = rotalari_oku()
    if len(sys.argv) > 1:
        istenen = sys.argv[1]
        rotalar = {k: v for k, v in rotalar.items() if k == istenen}
        if not rotalar:
            print('X "%s" adında rota yok.' % istenen)
            return 1
    if not rotalar:
        print('X hiç kayıtlı rota yok. Önce bir köyde rota kaydet.')
        return 1

    taban_yolu = os.path.join(_HARITA, 'tabanlar.json')
    tabanlar = {}
    if os.path.exists(taban_yolu):
        try:
            with io.open(taban_yolu, encoding='utf-8') as f:
                tabanlar = json.load(f)
        except Exception:
            pass

    print('=' * 74)
    print('HARİTA HİZALAMA — kayıtlı rotalardan ölçüm')
    print('=' * 74)
    yazildi = 0
    for ad, nokta in sorted(rotalar.items()):
        print()
        print('--- %s  (%d nokta) ---' % (ad, len(nokta)))
        (tx, ty), adaylar = hizala(d, nokta)
        if not adaylar:
            print('  X uyan harita yok (rota hiçbir ızgaraya sığmadı)')
            continue
        print('  taban konum: %d, %d' % (tx, ty))
        print('  %-30s %8s %9s %8s' % ('harita', 'rota', 'harita', 'kazanç'))
        for kazanc, rp, mp, h in adaylar[:4]:
            print('  %-30s %7.1f%% %8.1f%% %+7.1f' % (h, rp, mp, kazanc))

        en = adaylar[0]
        ikinci = adaylar[1] if len(adaylar) > 1 else (0, 0, 0, '')
        fark = en[0] - ikinci[0]
        print()
        if en[1] < 90.0:
            print('  ? KARARSIZ: en iyi adayda bile rotanın %%%.1f\'i açık.'
                  % en[1])
            print('    Rota yanlış haritada kaydedilmiş olabilir.')
            continue
        if fark < 10.0 and ikinci[3]:
            print('  ? KARARSIZ: %s ile %s arasındaki fark yalnızca %.1f puan.'
                  % (en[3], ikinci[3], fark))
            print('    Daha uzun bir rota kaydedince ayrışır.')
            continue
        print('  ✓ %s — rota %%%.1f serbest, harita %%%.1f  (kazanç %+.1f)'
              % (en[3], en[1], en[2], en[0]))
        eski = tabanlar.get(en[3])
        if eski and tuple(eski) != (tx, ty):
            print('  ! bu harita daha önce %s olarak hizalanmıştı — '
                  'yenisi yazılıyor' % (eski,))
        tabanlar[en[3]] = [tx, ty]
        yazildi += 1

    if yazildi:
        with io.open(taban_yolu, 'w', encoding='utf-8') as f:
            json.dump(tabanlar, f, ensure_ascii=False, indent=2,
                      sort_keys=True)
        for ad, h in d['haritalar'].items():
            h['taban'] = tabanlar.get(ad)
        with io.open(os.path.join(_HARITA, 'harita.json'), 'w',
                     encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)
        print()
        print('%d harita hizalandı -> harita/tabanlar.json' % yazildi)
        # Panel radarı duvarları APK assets'inden okuyor; iki kopya
        # ayrışmasın diye yeni hiza oraya da yazılır.
        try:
            sys.path.insert(0, _BURASI)
            from harita_cikar import assetlere_kopyala
            n = assetlere_kopyala()
            if n:
                print('%d dosya APK assets dizinine kopyalandı — panelde '
                      'görmek için APK yeniden derlenmeli' % n)
        except Exception as e:
            print('! assets kopyalanamadı: %s' % e)
    print()
    print('hizalı harita: %d / %d'
          % (sum(1 for v in d['haritalar'].values() if v.get('taban')),
             len(d['haritalar'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
