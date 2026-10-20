# -*- coding: utf-8 -*-
"""
PAZAR TARAYICI — oyuncu dükkânlarını gezip içindekileri BİLDİRİR.

SATIN ALMA YOK. Bot yalnızca dükkânları açıp içeriği okur, kapatır ve bulduğunu
listeler. Hiçbir alım/satım paketi göndermez.

Nasıl çalışır
-------------
  1. /api/varliklar → oyuncu dükkânlarını süz (tip=1, vnum=30000, "... Marketi")
  2. Her dükkâna tıkla:  1A|vid + 07(bFunc=0 DUR)  — tek başına 0x1A yetmiyor
  3. Gelen 0x26 GC_SHOP'u çöz (80 slot × 43 bayt: vnum/fiyat/adet)
  4. 32 00 ile kapat, sıradakine geç
  5. Eşleşenleri bildir (ad filtresi + en yüksek fiyat)

vnum → ad tablosu items_tr.txt'ten okunur (28.655 eşya).

KULLANIM
--------
    python tools/pazar_tara.py --ara "iksir" --azami 50000
    python tools/pazar_tara.py --ara "kral ganimeti"
    python tools/pazar_tara.py --liste          # sadece dükkânları say, açma
"""

import argparse
import importlib.util
import json
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

# items_tr.txt aranacak yerler (ilk bulunan kullanılır)
AD_DOSYALARI = (
    os.path.join(_KOK, 'items_tr.txt'),
    os.path.join(_KOK, 'veri', 'items_tr.txt'),
    r'C:\Users\Abdulkadir\Desktop\romia 2 bot 2\source\resources\assets\items_tr.txt',
)


def ad_fold(s):
    """Türkçe-duyarsız karşılaştırma için sadeleştir.

    DİKKAT — büyük harfler KÜÇÜLTMEDEN ÖNCE çevrilmeli: Python'da
    'İ'.lower() 'i' + U+0307 (birleşen nokta) üretiyor, yani iki karakter.
    Önce küçültüp sonra çevirmek o noktayı bırakıyordu ve "Mavi İksir(B)"
    aramada 'iksir' ile HİÇ eşleşmiyordu."""
    s = (s or '').strip()
    for a, b in (('İ', 'I'), ('Ş', 'S'), ('Ğ', 'G'), ('Ü', 'U'),
                 ('Ö', 'O'), ('Ç', 'C'), ('Â', 'A'), ('Î', 'I')):
        s = s.replace(a, b)
    s = s.lower().replace('\u0307', '')        # kalan birleşen noktayı at
    for a, b in (('ı', 'i'), ('ş', 's'), ('ğ', 'g'), ('ü', 'u'),
                 ('ö', 'o'), ('ç', 'c'), ('â', 'a'), ('î', 'i')):
        s = s.replace(a, b)
    return s


class EsyaAdlari:
    """vnum → eşya adı (items_tr.txt)."""

    def __init__(self, yol=None):
        self.tablo = {}
        self.yol = None
        for y in ([yol] if yol else []) + list(AD_DOSYALARI):
            if y and os.path.exists(y):
                self._yukle(y)
                self.yol = y
                break

    def _yukle(self, yol):
        try:
            with open(yol, encoding='utf-8', errors='replace') as f:
                for satir in f:
                    p = satir.rstrip('\n').split('\t', 1)
                    if len(p) == 2 and p[0].strip().isdigit():
                        self.tablo[int(p[0])] = p[1].strip()
        except Exception:                               # noqa: BLE001
            pass

    def ad(self, vnum):
        return self.tablo.get(int(vnum), 'vnum %d' % vnum)


