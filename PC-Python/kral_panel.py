# -*- coding: utf-8 -*-
"""
KRALI YAKALA — otomatik oynatıcı panel (ayrı program).

APK'daki ApiSunucu'ya (:30200) bağlanır, tambot ile AYNI enjeksiyon yolunu
kullanır: hamleleri 0xe2 paketiyle gönderir, sonuçları /api/log'dan 0xee
paketleriyle okur. Değerleri açmadan göremediğimiz için kural gereği oynar:

    el kartı H, açılan masa kartı V:
      V <  H  -> +V*10 puan, AYNI kartla açmaya DEVAM (zincir)
      V == H  -> +V*10 puan, hamle biter (sıradaki kart)
      V >  H  -> 0 puan, hamle biter
    Kral kartı (H=6) YALNIZ masadaki 6'yı yakalar (+100), başka hiçbir kartı almaz.
    H=5 TUZAĞI: açtığın kartın komşusunda KAPALI bir 5 varsa 5 kartın gider (0 puan).
    Bu yüzden "kuru kafa" baytı mayın tarlası gibi çözülür: kafa=0 → o kartın 8
    komşusunun hiçbiri 5 değildir. El destesi: 1,1,1,1,1,2,2,3,3,4,5,K (12 kart).

    python kral_panel.py           # panel
    python kral_panel.py --test    # APK'sız: benzetimle beyin/kural testi

GÜVENLİK: tambot'taki üç kapı (proxy/enjeksiyon/kanal) açık değilse APK paketi
göndermez; panel de uyarır. Kart oyununu OYUNDA kart masasının başındayken aç.
"""

import argparse
import importlib.util
import itertools
import math
import os
import random
import sys
import threading
import time

KOK = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tambot", os.path.join(KOK, "tambot.py"))
tb = importlib.util.module_from_spec(_spec)
# tambot'u içe aktarmak modül düzeyinde yalnız tanımları çalıştırır (pencere açmaz).
_spec.loader.exec_module(tb)

KOYU, PANEL, CIZGI = "#0f1117", "#171922", "#262a36"
METIN, SOLUK, VURGU = "#e6e8ef", "#9aa0b4", "#33aaff"
OK, UYARI, HATA = "#37d67a", "#ffb020", "#ff5a5a"
DEGER_RENK = {1: "#9aa0b4", 2: "#37d67a", 3: "#33aaff",
              4: "#ffb020", 5: "#ff8c42", 6: "#ff5a5a"}   # 6 = Kral


# ── paket / çözümleme (saf, test edilebilir) ─────────────────────────────
def paket_e2(mod, arg):
    return bytes([0xE2, mod & 0xFF, arg & 0xFF])


def ee_coz_hex(hx):
    """/api/log'daki bir 0xee hex dizisini olaylara çevirir."""
    try:
        b = bytes(int(x, 16) for x in hx.split())
    except Exception:                                      # noqa: BLE001
        return []
    olaylar = []
    i = 0
    while i + 4 <= len(b):
        if b[i] == 0xEE:
            L = b[i + 1]
            if L >= 4 and b[i + 2] == 0x00 and i + L <= len(b):
                p = b[i:i + L]
                sub = p[3]
                if sub == 3 and L >= 11:
                    puan = int.from_bytes(p[4:8], "little")
                    # p[11]=puan aldın mı, p[12]=hamle bitti mi, p[14]=yakında 5 (kuru kafa)
                    aldi = p[11] if L >= 12 else 0
                    bitti = p[12] if L >= 13 else 1
                    kafa5 = p[14] if L >= 15 else 0
                    olaylar.append(("sonuc", p[9], p[10], puan, aldi, bitti, kafa5))
                elif sub == 4 and L >= 6:
                    olaylar.append(("board", p[4], p[5]))
                elif sub == 2 and L >= 5:
                    olaylar.append(("el", p[4]))
                elif sub == 1:
                    olaylar.append(("baslat",))
                i += L
                continue
        i += 1
    return olaylar


