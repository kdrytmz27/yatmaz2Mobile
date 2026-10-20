# -*- coding: utf-8 -*-
"""
PAZAR FIRSAT TAKİBİ — anlık. Ucuzlayanı ve yeni çıkanı hemen yakalar.

Önbellek burada "eski veri" değil, KIYAS TABANIdır: bir şeyin ucuzladığını
söyleyebilmek için eski fiyatını bilmek gerekir. Gösterilen şey hep canlı.

Üç tür fırsat:
    YENİ      — bu eşya daha önce hiç görülmedi
    UCUZLADI  — aynı eşya, gördüğümüz en düşük fiyatın altında
    HEDEF     — izleme listendeki kurala uyuyor (ad / azami fiyat / efsun)

Fiyat geçmişi vnum başına tutulur (veri/pazar_fiyat.json): en düşük, en son,
kaç kez görüldü. Böylece "350.000 normal mi ucuz mu" sorusuna cevap verebiliriz.
"""

import json
import os
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)

FIYAT_DOSYA = os.path.join(_KOK, 'veri', 'pazar_fiyat.json')


def ad_fold(s):
    """Türkçe-duyarsız (bkz. pazar_tara.ad_fold — büyükler ÖNCE çevrilir)."""
    s = (s or '').strip()
    for a, b in (('İ', 'I'), ('Ş', 'S'), ('Ğ', 'G'), ('Ü', 'U'),
                 ('Ö', 'O'), ('Ç', 'C'), ('Â', 'A'), ('Î', 'I')):
        s = s.replace(a, b)
    s = s.lower().replace('̇', '')
    for a, b in (('ı', 'i'), ('ş', 's'), ('ğ', 'g'), ('ü', 'u'),
                 ('ö', 'o'), ('ç', 'c'), ('â', 'a'), ('î', 'i')):
        s = s.replace(a, b)
    return s


class Kural:
    """İzleme kuralı: ad parçası + azami fiyat + efsun + en az değer."""

    def __init__(self, ad='', azami=0, efsun='', en_az=0):
        self.ad = ad
        self.azami = int(azami or 0)
        self.efsun = efsun
        self.en_az = int(en_az or 0)

    def uyar_mi(self, esya_adi, fiyat, efsunlar):
        if self.ad and ad_fold(self.ad) not in ad_fold(esya_adi):
            return False
        if self.azami and fiyat > self.azami:
            return False
        if self.efsun:
            ef = ad_fold(self.efsun)
            if not any(ef in ad_fold(x.get('ad', ''))
                       and x.get('deger', 0) >= self.en_az
                       for x in (efsunlar or [])):
                return False
        return True

    def metin(self):
        p = [self.ad or 'her eşya']
        if self.azami:
            p.append('≤ %s' % '{:,}'.format(self.azami).replace(',', '.'))
        if self.efsun:
            p.append('%s ≥ %d' % (self.efsun, self.en_az))
        return '  '.join(p)

    def sozluk(self):
        return {'ad': self.ad, 'azami': self.azami,
                'efsun': self.efsun, 'en_az': self.en_az}


class FiyatGecmisi:
    """vnum → {en_dusuk, son, gorulme}. Ucuzlamayı bundan anlarız."""

    def __init__(self, yol=FIYAT_DOSYA):
        self.yol = yol
        self.tablo = {}
        self.yukle()

    def yukle(self):
        try:
            with open(self.yol, encoding='utf-8') as f:
                self.tablo = {int(k): v for k, v in json.load(f).items()}
        except Exception:                               # noqa: BLE001
            self.tablo = {}

    def kaydet(self):
        try:
            os.makedirs(os.path.dirname(self.yol), exist_ok=True)
            with open(self.yol, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in self.tablo.items()}, f)
        except Exception:                               # noqa: BLE001
            pass

    def bak(self, vnum):
        return self.tablo.get(int(vnum))

    def isle(self, vnum, fiyat):
        """Döner: ('yeni'|'ucuzladi'|None, eski_en_dusuk)."""
        vnum = int(vnum)
        k = self.tablo.get(vnum)
        if k is None:
            self.tablo[vnum] = {'en_dusuk': fiyat, 'son': fiyat, 'gorulme': 1}
            return 'yeni', None
        eski = k['en_dusuk']
        k['son'] = fiyat
        k['gorulme'] = k.get('gorulme', 0) + 1
        if fiyat < eski:
            k['en_dusuk'] = fiyat
            return 'ucuzladi', eski
        return None, eski


class FirsatAvcisi:
    """Gelen dükkân içeriğini kurallara ve fiyat geçmişine göre süzer."""

    def __init__(self, adlar, gecmis=None, kurallar=None, bildir=None):
        self.adlar = adlar
        self.gecmis = gecmis or FiyatGecmisi()
        self.kurallar = list(kurallar or [])
        self.bildir = bildir or (lambda f: None)
        self.firsatlar = []          # en yeni başta
        self._gorulen = set()        # (vid, slot, fiyat) — aynısını tekrarlama

    def dukkan(self, vid, dukkan_adi, esyalar):
        """Bir dükkânın içeriğini işle. Döner: bulunan fırsat sayısı."""
        n = 0
        for e in esyalar:
            anahtar = (vid, e.get('slot'), e.get('fiyat'))
            if anahtar in self._gorulen:
                continue
            self._gorulen.add(anahtar)
            fiyat = e.get('fiyat', 0)
            if fiyat <= 0:
                continue                  # fiyatsız/boş
            vnum = e.get('vnum')
            ead = self.adlar.ad(vnum)
            efs = e.get('efsunlar') or []
            tur, eski = self.gecmis.isle(vnum, fiyat)
            kural = next((k for k in self.kurallar
                          if k.uyar_mi(ead, fiyat, efs)), None)
            if not kural and tur != 'ucuzladi':
                continue                  # ilgimizi çekmiyor
            f = {'zaman': time.time(), 'vid': vid, 'dukkan': dukkan_adi,
                 'esya': ead, 'vnum': vnum, 'fiyat': fiyat,
                 'adet': e.get('adet', 1), 'efsunlar': efs,
                 'tur': 'HEDEF' if kural else 'UCUZLADI',
                 'eski_fiyat': eski}
            if tur == 'yeni' and kural:
                f['tur'] = 'HEDEF'
            self.firsatlar.insert(0, f)
            del self.firsatlar[400:]
            n += 1
            try:
                self.bildir(f)
            except Exception:                           # noqa: BLE001
                pass
        return n

    def temizle(self):
        self.firsatlar = []
        self._gorulen = set()
