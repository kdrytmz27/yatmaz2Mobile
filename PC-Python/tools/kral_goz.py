# -*- coding: utf-8 -*-
"""
KRALI YAKALA — GÖZ (ekranı okur)

Paket yolunda cevaplar 1-4 saniye gecikiyordu; oyun o hızda doğru oynanamıyor.
Bu yüzden durumu paketten ÇIKARMAK yerine EKRANDAN OKUYORUZ: masadaki 25 kart,
eldeki kart ve puan zaten ekranda yazıyor.

Kartlar renkten tanınır (ölçülen gerçek değerler):
    kapalı (8,57,50) turkuaz | 1 yeşil | 2 turuncu | 3 sarı | 4 mor | 5 mavi | K kırmızı
Ton (hue) kullanıldığı için kartın parlak ya da soluk olması sonucu bozmaz.

KULLANIM
--------
    python tools/kral_goz.py                # telefondan oku ve masayı yaz
    python tools/kral_goz.py --dosya x.png  # var olan görüntüyü oku
    python tools/kral_goz.py --surekli 10   # 10 kez üst üste oku (kararlılık testi)

Çıktı: log/kral_ekran.png ve log/kral_ekran_isaretli.png
"""

import argparse
import colorsys
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

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError as e:                                # noqa: BLE001
    print('X Pillow/numpy gerekli:', e)
    sys.exit(1)

import kanal_bul as kb                                  # noqa: E402

# Ölçülen referans tonlar (derece). Ton kullanıyoruz: parlaklık değişse de
# kartın rengi aynı kalır, böylece soluk/parlak ayrımı sonucu bozmaz.
TONLAR = {"kapali": 170.0, 1: 95.0, 2: 34.0, 3: 51.0, 4: 302.0, 5: 220.0, 6: 12.0}
AD = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "K",
      "kapali": "?", "kafa": "\u2620"}   # ☠ = kapalı + yakında 5