# ── oyun beyni (saf: gonder + ee_al callback'leriyle) ────────────────────
class KralOyun:
    BES_TOPLAM = 3                      # masadaki 5 adedi (kayıttan doğrulandı)
    DESTE = (1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 6)   # el destesi: sabit ve ARTAN

    def __init__(self, gonder, ee_al, gecikme=0.35, gunluk=None, sifirla=None):
        self.gonder = gonder            # gonder(paket_bytes)
        self.ee_al = ee_al              # ee_al() -> [olay, ...] (yeni olaylar)
        self.sifirla = sifirla or (lambda: None)   # yeni oyun: bayat log'u yut
        self.gecikme = gecikme
        self.gunluk = gunluk or (lambda s: None)
        self.skor = 0
        self.el = None
        self.board = {}                 # pos -> deger (NOT DEFTERİ: görülen değer)
        self.acilan = set()             # YAKALANAN (masadan kalkan) pozisyonlar
        self.kafa = {}                  # açılan pos -> yakında 5 var mı (kuru kafa)
        self.atlanan = set()            # bu hamlede cevapsız kalanlar
        self.basarisiz = {}             # pos -> üst üste cevapsız sayısı
        self._kilit = 0
        self.kalan_deste = []           # destede kalan kartlar (artan)
        self._kart_tukendi = False      # son hamle bitti mi (kart harcandı mı)
        self.gecikmeler = []            # açılış cevabı gecikmeleri (ms)
        self.zaman_asimi = 0            # hiç cevap gelmeyen açılış sayısı
        self.kart_gecikmeler = []       # kart isteği cevabı gecikmeleri (ms)
        self.kart_asimi = 0

    def _topla(self, sure):
        """sure boyunca yeni ee olaylarını toplar.

        İlk olay gelir gelmez dönmek YANLIŞ: sunucu 'el kartı' ile 'sonuç'
        paketlerini ayrı anlarda yollayabiliyor; erken dönersek sonucu bir
        SONRAKİ adıma sayıyoruz (log'da 'el kartı' üst üste görünüp açılış
        cevabı kaybolmasının sebebi buydu). Olay geldikten sonra kısa bir
        'oturma' penceresi boyunca dinlemeye devam ederiz."""
        yerlesme = 0.0 if self.gecikme <= 0 else 0.35   # benzetimde bekleme yok
        bitis = time.time() + sure
        toplu = []
        while time.time() < bitis:
            toplu += self.ee_al()
            if toplu:
                break
            time.sleep(0.03)
        if toplu and yerlesme:
            son = time.time() + yerlesme
            while time.time() < son:
                ek = self.ee_al()
                if ek:
                    toplu += ek
                    son = time.time() + yerlesme        # akış sürüyor, biraz daha
                else:
                    time.sleep(0.03)
        else:
            toplu += self.ee_al()
        return toplu

    def _ogren(self, olaylar):
        """Olaylardan yalnız MASA BİLGİSİ öğrenir (değer + kuru kafa).

        Bayat olaylar araya karışsa bile masa aynı masa olduğu için değerler
        geçerlidir; bu yüzden öğrenmek güvenlidir. Puan/yakalama takibi burada
        YAPILMAZ — o, hamleye ait eşleşen cevapta yapılır (_yakalama_isle)."""
        for o in olaylar:
            if o[0] == "sonuc":
                self.board[o[1]] = o[2]
                if len(o) >= 7:
                    self.kafa[o[1]] = bool(o[6])
            elif o[0] == "board":
                self.board[o[1]] = o[2]
            # NOT: 'el' olaylari burada ISLENMEZ. Gecikme 200-3000 ms
            # oldugu icin log'daki 'el' paketlerinin guncel mi bayat mi oldugu
            # ayirt edilemiyor. El karti DESTEDEN sayilarak bilinir; paket
            # yalnizca kart isteginin eslesen cevabinda dikkate alinir.
    def _yakalama_isle(self, sonuc):
        """Hamlemize ait EŞLEŞEN cevabı işler; yakalandı mı karar verir."""
        pos, deger, puan = sonuc[1], sonuc[2], sonuc[3]
        kafa = bool(sonuc[6]) if len(sonuc) >= 7 else False
        # 'aldi' baytına güvenme (5 tuzağında aldi=1 ama puan artmaz).
        # Tek güvenilir ölçüt: PUAN ARTIŞI.
        if puan < self.skor:
            # Puan bir oyun içinde ASLA azalmaz → bu olay bayat (log'da dolaşan
            # eski bir pakettir). Tamamen yok say; yoksa puanı geri alır ve
            # yakalama takibini bozarız.
            return False
        kazandik = puan > self.skor
        if kazandik:
            self.skor = puan
        H = self.el or 0
        bitti = bool(sonuc[5]) if len(sonuc) >= 7 else (deger >= H)
        if kazandik:
            self.acilan.add(pos)                   # yakalandı → masadan kalktı
            # Yakaladığımız değer elin ALT SINIRINI verir:
            #   zincir sürdü (bitti=0) → el > deger → el ≥ deger+1
            #   hamle bitti (bitti=1) → el == deger
            # "5 ken 4 gördü" düzeltmesi: el=4 sanıp 4 yakalayıp zincir sürerse
            # 4<gerçek el, yani el ≥ 5 → burada yükseltiyoruz.
            alt = deger + 1 if not bitti else deger
            if alt > H:
                self.gunluk("  ← el kartı düzeltildi: %s → %d  (%d yakaladık, %s)"
                            % (self.el, alt, deger,
                               "zincir sürüyor" if not bitti else "hamle bitti"))
                self.el = alt
        elif H and deger <= H and not (H == 5 and kafa) and not (H == 6 and deger != 6):
            # Yakalayabilmemiz gerekirdi ama puan gelmedi → kart masada değil.
            self.acilan.add(pos)
        return kazandik

    @staticmethod
    def _komsular(pos):
        r, c = divmod(pos, 5)
        ns = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 5 and 0 <= nc < 5:
                        ns.append(nr * 5 + nc)
        return ns

    # ── OLASILIKSAL MAYIN TARLASI ÇIKARIMI ───────────────────────────────
    # Masa dağılımı sabit (kayıttan): 7×1, 4×2, 5×3, 5×4, 3×5, 1×K. Tam 3 beş
    # var → 5'lerin TÜM tutarlı yerleşimleri sayılır (≤ C(25,3)=2300, bitmask ile
    # hızlı). Her hücre için: P(5), tuzak olasılığı (komşuda kapalı 5), değer
    # dağılımı. Kararlar bu olasılıklarla beklenen değere göre verilir.
    MASA_DAGILIM = {1: 7, 2: 4, 3: 5, 4: 5, 5: 3, 6: 1}
    K_ZINCIR = 60.0        # zincirin sürmesinin değeri (izci)  [taramayla ayarlandı]
    K_ZINCIR5 = 95.0       # zincirin sürmesinin değeri (5 kartı) [taramayla ayarlandı]
    L_BILGI = 12.0         # bilgi kazancı ağırlığı (izci keşfi)
    M_BOLGE = 0.6          # tuzak bölgesi önceliği (5'in alamayacağı kartlar)
    _NBR_MASK = None

    @classmethod
    def _nbr_mask(cls):
        if cls._NBR_MASK is None:
            cls._NBR_MASK = [sum(1 << n for n in cls._komsular(p)) for p in range(25)]
        return cls._NBR_MASK

    def _cikarim(self):
        """5'lerin tutarlı yerleşimlerini sayar → P5, tuzak, kalan dağılım."""
        nbr = self._nbr_mask()
        bilinen5 = [p for p, d in self.board.items() if d == 5]
        bilinmeyen = [p for p in range(25) if p not in self.board]
        eksik = self.BES_TOPLAM - len(bilinen5)
        taban = sum(1 << p for p in bilinen5)
        # HIZ: kafa=0 → o kartın komşuları KESİN 5 değil. Bu hücreleri adaylardan
        # baştan atarsak sayılacak kombinasyon sayısı çok küçülür (2300 → onlarca).
        yasak = 0
        kafa1 = []
        for p, var in self.kafa.items():
            if var:
                kafa1.append(nbr[p])
            else:
                yasak |= nbr[p]
        adaylar = [p for p in bilinmeyen if not (yasak >> p & 1)]
        anahtar = (taban, yasak, tuple(sorted(kafa1)), tuple(adaylar), eksik)
        if getattr(self, "_yer_anahtar", None) == anahtar:
            yer = self._yer_onbellek                   # durum değişmedi → yeniden sayma
        else:
            yer = []
            if 0 <= eksik <= len(adaylar) and not (taban & yasak):
                for combo in itertools.combinations(adaylar, eksik):
                    S = taban
                    for c in combo:
                        S |= 1 << c
                    if all(m & S for m in kafa1):       # her kafa=1 açıklanmalı
                        yer.append(S)
            self._yer_anahtar, self._yer_onbellek = anahtar, yer
        self.yerlesimler = yer
        n = len(yer)
        acik_mask = sum(1 << p for p in self.acilan)
        # HIZ: komşuluk simetrik → "c tuzaklı" demek "c, bir 5'in komşusu" demek.
        # Her yerleşim için 25 hücreyi test etmek yerine, 3 beşin komşu maskesini
        # birleştirip (tek OR) hücre sayaçlarını maske başına topluyoruz.
        p5cnt, tcnt, maske_say = [0] * 25, [0] * 25, {}
        for S in yer:
            t, s = 0, S
            while s:
                b = s & -s
                p = b.bit_length() - 1
                p5cnt[p] += 1
                if not (b & acik_mask):                     # yakalanan 5 masada yok
                    t |= nbr[p]
                s ^= b
            maske_say[t] = maske_say.get(t, 0) + 1
        for t, adet in maske_say.items():
            s = t
            while s:
                b = s & -s
                tcnt[b.bit_length() - 1] += adet
                s ^= b
        self.P5, self.tuzak = {}, {}
        for c in range(25):
            if c in self.board:
                self.P5[c] = 1.0 if self.board[c] == 5 else 0.0
            else:
                self.P5[c] = (p5cnt[c] / n) if n else None
            self.tuzak[c] = (tcnt[c] / n) if n else None
        rem = dict(self.MASA_DAGILIM)
        for d in self.board.values():
            rem[d] = rem.get(d, 0) - 1
        self.rem = rem
        self.unk = len(bilinmeyen)

    def _pv(self, c):
        """Bilinmeyen c için P(V=v)."""
        p5 = self.P5.get(c)
        if p5 is None:
            p5 = (self.rem.get(5, 0) / self.unk) if self.unk else 0.0
        non5 = sum(max(v, 0) for k, v in self.rem.items() if k != 5)
        pv = {5: p5}
        for k in (1, 2, 3, 4, 6):
            pv[k] = ((1 - p5) * max(self.rem.get(k, 0), 0) / non5) if non5 > 0 else 0.0
        return pv

    @staticmethod
    def _ent(q):
        if q is None or q <= 0.0 or q >= 1.0:
            return 0.0
        return -(q * math.log2(q) + (1 - q) * math.log2(1 - q))

    def _guvenli(self, c):
        return self.tuzak.get(c) == 0.0

    def _ev5(self, c):
        """5 kartıyla güvenli bilinmeyen c'yi açmanın beklenen değeri."""
        pv = self._pv(c)
        ev = sum(pv[v] * v * 10 for v in (1, 2, 3, 4)) + pv[5] * 50
        p_cont = sum(pv[v] for v in (1, 2, 3, 4))
        return ev + p_cont * self.K_ZINCIR5

    def _kesif_skoru(self, c, H):
        """İzci (H<=4) keşif skoru: puan + zincir + bilgi + tuzak-bölgesi."""
        pv = self._pv(c)
        ev = sum(pv[v] * v * 10 for v in range(1, H + 1))
        p_cont = sum(pv[v] for v in range(1, H))
        q = self.tuzak.get(c)
        bilgi = self._ent(q) + self._ent(pv[5])
        bolge = q or 0.0
        return (ev + p_cont * self.K_ZINCIR + self.L_BILGI * bilgi
                + self.M_BOLGE * bolge * ev, p_cont)

    def _sonraki_pos(self):
        """Beklenen değere göre karar. Kural: H, 1..H yakalar; V<H zincir sürer,
        V==H puan+biter, V>H 0+biter. H=5 tuzağı: komşuda kapalı 5 → 5'in gider.
        Kral yalnız 6'yı alır. Iskalanan kart geri kapanır (deftere yazılır)."""
        self._cikarim()
        es = self.acilan | getattr(self, "atlanan", set())
        kalan = [p for p in range(25) if p not in es]
        if not kalan:
            return None
        H = self.el or 1
        bilinmeyen = [p for p in kalan if p not in self.board]
        bilinen = [p for p in kalan if p in self.board]

        if H == 6:                                         # KRAL: yalnız 6
            b6 = [p for p in bilinen if self.board[p] == 6]
            if b6:
                return b6[0]
            if not bilinmeyen:
                return None
            return max(bilinmeyen, key=lambda c: self._pv(c)[6])

        if H == 5:
            # 1) güvenli bilinen V<5 → zincir (en yüksek önce)
            dus = [p for p in bilinen if self.board[p] < 5 and self._guvenli(p)]
            if dus:
                return max(dus, key=lambda p: self.board[p])
            # 2) güvenli bilinmeyen → en iyi beklenen değer
            guv = [c for c in bilinmeyen if self._guvenli(c)]
            if guv:
                return max(guv, key=self._ev5)
            # 3) güvenli yer kalmadı: bilinen güvenli 5 (+50) mi, hesaplı kumar mı?
            b5 = [p for p in bilinen if self.board[p] == 5 and self._guvenli(p)]
            en_iyi, en_deger = None, (50.0 if b5 else 0.0)
            for c in kalan:
                t = self.tuzak.get(c)
                if t is None or t >= 1.0:
                    continue
                if c in self.board:
                    v = self.board[c]
                    if v > 5:
                        continue
                    kaz = v * 10 + (self.K_ZINCIR5 if v < 5 else 0)
                else:
                    kaz = self._ev5(c)
                deger = (1 - t) * kaz
                if deger > en_deger:
                    en_iyi, en_deger = c, deger
            if en_iyi is not None:
                return en_iyi
            if b5:
                return b5[0]
            # Hiçbir olasılık hesaplanamadıysa (çelişkili gözlem → tutarlı
            # yerleşim yok) KARARSIZ KALMA: en değerli kartı harcamadan
            # oyunu bırakmaktansa bilinmeyen bir kart aç.
            if bilinmeyen:
                return random.choice(bilinmeyen)
            return kalan[0] if kalan else None

        # ── İZCİLER H=1..4 ───────────────────────────────────────────
        # 1) zincir bağı: bilinen V<H (tuzak bölgesindekiler önce — 5 onları alamaz)
        dus = [p for p in bilinen if self.board[p] < H]
        if dus:
            return max(dus, key=lambda p: ((self.tuzak.get(p) or 0.0), self.board[p]))
        # 2) keşif mi, bilinen ==H ile bitirmek mi?
        esit = [p for p in bilinen if self.board[p] == H]
        # "şimdi ya da asla": H=4 ve tuzak bölgesindeki bilinen 4 (5 alamaz, başka 4 yok)
        simdi = [p for p in esit if H == 4 and (self.tuzak.get(p) or 0.0) > 0.0]
        if bilinmeyen:
            c, (skor, p_cont) = max(((c, self._kesif_skoru(c, H)) for c in bilinmeyen),
                                    key=lambda t: t[1][0])
            if simdi and p_cont < 0.7:
                return max(simdi, key=lambda p: self.tuzak.get(p) or 0.0)
            return c
        if esit:
            return max(esit, key=lambda p: (self.tuzak.get(p) or 0.0))
        return None

    def _deste_kur(self, ilk):
        """Elde duran kart 'ilk' ise destede ondan sonrası kalmıştır (artan sıra)."""
        kalan = [c for c in self.DESTE if c >= ilk]
        if kalan and kalan[0] == ilk:
            kalan.pop(0)                    # bu kart şu an ELDE
        self.kalan_deste = kalan

    def _sonraki_kart(self):
        """Destedeki sıradaki kart; bittiyse None. Pakete muhtaç değiliz."""
        if getattr(self, "kalan_deste", None):
            return self.kalan_deste.pop(0)
        return None

    def _deste_dus(self, deger):
        """Sunucunun verdiği el kartını yedek sayaçtan düş (yalnız takip)."""
        try:
            self.kalan_deste.remove(deger)
        except (ValueError, AttributeError):
            pass

    @staticmethod
    def _ortanca(d):
        if not d:
            return 0.0
        y = sorted(d)
        n = len(y)
        return y[n // 2] if n % 2 else (y[n // 2 - 1] + y[n // 2]) / 2.0

    def _gecikme_ozeti(self):
        """Cevap gecikmelerini özetle — 'geç geliyor' mu 'hiç gelmiyor' mu?"""
        g, k = self.gecikmeler, self.kart_gecikmeler
        if g:
            self.gunluk("⏱ açılış cevabı: en hızlı %.0f / ortanca %.0f / en yavaş "
                        "%.0f ms  (%d cevap, %d zaman aşımı)"
                        % (min(g), self._ortanca(g), max(g), len(g), self.zaman_asimi))
        elif self.zaman_asimi:
            self.gunluk("⏱ açılış cevabı: HİÇ gelmedi (%d deneme)" % self.zaman_asimi)
        if k:
            self.gunluk("⏱ kart isteği : en hızlı %.0f / ortanca %.0f / en yavaş "
                        "%.0f ms  (%d cevap, %d zaman aşımı)"
                        % (min(k), self._ortanca(k), max(k), len(k), self.kart_asimi))
        elif self.kart_asimi:
            self.gunluk("⏱ kart isteği : HİÇ gelmedi (%d deneme)" % self.kart_asimi)
        yavas = [x for x in g if x > 1500]
        if yavas:
            self.gunluk("   NOT: %d cevap 1.5 sn'den yavaş geldi — okuma gecikiyor."
                        % len(yavas))

    def _bekle(self, kosul, sure):
        """sure boyunca olay toplar; kosul(olay) sağlanan İLK olayı döndürür.
        Toplanan her şeyden masa bilgisi öğrenilir (bayat olsa da geçerli)."""
        hizli = self.gecikme <= 0
        bitis = time.time() + (0.05 if hizli else sure)
        bulunan = None
        while time.time() < bitis:
            olaylar = self.ee_al()
            if olaylar:
                self._ogren(olaylar)
                for o in olaylar:
                    if bulunan is None and kosul(o):
                        bulunan = o
                if bulunan is not None:
                    return bulunan
            if hizli:
                break
            time.sleep(0.03)
        return bulunan

    def oyna(self, calisiyor, ilk_el=None, baslat=True, devam=False):
        """Bir tam oyun oynar. calisiyor(): durdurma kontrolü. Döner: skor.

        ilk_el: masa ZATEN açıksa elde duran kartın değeri. Sunucu elde kart
        varken yeni kart vermez (e2 01 00'ı sessizce yok sayar), o yüzden
        doğrudan kart açarız.
        baslat: açık masada devam ederken BAŞLAT gönderme.
        devam : aynı masaya devam — NOT DEFTERİNİ (board/kafa/yakalananlar)
                ve puanı KORU. Masa aynı masa, bilgi çöpe gitmesin."""
        if not devam:
            self.skor = 0
            self.board = {}
            self.acilan = set()
            self.kafa = {}
        self.el = None
        self._kart_tukendi = True           # ilk çekiliş de taze (sunucudan) gelsin
        self.kalan_deste = list(self.DESTE)  # yedek sayaç (sunucu cevapsızsa)
        self.basarisiz = {}
        self.atlanan = set()
        self._kilit = 0
        self.sifirla()                                     # bayat log'u yut
        if baslat:
            self.gonder(paket_e2(0, 1))                    # BAŞLAT
            self._bekle(lambda o: o[0] in ("baslat", "el"), 2.0)
            time.sleep(self.gecikme)
        bos = 0
        while calisiyor():
            if ilk_el is not None:
                el, ilk_el = ilk_el, None
                self._deste_kur(el)
                self.gunluk("elde duran kart = %d — deste: %s"
                            % (el, self.kalan_deste))
            else:
                _t0 = time.time()
                self.gonder(paket_e2(1, 0))                # sıradaki el kartı
                o = self._bekle(lambda o: o[0] == "el", 2.0)
                _ms = (time.time() - _t0) * 1000.0
                if o:
                    self.kart_gecikmeler.append(_ms)
                else:
                    self.kart_asimi += 1
                # EL KARTI: sunucunun 'el' olayı (ee 05 00 02) log halka
                # tamponunda BAYAT dolaşıyor — ESKİ elin değeri gelip "sanki
                # 5 ken 4 gördü" oluyordu. O yüzden pakete GÜVENMİYORUZ. Deste
                # SABİT ve ARTAN sıralı → sıradaki kart tahminimiz; gerçek değeri
                # SONUÇLARDAN kesinleştiriyoruz (_yakalama_isle: zincir sürerse
                # el ≥ açılan+1).
                gelen = o[1] if o else None
                if self._kart_tukendi:
                    self._kart_tukendi = False
                    el = self._sonraki_kart()          # deste sırası (tahmin)
                    if el is None and gelen is not None:
                        el = gelen                     # deste bitti ama kart geldi
                else:
                    # Hamle bitmemişti: kart HÂLÂ ELDE, değeri değişmedi.
                    el = self.el
            if el is None:
                # (a) deste bitti ya da (b) ELDE HÂLÂ KART VAR (sunucu elde kart
                # varken yenisini vermez). (b) ise mevcut kartla devam etmeliyiz.
                bos += 1
                if self.el and bos < 4:
                    el = self.el
                    self.gunluk("yeni kart gelmedi — elde %d duruyor olabilir, "
                                "onunla devam (%d/3)" % (el, bos))
                else:
                    self.gunluk("el kartı gelmedi — deste bitti sayıyorum")
                    break
            else:
                bos = 0
            self.el = el
            self.gunluk("el kartı = %d%s" % (el, "  (KRAL)" if el >= 6 else ""))
            # Zaman aşımına uğrayanlar (çok muhtemelen zaten alınmış) hamleler
            # arası da atlansın — yoksa beyin aynı ölü kartı tekrar seçip her
            # seferinde bekliyor (önceki oyunda 9 zaman aşımı = ~23 sn çöp).
            self.atlanan = set(self.basarisiz)
            time.sleep(self.gecikme)
            hamle_yapildi = False
            while calisiyor():
                pos = self._sonraki_pos()
                if pos is None:
                    break
                _t0 = time.time()
                self.gonder(paket_e2(2, pos))              # AÇ pos
                # SADECE bu pozisyona ait cevabı kabul et (bayat olay karışmasın)
                sonuc = self._bekle(
                    lambda o, p=pos: o[0] == "sonuc" and o[1] == p, 3.0)
                _ms = (time.time() - _t0) * 1000.0
                if sonuc is not None:
                    self.gecikmeler.append(_ms)
                else:
                    self.zaman_asimi += 1
                    self.gunluk("  ⏱ masa[%d]: %.0f ms bekledim, cevap YOK" % (pos, _ms))
                time.sleep(self.gecikme)
                if sonuc is None:
                    # Cevapsızlık "yakalandı" demek DEĞİL. Kalıcı elersek, Kral'ın
                    # tek hedefi olan 6'yı da eleyip oyunu kilitleyebiliriz.
                    self.basarisiz[pos] = self.basarisiz.get(pos, 0) + 1
                    if self.basarisiz[pos] >= 2:
                        # Israrla cevapsız: bu kart artık masada yok say, yoksa
                        # her hamlede aynı ölü kartı seçip oyunu kilitliyoruz.
                        self.acilan.add(pos)
                        self.gunluk("  masa[%d] ısrarla cevapsız — masada yok "
                                    "sayıyorum" % pos)
                    else:
                        self.atlanan.add(pos)
                        self.gunluk("  masa[%d] için cevap yok — atlıyorum" % pos)
                    break
                hamle_yapildi = True
                kazandik = self._yakalama_isle(sonuc)
                deger = sonuc[2]
                bitti = sonuc[5] if len(sonuc) >= 7 else (deger >= self.el)
                kafa = sonuc[6] if len(sonuc) >= 7 else 0
                self.gunluk("  aç masa[%d] = %d  → puan %d%s%s%s  (%.0f ms)"
                            % (pos, deger, self.skor,
                               "  +" if kazandik else "",
                               "  💀(yakında 5)" if kafa else "",
                               "" if not bitti else "  [hamle bitti]", _ms))
                if bitti:
                    # Hamle bitti → ELDEKİ KART HARCANDI. (V<H olsaydı bitti=0
                    # gelir, kart elde kalır ve zincir sürerdi — 2 ile 1 bulmak
                    # gibi.) Desteyi ancak burada ilerletmeye hak kazanırız.
                    self._kart_tukendi = True
                    break
            if not hamle_yapildi:
                kilit = getattr(self, "_kilit", 0) + 1
                self._kilit = kilit
                if kilit >= 3:
                    self.gunluk("üst üste hamle yapılamıyor — oyunu bitiriyorum")
                    break
            else:
                self._kilit = 0
            if len(self.acilan) >= 25:
                break
        # BİTİR'i yalnız gerçekten oynadıysak gönder (boşuna oturum kapatmasın).
        if self.board or self.skor:
            self.gonder(paket_e2(3, 0))                    # BİTİR / ödül al
            self._bekle(lambda o: False, 1.5)
            self.gunluk("oyun bitti — puan %d" % self.skor)
            self._gecikme_ozeti()
        else:
            self.gunluk("hiç hamle olmadı — BİTİR göndermedim (oturum korunuyor).")
        return self.skor


# ── APK bağlantısı: gonder + /api/log'dan ee okuma ───────────────────────
class ApkKopru:
    """/api/log EKLEMELİ (append-only) bir halka tampon: son N kaydı verir.

    DİKKAT: kayıtları içeriğe göre ayıklamak YANLIŞ olur — deste 1,1,1,1,1 ile
    başladığı için 'el kartı = 1' paketinin hex'i birebir AYNI gelir ve ikinci
    kopya 'zaten gördüm' diye silinirdi (bot da 'el gelmedi' sanıp oyunu erken
    bitirirdi). Onun yerine listeyi bir öncekiyle HİZALAYIP yalnızca sona
    eklenenleri alıyoruz; böylece birebir aynı paketler de doğru sayılır.
    """
    def __init__(self, api):
        self.api = api
        self._onceki = None                 # None = temel henüz alınmadı
        self.son_enjekte = None
        self._kuyruk = []
        self._kilit = threading.Lock()
        self._calis = False
        self._iplik = None

    # ── kesintisiz dinleme ────────────────────────────────────────────────
    def basla(self):
        """Arka planda sürekli log oku. Bot uyurken bile bildirim kaçmasın."""
        if self._iplik and self._iplik.is_alive():
            return
        self._calis = True
        self._iplik = threading.Thread(target=self._dongu, daemon=True)
        self._iplik.start()

    def dur(self):
        self._calis = False

    def _dongu(self):
        while self._calis:
            try:
                olaylar = self._oku()
            except Exception:                           # noqa: BLE001
                olaylar = []
            if olaylar:
                with self._kilit:
                    self._kuyruk.extend(olaylar)
                    if len(self._kuyruk) > 4000:        # taşmasın
                        self._kuyruk = self._kuyruk[-2000:]
            time.sleep(0.04)

    def gonder(self, paket):
        self.son_enjekte = self.api.enjekte(paket)      # cevabı sakla (tanı için)
        return self.son_enjekte

    def sifirla(self):
        """Yeni oyundan önce: o ana kadarki her şeyi 'görülmüş' say."""
        self._onceki = None
        with self._kilit:
            self._kuyruk = []

    @staticmethod
    def _anahtar(k):
        # DİKKAT: 'zaman' anahtara GİRMEZ. Sorgudan sorguya değişebiliyor
        # (göreli damga) ve o zaman hiçbir kayıt eşleşmez; hizalama çöker,
        # her sorgu "hepsi yeni" döner, bot bayat paket seline boğulur.
        # Sırayı karşılaştırdığımız için birebir aynı paketler yine doğru sayılır.
        return (k.get("opcode"), k.get("hex"), bool(k.get("giden")))

    def _oku(self):
        """Bir kez log çekip YENİ kayıtları olaya çevirir (iplik içinden)."""
        kayit = self.api.get("/api/log", n=150)
        if not isinstance(kayit, list):
            return []
        anah = [self._anahtar(k) for k in kayit]
        onceki, self._onceki = self._onceki, anah
        if onceki is None:                  # ilk çekim = temel; eskisi yutulur
            return []
        yeni_kayitlar = kayit
        for k in range(len(anah) + 1):
            ort = len(anah) - k
            if ort <= len(onceki) and anah[:ort] == onceki[len(onceki) - ort:]:
                yeni_kayitlar = kayit[ort:]
                break
        if onceki and len(yeni_kayitlar) == len(kayit) and len(kayit) > 20:
            # Hiç örtüşme yok = gerçek taşma (ya da log sıfırlandı). Tüm geçmişi
            # "yeni" saymak bayat sel yaratır; yalnız en son kayıtları al.
            yeni_kayitlar = kayit[-20:]
        cikti = []
        for k in yeni_kayitlar:
            if k.get("giden") or k.get("opcode") != 0xEE:
                continue
            cikti += ee_coz_hex(k.get("hex") or "")
        return cikti

    def ee_al(self):
        """Kuyruğu boşaltır. Ağ çağrısı YOK — dinleme arka planda sürüyor."""
        if not (self._iplik and self._iplik.is_alive()):
            return self._oku()              # dinleyici yoksa eski usul
        with self._kilit:
            c, self._kuyruk = self._kuyruk, []
        return c


def tek_paket(api, gunluk, mod=1, arg=0, sure=3.0):
    """YALITILMIŞ TEST — oyuna DOKUNMA; tek bir e2 enjekte edip ne olduğunu izler.

    Tanıda senin tıklamalarınla bizim paketimiz karışıyordu. Burada tek paket
    gönderip zaman damgalı izliyoruz: (a) paketimiz GİDEN olarak log'a düştü mü,
    (b) arkasından sunucudan bir 0xEE geldi mi. İkisi de netleşir."""
    paket = paket_e2(mod, arg)
    bekle = paket.hex(" ").upper()
    kopru = ApkKopru(api)
    kopru.ee_al()                                   # temel al
    onceki = kopru._onceki or []

    cevap = api.enjekte(paket)
    t0 = time.time()
    ad = {0: "BAŞLAT", 1: "el kartı iste", 2: "AÇ masa[%d]" % arg,
          3: "BİTİR/ödül"}.get(mod, "?")
    gunluk("gönderildi: %s  = %s   (/api/enjekte: %r)" % (bekle, ad, cevap))

    bizimki, ee_geldi, satir = 0, 0, 0
    while time.time() - t0 < sure:
        kayit = api.get("/api/log", n=1000)
        if isinstance(kayit, list):
            anah = [ApkKopru._anahtar(k) for k in kayit]
            yeni = kayit
            for k in range(len(anah) + 1):
                ort = len(anah) - k
                if ort <= len(onceki) and anah[:ort] == onceki[len(onceki) - ort:]:
                    yeni = kayit[ort:]
                    break
            onceki = anah
            for k in yeni:
                op = k.get("opcode") or 0
                hx = (k.get("hex") or "").upper()
                gd = bool(k.get("giden"))
                if gd and hx.startswith(bekle):
                    bizimki += 1
                if not gd and op == 0xEE:
                    ee_geldi += 1
                if (gd and op == 0xE2) or (not gd and op == 0xEE):
                    if satir < 20:
                        satir += 1
                        gunluk("  +%.2fs %s 0x%02X  %s"
                               % (time.time() - t0, "→" if gd else "←", op, hx[:40]))
        time.sleep(0.05)

    gunluk("— paketimiz GİDEN'de göründü mü: %s   |   gelen 0xEE: %d"
           % ("EVET (%d)" % bizimki if bizimki else "HAYIR", ee_geldi))
    if not bizimki:
        gunluk("SONUÇ: enjekte ettiğimiz paket sunucuya ÇIKMIYOR.")
    elif ee_geldi:
        gunluk("SONUÇ: paket çıktı VE cevap geldi → yol tamamen çalışıyor; "
               "sorun oyun döngüsünün zamanlamasında.")
    else:
        gunluk("SONUÇ: paket çıkıyor ama sunucu CEVAPSIZ bırakıyor. Oyun bu "
               "e2'yi kabul etmiyor (sıra/durum ya da ek doğrulama).")


def tani(api, gunluk, sure=10.0):
    """HAM TRAFİK TANISI — iddia etmeden ÖLÇ.

    En kritik soru: /api/log bu oyunun 0xEE cevaplarını YAKALIYOR mu? Bunu ancak
    SEN elle bir karta tıklarken bakarak anlarız: tıklaman sunucudan kesin bir
    0xEE döndürür. Log'da görünmüyorsa sorun OKUMA yolundadır; görünüyorsa
    bizim enjekte ettiğimiz e2 sunucuca reddediliyordur."""
    d = api.get("/api/durum")
    if not isinstance(d, dict):
        gunluk("X APK'ye ulaşılamıyor — adres / adb forward / token?")
        return
    proxy, kuy = d.get("proxy") or {}, d.get("kuyruk") or {}
    gunluk("kapılar: açık=%s bağlı=%s enjeksiyon=%s kanal=%s"
           % (proxy.get("acik"), proxy.get("bagli"),
              proxy.get("enjeksiyon"), kuy.get("kanal")))
    gunluk(">>> ŞİMDİ OYUNDA BİR KARTA ELLE TIKLA (%d sn izliyorum) <<<" % int(sure))

    N = 1000
    onceki = None
    hist_gelen, hist_giden = {}, {}
    ee_ornek, tasma, toplam = [], 0, 0
    t0 = time.time()
    while time.time() - t0 < sure:
        kayit = api.get("/api/log", n=N)
        if not isinstance(kayit, list):
            time.sleep(0.05)
            continue
        anah = [ApkKopru._anahtar(k) for k in kayit]
        if onceki is None:
            onceki = anah
            time.sleep(0.05)
            continue
        yeni_k, hizalandi = kayit, False
        for k in range(len(anah) + 1):
            ort = len(anah) - k
            if ort <= len(onceki) and anah[:ort] == onceki[len(onceki) - ort:]:
                yeni_k, hizalandi = kayit[ort:], True
                break
        if not hizalandi or (yeni_k and len(yeni_k) >= len(anah)):
            tasma += 1                 # log çok hızlı aktı → paket kaçmış olabilir
        onceki = anah
        for k in yeni_k:
            toplam += 1
            op = k.get("opcode") or 0
            h = hist_giden if k.get("giden") else hist_gelen
            h[op] = h.get(op, 0) + 1
            if not k.get("giden") and op == 0xEE and len(ee_ornek) < 8:
                ee_ornek.append(k.get("hex") or "")
        time.sleep(0.05)

    def dok(ad, h):
        if not h:
            gunluk("  %s: (hiç yok)" % ad)
            return
        sir = sorted(h.items(), key=lambda kv: -kv[1])[:14]
        gunluk("  %s: %s" % (ad, "  ".join("0x%02X x%d" % (o, n) for o, n in sir)))

    gunluk("— %d paket okundu, taşma(hızlı akış)=%d" % (toplam, tasma))
    dok("GELEN", hist_gelen)
    dok("GİDEN", hist_giden)
    for x in ee_ornek:
        gunluk("  ee örnek: %s" % x[:60])

    ee = hist_gelen.get(0xEE, 0)
    if ee:
        gunluk("SONUÇ: 0xEE OKUNABİLİYOR (%d adet) → okuma yolu sağlam. Sorun, "
               "bizim gönderdiğimiz e2'nin sunucuca kabul edilmemesinde." % ee)
    elif toplam == 0:
        gunluk("SONUÇ: log'dan hiç paket okunamadı — /api/log erişimi sorunlu.")
    else:
        gunluk("SONUÇ: %d paket aktı ama 0xEE YOK. Elle tıkladıysan bu oyunun "
               "kart paketleri bu log'a DÜŞMÜYOR → okuma için başka yol gerek."
               % toplam)
    if tasma:
        gunluk("  NOT: taşma=%d — log çok hızlı akıyor, paket kaçmış olabilir."
               % tasma)


def _main_gui():
    import tkinter as tk
    kok = tk.Tk()
    kok.title("Kralı Yakala — Otomatik")
    kok.configure(bg=KOYU)
    kok.geometry("560x620")
    kok.minsize(520, 560)
    api = tb.Api()
    durum = {"calisiyor": False, "iplik": None}

    def stil_btn(ana, metin, komut, renk=CIZGI):
        return tk.Button(ana, text=metin, command=komut, bg=renk,
                         fg=KOYU if renk in (VURGU, OK, HATA) else METIN,
                         activebackground=VURGU, relief="flat", bd=0, padx=12, pady=6,
                         font=("Segoe UI", 10, "bold"), cursor="hand2")

    ust = tk.Frame(kok, bg=KOYU)
    ust.pack(fill="x", padx=12, pady=(12, 6))
    tk.Label(ust, text="Kralı Yakala — Otomatik", bg=KOYU, fg=METIN,
             font=("Segoe UI", 15, "bold")).pack(side="left")
    durum_et = tk.Label(ust, text="durduruldu", bg=KOYU, fg=SOLUK, font=("Segoe UI", 10))
    durum_et.pack(side="right")

    ayar = tk.Frame(kok, bg=PANEL, highlightbackground=CIZGI, highlightthickness=1)
    ayar.pack(fill="x", padx=12, pady=6)
    tk.Label(ayar, text="Adres", bg=PANEL, fg=SOLUK, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", padx=8, pady=4)
    adres_var = tk.StringVar(value=tb.VARSAYILAN_ADRES)
    tk.Entry(ayar, textvariable=adres_var, bg=KOYU, fg=METIN, insertbackground=METIN,
             relief="flat", width=20, font=("Consolas", 9)).grid(row=0, column=1, padx=4)
    tk.Label(ayar, text="Kaç oyun (0=sonsuz)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=8)
    oyun_var = tk.IntVar(value=1)
    tk.Spinbox(ayar, from_=0, to=999, textvariable=oyun_var, width=6, bg=KOYU, fg=METIN,
               relief="flat", font=("Consolas", 9)).grid(row=0, column=3, padx=4)
    devam_var = tk.BooleanVar(value=True)
    tk.Checkbutton(ayar, text="Masa zaten açık (BAŞLAT gönderme)",
                   variable=devam_var, bg=PANEL, fg=METIN, selectcolor=KOYU,
                   activebackground=PANEL, activeforeground=METIN,
                   font=("Segoe UI", 9)).grid(row=2, column=0, columnspan=2,
                                              sticky="w", padx=8)
    tk.Label(ayar, text="Elimdeki kart (0=bilinmiyor)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=2, column=2, sticky="w", padx=8)
    elim_var = tk.IntVar(value=1)
    tk.Spinbox(ayar, from_=0, to=6, textvariable=elim_var, width=4, bg=KOYU,
               fg=METIN, relief="flat", font=("Consolas", 9)).grid(row=2, column=3)
    tk.Label(ayar, text="Hamle gecikmesi (ms)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=8, pady=4)
    gec_var = tk.IntVar(value=800)
    tk.Spinbox(ayar, from_=50, to=3000, increment=50, textvariable=gec_var, width=6,
               bg=KOYU, fg=METIN, relief="flat", font=("Consolas", 9)).grid(row=1, column=1)

    skor_et = tk.Label(kok, text="Puan: 0     El kartı: -", bg=KOYU, fg=OK,
                       font=("Segoe UI", 13, "bold"))
    skor_et.pack(anchor="w", padx=12, pady=(6, 0))

    izgara = tk.Frame(kok, bg=KOYU)
    izgara.pack(padx=12, pady=8)
    hucreler = {}
    for pos in range(25):
        h = tk.Label(izgara, text="?", width=4, height=2, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 12, "bold"), relief="flat",
                     highlightthickness=1, highlightbackground=CIZGI)
        h.grid(row=pos // 5, column=pos % 5, padx=3, pady=3)
        hucreler[pos] = h

    log = tk.Text(kok, bg=KOYU, fg=METIN, relief="flat", font=("Consolas", 9),
                  height=10, wrap="word", state="disabled")
    log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def log_yaz(s):
        log.configure(state="normal")
        log.insert("end", s + "\n")
        log.see("end")
        log.configure(state="disabled")

    def tazele(oyun):
        skor_et.configure(text="Puan: %d     El kartı: %s"
                          % (oyun.skor, oyun.el if oyun.el else "-"))
        for pos, h in hucreler.items():
            if pos in oyun.board:
                d = oyun.board[pos]
                h.configure(text=("K" if d >= 6 else str(d)),
                            fg=KOYU, bg=DEGER_RENK.get(d, METIN))
            elif pos in oyun.acilan:
                h.configure(text="·", fg=SOLUK, bg=PANEL)
            else:
                h.configure(text="?", fg=SOLUK, bg=PANEL)

    # kuyruk + tazeleme ana thread'de
    kuyruk_ref = {"q": None}

    def _tik():
        oyun = durum.get("_oyun")
        if oyun is not None:
            tazele(oyun)
            durum_et.configure(text="oynuyor" if durum["calisiyor"] else "durduruldu",
                               fg=OK if durum["calisiyor"] else SOLUK)
        q = kuyruk_ref["q"]
        if q is not None:
            while q:
                log_yaz(q.pop(0))
        kok.after(200, _tik)

    def baslat():
        if durum["calisiyor"]:
            return
        api.adres = adres_var.get().strip() or tb.VARSAYILAN_ADRES
        api._sifirla()
        durum["calisiyor"] = True
        durum_et.configure(text="oynuyor", fg=OK)
        kuyruk = []
        kuyruk_ref["q"] = kuyruk

        def sarmal():
            kopru = ApkKopru(api)
            kopru.basla()                   # kesintisiz dinlemeye başla

            def gunluk(s):
                kuyruk.append(s)
            n_oyun = oyun_var.get()
            oynanan = 0
            while durum["calisiyor"] and (n_oyun == 0 or oynanan < n_oyun):
                d = api.get("/api/durum")
                if not isinstance(d, dict):
                    kuyruk.append("APK'ye ulaşılamıyor (adres/token/adb forward?)")
                    break
                proxy = d.get("proxy") or {}
                kuyruk_d = d.get("kuyruk") or {}
                if not (bool(proxy.get("acik")) and bool(proxy.get("bagli"))
                        and bool(proxy.get("enjeksiyon"))
                        and "Proxy" in str(kuyruk_d.get("kanal", ""))):
                    kuyruk.append("KAPI KAPALI — proxy/enjeksiyon/kanal(Proxy) aç")
                    break
                oyun = durum.get("_oyun") if (devam_var.get() and oynanan) else None
                if oyun is None:
                    oyun = KralOyun(kopru.gonder, kopru.ee_al,
                                    gecikme=gec_var.get() / 1000.0, gunluk=gunluk,
                                    sifirla=kopru.sifirla)
                oyun.gecikme = gec_var.get() / 1000.0
                durum["_oyun"] = oyun
                kuyruk.append("== yeni oyun ==")
                ie = elim_var.get() or None
                oyun.oyna(lambda: durum["calisiyor"],
                          ilk_el=ie if oynanan == 0 else None,
                          baslat=not devam_var.get(),
                          devam=devam_var.get() and oynanan > 0)
                oynanan += 1
            kopru.dur()
            durum["calisiyor"] = False
            kuyruk.append("== durduruldu ==")

        durum["iplik"] = threading.Thread(target=sarmal, daemon=True)
        durum["iplik"].start()

    def dur():
        durum["calisiyor"] = False

    dug = tk.Frame(kok, bg=KOYU)
    dug.pack(fill="x", padx=12, pady=(0, 10))
    stil_btn(dug, "▶ Otomatik oyna", baslat, OK).pack(side="left")
    stil_btn(dug, "■ Durdur", dur, HATA).pack(side="left", padx=8)

    def tani_bas():
        if durum["calisiyor"]:
            return
        api.adres = adres_var.get().strip() or tb.VARSAYILAN_ADRES
        api._sifirla()
        kuyruk = []
        kuyruk_ref["q"] = kuyruk
        kuyruk.append("== TANI (6 sn ham trafik) ==")
        threading.Thread(target=lambda: tani(api, kuyruk.append),
                         daemon=True).start()

    stil_btn(dug, "🔍 Tanı", tani_bas).pack(side="left", padx=8)

    tk.Label(dug, text="mod", bg=KOYU, fg=SOLUK,
             font=("Segoe UI", 9)).pack(side="left", padx=(12, 2))
    mod_var = tk.IntVar(value=0)
    tk.Spinbox(dug, from_=0, to=3, textvariable=mod_var, width=3, bg=PANEL,
               fg=METIN, relief="flat", font=("Consolas", 9)).pack(side="left")
    tk.Label(dug, text="arg", bg=KOYU, fg=SOLUK,
             font=("Segoe UI", 9)).pack(side="left", padx=(6, 2))
    arg_var = tk.IntVar(value=1)
    tk.Spinbox(dug, from_=0, to=24, textvariable=arg_var, width=3, bg=PANEL,
               fg=METIN, relief="flat", font=("Consolas", 9)).pack(side="left")

    def tek_bas():
        if durum["calisiyor"]:
            return
        api.adres = adres_var.get().strip() or tb.VARSAYILAN_ADRES
        api._sifirla()
        m, a = mod_var.get(), arg_var.get()
        kuyruk = []
        kuyruk_ref["q"] = kuyruk
        kuyruk.append("== TEK PAKET (mod=%d arg=%d) — oyuna DOKUNMA ==" % (m, a))
        threading.Thread(target=lambda: tek_paket(api, kuyruk.append, m, a),
                         daemon=True).start()

    stil_btn(dug, "🧪 Tek paket", tek_bas).pack(side="left", padx=8)

    log_yaz("Hazır. Oyunda kart masasının başına geç, üç kapıyı aç, sonra 'Otomatik oyna'.")
    _tik()
    kok.mainloop()


# ── APK'sız benzetim testi ───────────────────────────────────────────────
def _test():
    print("KRALI YAKALA beyin testi (benzetim)")

    class Sunucu:
        """Basit Kralı Yakala sunucusu — kuralları uygular, ee olayları üretir."""
        def __init__(self, tohum=0):
            r = random.Random(tohum)
            # 25 kart: değerler 1-5 dağınık + tek 6 (Kral)
            self.board = [r.choice([1, 1, 2, 2, 3, 3, 4, 5]) for _ in range(25)]
            self.board[r.randrange(25)] = 6
            self.acik = [False] * 25
            # el: 5x1,2x2,2x3,1x4,1x5,1x6(Kral)
            self.el_destesi = [1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 6]
            self.el_sira = 0
            self.el = None
            self.skor = 0
            self.kuyruk = []

        def gonder(self, paket):
            mod, arg = paket[1], paket[2]
            if mod == 0:
                self.kuyruk.append(("baslat",))
            elif mod == 1:                                  # sıradaki el kartı
                if self.el_sira < len(self.el_destesi):
                    self.el = self.el_destesi[self.el_sira]
                    self.el_sira += 1
                    self.kuyruk.append(("el", self.el))
                # deste bittiyse cevap yok (bot bunu 'el bitti' sayar)
            elif mod == 2:                                  # aç pos
                pos = arg
                if 0 <= pos < 25 and not self.acik[pos] and self.el:
                    V = self.board[pos]
                    H = self.el
                    # KURU KAFA: açtığın kartın komşusunda KAPALI 5 var mı
                    kafa5 = 1 if any(self.board[n] == 5 and not self.acik[n]
                                     for n in KralOyun._komsular(pos)) else 0
                    if H == 6:                              # Kral yalnız 6'yı yakalar
                        aldi = (V == 6)
                        if aldi:
                            self.skor += 100
                            self.acik[pos] = True           # yakalandı → kalkar
                        bitti = 1
                    elif H == 5 and kafa5:                  # TUZAK: 5 kartın yakalanır
                        aldi = 0
                        bitti = 1
                    else:
                        aldi = (V <= H)                     # H, 1..H değerini yakalar
                        if aldi:
                            self.skor += V * 10
                            self.acik[pos] = True           # yakalandı → kalkar
                        bitti = 0 if (aldi and V < H) else 1
                    # MODEL (b): ıska/tuzak → acik False kalır, kart geri kapanır;
                    # değeri görüldü (deftere yazılır), sonra doğru kartla açılır.
                    self.kuyruk.append(("sonuc", pos, V, self.skor,
                                        1 if aldi else 0, bitti, kafa5))
            elif mod == 3:
                self.kuyruk.append(("odul", self.skor))

        def ee_al(self):
            c = self.kuyruk
            self.kuyruk = []
            return c

    s = Sunucu(tohum=42)
    oyun = KralOyun(s.gonder, s.ee_al, gecikme=0.0, gunluk=lambda x: None)
    skor = oyun.oyna(lambda: True)
    print("board       :", s.board)
    print("açılan sayısı:", sum(s.acik))
    print("beyin skoru :", skor, " sunucu skoru:", s.skor)
    print("el destesi bitti mi:", oyun.el is not None)
    tamam = (skor == s.skor and sum(s.acik) > 0)
    print("SONUÇ:", "TAMAM" if tamam else "HATA")
    sys.exit(0 if tamam else 1)


def main():
    ap = argparse.ArgumentParser(description="Kralı Yakala otomatik panel")
    ap.add_argument("--test", action="store_true", help="APK'sız benzetim testi")
    a = ap.parse_args()
    if a.test:
        _test()
    else:
        _main_gui()


if __name__ == "__main__":
    main()
