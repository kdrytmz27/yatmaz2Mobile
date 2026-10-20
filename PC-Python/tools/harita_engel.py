# -*- coding: utf-8 -*-
"""
Gidilemez yer haritası — bot bunu okuyup duvara girmeden yol bulur.

Veri tools/harita_cikar.py ile oyundan çıkarıldı, taban konumları
tools/harita_hizala.py ile kayıtlı rotalardan ölçüldü. Ayrıntılı
gerekçe o iki dosyanın başında.

KULLANIM
--------
    h = Harita.yukle()
    h.hangi_harita(x, y)        -> 'metin2_map_c1' ya da None
    h.engel_mi(x, y)            -> True/False
    h.gorus_acik(ax, ay, bx, by)-> aradaki doğru temiz mi
    h.yol_bul(ax, ay, bx, by)   -> [(x, y), ...] ara noktalar
"""
import heapq
import io
import json
import os

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
_DIZIN = os.path.join(_KOK, 'harita')


class Harita(object):
    """Tek bir haritanın engel ızgarası."""

    def __init__(self, ad, taban, g, y, paket, hucre):
        self.ad = ad
        self.taban_x, self.taban_y = taban
        self.g = g                  # hücre cinsinden genişlik
        self.y = y
        self.paket = paket          # hücre başına 1 bit
        self.hucre = hucre          # bir hücre kaç ham birim

    # ---- temel sorgular ----

    def icinde_mi(self, x, y):
        gx, gy = x - self.taban_x, y - self.taban_y
        return 0 <= gx < self.g * self.hucre and 0 <= gy < self.y * self.hucre

    def _hucre(self, x, y):
        return (x - self.taban_x) // self.hucre, (y - self.taban_y) // self.hucre

    def _kapali(self, cx, cy):
        # Harita dışı = kapalı. Kenardan taşan bir yol kabul edilmemeli.
        if cx < 0 or cy < 0 or cx >= self.g or cy >= self.y:
            return True
        i = cy * self.g + cx
        return bool(self.paket[i >> 3] & (1 << (i & 7)))

    def engel_mi(self, x, y):
        cx, cy = self._hucre(x, y)
        return self._kapali(cx, cy)

    def bosluk(self, x, y, yaricap):
        """
        Çevresi de açık mı?

        Karakterin gövdesi var; duvarın 1 hücre dibinden geçen bir yol
        pratikte takılıyor. Yol ararken hücreleri yarıçap kadar
        şişiriyoruz.
        """
        cx, cy = self._hucre(x, y)
        for dy in range(-yaricap, yaricap + 1):
            for dx in range(-yaricap, yaricap + 1):
                if self._kapali(cx + dx, cy + dy):
                    return False
        return True

    # ---- görüş ----

    def gorus_acik(self, ax, ay, bx, by, adim=None, yaricap=0):
        """
        İki nokta arasındaki DÜZ ÇİZGİ temiz mi?

        Bot çoğu bacağı düz gidebiliyor; yol arama pahalı. Önce buna
        bakıp temizse hiç yol aramamak, her bacakta A* koşturmaktan
        çok daha ucuz.

        `yaricap`: çizginin bu kadar hücre çevresi de açık olmalı.
        A* gövde payı bırakıyordu ama düzleştirme bu denetimden
        geçtiği için payı geri bozuyordu — yol yeniden duvara
        yaslanıyor, bot da köşelerde takılıyordu. İki yer aynı payı
        kullanmalı.
        """
        adim = adim or self.hucre
        dx, dy = bx - ax, by - ay
        uzak = max(abs(dx), abs(dy))
        if uzak == 0:
            return (self.bosluk(ax, ay, yaricap) if yaricap
                    else not self.engel_mi(ax, ay))
        n = max(1, int(uzak // adim))
        for i in range(n + 1):
            t = i / float(n)
            x, y = int(ax + dx * t), int(ay + dy * t)
            if yaricap:
                if not self.bosluk(x, y, yaricap):
                    return False
            elif self.engel_mi(x, y):
                return False
        return True

    # ---- yol bulma ----

    def yol_bul(self, ax, ay, bx, by, kaba=4, yaricap=1, azami_dugum=60000):
        """
        A* ile ara noktalar. Yol yoksa None.

        `kaba`: kaç hücrede bir düğüm. 1 m'lik ızgarada A* bir köy
        haritasında 1.3 milyon düğüm demek — Python'da saniyeler sürer.
        4 hücre (4 m) adımla 80 bin düğüme iner ve yol yeterince iyi
        çıkar; sonuç zaten düzleştiriliyor.

        `yaricap`: duvara kaç hücre yaklaşılabilir (gövde payı).
        """
        if not (self.icinde_mi(ax, ay) and self.icinde_mi(bx, by)):
            return None
        adim = self.hucre * kaba

        def acik(x, y):
            return self.bosluk(x, y, yaricap)

        bas = (ax // adim, ay // adim)
        son = (bx // adim, by // adim)
        if bas == son:
            return []

        def dunya(d):
            return d[0] * adim + adim // 2, d[1] * adim + adim // 2

        # Hedef hücresi kapalıysa (metin duvara yaslanmış olabilir)
        # gövde payını bırak, yine de ulaşmayı dene.
        hedef_acik = acik(*dunya(son))

        def gecilir(d):
            wx, wy = dunya(d)
            if not self.icinde_mi(wx, wy):
                return False
            if d == son and not hedef_acik:
                return not self.engel_mi(wx, wy)
            return acik(wx, wy)

        komsu = ((1, 0), (-1, 0), (0, 1), (0, -1),
                 (1, 1), (1, -1), (-1, 1), (-1, -1))

        def tahmin(d):
            dx, dy = abs(d[0] - son[0]), abs(d[1] - son[1])
            return (dx + dy) + (1.4142 - 2) * min(dx, dy)

        kuyruk = [(tahmin(bas), 0.0, bas)]
        nereden = {bas: None}
        maliyet = {bas: 0.0}
        dugum = 0
        while kuyruk:
            _, m, d = heapq.heappop(kuyruk)
            if d == son:
                break
            if m > maliyet.get(d, 1e18):
                continue
            dugum += 1
            if dugum > azami_dugum:
                return None
            for kx, ky in komsu:
                k = (d[0] + kx, d[1] + ky)
                if not gecilir(k):
                    continue
                if kx and ky:
                    # Köşeden kesme yok: iki komşu da açık olmalı, yoksa
                    # duvarın köşesinden geçen bir yol üretiliyor.
                    if not (gecilir((d[0] + kx, d[1])) and
                            gecilir((d[0], d[1] + ky))):
                        continue
                ym = m + (1.4142 if kx and ky else 1.0)
                if ym < maliyet.get(k, 1e18):
                    maliyet[k] = ym
                    nereden[k] = d
                    heapq.heappush(kuyruk, (ym + tahmin(k), ym, k))
        if son not in nereden:
            return None

        yol = []
        d = son
        while d is not None:
            yol.append(dunya(d))
            d = nereden[d]
        yol.reverse()
        return self._duzlestir([(ax, ay)] + yol[1:-1] + [(bx, by)],
                               yaricap)

    def _duzlestir(self, yol, yaricap=0):
        """
        Görüş açıksa aradaki noktaları at.

        A* ızgara üzerinde zikzak üretiyor; her 4 m'de bir dönen bir
        yürüyüş dışarıdan makine gibi görünür. Bir noktadan görülebilen
        en uzak noktaya doğrudan gidilir.

        `yaricap` ARAMAYLA AYNI olmalı. Eskiden düzleştirme payı hiç
        hesaba katmıyordu: A* duvardan uzak bir yol buluyor, düzleştirme
        onu kısaltmak için duvara yaslıyordu. Sahada "engellerin
        dibinden gidiyor, takılıyor" olarak görüldü.
        """
        if len(yol) < 3:
            return yol[1:]
        temiz = [yol[0]]
        i = 0
        while i < len(yol) - 1:
            j = len(yol) - 1
            while j > i + 1:
                if self.gorus_acik(yol[i][0], yol[i][1],
                                   yol[j][0], yol[j][1], yaricap=yaricap):
                    break
                j -= 1
            temiz.append(yol[j])
            i = j
        return temiz[1:]


class Dunya(object):
    """Bütün haritalar; konuma göre doğrusunu seçer."""

    def __init__(self, haritalar, hucre):
        self.haritalar = haritalar
        self.hucre = hucre

    def __bool__(self):
        return bool(self.haritalar)

    __nonzero__ = __bool__

    @classmethod
    def yukle(cls, dizin=None):
        """harita/ dizinini okur. Veri yoksa boş Dünya döner."""
        dizin = dizin or _DIZIN
        yol = os.path.join(dizin, 'harita.json')
        if not os.path.exists(yol):
            return cls({}, 100)
        try:
            with io.open(yol, encoding='utf-8') as f:
                d = json.load(f)
        except Exception:
            return cls({}, 100)
        hucre = d.get('hucre', 100)
        haritalar = {}
        for ad, h in d.get('haritalar', {}).items():
            taban = h.get('taban')
            if not taban:
                continue            # hizasız harita kullanılamaz
            p = os.path.join(dizin, h['dosya'])
            if not os.path.exists(p):
                continue
            with open(p, 'rb') as f:
                paket = f.read()
            haritalar[ad] = Harita(ad, taban, h['g'], h['y'], paket, hucre)
        return cls(haritalar, hucre)

    def hangi(self, x, y):
        """
        Bu konum hangi haritada?

        Haritalar dünyada ayrı bölgelerde durduğu için konum tek başına
        yetiyor; sunucudan harita adı istemeye gerek yok. Birden fazla
        haritaya düşerse (taban çakışması) None döner — yanlış haritanın
        duvarlarına inanmaktansa hiç inanmamak doğru.
        """
        uyan = [h for h in self.haritalar.values() if h.icinde_mi(x, y)]
        return uyan[0] if len(uyan) == 1 else None
