# -*- coding: utf-8 -*-
"""
KRALI YAKALA — GÖZLE OYNATICI (çekirdek; panel de bunu kullanır)

Paket yolu bırakıldı: oradaki cevaplar 374-4010 ms gecikiyor, eldeki kart
1↔2↔4↔6 diye zıplıyordu. Burada durum EKRANDAN okunur, hamle EKRANA tıklanır
(adb input tap) ve sonuç yine EKRANDAN doğrulanır.

NOT DEFTERİ — neden şart:
    YAKALANAN kart ekranda DURUYOR (Puan 30 iken üç tane 1 görünüyordu), ama
    YAKALANAMAYAN kart geri kapanıyor, ekranda görünmüyor. Yani ekranı her
    turda sıfırdan okursak ıskaladığımız kartın değerini UNUTURUZ. Bu yüzden
    gördüğümüz her değeri kalıcı deftere yazıyoruz; beyin masayı defterden
    görür, ekrandan değil.

KULLANIM
--------
    python tools/kral_oyna.py            # oyna
    python tools/kral_oyna.py --kuru     # tıklama YOK, sadece kararı yaz
    python tools/kral_oyna.py --hamle 8  # en fazla 8 hamle

Oyunda "Pop-Up" kutusunun işareti KALDIRILMIŞ olmalı.
"""

import argparse
import importlib.util
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

import kral_goz as goz                                  # noqa: E402

_sp = importlib.util.spec_from_file_location(
    'kral_beyin', os.path.join(_KOK, 'kral_panel.py'))
kp = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(kp)

# Deste bileşimi ekrandaki sayılarla doğrulandı
DESTE_BASLANGIC = {1: 5, 2: 2, 3: 2, 4: 1, 5: 1, 6: 1}