class PazarTarayici:
    """Dükkânları gezer, içeriği okur. Hiçbir şey satın almaz."""

    ONBELLEK = os.path.join(_KOK, 'veri', 'pazar_onbellek.json')

    def __init__(self, api=None, gunluk=None, adlar=None, bekle=0.4):
        self.api = api or tb.Api()
        self.gunluk = gunluk or (lambda s: None)
        self.adlar = adlar or EsyaAdlari()
        # Sunucu 60 ms'de cevaplıyor (kayıtla ölçüldü); 0.4 sn fazlasıyla yeter.
        self.bekle = bekle
        self.dukkanlar = {}   # (kanal,vid) -> {ad, esyalar, zaman, kanal, vid}
        self._gorulen_log = None
        self.kanal = 0
        # Etkileşim menzili dar; uzaktaki dükkâna tıklamak boşuna
        # paket. 0 = sınırsız (elle büyütülebilir).
        self.azami_ham = 1000          # 10 m
        self.onbellek_yukle()

    # ── önbellek: bir kez oku, sonra anında ara ─────────────────────────
    def onbellek_yukle(self):
        try:
            with open(self.ONBELLEK, encoding='utf-8') as f:
                for d in json.load(f):
                    self.dukkanlar[(d.get('kanal', 0), d['vid'])] = d
            if self.dukkanlar:
                self.gunluk('önbellek: %d dükkân yüklendi' % len(self.dukkanlar))
        except Exception:                               # noqa: BLE001
            pass

    def onbellek_kaydet(self):
        try:
            os.makedirs(os.path.dirname(self.ONBELLEK), exist_ok=True)
            with open(self.ONBELLEK, 'w', encoding='utf-8') as f:
                json.dump(list(self.dukkanlar.values()), f, ensure_ascii=False)
        except Exception as e:                          # noqa: BLE001
            self.gunluk('önbellek yazılamadı: %s' % type(e).__name__)

    def kanal_oku(self):
        """Bağlı olunan kanal (port'tan). Dükkânlar kanala göre ayrı tutulur."""
        d = self.api.get('/api/durum')
        if not isinstance(d, dict):
            return 0
        p = d.get('proxy') or {}
        try:
            k = int(p.get('kanal', 0) or 0)
        except (TypeError, ValueError):
            k = 0
        if not k:
            try:
                k = tb.port_kanali(int(p.get('port', 0) or 0))
            except (TypeError, ValueError):
                k = 0
        return k

    def bayat_mi(self, kanal, vid, tazelik_dk):
        d = self.dukkanlar.get((kanal, vid))
        if not d:
            return True
        if not tazelik_dk:
            return False
        return (time.time() - d.get('zaman', 0)) > tazelik_dk * 60

    # ── yardımcılar ─────────────────────────────────────────────────────
    def kapilar(self):
        d = self.api.get('/api/durum')
        if not isinstance(d, dict):
            return False, "APK'ye ulaşılamıyor", None
        p = d.get('proxy') or {}
        if not (p.get('acik') and p.get('bagli') and p.get('enjeksiyon')):
            return False, 'kapılar kapalı (proxy/bağlı/enjeksiyon)', d
        return True, '', d

    def dukkanlari_bul(self, bx=None, by=None, azami_ham=0):
        """Oyuncu dükkânları: [(vid, ad, x, y, mesafe_ham), ...] — YAKINDAN uzağa.

        Mesafe önemli: dükkânlar 1.9-31.5 m arasına yayılıyor ama etkileşim
        menzili dar. Uzaktakine tıklamak boşuna paket; sunucu yok sayıyor."""
        vs = self.api.get('/api/varliklar', n=200)
        if not isinstance(vs, list):
            return []
        out = []
        for v in vs:
            if not (pp.dukkan_mi(v) and v.get('vid')):
                continue
            ad = v.get('ad') or v.get('isim') or '?'
            vx, vy = v.get('x'), v.get('y')
            m = None
            if bx and by and vx is not None and vy is not None:
                m = math.hypot(int(vx) - bx, int(vy) - by)
            out.append((int(v['vid']), ad,
                        int(vx) if vx is not None else 0,
                        int(vy) if vy is not None else 0,
                        m))
        if bx and by:
            out.sort(key=lambda t: (t[4] is None, t[4] or 0))
            if azami_ham:
                out = [t for t in out if t[4] is not None and t[4] <= azami_ham]
        return out

    def _konumum(self):
        d = self.api.get('/api/durum') or {}
        k = d.get('konum') or {}
        return (int(k.get('x', 0) or 0), int(k.get('y', 0) or 0),
                int(d.get('tik', 0) or 0), d)

    # ── log okuma: HALKA TAMPON, indeksle değil HİZALAMAYLA ────────────
    # /api/log son N kaydı verir; dolduktan sonra uzunluk sabit kalır. Bu
    # yüzden "kaçıncı kayıttan sonrası yeni" diye indeks tutmak ÇALIŞMAZ
    # (kayit[200:] hep boş döner). Listeyi bir öncekiyle hizalayıp yalnız
    # SONA EKLENENLERİ alıyoruz. Anahtara 'zaman' KOYMUYORUZ: sorgudan
    # sorguya değişebiliyor ve hizalamayı çökertiyor.
    LOG_N = 400

    @staticmethod
    def _anahtar(k):
        return (k.get('opcode'), k.get('hex'), bool(k.get('giden')))

    def _log_sifirla(self):
        """O ana kadarki log'u 'görülmüş' say (bayat 0x26 karışmasın)."""
        kayit = self.api.get('/api/log', n=self.LOG_N)
        self._gorulen_log = ([self._anahtar(k) for k in kayit]
                             if isinstance(kayit, list) else [])

    def _yeni_kayitlar(self):
        """Log'a SONRADAN eklenen kayıtlar."""
        kayit = self.api.get('/api/log', n=self.LOG_N)
        if not isinstance(kayit, list):
            return []
        anah = [self._anahtar(k) for k in kayit]
        onceki = self._gorulen_log
        self._gorulen_log = anah
        if onceki is None:
            return []
        for k in range(len(anah) + 1):
            ort = len(anah) - k
            if ort <= len(onceki) and anah[:ort] == onceki[len(onceki) - ort:]:
                return kayit[ort:]
        return kayit[-20:]          # hizalanamadı (taşma) → yalnız son kayıtlar

    def _yeni_shop_paketleri(self):
        """Yeni kayıtlardan 0x26 çerçevelerini çöz."""
        cikti = []
        for k in self._yeni_kayitlar():
            if k.get('giden') or k.get('opcode') != pp.BASLIK:
                continue
            hx = k.get('hex') or ''
            try:
                b = bytes(int(x, 16) for x in hx.split())
            except ValueError:
                continue
            for cer in pp.cerceveleri_ayikla(b):
                d = pp.coz(cer)
                if d and d['alt'] == pp.ALT_ICERIK:
                    cikti.append(d)
        return cikti

    # ── tanı: tek dükkâna tıkla, log'da ne göründüğünü DÖK ──────────────
    def tani(self, vid=None, sure=4.0):
        ok, neden, d = self.kapilar()
        self.gunluk('kapılar: %s' % ('AÇIK' if ok else neden))
        if not ok:
            return
        bx, by, tik, _d = self._konumum()
        liste = self.dukkanlari_bul(bx, by)
        self.gunluk('görünen dükkân: %d' % len(liste))
        if not liste:
            return
        sec = liste[0] if vid is None else next(
            (t for t in liste if t[0] == vid), liste[0])
        vid, ad, hx, hy, m = sec
        self.gunluk('konum: x=%d y=%d tik=%d' % (bx, by, tik))
        if not (bx and by):
            self.gunluk('X konum bilinmiyor — paket okuyucu açık mı?')
            return
        brot = tb.yon_bayti(hx - bx, hy - by) if (hx or hy) else 0
        self.gunluk('hedef: %s  (%.1f m, bRot=%d)' % (ad, (m or 0) / 100.0, brot))
        paket = tb.paket_tikla_tam(vid, bx, by, tik, brot=brot)
        self.gunluk('gönderiliyor (%d bayt): %s' % (len(paket), paket.hex(' ')))
        self._log_sifirla()
        cevap = self.api.enjekte(paket)
        self.gunluk('/api/enjekte: %r' % (cevap,))
        t0 = time.time()
        sayac = {}
        en_uzun = 0
        while time.time() - t0 < sure:
            time.sleep(0.15)
            for k in self._yeni_kayitlar():
                op = k.get('opcode') or 0
                yon = 'giden' if k.get('giden') else 'gelen'
                sayac[(yon, op)] = sayac.get((yon, op), 0) + 1
                hx = k.get('hex') or ''
                n = len(hx.split())
                if not k.get('giden') and op == pp.BASLIK:
                    en_uzun = max(en_uzun, n)
                    self.gunluk('  ← 0x26 geldi: %d bayt (tam paket %d olmalı)'
                                % (n, pp.ICERIK_BOY))
                    for cer in pp.cerceveleri_ayikla(
                            bytes(int(x, 16) for x in hx.split())):
                        c = pp.coz(cer)
                        if c:
                            self.gunluk('     alt=%s sahip=%s eşya=%d'
                                        % (c['alt'], c['sahip_vid'],
                                           len(c['esyalar'])))
        self.api.enjekte(tb.paket_dukkan_kapat())
        self.gunluk('%s — tanı bitti' % ad)
        self.gunluk('log\'da görülenler: %s'
                    % '  '.join('%s 0x%02X x%d' % (y, o, n)
                                for (y, o), n in sorted(sayac.items())))
        if not en_uzun:
            self.gunluk('SONUÇ: 0x26 HİÇ görünmedi → paket çıkmıyor ya da '
                        'sunucu dükkânı açmıyor.')
        elif en_uzun < pp.ICERIK_BOY:
            self.gunluk('SONUÇ: 0x26 geldi ama KISA (%d/%d) → log hex\'i '
                        'kırpıyor; okuma yolunu değiştirmeliyiz.'
                        % (en_uzun, pp.ICERIK_BOY))
        else:
            self.gunluk('SONUÇ: 0x26 TAM geldi — tarama çalışmalı.')

    # ── tek dükkân ──────────────────────────────────────────────────────
    def dukkan_oku(self, vid, ad='?', hx=0, hy=0):
        """Dükkânı açar, içeriği okur, kapatır. Döner: eşya listesi ya da None."""
        bx, by, tik, d = self._konumum()
        if not (bx and by):
            self.gunluk('konum bilinmiyor — proxy/paket okuyucu açık mı?')
            return None

        self._log_sifirla()
        # 0x1A TEK BAŞINA dükkânı açmıyor; 0x07 (bFunc=0 DUR) ile birlikte gider.
        # bRot ÖNEMLİ: paketin anlamı "durdum ve ONA DÖNDÜM". Gerçek istemci
        # dükkâna dönük bir yön gönderiyor (kayıtta 7), biz 0 gönderdiğimizde
        # sunucu cevap vermiyordu.
        brot = tb.yon_bayti(hx - bx, hy - by) if (hx or hy) else 0
        self.api.enjekte(tb.paket_tikla_tam(vid, bx, by, tik, brot=brot))
        bitis = time.time() + max(2.0, self.bekle * 2)
        esyalar = None
        while time.time() < bitis:
            time.sleep(0.15)
            for s in self._yeni_shop_paketleri():
                if s['sahip_vid'] == vid or esyalar is None:
                    esyalar = s['esyalar']
            if esyalar is not None:
                break
        # her durumda kapat (açık dükkân sonrakini engelliyor)
        self.api.enjekte(tb.paket_dukkan_kapat())
        time.sleep(0.2)
        if esyalar is None:
            self.gunluk('  %s — cevap gelmedi' % ad)
            return None
        self.dukkanlar[(self.kanal, vid)] = {
            'vid': vid, 'kanal': self.kanal, 'ad': ad,
            'esyalar': esyalar, 'zaman': time.time()}
        return esyalar

    # ── tarama ──────────────────────────────────────────────────────────
    def tara(self, calisiyor=None, en_fazla=0, tazelik_dk=60):
        """Görünen dükkânları tarar. Önbellekte TAZE olanı tekrar açmaz.

        tazelik_dk=0 → önbellektekine hiç dokunma (yalnız yeni dükkânlar)."""
        calisiyor = calisiyor or (lambda: True)
        ok, neden, _ = self.kapilar()
        if not ok:
            self.gunluk('X %s — dükkân açmak için enjeksiyon gerekiyor.' % neden)
            return 0
        self.kanal = self.kanal_oku()
        bx, by, _tik, _d = self._konumum()
        liste = self.dukkanlari_bul(bx, by, self.azami_ham)
        if not liste:
            self.gunluk('menzilde oyuncu dükkânı yok (pazarda mısın? '
                        'menzili büyüt ya da dükkânların arasına yürü)')
            return 0
        yeni = [t for t in liste if self.bayat_mi(self.kanal, t[0], tazelik_dk)]
        atlanan = len(liste) - len(yeni)
        if en_fazla:
            yeni = yeni[:en_fazla]
        self.gunluk('ch%s: %d dükkân görünüyor, %d taze (atlandı), %d açılacak'
                    % (self.kanal or '?', len(liste), atlanan, len(yeni)))
        okunan = 0
        for i, (vid, ad, hx, hy, m) in enumerate(yeni, 1):
            if not calisiyor():
                self.gunluk('durduruldu')
                break
            esyalar = self.dukkan_oku(vid, ad, hx, hy)
            if esyalar is not None:
                okunan += 1
                self.gunluk('[%d/%d] %s (%.1f m) — %d eşya'
                            % (i, len(yeni), ad, (m or 0) / 100.0, len(esyalar)))
            time.sleep(self.bekle)
        if okunan:
            self.onbellek_kaydet()
        return okunan

    def kapsam(self):
        """Önbellekte ne var: kanal -> (dükkân sayısı, en eski kayıt yaşı dk)."""
        out = {}
        simdi = time.time()
        for (k, _v), d in self.dukkanlar.items():
            n, yas = out.get(k, (0, 0))
            out[k] = (n + 1, max(yas, (simdi - d.get('zaman', simdi)) / 60.0))
        return out

    # ── sorgulama ───────────────────────────────────────────────────────
    def bul(self, arama='', azami_fiyat=0, efsun='', en_az_deger=0):
        """Toplanan dükkânlarda ara. Döner: [(fiyat, ad, esya_adi, adet, vid)]"""
        ar = ad_fold(arama)
        ef = ad_fold(efsun)
        out = []
        for (kanal, vid), d in self.dukkanlar.items():
            for e in d['esyalar']:
                ead = self.adlar.ad(e['vnum'])
                if ar and ar not in ad_fold(ead):
                    continue
                if azami_fiyat and e['fiyat'] > azami_fiyat:
                    continue
                efs = e.get('efsunlar') or []
                if ef:
                    uyan = [x for x in efs
                            if ef in ad_fold(x.get('ad', ''))
                            and x.get('deger', 0) >= en_az_deger]
                    if not uyan:
                        continue
                out.append((e['fiyat'], d['ad'], ead, e['adet'],
                            d.get('kanal', kanal), vid, efs))
        # ANAHTARLA sırala: fiyat ve eşya aynı olduğunda demetin sonundaki
        # efsun SÖZLÜKLERİ karşılaştırılmaya çalışılıyor ve TypeError veriyordu.
        out.sort(key=lambda r: (r[0], r[2], r[1], r[5]))
        return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pazar tarayıcı (yalnız bildirim)')
    ap.add_argument('--ara', default='', help='eşya adı parçası')
    ap.add_argument('--azami', type=int, default=0, help='en yüksek fiyat')
    ap.add_argument('--liste', action='store_true',
                    help='sadece dükkânları say, açma')
    ap.add_argument('--tani', action='store_true',
                    help='TEK dükkâna tıkla, log\'da ne göründüğünü dök')
    ap.add_argument('--en-fazla', type=int, default=0,
                    help='en fazla kaç dükkân taransın (0=hepsi)')
    a = ap.parse_args(argv)

    t = PazarTarayici(gunluk=print)
    print('eşya adı tablosu: %s (%d eşya)'
          % (t.adlar.yol or 'BULUNAMADI', len(t.adlar.tablo)))
    if a.tani:
        t.tani()
        return
    if a.liste:
        bx, by, _t, _d = t._konumum()
        liste = t.dukkanlari_bul(bx, by)
        print('%d oyuncu dükkânı görünüyor (yakından uzağa):' % len(liste))
        for vid, ad, hx, hy, m in liste[:80]:
            print('   %6.1f m  vid=%-10d %s' % ((m or 0) / 100.0, vid, ad))
        return
    t.tara(en_fazla=a.en_fazla)
    sonuc = t.bul(a.ara, a.azami)
    print('\n' + '=' * 70)
    print('SONUÇ: %d eşleşme%s' % (len(sonuc),
                                   (" — '%s'" % a.ara) if a.ara else ''))
    print('=' * 70)
    for fiyat, dad, ead, adet, kanal, vid, efs in sonuc[:120]:
        print('%14s  %-34s %3d ad.  ch%-2s %s'
              % (pp._yang(fiyat), ead[:34], adet, kanal or '?', dad))
        if efs:
            print('%16s%s' % ('', ', '.join('%s %+d' % (x['ad'], x['deger'])
                                            for x in efs)))


if __name__ == '__main__':
    main()