def ekran_al():
    """adb ile telefondan ekran görüntüsü (telefonun KENDİ koordinatları)."""
    adb = kb.adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        return None
    dev = subprocess.run([adb, 'devices'], capture_output=True,
                         timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in dev:
        print('X Cihaz bağlı değil (adb devices boş).')
        return None
    t0 = time.time()
    ham = subprocess.run([adb, 'exec-out', 'screencap', '-p'],
                         capture_output=True, timeout=30).stdout
    if not ham or len(ham) < 1000:
        print('X Ekran görüntüsü alınamadı.')
        return None
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    yol = os.path.join(_KOK, 'log', 'kral_ekran.png')
    with open(yol, 'wb') as f:
        f.write(ham)
    try:
        _im = Image.open(yol)
        print('ekran alındı (%.0f ms) — %d x %d'
              % ((time.time() - t0) * 1000, _im.width, _im.height))
    except Exception:                                   # noqa: BLE001
        print('ekran alındı (%.0f ms)' % ((time.time() - t0) * 1000))
    return yol


def _ton(rgb):
    r, g, b = [v / 255.0 for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0, l, s


def _fark(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def sinifla(rgb):
    """Kartın ortanca rengini karta çevirir.

    Döner: 1-6 (açık kart), 'kapali', 'kafa' (kapalı + kuru kafa) ya da None.
    Kapalı sırt ile kuru kafalı kart AYNI tonda (turkuaz) ama parlaklıkları
    çok farklı: sırt (4,55,47) koyu, kuru kafa (104,149,161) açık.
    """
    h, l, s = _ton(rgb)
    if l < 0.06 or s < 0.10:
        return None                                    # zemin / belirsiz
    # turkuaz ailesi: koyu = kapalı, açık = kuru kafa (yakında 5 uyarısı)
    if _fark(h, 175.0) <= 35.0:
        return 'kafa' if l > 0.32 else 'kapali'
    if s < 0.15:
        return None
    en_iyi, en_fark = None, 999.0
    for k, t in TONLAR.items():
        if k == 'kapali':
            continue
        d = _fark(h, t)
        if d < en_fark:
            en_iyi, en_fark = k, d
    return en_iyi if en_fark <= 28.0 else None


def _kart_maskesi(a):
    """Kapalı kart sırtı: koyu turkuaz (8,57,50)."""
    r = a[:, :, 0].astype(np.int16)
    g = a[:, :, 1].astype(np.int16)
    b = a[:, :, 2].astype(np.int16)
    return (g > r + 12) & (b > r + 4) & (g > 45) & (g < 190) & (r < 130)


def _bloklar(mask, en_az):
    h, w = mask.shape
    gor = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if gor[y0, x0]:
            continue
        yig = [(y0, x0)]
        gor[y0, x0] = True
        miny = maxy = y0
        minx = maxx = x0
        say = 0
        while yig:
            y, x = yig.pop()
            say += 1
            miny = min(miny, y); maxy = max(maxy, y)
            minx = min(minx, x); maxx = max(maxx, x)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not gor[ny, nx]:
                    gor[ny, nx] = True
                    yig.append((ny, nx))
        if say >= en_az:
            out.append((minx, miny, maxx, maxy, say))
    return out


def _kumele(degerler, esik):
    """Yakın değerleri gruplayıp her grubun ortasını döndürür."""
    if not degerler:
        return []
    d = sorted(degerler)
    gruplar = [[d[0]]]
    for v in d[1:]:
        if v - gruplar[-1][-1] <= esik:
            gruplar[-1].append(v)
        else:
            gruplar.append([v])
    return [sum(g) / float(len(g)) for g in gruplar]


def masa_bul(a):
    """Kapalı kart bloklarından 5x5 ızgarayı çıkarır. Döner: (merkezler, hucre)."""
    h, w = a.shape[:2]
    bloklar = _bloklar(_kart_maskesi(a), en_az=max(400, (w * h) // 6000))
    kartlar = []
    for x0, y0, x1, y1, say in bloklar:
        gw, gh = x1 - x0 + 1, y1 - y0 + 1
        if gw < 18 or gh < 18:
            continue
        if not (0.5 <= gw / float(gh) <= 1.9):
            continue
        if say < 0.35 * gw * gh:
            continue
        kartlar.append((x0, y0, x1, y1))
    if len(kartlar) < 4:
        return None, None, kartlar
    gwm = int(np.median([x1 - x0 for x0, _, x1, _ in kartlar]))
    ghm = int(np.median([y1 - y0 for _, y0, _, y1 in kartlar]))
    sutun = _kumele([(x0 + x1) / 2.0 for x0, _, x1, _ in kartlar], gwm * 0.6)
    satir = _kumele([(y0 + y1) / 2.0 for _, y0, _, y1 in kartlar], ghm * 0.6)
    # 5'e tamamla (açık kartlar maskede yok; aradaki boşlukları doldur)
    def tamamla(k, adim):
        k = list(k)
        if len(k) >= 5:
            return k[:5]
        if len(k) < 2:
            return None
        ad = np.median(np.diff(k)) if len(k) > 1 else adim
        while len(k) < 5:
            k.append(k[-1] + ad)
        return k
    sutun = tamamla(sutun, gwm * 1.25)
    satir = tamamla(satir, ghm * 1.25)
    if not sutun or not satir:
        return None, None, kartlar
    merkez = [(int(x), int(y)) for y in satir for x in sutun]
    return merkez, (gwm, ghm), kartlar


def _orta_renk(a, x, y, r):
    b = a[max(0, y - r):y + r, max(0, x - r):x + r].reshape(-1, 3)
    if not len(b):
        return (0, 0, 0)
    return tuple(int(v) for v in np.median(b, axis=0))


def kartim_bul(a, merkez, hucre):
    """Masanın SAĞINDAKİ 'Kartım' kartını bulup sınıflandırır.

    Masa ızgarası bilindiği için 'Kartım' onun sağında, ilk satır hizasında
    aranır. Kart rengi doygun olduğundan en doygun blok seçilir."""
    gw, gh = hucre
    sag = max(x for x, _ in merkez)
    ust = min(y for _, y in merkez)
    x0 = int(sag + 0.6 * gw)
    x1 = int(sag + 3.2 * gw)
    y0 = int(ust - 1.0 * gh)
    y1 = int(ust + 1.6 * gh)
    h, w = a.shape[:2]
    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None, None
    bolge = a[y0:y1, x0:x1]
    # en doygun ve yeterince aydınlık pikselleri bul
    mx = bolge.max(axis=2).astype(np.int16)
    mn = bolge.min(axis=2).astype(np.int16)
    doy = mx - mn
    mask = (doy > 55) & (mx > 90)
    if mask.sum() < 40:
        return None, (x0, y0, x1, y1)
    ys, xs = np.nonzero(mask)
    cx, cy = int(np.median(xs)), int(np.median(ys))
    rgb = _orta_renk(bolge, cx, cy, max(5, min(gw, gh) // 5))
    return sinifla(rgb), (x0, y0, x1, y1)


def oku(yol, ciz_kaydet=True):
    im = Image.open(yol).convert('RGB')
    a = np.asarray(im)
    merkez, hucre, kartlar = masa_bul(a)
    if not merkez:
        print('! Masa bulunamadı (%d kart bloğu). Oyunda Kralı Yakala penceresi '
              'açık mı?' % len(kartlar))
        return None
    gw, gh = hucre
    r = max(6, min(gw, gh) // 4)
    masa = []
    for (x, y) in merkez:
        masa.append(sinifla(_orta_renk(a, x, y, r)))

    print('MASA (5x5):')
    for i in range(5):
        print('   ' + '  '.join(
            ('%2s' % AD.get(masa[i * 5 + j], '·')) for j in range(5)))
    kapali = sum(1 for m in masa if m == 'kapali')
    acik = sum(1 for m in masa if isinstance(m, int))
    print('kapalı %d, okunan %d, belirsiz %d' % (kapali, acik, 25 - kapali - acik))
    sx = [x for x, _ in merkez[:5]]
    sy = [y for i, (_, y) in enumerate(merkez) if i % 5 == 0]
    print('ızgara: sütunlar x=%s' % sx)
    print('        satırlar y=%s   hücre=%dx%d' % (sy, gw, gh))
    el, kb_ = kartim_bul(a, merkez, hucre)
    print('KARTIM : %s' % (AD.get(el, 'boş/okunamadı'),))
    deste = deste_oku(a, merkez, hucre)
    if deste:
        print('DESTE  : %s' % '  '.join(
            '%s' % AD.get(k, k) for k in sorted(deste)))
    else:
        print('DESTE  : okunamadı')
    kafalar = [i for i, m in enumerate(masa) if m == 'kafa']
    if kafalar:
        print('KURU KAFA (yakında 5): %s' % kafalar)

    if ciz_kaydet:
        ciz = im.copy()
        d = ImageDraw.Draw(ciz)
        for idx, (x, y) in enumerate(merkez):
            renk = (0, 255, 0) if masa[idx] == 'kapali' else (
                (255, 80, 80) if masa[idx] is None else (80, 160, 255))
            d.rectangle([x - gw // 2, y - gh // 2, x + gw // 2, y + gh // 2],
                        outline=renk, width=3)
            d.text((x - 6, y - 8), AD.get(masa[idx], '·'), fill=(255, 255, 255))
        if kb_:
            d.rectangle(list(kb_), outline=(255, 255, 0), width=3)
            d.text((kb_[0] + 4, kb_[1] + 4), 'KARTIM', fill=(255, 255, 0))
        cikti = os.path.join(_KOK, 'log', 'kral_ekran_isaretli.png')
        ciz.save(cikti)
        print('işaretli görüntü: %s' % cikti)
    return masa


def ekrana_bas(x, y):
    """adb 'input tap' — DISPLAY koordinatı alır, screencap ile aynı uzay."""
    adb = kb.adb_bul()
    if not adb:
        return False, 'adb yok'
    t0 = time.time()
    r = subprocess.run([adb, 'shell', 'input', 'tap', str(int(x)), str(int(y))],
                       capture_output=True, timeout=20)
    ms = (time.time() - t0) * 1000
    cikti = (r.stdout or b'').decode('utf-8', 'replace').strip()
    hata = (r.stderr or b'').decode('utf-8', 'replace').strip()
    return r.returncode == 0 and not hata, '%.0f ms%s%s' % (
        ms, ('  ' + cikti) if cikti else '', ('  HATA:' + hata) if hata else '')


def deste_oku(a, merkez, hucre):
    """Alt sıradaki kartları TESPİT ederek bulur. Döner: {kart: (x, y)}.

    Konumu formülle hesaplamak kayıyordu (6. kartta ~24 px sapma), bu yüzden
    masanın altındaki doygun renkli blokları buluyoruz. Kart ölçüsüne uymayan
    bloklar (pencere dışındaki çimen vb.) boyutla elenir.
    """
    gh = (merkez[5][1] - merkez[0][1]) or hucre[1]
    alt = merkez[-1][1]
    y0 = int(alt + 0.7 * gh)
    y1 = int(alt + 2.3 * gh)
    h, w = a.shape[:2]
    y0, y1 = max(0, y0), min(h, y1)
    if y1 - y0 < 10:
        return {}
    bolge = a[y0:y1]
    mx = bolge.max(axis=2).astype(np.int16)
    mn = bolge.min(axis=2).astype(np.int16)
    mask = ((mx - mn) > 35) & (mx > 55)
    bulunan = {}
    for x0, by0, x1, by1, say in _bloklar(mask, en_az=800):
        gw2, gh2 = x1 - x0 + 1, by1 - by0 + 1
        if not (60 <= gw2 <= 200 and 45 <= gh2 <= 140):
            continue                                   # kart ölçüsü değil
        cx, cy = (x0 + x1) // 2, (by0 + by1) // 2 + y0
        k = sinifla(_orta_renk(a, cx, cy, max(8, gw2 // 6)))
        if isinstance(k, int) and k not in bulunan:
            bulunan[k] = (cx, cy)
    return bulunan


def durum_oku(yol=None):
    """Ekranı okuyup (masa, elkart, merkezler, hucre) döndürür. Çizim yok."""
    yol = yol or ekran_al()
    if not yol:
        return None
    im = Image.open(yol).convert('RGB')
    a = np.asarray(im)
    merkez, hucre, _ = masa_bul(a)
    if not merkez:
        return None
    gw, gh = hucre
    r = max(6, min(gw, gh) // 4)
    masa = [sinifla(_orta_renk(a, x, y, r)) for (x, y) in merkez]
    el, _kb = kartim_bul(a, merkez, hucre)
    return {"masa": masa, "el": el, "merkez": merkez, "hucre": hucre,
            "deste": deste_oku(a, merkez, hucre),
            "kafa": [i for i, m in enumerate(masa) if m == 'kafa']}


def tikla_dene(pos):
    """pos'a DOKUNUP sonucu ekrandan doğrular — eylem yolu çalışıyor mu?

    Telefonun kendi koordinatlarını kullanıyoruz (adb screencap native çözünürlük
    verir), bu yüzden /api/dokun için dönüştürme gerekmez."""
    onceki = durum_oku()
    if not onceki:
        print('X masa okunamadı')
        return
    if not (0 <= pos < 25):
        print('X pos 0-24 arası olmalı')
        return
    print('ÖNCE : hücre[%d] = %s   |  elde: %s'
          % (pos, AD.get(onceki["masa"][pos], '·'), AD.get(onceki["el"], '?')))
    x, y = onceki["merkez"][pos]
    print('dokunuluyor: (%d, %d)' % (x, y))
    t0 = time.time()
    ok, bilgi = ekrana_bas(x, y)
    print('  input tap: %s  (%s)' % ('tamam' if ok else 'BAŞARISIZ', bilgi))

    for bekle in (0.6, 1.2, 2.0):
        time.sleep(bekle)
        sonra = durum_oku()
        if not sonra:
            continue
        yeni = sonra["masa"][pos]
        if yeni != onceki["masa"][pos] or sonra["el"] != onceki["el"]:
            print('SONRA: hücre[%d] = %s   |  elde: %s   (%.1f sn sonra)'
                  % (pos, AD.get(yeni, '·'), AD.get(sonra["el"], '?'),
                     time.time() - t0))
            degisen = [i for i in range(25)
                       if sonra["masa"][i] != onceki["masa"][i]]
            print('değişen hücreler:', degisen)
            print('SONUÇ: TIKLAMA ÇALIŞIYOR — eylem yolu hazır.')
            return
    print('SONUÇ: ekranda değişiklik göremedim.')
    print('  Olasılıklar: (a) oyun input tap kabul etmiyor → /api/dokun ile')
    print('  ham koordinat eşlemesi kurarız, (b) koordinat ızgarası kaymış.')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kralı Yakala ekran okuma')
    ap.add_argument('--dosya', help='var olan PNG üzerinde çalış')
    ap.add_argument('--surekli', type=int, default=0,
                    help='N kez üst üste oku (kararlılık testi)')
    ap.add_argument('--tikla', type=int, default=-1,
                    help='0-24: o hücreye dokun ve sonucu ekrandan doğrula')
    a = ap.parse_args(argv)
    if a.tikla >= 0:
        tikla_dene(a.tikla)
        return
    if a.surekli:
        for i in range(a.surekli):
            yol = a.dosya or ekran_al()
            if not yol:
                return
            print('--- okuma %d ---' % (i + 1))
            oku(yol, ciz_kaydet=(i == 0))
            time.sleep(0.3)
        return
    yol = a.dosya or ekran_al()
    if yol:
        oku(yol)


if __name__ == '__main__':
    main()