class GozOyuncu:
    """Ekranı okuyup tıklayarak oynar; kalıcı not defteri tutar."""

    def __init__(self, gunluk=None, bekle=1.0, kuru=False, sunucu=False):
        self.gunluk = gunluk or (lambda s: None)
        self.bekle = bekle
        self.kuru = kuru
        # KARMA MOD: bakış ekrandan, hamle sunucudan (e2 paketi).
        self.sunucu = bool(sunucu)
        self.kopru = None
        if self.sunucu and not kuru:
            self.kopru = kp.ApkKopru(kp.tb.Api())
            self.kopru.basla()          # 0xee'leri arka planda dinle (yedek okuma)
        self.beyin = kp.KralOyun(lambda p: None, lambda: [], gecikme=0.0,
                                 gunluk=lambda s: None)
        self.sifirla()

    def sifirla(self):
        self.defter = {}            # pos -> değer (KALICI; ıska geri kapanır)
        self.kafali = set()         # ekranda kafa ikonu olan hücreler
        self.kafa_karti = {}        # pos -> bu kartı açınca YENİ kafa çıktı mı
        self.yakalanan = set()      # kuraldan çıkarılan: alınmış kartlar
        self.kalan = dict(DESTE_BASLANGIC)
        self.durum = None
        self.hamle = 0
        self._ilk_okuma = True      # ilk karede görünenler zaten alınmıştır

    # ── ekran → defter → beyin ───────────────────────────────────────────
    def _deftere_yaz(self, d):
        """Ekranda görülen her değeri kalıcı deftere işler.

        İLK karede görünen değerler ZATEN ALINMIŞ kartlardır: ıskalanan kart
        geri kapanır, yalnız yakalanan kart değeriyle ekranda kalır. Bunları
        işaretlemezsek bot üstlerine tekrar tıklayıp hamle harcar."""
        ilk = self._ilk_okuma
        yeni_alinan = []
        for i, v in enumerate(d['masa']):
            if isinstance(v, int):
                self.defter[i] = v
                if ilk:
                    self.yakalanan.add(i)
                    yeni_alinan.append(i)
        self.kafali |= set(d.get('kafa') or [])
        if ilk:
            self._ilk_okuma = False
            if yeni_alinan:
                self.gunluk('masada zaten alınmış %d kart var: %s '
                            '(tekrar tıklamayacağım)'
                            % (len(yeni_alinan), yeni_alinan))

    def _beyne_aktar(self):
        """Defteri + kuru kafaları beynin modeline yazar.

        Kuru kafa çevirisi: oyun kafa ikonunu AÇILAN kartın KOMŞULARINA
        çiziyor; beyin ise 'açılan kartın yanında 5 var mı' diye tutuyor."""
        b = self.beyin
        b.board = dict(self.defter)
        b.acilan = set(self.yakalanan)
        # Yalnız KENDİ açtığımız kartların kafa bilgisini kullan (atfedilebilir).
        # Ekrandaki kafa ikonlarından geriye doğru çıkarım yapmak çelişki
        # üretiyordu; bkz. modül başlığı.
        b.kafa = dict(self.kafa_karti)
        if self.durum and isinstance(self.durum.get('el'), int):
            b.el = self.durum['el']

    # ── eylem: sunucu paketi ya da ekrana dokunma ───────────────────────
    def _kapilar_acik(self):
        """Sunucu modu için üç kapı (proxy/bağlı/enjeksiyon) açık mı?"""
        try:
            d = self.kopru.api.get("/api/durum")
        except Exception:                               # noqa: BLE001
            return False, "APK'ye ulaşılamıyor"
        if not isinstance(d, dict):
            return False, "APK'ye ulaşılamıyor"
        p = d.get("proxy") or {}
        if not (p.get("acik") and p.get("bagli") and p.get("enjeksiyon")):
            return False, "kapılar kapalı (proxy/bağlı/enjeksiyon)"
        return True, ""

    def _eylem_ac(self, pos, x, y):
        """Masadaki pos'u aç. Sunucu modunda paket, yoksa ekrana dokun."""
        if self.sunucu and self.kopru is not None:
            self.kopru.gonder(kp.paket_e2(2, pos))
            return True, "paket e2 02 %02x" % pos
        return goz.ekrana_bas(x, y)

    def _eylem_kart(self, x, y):
        """Desteden kart seç. Sunucu modunda 'sıradaki kartı ver' paketi."""
        if self.sunucu and self.kopru is not None:
            self.kopru.gonder(kp.paket_e2(1, 0))
            return True, "paket e2 01 00"
        return goz.ekrana_bas(x, y)

    def _paketten_deger(self, pos):
        """0xee sonuç paketinden pos'un değeri (ekran kaçırdıysa yedek).

        Iskalanan kart ekran görüntüsü alınmadan geri kapanabiliyor; paket
        değeri yine de bildiriyor. Gecikmesi sorun değil, deftere yazmak için
        zamanında gelmesi yeterli."""
        if self.kopru is None:
            return None
        try:
            for o in self.kopru.ee_al():
                if o and o[0] == "sonuc" and o[1] == pos:
                    return o[2]
        except Exception:                               # noqa: BLE001
            pass
        return None

    # ── adımlar ──────────────────────────────────────────────────────────
    def adim(self):
        """Bir adım oynar. Döner: True (devam) / False (dur)."""
        d = goz.durum_oku()
        if not d:
            self.gunluk('X masa okunamadı — Kralı Yakala penceresi açık mı?')
            return False
        self.durum = d
        self._deftere_yaz(d)
        self._beyne_aktar()
        if not isinstance(d.get('el'), int):
            return self._kart_sec(d)
        return self._kart_ac(d)

    def _kart_sec(self, d):
        """Kartım boşsa desteden EN KÜÇÜĞÜ seç (kural: küçükten büyüğe)."""
        deste = d.get('deste') or {}
        aday = [k for k in sorted(deste) if self.kalan.get(k, 0) > 0]
        if not aday:
            self.gunluk('destede kullanılabilir kart kalmadı — oyun bitti.')
            return False
        kart = aday[0]
        x, y = deste[kart]
        self.gunluk('[%d] elde kart yok → desteden %s seçiliyor'
                    % (self.hamle + 1, goz.AD.get(kart, kart)))
        if self.kuru:
            return False
        ok, bilgi = self._eylem_kart(x, y)
        if not ok:
            self.gunluk('  X hamle gönderilemedi: %s' % bilgi)
            return False
        time.sleep(self.bekle)
        sonra = goz.durum_oku()
        if sonra:
            self._deftere_yaz(sonra)
            el = sonra.get('el')
            if el == kart:
                self.kalan[kart] = max(0, self.kalan.get(kart, 0) - 1)
                self.gunluk('  → Kartım = %s' % goz.AD.get(kart, kart))
            elif isinstance(el, int):
                self.kalan[el] = max(0, self.kalan.get(el, 0) - 1)
                self.gunluk('  → Kartım = %s (beklenen %s değildi)'
                            % (goz.AD.get(el), goz.AD.get(kart)))
            else:
                self.kalan[kart] = 0
                self.gunluk('  → Kartım boş kaldı; %s bitmiş sayıyorum'
                            % goz.AD.get(kart, kart))
        self.hamle += 1
        return True

    def _kart_ac(self, d):
        """Beynin seçtiği hücreyi aç, sonucu ekrandan doğrula."""
        pos = self.beyin._sonraki_pos()
        if pos is None:
            self.gunluk('beyin açacak hücre bulamadı — bitiriyorum.')
            return False
        H = d['el']
        x, y = d['merkez'][pos]
        self.gunluk('[%d] elde %s → masa[%d] açılıyor'
                    % (self.hamle + 1, goz.AD.get(H), pos))
        if self.kuru:
            return False
        ok, bilgi = self._eylem_ac(pos, x, y)
        if not ok:
            self.gunluk('  X hamle gönderilemedi: %s' % bilgi)
            return False
        time.sleep(self.bekle)

        yeni = goz.durum_oku()
        if not yeni:
            self.gunluk('  ! sonuç okunamadı')
            self.hamle += 1
            return True
        onceki_kafa = set(d.get('kafa') or [])
        self._deftere_yaz(yeni)
        degisen = [i for i in range(25) if d['masa'][i] != yeni['masa'][i]]
        # Bu açılışın KENDİ kafa bilgisi: pos'un komşularında YENİ kafa çıktı mı?
        yeni_kafa = set(yeni.get('kafa') or []) - onceki_kafa
        komsu = set(self.beyin._komsular(pos))
        if yeni_kafa & komsu:
            self.kafa_karti[pos] = True
        elif isinstance(yeni['masa'][pos], int) or degisen:
            self.kafa_karti[pos] = False        # açıldı ama kafa çıkmadı
        V = yeni['masa'][pos]
        if not isinstance(V, int):
            # Iska: kart ekran görüntüsünden ÖNCE geri kapanmış olabilir.
            # Değeri 0xee paketinden al (sunucu modunda), yoksa defterden.
            V = self._paketten_deger(pos)
            if isinstance(V, int):
                self.defter[pos] = V
                self.gunluk('  (değeri paketten aldım: masa[%d]=%d)' % (pos, V))
            else:
                V = self.defter.get(pos)
        not_ = ''
        if not degisen and yeni.get('el') == H:
            self.yakalanan.add(pos)
            not_ = '  [değişmedi → zaten alınmış]'
        elif isinstance(V, int) and isinstance(H, int):
            kafali = pos in (yeni.get('kafa') or [])
            if H == 6:
                alindi = (V == 6)
            elif H == 5 and kafali:
                alindi = False                # 5 tuzağı: puan yok
            else:
                alindi = (V <= H)
            if alindi:
                self.yakalanan.add(pos)
                not_ = '  [YAKALANDI +%d]' % (100 if V == 6 else V * 10)
            else:
                not_ = '  [ıskaladı — deftere yazdım]'
        self.gunluk('  → masa[%d] = %s | değişen: %s | Kartım: %s%s'
                    % (pos, goz.AD.get(V, '·'), degisen,
                       goz.AD.get(yeni.get('el'), 'boş'), not_))
        self.hamle += 1
        return True

    def _ilerleme(self):
        """Oyunun ilerlediğini gösteren özet: defter / alınan / kalan deste."""
        return (len(self.defter), len(self.yakalanan),
                sum(self.kalan.values()))

    def oyna(self, calisiyor=None, max_hamle=None):
        """Oyun BİTENE KADAR oynar.

        max_hamle yalnız son çare emniyeti (None = sınırsız). Asıl durma
        ölçütü ilerlemedir: deste biterse, beyin açacak yer bulamazsa ya da
        üst üste hiçbir şey değişmezse durur."""
        calisiyor = calisiyor or (lambda: True)
        if self.sunucu and self.kopru is not None:
            ok, neden = self._kapilar_acik()
            self.gunluk('mod: gözle BAK + sunucudan OYNA  (%s)'
                        % ('kapılar açık' if ok else 'UYARI: ' + neden))
            if not ok:
                self.gunluk('  sunucu modu çalışmaz; tambot kapılarını aç ya da '
                            'ekrana dokunma moduna geç.')
                return
        elif not self.kuru:
            self.gunluk('mod: gözle BAK + ekrana DOKUN')
        onceki, duragan = self._ilerleme(), 0
        while calisiyor():
            if max_hamle is not None and self.hamle >= max_hamle:
                self.gunluk('hamle sınırına ulaşıldı (%d).' % max_hamle)
                return
            if not self.adim():
                self.gunluk('oyun bitti — %d hamle, %d kart alındı, defterde %d kart.'
                            % (self.hamle, len(self.yakalanan), len(self.defter)))
                return
            simdi = self._ilerleme()
            duragan = 0 if simdi != onceki else duragan + 1
            onceki = simdi
            if duragan >= 6:
                self.gunluk('6 hamledir hiçbir şey ilerlemiyor — duruyorum '
                            '(%d kart alındı).' % len(self.yakalanan))
                return


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kralı Yakala — gözle oynatıcı')
    ap.add_argument('--kuru', action='store_true',
                    help='tıklama yok; sadece kararı yaz')
    ap.add_argument('--hamle', type=int, default=None,
                    help='emniyet sınırı (varsayılan: oyun bitene kadar)')
    ap.add_argument('--bekle', type=float, default=1.0,
                    help='hamle sonrası bekleme (sn)')
    ap.add_argument('--sunucu', action='store_true',
                    help='hamleyi sunucuya paketle gönder (bakış yine ekrandan)')
    a = ap.parse_args(argv)
    GozOyuncu(gunluk=print, bekle=a.bekle, kuru=a.kuru,
              sunucu=a.sunucu).oyna(max_hamle=a.hamle)


if __name__ == '__main__':
    main()
