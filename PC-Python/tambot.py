# -*- coding: utf-8 -*-
"""
Tam Bot — Romia2 masaüstü otomasyonu
====================================

BAĞIMSIZ dosyadır. r2_masaustu.py'yi ne içe aktarır ne de değiştirir; ikisi
aynı anda çalışabilir. APK'daki ApiSunucu'ya (:30200) HTTP ile bağlanır.

    python tambot.py

Ne yapar
--------
  • Yakındaki canavar/metin taşlarını hedefler ve saldırır
  • Yere düşen eşyaları ve Yang'ı otomatik toplar
  • Rota üzerinde devriye gezer, hedef bitince sıradaki noktaya gider
  • Wait-hack (ışınlan-vur-dön) — isteğe bağlı
  • Sıkışma tespiti ve kurtarma

Paket ofsetleri
---------------
Hepsi 29 Ağu 2026 canlı yakalamasıyla doğrulanmıştır
(bkz. docs/PROTOKOL_OFSET.md):

    0x07  16 bayt  CG_MOVE      07 | bFunc | bArg | bRot | x | y | tik
    0x02   6 bayt  CG_ATTACK    02 | bType | vid
    0x3D   5 bayt  CG_TARGET    3D | vid
    0x0F   5 bayt  CG_PICKUP    0F | vid        <-- eskiden 0x0D sanılıyordu
    0x34   9 bayt  CG_USE_SKILL 34 | vnum | vid

GÜVENLİK — üç kapı
------------------
Hiçbir paket kazara gitmez. Gerçekten göndermek için APK tarafında üçü de
açık olmalı:
    1. Proxy servisi açık ve oyun bağlantısı proxy'den geçiyor
    2. Enjeksiyon açık   (/api/enjeksiyon?ac=1)
    3. Kuyruk kanalı proxy (/api/kanal?ad=proxy)

Bot varsayılan olarak KURU ÇALIŞIR: ne yapacağını loglar, paket göndermez.
Göndermeye başlamak için arayüzdeki "Kuru çalışma" kutusunu kapatman gerekir;
o sırada üç kapı kapalıysa bot seni uyarır ve yine göndermez.
"""

import http.client
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.parse

# tools/ dizinini içe aktarma yoluna ekle: OCR köprüsü orada duruyor.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tools"))
from tkinter import messagebox, scrolledtext, ttk

# ─── Görünüm (r2_masaustu.py ile aynı palet) ───────────────────────────
KOYU  = "#0e0f13"
PANEL = "#171922"
CIZGI = "#262a36"
METIN = "#e6e8ef"
SOLUK = "#9aa0b4"
VURGU = "#33aaff"
UYARI = "#ffd166"
HATA  = "#e05050"
OK    = "#00c878"
ALTIN = "#ffcc33"

VARSAYILAN_ADRES = "127.0.0.1:30200"


def _adb_bul():
    """adb.exe'yi bul: ADB_YOLU, Android SDK, yaygın konumlar, sonra PATH."""
    for a in (os.environ.get("ADB_YOLU"),
              os.path.expanduser(
                  r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
              r"C:\Program Files\platform-tools\adb.exe",
              r"C:\platform-tools\adb.exe"):
        if a and os.path.exists(a):
            return a
    return "adb"                                          # PATH'te olabilir


ADB = _adb_bul()

# EXE (PyInstaller) olarak paketlenince ayar/rota dosyaları EXE'nin yanında
# (kalıcı) durmalı — kod _MEIPASS'tan (geçici) çalışsa bile.
if getattr(sys, "frozen", False):
    _VERI_KOK = os.path.dirname(sys.executable)
else:
    _VERI_KOK = os.path.dirname(os.path.abspath(__file__))

# Ayarlar bu dosyada saklanır (EXE/py'nin yanında).
AYAR_DOSYASI = os.path.join(_VERI_KOK, "tambot_ayar.json")
# Adlandırılmış rotalar AYRI dosyada durur.
#
# Neden ayarlardan ayrı: "Ayarları sıfırla" rotaların hepsini de silerdi.
# Bir rotayı gezerek kaydetmek dakikalar sürüyor; bir onay kutusunu geri
# almakla aynı kefeye konmamalı. Ayrıca ayrı dosya paylaşmayı kolaylaştırır
# — kitaplık dosyasını olduğu gibi başkasına verebilirsin.
ROTA_DOSYASI = os.path.join(_VERI_KOK, "tambot_rotalar.json")
# Diske YAZILMAYAN alanlar. Token bir kimlik bilgisidir; düz metin olarak
# saklamak yerine her açılışta yeniden girilir.
# Diske YAZILMAYAN ayarlar.
#
# token_var      : gizli bilgi, dosyada durmasın.
# kendi_vid_elle_var : vid HER OYUN GİRİŞİNDE DEĞİŞİYOR (kayıtlarda
#   9525679 / 5090706 / 10925029 / 2528459 gibi). Diske yazılsaydı bir
#   sonraki oturumda eski, artık başka bir varlığa ait olabilecek bir
#   vid'e hizalama paketi gönderirdik — istemci yanlış varlığı taşırdı.
#   Bu yüzden elle/butonla bulunan vid yalnızca o oturum için geçerlidir.
KAYDEDILMEZ = {"token_var", "kendi_vid_elle_var"}

# Varlik.java CHAR_TYPE sabitleri
TIP_MOB, TIP_NPC, TIP_METIN, TIP_OYUNCU = 0, 1, 2, 6


def bildirim_sesi():
    """
    Metin bulununca kısa bildirim sesi: iki kez "di-dıt".

    Arka planda çalar, çağıranı bekletmez. Windows dışında ya da ses
    aygıtı yoksa sessizce geçer. TAMBOT_SESSIZ ortam değişkeni varsa
    çalmaz (testler çalışırken bilgisayar ötmesin).

    Döner: True = çalmaya başladı.
    """
    if os.environ.get("TAMBOT_SESSIZ"):
        return False

    def cal():
        try:
            import winsound
            for _ in range(2):
                winsound.Beep(1000, 140)
                winsound.Beep(1500, 220)
                time.sleep(0.08)
        except Exception:                              # noqa: BLE001
            try:
                import winsound
                winsound.MessageBeep()
            except Exception:                          # noqa: BLE001
                pass

    threading.Thread(target=cal, daemon=True).start()
    return True


def port_kanali(port):
    """
    Oyun sunucusu portundan kanal numarası; kanal portu değilse 0.

    12 Eyl 2026'da doğrulandı: oyun ekranında "KAOS, CH-4" yazarken
    bağlantı portu 30019'du. Aynı gün proxy kaydında görülen portlar
    (30007, 30011 ... 30027) bu düzene birebir oturuyor:

        kanal = (port - 30003) / 4        ch1 = 30007 ... ch8 = 30035

    30003 giriş sunucusu, 30025 karakter seçimi — kanal değiller.
    Eski düzen (30000 + 4 x kanal) artık geçerli değil; APK'nın verdiği
    kanal numarası o yüzden hep 0 geliyor.
    """
    try:
        port = int(port)
    except (TypeError, ValueError):
        return 0
    fark = port - 30003
    if fark <= 0 or fark % 4:
        return 0
    kanal = fark // 4
    return kanal if 1 <= kanal <= 20 else 0


class MetinSureTutucu:
    """
    METİN SÜRE TUTUCU — kanal bazlı metin yeniden doğma sayacı.

    Bir kanalda metin kırılınca o kanal için geri sayım başlar
    (varsayılan 15 dk). Her kanalın sayacı ayrıdır.

    KIRILMA NASIL ANLAŞILIYOR
    -------------------------
    APK ölüm paketini (0x46) yalnızca çerçeveliyor, bir yere yazmıyor.
    Ama metinler HAREKET ETMEZ ve APK duran nesneleri 6 saat listede
    tutar. Yani yakınındayken (25 m) bir yoklamadan diğerine (0,6 sn)
    listeden düşen metin görüş alanından çıkmış olamaz — kırılmıştır.

    Yanlış alarm olmasın diye şu durumlarda sayaç BAŞLAMAZ:
      - port değişti (kanal değişimi: liste baştan kuruluyor)
      - konum 30 m'den fazla sıçradı (ışınlanma / harita değişimi)
      - varlık listesi bütünüyle boşaldı
      - konum bilinmiyor

    TEKRAR
    ------
    `tekrar` açıksa süre dolunca sayaç durmaz, aynı kanalda yeniden
    başlar (yeni turun süresi `tekrar_dk`). Bir kez başlatmak yeter.
    Sayaç hiç eksiye düşmediği için "HAZIR" ayrıca tutulur: süre en
    son dolduğundan beri o kanalda bulunulmadıysa kanal hazırdır
    (`hazir_mi`). O kanalda bulununca (`goruldu`) hazır söner.
    """

    YAKIN = 2500        # ham — bu mesafede kaybolan metin görüş dışına çıkmış olamaz
    SICRAMA = 3000      # ham — yoklamalar arası bundan fazla konum farkı = ışınlanma

    def __init__(self):
        self._kilit = threading.Lock()
        self.bitisler = {}          # kanal -> bitiş anı (epoch sn)
        self.tekrar = False         # süre dolunca yeniden başlat
        self.tekrar_dk = None       # yeni turun süresi; None -> başlatılırkenki
        self.sureler = {}           # kanal -> tur süresi (sn)
        self.doguslar = {}          # kanal -> süre en son dolduğu an
        self.gorulmeler = {}        # kanal -> o kanalda en son bulunulan an
        self._onceki = {}           # vid -> (x, y, ad)
        self._onceki_port = 0
        self._onceki_konum = None

    def guncelle(self, durum, varliklar, sure_dk, simdi=None):
        """Yeni yoklama verisini işler. Döner: [(kanal, metin adı), ...]."""
        simdi = time.time() if simdi is None else simdi
        durum = durum if isinstance(durum, dict) else {}
        p = durum.get("proxy") or {}
        k = durum.get("konum") or {}
        try:
            port = int(p.get("port", 0) or 0)
        except (TypeError, ValueError):
            port = 0
        konum = None
        if k.get("bilinir"):
            try:
                konum = (int(k.get("x", 0)), int(k.get("y", 0)))
            except (TypeError, ValueError):
                konum = None

        varliklar = varliklar if isinstance(varliklar, list) else []
        metinler = {}
        for v in varliklar:
            if v.get("tip") == TIP_METIN and v.get("vnum", 0) > 0 and v.get("vid"):
                metinler[v["vid"]] = (int(v.get("x", 0)), int(v.get("y", 0)),
                                      v.get("ad") or "metin")

        olaylar = []
        guvenilir = (konum is not None and port and port == self._onceki_port
                     and self._onceki_konum is not None and varliklar
                     and mesafe_ham(konum[0], konum[1], self._onceki_konum[0],
                                    self._onceki_konum[1]) <= self.SICRAMA)
        if guvenilir:
            for vid, (mx, my, ad) in self._onceki.items():
                if vid in metinler:
                    continue
                if mesafe_ham(konum[0], konum[1], mx, my) <= self.YAKIN:
                    kanal = port_kanali(port)
                    self.baslat(kanal, sure_dk, simdi)
                    olaylar.append((kanal, ad))

        self._onceki = metinler
        self._onceki_port = port
        self._onceki_konum = konum
        return olaylar

    def baslat(self, kanal, sure_dk, simdi=None):
        """Sayacı başlatır; çalışıyorsa tur baştan başlar."""
        simdi = time.time() if simdi is None else simdi
        sure = max(0.1, float(sure_dk)) * 60.0
        k = int(kanal)
        with self._kilit:
            self.bitisler[k] = simdi + sure
            self.sureler[k] = sure
            self.doguslar.pop(k, None)
            self.gorulmeler[k] = simdi

    def sifirla(self, kanal=None):
        with self._kilit:
            for sozluk in (self.bitisler, self.sureler,
                           self.doguslar, self.gorulmeler):
                if kanal is None:
                    sozluk.clear()
                else:
                    sozluk.pop(int(kanal), None)

    def izlemeyi_sifirla(self):
        """
        Önceki yoklamayı unut.

        Otomatik tespit kapalıyken metinler izlenmiyor. Açıldığında eski
        listeyle karşılaştırılırsa arada kaybolan metin "kırıldı" sanılır;
        o yüzden ilk yoklama sıfırdan başlar.
        """
        self._onceki = {}
        self._onceki_port = 0
        self._onceki_konum = None

    def _ilerlet(self, k, simdi):
        """(Kilit içinde) TEKRAR açıksa dolmuş sayacı sonraki tura taşır."""
        b = self.bitisler.get(k)
        if b is None or not self.tekrar or simdi < b:
            return
        if self.tekrar_dk:
            sure = float(self.tekrar_dk) * 60.0
        else:
            sure = self.sureler.get(k) or 900.0
        sure = max(6.0, sure)
        # Uygulama kapalıyken birden fazla tur geçmiş olabilir.
        tur = int((simdi - b) // sure)
        son = b + tur * sure
        self.doguslar[k] = son
        self.bitisler[k] = son + sure
        self.sureler[k] = sure

    def kalan(self, kanal, simdi=None):
        """Kalan saniye; sayaç yoksa None, süresi dolduysa <= 0 (TEKRAR kapalı)."""
        simdi = time.time() if simdi is None else simdi
        k = int(kanal)
        with self._kilit:
            self._ilerlet(k, simdi)
            b = self.bitisler.get(k)
        return None if b is None else b - simdi

    def goruldu(self, kanal, simdi=None):
        """O kanaldayız: dolmuş süre artık "gidilmedi" sayılmaz."""
        simdi = time.time() if simdi is None else simdi
        k = int(kanal)
        with self._kilit:
            self._ilerlet(k, simdi)
            self.gorulmeler[k] = simdi

    def hazir_mi(self, kanal, simdi=None):
        """
        O kanalda metin çıkmış olmalı mı?

        TEKRAR kapalı: süre dolduysa. TEKRAR açık: süre en son dolduğundan
        beri o kanalda bulunulmadıysa.
        """
        simdi = time.time() if simdi is None else simdi
        k = int(kanal)
        with self._kilit:
            self._ilerlet(k, simdi)
            b = self.bitisler.get(k)
            if b is None:
                return False
            if b - simdi <= 0:
                return True
            d = self.doguslar.get(k)
            return d is not None and d > self.gorulmeler.get(k, 0.0)

    def disari(self):
        with self._kilit:
            veri = {str(k): v for k, v in self.bitisler.items()}
            veri["_sure"] = {str(k): v for k, v in self.sureler.items()}
            veri["_dogus"] = {str(k): v for k, v in self.doguslar.items()}
            veri["_gorulme"] = {str(k): v for k, v in self.gorulmeler.items()}
            return veri

    def iceri(self, veri):
        """Kayıttan yükler (eski biçim — yalnızca bitişler — da okunur)."""
        veri = veri if isinstance(veri, dict) else {}

        def sayilar(kaynak):
            cikti = {}
            for k, v in (kaynak.items() if isinstance(kaynak, dict) else ()):
                if str(k).startswith("_"):
                    continue
                try:
                    cikti[int(k)] = float(v)
                except (TypeError, ValueError):
                    continue
            return cikti

        with self._kilit:
            self.bitisler = sayilar(veri)
            self.sureler = sayilar(veri.get("_sure"))
            self.doguslar = sayilar(veri.get("_dogus"))
            self.gorulmeler = sayilar(veri.get("_gorulme"))

# Eşya vnum'ları
VNUM_YANG = 1


# ═══════════════════════════════════════════════════════════════════════
#  Paket kurucular — ofsetler canlı yakalamayla doğrulandı
# ═══════════════════════════════════════════════════════════════════════

def _u32(v):
    return list((int(v) & 0xFFFFFFFF).to_bytes(4, "little"))


def paket_hareket(x, y, tik, bfunc=1, brot=0):
    """
    CG_MOVE (16 bayt). bfunc: 0=dur(WAIT), 1=yürü(MOVE), 3=saldırı.
    brot: yön baytı, derece = (90 - brot*5) mod 360.
    """
    return bytes([0x07, bfunc & 0xFF, 0x00, brot & 0xFF]
                 + _u32(x) + _u32(y) + _u32(tik))


def paket_hedef(vid):
    """CG_TARGET (5 bayt). vid=0 → hedefi temizler."""
    return bytes([0x3D] + _u32(vid))


def paket_saldiri(vid, btype=0):
    """CG_ATTACK (6 bayt): 02 | bType | vid."""
    return bytes([0x02, btype & 0xFF] + _u32(vid))


# Toplama: aynı vid'e bu kadar sn içinde tekrar paket gönderme (kalıcı kara
# liste değil — toplanmayan eşya yaklaşınca yeniden denensin diye kısa).
TOPLA_BEKLEME = 1.5
# Tek turda gönderilecek en çok toplama paketi (menzildeki hepsi birden).
TOPLA_AZAMI = 40


def paket_topla(vid):
    """
    CG_ITEM_PICKUP (5 bayt): 0F | vid.

    Opcode 29 Ağu 2026'da doğrulandı. Protokol belgesindeki eski 0x0D
    tahmini YANLIŞTI — o yüzden eski botlarda toplama hiç çalışmıyordu.
    Giden akışta 0x0F taşıyan 22 konumun hepsinde vid, gelen 0x1A
    paketlerinden bilinen gerçek bir yer-eşyası kimliğiydi.
    """
    return bytes([0x0F] + _u32(vid))


def paket_toplu_konum(ogeler):
    """
    CG_SYNC_POSITION: 08 | u16 wSize | [vid(4) | x(4) | y(4)] x N

    wSize = 3 + 12*N. Gelen 0x05'in giden aynasıdır.

    <b>Saldırıda ŞART:</b> gerçek istemci saldırırken bunu CG_ATTACK'in
    hemen ardına ekleyip TEK segment olarak gönderiyor — 29 Ağu 2026
    yakalamasında 1648 saldırı segmentinin hepsi 21 bayttı:
        02 00 <vid>            CG_ATTACK      (6)
        08 0F 00 <vid><x><y>   CG_SYNC_POS    (15)
    Yalnızca 0x02 gönderildiğinde sunucu vuruşu saymıyordu.
    """
    govde = b""
    for vid, x, y in ogeler:
        govde += bytes(_u32(vid) + _u32(x) + _u32(y))
    boy = 3 + len(govde)
    return bytes([0x08, boy & 0xFF, (boy >> 8) & 0xFF]) + govde


def paket_yetenek(vnum, vid=0):
    """CG_USE_SKILL (9 bayt): 34 | vnum(u32) | vid(u32)."""
    return bytes([0x34] + _u32(vnum) + _u32(vid))


def paket_istemci_hizala(vid, x, y):
    """
    GC_SYNC_POSITION (15 bayt): 05 | u16 boy=15 | vid | x | y

    <b>İSTEMCİYE gönderilir</b> (sunucuya değil). İstemcinin karakterini
    verilen konuma taşır.

    29 Ağu 2026'da canlı denemeyle bulundu. Üç aday sırayla denendi:
      0x01 CHARACTER_ADD (kendi vid) -> istemci kımıldamadı
      0x03 MOVE          (kendi vid) -> kımıldamadı
      0x05 SYNC_POSITION (kendi vid) -> KARAKTER TAŞINDI

    Neden kritik: sunucu kendi hareketimizi bize geri yollamıyor (859 gelen
    0x03'ün sıfırı bizim vid'imizi taşıyor). Bot sunucuda ilerlediğinde
    istemci eski konumda kalıyor ve ilk fırsatta kendi konumunu bildirip
    bizi geri çekiyordu. Bu paketle istemci de aynı yere getirilir.

    Yalnızca GÖRÜNTÜYÜ hizalar; sunucudaki gerçeği değiştirmez.
    """
    govde = _u32(vid) + _u32(x) + _u32(y)
    boy = 3 + len(govde)
    return bytes([0x05, boy & 0xFF, (boy >> 8) & 0xFF] + govde)


# İstemcinin yürüme animasyonunu çizerken kullandığı hız sabiti.
# 23 Ağu 2026 kaydındaki 163 gerçek GC_MOVE paketinden ölçüldü
# (tools/hareket_paketi_incele.py): mesafe/süre oranı hep 0.43 ham/ms.
#   401 ham /  942 ms = 0.43
#  1250 ham / 2937 ms = 0.43
ISTEMCI_HAM_MS = 0.43


def paket_istemci_hareket(vid, x, y, tik, sure_ms, brot=0):
    """
    GC_MOVE (24 bayt) — İSTEMCİYE gönderilir, karakteri ANİMASYONLA yürütür.

        +0  u8   header = 0x03
        +1  u8   bFunc      0 = hedefe yürü  (kayıtta 155/176 böyle)
        +2  u8   bArg       kayıtta HEP 0
        +3  u8   bRot       yön (derece/5, 0-71)
        +4  u32  dwVID
        +8  i32  lX
        +12 i32  lY
        +16 u32  dwTime     sunucu tiki
        +20 u32  dwDuration hareket KAÇ MS sürecek   <-- animasyonun anahtarı

    NEDEN BU PAKET
    --------------
    0x05 SYNC_POSITION bir konum DÜZELTMESİ: istemci karakteri oraya
    oturtur, hareket durum makinesini hiç çalıştırmaz. Arka arkaya küçük
    adımlarla gönderince karakter koşmadan SÜRÜKLENİYOR — sahada görülen
    buydu.

    Başka oyuncular ekranda düzgün koşuyor; onları çizdiren paket bu.
    23 Ağu 2026 kaydından alanları ölçüldü (bkz. ISTEMCI_HAM_MS).

    ÖNCEKİ DENEMEDE NEDEN ÇALIŞMADI
    -------------------------------
    tools/istemci_hizala.py bu paketi denemiş ve "kımıldamadı" demişti —
    ama dwTime ve dwDuration alanlarını SIFIR gönderiyordu. Süresi sıfır
    olan bir hareketin gidecek zamanı yok. Kayıttaki 163 gerçek paketin
    hepsinde süre > 0.
    """
    sure = max(1, int(sure_ms))
    return bytes([0x03, 0, 0, brot & 0xFF]
                 + _u32(vid) + _u32(x) + _u32(y)
                 + _u32(tik) + _u32(sure))


def paket_tikla(vid):
    """CG_ON_CLICK (5 bayt): 1A | dwVID. Tek başına — genelde YETMEZ."""
    return bytes([0x1A] + _u32(vid))


def paket_tikla_tam(vid, bx, by, tik, brot=0):
    """
    NPC tıklaması — gerçek istemcinin gönderdiği TAM segment (21 bayt).

    29 Ağu 2026 yakalamasında istemci tıklamayı ASLA tek başına göndermiyor;
    hep CG_MOVE(bFunc=0 = DUR) ile aynı segmentte yolluyor — yani "durdum ve
    ona döndüm" diyor:

        1A A4310000 | 07 00 00 24 <x> <y> <tik>     = 5 + 16 = 21 bayt

    Yalnızca 0x1A gönderildiğinde sunucu dükkânı AÇMIYORDU (canlı denendi).
    Buradaki x,y OYUNCUNUN kendi konumudur (hedefin değil), çünkü bFunc=0
    "buradayım ve durdum" demektir.
    """
    return (bytes([0x1A] + _u32(vid))
            + paket_hareket(bx, by, tik, bfunc=0, brot=brot))


# CG_SHOP alt başlıkları (standart Metin2 enum'u; canlı yakalamayla uyuştu)
SHOP_KAPAT = 0x00       # 32 00              — dükkânı kapat
SHOP_SATIN_AL = 0x01
SHOP_SAT = 0x02
SHOP_SAT2 = 0x03        # 32 03 slot adet    — kullanılan bu


def paket_dukkan_kapat():
    """CG_SHOP END (2 bayt): 32 00."""
    return bytes([0x32, SHOP_KAPAT])


def paket_sat(slot, adet=1):
    """
    CG_SHOP SELL2 (4 bayt): 32 | 03 | u8 slot | u8 adet.

    29 Ağu 2026 doğrulaması — 5 eşya satıldı, giden akışta tam 5 kez:
        32 03 19 01   slot 25
        32 03 1A 01   slot 26
        32 03 2D 01   slot 45
        32 03 2E 01   slot 46
        32 03 33 01   slot 51
    Değişen tek alan +2 (slot); +3 hep 01 (adet).
    """
    return bytes([0x32, SHOP_SAT2, slot & 0xFF, max(1, adet) & 0xFF])


def mesafe_ham(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def yon_bayti(dx, dy):
    """
    Hedefe bakan yön baytı (bRot): derece/5, 0-71.

    KAYITTAN DOĞRULANDI — tools/yon_bayti_dogrula.py, 5 kayıtta toplam
    938 gerçek yürüme çifti. Yöntem: ardışık 0x07 paketlerinin konum
    farkından yön hesaplanıp pakette yazan bRot ile karşılaştırıldı.

        atan2(dx,  dy)   ortalama sapma  1.4 birim   ±1 içinde %84   <- BU
        atan2(-dx, dy)   ortalama sapma 15.0 birim   ±1 içinde  %6
        atan2(dy,  dx)   ortalama sapma 19.5 birim   ±1 içinde  %2
        eski formül      ortalama sapma 21.0 birim   ±1 içinde  %1

    ESKİ FORMÜL NEDEN KARAKTERİ DÖNDÜRÜYORDU
    ----------------------------------------
    Eskisi `(90 - atan2(-dy, dx))` idi. θ = atan2(dy, dx) dersek:
        doğru : 90 - θ
        eski  : 90 + θ
    Yani hata sabit bir kayma değil, **2θ** — yönle birlikte değişen bir
    AYNA yansıması. Rota üzerinde yön değiştikçe bakış açısı iki katı
    savruluyordu; bot akan paket göndermeye başlayınca bu, dışarıdan
    "kendi etrafında dönüyor" olarak göründü. Tek paket yollanırken göze
    batmıyordu çünkü karakter zaten çoğu zaman duruyordu.
    """
    if dx == 0 and dy == 0:
        return 0
    return int(round((math.degrees(math.atan2(dx, dy)) % 360) / 5)) % 72


# ═══════════════════════════════════════════════════════════════════════
#  API istemcisi — kalıcı bağlantı (iş parçacığı başına)
# ═══════════════════════════════════════════════════════════════════════

class Api:
    def __init__(self):
        self.adres = VARSAYILAN_ADRES
        self.token = ""
        self.zaman_asimi = 1.5
        self.son_hata = ""
        self._yerel = threading.local()

    def _baglanti(self):
        conn = getattr(self._yerel, "conn", None)
        if conn is None or getattr(self._yerel, "host", None) != self.adres:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            self._yerel.host = self.adres
            self._yerel.conn = http.client.HTTPConnection(
                self.adres, timeout=self.zaman_asimi)
        return self._yerel.conn

    def _sifirla(self):
        conn = getattr(self._yerel, "conn", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        self._yerel.conn = None

    def _sorgu(self, params):
        p = {k: v for k, v in (params or {}).items() if v is not None}
        if self.token:
            p["t"] = self.token
        return ("?" + urllib.parse.urlencode(p)) if p else ""

    def get(self, yol, **params):
        for deneme in range(2):
            try:
                conn = self._baglanti()
                bas = {"Connection": "keep-alive"}
                if self.token:
                    bas["X-R2-Token"] = self.token
                conn.request("GET", yol + self._sorgu(params), headers=bas)
                r = conn.getresponse()
                ham = r.read().decode("utf-8", "replace")
                self.son_hata = ""
                return json.loads(ham)
            except Exception as e:                       # noqa: BLE001
                self._sifirla()
                if deneme == 1:
                    self.son_hata = type(e).__name__
        return None

    def post(self, yol, govde, **params):
        for deneme in range(2):
            try:
                conn = self._baglanti()
                bas = {"Connection": "keep-alive",
                       "Content-Type": "text/plain; charset=utf-8"}
                if self.token:
                    bas["X-R2-Token"] = self.token
                conn.request("POST", yol + self._sorgu(params),
                             body=govde.encode("utf-8"), headers=bas)
                r = conn.getresponse()
                ham = r.read().decode("utf-8", "replace")
                self.son_hata = ""
                return json.loads(ham)
            except Exception as e:                       # noqa: BLE001
                self._sifirla()
                if deneme == 1:
                    self.son_hata = type(e).__name__
        return None

    def enjekte(self, paket):
        """Ham baytları SUNUCUYA gönderir. Üç kapı kapalıysa APK reddeder."""
        return self.post("/api/enjekte",
                         " ".join("%02X" % b for b in paket))

    def dokun(self, x, y):
        """Ekrana dokun — kanal menüsüne basmak için."""
        return self._dokun_cevap(self.get("/api/dokun", x=int(x), y=int(y)))

    def dokunma_ac(self, acik=True):
        return self._dokun_cevap(
            self.get("/api/dokun", ac=1 if acik else 0))

    @staticmethod
    def _dokun_cevap(c):
        """
        Dokunma yanıtını DOĞRULAR — "ok" tek başına yetmiyor.

        APK bilinmeyen bir yolu görünce durum JSON'unu döndürüyor
        (ApiSunucu: default -> durumJson()). O JSON'un başında da
        {"ok":true,...} var. Eski APK'da /api/dokun yolu hiç yokken bot
        bu yanıta bakıp "dokunma tamamlandı" diyordu — ekranda hiçbir şey
        olmamasına rağmen. Sahada tam bu yaşandı.

        Gerçek dokunma yanıtında "acik" alanı bulunur; durum JSON'unda
        bulunmaz. Ayrım bundan yapılıyor.
        """
        if not isinstance(c, dict):
            return {"ok": False, "hata": "yanıt yok"}
        if "acik" in c:
            return c
        # APK GERÇEK BİR HATA döndürmüş olabilir — onu "eski sürüm" diye
        # yorumlamak yanlış teşhize yol açtı. Örnek: dokunma kapalıyken
        # APK {"ok":false,"hata":"dokunma kapalı"} dönüyor; bot bunu
        # "APK bu isteği tanımıyor" sanıp saatlerce yanlış yere baktırdı.
        if c.get("hata"):
            return {"ok": False, "hata": str(c["hata"])}
        # Ne "acik" ne "hata" var: bilinmeyen yol durum JSON'una düşmüş
        # demektir (ApiSunucu: default -> durumJson), yani uç yok.
        return {"ok": False,
                "hata": "APK bu isteği tanımıyor — ESKİ SÜRÜM. "
                        "Yeni APK'yı kur: adb install -r "
                        "app/build/outputs/apk/debug/app-debug.apk"}

    def enjekte_istemci(self, paket):
        """Ham baytları İSTEMCİYE yazar (sunucudan geliyormuş gibi)."""
        return self.post("/api/enjekte_istemci",
                         " ".join("%02X" % b for b in paket))


# ═══════════════════════════════════════════════════════════════════════
#  Ayarlar
# ═══════════════════════════════════════════════════════════════════════

class Ayar:
    """Arayüzden okunan tüm bot ayarları tek yerde."""

    def __init__(self):
        self.kuru          = True     # paket GÖNDERME, sadece logla
        # Modül ana anahtarları — kapalıysa o modülün bütün ayarları
        # kapalı gibi davranır (bkz. _ayarlari_al).
        self.modul_hedefleme = True
        self.modul_rota = True
        # BASİT HEDEFLEME: menzildeki en yakın N hedefe vur, başka
        # koşul arama. Masaüstü tambot.py'deki davranış.
        self.basit_hedefleme = True
        self.hedef_mob     = True
        self.hedef_metin   = False
        self.menzil        = 2500     # ham birim (25 m) — saldırı menzili
        self.tarama        = 6000     # ham birim (60 m) — hedef arama
        # İki saldırı arası. 300 ms (saniyede 3.3 vuruş) GERÇEKÇİ DEĞİL:
        # Metin2'de saldırı hızı sunucuda denetlenir, normal hız ~1/sn.
        # 29 Ağu ölçümünde bot 300 ms ile vururken hedeflerin canı %100'de
        # kaldı — sunucu vuruşları saymıyordu.
        self.vurus_ms      = 50
        # Tek turda kaç vuruş gönderilecek (aralarında vurus_ms bekleme).
        #
        # Tur başına tek vuruş, hızı ana döngüye bağlıyordu: her turda
        # iki HTTP gidiş-dönüşü var, o yüzden vurus_ms 50 olsa bile
        # gerçek aralık çok daha büyük kalıyordu. Seri bu bağı koparır.
        self.vurus_seri = 4
        # ÇOKLU HEDEF: her turda en yakın N canavara sırayla vur.
        # Eski BotPanel mantığı; tek hedefe kilitlenmekten daha etkili.
        self.coklu_hedef   = True
        self.max_hedef     = 10
        # PvP: saldırılabilir OYUNCULARA da vur. Canavar hızından (vurus_ms)
        # AYRI, ms cinsinden aralık — istediğin gibi ayarla (ör. 500 ms).
        self.oyuncu_vur      = False
        self.oyuncu_vurus_ms = 500
        # Oyuncuya özel saldırı menzili (ham). Canavardan AYRI: oyunun gerçek
        # vuruş menzili kısa (~3 m) olduğu için varsayılan 300 = 3 m; böylece
        # yalnız gerçekten yanına gelen oyuncuya vurur, boşa paket gitmez.
        self.oyuncu_menzil   = 300
        self.topla_acik    = True
        self.topla_menzil  = 1500     # 15 m
        self.sadece_benim  = True     # yalnızca sahibi ben/boş olanı topla
        self.oyuncu_adi    = ""       # sahip filtresi için
        self.yang_oncelik  = True
        # Eşya filtresi: virgülle ayrılmış vnum ya da isim parçası.
        #   "1, 27002, iksir"  →  Yang, o vnum ve adında "iksir" geçen her şey
        self.filtre_mod    = "hepsi"  # hepsi | beyaz | kara
        self.filtre_metin  = ""
        self.yetenek_acik  = False
        self.yetenek_vnum  = 1
        self.yetenek_ms    = 4000
        # WAIT-HACK: bu sunucuda ÇALIŞMIYOR.
        #
        # 29 Ağu 2026 ölçümü: sunucu hareket paketini KABUL EDİYOR ama
        # ışınlamıyor — yürüterek götürüyor (50 m~4 sn, 80 m~6 sn,
        # 120 m~9 sn ≈ 13 m/s). Reddettiği şey mesafe değil, bfunc=0 ile
        # yapılan "anında vardım" iddiası. Wait-hack tam da onu yaptığı
        # için hedefe varmadan saldırıyor ve vuruş menzil dışında kalıyor.
        #
        # Buna karşılık SALDIRI çalışıyor: 3 m'deki hedefe tek dizi
        # gönderildiğinde can %100 → %62 düştü. Yani bot GERÇEKTEN yakın
        # hedefleri döverek çalışır; ışınlanarak değil.
        self.wait_hack     = False
        self.wh_menzil     = 6000
        # Wait-hack'i istemcinin sessiz anına denk getir (bkz. Motor._pencere_bekle)
        self.wh_pencere    = True
        self.wh_donus      = False    # vurduktan sonra eski konuma dön mü
        self.wh_bekleme_ms = 400      # pencere için en fazla bu kadar bekle
        # Hedef kilidi: seçilen hedefi ölene kadar bırakma. Kapalıyken bot her
        # turda "en yakın"ı yeniden seçer; ışınlandıktan sonra en yakın
        # değiştiği için hedeften hedefe atlayıp haritada sürükleniyordu.
        self.hedef_kilit   = True
        # 0 = SINIRSIZ, hedef ölene kadar dövüş.
        #
        # Ölüm zaten yakalanıyor: can 0 olunca ya da varlık listeden
        # düşünce (0x46 ölüm / 0x02 silme) kilit kendiliğinden açılır.
        # Süre sınırı yalnızca geç kırılan metin taşlarını yarıda
        # bıraktırıyordu. Sıfırdan büyük bir değer, takılıp kalmaya karşı
        # istenirse kullanılabilir.
        self.kilit_sure    = 0
        # Ev noktası: HEDEF SEÇİMİNİ sınırlar — bot başladığı noktadan bu
        # kadar uzaktaki canavarları hedeflemez. (Eve geri yürüme davranışı
        # kaldırıldı; bot kendiliğinden yer değiştirmez.)
        # 0 = sınırsız.
        self.ev_yaricap    = 8000     # ham birim (80 m)
        self.devriye       = False    # hedef yoksa rotada ilerle
        # Yerel rota: [[hamX, hamY], ...]. APK'daki rotadan bağımsız,
        # tambot_ayar.json içinde saklanır.
        self.rota          = []
        self.rota_gez      = False    # hedef yokken rotada ilerle
        self.rota_yaricap  = 500      # ham — bu kadar yaklaşınca nokta geçildi
        # Rota sonuna varinca ne olacak?
        #   oto          — son ile ilk nokta yan yanaysa halka, degilse gidis-donus
        #   dongu        — her zaman basa sar
        #   gidis_donus  — uctan don, geldigin yoldan geri git
        self.rota_mod = "oto"
        # Rotada METİN avı. Hedefleme sekmesinden BAĞIMSIZDIR.
        #
        # Ayrım şu işe yarıyor: rota metin arar ve kırar; metin kırılınca
        # içinden çıkan canavarları Hedefleme sekmesi halleder. İkisi aynı
        # listeye bağlı olsaydı ya canavar peşinde rotayı bırakırdı ya da
        # canavarlara hiç vurmazdı.
        self.rota_metin = True
        # Rota üzerindeyken metin bu yarıçapta aranır (ham).
        self.rota_metin_menzil = 6000
        # Yalnızca bu metinlere git. Boş = hepsi.
        # Türkçe-duyarsız, parça eşleşmesi: "karanlik" -> "Karanlık Metin"
        self.rota_metin_adlari = ""
        # Tur sayılması için en az kaç nokta geçilmiş olmalı.
        # 0 = sayma yok: rotanın sonuna varmak turu bitirir (varsayılan).
        # Rotaya sondan yakın bir noktada başlanınca tur çok kısa
        # sürüyorsa bu değer yükseltilebilir.
        self.tur_en_az_nokta = 0
        # Rota turu bitince sıradaki kanala geç.
        self.kanal_degistir = False
        # Gezilecek kanallar. Boş = 1..8
        self.kanallar = "1,2,3,4,5,6,7,8"
        # Tur bitince kanal değişimini BEKLE (True) ya da botu durdur (False).
        #
        # Kanal değiştirmek ayrı bir sunucuya bağlanmak demek (ölçüldü:
        # port = 30000 + 4 x kanal), bot bunu yapamaz. Ama sen elle
        # geçtiğinde algılayıp devam edebilir.
        self.kanal_bekle = True
        # Kanal menüsüne basma dizisi. Boşsa bot yalnızca uyarır.
        # Satır başına bir komut: 'tap X Y', 'bekle MS', 'tus KOD'.
        # Koordinatta {..} içinde k = kanal numarası kullanılabilir:
        #     tap 320 {700+k*90}
        # tools/dokunma_kaydet.py ile kaydedilir.
        self.kanal_dokunma = ""
        # Kanal değişiminde dizideki her "bekle" en fazla bu kadar (ms).
        # Kayıttaki beklemeler insan tepki süresi (2,7 sn'ye kadar);
        # menü ~1 sn'de açılıyor. 0 = kayıttaki süre aynen.
        self.kanal_menu_bekle = 1000
        # Elle geçmen için ne kadar beklenecek (ms). Süre dolarsa bot durur.
        self.kanal_bekleme = 120000
        # METİN ARA: metin görünmüyorsa sıradaki kanala geç, görürse kal.
        # Kanalı 'kanal_dokunma' dizisi değiştirir. Açıkken tur sonu kanal
        # değişimi devre dışı kalır — kanal değiştirmeyi TEK özellik yönetsin.
        self.metin_ara = False
        # Metin görülmezse kaç saniye sonra kanal değişsin.
        self.metin_ara_sure = 20
        # Yeni girilen kanalda metin görünmezse bu kadar sn sonra geç.
        self.metin_ara_yeni_sure = 3
        # Metin bulununca bildirim sesi çal.
        self.metin_ara_ses = True
        # METİN SÜRE TUTUCU: kırılan metin için kanal bazlı geri sayım.
        # Paket göndermez, yalnızca okur — bot çalışmasa da izler.
        self.metin_sure_tutucu = True
        self.metin_sure_dk = 15
        # Yakındaki metin kırılınca sayacı KENDİLİĞİNDEN başlat.
        # Kapalı (varsayılan): sayaçlar yalnızca elle başlatılır.
        self.metin_sure_otomatik = False
        # Süre dolunca sayaç aynı kanalda aynı süreyle yeniden başlasın.
        self.metin_sure_tekrar = True
        # Hedefin KAÇ HAM yakınına kadar yürünecek.
        #
        # Saldırı menzili (menzil) sunucunun gerçek vuruş alanından
        # geniş olabiliyor; 'menzile girdim' deyip durmak yetmiyordu.
        # Bu değer, gerçekten dibine gitmek için. 300 ham = 3 m.
        self.metin_yaklasma = 300
        # Ekran olcusu — dokunma noktasi disari tasarsa gonderilmez.
        self.ekran_genislik = 1080
        self.ekran_yukseklik = 1920
        # ISTEMCI ESAS: enjekte ettigimiz konum bir NIYET, istemcinin
        # bildirdigi bir OLCUM. Ayristiklarinda olcum kazanir — yoksa
        # bot ilerlemedigi bir yolda ilerlediğini sanir.
        self.istemci_esas = True
        # Kac ham birim sapma 'takildi' sayilir (800 = 8 m).
        self.sapma_siniri = 800
        # Istemcinin son haberi bu kadar ms icindeyse guvenilir.
        self.istemci_sabir_ms = 3000
        # SALDIRI DUGMESI — sag alttaki kilic. SABIT yerde oldugu icin
        # nisan almaya gerek yok: metin SECILDIKTEN sonra bu dugmeye
        # basiliyor. Yeri bir kez kaydedilir:
        #     python tools/saldiri_dugmesi.py
        # 0,0 = kayitli degil, eski paket yolu kullanilir.
        self.saldiri_dugme_x = 0
        self.saldiri_dugme_y = 0
        # Onay sonrasi dugmeye kac kez basilacak.
        self.saldiri_basma = 5
        # Basislar arasi bekleme (ms).
        self.saldiri_basma_ms = 220
        # SECIM PAKETI + DUGME: metinin vid'i elimizde, yanina kadar
        # yuruyoruz. Ekranda piksel aramadan secip dugmeye basiyoruz;
        # boylece vurusu ISTEMCI de baslatiyor. Hizi ise paketler
        # veriyor - ikisi birlikte calisiyor (bkz. _metin_saldirisi).
        self.metin_paket_secim = True
        # Rotada YALNIZCA metinden çıkan canavarlara vur.
        # Kapalıysa yol boyunca rastladığı her canavara saldırır.
        self.sadece_metin_canavari = True
        # Rota metini bulup tıklayınca saldırıyı KENDİ açar.
        # Hedefleme sekmesindeki kutular kapalı olsa bile metine ve
        # ondan çıkan canavarlara vurulur; metin ölünce kapanır.
        self.rota_kendi_saldiri = True
        # Metine vurduktan sonra canavarlara kaç saniye vurulabilir.
        self.metin_savas_suresi = 30
        # Can %0'a düşen bir hedefe kaç saniye daha vurulacak.
        #
        # Can %0 ÖLÜ demek değil: metin canı sıfırlanınca hâlâ ayakta
        # duruyor ve vurulmaya devam etmesi gerekiyor. Gerçek ölüm
        # işareti varlığın listeden düşmesi. Bu süre yalnızca takılı
        # kalmış bir cesede sonsuza kadar vurmamak için. 0 = süresiz.
        self.sifir_can_sabri = 20
        self.rota_bekle    = 0        # noktada bekleme, ms
        # Sadece rota: savaşma/toplama yapma, yalnızca noktaları gez.
        self.sadece_rota   = False
        # ── Market ──
        # Envanteri GÖREMİYORUZ: sunucu envanter durumunu bize bildirmiyor.
        # Bu yüzden hangi slotların satılacağı ELLE belirtilir. Boş slota
        # gönderilen satış paketini sunucu yok sayar, zararı olmaz — ama
        # dolu ve DEĞERLİ bir slot yazılırsa o eşya satılır. Aralığı dikkatli seç.
        self.npc_vid       = 0        # 0 = en yakın NPC
        self.slot_bas      = 25
        self.slot_son      = 45
        self.satis_adet    = 1
        self.satis_gecikme = 250      # satışlar arası ms
        # Envanter dolu uyarısını izle. Sunucu envanter durumunu ayrıca
        # bildirmiyor; tek göstergemiz sistem sohbet satırı (0x04, bType=1).
        self.uyari_izle    = True
        self.uyari_metin   = "fazla eşya"     # aranan parça (küçük/büyük fark etmez)
        # Market noktası (HAM birim). Uyarı gelince bot buraya yürür.
        # 0,0 = ayarlanmamış; o durumda bot sadece durur.
        self.market_x      = 0
        self.market_y      = 0
        # Uyarı gelince: sadece dur mu, yoksa markete gidip satıp dönsün mü?
        self.otomatik_market = False
        self.yaklas        = True     # bot HAREKET edebilir mi (rota/devriye)
        # HEDEFE YÜRÜMEK AYRI BİR İZİN.
        #
        # Eskiden tek "yaklas" ayarı iki ayrı işi yönetiyordu: rota/devriye
        # hareketi VE menzil dışındaki hedefe yürüme. Hedefe yürümeyi
        # kapatmak isteyen rotayı da kapatmak zorunda kalıyordu.
        #
        # Hedefe yürümek 0x07 hareket paketi gönderir; haritada "enjekte
        # konum" olarak görünen şey budur. Kapalıyken hedefleme YALNIZCA
        # menzildekine vurur, karakteri kımıldatmaz — hareketi rota
        # (ya da oyuncu) yapar.
        self.hedefe_yuru   = False        # Tek hamlede gidilecek azami mesafe. 29 Ağu 2026 ölçümü: 50/80/120 m
        # hepsi KABUL edildi — sunucu ışınlamıyor, YÜRÜTEREK götürüyor.
        # Bu yüzden yolu ufak adımlara bölmeye gerek yok.
        self.adim_mesafe   = 12000    # ham birim (120 m)
        # Oyunun kendi engel haritasını kullan (harita/ dizini).
        #
        # Kapatmak, botu eski davranışa döndürür: düz çizgide yürür ve
        # duvara girer. Veri yoksa ya da bulunduğumuz harita hizasızsa
        # zaten kendiliğinden devre dışı kalıyor.
        self.duvar_kacin = True
        # ENGEL PAYI (hucre = metre): yol duvarlara bu kadar
        # yaklasmasin. 1 iken bot "engellerin dibinden" gecip
        # kosede takiliyordu.
        self.duvar_payi = 2
        # Yolun yüzde kaçını bekleyip sonraki paketi hazırlayacağız.
        # 100 = tam bekle (karakter her adımda duraklar).
        # 85  = son %15'te sonraki hedefi yolla, yürüyüş kesilmez.
        self.erken_donus = 85
        # Hareket paketleri arası süre (ms).
        # 155 = gerçek istemcinin ölçülen ritmi (ortanca, 85 pakette).
        # Bu değerle her pakette ~70 ham ilerlenir — istemciyle birebir.
        self.akis_aralik_ms = 155
        # Ölçülen yürüme hızı: 50 m~4 sn, 80 m~6 sn, 120 m~9 sn ≈ 1300 ham/sn
        # Ham birim / saniye.
        #
        # 430 = 0.43 ham/ms. Bu değer TAHMİN DEĞİL: 23 Ağu 2026 kaydındaki
        # 163 gerçek GC_MOVE paketinin mesafe/süre oranı ölçüldü
        # (tools/hareket_paketi_incele.py) ve hepsinde aynı çıktı:
        #     401 ham /  942 ms = 0.43
        #    1250 ham / 2937 ms = 0.43
        # Yani oyundaki yürüme hızı sabiti bu.
        #
        # Eski varsayılan 1300 idi; o, tek bir kaba ölçümden ("80 m ~6 sn")
        # geliyordu. Fazla yüksek bir hız botun "vardım" sanıp erken
        # ilerlemesine yol açar — rota noktaları ıskalanır. Binek/hız
        # iksiri kullanıyorsan bu değeri yükseltebilirsin.
        # 2150 = 430 x 5.
        #
        # 430, oyunun TEMEL yürüme hızı — 163 gerçek GC_MOVE paketinden
        # ölçüldü (0.43 ham/ms). Ama karakterin bineği/hız iksiri varsa
        # gerçekte çok daha hızlı koşuyor.
        #
        # Bot komutu yavaş yollarsa animasyon ile yer değiştirme uyuşmuyor:
        # ayaklar hızlı koşuyor, gövde yavaş ilerliyor. Dışarıdan bakan
        # "geriye kayıyor" görüyor (moonwalk). Sahada görülen buydu.
        #
        # Bu değer karakterin GERÇEK hızıyla eşleşmeli. Ölçmek için
        # Hareket sekmesindeki "Hızımı ÖLÇ" butonunu kullan.
        self.yurume_hizi   = 2150
        # Hareket enjekte edildikten sonra İSTEMCİYİ de aynı yere hizala.
        # Olmazsa istemci eski konumunu tekrar bildirip bizi geri çeker.
        self.istemci_hizala = True
        # 0 = otomatik (APK'nin 0x11 oylamasi). Otomatik yanilirsa
        # buraya vid elle girilir; hizalama o vid'e gider.
        self.kendi_vid_elle = 0
        # KARAKTER ADI — kendi vid'imizi bulmanın en basit yolu.
        #
        # vid her oturumda değişiyor, ad değişmiyor. Sunucu 0x88 ile
        # oyuncu isimlerini yolluyor ve kendi karakterimiz de o listede
        # (29 Ağu 2026 kaydında vid 2528459 -> 'DOMALTAN'). Adı bilince
        # vid tek bir eşleşmeyle çıkıyor: oylama yok, oran yok, bekleme
        # yok, kanal değişince kendi kendine tazeleniyor.
        self.karakter_adi = ""
        # İstemci hizalaması yol boyunca KADEMELİ gönderilir; tek seferde
        # gönderilirse karakter ışınlanmış gibi sıçrar. Bu aralık ne kadar
        # küçükse hareket o kadar akıcı görünür.
        self.hizala_adim_ms = 150
        # İstemci kaç HAM birimde bir hizalanacak. 0 = yalnızca bacak sonu.
        #
        # Mesafeye bağlı, adıma değil: market yolu gibi uzun bacaklarda
        # "bacak sonunda bir kez" 28 saniye sessizlik demekti.
        #
        # SYNC_POSITION Z (yükseklik) taşımadığı için istemci her pakette
        # karakteri araziye yeniden oturtuyor ve bu kısa bir düşme olarak
        # görünüyor. 800 ham (8 m) ≈ 2 saniyede bir — denge noktası.
        self.hizala_mesafe = 800
        # "senkron" = GC_SYNC_POSITION 0x05 — ÇALIŞAN yöntem, animasyonsuz
        # "hareket" = GC_MOVE 0x03 — bu sunucuda ETKİSİZ, aşağıya bak
        #
        # 29 Ağu 2026 canlı denemesi (tools/animasyon_testi.py): kendi
        # vid'imizle gönderilen 0x03 istemciyi HİÇ kımıldatmadı. Metin2
        # istemcisi kendi karakterinin hareketini kendisi yönetir; sunucudan
        # gelen MOVE yalnızca BAŞKA varlıklara uygulanır. Seçenek yine de
        # duruyor — başka bir sunucu/istemci sürümünde işe yarayabilir.
        self.hizala_yontem = "senkron"
        # Wait-hack dizisine "DUR" (bfunc=0) eklensin mi. Ölçümde yalnızca
        # YÜRÜ gönderilen 30 m'lik hareket kabul edildi; DUR'lu dizi ise
        # hiç hasar vermedi. Şüpheli bu paket.
        self.wh_dur_paketi = False
        self.dur_can       = 0        # canım %X altına düşerse dur (0=kapalı)


# ═══════════════════════════════════════════════════════════════════════
#  Bot motoru
# ═══════════════════════════════════════════════════════════════════════

class Motor:
    """
    Tek iş parçacığında dönen durum makinesi.

    Döngü: durum oku → güvenlik → topla → hedefle/saldır → devriye.
    Arayüzle yalnızca kuyruk üzerinden konuşur (thread-safe).
    """

    def __init__(self, api, ayar, bildir):
        self.api = api
        self.ayar = ayar
        self.bildir = bildir          # (seviye, metin) -> None
        self.calisiyor = False
        self._is = None

        # istatistik
        self.oldurulen = 0
        self.toplanan = 0
        self.yang_toplanan = 0
        self.gonderilen = 0
        self.baslangic = 0
        self.durum_metni = "beklemede"

        # iç durum
        self._onceki_mob = set()
        # Toplama denemesi geçmişi: vid -> son gönderim anı. KALICI kara liste
        # DEĞİL: eşya gerçekten toplanınca yer listesinden (0x1B) zaten düşer;
        # düşmediyse (sunucu menzili dışındaydı) yaklaşınca yeniden denensin.
        self._toplandi = {}
        self._son_vurus = 0.0
        self._son_yetenek = 0.0
        # (0, 0) — None DEĞİL: _saldir metine tıklarken buradan konum
        # okuyor ve bot daha ilk turunu tamamlamadan saldırırsa None
        # indekslemesi çökerdi.
        self._son_konum = (0, 0)
        self._sikisma = 0
        self._rota_indeks = 0
        self._rota_baslangic_secildi = False
        self._rota_kimligi = None
        self._dunya = None            # engel haritası (tembel yüklenir)
        self._yol_hedef = None        # önbellekteki yolun SON hedefi
        self._yol = []                # kalan ara noktalar
        self._sapma_uyari = 0.0
        self._konum_kaynak = ""
        self._nokta_zamani = 0.0
        self._rota_yon = 1
        self._rota_onceki = -1
        self._kapi_uyarildi = False
        # wait-hack pencere takibi
        #
        # Pencere bilgisi doğrudan APK'dan gelir (istemciHareketYas);
        # saat farkı ya da günlük taraması gerekmez.
        # isabet doğrulama: saldırdığımız hedefin canı gerçekten düşüyor mu?
        self._son_hedef_id = 0
        self._son_hedef_can = -1
        self._son_uyari_zaman = 0      # aynı uyarıyı tekrar saymamak için
        self._kendi_vid = 0            # 0x11'den öğrenilir, API'den okunur
        self._kendi_vid_adli = False  # ad eşleşmesiyle bulunduysa True
        self._ad_vid_zamani = 0.0     # adın en son görüldüğü an
        self._ad_vid_arama = 0.0      # kendi başına liste çekme kısıtı
        self._vid_supheli = False      # vid bir canavara mı denk geldi
        self._vid_denetim_zamani = 0.0
        self.isabet = 0                # can düştü → saldırı sunucuya işledi
        self.iskaladi = 0              # can hiç değişmedi → işlemedi
        # hedef kilidi ve ev noktası
        self._kilit_id = 0
        self._kilit_baslangic = 0.0
        # Zaman aşımına uğrayan hedefler: {vid: ne zamana kadar seçilmesin}
        # Yoksa bot aynı öldüremediği canavarı sonsuza kadar yeniden seçiyor.
        self._bekleyen = {}
        self._tur_sayisi = 0
        self._tur_adim = 0
        self._tam_tur_gerekli = False
        self._kanal_indeks = -1
        # Metin ara: son metin görülme / kanala varış anı.
        self._metin_ara_zaman = 0.0
        self._metin_ara_buldu = False
        self._metin_ara_uyari = 0.0
        # Kanala yeni girildiği an (0 = taze giriş değil).
        self._metin_ara_varis = 0.0
        # Geçişlerden ÖĞRENİLEN port -> kanal (APK'nın numarası hep 0).
        self._port_kanal = {}
        # Metin süre tutucu arayüzde yaşar; arayüz buraya bağlar.
        # Yoksa (arayüzsüz kullanım) metin ara eski sırayla gezer.
        self.sure_tutucu = None
        self.sure_kaydet = None
        self._bekleme_uyari = 0.0
        self._son_tik = 0
        self._son_saldiri_imza = ()
        self._son_saldiri_log = 0.0
        self._son_oyuncu_vurus = 0.0     # PvP yavaş saldırı zamanlayıcısı
        self._oyuncu_vur_log = 0.0
        self._ekran_donus = -1
        self._dokunma_acildi = False
        self._metin_atlanan = set()
        self._metin_tik = {}
        self._can_sifir = {}
        self._metin_zamani = 0.0
        self._metin_pesinde = 0.0
        # Hedefleme vuruş döngüsü (ayrı iş parçacığı) — bkz. _hedefleme_dongusu
        self._vurus_is = None
        self._vurus_nesil = 0
        self._vurus_log = 0.0
        self._son_hedef_gorulme = 0.0
        self._metin_av_vid = 0
        self._metin_av_basi = 0.0
        self._saldirdiklarim = {}
        self._hizala_uyari = {}
        self._market_istegi = False
        self._ev_x = 0
        self._ev_y = 0
        self._pencere_taze = 0         # istemcinin hemen ardından ateşlendi
        self._pencere_bos = 0          # istemci sessizken ateşlendi
        self._pencere_kacti = 0        # pencere bulunamadı, yine de ateşlendi
        self._son_pencere = "-"

    # ---- yaşam döngüsü ----

    def basla(self):
        if self.calisiyor:
            return
        self.calisiyor = True
        self.baslangic = time.time()
        self._onceki_mob.clear()
        self._toplandi.clear()
        self._kapi_uyarildi = False
        self._son_uyari_zaman = 0
        self._rota_baslangic_secildi = False
        self._nokta_zamani = 0.0
        self._rota_yon = 1
        self._rota_onceki = -1
        self._is = threading.Thread(target=self._dongu, daemon=True)
        self._is.start()
        # HEDEFLEME VURUŞU KENDİ İŞ PARÇACIĞINDA — masaüstü tambot.py gibi.
        # Nesil numarası: Durdur'dan hemen sonra Başlat'a basılırsa eski
        # döngü uyurken yenisi açılıp aynı hedefe iki kat vurmasın.
        self._vurus_nesil += 1
        self._vurus_is = threading.Thread(
            target=self._hedefleme_dongusu, args=(self._vurus_nesil,),
            daemon=True)
        self._vurus_is.start()

    def dur(self):
        self.calisiyor = False
        self.durum_metni = "durduruldu"

    # ---- yardımcılar ----

    def _gonder(self, paket, aciklama):
        """Kuru moddaysa yalnızca loglar; değilse gerçekten gönderir."""
        if self.ayar.kuru:
            self.bildir("kuru", "[kuru] " + aciklama)
            return True
        c = self.api.enjekte(paket)
        if isinstance(c, dict) and c.get("ok"):
            self.gonderilen += 1
            return True
        hata = (c or {}).get("hata", self.api.son_hata or "yanıt yok")
        self.bildir("hata", "%s → gönderilemedi: %s" % (aciklama, hata))
        return False

    def _kapilar(self, durum):
        """Üç kapının durumu; hepsi açık değilse gerçek gönderim olmaz."""
        p = durum.get("proxy") or {}
        k = durum.get("kuyruk") or {}
        return {
            "proxy": bool(p.get("acik")) and bool(p.get("bagli")),
            "enjeksiyon": bool(p.get("enjeksiyon")),
            "kanal": "Proxy" in str(k.get("kanal", "")),
        }

    def _olu_sayilir(self, v):
        """
        Bu varlığı ölmüş sayıp bırakalım mı?

        CAN %0 ÖLÜ DEMEK DEĞİL
        ----------------------
        Eskiden {@code can == 0} görülünce hedef bırakılıyordu. Metinlerde
        bu yanlış: can %0'a düşüyor ama metin hâlâ ayakta duruyor ve
        vurulmaya devam etmesi gerekiyor. Bot canı sıfırlanınca vurmayı
        bırakıp gidiyordu — metin kırılmadan kalıyordu.

        Gerçek ölüm işareti CAN DEĞİL, varlığın listeden DÜŞMESİ
        (0x46 ölüm / 0x02 silme). O yüzden can %0 iken de vurmaya devam
        ediyoruz.

        Tek emniyet: ceset takılı kalırsa sonsuza kadar vurmayalım. Can
        %0'da {@code sifir_can_sabri} saniyeden uzun süre kalırsa artık
        bırakılır.
        """
        if v.get("can", -1) != 0:
            self._can_sifir.pop(v.get("vid"), None)
            return False
        sabir = self.ayar.sifir_can_sabri
        if sabir <= 0:
            return False                       # 0 = süresiz vur
        vid = v.get("vid")
        ilk = self._can_sifir.get(vid)
        simdi = time.time()
        if ilk is None:
            self._can_sifir[vid] = simdi
            if len(self._can_sifir) > 200:
                esik = simdi - 300
                self._can_sifir = {k: t for k, t in list(self._can_sifir.items())
                                   if t > esik}
            return False
        return simdi - ilk > sabir

    def _metin_vurusa_acik(self, v):
        """
        Bu metin çoklu hedefleme listesine (hızlı vuruş) girebilir mi?

        NEDEN GEREKLİ
        -------------
        Vuruş aralığı (_son_vurus) TEK ve iki ayrı saldırı yeri onu
        paylaşıyor: çoklu hedefleme ve rotanın metin vuruşu. Canavar
        sürüsü her turda sayacı sıfırlayınca sıra metine geldiğinde
        aralık hiç dolmuyor ve metin yalnızca ortalıkta canavar
        kalmadığı anlarda vuruş alıyordu. Sahada "metine 7x paketi
        göndermiyor" olarak görüldü.

        Çözüm: metin SEÇİLDİKTEN sonra (düğmeye basıldıktan sonra)
        canavarlarla AYNI seriye giriyor. Böylece tek bir seride hem
        metin hem çevresindeki canavarlar vuruluyor.

        Seçilmeden önce girmiyor — düğmeye basmadan paketle dövmek
        istemediğimiz şey. Düğme hiç kurulmamışsa kural yok, metin
        eskisi gibi doğrudan dövülüyor.
        """
        if not (self.ayar.metin_paket_secim
                and (self.ayar.saldiri_dugme_x
                     or self.ayar.saldiri_dugme_y)):
            return True
        d = self._metin_tik.get(v.get("vid"))
        return bool(d and d.get("dugme_bas"))

    def _metin_basinda_miyiz(self):
        """
        Şu an bir metinle uğraşıyor muyuz?

        Metin KIRILINCA yok oluyor ve canavarlar onun yerine doğuyor.
        Yani "yakında metin var mı" diye bakmak işe yaramaz — tam da
        canavarlarla dövüşeceğimiz anda metin ortada olmaz. Bu yüzden
        ZAMAN penceresi kullanılıyor: son metine vuruştan bu yana
        geçen süre.
        """
        if not self._metin_zamani:
            return False
        return (time.time() - self._metin_zamani
                <= max(3, self.ayar.metin_savas_suresi))

    def _metin_pesinde_miyiz(self):
        """
        Şu an bir metine GİDİYOR muyuz?

        _metin_basinda_miyiz yalnızca VURUŞ anını biliyor. Oysa rotadan
        asıl uzaklaştığımız yer YÜRÜYÜŞ: metini 50 m öteden görüp duvarı
        dolanırken rotadan 130 m açılabiliyoruz. O sırada "koptuk" deyip
        indeksi en yakın noktaya çekmek sahada şu döngüyü üretti:

            metini gör -> dolan -> "koptuk" -> indeks sıfırlan ->
            metini yine gör -> ...

        Bu yüzden av süresince ayrı bir damga tutuluyor. Damga tazeyken
        rotadan uzaklaşmak KASITLI sayılır, kopma değil.
        """
        if not self._metin_pesinde:
            return False
        return (time.time() - self._metin_pesinde
                <= max(8, self.ayar.metin_savas_suresi))

    def _hedef_uygun_basit(self, v, bx, by, azami):
        """
        BASİT HEDEFLEME — masaüstü tambot.py'deki mantığın aynısı.

        Orada tek kural vardı ve çalışıyordu:

            tipler = [0] Canavar / [2] Metin / [0,2] ikisi
            yakin  = tipi uyan, vnum>0, menzil içindeki varlıklar
            hedefler = yakin[:max_hedef]

        Aşağıdaki _hedef_uygun ise zamanla yedi ayrı kapı biriktirdi:
        rota metin avı, "sadece metin canavarı", metin tıklama onayı,
        atlanan metinler, av alanı yarıçapı, rota savaşı penceresi...
        Her biri tek başına gerekçeliydi ama birlikte şu oldu — bir kapı
        kapalıysa bot hiçbir şeye vurmuyor ve HANGİ kapının kapattığı
        görünmüyordu.

        Bu yol o kapıların hiçbirine bakmıyor. Rota kendi metin avını
        ayrıca sürdürüyor; ikisi birbirine karışmıyor.
        """
        tip = v.get("tip", -1)
        # ROTANIN KENDİ VURUŞU BASİT MODDA DA GEÇERLİ.
        #
        # Basit süzgeci yazarken bunu taşımayı unutmuştum ve sahada şu
        # görüldü: Hedefleme KAPALI + Rota AÇIK iken bot metini kırıyor
        # ama metinden çıkan canavarlara hiç vurmuyordu. Sebep, modül
        # kapalıyken hedef_mob'un False olması ve basit süzgecin başka
        # hiçbir şeye bakmaması.
        #
        # "Rotanın KENDİ vuruşu" ayarının tamamı zaten şunu vaat ediyor:
        # metin başındayken Hedefleme kapalı olsa bile metine VE ondan
        # çıkan canavarlara vurulur. Pencere kapanınca (metin_savas_suresi)
        # kendiliğinden bitiyor.
        rota_savasi = (self.ayar.rota_kendi_saldiri
                       and self.ayar.rota_metin
                       and self._metin_basinda_miyiz())
        if tip == TIP_MOB and not self.ayar.hedef_mob and not rota_savasi:
            return False
        if tip == TIP_METIN and not self.ayar.hedef_metin and not rota_savasi:
            return False
        if tip not in (TIP_MOB, TIP_METIN):
            return False

        # ATLANAN metin hiçbir yoldan dövülmez: rota ona "varamıyorum"
        # dediyse hedefleme de peşine düşmesin.
        if tip == TIP_METIN and v.get("vid") in self._metin_atlanan:
            return False
        # METİNLER ROTANIN İŞİ — ama YALNIZCA rota onları avlıyorsa.
        #
        # Saldırı düğmesine basmanın amacı dışarıdan normal vuruş hissi
        # vermek ve bunu ROTADA yapıyoruz: bot metinin yanına varır,
        # seçer, düğmeye basar. Hedefleme sekmesi ise eskisi gibi
        # paketle çalışıyor — orada düğme aramıyoruz.
        #
        # Rota metini sahiplenmiyorsa (modül kapalı ya da nokta yok)
        # metin buradan dövülür; yoksa hiç kırılmazdı.
        if (tip == TIP_METIN and self.ayar.rota_metin
                and self.ayar.rota):
            # SEÇİLMİŞ metin hızlı vuruş listesine girer.
            if not self._metin_vurusa_acik(v):
                return False

        if v.get("vnum", 0) <= 0:
            return False
        if self._olu_sayilir(v):
            return False
        return mesafe_ham(bx, by, v.get("x", 0), v.get("y", 0)) < azami

    def _hedef_uygun(self, v, bx, by, azami):
        tip = v.get("tip", -1)
        # ROTANIN KENDİ VURUŞU
        #
        # Rota metini bulup tıkladığında saldırıyı KENDİ açar; Hedefleme
        # sekmesindeki kutular kapalı olsa bile metine ve ondan çıkan
        # canavarlara vurulur. Metin ölüp pencere kapanınca yine kapanır.
        #
        # Neden ayrı: Hedefleme sekmesi "her yerde şuna vur" demek, rota
        # ise "metin başındayken şuna vur" demek. İkisini aynı kutulara
        # bağlamak, kullanıcıyı ikisinden birini seçmeye zorluyordu.
        rota_savasi = (self.ayar.rota_kendi_saldiri
                       and self.ayar.rota_metin
                       and self._metin_basinda_miyiz())
        if tip == TIP_MOB and not self.ayar.hedef_mob and not rota_savasi:
            return False
        # ROTADA GEZERKEN YOLDAKİ CANAVARLARA VURMA.
        #
        # İstenen davranış: rota metin arar, metini kırar, metinden ÇIKAN
        # canavarlarla dövüşür — ama yol boyunca rastladığı her canavara
        # saldırıp rotayı aksatmaz. Ayrım "metin başında mıyız" ile
        # yapılıyor: metine vurduktan sonraki pencerede canavarlar
        # serbest, dışında değil.
        if (tip == TIP_MOB and self.ayar.sadece_metin_canavari
                and self.ayar.rota_metin
                and not self._metin_basinda_miyiz()):
            return False
        # METİNLER ROTANIN İŞİ — ama YALNIZCA rota onları avlıyorsa.
        # (Gerekçe _hedef_uygun_basit'te.)
        if tip == TIP_METIN and self.ayar.rota_metin and self.ayar.rota:
            # SEÇİLMİŞ metin hızlı vuruş listesine girer.
            if not self._metin_vurusa_acik(v):
                return False
        # ATLANAN metin hiçbir yoldan dövülmez — rota "varamıyorum"
        # dediyse hedefleme de peşine düşmesin.
        if tip == TIP_METIN and v.get("vid") in self._metin_atlanan:
            return False
        if tip == TIP_METIN and not self.ayar.hedef_metin and not rota_savasi:
            return False
        if tip not in (TIP_MOB, TIP_METIN):
            return False
        if v.get("vnum", 0) <= 0:
            return False
        if self._olu_sayilir(v):
            return False
        return mesafe_ham(bx, by, v.get("x", 0), v.get("y", 0)) <= azami

    @staticmethod
    def _sadelestir(s):
        """
        Türkçe-duyarsız arama anahtarı.

        casefold() tek başına yetmez: "İ" (U+0130) casefold ile "i̇" olur
        (i + birleşen nokta), bu da "i" ile eşleşmez. Bu yüzden "Kırmızı
        İksir" içinde "iksir" aranınca bulunamıyordu.

        Burada aksanlar ayrıştırılıp atılır: İ→i, ı→i, ş→s, ğ→g, ç→c,
        ö→o, ü→u. Böylece Türkçe karakter yazmadan da arama yapılabilir —
        "havuc" yazınca "Havuç" bulunur.
        """
        import unicodedata
        s = (s or "").replace("ı", "i").replace("I", "i").replace("İ", "i")
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        return s.lower()

    @classmethod
    def _filtre_coz(cls, metin):
        """
        '1, 27002, iksir' → ({1, 27002}, ['iksir'])

        Sayılar vnum olarak, geri kalanı isim parçası olarak yorumlanır.
        """
        vnumlar, parcalar = set(), []
        for ham in (metin or "").replace(";", ",").split(","):
            p = ham.strip()
            if not p:
                continue
            if p.isdigit():
                vnumlar.add(int(p))
            else:
                parcalar.append(cls._sadelestir(p))
        return vnumlar, parcalar

    def _filtre_gecer(self, e):
        """Eşya filtresinden geçiyor mu? 'hepsi' modunda her şey geçer."""
        mod = self.ayar.filtre_mod
        if mod == "hepsi":
            return True
        vnumlar, parcalar = self._filtre_coz(self.ayar.filtre_metin)
        if not vnumlar and not parcalar:
            return True                    # filtre boş → kısıtlama yok
        vnum = e.get("vnum", 0)
        ad = self._sadelestir(e.get("ad") or "")
        eslesti = vnum in vnumlar or any(p in ad for p in parcalar)
        return eslesti if mod == "beyaz" else not eslesti

    def _esya_uygun(self, e, bx, by):
        if mesafe_ham(bx, by, e.get("x", 0), e.get("y", 0)) > self.ayar.topla_menzil:
            return False
        son = self._toplandi.get(e.get("vid"))
        if son is not None and time.time() - son < TOPLA_BEKLEME:
            return False           # az önce denendi; yaklaşınca yeniden denenir
        if not self._filtre_gecer(e):
            return False
        if self.ayar.sadece_benim:
            sahip = (e.get("sahip") or "").strip()
            benim = self.ayar.oyuncu_adi.strip()
            # sahip boşsa herkese açıktır; doluysa bize ait olmalı
            if sahip and benim and sahip.lower() != benim.lower():
                return False
            if sahip and not benim:
                # adımızı bilmiyoruz: sahipli eşyaya dokunma
                return False
        return True

    # ---- ana döngü ----

    def _dongu(self):
        self.bildir("bilgi", "bot başladı — %s" %
                    ("KURU ÇALIŞMA (paket gönderilmez)" if self.ayar.kuru
                     else "GERÇEK GÖNDERİM"))
        while self.calisiyor:
            try:
                self._tur()
            except Exception as e:                    # noqa: BLE001
                self.bildir("hata", "döngü hatası: %s: %s"
                            % (type(e).__name__, e))
                time.sleep(1.0)
        self.bildir("bilgi", "bot durdu")

    def _tur(self):
        durum = self.api.get("/api/durum")
        if not durum:
            self.durum_metni = "API'ye ulaşılamıyor"
            time.sleep(1.0)
            return


        konum = durum.get("konum") or {}
        self._kendi_vid_ogren(konum)
        # Ekran dönüşü APK'dan gelir; kaydırmaları çevirmek için lazım.
        try:
            d = int((durum.get("proxy") or {}).get("donus", -1))
        except (TypeError, ValueError):
            d = -1
        if d in (0, 90, 180, 270) and d != self._ekran_donus:
            self._ekran_donus = d
            self.bildir("bilgi",
                        "ekran dönüşü: %d derece — tıklama kaydırmaları "
                        "buna göre çevrilecek" % d)
        if not konum.get("bilinir"):
            self.durum_metni = "konum bilinmiyor (paket okuyucu/proxy açık mı?)"
            time.sleep(0.5)
            return
        bx, by, konum_kaynak = self._konumum(konum)
        # Saldırı yolları tik'i doğrudan görmüyor; tıklama paketi için lazım.
        self._son_tik = int(durum.get("tik", 0) or 0)
        if konum_kaynak != self._konum_kaynak:
            self._konum_kaynak = konum_kaynak
            self.bildir("bilgi",
                        "konum kaynağı: %s"
                        % ("ÖLÜ HESAP (bot kendi yürüyor, istemci sessiz)"
                           if konum_kaynak == "enjekte"
                           else "İSTEMCİ (oyuncu/istemci konum bildiriyor)"))

        # --- güvenlik kapıları ---
        if not self.ayar.kuru:
            kapi = self._kapilar(durum)
            if not all(kapi.values()):
                if not self._kapi_uyarildi:
                    self._kapi_uyarildi = True
                    eksik = [a for a, v in kapi.items() if not v]
                    self.bildir("uyari",
                                "GÖNDERİM KAPALI — açık olmayan kapı: %s. "
                                "Paket gönderilmiyor." % ", ".join(eksik))
                self.durum_metni = "kapılar kapalı"
                time.sleep(1.0)
                return
            self._kapi_uyarildi = False

        # --- can kontrolü ---
        if self.ayar.dur_can > 0:
            # kendi canımız /api/durum'da yok; hedefteki can bilgisi varlıkta.
            # Bu yüzden yalnızca bilgilendirme amaçlı bırakıldı.
            pass

        # --- sıkışma tespiti ---
        if self._son_konum == (bx, by):
            self._sikisma += 1
        else:
            self._sikisma = 0
        self._son_konum = (bx, by)

        # "Sadece rota" modunda savaş/toplama yok; varlık listesini çekmek
        # her turda gereksiz bir HTTP gidiş-dönüşü demek. O gecikme iki
        # hareket paketi arasına giriyor ve yürüyüşü kesiyor.
        if self.ayar.sadece_rota and self.ayar.yaklas and self.ayar.rota:
            # Metin avı açıksa varlık listesi gerekiyor; kapalıysa o HTTP
            # gidiş-dönüşünü atlayıp yürüyüşü kesintisiz tutuyoruz.
            rv = None
            if self.ayar.rota_metin:
                rv = self.api.get("/api/varliklar", n=80)
                if not isinstance(rv, list):
                    rv = None
            if rv is not None and self.ayar.kendi_vid_elle <= 0:
                self._kendi_vid_adla(rv)
            if self._rota_devriyesi(durum, bx, by, rv):
                return

        varliklar = self.api.get("/api/varliklar", n=80) or []
        if not isinstance(varliklar, list):
            varliklar = []
        # Liste zaten elimizde: ad eşleşmesini bedavaya tazele.
        if self.ayar.kendi_vid_elle <= 0:
            self._kendi_vid_adla(varliklar)

        # --- ölüm sayacı: kaybolan hedefler ---
        simdiki = {v.get("vid") for v in varliklar
                   if v.get("tip") in (TIP_MOB, TIP_METIN)}
        kaybolan = self._onceki_mob - simdiki
        if kaybolan:
            self.oldurulen += len(kaybolan)
        self._onceki_mob = simdiki

        # ─── METİN ARA ───
        # Metin görünmüyorsa (ve dövüşmüyorsak) sıradaki kanala geç.
        if self.ayar.metin_ara and self._metin_ara_kontrol(durum, bx, by,
                                                           varliklar):
            return

        # "Sadece rota" modunda savaş ve toplama atlanır — yalnızca gezilir.
        if self.ayar.sadece_rota:
            if self.ayar.yaklas and self._rota_devriyesi(durum, bx, by,
                                                         varliklar):
                return
            self.durum_metni = "sadece rota — nokta yok"
            time.sleep(0.4)
            return

        # ─── 1) EŞYA TOPLA ───
        if self.ayar.topla_acik and self._topla(bx, by):
            return

        # ─── 2) HEDEF SEÇ ve SALDIR ───
        # ─── isabet doğrulama ───
        # Bir önceki turda saldırdığımız hedefin canı düştü mü? Düştüyse
        # saldırı sunucuya İŞLEDİ; hiç değişmediyse paket gitti ama sunucu
        # saymadı (menzil denetimi, hedef geçersiz vb.).
        if self._son_hedef_id:
            for v in varliklar:
                if v.get("vid") == self._son_hedef_id:
                    can = v.get("can", -1)
                    if can >= 0 and self._son_hedef_can >= 0:
                        if can < self._son_hedef_can:
                            self.isabet += 1
                        elif can == self._son_hedef_can:
                            self.iskaladi += 1
                    self._son_hedef_can = can
                    break
            else:
                # hedef listeden düştü = büyük ihtimalle öldü
                self._son_hedef_id = 0
                self._son_hedef_can = -1

        # ─── ELLE MARKET İSTEĞİ ───
        # Butondan gelen istek burada karşılanır: yürüyüşün ortasına
        # dalmak yerine turun başında temiz bir noktada başlar.
        if self._market_istegi:
            self._market_istegi = False
            if self._ev_x == 0 and self._ev_y == 0:
                self._ev_x, self._ev_y = bx, by
            self._market_turu(durum, bx, by)
            return

        # ─── ENVANTER UYARISI ───
        if self.ayar.uyari_izle and self._envanter_dolu_mu():
            if (self.ayar.otomatik_market and self.ayar.market_x
                and self._market_uygun_mu(bx, by)[0]):
                self._market_turu(durum, bx, by)
                return
            self.durum_metni = "ENVANTER DOLU — bot durduruldu"
            self.bildir("uyari",
                        "ENVANTER DOLU uyarısı geldi — bot durduruldu. "
                        "Markete gidip sat, sonra tekrar başlat. "
                        "(Otomatik market için Market sekmesine bak.)")
            self.calisiyor = False
            return

        # ─── PvP: OYUNCUYA YAVAŞ SALDIRI ───
        # Canavar/metin akışını bozmadan, ayrı ve büyük aralıkla (belli
        # olmasın diye) saldırılabilir bir oyuncuya tek vuruş serpiştirir.
        self._oyuncu_vur_dene(varliklar, bx, by)

        # ── ÇOKLU HEDEF (varsayılan) ──
        # Menzildeki en yakın N canavara sırayla vur. Kilit/tek hedef
        # mantığından daha etkili olduğu canlı kullanımda görüldü.
        if self.ayar.coklu_hedef and not self.ayar.wait_hack:
            if self.ayar.basit_hedefleme:
                # Basit modda av alanı yarıçapı da yok — masaüstü
                # sürümünde öyleydi ve "rotadan uzaklaşınca hiçbir şeye
                # vurmuyor" sorunu da o yarıçaptan çıkıyordu.
                yakinlar = [v for v in varliklar
                            if self._hedef_uygun_basit(v, bx, by,
                                                       self.ayar.menzil)]
            else:
                yakinlar = [v for v in varliklar
                            if self._hedef_uygun(v, bx, by, self.ayar.menzil)
                            and not (self.ayar.ev_yaricap > 0
                                     and self._ev_disinda(
                                         v, self.ayar.ev_yaricap))]
            if yakinlar:
                if self._hedefleme_isci_acik():
                    # VURUŞU AYRI İŞ PARÇACIĞI YAPIYOR (_hedefleme_dongusu).
                    # Burada yalnızca YERİNDE KAL: rota yürümesin, hedefler
                    # menzilde kalsın. Burada da vurmak iki kat paket olurdu.
                    self.durum_metni = "%d hedefe saldırı" % len(yakinlar)
                    time.sleep(0.1)
                    return
                yakinlar.sort(key=lambda v: mesafe_ham(bx, by, v["x"], v["y"]))
                self._coklu_saldiri(yakinlar, bx, by)
                return

        hedef = self._hedef_sec(varliklar, bx, by)
        if hedef is not None:
            uzak = mesafe_ham(bx, by, hedef["x"], hedef["y"])

            if self.ayar.wait_hack and uzak <= self.ayar.wh_menzil:
                self._wait_hack(hedef, bx, by, int(durum.get("tik", 0)))
                return
            if uzak <= self.ayar.menzil:
                self._saldir(hedef)
                return
            if self.ayar.yaklas and self.ayar.hedefe_yuru:
                # Hedefe son yaklaşmada da tam yürü — %15 eksik kalırsa
                # vuruş alanına giremiyoruz.
                yakinlik = max(50, self.ayar.metin_yaklasma)
                pay = max(0.0, (uzak - yakinlik) / uzak) if uzak else 0.0
                self._yuru(int(bx + (hedef["x"] - bx) * pay),
                           int(by + (hedef["y"] - by) * pay), durum,
                           "hedefe yaklaş: %s (%.0f m)"
                           % (hedef.get("ad", "?"), uzak / 100.0), tam=True)
                return

        # ─── 3) ROTA / DEVRİYE ───
        # İkisi de hareket demektir; "hedefe yürü" kapalıysa yapılmaz.
        if self.ayar.rota_gez and self.ayar.yaklas:
            if self._rota_devriyesi(durum, bx, by, varliklar):
                return
        if self.ayar.devriye and self.ayar.yaklas:
            self._devriye(durum, bx, by)
        else:
            self.durum_metni = "hedef yok — bekleniyor"
            time.sleep(0.4)

    # ---- eylemler ----

    def _hizala_yol_boyunca(self, bx, by, hx, hy, sure, tik=0):
        """
        Yürüyüş süresince istemciyi hedefe getirir.

        İKİ YÖNTEM
        ----------
        "hareket" (varsayılan) — TEK bir GC_MOVE (0x03) paketi. İstemci
            karakteri kendi koşma animasyonuyla oraya yürütür; ara paket
            gerekmez, süreyi paketin kendi dwDuration alanı taşır.

        "senkron" — arka arkaya GC_SYNC_POSITION (0x05). Konum düzeltmesi
            olduğu için animasyon YOK: karakter kayarak/sürüklenerek gider.
            Eski davranış; 0x03 bir haritada tutmazsa yedek olarak durur.

        Her iki yöntemde de yol süresi kadar beklenir — sunucu bizi
        yürüterek götürüyor, bot varışı süreyle tahmin ediyor.
        """
        if not self.ayar.istemci_hizala or not self._kendi_vid:
            time.sleep(sure)
            return

        if self.ayar.hizala_yontem == "hareket":
            yb = yon_bayti(hx - bx, hy - by)
            self._istemciyi_yurut(hx, hy, tik, sure * 1000.0, yb)
            time.sleep(sure)
            # Varışta tek bir düzeltme: animasyon süresi ile sunucunun
            # gerçek hızı birebir tutmayabilir, kalan farkı kapatır.
            self._istemciyi_hizala(hx, hy)
            return

        adim = max(0.05, self.ayar.hizala_adim_ms / 1000.0)
        sayi = max(1, int(round(sure / adim)))
        # İstemci geride kaldıysa yol uzundur; süreye göre 3-4 adım yetmez,
        # aradaki sıçrama yine ışınlanma gibi görünür. Her ~2 m'ye bir nokta
        # düşecek kadar adım koy (üst sınır 60 — paket seli olmasın).
        yol = mesafe_ham(bx, by, hx, hy)
        sayi = max(sayi, min(60, int(yol / 200.0)))
        for i in range(1, sayi + 1):
            if not self.calisiyor:
                break
            time.sleep(sure / sayi)
            t = i / float(sayi)
            self._istemciyi_hizala(int(bx + (hx - bx) * t),
                                   int(by + (hy - by) * t))

    def _kendi_vid_adla(self, varliklar=None):
        """
        Kendi vid'imizi KARAKTER ADINDAN bulur — en basit yol.

        NEDEN
        -----
        vid'i bulmanın iki dolaylı yolu vardı ve ikisi de istatistikti:

        • 0x11 durum tiki + çoğunluk oyu — 3 oy birikene kadar bekliyor,
          bazı oturumlarda o paket HİÇ GELMİYOR (29 Ağu 2026, 179 saniye,
          5771 paket, sıfır 0x11).
        • 0x3E savaş vuruşu + isabet/ıska oranı — bot savaşana kadar hiçbir
          şey öğrenilmiyor, aynı canavara vuran başka oyuncu tabloyu
          bozabiliyor.

        İkisi de "kim olduğumuzu davranışımızdan çıkarma" denemesi. Oysa
        sunucu adımızı zaten söylüyor: 0x88 isim paketi kendi karakterimiz
        için de geliyor ve varlık listesinde `ad` alanında duruyor.

        vid her oturumda değişir, AD DEĞİŞMEZ. Kullanıcı adını bir kez
        yazar; eşleşme tek adımda, kesin ve anında olur. Kanal değişince
        yeni vid bir sonraki turda kendiliğinden yakalanır.

        Döner: kilit kuruldu mu (True = vid addan biliniyor).
        """
        ham = (self.ayar.karakter_adi or "").strip()
        if not ham:
            if self._kendi_vid_adli:
                self._kendi_vid_adli = False
            return False

        simdi = time.time()
        if varliklar is None:
            # Liste elde yoksa: kilitliysek ve az önce doğrulandıysa hiç
            # istek atma. "Sadece rota" modunda her HTTP gidiş-dönüşü
            # yürüyüşü kesiyor, o yüzden bedavaya bakmak şart.
            if self._kendi_vid_adli and simdi - self._ad_vid_zamani < 10.0:
                return True
            if simdi - self._ad_vid_arama < 2.0:
                return self._kendi_vid_adli
            self._ad_vid_arama = simdi
            varliklar = self.api.get("/api/varliklar", n=80)
            if not isinstance(varliklar, list):
                return self._kendi_vid_adli

        hedef = self._sadelestir(ham)
        eslesen = []
        for v in varliklar or []:
            # Canavar/metin olamayız; adaş bir canavar varsa tuzağa düşme.
            if v.get("tip") in (TIP_MOB, TIP_METIN):
                continue
            if self._sadelestir(v.get("ad") or "") == hedef:
                eslesen.append(v)

        if len(eslesen) > 1:
            self._hizala_sustur(
                "ad cakismasi",
                "\"%s\" adında %d varlık var — hangisi olduğun belli "
                "değil, ad eşleşmesi kullanılmıyor." % (ham, len(eslesen)))
            return self._kendi_vid_adli

        if not eslesen:
            # Ad görünmüyor: yeni oturum ya da isim paketi henüz gelmedi.
            # Eski vid'i sonsuza dek tutmak tehlikeli — o vid artık başka
            # birine ait olabilir. 15 saniye sonra kilidi bırak, eski
            # yollar (0x11 / savaş) devralsın.
            if self._kendi_vid_adli and simdi - self._ad_vid_zamani > 15.0:
                self._kendi_vid_adli = False
                self.bildir("uyari",
                            "\"%s\" 15 saniyedir listede yok — ad kilidi "
                            "bırakıldı, otomatik bulmaya dönülüyor" % ham)
            return self._kendi_vid_adli

        vid = int(eslesen[0].get("vid", 0) or 0)
        if vid <= 0:
            return self._kendi_vid_adli
        self._ad_vid_zamani = simdi
        if vid != self._kendi_vid or not self._kendi_vid_adli:
            eski = self._kendi_vid
            self._kendi_vid = vid
            self._kendi_vid_adli = True
            self._vid_supheli = False
            self.bildir("basari",
                        "kendi vid ADDAN bulundu: %s -> %d%s"
                        % (eslesen[0].get("ad") or ham, vid,
                           " (eski %d)" % eski if eski and eski != vid
                           else ""))
        return True

    def _kendi_vid_ogren(self, konum):
        """
        Kendi vid'imizi API'den alır — ama körü körüne değil.

        NEDEN DENETİM VAR
        -----------------
        İstemciye gönderdiğimiz paket hangi vid'i taşırsa istemci O VARLIĞI
        oynatır. Yanlış vid = ekranda kendi karakterin yerine yandaki bir
        canavarın/atın taşınması. Sahada tam olarak bu yaşandı.

        APK vid'i 0x11 paketinden öğreniyor. 29 Ağu 2026 kaydının
        çerçevelenmiş analizi (tools/kendi_vid_cerceve.py) gösterdi ki 0x11
        neredeyse hep tek bir vid taşıyor ama akış nadiren kaydığında tek
        oyluk hayalet değerler doğuyor. APK artık çoğunluk oyu kullanıyor;
        burada ikinci bir kontrol var: az oylu bir vid'e ASLA paket gönderme.
        """
        try:
            v = int(konum.get("kendiVid", 0) or 0)
            oy = int(konum.get("kendiVidOyu", -1))
            aday = int(konum.get("kendiVidAday", -1))
        except (TypeError, ValueError):
            return
        # ÖNCE AD. Elle girilen vid bir hata ayıklama kaçamağı olduğu
        # için ondan sonra gelir; ad kilidi varken 0x11 oylaması ve savaş
        # çıkarımı hiç çalışmaz — kesin bilgiyi tahminle ezmenin anlamı yok.
        if self.ayar.kendi_vid_elle <= 0 and self._kendi_vid_adla():
            return

        if self.ayar.kendi_vid_elle > 0:
            # Elle girilen vid, APK'nın bulduğuyla ÇELİŞİYORSA uyar.
            # Kanal değişiminden sonra eski elle değer kalmış olabilir.
            if v > 0 and oy >= 3 and v != self.ayar.kendi_vid_elle:
                self._hizala_sustur(
                    "elle catisma",
                    "elle girilen vid %d, ama APK %d diyor (%d oy). "
                    "Kanal değiştiysen elle değeri 0 yap."
                    % (self.ayar.kendi_vid_elle, v, oy))
            if self._kendi_vid != self.ayar.kendi_vid_elle:
                self._kendi_vid = self.ayar.kendi_vid_elle
                self.bildir("bilgi", "kendi vid ELLE ayarlandı: %d"
                            % self._kendi_vid)
            return
        if v <= 0:
            # APK vid'i unuttu (yeni oturum: kanal değişimi / yeniden
            # giriş). Eskisini tutmaya devam edersek artık başka birine
            # ait olabilecek bir vid'e paket göndeririz.
            if self._kendi_vid:
                self._kendi_vid = 0
                self._saldirdiklarim.clear()
                self.bildir("uyari",
                            "kendi vid SIFIRLANDI (yeni oturum). Bot bir "
                            "canavara saldırınca yeniden öğrenilecek.")
            return
        # oy bilgisi olmayan eski APK: eskisi gibi davran ama uyar
        if oy < 0:
            if self._kendi_vid != v:
                self._kendi_vid = v
                self.bildir("uyari",
                            "kendi vid %d — APK oy bilgisi vermiyor, "
                            "eski sürüm. Hizalama riskli." % v)
            return
        if oy < 3:
            if self._kendi_vid:
                self.bildir("uyari",
                            "kendi vid adayı %d yalnızca %d oy aldı — "
                            "güvenilmez, hizalama duraklatıldı" % (v, oy))
                self._kendi_vid = 0
            return
        if v != self._kendi_vid:
            self._kendi_vid = v
            self.bildir("bilgi", "kendi vid: %d (%d oy, %d aday)"
                        % (v, oy, aday))

    def _vid_baskasi_mi(self, vid):
        """
        Bu vid gerçekten biz miyiz — yoksa listedeki bir canavar mı?

        Sunucu bize KENDİ hareketimizi yollamıyor, dolayısıyla kendi vid'imiz
        varlık listesinde canavar/metin olarak görünemez. Görünüyorsa vid
        yanlıştır ve istemci o varlığı oynatır.
        """
        if not vid:
            return True
        simdi = time.time()
        if simdi - self._vid_denetim_zamani < 5.0:
            return self._vid_supheli
        self._vid_denetim_zamani = simdi
        varliklar = self.api.get("/api/varliklar", n=120)
        if not isinstance(varliklar, list):
            return self._vid_supheli
        for v in varliklar:
            if int(v.get("vid", 0) or 0) != vid:
                continue
            tip = v.get("tip")
            if tip in (TIP_MOB, TIP_METIN):
                if not self._vid_supheli:
                    self._vid_supheli = True
                    self.bildir(
                        "hata",
                        "kendi vid %d varlık listesinde %s olarak görünüyor "
                        "(%s) — BU BİZ DEĞİLİZ. İstemci paketleri durduruldu, "
                        "yoksa istemci o varlığı oynatır. Hareket "
                        "sekmesinden vid'i elle girebilirsin."
                        % (vid, "canavar" if tip == TIP_MOB else "metin",
                           v.get("ad") or "?"))
                return True
            break
        self._vid_supheli = False
        return False

    def _hizalama_araligi(self):
        """
        İstemci kaç HAM birimde bir hizalanacak.

        NEDEN MESAFE, ADIM DEĞİL
        ------------------------
        Önce "bacak sonunda bir kez" yapılmıştı. Rota bacakları ~8 m olduğu
        için orada iyi çalıştı — ama MARKETE giderken bacak, adım mesafesi
        kadar uzun oluyor (varsayılan 120 m). 430 ham/s hızda bu, 28 saniye
        boyunca istemciye tek bir paket bile gitmemesi demek: istemci
        yerinde çakılı kalıyor, sonra bir anda 120 m sıçrıyor. Sahada
        "markete giderken sync çalışmıyor" olarak görüldü.

        Mesafeye bağlayınca bacak uzunluğu fark etmiyor: rota bacağında da
        market yolunda da her N ham'da bir hizalama gider.

        NEDEN SEYRELTİYORUZ
        -------------------
        SYNC_POSITION yalnızca X,Y taşır, Z (yükseklik) yok. İstemci her
        pakette karakteri araziye yeniden oturtuyor ve bu kısa bir DÜŞME
        olarak görünüyor. Saniyede 6 hizalama gönderince karakter "düşe
        düşe" ilerliyordu. Varsayılan 800 ham (8 m) ≈ 2 saniyede bir.
        """
        return max(0, int(self.ayar.hizala_mesafe))

    def _istemciyi_yurut(self, x, y, tik, sure_ms, brot=0):
        """
        İstemciyi ANİMASYONLA yürütür (GC_MOVE).

        Süre, sunucunun bizi gerçekten taşıdığı süreyle aynı verilir ki
        istemci ile sunucu adım adım aynı yerde olsun. Kayıttaki gerçek
        paketlerde oran 0.43 ham/ms idi; bizim yürüme hızımız ondan çok
        farklıysa animasyon hızlı/yavaş görünür ama yine de ANİMASYONLU
        olur — sürüklenme biter.
        """
        if not self.ayar.istemci_hizala or not self._kendi_vid:
            return
        if self._vid_baskasi_mi(self._kendi_vid):
            return
        paket = paket_istemci_hareket(self._kendi_vid, int(x), int(y),
                                      int(tik), sure_ms, brot)
        if self.ayar.kuru:
            self.bildir("kuru", "[kuru] istemciyi yürüt -> %d,%d  %d ms"
                        % (x, y, sure_ms))
            return
        c = self.api.enjekte_istemci(paket)
        if not (isinstance(c, dict) and c.get("ok")):
            self.bildir("hata", "istemci yürütülemedi: %s"
                        % ((c or {}).get("hata", self.api.son_hata or "?")))

    def _hedefi_not_et(self, vid):
        """
        Saldırdığımız hedefi zaman damgasıyla kaydeder.

        Kendi vid'imizi savaştan çıkarmak için gerekli: sunucu vuruşu
        {@code 0x3E | vuran | vurulan} olarak geri yolluyor. Vurulan bizim
        az önce saldırdığımız hedefse, vuran biziz.
        """
        if vid:
            self._saldirdiklarim[int(vid)] = time.time()
            if len(self._saldirdiklarim) > 200:
                esik = time.time() - 15.0
                self._saldirdiklarim = {k: t for k, t
                                        in list(self._saldirdiklarim.items())
                                        if t > esik}

    def _vid_ara(self, sure=25.0, bildir=None):
        """
        Kendi vid'imizi CANLI savaştan bulur — kayıt almadan.

        NEDEN BOTUN İÇİNDE
        ------------------
        Doğru vid'i bulmanın yolu şuydu: pcap al, tools/kendi_vid_savastan.py
        çalıştır, çıkan sayıyı elle gir. Her oyun girişinde vid değiştiği
        için bu her seferinde tekrarlanacaktı. Oysa gereken her şey zaten
        elimizde: bot kime saldırdığını BİLİYOR (paketi kendi yolluyor) ve
        gelen savaş paketleri /api/log'da duruyor.

        ÖLÇÜT — oran, salt sayım değil
        ------------------------------
        "Vurulan bizim hedefimizdi, demek vuran biziz" tek başına yetmiyor:
        aynı canavara vuran BAŞKA oyuncular da bu testi geçiyor. Sahada
        yanlış aday 20371 oy toplamıştı.

        Ayrımı OLUMSUZ kanıt yapıyor: başka oyuncu bizim vurmadığımız
        şeylere de vurur, biz vurmayız. Kayıtta ölçülmüştü —
        biz %100 örtüşme, başkaları %0.

        Döner: (vid, isabet, iska, adaylar) — bulunamazsa vid 0.
        """
        from collections import defaultdict
        kanit = defaultdict(lambda: [0, 0])
        gorulen = set()
        bitis = time.time() + sure
        while time.time() < bitis and self.calisiyor is not False:
            kayitlar = self.api.get("/api/log", n=200)
            if isinstance(kayitlar, list):
                for k in kayitlar:
                    if k.get("giden") or k.get("opcode") != 0x3E:
                        continue
                    anahtar = (k.get("zaman"), k.get("hex"))
                    if anahtar in gorulen:
                        continue
                    gorulen.add(anahtar)
                    hx = (k.get("hex") or "").split()
                    if len(hx) < 9:
                        continue
                    try:
                        vuran = int(hx[4] + hx[3] + hx[2] + hx[1], 16)
                        vurulan = int(hx[8] + hx[7] + hx[6] + hx[5], 16)
                    except ValueError:
                        continue
                    if not (0 < vuran < 100000000):
                        continue
                    # Kendimize saldırmayız: vuran hedef listemizdeyse canavar
                    if vuran in self._saldirdiklarim:
                        continue
                    t = self._saldirdiklarim.get(vurulan)
                    bizim = t is not None and time.time() - t < 15.0
                    kanit[vuran][0 if bizim else 1] += 1
            if bildir:
                en = max(kanit.items(), key=lambda kv: kv[1][0], default=None)
                bildir(len(gorulen), en)
            time.sleep(1.0)

        adaylar = sorted(kanit.items(), key=lambda kv: -kv[1][0])
        for vid, (isabet, iska) in adaylar:
            if isabet >= 5 and iska * 4 <= isabet:
                return vid, isabet, iska, adaylar
        return 0, 0, 0, adaylar

    def _hizala_sustur(self, anahtar, mesaj):
        """
        Hizalama uyarısını 10 saniyede bir basar.

        Hizalama saniyede birkaç kez çağrıldığı için her seferinde uyarmak
        günlüğü boğardı; ama hiç uyarmamak da kullanıcıyı kör bırakıyordu.
        """
        simdi = time.time()
        if simdi - self._hizala_uyari.get(anahtar, 0) < 10.0:
            return
        self._hizala_uyari[anahtar] = simdi
        self.bildir("uyari", mesaj)

    def _istemciyi_hizala(self, x, y):
        """
        İstemciyi sunucudaki konumumuza getirir (GC_SYNC_POSITION).

        Bot sunucuda ilerlediğinde istemci eski konumda kalır ve ilk
        fırsatta kendi konumunu bildirip bizi geri çeker. Bu çağrı o
        ayrışmayı kapatır — 29 Ağu 2026'da canlı denemeyle bulundu.
        """
        # SESSİZ İPTAL ETME.
        #
        # Eskiden bu üç durumda fonksiyon hiçbir şey söylemeden dönüyordu.
        # Kullanıcı "istemci eşitlemiyor" diyor ama nedenini göremiyordu:
        # ayar kapalı mı, vid mi yok, vid canavara mı denk geldi? Artık
        # her biri ayrı ayrı, 10 saniyede bir kez söyleniyor.
        if not self.ayar.istemci_hizala:
            self._hizala_sustur("ayar kapalı",
                                "istemci hizalama KAPALI — Hareket sekmesindeki "
                                "'İSTEMCİYİ de hizala' kutusu işaretli değil")
            return
        if not self._kendi_vid:
            self._hizala_sustur("vid yok",
                                "istemci hizalanamıyor: KENDİ VİD BİLİNMİYOR. "
                                "Bot bir canavara saldırınca öğrenilir "
                                "(0x3E savaş paketi). Sadece metin kırmak "
                                "yetmeyebilir — metinden çıkan canavarlara da "
                                "vurulmalı. python tools/vid_izle.py ile izle.")
            return
        if self._vid_baskasi_mi(self._kendi_vid):
            return                      # _vid_baskasi_mi kendi uyarısını basar
        paket = paket_istemci_hizala(self._kendi_vid, x, y)
        if self.ayar.kuru:
            self.bildir("kuru", "[kuru] istemciyi hizala -> %d,%d" % (x, y))
            return
        c = self.api.enjekte_istemci(paket)
        if not (isinstance(c, dict) and c.get("ok")):
            self.bildir("hata", "istemci hizalanamadı: %s"
                        % ((c or {}).get("hata", self.api.son_hata or "?")))

    def _noktaya_yuru(self, hx, hy, durum, etiket):
        """
        Bir noktaya yürür ve VARANA KADAR bekler.

        Sunucu ışınlamaz, yürütür (~13 m/s ölçüldü) ve kendi hareketimizi
        bize geri yollamaz — bu yüzden varışı süreyle tahmin ediyoruz.
        Uzun yol adım adım gider; her adımda tik tazelenir.
        """
        while self.calisiyor:
            konum = self.api.get("/api/konum") or {}
            # Ham x,y bot kendi yürürken donar; mesafe ölü hesaptan ölçülür,
            # yoksa daha ilk turda "ilerleme yok" deyip vazgeçerdik.
            bx, by, _ = self._konumum(konum)
            uzak = mesafe_ham(bx, by, hx, hy)
            if uzak <= 400:                      # 4 m — vardık say
                return True
            d = self.api.get("/api/durum") or durum
            self._yuru(hx, hy, d, "%s (%.0f m)" % (etiket, uzak / 100.0))
            # _yuru zaten yol süresince bekler; ilerleme yoksa döngü sürer
            yx, yy, _ = self._konumum(self.api.get("/api/konum") or {})
            if (yx, yy) == (bx, by):
                self.bildir("uyari", "%s — ilerleme yok, vazgeçildi" % etiket)
                return False
        return False

    def market_iste(self):
        """
        "Markete git" butonu — market turunu ELLE başlatır.

        Envanter uyarısını beklemez. İki durum var:

          • Bot çalışıyorsa: istek bayrağı konur, sıradaki turda market
            turuna girilir. Böylece yürüyüşün ortasına dalmayız.
          • Bot kapalıysa: tek seferlik bir tur çalıştırılır ve biter.
            Av yeri olarak ŞU ANKİ konum alınır, satıştan sonra oraya
            dönülür.

        Döner: kullanıcıya gösterilecek kısa mesaj.
        """
        if not self.ayar.market_x and not self.ayar.market_y:
            return "Market noktası ayarlı değil — önce konumu kaydet."
        if not self.ayar.npc_vid:
            return "NPC vid ayarlı değil — önce tıklamandan öğret."
        bx, by, _ = self._konumum(self.api.get("/api/konum") or {})
        uygun, sebep = self._market_uygun_mu(bx, by)
        if not uygun and sebep:
            return ("MARKETE GİDİLMEDİ — %s. Bu köyde markete git ve "
                    "\"Bulunduğum yeri market noktası yap\" de." % sebep)
        if self._market_istegi:
            return "Market turu zaten sırada."
        self._market_istegi = True
        if self.calisiyor:
            return "Market turu sıraya alındı."
        threading.Thread(target=self._tek_market_turu, daemon=True).start()
        return "Markete gidiliyor (tek seferlik)."

    def _harita_adi(self, x, y):
        """Bu konum hangi haritada? Bilinmiyorsa boş dizgi."""
        h = self._harita(x, y)
        return h.ad if h else ""

    def _market_uygun_mu(self, bx, by):
        """
        Kayıtlı market noktası BULUNDUĞUMUZ haritada mı?

        NEDEN ÖNEMLİ
        ------------
        Market konumu tek bir sayı çiftiydi ve köy değişince eskisi
        kalıyordu. Sahada görülen: 1. köydeyken kayıtlı market
        (867483, 243613) 2. köyün haritasındaydı (metin2_map_c3).
        Bot oraya yürümeye çalışıyor, hedef bu haritanın dışında
        olduğu için yol bulunamıyor ve tur sessizce ölüyordu.

        Döner: (uygun_mu, açıklama)
        """
        mx, my = self.ayar.market_x, self.ayar.market_y
        if not (mx or my):
            return False, "market noktası ayarlı değil"
        burasi = self._harita_adi(bx, by)
        orasi = self._harita_adi(mx, my)
        if not burasi or not orasi:
            # Harita bilinmiyorsa engelleme — engel haritası olmayan
            # bir yerde de market kullanılabilmeli.
            return True, ""
        if burasi != orasi:
            return False, ("kayıtlı market %s haritasında, sen %s "
                           "haritasındasın" % (orasi, burasi))
        return True, ""

    def _tek_market_turu(self):
        """Bot kapalıyken çalışan tek seferlik market turu."""
        self.calisiyor = True
        try:
            durum = self.api.get("/api/durum")
            if not durum:
                self.bildir("hata", "API'ye ulaşılamıyor — market turu iptal")
                return
            konum = durum.get("konum") or {}
            self._kendi_vid_ogren(konum)
            kx, ky = self._istemci_konumu(konum, 0, 0)
            uygun, sebep = self._market_uygun_mu(kx, ky)
            if not uygun and sebep:
                # Sessizce ölmek yerine SEBEBİNİ söyle. Eskiden bot
                # başka haritadaki markete yürümeye çalışıp takılıyor,
                # kullanıcı "duruyor, yürümüyor" görüyordu.
                self.bildir("hata",
                            "MARKET TURU İPTAL — %s. Bu köyde markete "
                            "git ve 'Bulunduğum yeri market noktası yap' "
                            "de." % sebep)
                return
            if not konum.get("bilinir"):
                self.bildir("hata", "konum bilinmiyor — market turu iptal")
                return
            if not self.ayar.kuru:
                kapi = self._kapilar(durum)
                if not all(kapi.values()):
                    eksik = [a for a, v in kapi.items() if not v]
                    self.bildir("hata", "GÖNDERİM KAPALI — %s. Market turu iptal."
                                % ", ".join(eksik))
                    return
            bx, by, _ = self._konumum(konum)
            # Dönüş noktası: şu an neredeysek orası
            self._ev_x, self._ev_y = bx, by
            self._market_istegi = False
            self._market_turu(durum, bx, by)
        except Exception as e:                        # noqa: BLE001
            self.bildir("hata", "market turu hatası: %s: %s"
                        % (type(e).__name__, e))
        finally:
            self._market_istegi = False
            self.calisiyor = False
            self.durum_metni = "hazır"

    def _agdan_yuru(self, hx, hy, durum, etiket):
        """
        Hedefe KAYITLI ROTA ÜZERİNDEN gider — düz çizgiyle değil.

        NEDEN
        -----
        Kayıtlı rota tanımı gereği engelsiz — çünkü sen oradan geçtin.
        Uzun bir yolculuğu düz çizgi yerine bu yol ağı üzerinden yaparsak
        duvara girmeyiz.

        1 Eyl 2026'dan beri oyunun KENDİ engel haritası da elimizde
        (harita/ dizini, tools/harita_cikar.py) ve _yuru her bacakta ona
        bakıyor. İkisi çelişmiyor, tamamlıyor: engel haritası "buradan
        geçilmez" der, kayıtlı rota "buradan geçmek MANTIKLI" der. Rota
        ağı hâlâ daha iyi bir güzergâh seçiyor, çünkü A* en kısa yolu
        arar ve en kısa yol dar geçitlerden sürtünerek geçebiliyor.

        Yöntem:
          1. Bulunduğumuz yere en yakın rota noktasını bul  (A)
          2. Hedefe en yakın rota noktasını bul             (B)
          3. A'ya git, rota üzerinde A'dan B'ye yürü, sonra hedefe git

        Rota yoksa ya da hedef zaten yakınsa düz çizgiyle gidilir.
        """
        noktalar = self.ayar.rota
        kb, kby, _ = self._konumum(durum.get("konum") or {})
        dogrudan = mesafe_ham(kb, kby, hx, hy)

        # Kısa yolda ağa sapmak anlamsız; rota yoksa da seçenek yok.
        #
        # Eşik 30 m. Önce adim_mesafe (120 m) kullanılmıştı ama o, ağın
        # hiç devreye girmemesine yol açıyordu: bir köyün içindeki market
        # yolu çoğu zaman 120 m'den kısa ve tam da duvarlı olan kısım orası.
        if len(noktalar) < 2 or dogrudan < 3000:
            return self._noktaya_yuru(hx, hy, durum, etiket)

        def enyakin(px, py):
            return min(range(len(noktalar)),
                       key=lambda i: mesafe_ham(px, py, int(noktalar[i][0]),
                                                int(noktalar[i][1])))

        a = enyakin(kb, kby)
        b = enyakin(hx, hy)
        a_uzak = mesafe_ham(kb, kby, int(noktalar[a][0]), int(noktalar[a][1]))
        b_uzak = mesafe_ham(hx, hy, int(noktalar[b][0]), int(noktalar[b][1]))

        # Ağ ancak İKİ UCU DA yola yakınsa işe yarar. Hedef yoldan 50 m
        # uzaktaysa oraya zaten düz çizgiyle gitmek zorundayız; ağa sapmak
        # yolu uzatmaktan başka işe yaramaz.
        if a_uzak > 5000 or b_uzak > 5000:
            self.bildir("uyari",
                        "%s — kayıtlı yol uzak (giriş %.0f m, çıkış %.0f m), "
                        "düz çizgiyle gidiliyor"
                        % (etiket, a_uzak / 100.0, b_uzak / 100.0))
            return self._noktaya_yuru(hx, hy, durum, etiket)

        # Rota üzerinde A'dan B'ye hangi yön kısa? (halka ise iki seçenek var)
        halka = self._rota_halka_mi(noktalar)
        n = len(noktalar)
        if halka:
            ileri = (b - a) % n
            geri = (a - b) % n
            sira = ([(a + k) % n for k in range(ileri + 1)] if ileri <= geri
                    else [(a - k) % n for k in range(geri + 1)])
        else:
            sira = (list(range(a, b + 1)) if a <= b
                    else list(range(a, b - 1, -1)))

        self.bildir("bilgi",
                    "%s — kayıtlı yol üzerinden: nokta %d → %d (%d nokta)"
                    % (etiket, a + 1, b + 1, len(sira)))

        for sayac, i in enumerate(sira):
            if not self.calisiyor:
                return False
            nx, ny = int(noktalar[i][0]), int(noktalar[i][1])
            if not self._noktaya_yuru(nx, ny, durum,
                                      "%s [yol %d/%d]"
                                      % (etiket, sayac + 1, len(sira))):
                self.bildir("uyari", "%s — yol üzerinde takıldık" % etiket)
                return False
        return self._noktaya_yuru(hx, hy, durum, "%s [son adım]" % etiket)

    def _market_turu(self, durum, bx, by):
        """
        Envanter dolunca: markete yürü, dükkânı aç, sat, kapat, av yerine dön.

        Av yeri = botun BAŞLADIĞI konum (ev noktası). Market noktası ve NPC
        vid'i kullanıcı tarafından ayarlanır; ikisi de bilinmeden bu akış
        çalışamaz çünkü dükkân NPC'leri hareketsizdir ve varlık listesinde
        görünmezler.
        """
        ev_x, ev_y = self._ev_x, self._ev_y
        self.bildir("uyari", "── OTOMATİK MARKET TURU ──")

        self.durum_metni = "markete gidiliyor"
        if not self._agdan_yuru(self.ayar.market_x, self.ayar.market_y,
                                durum, "markete yürü"):
            self.bildir("hata", "markete varılamadı — bot durduruldu")
            self.calisiyor = False
            return

        # Dükkânı aç: tıkla + DUR tek segmentte (tek başına 0x1A yetmiyor)
        vid = self.ayar.npc_vid
        if not vid:
            self.bildir("hata", "NPC vid ayarlı değil — satış yapılamaz")
            self.calisiyor = False
            return
        konum = self.api.get("/api/konum") or {}
        d = self.api.get("/api/durum") or durum
        px, py = int(konum.get("x", 0)), int(konum.get("y", 0))
        self.durum_metni = "dükkân açılıyor"
        self._gonder(paket_tikla_tam(vid, px, py, int(d.get("tik", 0)),
                                     int(konum.get("yon", 0) / 5) % 72),
                     "dükkânı aç #%d" % vid)
        time.sleep(1.0)

        bas, son = self.ayar.slot_bas, self.ayar.slot_son
        if son < bas:
            bas, son = son, bas
        self.durum_metni = "satılıyor (%d-%d)" % (bas, son)
        for slot in range(bas, son + 1):
            if not self.calisiyor:
                break
            self._gonder(paket_sat(slot, self.ayar.satis_adet),
                         "SAT slot %d" % slot)
            time.sleep(max(0.05, self.ayar.satis_gecikme / 1000.0))
        self._gonder(paket_dukkan_kapat(), "dükkânı kapat")
        time.sleep(0.5)

        self.durum_metni = "av yerine dönülüyor"
        if ev_x or ev_y:
            self._agdan_yuru(ev_x, ev_y, durum, "av yerine dön")
        self.bildir("bilgi", "── market turu bitti, ava devam ──")

    def _envanter_dolu_mu(self):
        """
        Sunucudan "çok fazla eşya taşıyorsun" benzeri bir SİSTEM uyarısı
        geldi mi?

        Envanteri doğrudan göremiyoruz — sunucu envanter durumunu ayrı bir
        pakette bildirmiyor. Tek göstergemiz 0x04 CHAT'in bType=1 (sistem)
        satırları. Metin CP1254'tür; arama Türkçe-duyarsız yapılır.

        Yalnızca bot başladıktan SONRA gelen uyarılar sayılır; eski
        satırlar botu hemen durdurmasın.
        """
        satirlar = self.api.get("/api/sohbet", n=30, tip=1)
        if not isinstance(satirlar, list) or not satirlar:
            return False
        aranan = self._sadelestir(self.ayar.uyari_metin)
        if not aranan:
            return False
        for s in satirlar:
            t = s.get("zaman", 0)
            if t <= self._son_uyari_zaman:
                continue
            if aranan in self._sadelestir(s.get("metin", "")):
                self._son_uyari_zaman = t
                self.bildir("uyari", "sistem: %s" % s.get("metin", "")[:80])
                return True
        # görülen en yeni damgayı kaydet ki eskiler tekrar taranmasın
        if satirlar:
            self._son_uyari_zaman = max(self._son_uyari_zaman,
                                        max(s.get("zaman", 0) for s in satirlar))
        return False

    def _hedef_sec(self, varliklar, bx, by):
        """
        Hedef seçer. Kilit açıksa mevcut hedefi ölene kadar bırakmaz.

        <b>Neden kilit gerekli:</b> her turda "en yakın"ı seçmek, ışınlanan
        bir botta işe yaramıyor. Hedefin yanına gidince en yakın canavar
        değişiyor, bot yarım bırakıp ona atlıyor, oradan bir başkasına...
        Sonuçta hiçbirini öldürmeden haritada sürükleniyor. Log'da tam bunu
        gördük: Aç Boz Ayı ×18 → Alfa Gri Kurt ×3 → Siyah Ayı ×7 → ...

        <b>Ev noktası:</b> adaylar mevcut konuma değil EV'e göre sınırlanır.
        Yoksa bot her ışınlanmada bulunduğu yerden yeni hedef seçip zincirleme
        uzaklaşıyor.
        """
        simdi = time.time()

        # Ev noktası ilk turda sabitlenir
        if self._ev_x == 0 and self._ev_y == 0:
            self._ev_x, self._ev_y = bx, by

        # 1) Kilitli hedef hâlâ geçerli mi?
        if self.ayar.hedef_kilit and self._kilit_id:
            for v in varliklar:
                if v.get("vid") != self._kilit_id:
                    continue
                # can %0 ÖLÜ DEĞİL — metin hâlâ ayakta olabilir.
                # Kilit yalnızca varlık listeden düşünce ya da ceset
                # takılı kalınca bırakılır (bkz. _olu_sayilir).
                if self._olu_sayilir(v):
                    break
                # kilit_sure = 0 -> SINIRSIZ: ölene kadar dövüş.
                #
                # Süre sınırı, ölümü göremediğimiz varsayımıyla konmuştu.
                # Oysa ölüm ZATEN yakalanıyor: hedefin can'ı 0 olunca ya da
                # varlık listeden düşünce (0x46 ölüm / 0x02 silme) kilit
                # kendiliğinden bırakılıyor — iki satır yukarısı bunu yapıyor.
                # Metin taşları geç kırıldığı için süre sınırı yalnızca
                # yarıda bıraktırıyordu.
                #
                # Emniyet: paket kaçarsa bile APK varlığı 120 sn sonra
                # listeden düşürür (VARLIK_OMRU_MS), kilit o zaman açılır.
                if (self.ayar.kilit_sure > 0
                        and simdi - self._kilit_baslangic > self.ayar.kilit_sure):
                    # Bekleme listesine al, yoksa hemen tekrar seçilir
                    self._bekleyen[self._kilit_id] = simdi + self.ayar.kilit_sure * 2
                    self.bildir("uyari",
                                "hedef %s %d sn'de ölmedi — %d sn atlanacak"
                                % (v.get("ad", "?"), self.ayar.kilit_sure,
                                   self.ayar.kilit_sure * 2))
                    break
                return v                                   # kilit sürüyor
            # buraya düştüysek kilit bitti
            self._kilit_id = 0

        # 2) Yeni hedef: EV'e yakınlık esas
        ev = self.ayar.ev_yaricap
        # süresi dolan bekleme kayıtlarını temizle
        for vid in [k for k, t in self._bekleyen.items() if t < simdi]:
            del self._bekleyen[vid]
        adaylar = []
        for v in varliklar:
            if self._bekleyen.get(v.get("vid"), 0) > simdi:
                continue                               # yakın zamanda bırakıldı
            if self.ayar.basit_hedefleme:
                if not self._hedef_uygun_basit(v, bx, by, self.ayar.tarama):
                    continue
            else:
                if not self._hedef_uygun(v, bx, by, self.ayar.tarama):
                    continue
                if ev > 0 and self._ev_disinda(v, ev):
                    continue                               # av alanının dışı
            adaylar.append(v)
        if not adaylar:
            return None
        adaylar.sort(key=lambda v: mesafe_ham(bx, by, v["x"], v["y"]))
        yeni = adaylar[0]
        if self.ayar.hedef_kilit:
            self._kilit_id = yeni["vid"]
            self._kilit_baslangic = simdi
        return yeni


    def _ev_disinda(self, v, ev):
        """
        Bu hedef av alanının dışında mı?

        SABİT EV NOKTASI ROTAYLA ÇAKIŞIYORDU
        ------------------------------------
        Av alanı, botun BAŞLADIĞI tek bir noktaya göre ölçülüyordu
        (varsayılan yarıçap 80 m). Bu, sabit bir noktada avlanırken
        doğru — ışınlanan bot zincirleme uzaklaşmasın diye konmuştu.

        Ama ROTADA gezerken yanlış: rota başlangıçtan 80 m'den uzağa
        çıktığı anda TÜM hedefler eleniyor, bot rotayı yürüyor ama
        hiçbir şeye saldırmıyordu. Rota + savaş birlikte çalışmıyordu.

        Rota açıkken av alanı artık ROTANIN ÇEVRESİ: hedefin en yakın
        rota noktasına uzaklığı ölçülüyor. Yani "rotanın X metre
        yakınındaki her şeye saldır" demek oluyor — istenen davranış bu.
        """
        hx, hy = v.get("x", 0), v.get("y", 0)
        noktalar = self.ayar.rota
        if self.ayar.rota_gez and noktalar:
            en_yakin = min(mesafe_ham(hx, hy, int(n[0]), int(n[1]))
                           for n in noktalar)
            return en_yakin > ev
        return mesafe_ham(self._ev_x, self._ev_y, hx, hy) > ev

    def _topla(self, bx, by):
        esyalar = self.api.get("/api/esyalar", n=60)
        if not isinstance(esyalar, list) or not esyalar:
            return False
        uygun = [e for e in esyalar if self._esya_uygun(e, bx, by)]
        if not uygun:
            return False
        if self.ayar.yang_oncelik:
            uygun.sort(key=lambda e: (0 if e.get("yang") else 1,
                                      mesafe_ham(bx, by, e["x"], e["y"])))
        else:
            uygun.sort(key=lambda e: mesafe_ham(bx, by, e["x"], e["y"]))

        # OYUNDAKİ TOPLAMA TUŞU GİBİ: yakındaki uygun eşyaların HEPSİNİ birden
        # topla (tek tek değil). Gerçek istemci de tek basışta her vid için
        # 0x0F yolluyor (ölüm kaydında 0f..0f.. art arda görüldü).
        simdi = time.time()
        gonderilen = 0
        for e in uygun[:TOPLA_AZAMI]:
            vid = e.get("vid")
            ad = e.get("ad", "?")
            if not self._gonder(paket_topla(vid), "TOPLA %s #%s" % (ad, vid)):
                continue
            ilk_deneme = vid not in self._toplandi
            self._toplandi[vid] = simdi
            if ilk_deneme:                     # sayaç tekrar denemelerle şişmesin
                self.toplanan += 1
                if e.get("yang"):
                    self.yang_toplanan += 1
            gonderilen += 1
        if gonderilen:
            self.durum_metni = "topluyor: %d eşya" % gonderilen
            self.bildir("topla", "%d eşya toplanıyor" % gonderilen)
        # geçmiş şişmesin: bekleme süresi geçmiş kayıtları at
        if len(self._toplandi) > 400:
            self._toplandi = {v: t for v, t in self._toplandi.items()
                              if simdi - t < TOPLA_BEKLEME}
        time.sleep(0.12)
        return bool(gonderilen)

    def _yetenek_dene(self, vid, ad="?"):
        """
        Süresi geldiyse yeteneği hedefe kullanır.

        NEDEN AYRI BİR YARDIMCI
        -----------------------
        Yetenek paketi yalnızca _saldir içinde gönderiliyordu. Ama
        varsayılan saldırı yolu ÇOKLU HEDEF (_coklu_saldiri) ve orada
        yetenek hiç yoktu: "Yetenek kullan" kutusu işaretlense bile tek
        paket gitmiyordu. İki saldırı yolunun da aynı yardımcıyı
        çağırması bu sessiz boşluğu kapatıyor.

        Aralık (yetenek_ms) ortak: çoklu hedefte her hedefe ayrı yetenek
        atılmaz, geçiş başına bir kez.
        """
        if not self.ayar.yetenek_acik or not vid:
            return False
        simdi = time.time()
        if simdi - self._son_yetenek < self.ayar.yetenek_ms / 1000.0:
            return False
        self._gonder(paket_yetenek(self.ayar.yetenek_vnum, vid),
                     "YETENEK %d → %s #%s"
                     % (self.ayar.yetenek_vnum, ad, vid))
        self._son_yetenek = simdi
        return True

    def _hedefleme_isci_acik(self):
        """Hedefleme vuruş döngüsü şu an çalışıyor mu?"""
        t = self._vurus_is
        return bool(t is not None and t.is_alive() and self.calisiyor
                    and self.ayar.coklu_hedef and not self.ayar.wait_hack)

    def _vurus_bekle(self, sure, nesil):
        """
        Durdur'a ANINDA tepki verecek şekilde bekler.

        Referans döngü düz time.sleep(2) kullanıyordu; Durdur'dan sonra
        2 saniyeye kadar ayakta kalabiliyordu. Burada 50 ms'lik dilimlerle
        bekleniyor.
        """
        son = time.time() + sure
        while time.time() < son:
            if not self.calisiyor or nesil != self._vurus_nesil:
                return False
            time.sleep(min(0.05, max(0.0, son - time.time())))
        return self.calisiyor and nesil == self._vurus_nesil

    def _hedefleme_dongusu(self, nesil):
        """
        HEDEFLEME VURUŞU — masaüstü tambot.py'deki _bot_dongu'nun aynısı.

        NEDEN AYRI İŞ PARÇACIĞI
        -----------------------
        Eskiden vuruş _tur'un bir dalıydı. Aynı turda önce eşya toplama,
        veri çekimi ve rota yürüyüşü çalışıyordu; bunlardan biri sürerken
        hiç vuruş gitmiyordu. Kullanıcı bunu "vuruyor, biraz duruyor,
        tekrar vuruyor" diye tarif etti ve masaüstündeki botun davranışını
        istedi: Başlat'a basınca vursun, Durdur'a basınca dursun.

        Referans (Desktop/tambot.py 439-513) aynen şunu yapıyor:
            konum + varlık listesi çek
            tip, vnum > 0, mesafe < menzil olanları ayır (liste sırasıyla)
            yoksa 0.5 sn bekle
            hız aralığı dolduysa ilk max_hedef hedefe:
                hedefle -> 10 ms -> saldır
            döngü başına 50 ms bekle

        REFERANSTAN BİLEREK AYRILAN TEK YER
        -----------------------------------
        Referansın bot_saldir'ı saldırıya 0x08 KONUM paketi ekliyor
        (hedefin x,y'si). Kullanıcı hedeflemede konum gönderilmemesini
        açıkça istediği için burada yalnızca 02 00 <vid> gidiyor.
        Ölçüm: 0x08 isabeti değiştirmiyor (%92 / %90, 105 örnek).

        BU BOTA UYUM İÇİN EKLENENLER
        ----------------------------
        - Kapılar kapalıysa (proxy bağlı değil vb.) paket denenmez.
        - Konum _konumum'dan: bot rota yürürken ham x,y donuyor.
        - Hedef süzgeci _hedef_uygun_basit — referansın süzgeciyle aynı,
          üstüne rotanın metin sahipliği ve ölü-hedef sabrı.
        - Durdur'a 50 ms içinde tepki.
        """
        son_saldir = 0.0
        while self.calisiyor and nesil == self._vurus_nesil:
            try:
                if (not self.ayar.coklu_hedef or self.ayar.wait_hack
                        or self.ayar.sadece_rota):
                    self._vurus_bekle(0.5, nesil)
                    continue

                durum = self.api.get("/api/durum")
                varliklar = self.api.get("/api/varliklar", n=80)
                if (not isinstance(durum, dict) or not isinstance(varliklar, list)
                        or not varliklar):
                    self._vurus_bekle(2.0, nesil)
                    continue
                if not self.ayar.kuru and not all(self._kapilar(durum).values()):
                    self._vurus_bekle(1.0, nesil)
                    continue
                konum = durum.get("konum") or {}
                if not konum.get("bilinir"):
                    self._vurus_bekle(0.5, nesil)
                    continue
                bx, by, _ = self._konumum(konum)

                yakin = [v for v in varliklar
                         if self._hedef_uygun_basit(v, bx, by, self.ayar.menzil)]
                if not yakin:
                    self._vurus_bekle(0.5, nesil)
                    continue
                self._son_hedef_gorulme = time.time()

                simdi = time.time()
                hiz = self.ayar.vurus_ms / 1000.0
                if simdi - son_saldir >= hiz:
                    hedefler = yakin[:max(1, self.ayar.max_hedef)]
                    self._yetenek_dene(hedefler[0].get("vid"),
                                       hedefler[0].get("ad", "?"))
                    for mob in hedefler:
                        if not self.calisiyor or nesil != self._vurus_nesil:
                            break
                        vid = mob["vid"]
                        self._hedefi_not_et(vid)
                        self._gonder(paket_hedef(vid), "HEDEFLE #%s" % vid)
                        time.sleep(0.01)
                        self._gonder(paket_saldiri(vid),
                                     "SALDIR %s #%s" % (mob.get("ad", "?"), vid))
                    son_saldir = simdi
                    self._son_vurus = time.time()
                    self.durum_metni = "%d hedefe saldırı" % len(hedefler)
                    if simdi - self._vurus_log > 2.0:
                        self._vurus_log = simdi
                        self.bildir("bilgi", "%d hedefe saldırı — en yakın: %s"
                                    % (len(hedefler), hedefler[0].get("ad", "?")))
                self._vurus_bekle(0.05, nesil)
            except Exception as e:                    # noqa: BLE001
                self.bildir("hata", "vuruş döngüsü hatası: %s: %s"
                            % (type(e).__name__, e))
                self._vurus_bekle(1.0, nesil)

    def _coklu_saldiri(self, adaylar, bx, by):
        """
        ÇOKLU HEDEF saldırısı — eski BotPanel mantığı.

        Tek hedefe kilitlenmek yerine menzildeki EN YAKIN N canavara sırayla
        vurur. Kullanıcının ölçtüğü davranış bu: hasar yayılıyor, sürü
        halinde geliyorlar ve toplu düşüyorlar.

        Her hedef için iki ayrı enjeksiyon:
            3D | vid                          hedefle
            02 00 | vid | 08 0F 00 | vid|x|y  saldır + konum senkronu

        İkinci pakette taşınan koordinat HEDEFİN konumudur (bizimki değil).
        Gerçek istemci de saldırırken bu ikisini birlikte gönderiyor —
        yakalamada 1648 saldırı segmentinin hepsi 21 bayttı.
        """
        simdi = time.time()
        if simdi - self._son_vurus < self.ayar.vurus_ms / 1000.0:
            time.sleep(0.02)
            return
        hedefler = adaylar[:max(1, self.ayar.max_hedef)]
        # YETENEK: geçiş başına bir kez, EN YAKIN hedefe.
        # Alan etkili yetenekler zaten çevreyi vuruyor; her hedefe ayrı
        # atmak hem gereksiz hem de aralık ayarını anlamsız kılardı.
        if hedefler:
            self._yetenek_dene(hedefler[0].get("vid"),
                               hedefler[0].get("ad", "?"))
        for h in hedefler:
            if not self.calisiyor:
                break
            vid = h["vid"]
            self._hedefi_not_et(vid)
            # METİN TIKLAMASI (0x1A) DA GÖNDERİLMİYOR.
            #
            # Görünürde saldırıyla ilgisiz bir "tıklama" paketiydi ama
            # paket_tikla_tam'ın içinde 0x07 HAREKET paketi var
            # (bFunc=0, bizim x,y'miz). Yani konum senkronunu 0x08'den
            # çıkarmak yetmiyordu: konum buradan gitmeye devam ediyordu.
            #
            # Saldırı yolu artık SALT hedefle+saldır.
            # HEDEF BAŞINA TEK VURUŞ — içeride seri YOK.
            #
            # Eskiden burada her hedef için vurus_seri kadar vuruş
            # gönderiliyor ve aralarında vurus_ms uyunuyordu. 10 hedefle
            # bu, bir geçişi saniyelere çıkarıyordu: 10 x 5 = 50 HTTP
            # isteği artı ~1.5 sn uyku. Dışarıdan görünen "10 tane
            # gönderip duruyor" buydu — ilk hedef, sıra ona yeniden
            # gelene kadar saniyelerce vuruş almıyordu.
            #
            # Geçişin kendisi zaten çok paket gönderiyor; asıl istenen
            # geçişin HIZLI bitip yeniden başlaması. Seri, tek hedefe
            # vurulan _saldir yolunda duruyor — orada döngü hızına
            # bağımlılığı gerçekten kırıyor.
            # KONUM SENKRONU (0x08) GÖNDERİLMİYOR.
            #
            # Ölçüldü (6 Eyl 2026, 105 örnek, 3 m içinde):
            #     hedefle+saldır          %92 isabet
            #     hedefle+saldır+konum    %90 isabet
            # Fark yok — 0x08 sunucunun saldırıyı kabul etmesinde rol
            # oynamıyor, yalnızca her vuruşa 15 bayt ekliyordu.
            #
            # KARŞI KANIT (kayda geçsin): gerçek istemcinin pcap'inde
            # 1826 saldırının 1711'i (%94) hemen ardından 0x08
            # gönderiyor. Yani bu biçim istemciden AYRILIYOR. İşleyiş
            # için gerek yok, ama "gerçek istemci gibi görün" ölçütüne
            # göre bir geri adım.
            self._gonder(paket_hedef(vid), "HEDEFLE #%s" % vid)
            self._gonder(paket_saldiri(vid),
                         "SALDIR %s #%s" % (h.get("ad", "?"), vid))
        self._son_vurus = simdi
        self.durum_metni = "%d hedefe saldırı" % len(hedefler)
        # GÜNLÜĞÜ BOĞMA.
        #
        # Her vuruşta satır basılıyordu; saniyede 6-8 vuruşla günlük
        # okunmaz hale geliyor ve arasındaki gerçek olaylar (tıklama,
        # onay, uyarı) kayboluyordu. Artık yalnızca hedef kümesi
        # değişince ya da 5 saniyede bir yazılıyor.
        if hedefler:
            imza = tuple(sorted(h.get("vid") for h in hedefler))
            if (imza != self._son_saldiri_imza
                    or simdi - self._son_saldiri_log > 5.0):
                self._son_saldiri_imza = imza
                self._son_saldiri_log = simdi
                self.bildir("bilgi", "%d hedefe saldırı — en yakın: %s"
                            % (len(hedefler), hedefler[0].get("ad", "?")))
        # isabet takibi ilk hedef üzerinden
        if hedefler and hedefler[0]["vid"] != self._son_hedef_id:
            self._son_hedef_id = hedefler[0]["vid"]
            self._son_hedef_can = hedefler[0].get("can", -1)

    def _metin_saldirisi(self, metin, bx, by):
        """
        METİNE VUR — seçim paketi, sonra saldırı düğmesi.

        TEK YOL
        -------
        Metinin vid'i zaten elimizde ve yanına kadar yürüyoruz. Seçimi
        paketle göndermek (0x3D) mümkünken ekranda "yazı nerede" diye
        aramanın hiçbir gereği yok.

        Eskiden burada üç ayrı nişan alma yöntemi vardı — kalibrasyon,
        OCR, beyaz etiket bulma — ve üçü de aynı soruyu çözmeye
        çalışıyordu: "hangi piksele basayım". Hepsi DEĞİŞKEN bir hedefe
        nişan alıyordu (metin kameraya göre her karede başka yerde) ve
        hiçbiri güvenilir olmadı. Saldırı düğmesi ise SABİT: bir kez
        kaydedilir, bir daha şaşmaz.

        Düğme kayıtlı değilse eski paket yoluna düşülür — özellik
        kurulmamış diye bot metinsiz kalmasın.

            python tools/saldiri_dugmesi.py
        """
        vid = metin.get("vid")
        if not vid:
            return

        # DÜĞME VE PAKET BİRLİKTE.
        #
        # Bir süre yalnızca düğme denendi: günlük "saldırı düğmesine 5x
        # basıldı" ile doluyor ama hızlı vuruş (7x paket) hiç açılmıyordu.
        # İstemcinin kendi vuruş hızı bota göre yavaş kalıyor.
        #
        # Artık ikisi de var: düğme seçimi/vuruşu İSTEMCİYE başlatıyor,
        # paketler hızı veriyor. Düğme her turda değil, aralıkla basılıyor
        # — 5 basış ~1.1 sn sürüyor ve her turda yapılırsa paketlerin
        # önünü tıkıyordu.
        if (self.ayar.metin_paket_secim
                and (self.ayar.saldiri_dugme_x
                     or self.ayar.saldiri_dugme_y)):
            self._metin_secip_dugmeye_bas(metin)
        elif self.ayar.metin_paket_secim:
            self._hizala_sustur(
                "dugme yok",
                "saldırı düğmesi KAYITLI DEĞİL — metine paketle "
                "vuruluyor. python tools/saldiri_dugmesi.py ile "
                "düğmenin yerini kaydedebilirsin.")

        # HIZLI VURUŞ — düğmeye basılmış olsun ya da olmasın.
        # _saldir kendi aralığını (vurus_ms) uyguluyor.
        #
        # Hedefleme döngüsü çalışıyorsa metine o vuruyor (düğmeye
        # basıldıktan sonra metin onun listesine giriyor); burada da
        # vurmak aynı metine iki kat paket demek.
        if not self._hedefleme_isci_acik():
            self._saldir(metin)

    # Seçim paketi gönderildikten sonra istemcinin hedefi almasını kaç
    # saniye bekleyeceğiz. ÖLÇÜLDÜ, tahmin değil: 94-150 ms (ortanca
    # 123), 6/6 başarı — frida/okuma_modu.py. Üstüne pay bırakıldı.
    SECIM_GECIKMESI = 0.25

    def _metin_secip_dugmeye_bas(self, metin):
        """
        Metini SEÇER ve saldırı düğmesine basar.

        Bu, vuruşu İSTEMCİYE başlatan adım. Hızı paketler veriyor
        (bkz. _metin_saldirisi -> _saldir); burası yalnızca istemcinin
        de saldırıda olmasını sağlıyor.

        Her turda basılmıyor: 5 basış ~1.1 sn sürüyor ve turu bu kadar
        bloklamak hızlı vuruşu boğuyordu. İstemci saldırıya bir kez
        başlayınca zaten kendi kendine vuruyor, aralıkla tazelemek
        yetiyor.

        Döner: bu turda düğmeye basıldıysa True.
        """
        vid = metin.get("vid")
        if not vid:
            return False
        d = self._metin_tik.setdefault(vid, {})
        # METİN BAŞINA BİR KEZ.
        #
        # İstemci saldırıya bir kez başlayınca kendi kendine vurmaya
        # devam ediyor; tazelemeye gerek yok. Aralıkla basmak günlüğü
        # doldurup her seferinde turu ~1.1 sn blokluyordu.
        if d.get("dugme_bas"):
            return False

        self._gonder(paket_hedef(vid), "HEDEF SEÇ %s #%s"
                     % (metin.get("ad", "?"), vid))

        # SEÇİMİN İSTEMCİYE VARMASINI BEKLE.
        #
        # 6 Eyl 2026'da Frida ile İSTEMCİNİN BELLEĞİNDEN ölçüldü
        # (frida/okuma_modu.py). Enjekte ettiğimiz 0x3D istemcinin kendi
        # m_dwTargetVID alanını GERÇEKTEN değiştiriyor — ama hemen değil:
        # paket sunucuya gidiyor, sunucu istemciye hedef paketi yolluyor,
        # istemci onu işleyince alan doluyor. 6/6 denemede tuttu,
        # gecikme 94-150 ms (ortanca 123).
        #
        # Beklemeden basınca İLK basış istemci daha hedefi almadan
        # düşüyordu: düğme o an neyi seçiliyse ona vuruyordu. Sahada
        # "seçtiğimiz metine vurmuyor" diye görülen şey buydu.
        time.sleep(self.SECIM_GECIKMESI)

        if not self._saldiri_dugmesine_bas():
            return False
        d["dugme_bas"] = d.get("dugme_bas", 0) + 1
        self._metin_zamani = time.time()
        return True

    def _saldiri_dugmesine_bas(self, adet=None):
        """
        Sağ alttaki SALDIRI DÜĞMESİNE basar.

        NEDEN BU YOL
        ------------
        Metine nişan almak için üç ayrı yöntem denendi (kalibrasyon, OCR,
        etiket bulma) ve hepsi DEĞİŞKEN bir hedefe nişan alıyordu: metin
        ekranda her karede başka yerde.

        Oysa saldırı düğmesi SABİT. 2 Eyl 2026'da ölçüldü ki dokunma
        boru hattı sağlam ve bir isme dokununca oyunun seçili hedefi
        gerçekten değişiyor. Öyleyse iş ikiye ayrılıyor:

            1. metini SEÇ   (tek dokunuş — nişan yalnızca burada gerek)
            2. DÜĞMEYE BAS  (sabit yer, nişan yok)

        Vuruşlar istemcinin kendi zamanlamasıyla gidiyor, yani dışarıdan
        doğal görünüyor — paket enjekte etmenin aksine.

        Düğme yeri bir kez kaydedilir: python tools/saldiri_dugmesi.py
        """
        dx = int(self.ayar.saldiri_dugme_x)
        dy = int(self.ayar.saldiri_dugme_y)
        if not (dx or dy):
            self._hizala_sustur(
                "saldiri dugmesi",
                "saldırı düğmesinin yeri kayıtlı değil — "
                "python tools/saldiri_dugmesi.py ile bir kez kaydet")
            return False
        adet = adet if adet is not None else self.ayar.saldiri_basma
        adet = max(1, min(20, int(adet)))
        basildi = 0
        for i in range(adet):
            if not self.calisiyor:
                break
            if self.api.dokun(dx, dy):
                basildi += 1
            if i + 1 < adet:
                time.sleep(max(0.05, self.ayar.saldiri_basma_ms / 1000.0))
        if basildi:
            self.bildir("bilgi", "saldırı düğmesine %dx basıldı (%d, %d)"
                        % (basildi, dx, dy))
        return basildi > 0

    def _oyuncu_vur_dene(self, varliklar, bx, by):
        """
        PvP — saldırılabilir OYUNCULARA çok yavaş vur (hile belli olmasın).

        Canavar saldırısı vurus_ms (çok hızlı) ile gider; oyuncu saldırısı
        AYRI bir aralıkla (oyuncu_vurus_ms, ms cinsinden; varsayılan 500) tek
        vuruş atar. Kendimizi ve sahibi (oyuncu_adi) asla hedeflemez.
        Saldırılamayan oyuncuya paket gitse de sunucu yok sayar (zararsız).
        """
        if not self.ayar.oyuncu_vur:
            return
        simdi = time.time()
        if simdi - self._son_oyuncu_vurus < self.ayar.oyuncu_vurus_ms / 1000.0:
            return
        benim = self._sadelestir(self.ayar.oyuncu_adi)
        aday, aday_uz = None, None
        for v in varliklar:
            if v.get("tip") != TIP_OYUNCU:
                continue
            if self._kendi_vid and v.get("vid") == self._kendi_vid:
                continue                                   # kendimiz
            if benim and self._sadelestir(v.get("ad", "")) == benim:
                continue                                   # sahibimiz
            uz = mesafe_ham(bx, by, v.get("x", 0), v.get("y", 0))
            if uz > self.ayar.oyuncu_menzil:
                continue
            if aday is None or uz < aday_uz:
                aday, aday_uz = v, uz
        if aday is None:
            return
        self._son_oyuncu_vurus = simdi
        vid = aday["vid"]
        self._gonder(paket_hedef(vid) + paket_saldiri(vid),
                     "OYUNCU VUR %s #%s (yavaş)" % (aday.get("ad", "?"), vid))
        if simdi - self._oyuncu_vur_log > 3.0:
            self._oyuncu_vur_log = simdi
            self.bildir("bilgi", "oyuncuya yavaş saldırı: %s (%.0f m) — %.1f sn'de bir"
                        % (aday.get("ad", "?"), aday_uz / 100.0,
                           self.ayar.oyuncu_vurus_ms / 1000.0))

    def _saldir(self, hedef):
        simdi = time.time()
        aralik = self.ayar.vurus_ms / 1000.0
        kalan = aralik - (simdi - self._son_vurus)
        if kalan > 0:
            # KALAN kadar uyu, sabit 30 ms değil.
            #
            # Eskiden burada sabit time.sleep(0.03) vardı: vurus_ms 50'ye
            # ayarlansa bile tur başına tek vuruş gidiyor, üstüne 30 ms
            # uyku ve iki HTTP gidiş-dönüşü biniyordu. Gerçek hız ayarın
            # çok altında kalıyordu.
            time.sleep(min(kalan, 0.05))
            return
        vid = hedef["vid"]
        ad = hedef.get("ad", "?")
        self._hedefi_not_et(vid)
        self.durum_metni = "saldırıyor: %s" % ad
        if vid != self._son_hedef_id:
            self._son_hedef_id = vid
            self._son_hedef_can = hedef.get("can", -1)

        # METİN TIKLAMASI (0x1A) GÖNDERİLMİYOR.
        #
        # paket_tikla_tam görünürde "tıklama"ydı ama içinde 0x07 HAREKET
        # paketi taşıyordu (bFunc=0, bizim x,y'miz). Saldırıdan konumu
        # çıkarmak istendiğinde 0x08'i kaldırmak yetmedi; konum buradan
        # gitmeye devam ediyordu.
        #
        # paket_tikla_tam duruyor: NPC dükkânı için GEREKLİ olduğu canlı
        # denemeyle bulunmuştu (yalnız 0x1A ile dükkân açılmıyor).
        # Kaldırılan yalnızca SALDIRI yolundaki kullanımı.

        # Hedefle + saldır TEK pakette. Konum senkronu (0x08) YOK.
        #
        # Bu yorum bir süre koddan ayrı düşmüştü: "BİLEREK yok" diyordu
        # ama kod onu gönderiyordu. Artık ikisi de aynı şeyi söylüyor
        # (gerekçe _coklu_saldiri'de ölçümle birlikte yazılı).
        #
        # SERİ VURUŞ: tur başına tek paket, ana döngünün hızına
        # bağımlıydı (iki HTTP gidiş-dönüşü + uyku). vurus_ms 50 olsa da
        # gerçek aralık çok daha büyük kalıyordu. Seri, vuruş hızını
        # döngüden ayırıyor: tek turda birkaç vuruş, aralarında tam
        # vurus_ms kadar bekleme.
        dizi = paket_hedef(vid) + paket_saldiri(vid)
        adet = max(1, min(20, self.ayar.vurus_seri))
        for i in range(adet):
            if i:
                time.sleep(aralik)
                if not self.calisiyor:
                    break
            self._gonder(dizi, "SALDIR %s #%s" % (ad, vid))
        self._son_vurus = time.time()

        self._yetenek_dene(vid, ad)
        time.sleep(0.03)

    def _istemci_son_hareket(self):
        """
        İstemcinin (BOT'un değil) son kendi hareketinden bu yana geçen süre,
        saniye cinsinden. Bilinemezse None.

        <b>Doğrudan APK'dan okunur</b> (`/api/konum` → `istemciHareketYas`).
        Yaş telefonun kendi saatiyle hesaplandığı için PC–telefon saat farkı
        (ölçüldü: 111 saniye) burada hiç devreye girmez.

        Önceki iki deneme neden başarısızdı:
          1) /api/log'daki zaman damgasını PC saatiyle karşılaştırmak —
             111 sn fark yüzünden sonuç hep negatif çıkıp 0'a kırpılıyor,
             her seferinde sahte "taze pencere" veriyordu.
          2) Saat farkı düzeltilse bile bot saniyede ~8 paket enjekte ediyor;
             bunlar tcpdump üzerinden günlük halkasına düşüp istemcinin
             paketini listeden atıyordu → "ritim okunamadı".
        """
        k = self.api.get("/api/konum")
        if not isinstance(k, dict):
            return None
        yas = k.get("istemciHareketYas", -1)
        if not isinstance(yas, (int, float)) or yas < 0:
            return None
        return yas / 1000.0

    def _pencere_bekle(self):
        """
        Wait-hack'i istemcinin SESSİZ anına denk getirir.

        Neden gerekli — 29 Ağu 2026 ölçümü:
          • Sunucu kendi hareketimizi bize GERİ YOLLAMIYOR
            (859 gelen 0x03'ün sıfırı bizim vid'imizi taşıyor).
          • İstemci kendi konumunu sürekli tekrar bildiriyor.
            Yürürken her ~161 ms, dururken medyan 343 ms — ama %90'ı
            1204 ms'ye, en uzunu 7.5 sn'ye kadar çıkıyor.
          • Dolayısıyla enjekte edilen konum, istemcinin bir sonraki
            paketine kadar yaşıyor. Rastgele zamanlamada bu pencerenin
            ortasına düşme ihtimali yarı yarıya.

        Strateji: istemci yeni bir 0x07 gönderdiyse hemen ateşle (önümüzde
        tam pencere var). Uzun süredir sessizse zaten boştayız, yine ateşle.
        Arada kaldıysak kısa süre bekleyip tekrar bak.

        @return açıklama metni (log için)
        """
        if not self.ayar.wh_pencere:
            return "pencere kapalı"
        sinir = time.time() + self.ayar.wh_bekleme_ms / 1000.0
        while time.time() < sinir and self.calisiyor:
            gecen = self._istemci_son_hareket()
            if gecen is None:
                return "ritim okunamadı"
            if gecen < 0.08:
                self._pencere_taze += 1
                return "taze pencere (%.0f ms önce)" % (gecen * 1000)
            if gecen > 0.45:
                self._pencere_bos += 1
                return "istemci sessiz (%.1f sn)" % gecen
            time.sleep(0.03)
        self._pencere_kacti += 1
        return "pencere bulunamadı (zorla)"

    def _wait_hack(self, hedef, bx, by, tik):
        """
        Hedefin yanına ışınlan ve vur.

        wh_donus açıksa eski konuma geri döner (klasik wait-hack:
        yerinden oynamadan uzaktakine vurmak). Kapalıysa karakter hedefin
        yanında kalır — bu durumda zaten normal saldırı menzilindeyiz,
        sunucunun mesafe denetimine takılma ihtimali ortadan kalkar.
        """
        pencere = self._pencere_bekle()
        self._son_pencere = pencere
        hx, hy = hedef["x"], hedef["y"]
        ad = hedef.get("ad", "?")
        self._hedefi_not_et(hedef["vid"])
        self.durum_metni = "wait-hack: %s" % ad
        if hedef["vid"] != self._son_hedef_id:
            self._son_hedef_id = hedef["vid"]
            self._son_hedef_can = hedef.get("can", -1)
        yb = yon_bayti(hx - bx, hy - by)
        vid = hedef["vid"]

        # ── Dizinin TAMAMI tek pakette ──
        #
        # Eskiden bunlar 4 ayrı /api/enjekte çağrısıydı, aralarında uyku
        # vardı: toplam 100–150 ms. O süre boyunca istemci kendi 0x07'sini
        # gönderirse sunucu bizi geri çekiyor ve saldırı boşa gidiyordu —
        # "bazen kaçırıyor"un sebebi buydu.
        #
        # Tek hex bloğu olarak gönderilince APK bunu tek write() ile sokete
        # basar; dört paket sunucuya tek TCP segmentinde, aralarında hiç
        # boşluk olmadan varır. İstemcinin araya girme ihtimali kalmaz.
        # ── Yalnızca HEDEFLE + SALDIR ──
        #
        # Konum taşıyan iki paket de çıkarıldı:
        #   0x07 (yürü)  — sunucu ışınlamıyor, yürüterek götürüyor; saldırı
        #                  anında hedefe varılmış olmuyor.
        #   0x08 (konum) — gerçek istemci saldırıya bunu ekliyor ama burada
        #                  eklendiğinde saldırı çalışmıyordu.
        #
        # Kalan 11 bayt bulunduğumuz yerden vurur; sunucu mesafeyi kendi
        # bildiği konuma göre değerlendirir.
        # ── ÇALIŞAN DİZİ — 42 bayt ──
        #
        #   07 (16)  hedefin konumuna yürü
        #   3D (5)   hedefle
        #   02 (6)   saldır
        #   08 (15)  konum senkronu (hedefin koordinatı)
        #
        # Hareket paketi wait-hack'in TA KENDİSİDİR, opsiyonel değildir.
        # Bir ara "saldırıya konum koyma" isteği bu yola da uygulanmış ve
        # wait-hack normal saldırıya dönüşmüştü; o istek ÇOKLU SALDIRI
        # yolu içindi, burası için değil.
        dizi = (paket_hareket(hx, hy, tik, bfunc=1, brot=yb)
                + (paket_hareket(hx, hy, tik, bfunc=0, brot=yb)
                   if self.ayar.wh_dur_paketi else b"")
                + paket_hedef(vid)
                + paket_saldiri(vid)
                + paket_toplu_konum([(vid, hx, hy)]))
        if self.ayar.wh_donus:
            # Eski konuma dön: yerinden oynamadan uzaktakine vurmak için.
            # Kapalıyken karakter hedefin yanında KALIR — o zaman zaten normal
            # saldırı menzilindeyiz, sunucunun mesafe denetimine takılmayız.
            dizi += (paket_hareket(bx, by, tik, bfunc=1,
                                   brot=yon_bayti(bx - hx, by - hy))
                     + paket_hareket(bx, by, tik, bfunc=0))

        self._istemciyi_hizala(hx, hy)
        self.bildir("bilgi", "WH → %s  [%s]  %d bayt tek atış"
                    % (ad, pencere, len(dizi)))
        self._gonder(dizi, "WH dizi → %s (#%s)" % (ad, vid))

        self._son_vurus = time.time()
        time.sleep(max(0.05, self.ayar.vurus_ms / 1000.0))

    def _harita(self, x, y):
        """Bu konumun engel haritası. Veri yoksa None."""
        if not self.ayar.duvar_kacin:
            return None
        if self._dunya is None:
            try:
                from harita_engel import Dunya
                self._dunya = Dunya.yukle()
            except Exception as e:
                self.bildir("uyari", "engel haritası yüklenemedi: %s" % e)
                self._dunya = False
            if self._dunya:
                self.bildir("bilgi",
                            "engel haritası yüklendi: %s"
                            % ", ".join(sorted(self._dunya.haritalar)))
            elif self._dunya is not False:
                self.bildir("uyari",
                            "engel haritası boş — python tools/"
                            "harita_cikar.py ve harita_hizala.py çalıştır")
        if not self._dunya:
            return None
        return self._dunya.hangi(x, y)

    def _duvarsiz_hedef(self, bx, by, hx, hy):
        """
        Hedefe düz gidilemiyorsa ARA NOKTA verir.

        NEDEN GEREKLİ
        -------------
        Sunucu enjekte ettiğimiz hareketi kabul edip bizi duvarın içinden
        geçiriyor, istemci geçmiyor. Sonuç: sunucuda bir yerdeyiz,
        ekranda başka yerde. Sahada "sunucu gitse de istemci gitmiyor"
        diye görüldü.

        Elimizde artık oyunun KENDİ çarpışma verisi var (harita/ dizini,
        tools/harita_cikar.py). Bacağın önü kapalıysa A* ile dolanılır.

        HATA DURUMUNDA ESKİ DAVRANIŞ
        ----------------------------
        Harita yoksa, hiza yoksa ya da yol bulunamazsa hedef olduğu gibi
        döner — yani bot en kötü ihtimalle eskisi kadar iyi çalışır.
        Yanlış bir duvar verisi yüzünden botun durması, duvara girmesinden
        daha kötü olurdu.
        """
        h = self._harita(bx, by)
        if h is None:
            return hx, hy

        if h.gorus_acik(bx, by, hx, hy):
            # Önü açık: önbelleği bırak, doğrudan git.
            self._yol_hedef = None
            self._yol = []
            return hx, hy

        # Aynı hedef için hesaplanmış yol varsa onu sürdür.
        if self._yol_hedef == (hx, hy) and self._yol:
            while self._yol and mesafe_ham(bx, by, self._yol[0][0],
                                           self._yol[0][1]) < 150:
                self._yol.pop(0)
            if self._yol and h.gorus_acik(bx, by, self._yol[0][0],
                                          self._yol[0][1]):
                return self._yol[0]

        yol = h.yol_bul(bx, by, hx, hy,
                        yaricap=max(0, self.ayar.duvar_payi))
        if not yol:
            self._yol_hedef = None
            self._yol = []
            self._hizala_sustur(
                "yol yok",
                "hedefe yol bulunamadı (%.0f, %.0f) — duvarın arkasında "
                "olabilir. Düz çizgiyle deneniyor."
                % (hx / 100.0, -hy / 100.0))
            return hx, hy

        self._yol_hedef = (hx, hy)
        self._yol = list(yol)
        self.bildir("bilgi",
                    "duvar var — %d ara noktayla dolanılıyor (%s)"
                    % (len(yol), h.ad))
        return self._yol[0]

    def _yuru(self, hx, hy, durum, aciklama, tam=False):
        """
        Hedefe doğru yürür — GERÇEK İSTEMCİNİN RİTMİYLE.

        NASIL YÜRÜR GERÇEK İSTEMCİ
        --------------------------
        21 Ağu 2026 kaydındaki 85 giden 0x07 paketi ölçüldü
        (tools/giden_hareket_deseni.py). Desen çok net:

            #    Δt(ms)  func  rot   x        y        Δmesafe  hız
            2    178     1     68    935994   263399   69       387
            3    161     1     68    935968   263472   77       481
            4    165     1     68    935944   263537   69       419
            5    152     1     68    935918   263610   77       510
            ...
            11   67      0     69    935817   263990   39       580  <- DUR

            paketler arası süre  : ortanca 155 ms  (%99'u 1 sn'den kısa)
            paketler arası mesafe: ortanca  70 ham
            bFunc                : yürürken 1 (81 paket), dururken 0 (4)

        Yani istemci tek bir "şuraya git" paketi YOLLAMAZ. Her ~155 ms'de
        bir, ~70 ham ilerlemiş yeni bir konumla AKAN paket dizisi yollar.

        BOTUN ESKİ HALİ NEDEN "BOT GİBİ" GÖRÜNÜYORDU
        --------------------------------------------
        Bot tek bir uzak hedef yolluyor, sunucu bizi oraya yürütüyor,
        VARIYORUZ ve DURUYORUZ; sonra bot bir sonrakini yolluyor. Dışarıdan
        bakan yürü-dur-yürü-dur görüyordu. Bekleme oranıyla oynamak bunu
        çözmedi çünkü sorun bekleme değil, PAKET SAYISIYDI: bir bacak için
        1 paket yerine 12 paket olmalı.

        Artık yol adımlara bölünüp aynı ritimde akıtılıyor. İstemci
        hizalaması da aynı adımlara biniyor — ayrıca senkron döngüsü
        gerekmiyor.
        """
        tik = int(durum.get("tik", 0))
        konum = durum.get("konum") or {}
        # İKİ AYRI KONUM, iki ayrı iş:
        #
        #  bx,by  — SUNUCUDA neredeyiz (ölü hesap). Hareket paketleri buradan
        #           hesaplanır; ham x,y bot kendi yürürken donduğu için tek
        #           başına kullanılamaz.
        #
        #  cx,cy  — İSTEMCİ kendini nerede sanıyor (ham x,y). İstemci
        #           hizalaması BURADAN başlamalı; ölü hesaptan başlatırsak
        #           istemciye bulunduğu yerden çok uzakta bir şerit göndermiş
        #           oluruz ve istemci o sıçramayı yutmaz.
        bx, by, _ = self._konumum(konum)
        cx, cy = self._istemci_konumu(konum, bx, by)
        # DUVAR DENETİMİ, bacak bölünmeden ÖNCE.
        #
        # Bölünmüş kısa bacağa bakmak yetmez: 120 m ötedeki hedefin önü
        # kapalıyken ilk 20 m açık olabiliyor. O zaman bot duvara doğru
        # yürüyüp burnunu dayıyor. Kaçınma tam hedefe göre yapılmalı.
        hx, hy = self._duvarsiz_hedef(bx, by, hx, hy)
        uzak = mesafe_ham(bx, by, hx, hy)
        adim = max(500, self.ayar.adim_mesafe)

        if uzak > adim:
            # Sınırı aşan yolu böl: yalnızca "adim" kadar ilerle
            oran = adim / uzak
            hx = int(bx + (hx - bx) * oran)
            hy = int(by + (hy - by) * oran)
            uzak = adim
            aciklama += " [adım %.0f m]" % (adim / 100.0)

        if uzak < 1:
            return

        yb = yon_bayti(hx - bx, hy - by)
        self.durum_metni = aciklama

        # Akış parametreleri — gerçek istemciden ölçülen değerler
        aralik_ms = max(50, min(1000, self.ayar.akis_aralik_ms))
        hiz = max(50.0, float(self.ayar.yurume_hizi))
        adim_ham = max(10.0, hiz * aralik_ms / 1000.0)
        sayi = max(1, int(math.ceil(uzak / adim_ham)))

        # Son adımı atlayıp erken dön: sıradaki hedef, bu bacak bitmeden
        # yola çıkar ve sunucu yürüyüşü kesmeden sürdürür.
        # TAM yürüyüş: son yaklaşmada yolun tamamı yürünür.
        #
        # Normalde yolun %85'inde durup sıradaki bacağı erken başlatıyoruz
        # (kesintisizlik için). Ama hedefe SON yaklaşmada bu yanlış: %15
        # eksik kalıyor ve bot vuruş alanının dışında kalabiliyor.
        oran = (1.0 if tam
                else min(1.0, max(0.3, self.ayar.erken_donus / 100.0)))
        gonderilecek = max(1, int(round(sayi * oran)))

        istemciye = (self.ayar.istemci_hizala
                     and self.ayar.hizala_yontem == "senkron")

        # ZAMAN GÜDÜMLÜ AKIŞ — adım güdümlü değil.
        #
        # 29 Ağu 2026 ölçümü (tools ile pcap karşılaştırması) şunu gösterdi:
        #
        #     gerçek geçen süre    gönderdiğimiz dwTime artışı
        #     BOT           210 ms   hep tam 155      <- YANLIŞ
        #     GERÇEK OYUNCU 150 ms   149
        #     GERÇEK OYUNCU 1683 ms  1650
        #
        # Gerçek istemcinin dwTime'ı gerçek zamanla birebir ilerliyor.
        # Bizimki her pakette sabit "aralik_ms" sayıyordu; oysa bir tur
        # sleep + enjeksiyon HTTP'si ~210 ms sürüyor. Saatimiz her pakette
        # ~55 ms geri kalıyor, bacak sonunda /api/durum'dan tazelenince
        # 741-818 ms ileri sıçrıyordu. Testere dişi bir zaman çizgisi.
        #
        # Sunucu hareket hızını dwTime farkından denetler; saat böyle
        # savrulunca bizi kâh geçiriyor kâh tutuyor — dışarıdan yürü-dur
        # olarak görünen buydu. Paket akışında hiç boşluk yoktu (en büyük
        # 235 ms), sorun akışta değil ZAMANDAYDI.
        #
        # Artık hem konum hem dwTime GERÇEK saatten türetiliyor.
        toplam_sure = uzak / hiz                      # saniye
        hizala_aralik = self._hizalama_araligi()
        son_hizalama = 0.0
        t0 = time.monotonic()
        son_t = 0.0
        adim_sayaci = 0
        while self.calisiyor:
            dongu_basi = time.monotonic()
            gecen = dongu_basi - t0
            t = 1.0 if toplam_sure <= 0 else min(1.0, gecen / toplam_sure)
            # Eşiği aştıysak son paketi TAM eşikte yollayıp çıkarız.
            #
            # Eskiden burada "t > oran ise break" vardı. tam=True iken
            # oran 1.0 ve t de min(1.0, ...) ile 1.0'da kapandığı için
            # koşul HİÇ sağlanmıyordu: sonsuz döngü. Son yaklaşmada bot
            # kilitleniyordu.
            if t >= oran:
                t = oran
                bitti = True
            else:
                bitti = False
            adim_sayaci += 1
            ax = int(bx + (hx - bx) * t)
            ay = int(by + (hy - by) * t)
            self._gonder(paket_hareket(ax, ay, tik + int(gecen * 1000.0),
                                       bfunc=1, brot=yb), aciklama)
            if istemciye and hizala_aralik > 0:
                yol_alinan = uzak * t
                if yol_alinan - son_hizalama >= hizala_aralik:
                    son_hizalama = yol_alinan
                    self._istemciyi_hizala(
                        int(cx + (hx - cx) * t), int(cy + (hy - cy) * t))
            son_t = t
            if bitti:
                break
            # MENZİLE HEDEF GİRDİ: rota bacağını yarıda kes.
            #
            # Vuruş ayrı iş parçacığında sürüyor; yürümeye devam edersek
            # dövdüğümüz canavardan uzaklaşıp vuruşları menzil dışına
            # düşürüyorduk. Son yaklaşma (tam=True) kesilmez — metine
            # varmak zorundayız.
            if (not tam and self._hedefleme_isci_acik()
                    and time.time() - self._son_hedef_gorulme < 0.3):
                self.durum_metni = "yürüyüş kesildi — menzilde hedef var"
                break
            # Ritmi TUTTUR: geçen işlem süresini düş, yoksa aralık şişer.
            uyu = aralik_ms / 1000.0 - (time.monotonic() - dongu_basi)
            if uyu > 0:
                time.sleep(uyu)
        if not self.calisiyor:
            return

        # Bacak sonu hizalaması: her iki yöntemde de bir kez.
        # Yürüyüş yarıda kesildiyse gidilen yere hizala, bacak sonuna değil.
        if self.ayar.istemci_hizala:
            self._istemciyi_hizala(int(bx + (hx - bx) * son_t),
                                   int(by + (hy - by) * son_t))

    def _istemci_konumu(self, konum, yedek_x=0, yedek_y=0):
        """
        İstemcinin KENDİNİ sandığı yer — ham /api/konum x,y.

        Bu değer yalnızca istemci kendi 0x07'sini gönderdiğinde güncellenir,
        yani bot yürürken donar. İşte tam da bu yüzden istemci hizalaması
        için doğru başlangıç noktası odur: istemci gerçekten orada duruyor.
        Hiç bilinmiyorsa ölü hesaba düşülür.
        """
        try:
            x, y = int(konum.get("x", 0)), int(konum.get("y", 0))
        except (TypeError, ValueError):
            return yedek_x, yedek_y
        if not konum.get("bilinir") or (x == 0 and y == 0):
            return yedek_x, yedek_y
        return x, y

    def _konumum(self, konum):
        """
        Botun GERÇEK konumu — ölü hesap (dead reckoning) ile.

        NEDEN GEREKLİ
        -------------
        /api/konum'daki x,y YALNIZCA istemci kendi 0x07'sini gönderdiğinde
        güncellenir (APK: DunyaDurumu.konumBildir yalnız ayrıştırıcıdan
        beslenir). Sunucu bizim hareketimizi bize geri yollamıyor —
        29 Ağu 2026 ölçümü: 859 gelen 0x03 MOVE'un SIFIRI bizim vid'imizdi.

        Sonuç: bot kendi başına yürürken (oyuncu ekrana dokunmuyor) bu değer
        DONUYOR. Mesafeler hep o donmuş noktadan hesaplandığı için:
          • rota noktasına asla "varılmıyor", uzaklık hiç küçülmüyor
          • _sikisma sayacı doluyor ve nokta ATLANIYOR — rota sırayla değil,
            zamanlayıcıyla ilerlemiş oluyor
          • _yuru her turda aynı donmuş noktadan aynı adımı yeniden yolluyor
        Yani bot rotayı değil, rotanın ilk adımını tekrar tekrar yürüyor.

        ÇÖZÜM
        -----
        Enjekte ettiğimiz son konum (enjekteX/enjekteY) istemcininkinden
        TAZE ise onu kullan. İstemci daha yeni konuşmuşsa onu kullan —
        istemci gerçeği söyler: duvara çarpıp duramadıysa bunu oradan
        anlarız.

        Döner: (x, y, kaynak)
        """
        def sayi(ad, varsayilan=-1):
            try:
                return int(konum.get(ad, varsayilan))
            except (TypeError, ValueError):
                return varsayilan

        ix, iy = sayi("x", 0), sayi("y", 0)
        ex, ey = sayi("enjekteX", 0), sayi("enjekteY", 0)
        iyas = sayi("istemciHareketYas")
        eyas = sayi("enjekteYas")

        taze_enjekte = (eyas >= 0 and (ex or ey)
                        and (iyas < 0 or eyas < iyas))
        if not taze_enjekte:
            return ix, iy, "istemci"

        # İSTEMCİ GERİDE KALDIYSA ONA GERİ DÖN.
        #
        # Eskiden burada yalnızca UYARI basılıyor, sonra yine enjekte
        # edilen konum döndürülüyordu. Yani bot "gittim" sanmaya devam
        # ediyordu. Sahada görülen tam buydu: karakter canavara takılıyor,
        # sunucuda metinin yanına "varıyoruz" ama istemci geride kalıyor;
        # ekran başka yeri gösterdiği için OCR da etiket de metini
        # bulamıyor ("sunucuda gitse de gidemiyor").
        #
        # İstemci YAKIN ZAMANDA konuştuysa gerçeği o söyler — enjekte
        # ettiğimiz konum bir niyet, istemcininki bir ölçüm. Ölçüm
        # niyeti ezer.
        #
        # Neden süre sınırı: istemci yalnızca hareket ederken konuşuyor.
        # Uzun süredir sessizse "orada duruyor" mu yoksa "haber vermedi"
        # mi ayırt edilemez; o zaman ölü hesap daha iyi bir tahmin.
        if iyas >= 0 and iyas < 4000:
            fark = mesafe_ham(ix, iy, ex, ey)
            if (self.ayar.istemci_esas and (ix or iy)
                    and iyas <= max(500, self.ayar.istemci_sabir_ms)
                    and fark > max(100, self.ayar.sapma_siniri)):
                if time.time() - self._sapma_uyari > 6.0:
                    self._sapma_uyari = time.time()
                    self.bildir("uyari",
                                "istemci %.0f m geride — konum ONA "
                                "sabitlendi (takılmış olabilir; bot "
                                "oradan devam edecek)" % (fark / 100.0))
                return ix, iy, "istemci (sapma)"
            if fark > 1500 and time.time() - self._sapma_uyari > 6.0:
                self._sapma_uyari = time.time()
                self.bildir("uyari",
                            "engel? istemci bizi %.0f m geride bildirdi "
                            "(gittiğimizi sandığımız yer tutmadı)"
                            % (fark / 100.0))
        return ex, ey, "enjekte"

    def _rota_dongusel_mu(self, noktalar):
        """
        Rota KAPALI bir halka mı, yoksa açık bir hat mı?

        Kaydederken bir tur atıp başladığın yere döndüysen son nokta ile ilk
        nokta yan yanadır — sondan başa geçmek doğaldır. Ama düz bir hattı
        (ör. köyden madene) kaydettiysen son ile ilk arası yüzlerce metredir;
        oraya kuş uçuşu dönmek kayıtlı yolun dışından geçer, duvara girer.

        Ölçüt: son-ilk arası, ardışık noktaların ORTALAMA aralığının 3
        katından küçükse halka sayılır.
        """
        if len(noktalar) < 3:
            return False
        toplam = 0.0
        for i in range(len(noktalar) - 1):
            toplam += mesafe_ham(int(noktalar[i][0]), int(noktalar[i][1]),
                                 int(noktalar[i + 1][0]), int(noktalar[i + 1][1]))
        ortalama = toplam / max(1, len(noktalar) - 1)
        kapanis = mesafe_ham(int(noktalar[-1][0]), int(noktalar[-1][1]),
                             int(noktalar[0][0]), int(noktalar[0][1]))
        return kapanis <= max(3.0 * ortalama,
                              max(200, self.ayar.rota_yaricap) * 2.0)

    def _rota_halka_mi(self, noktalar):
        """Ayardaki mod ile otomatik tespiti birleştirir."""
        if self.ayar.rota_mod == "dongu":
            return True
        if self.ayar.rota_mod == "gidis_donus":
            return False
        return self._rota_dongusel_mu(noktalar)

    def _rota_ilerlet(self, noktalar):
        """
        Sıradaki noktaya geçer.

        Halka rotada başa sarar. HAT rotada UÇTAN DÖNER — yani 21/21'e
        varınca 1'e gitmeye çalışmaz; 20, 19, 18 diye geldiği yoldan geri
        gider.

        Eskiden her rota halka sanılıyordu: son noktaya varınca hedef ilk
        nokta oluyor, arada 246 m'lik boşluk "rotadan koptuk" sayılıp en
        yakın noktaya (yine son noktaya) geri bağlanıyordu. Bot uçta sonsuz
        döngüye giriyordu.
        """
        n = len(noktalar)
        self._rota_onceki = self._rota_indeks
        if n <= 1:
            return
        if self._rota_halka_mi(noktalar):
            yeni_i = (self._rota_indeks + 1) % n
            self._rota_indeks = yeni_i
            self._tur_adim += 1
            # TUR = ROTANIN SONUNA VARMAK.
            #
            # Yani indeks 0'a sarınca tur biter; nereden başlandığına
            # bakılmaz. 145 noktalık rotada 130'dan başlandıysa 15 adımda
            # tur biter — kullanıcının istediği davranış bu.
            #
            # Bir ara "tam devir" (n adım) sayılmıştı; kullanıcı bunu
            # geri aldırdı. Kanal değişimi rotanın SONUNA bağlı, kat
            # edilen mesafeye değil.
            #
            # Çok kısa turlar rahatsız ederse "Tur için en az nokta"
            # ayarı 0'dan büyük yapılabilir; o zaman sarma yetmez, o
            # kadar nokta da geçilmiş olmalı.
            # KANAL DEĞİŞİMİNDEN SONRA TAM TUR ŞART.
            #
            # Kanal değişince bot rotaya EN YAKIN noktadan başlıyor. O
            # nokta rotanın sonuna yakınsa birkaç adımda indeks 0'a
            # sarıyor, "tur bitti" deyip yine kanal değiştiriyordu —
            # kanallar arasında sonsuz zıplama. Sahada görülen buydu.
            #
            # Çözüm: geçişten sonraki İLK turda sarma yetmez, rotanın
            # tamamı yürünmüş olmalı. Sonraki turlarda eski kural geçerli.
            gereken = (n if self._tam_tur_gerekli
                       else self.ayar.tur_en_az_nokta)
            if yeni_i == 0 and self._tur_adim >= gereken:
                self._tur_adim = 0
                self._tam_tur_gerekli = False
                self._tur_bitti()
            return
        sonraki = self._rota_indeks + self._rota_yon
        if sonraki >= n:
            self._rota_yon = -1
            sonraki = n - 2
            self.bildir("bilgi", "rota sonu — geri dönülüyor")
        elif sonraki < 0:
            self._rota_yon = 1
            sonraki = 1
            self.bildir("bilgi", "rota başı — ileri gidiliyor")
            # Hat rotada BAŞA dönmek bir tur demektir: gidiş + dönüş.
            # Burada sayaç kullanmaya gerek yok, uçtan uca gidilmiş olur.
            self._tur_adim = 0
            self._tur_bitti()
        self._rota_indeks = sonraki
        self._tur_adim += 1

    def _tur_bitti(self):
        """
        Rotanın bir turu tamamlandı.

        Halka rotada başa sarınca, hat rotada gidip geri gelince sayılır.
        Kanal değiştirme buna bağlanır: her tur sonunda sıradaki kanala
        geçilir, böylece bot aynı metinleri boşuna beklemez.
        """
        self._tur_sayisi += 1
        self.bildir("bilgi", "── ROTA TURU %d TAMAMLANDI ──" % self._tur_sayisi)
        # Metin ara açıkken kanal değişimini O yönetir: tur sonunda da
        # geçilseydi metin görülen kanal terk edilirdi.
        if self.ayar.kanal_degistir and not self.ayar.metin_ara:
            self._kanal_ilerlet()

    def _kanal_ilerlet(self, sebep="tur"):
        """
        Sıradaki kanala geçilmesini bekler.

        NEDEN BOT KENDİ DEĞİŞTİREMİYOR
        ------------------------------
        29 Ağu 2026 ölçümü (tools/kanal_bul.py) kesin sonuç verdi: kanal
        değiştirmek AYRI BİR SUNUCUYA bağlanmak demek. Kayıtta 7 yeni TCP
        bağlantısı ve şu portlar görüldü:

            30001  giriş sunucusu
            30004  ch1     30016  ch4
            30008  ch2     30020  ch5
            30012  ch3     30024  ch6

        Kural: port = 30000 + 4 x kanal.

        Yani tek bir paket enjekte ederek yapılamaz; istemcinin mevcut
        bağlantıyı kapatıp yenisini açması gerekir. Proxy yalnızca var
        olan bağlantıya yazabildiği için bot bunu yapamaz.

        YAPABİLDİĞİMİZ
        --------------
        Turu bitirince DURUR, hangi kanala geçilmesi gerektiğini söyler ve
        sen elle geçtiğinde bunu ALGILAYIP kendiliğinden devam eder.
        Kanalı /api/durum -> proxy.kanal alanından okuyoruz.
        """
        liste = self._kanal_listesi()
        if not liste:
            return False
        d = self.api.get("/api/durum") or {}
        eski_port = self._port_oku(d)
        simdiki = self._kanal_oku(d)
        hedef = None
        # METİN ARA + SAYAÇ: hazır kanallara git, bekleyenleri atla.
        if sebep == "metin" and self._sayac_kullan():
            hedef = self._hazir_kanal_sec(liste, simdiki)
            if hedef is None:
                self._hepsi_beklemede_bildir(liste)
                return False
        if hedef is None:
            # Sıradaki kanal: bulunduğumuzun listedeki bir sonrası
            if simdiki in liste:
                hedef = liste[(liste.index(simdiki) + 1) % len(liste)]
            else:
                self._kanal_indeks = (self._kanal_indeks + 1) % len(liste)
                hedef = liste[self._kanal_indeks]

        if sebep == "metin":
            self.bildir("uyari", "── METİN YOK — ch%d'E GEÇİLİYOR ──" % hedef)
        else:
            self.bildir("uyari",
                        "── TUR %d BİTTİ — ŞİMDİ ch%d'E GEÇ ──"
                        % (self._tur_sayisi, hedef))

        # OTOMATİK: dokunma dizisi tanımlıysa menüye bas.
        dokunuldu = False
        if self.ayar.kanal_dokunma.strip():
            # Sondaki "bekle" atlanır: geçiş aşağıda porttan bekleniyor.
            # Aradaki beklemeler de en fazla kanal_menu_bekle ms.
            dokunuldu = self._dokunma_dizisi_calistir(
                self.ayar.kanal_dokunma, hedef, sondaki_bekle=False,
                bekle_ust_ms=int(getattr(self.ayar, "kanal_menu_bekle", 0) or 0))
            if dokunuldu:
                self.durum_metni = "ch%d bekleniyor (dokunma yapıldı)" % hedef
            else:
                self.bildir("uyari",
                            "dokunma dizisi çalışmadı — elle geçmen gerekiyor")
        else:
            # Eskiden burada sessizce geçiliyordu; kullanıcı dizinin hiç
            # çalışmadığını göremiyordu. Metin ara bunu her 20 sn'de bir
            # denediği için uyarı 30 sn'de bire kısıldı.
            simdi = time.time()
            if sebep != "metin" or simdi - self._metin_ara_uyari > 30.0:
                self._metin_ara_uyari = simdi
                self.bildir("uyari",
                            "DOKUNMA DİZİSİ BOŞ — otomatik geçiş yapılamıyor. "
                            "log/kanal_dokunuslar.txt içeriğini Rota sekmesindeki "
                            "kutuya yapıştır.")

        # Metin ara elle geçişi BEKLEMEZ: dizi çalışmadıysa bot her denemede
        # dakikalarca donardı. Bulunduğu kanalda aramaya devam eder.
        if sebep == "metin" and not dokunuldu:
            return False

        if not self.ayar.kanal_bekle:
            # Beklemek istenmiyorsa bile DURMA: kanalı elle değiştirmek
            # kullanıcının işi, botun avlanmayı bırakması gereksiz.
            self.bildir("uyari",
                        "kanal geçişi beklenmiyor — bu kanalda devam "
                        "ediliyor")
            self._tur_adim = 0
            self._tam_tur_gerekli = True
            return False

        # GEÇİŞ PORTTAN ALGILANIYOR (12 Eyl 2026).
        #
        # Eskiden kanal NUMARASI bekleniyordu. Sunucunun port düzeni değişti
        # (gözlenen: 30007, 30011 ... 30027 — "30000 + 4 x kanal" artık
        # tutmuyor) ve APK'nın verdiği numara hep 0 geldiği için bot geçişi
        # HİÇ görmüyordu: dokunuşlar yapılıp kanal gerçekten değişiyordu ama
        # süre dolunca "kanal değişmedi" denip rota ve vid sıfırlanmıyordu.
        # Her kanal ayrı port olduğu için port değişimi kesin işaret.
        self.durum_metni = "ch%d bekleniyor" % hedef
        sure = max(30.0, self.ayar.kanal_bekleme / 1000.0)
        yeni_port = self._kanal_gecisini_bekle(eski_port, sure)
        if yeni_port:
            self._port_kanal[yeni_port] = hedef
            if hedef in liste:
                self._kanal_indeks = liste.index(hedef)
            self.bildir("bilgi",
                        "KANAL DEĞİŞTİ: ch%s -> ch%d (port %d -> %d) — rota "
                        "sıfırlanıyor" % (simdiki or "?", hedef, eski_port,
                                          yeni_port))
            self._kanal_degisti_sifirla()
            # Harita yüklensin. Metin ara beklemez: yeni kanalda kendi kısa
            # süresi var; bu 3 sn her boş kanalda boşa gidiyordu.
            if sebep != "metin":
                time.sleep(3.0)
            return True

        if self.calisiyor:
            if dokunuldu and eski_port and not simdiki:
                # Dizi çalıştı ama port değişmedi: büyük ihtimalle ZATEN o
                # kanaldaydık (kanal bilinmediği için sıra ch1'den başlar).
                # Öğren ki bir sonraki geçiş sıradakine gitsin.
                self._port_kanal[eski_port] = hedef
                sonraki = hedef
                if hedef in liste:
                    self._kanal_indeks = liste.index(hedef)
                    sonraki = liste[(self._kanal_indeks + 1) % len(liste)]
                self.bildir("uyari",
                            "port değişmedi — büyük ihtimalle zaten ch%d'deyiz; "
                            "sonraki geçiş ch%d'e" % (hedef, sonraki))
            else:
                # SÜRE DOLDU AMA DURMA.
                #
                # Kanal değişmemiş olması avlanmayı engellemiyor — bulunduğu
                # kanalda devam etmesi her zaman durmasından iyi. Bir sonraki
                # denemede yeniden denenir.
                self.bildir("uyari",
                            "kanal değişmedi — bu kanalda devam ediliyor, "
                            "sonra yeniden denenecek")
            self._tur_adim = 0
            self._tam_tur_gerekli = True
        return False

    def _port_oku(self, durum=None):
        """Oyunun bağlı olduğu sunucu portu; bilinmiyorsa 0."""
        d = durum if isinstance(durum, dict) else (self.api.get("/api/durum")
                                                  or {})
        try:
            return int((d.get("proxy") or {}).get("port", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _kanal_gecisini_bekle(self, eski_port, sure):
        """
        Port değişip bağlantı ve konum hazır olana kadar bekler.

        Döner: yeni port; süre dolarsa ya da bot durdurulursa 0.
        """
        bitis = time.time() + sure
        hatirlatma = time.time() + 20.0
        while self.calisiyor and time.time() < bitis:
            d = self.api.get("/api/durum") or {}
            port = self._port_oku(d)
            if (port and port != eski_port
                    and (d.get("proxy") or {}).get("bagli")
                    and (d.get("konum") or {}).get("bilinir")):
                return port
            if time.time() >= hatirlatma:
                hatirlatma = time.time() + 20.0
                self.bildir("uyari", "hâlâ kanal geçişi bekleniyor (%d sn kaldı)"
                            % int(bitis - time.time()))
            time.sleep(0.5)
        return 0

    def _kanal_degisti_sifirla(self):
        """Yeni kanal = yeni sunucu: harita, rota konumu ve vid geçersiz."""
        # Yeni harita: eski varlıklar ve rota konumu geçersiz
        self._rota_baslangic_secildi = False
        self._onceki_mob.clear()
        self._kilit_id = 0
        self._ev_x = self._ev_y = 0
        # Yeni kanalda tur sayacı sıfırdan; bir sonraki kanal
        # değişimi için rotanın TAMAMI yürünmüş olmalı.
        self._tur_adim = 0
        self._tam_tur_gerekli = True
        # YENİ OTURUM = YENİ VİD.
        #
        # Kanal ayrı bir sunucu; karaktere yeni bir vid veriliyor.
        # Eskisini tutarsak hizalama paketi artık başka birine ait
        # olabilecek bir vid'e gider. Elle girilmiş vid de aynı
        # sebeple geçersiz — o yüzden ayarı da temizliyoruz.
        self._kendi_vid = 0
        # Ad kilidi de bırakılır: yeni kanalda AYNI AD yeni bir vid
        # taşıyor. Ad AYARI silinmez — yalnızca eşleştiği vid değişiyor.
        self._kendi_vid_adli = False
        self._ad_vid_zamani = 0.0
        self._saldirdiklarim.clear()
        if self.ayar.kendi_vid_elle:
            self.ayar.kendi_vid_elle = 0
            self.bildir("uyari",
                        "elle girilen vid temizlendi — kanal "
                        "değişti, o numara artık geçerli değil")
        if (self.ayar.karakter_adi or "").strip():
            self.bildir("bilgi",
                        "yeni kanalda vid ADDAN bulunacak (%s) — "
                        "savaşmaya gerek yok"
                        % self.ayar.karakter_adi.strip())
        else:
            self.bildir("bilgi",
                        "yeni kanalda vid sıfırdan öğrenilecek — "
                        "bot bir canavara saldırdığında bulunur. "
                        "Hareket sekmesine karakter adını yazarsan "
                        "anında bulunur.")
        # Metin ara sayacı yeni kanalda baştan başlar.
        self._metin_ara_zaman = time.time()
        self._metin_ara_varis = self._metin_ara_zaman
        self._metin_ara_buldu = False

    def _gorunen_metinler(self, varliklar):
        """Görünen, aranan türde ve canlı metinler (ad filtresi geçerli)."""
        cikti = []
        for v in varliklar or []:
            if v.get("tip") != TIP_METIN or v.get("vnum", 0) <= 0:
                continue
            if self._olu_sayilir(v) or v.get("vid") in self._metin_atlanan:
                continue
            if not self._metin_adi_uygun(v):
                continue
            cikti.append(v)
        return cikti

    def _metin_ara_kontrol(self, durum, bx, by, varliklar):
        """
        METİN ARA: metin görünmüyorsa sıradaki kanala geç, görürse kal.

        Kurallar:
          - Aranan türde (Metin adları filtresi) canlı bir metin görünüyorsa
            kanalda kalınır; onu rota ya da hedefleme kırar.
          - DÖVÜŞÜRKEN kanal değişmez: menzilde hedef varsa, metin penceresi
            açıksa ya da bir metine yürünüyorsa sayaç baştan başlar.
          - Metin "metin_ara_sure" saniye boyunca görülmezse sıradaki kanala
            geçilir (Rota sekmesindeki dokunma dizisiyle).
          - YENİ girilen kanalda ise "metin_ara_yeni_sure" (kısa) yeter:
            varlıklar girişten 1-2 sn sonra geliyor.

        Döner: True = kanal değişimi denendi, bu tur burada biter.
        """
        if not self.ayar.metin_ara:
            return False
        simdi = time.time()
        if self._metin_ara_zaman <= 0:
            self._metin_ara_zaman = simdi

        metinler = self._gorunen_metinler(varliklar)
        if metinler:
            if not self._metin_ara_buldu:
                self._metin_ara_buldu = True
                yakin = min(metinler, key=lambda v: mesafe_ham(
                    bx, by, v.get("x", 0), v.get("y", 0)))
                kanal = self._kanal_oku(durum)
                self.bildir("basari",
                            "METİN BULUNDU: %s (%.0f m) — %s kalınıyor"
                            % (yakin.get("ad", "?"),
                               mesafe_ham(bx, by, yakin.get("x", 0),
                                          yakin.get("y", 0)) / 100.0,
                               ("ch%d'de" % kanal) if kanal else "bu kanalda"))
                # Bulunuşta BİR KEZ: metin durdukça tekrar ötmez; kaybolup
                # yenisi görülünce (ya da yeni kanalda) yine çalar.
                if getattr(self.ayar, "metin_ara_ses", True):
                    bildirim_sesi()
            self._metin_ara_varis = 0.0
            self._metin_ara_zaman = simdi
            return False

        if self._metin_ara_buldu:
            self._metin_ara_buldu = False
            self._metin_ara_zaman = simdi
            self.bildir("bilgi",
                        "görünen metin kalmadı — %d sn içinde yenisi "
                        "görülmezse kanal değişecek"
                        % max(5, int(self.ayar.metin_ara_sure)))

        # DÖVÜŞÜRKEN KANAL DEĞİŞTİRME.
        if (self._metin_basinda_miyiz() or self._metin_pesinde_miyiz()
                or any(self._hedef_uygun_basit(v, bx, by, self.ayar.menzil)
                       for v in varliklar or [])):
            self._metin_ara_zaman = simdi
            return False

        bekle = max(5, int(self.ayar.metin_ara_sure))
        # YENİ KANAL: varlıklar girişten 1-2 sn sonra geliyor. Metin yoksa
        # uzun süreyi beklemek her boş kanalda ~20 sn kaybettiriyordu.
        yeni = bool(self._metin_ara_varis)
        if yeni:
            bekle = min(bekle, max(1, int(self.ayar.metin_ara_yeni_sure)))
        kalan = bekle - (simdi - self._metin_ara_zaman)
        if kalan > 0:
            self.durum_metni = ("metin aranıyor%s — %d sn sonra kanal değişecek"
                                % (" (yeni kanal)" if yeni else "",
                                   int(math.ceil(kalan))))
            return False

        self._metin_ara_zaman = simdi
        if self._sayac_kullan():
            kanal = self._kanal_oku(durum)
            if kanal:
                # Bu kanaldaydık: süresi dolduysa artık "gidilmedi" sayılmaz.
                self.sure_tutucu.goruldu(kanal)
                # BOŞ KANALA SAYAÇ YALNIZCA OTOMATİK AÇIKSA.
                #
                # Eskiden her boş kanalda sayaç başlıyordu. Sayaçlar tekrarlı
                # olunca 8 kanal bir kez gezildikten sonra hepsi "beklemede"
                # kalıyor, metin ara hiç kanal değiştirmiyordu. Sayaçları
                # artık kullanıcı elle başlatıyor.
                kalan = self.sure_tutucu.kalan(kanal)
                if (self.ayar.metin_sure_otomatik
                        and (kalan is None or kalan <= 0)):
                    dk = int(self.ayar.metin_sure_dk)
                    self.sure_tutucu.baslat(kanal, dk)
                    self.bildir("bilgi",
                                "ch%d'de metin yok — %d dk sayaç başlatıldı "
                                "(başkası kırmış olabilir)" % (kanal, dk))
                    if self.sure_kaydet:
                        self.sure_kaydet()
        gecti = self._kanal_ilerlet(sebep="metin")
        # Başarısız olsa bile hemen yeniden denemesin: sayaç baştan.
        self._metin_ara_zaman = time.time()
        if not gecti:
            # Geçilemedi (dizi çalışmadı, hepsi beklemede, port değişmedi):
            # kısa süreyle her 3 sn'de bir menüye basmasın — uzun süre beklenir.
            self._metin_ara_varis = 0.0
        return True

    def _sayac_kullan(self):
        """Metin ara kanal seçerken süre tutucuya bakacak mı?"""
        return bool(self.sure_tutucu is not None
                    and self.ayar.metin_sure_tutucu)

    def _hazir_kanal_sec(self, liste, simdiki):
        """
        Metin ara için gidilecek kanal; hepsi beklemedeyse None.

        Öncelik (bulunduğumuz kanaldan sonraki sırayla):
          1. HAZIR — sayacı dolmuş, metin büyük ihtimalle yeniden doğmuş
             (tekrarlı sayaçta: süre dolduktan sonra oraya gidilmemiş)
          2. sayacı hiç başlamamış (—) — orada ne olduğunu bilmiyoruz
        Sayacı süren kanallar ve bulunduğumuz kanal atlanır.
        """
        if not liste:
            return None
        if simdiki in liste:
            bas = liste.index(simdiki) + 1
        else:
            bas = self._kanal_indeks + 1
        sira = [liste[(bas + i) % len(liste)] for i in range(len(liste))]
        sira = [k for k in sira if k != simdiki]
        simdi = time.time()
        kalanlar = {k: self.sure_tutucu.kalan(k, simdi) for k in sira}
        for k in sira:
            if kalanlar[k] is not None and self.sure_tutucu.hazir_mi(k, simdi):
                return k
        for k in sira:
            if kalanlar[k] is None:
                return k
        return None

    def _hepsi_beklemede_bildir(self, liste):
        """Bütün kanalların sayacı sürüyor: kalıyoruz, ilk hazır olanı söyle."""
        simdi = time.time()
        kalanlar = [(self.sure_tutucu.kalan(k, simdi), k) for k in liste]
        kalanlar = [(sn, k) for sn, k in kalanlar if sn is not None]
        if not kalanlar:
            return
        sn, k = min(kalanlar)
        dk, san = divmod(int(math.ceil(max(0.0, sn))), 60)
        self.durum_metni = ("tüm kanallar beklemede — ch%d %d:%02d sonra hazır"
                            % (k, dk, san))
        if simdi - self._bekleme_uyari > 60.0:
            self._bekleme_uyari = simdi
            self.bildir("bilgi",
                        "tüm kanalların sayacı sürüyor — burada bekleniyor; "
                        "ilk hazır olacak: ch%d (%d:%02d)" % (k, dk, san))

    def _dokunma_dizisi_calistir(self, metin, kanal, sondaki_bekle=True,
                                 bekle_ust_ms=0):
        """
        Dokunma dizisini yürütür — kanal menüsüne basmak için.

        Biçim, satır başına bir komut:

            tap 540 1180        ekrana dokun
            bekle 800           beklе (ms)
            tus 4               tuş gönder (4 = GERİ)

        Koordinatlarda {k} kanal numarasıyla değiştirilir, böylece
        "kanal N'in satırı" hesaplanabilir:

            tap 320 {700+k*90}   -> ch3 için tap 320 970

        NEDEN DOKUNMA
        -------------
        Kanal değişimi ağ üzerinden yapılamıyor: kanallar ayrı sunucular
        (port = 30000 + 4×kanal, ölçüldü) ve geçiş yeni bir TCP bağlantısı
        açıyor. Proxy var olan bağlantıya yazabildiği için paketle
        olmuyor. Oyunun kendi menüsüne basmak tek yol; cihazda root
        olduğu için mümkün.

        Döner: True = dizi çalıştı.
        """
        satirlar = self._dizi_bolumu(metin, kanal)
        # SONDAKİ "bekle" SATIRLARI (kanal değişiminde atlanır).
        #
        # Kayıt aracı son dokunuştan kaydın bitişine kadar geçen süreyi de
        # yazıyor — sahada her kanal için "bekle 8000". Kanal değişiminde
        # geçiş hemen ardından PORTTAN bekleniyor (_kanal_gecisini_bekle);
        # bu uyku her değişimde 8 sn boşa gidiyordu.
        if not sondaki_bekle:
            while satirlar and satirlar[-1].split()[0].lower() == "bekle":
                satirlar.pop()
        if not satirlar:
            self.bildir("uyari",
                        "ch%d için dokunma dizisi yok — "
                        "python tools/dokunma_kaydet.py ile kaydet" % kanal)
            return False

        cevap = self.api.dokunma_ac(True)
        if not (isinstance(cevap, dict) and cevap.get("ok")):
            self.bildir("hata", "dokunma açılamadı: %s" % cevap)
            return False

        self.bildir("bilgi", "kanal %d için %d adımlık dokunma dizisi"
                    % (kanal, len(satirlar)))
        for satir in satirlar:
            if not self.calisiyor:
                return False
            parcalar = satir.split()
            komut = parcalar[0].lower()
            try:
                if komut == "bekle" and len(parcalar) >= 2:
                    ms = int(self._sayi_coz(parcalar[1], kanal))
                    if bekle_ust_ms and bekle_ust_ms > 0:
                        ms = min(ms, int(bekle_ust_ms))
                    time.sleep(min(30.0, max(0.0, ms / 1000.0)))
                    continue
                if komut == "tap" and len(parcalar) >= 3:
                    x = int(self._sayi_coz(parcalar[1], kanal))
                    y = int(self._sayi_coz(parcalar[2], kanal))
                    c = self.api.dokun(x, y)
                    if not (isinstance(c, dict) and c.get("ok")):
                        self.bildir("hata", "dokunma başarısız (%d,%d): %s"
                                    % (x, y, c))
                        return False
                    self.bildir("bilgi", "  tap %d,%d" % (x, y))
                    continue
                if komut == "tus" and len(parcalar) >= 2:
                    self.api.get("/api/dokun",
                                 tus=int(self._sayi_coz(parcalar[1], kanal)))
                    continue
                self.bildir("uyari", "anlaşılmayan dokunma satırı: %s" % satir)
            except Exception as e:                    # noqa: BLE001
                self.bildir("hata", "dokunma satırı çözülemedi (%s): %s"
                            % (satir, e))
                return False
        return True

    @staticmethod
    def _dizi_bolumu(metin, kanal):
        """
        Kanal başına dizi seçer.

        Menü konumu her kanal için farklı olduğundan diziler bölüm
        başlıklarıyla tutulur:

            [ch2]
            tap 540 1180
            bekle 300
            tap 320 760

            [ch3]
            ...

        Başlık yoksa metnin tamamı tüm kanallar için kullanılır —
        {k} ile hesaplanan tek bir dizi yazmak isteyenler için.
        """
        satirlar = [x.strip() for x in (metin or "").splitlines()]
        satirlar = [x for x in satirlar if x and not x.startswith("#")]
        if not any(x.lower().startswith("[ch") for x in satirlar):
            return satirlar

        bolum = None
        toplanan = []
        for satir in satirlar:
            m = re.fullmatch(r"\[ch(\d+)\]", satir, re.IGNORECASE)
            if m:
                bolum = int(m.group(1))
                continue
            if bolum == kanal:
                toplanan.append(satir)
        return toplanan

    @staticmethod
    def _sayi_coz(parca, kanal):
        """
        '540' -> 540 ;  '{700+k*90}' -> kanal 3 için 970.

        Süslü parantez içi yalnızca RAKAM, k ve + - * / ( ) içerebilir —
        rastgele kod çalıştırmayalım.
        """
        parca = parca.strip()
        if not (parca.startswith("{") and parca.endswith("}")):
            return int(parca)
        ifade = parca[1:-1].replace("k", str(int(kanal)))
        if not re.fullmatch(r"[0-9+\-*/() ]+", ifade):
            raise ValueError("ifadede izinsiz karakter: %s" % ifade)
        return int(eval(ifade, {"__builtins__": {}}, {}))   # noqa: S307

    def _kanal_oku(self, durum=None):
        """
        Şu an hangi kanaldayız? Bilinmiyorsa 0.

        Önce /api/durum -> proxy.kanal. O numara portun "30000 + 4 x kanal"
        olduğunu varsayıyor; port düzeni değiştiği için artık hep 0 geliyor.
        O zaman botun kendi geçişlerinden ÖĞRENDİĞİ port -> kanal eşleşmesine
        bakılır.
        """
        d = durum if isinstance(durum, dict) else self.api.get("/api/durum")
        if not isinstance(d, dict):
            return 0
        try:
            k = int((d.get("proxy") or {}).get("kanal", 0) or 0)
        except (TypeError, ValueError):
            k = 0
        if k:
            return k
        port = self._port_oku(d)
        # Önce botun kendi geçişlerinden öğrendiği, sonra doğrulanmış kural.
        return self._port_kanal.get(port) or port_kanali(port)

    def _kanal_listesi(self):
        """'1,2,3' -> [1,2,3]. Boşsa 1..8."""
        ham = (self.ayar.kanallar or "").strip()
        if not ham:
            return [1, 2, 3, 4, 5, 6, 7, 8]
        cikti = []
        for parca in ham.replace(";", ",").split(","):
            parca = parca.strip()
            if parca.isdigit():
                n = int(parca)
                if 1 <= n <= 99:
                    cikti.append(n)
        return cikti or [1, 2, 3, 4, 5, 6, 7, 8]

    def _rota_metin_avi(self, durum, bx, by, varliklar):
        """
        Rota üzerindeyken METİN arar; bulursa gider ve kırar.

        HEDEFLEME SEKMESİNDEN NEDEN AYRI
        --------------------------------
        Metin kırılınca içinden canavar çıkıyor. İkisi aynı hedef listesine
        bağlı olsaydı iki kötü seçenekten birini yapmak zorunda kalırdık:

          • canavarlar da hedeflenir -> bot metini bırakıp canavar kovalar,
            rota ilerlemez
          • canavarlar hedeflenmez  -> metinden çıkan canavarlara hiç
            vurulmaz

        Bu yüzden görev bölündü: ROTA metin arar ve kırar, HEDEFLEME sekmesi
        de metinden çıkan canavarları halleder. Hedefleme zaten rotadan önce
        çalıştığı için, canavar çıktığı anda ona vurulur; canavar bitince
        rota metin avına döner.

        Döner: bir iş yapıldıysa True (tur burada biter).
        """
        if not self.ayar.rota_metin or not varliklar:
            return False

        menzil = max(500, self.ayar.rota_metin_menzil)
        adaylar = []
        for v in varliklar:
            if v.get("tip") != TIP_METIN:
                continue
            if v.get("vnum", 0) <= 0 or self._olu_sayilir(v):
                continue
            if not self._metin_adi_uygun(v):
                continue
            if v.get("vid") in self._metin_atlanan:
                continue            # tıklanamadı, bir daha uğraşma
            uzak = mesafe_ham(bx, by, v.get("x", 0), v.get("y", 0))
            if uzak > menzil:
                continue
            # Rotanın çevresinde kalsın: 200 m ötedeki metine gitmek
            # rotayı terk etmek olur.
            if self.ayar.ev_yaricap > 0 and self._ev_disinda(
                    v, self.ayar.ev_yaricap):
                continue
            adaylar.append((uzak, v))
        if not adaylar:
            # Metin kalmadı ama PENCERE AÇIKSA metinden çıkan canavarlar
            # hâlâ ortada olabilir — rota ilerlemeden onları temizle.
            if (self.ayar.rota_kendi_saldiri
                    and self._metin_basinda_miyiz()
                    and self._rota_canavar_temizle(durum, bx, by, varliklar)):
                return True
            return False

        adaylar.sort(key=lambda p: p[0])
        uzak, metin = adaylar[0]
        ad = metin.get("ad", "metin")

        # VARILAMAYAN METİN SONSUZA DEK AVLANMASIN.
        #
        # Sahadaki döngünün ikinci yarısı buydu: metin duvarın ardında,
        # yanına hiç varılamıyor. Bot ona yürüyor, dolanıyor, görüşten
        # kaçırıyor, rotaya dönüyor, metini YİNE görüyor... Bu vid için
        # geçen süreyi ölçüp sabır bitince onu atlıyoruz. Metin kırılıp
        # yeniden doğunca yeni vid alacağı için kalıcı kayıp değil.
        vid = metin.get("vid")
        if self._metin_av_vid != vid:
            self._metin_av_vid = vid
            self._metin_av_basi = time.time()
        sabir = max(45.0, 3.0 * max(5, self.ayar.metin_savas_suresi))
        if time.time() - self._metin_av_basi > sabir:
            self._metin_atlanan.add(vid)
            self.bildir("uyari",
                        "%s ATLANDI — %.0f sn'dir yanına varılamıyor "
                        "(duvar ardında olabilir). Rotaya dönülüyor."
                        % (ad, time.time() - self._metin_av_basi))
            self._metin_av_vid = 0
            self._metin_av_basi = 0.0
            self._metin_pesinde = 0.0
            return False

        # AV BAŞLADI — bu damga rotanın "koptuk" kararını susturuyor.
        # Metine yürürken rotadan açılmak kasıtlıdır; indeks korunur ki
        # av bitince kaldığımız noktadan devam edelim.
        self._metin_pesinde = time.time()
        # Dönüş yürüyüşü için nokta sayacı da taze başlasın; yoksa av
        # bittiği anda "noktaya varılamadı" deyip nokta atlanıyordu.
        self._nokta_zamani = time.time()

        # SON YAKLAŞMA
        #
        # Saldırı menzili (varsayılan 25 m) sunucunun gerçek vuruş
        # alanından geniş; "menzile girdim" deyip durunca sunucu vuruşu
        # kabul etmiyordu. Ayrıca _yuru normalde yolun %85'inde duruyor,
        # yani %15 daha eksik kalıyordu. İkisi üst üste binince bot
        # metinin yanına hiç varamıyordu.
        #
        # Çözüm: metinin MERKEZİNE değil, ondan "yaklaşma mesafesi" kadar
        # önündeki noktaya TAM yürü. Oraya varınca gerçekten dibindeyiz.
        # EKRAN TIKLAMA MODUNDA DAHA UZAKTAN DUR.
        #
        # Kalibrasyon ölçümü (30 Ağu 2026) şunu gösterdi: metin 3 m
        # ötedeyken ekranda karakterden yalnızca 36-85 px uzakta görünüyor,
        # kalibrasyon hatası ise ~21 px (en kötü 35). Yani tıklama
        # karakterin kendisine denk gelebiliyor.
        #
        #     3 m  ->  36-85 px      8 m  ->  95-225 px
        #
        # Ama tıklarken saldırı menziline GİRMEYE GEREK YOK: tıklayınca
        # istemci kendisi yürüyüp saldırıyor. Bu yüzden ekran modunda
        # daha uzaktan durup tıklıyoruz — hem isabet payı büyüyor hem
        # yürüyüşü istemci yaptığı için daha doğal görünüyor.
        # TEK MESAFE AYARI: "Yaklaşma mesafesi".
        #
        # Bir ara ekran tıklaması için AYRI bir "tıklama mesafesi" vardı
        # ve kullanıcının yazdığı değeri eziyordu — 150 yazılsa bile bot
        # 8 m'de duruyordu. İki ayrı ayarın aynı şeyi yönetmesi kafa
        # karıştırdı ve iki kez aynı şikâyete yol açtı; ikincisi kaldırıldı.
        #
        # Alt sınır da yok: ne yazılırsa oraya kadar gidilir.
        yakinlik = max(1, self.ayar.metin_yaklasma)
        if uzak <= yakinlik:
            self.durum_metni = "metin kırılıyor: %s" % ad
            # Yanına vardık: sabır sayacı "varamama" süresini ölçüyor,
            # dövüş süresini değil. Sıfırla.
            self._metin_av_basi = time.time()
            # Canavar penceresini aç: bu metinden çıkacaklara vurulabilsin.
            self._metin_zamani = time.time()
            self._metin_saldirisi(metin, bx, by)
            return True
        if not self.ayar.yaklas:
            # Yürüyemiyorsak hiç değilse menzildeyse vur
            if uzak <= self.ayar.menzil:
                self._saldir(metin)
                return True
            return False
        # HEDEF, EŞİKTEN DAHA YAKIN OLMALI.
        #
        # Eskiden saldırı eşiği ile yürüme hedefi AYNI sayıydı. Metin
        # eşiğin bir tık dışındayken (150.7 ham, eşik 150) bot "yürü"
        # diyor ama hedefi de 150'ye koyduğu için hiç kımıldamıyordu:
        # sonsuz "2 m -> 2 m". Sahada tam bu görüldü.
        #
        # Hedefi eşiğin %70'ine koyunca varış eşiği rahatça geçiyor.
        hedef_uzak = yakinlik * 0.7
        pay = max(0.0, (uzak - hedef_uzak) / uzak)
        tx = int(bx + (metin["x"] - bx) * pay)
        ty = int(by + (metin["y"] - by) * pay)
        self._yuru(tx, ty, durum,
                   "metine git: %s (%.1f m -> %.1f m)"
                   % (ad, uzak / 100.0, hedef_uzak / 100.0), tam=True)
        return True

    def _metin_adi_uygun(self, v):
        """
        Bu metin aranan türlerden mi?

        Ayar boşsa HER metin kabul edilir. Doluysa yalnızca adı listedeki
        parçalardan birini içerenler — "karanlık, kıskançlık, siyah" gibi.

        Karşılaştırma Türkçe-duyarsız: _sadelestir "İ/ı" ve aksanları
        ayıklıyor, böylece "kiskanclik" yazınca "Kıskançlık Metini"
        bulunuyor.
        """
        ham = (self.ayar.rota_metin_adlari or "").strip()
        if not ham:
            return True
        ad = self._sadelestir(v.get("ad") or "")
        if not ad:
            # İsmi henüz gelmemiş metni eleme — 0x88 gecikmeli gelebiliyor.
            return True
        for parca in ham.replace(";", ",").split(","):
            parca = self._sadelestir(parca.strip())
            if parca and parca in ad:
                return True
        return False

    def _rota_canavar_temizle(self, durum, bx, by, varliklar):
        """
        Metin kırıldıktan sonra ortaya çıkan canavarları temizler.

        Metin ölünce yok oluyor, yerine canavarlar doğuyor. Rota o anda
        "metin yok" deyip yürümeye başlarsa canavarları arkasında bırakır
        ve peşine takılırlar. Pencere açık olduğu sürece onları da rota
        hallediyor.
        """
        menzil = max(self.ayar.menzil, self.ayar.metin_yaklasma)
        yakinlar = []
        for v in varliklar or []:
            if v.get("tip") != TIP_MOB:
                continue
            if v.get("vnum", 0) <= 0 or self._olu_sayilir(v):
                continue
            uzak = mesafe_ham(bx, by, v.get("x", 0), v.get("y", 0))
            if uzak <= menzil:
                yakinlar.append((uzak, v))
        if not yakinlar:
            return False
        yakinlar.sort(key=lambda p: p[0])
        self.durum_metni = "metin canavarları temizleniyor (%d)" % len(yakinlar)
        # Hedefleme döngüsü menzildekilere zaten vuruyor; rota yalnızca
        # beklesin. En yakını döngünün menzili dışındaysa rota vurmaya
        # devam eder (metin_yaklasma > menzil olabilir).
        if self._hedefleme_isci_acik() and yakinlar[0][0] < self.ayar.menzil:
            return True
        if self.ayar.coklu_hedef:
            self._coklu_saldiri([v for _, v in yakinlar], bx, by)
        else:
            self._saldir(yakinlar[0][1])
        return True

    def _rota_devriyesi(self, durum, bx, by, varliklar=None):
        """
        Kullanıcının tambot'ta oluşturduğu YEREL rotada gezer.

        APK'daki rota sisteminden bağımsızdır; noktalar tambot_ayar.json
        içinde saklanır. Sıradaki noktaya yürür, yarıçapa girince
        _rota_ilerlet ile bir sonrakine geçer.
        """
        noktalar = self.ayar.rota
        if not noktalar:
            return False

        # ROTA DEĞİŞTİYSE BAŞTAN KONUMLAN.
        #
        # Kitaplıktan bot çalışırken başka bir rota yüklenebiliyor. Eski
        # rotanın indeksi yeni rotada anlamsız — hatta yeni rota kısaysa
        # sınır dışı. Rotanın kimliği değiştiğinde en yakın nokta yeniden
        # seçilir; bu, kitaplıktan yükleyince botu durdurup başlatma
        # zorunluluğunu kaldırıyor.
        kimlik = (len(noktalar), tuple(noktalar[0]), tuple(noktalar[-1]))
        if kimlik != self._rota_kimligi:
            if self._rota_kimligi is not None:
                self.bildir("bilgi",
                            "rota değişti (%d nokta) — en yakın noktadan "
                            "devam ediliyor" % len(noktalar))
            self._rota_kimligi = kimlik
            self._rota_baslangic_secildi = False
        if self._rota_indeks >= len(noktalar):
            self._rota_indeks = 0

        # Rotada metin varsa ONA git — nokta ilerletmeden. Metin bitince
        # aşağıdaki devriye kaldığı noktadan devam eder.
        if self._rota_metin_avi(durum, bx, by, varliklar):
            return True

        # İlk turda EN YAKIN noktadan başla — baştan başlamak, rotanın uzak
        # ucundaysak gereksiz uzun bir yolculuk demek olurdu.
        if not self._rota_baslangic_secildi:
            self._rota_baslangic_secildi = True
            self._nokta_zamani = time.time()
            self._rota_yon = 1
            self._rota_onceki = -1
            self._tur_adim = 0          # tur sayacı buradan başlar
            self._rota_indeks = min(
                range(len(noktalar)),
                key=lambda i: mesafe_ham(bx, by,
                                         int(noktalar[i][0]),
                                         int(noktalar[i][1])))
            n = noktalar[self._rota_indeks]
            halka = self._rota_halka_mi(noktalar)
            # Hat rotanın SON ucundan başlıyorsak yön baştan geriye olmalı;
            # yoksa ilk ilerletme uçtan dönüş uyarısı basardı.
            if not halka and self._rota_indeks >= len(noktalar) - 1:
                self._rota_yon = -1
            self.bildir("bilgi",
                        "rotaya en yakın noktadan başlanıyor: %d/%d (%.0f m) — %s"
                        % (self._rota_indeks + 1, len(noktalar),
                           mesafe_ham(bx, by, int(n[0]), int(n[1])) / 100.0,
                           "halka" if halka else "gidiş-dönüş"))

        self._rota_indeks %= len(noktalar)
        hx = int(noktalar[self._rota_indeks][0])
        hy = int(noktalar[self._rota_indeks][1])
        uzak = mesafe_ham(bx, by, hx, hy)

        # Rotadan KOPTUK MU?
        #
        # Kayıt sırasında yürüdüğün yol duvarsızdır. Hedefe kuş uçuşu olması
        # gerekenden çok uzaksak (canavar kovaladık, engele takıldık,
        # ışınlandık) aradaki düz çizgi kayıtlı yoldan geçmiyor demektir;
        # duvarın içine yürürüz. Böyle bir durumda en yakın noktaya geri
        # bağlanıp sırayı oradan sürdürürüz.
        #
        # Eşik rotanın KENDİ ölçüsünden gelir: geldiğimiz nokta ile hedef
        # arasındaki KAYITLI mesafe. Rotada gerçekten uzun bir bacak varsa bu
        # kopma değildir; sabit eşik onu yanlışlıkla kopma sayıyordu.
        beklenen = 0.0
        if 0 <= self._rota_onceki < len(noktalar):
            o = noktalar[self._rota_onceki]
            beklenen = mesafe_ham(int(o[0]), int(o[1]), hx, hy)
        esik = max(4000.0, 2.5 * beklenen,
                   3.0 * max(200, self.ayar.rota_yaricap))
        # METİN AVI EŞİĞİ EZER.
        #
        # Metin avı 60 m'ye kadar kovalıyordu, kopma eşiği ise 40 m: uzak
        # bir metine gitmek kopmayı GARANTİ ediyordu. Sahada döngü şuydu —
        # metini gör, duvarı dolan, dolanırken "rotadan koptuk" de, en
        # yakın noktaya dön, metini yine gör...
        #
        # İki sayı aynı işi ölçüyor: "rotadan ne kadar uzaklaşmak
        # normal". Metin avı açıkken onun menzili taban oluyor. Duvar
        # dolanması yolu uzattığı için üstüne pay ekleniyor.
        if self.ayar.rota_metin:
            esik = max(esik, 1.6 * max(500, self.ayar.rota_metin_menzil))

        # AV SÜRERKEN KOPMA SAYILMAZ.
        #
        # Metine giderken rotadan uzaklaşmak KASITLI. O sırada indeksi
        # oynatmak, dönüşte gidilecek noktayı da kaybettiriyordu.
        #
        # DİKKAT: burada mesafeyi 0 yapmak YANLIŞ olur — aşağıdaki varış
        # denetimi ("uzak <= yarıçap") onu "noktaya vardık" sanıp indeksi
        # her turda bir ileri atıyordu. Sadece kopma dalı atlanıyor.
        av_suruyor = (self._metin_basinda_miyiz()
                      or self._metin_pesinde_miyiz())

        if uzak > esik and not av_suruyor:
            yakin = min(range(len(noktalar)),
                        key=lambda i: mesafe_ham(bx, by, int(noktalar[i][0]),
                                                 int(noktalar[i][1])))
            if yakin != self._rota_indeks:
                n = noktalar[yakin]
                self.bildir("uyari",
                            "rotadan koptuk (%.0f m > %.0f m) — en yakın "
                            "noktaya dönülüyor: %d/%d (%.0f m)"
                            % (uzak / 100.0, esik / 100.0, yakin + 1,
                               len(noktalar),
                               mesafe_ham(bx, by, int(n[0]), int(n[1])) / 100.0))
                self._rota_onceki = -1
                self._rota_indeks = yakin
                self._nokta_zamani = time.time()
                hx, hy = int(n[0]), int(n[1])
                uzak = mesafe_ham(bx, by, hx, hy)

        # Nokta zaman aşımı: bir noktaya makul sürede varamadıysak (duvar,
        # sunucunun reddi) orada takılıp kalma.
        if self._nokta_zamani <= 0:
            self._nokta_zamani = time.time()
        pay = min(30.0, 5.0 + uzak / max(200.0, self.ayar.yurume_hizi))
        zaman_asti = (time.time() - self._nokta_zamani) > pay

        if uzak <= max(200, self.ayar.rota_yaricap) or zaman_asti:
            if zaman_asti:
                self.bildir("uyari",
                            "nokta %d/%d'e %.0f sn'de varılamadı (%.0f m "
                            "kaldı) — sıradakine geçiliyor"
                            % (self._rota_indeks + 1, len(noktalar), pay,
                               uzak / 100.0))
            self._rota_ilerlet(noktalar)
            self._nokta_zamani = time.time()
            self._sikisma = 0
            if self.ayar.rota_bekle > 0:
                self.durum_metni = "rota: %d ms bekleniyor" % self.ayar.rota_bekle
                time.sleep(min(self.ayar.rota_bekle / 1000.0, 10.0))
                return True
            # Beklemeyecekse BURADA DURMA — sıradaki noktaya bu turda yürü.
            #
            # Eskiden burada return vardı: noktaya varılan tur hiç hareket
            # paketi göndermiyordu, sadece indeksi ilerletip dönüyordu.
            # Yani bot bir adım yürüyor, bir tur boyunca duruyor, sonra
            # tekrar yürüyordu. Başkasının ekranında "durup durup yürüme"
            # olarak görünen şeyin yarısı buydu.
            hx = int(noktalar[self._rota_indeks][0])
            hy = int(noktalar[self._rota_indeks][1])
            uzak = mesafe_ham(bx, by, hx, hy)
            if uzak <= max(200, self.ayar.rota_yaricap):
                return True                      # sonraki de dibimizde

        self._yuru(hx, hy, durum,
                   "rota %d/%d %s (%.0f m)"
                   % (self._rota_indeks + 1, len(noktalar),
                      "ileri" if self._rota_yon > 0 else "geri",
                      uzak / 100.0))
        return True

    def _devriye(self, durum, bx, by):
        rotalar = self.api.get("/api/rotalar")
        if not isinstance(rotalar, dict) or not rotalar.get("ok"):
            self.durum_metni = "devriye: rota okunamadı"
            time.sleep(1.0)
            return
        aktif = rotalar.get("aktif", "")
        rota = None
        for r in rotalar.get("rotalar", []):
            if r.get("ad") == aktif:
                rota = r
                break
        noktalar = (rota or {}).get("noktalar") or []
        if not noktalar:
            self.durum_metni = "devriye: aktif rota boş"
            time.sleep(1.0)
            return

        self._rota_indeks %= len(noktalar)
        n = noktalar[self._rota_indeks]
        hx, hy = int(n.get("x", 0)), int(n.get("y", 0))
        uzak = mesafe_ham(bx, by, hx, hy)
        yaricap = max(200, int(n.get("yaricap", 300)))

        if uzak <= yaricap or self._sikisma > 12:
            if self._sikisma > 12:
                self.bildir("uyari", "sıkışma algılandı, sıradaki noktaya geçiliyor")
                self._sikisma = 0
            self._rota_indeks = (self._rota_indeks + 1) % len(noktalar)
            bekle = int(n.get("bekle", 0))
            if bekle > 0:
                self.durum_metni = "devriye: %d ms bekleniyor" % bekle
                time.sleep(min(bekle / 1000.0, 5.0))
            return

        self._yuru(hx, hy, durum,
                   "devriye %d/%d (%.0f m)"
                   % (self._rota_indeks + 1, len(noktalar), uzak / 100.0))


# ═══════════════════════════════════════════════════════════════════════
#  Arayüz
# ═══════════════════════════════════════════════════════════════════════

class MetinAraGezgini(Motor):
    """
    METİN ARA TUŞU — bot kapalıyken de kanal aralığında gezer.

    Bot sekmesindeki tuşla başlar ve durur; botun ana döngüsünden
    bağımsızdır. Paket göndermez: yalnızca varlık listesine bakar ve
    kanal menüsüne dokunur. Kanallar düz sırayla gezilir
    (1-4: 1, 2, 3, 4, 1, ...); süre tutucuya bakılmaz.

      - Görünen metin varsa (Metin adları filtresi) kanalda durur.
      - Yeni girilen kanalda metin yoksa "yeni kanalda" süresi sonunda,
        metin kırılıp kaybolunca "metin kaybolunca" süresi sonunda geçer.
      - Menzilde canavar varken (dövüşürken) geçmez.

    Karar mantığı botunkiyle aynı (_metin_ara_kontrol, _kanal_ilerlet);
    ayarlar her adımda arayüzün ayarından kopyalanır.
    """

    def __init__(self, api, kaynak_ayar, bildir, ana_motor=None):
        super().__init__(api, Ayar(), bildir)
        self.kaynak_ayar = kaynak_ayar
        self.ana_motor = ana_motor
        self.ch_bas = 1
        self.ch_son = 8
        self.sure_tutucu = None          # düz sıra
        self.durum_metni = "kapalı"

    def aralik(self):
        """Gezilecek kanallar: [ch_bas .. ch_son] (ters girilse de)."""
        try:
            a, b = sorted((int(self.ch_bas), int(self.ch_son)))
        except (TypeError, ValueError):
            a, b = 1, 8
        a = min(max(1, a), 99)
        b = min(max(a, b), 99)
        return list(range(a, b + 1))

    def _ayari_tazele(self):
        """Arayüz ayarını kopyala; yalnızca metin ara için gerekenleri ez."""
        self.ayar.__dict__.update(self.kaynak_ayar.__dict__)
        self.ayar.metin_ara = True
        self.ayar.kanallar = ",".join(str(k) for k in self.aralik())
        self.ayar.kanal_bekle = True

    def basla(self):
        if self.calisiyor:
            return
        self._ayari_tazele()
        simdi = time.time()
        # Bulunduğu kanalda da "yeni kanal" gibi kısa bekle.
        self._metin_ara_zaman = simdi
        self._metin_ara_varis = simdi
        self._metin_ara_buldu = False
        # Aralık dışındaysak ilk geçiş aralığın BAŞINA.
        self._kanal_indeks = -1
        self.calisiyor = True
        self.durum_metni = "başlıyor"
        self._is = threading.Thread(target=self._dongu, daemon=True)
        self._is.start()

    def durdur(self):
        self.calisiyor = False

    def _dongu(self):
        a = self.aralik()
        self.bildir("basari", "METİN ARA başladı — ch%d-ch%d arası gezilecek"
                    % (a[0], a[-1]))
        while self.calisiyor:
            try:
                self._ara_adim()
            except Exception as e:                    # noqa: BLE001
                self.bildir("hata", "metin ara hatası: %s: %s"
                            % (type(e).__name__, e))
                time.sleep(1.0)
            time.sleep(0.4)
        self.durum_metni = "kapalı"
        self.bildir("bilgi", "METİN ARA durdu")

    def _ara_adim(self):
        """Tek karar adımı: bak, gerekirse kanal değiştir."""
        self._ayari_tazele()
        # Bot da metin arıyorsa ikisi aynı anda menüye basmasın.
        if (self.ana_motor is not None and self.ana_motor.calisiyor
                and self.kaynak_ayar.metin_ara):
            self.durum_metni = "bot da metin arıyor — tuş bekliyor"
            time.sleep(0.6)
            return
        d = self.api.get("/api/durum")
        d = d if isinstance(d, dict) else {}
        p = d.get("proxy") or {}
        k = d.get("konum") or {}
        if not p.get("bagli") or not k.get("bilinir"):
            self.durum_metni = "oyun bağlantısı bekleniyor"
            time.sleep(0.6)
            return
        v = self.api.get("/api/varliklar", n=120)
        if not isinstance(v, list):
            v = []
        try:
            bx, by = int(k.get("x", 0)), int(k.get("y", 0))
        except (TypeError, ValueError):
            bx = by = 0
        self.durum_metni = ""
        gecis = self._metin_ara_kontrol(d, bx, by, v)
        if self._metin_ara_buldu:
            kanal = self._kanal_oku(d)
            self.durum_metni = ("metin var — %s duruluyor"
                                % (("ch%d'de" % kanal) if kanal else "burada"))
        elif not gecis and not self.durum_metni:
            self.durum_metni = "dövüş sürüyor — kanal değişmez"

    def _kanal_degisti_sifirla(self):
        """Gezgin rota ya da vid tutmuyor: yalnızca metin ara sayaçları."""
        self._metin_ara_zaman = time.time()
        self._metin_ara_varis = self._metin_ara_zaman
        self._metin_ara_buldu = False


class TamBot(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Tam Bot — Romia2")
        self.configure(bg=KOYU)
        self.geometry("980x720")
        self.minsize(860, 620)

        self.api = Api()
        self.ayar = Ayar()
        self.kuyruk = queue.Queue()
        self.motor = Motor(self.api, self.ayar, self._bildir)
        self.son_durum = {}
        self.sure_tutucu = MetinSureTutucu()
        # Metin ara hazır kanalları seçerken aynı sayaca baksın; botun
        # başlattığı sayaçlar da kuyruk üzerinden diske yazılsın.
        self.motor.sure_tutucu = self.sure_tutucu
        self.motor.sure_kaydet = lambda: self.kuyruk.put(
            ("sure_kaydet", None, None))
        # METİN ARA TUŞU: bot kapalıyken de kanal aralığında gezer.
        self.metin_arayici = MetinAraGezgini(self.api, self.ayar, self._bildir,
                                             ana_motor=self.motor)
        self._sure_etiket_zaman = 0.0
        self._sure_yuklendi = False
        self.rota_noktalari = []   # [[hamX, hamY], ...]
        self._kayit_calisiyor = False

        # Açıklama paragrafları arayüz kurulurken kaydolur; anahtar
        # onlardan ÖNCE var olmalı.
        self._aciklamalar = []
        # Harita adı -> [market x, market y, npc vid]
        self._marketler = {}
        self._market_haritasi = ""
        self._ui_dunya = None
        self._sekme_anahtarlari = []
        self.aciklama_var = tk.BooleanVar(value=False)

        # MODÜL ANAHTARLARI
        #
        # Hedefleme ve Rota'nın ana anahtarı yoktu: kapatmak için birkaç
        # ayrı kutuyu kapatmak gerekiyordu (canavarlar+metinler, ya da
        # rota noktalarını silmek). Artık ikisi tek anahtarla kapanıyor.
        #
        # Toplama/Market/Wait-hack'e YENİ anahtar EKLENMEDİ — onların
        # zaten var (topla_var, oto_market_var, wh_var). İkinci bir
        # anahtar, iki ayrı "kapalı" durumu demek olurdu.
        self.modul_hedefleme_var = tk.BooleanVar(value=True)
        self.modul_rota_var = tk.BooleanVar(value=True)

        self._stil()
        self._ust()
        self._govde()
        self._alt()

        # Arayüz kurulduktan sonra kayıtlı ayarları uygula
        self.ayarlari_yukle()
        self._kitaplik_tazele()
        self.protocol("WM_DELETE_WINDOW", self._kapat)
        self.after(100, self._kuyrugu_isle)
        # Açılışta adb forward'ı kendiliğinden dene — kullanıcı her seferinde
        # cmd'den uğraşmasın (başarısızsa yalnız uyarı, düğme yine duruyor).
        self.after(300, self._adb_forward)
        threading.Thread(target=self._yoklayici, daemon=True).start()

    # ---- stil ----
    def _stil(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=KOYU, foreground=METIN, fieldbackground=PANEL)
        # Sekme şeridi de kompakt: varsayılan dolgu satır yüksekliğini
        # gereksiz büyütüyor ve 8 sekme iki satıra taşıyordu.
        s.configure("TNotebook", tabmargins=(2, 2, 2, 0), borderwidth=0)
        s.configure("TNotebook.Tab", padding=(6, 2),
                    font=("Segoe UI", 8))
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL)

    # KOMPAKT ÖLÇÜLER
    #
    # Panel "çok karmaşık" görünüyordu ve bunun bir kısmı gerçekten
    # boşluktu: her düğme 12 px yan, 5 px dikey dolgu; her kutu 4 px
    # ara; her yazı 9-10 punto. 80 ayarla çarpılınca ekranın büyük
    # kısmı boş alan oluyordu. Ölçüler tek yerden küçültülüyor —
    # bütün arayüz bu yardımcılardan geçtiği için tek değişiklik
    # her sekmeyi etkiliyor.
    def _btn(self, ana, metin, komut, renk=PANEL, gen=None):
        b = tk.Button(ana, text=metin, command=komut, bg=renk,
                      fg=KOYU if renk in (VURGU, OK, UYARI, ALTIN) else METIN,
                      activebackground=VURGU, activeforeground=KOYU,
                      relief="flat", bd=0, padx=5, pady=3,
                      font=("Segoe UI", 8), cursor="hand2")
        if gen:
            b.configure(width=gen)
        return b

    def _sekme_anahtari(self, baslik, degisken):
        """
        Bir sekmeyi açma/kapama anahtarına bağlar.

        Başlıkta ● (açık) / ○ (kapalı) gösteriliyor: hangi modülün
        çalıştığını görmek için sekmeyi açmak gerekmesin. M2Bob'da da
        modül listesi tek bakışta okunuyor; asıl istenen buydu.
        """
        self._sekme_anahtarlari.append((baslik, degisken))
        degisken.trace_add("write",
                           lambda *a: self._sekme_basliklari())

    def _sekme_basliklari(self):
        for baslik, degisken in self._sekme_anahtarlari:
            kap = self._sekme_kap.get(baslik)
            if kap is None:
                continue
            try:
                self.ayar_defteri.tab(
                    kap, text=("● " if degisken.get() else "○ ") + baslik)
            except Exception:
                pass

    def _aciklama(self, ana, metin):
        """
        Gri açıklama paragrafı — hepsi birden gizlenebilir.

        Arayüzde 83 tane var. Ayarların SAYISI değil, her ayarın altındaki
        4-6 satırlık paragraf panelin "çok karmaşık" görünmesine yol
        açıyordu: bir kez okunup bir daha bakılmayan metinler ekranın
        yarısını kaplıyordu.

        Etiket kendi çerçevesinin içine konuyor. Gizlerken yalnızca etiket
        pack'ten çıkıyor, çerçeve yerinde kalıyor — böylece açıp
        kapatınca kutuların SIRASI bozulmuyor. (Doğrudan pack_forget
        yapılsaydı geri pack sona eklenirdi ve düzen dağılırdı.)
        """
        kap = tk.Frame(ana, bg=PANEL)
        e = tk.Label(kap, text=metin, bg=PANEL, fg=SOLUK, justify="left",
                     anchor="w", font=("Segoe UI", 7))
        if self.aciklama_var.get():
            e.pack(fill="x")
        self._aciklamalar.append(e)
        return kap

    def _aciklama_degistir(self):
        goster = self.aciklama_var.get()
        for e in self._aciklamalar:
            try:
                if goster:
                    e.pack(fill="x")
                else:
                    e.pack_forget()
            except Exception:
                pass

    def _onay(self, ana, metin, degisken, komut=None):
        return tk.Checkbutton(ana, text=metin, variable=degisken, bg=PANEL,
                              fg=METIN, selectcolor=KOYU,
                              activebackground=PANEL, activeforeground=VURGU,
                              font=("Segoe UI", 8), anchor="w",
                              padx=0, pady=0, command=komut)

    def _sayi(self, ana, degisken, mn, mx, adim, gen=8):
        return tk.Spinbox(ana, from_=mn, to=mx, increment=adim,
                          textvariable=degisken, width=gen, bg=KOYU, fg=METIN,
                          insertbackground=METIN, relief="flat",
                          buttonbackground=CIZGI, font=("Consolas", 8))

    # ---- üst şerit ----
    def _ust(self):
        c = tk.Frame(self, bg=PANEL)
        c.pack(fill="x", padx=5, pady=(8, 4))

        tk.Label(c, text="Adres", bg=PANEL, fg=SOLUK).pack(side="left", padx=(10, 4))
        self.adres_var = tk.StringVar(value=VARSAYILAN_ADRES)
        tk.Entry(c, textvariable=self.adres_var, width=20, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat").pack(side="left", pady=3)

        tk.Label(c, text="Token", bg=PANEL, fg=SOLUK).pack(side="left", padx=(12, 4))
        self.token_var = tk.StringVar(value="")
        tk.Entry(c, textvariable=self.token_var, width=12, bg=KOYU, fg=METIN,
                 show="•", insertbackground=METIN, relief="flat").pack(side="left")

        self._btn(c, "adb forward", self._adb_forward).pack(side="left", padx=5)
        self._btn(c, "Bağlan", self._baglan, VURGU).pack(side="left", padx=2)

        self.baglanti_etiket = tk.Label(c, text="● bağlı değil", bg=PANEL,
                                        fg=HATA, font=("Segoe UI", 9, "bold"))
        self.baglanti_etiket.pack(side="left", padx=8)

        self.kapi_etiket = tk.Label(c, text="", bg=PANEL, fg=SOLUK,
                                    font=("Consolas", 9))
        self.kapi_etiket.pack(side="right", padx=8)

        tk.Checkbutton(c, text="? açıklamalar", variable=self.aciklama_var,
                       command=self._aciklama_degistir, bg=PANEL, fg=SOLUK,
                       selectcolor=KOYU, activebackground=PANEL,
                       activeforeground=VURGU, font=("Segoe UI", 8),
                       ).pack(side="right", padx=6)
        self._btn(c, "Sıfırla", self.ayarlari_sifirla).pack(side="right", padx=2)
        self._btn(c, "Ayarları kaydet",
                  lambda: self.ayarlari_kaydet()).pack(side="right", padx=2)

    # ---- gövde ----
    def _govde(self):
        kok = tk.Frame(self, bg=KOYU)
        kok.pack(fill="both", expand=True, padx=5, pady=2)

        sol = tk.Frame(kok, bg=KOYU, width=460)
        sol.pack(side="left", fill="y", padx=(0, 6))
        sol.pack_propagate(False)
        self._ayar_paneli(sol)

        sag = tk.Frame(kok, bg=KOYU)
        sag.pack(side="right", fill="both", expand=True)
        self._istatistik(sag)
        self._log_paneli(sag)

    def _kutu(self, ana, baslik):
        k = tk.LabelFrame(ana, text=" %s " % baslik, bg=PANEL, fg=VURGU,
                          font=("Segoe UI", 8, "bold"), bd=1, relief="solid",
                          labelanchor="nw")
        k.pack(fill="x", pady=2)
        return k

    def _ayar_paneli(self, disKap):
        """
        Sol ayar sütunu.

        Ayarlar çoğalınca BAŞLAT/DURDUR düğmeleri ekranın altında kalıyordu.
        Çözüm: düğmeler en alta SABİTLENİR (her zaman görünür), ayarlar ise
        kaydırılabilir bir tuvale konur.
        """
        # 1) Düğmeler önce pack edilir ki alttan yerini ayırsın
        d = tk.Frame(disKap, bg=KOYU)
        d.pack(side="bottom", fill="x", pady=(6, 0))
        self.basla_btn = self._btn(d, "▶  BAŞLAT", self._basla, OK)
        self.basla_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.dur_btn = self._btn(d, "■  DURDUR", self._dur, HATA)
        self.dur_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))
        self.dur_btn.configure(state="disabled")

        # 2) SEKMELİ ayar alanı
        #
        # Ayarlar tek sütunda alt alta uzuyordu; ilgisiz şeyler karışıyor ve
        # aşağısı görünmüyordu. Her konu kendi sekmesinde.
        self._sekme_kap = {}
        self.ayar_defteri = ttk.Notebook(disKap)
        self.ayar_defteri.pack(fill="both", expand=True)

        def sekme(baslik):
            """Kaydırılabilir bir sekme açar, içine yerleşilecek çerçeveyi verir."""
            dis = tk.Frame(self.ayar_defteri, bg=KOYU)
            self.ayar_defteri.add(dis, text=baslik)
            self._sekme_kap[baslik] = dis
            tuval = tk.Canvas(dis, bg=KOYU, highlightthickness=0)
            cubuk = ttk.Scrollbar(dis, orient="vertical", command=tuval.yview)
            tuval.configure(yscrollcommand=cubuk.set)
            cubuk.pack(side="right", fill="y")
            tuval.pack(side="left", fill="both", expand=True)
            ic = tk.Frame(tuval, bg=KOYU)
            pen = tuval.create_window((0, 0), window=ic, anchor="nw")
            ic.bind("<Configure>",
                    lambda e, t=tuval: t.configure(scrollregion=t.bbox("all")))
            tuval.bind("<Configure>",
                       lambda e, t=tuval, w=pen: t.itemconfigure(w, width=e.width))

            def _tek(e, t=tuval):
                t.yview_scroll(int(-e.delta / 120) * 3, "units")
            tuval.bind("<Enter>",
                       lambda e, t=tuval, f=_tek: t.bind_all("<MouseWheel>", f))
            tuval.bind("<Leave>", lambda e, t=tuval: t.unbind_all("<MouseWheel>"))
            return ic

        # BOT sekmesi EN ÖNDE ama EN SONDA doldurulur.
        #
        # İçindeki denetimler diğer sekmelerdeki tk değişkenlerinin ta
        # kendisi — kopya değil. Aynı değişkene bağlı iki Checkbutton Tk'de
        # kendiliğinden eşleşir, yani ikinci bir "durum" ortaya çıkmıyor ve
        # ayarların ikisi arasında ayrışması mümkün değil. Sekme yalnızca
        # her oturum dokunulan bir avuç ayarı tek ekrana topluyor;
        # gerisi konu sekmelerinde duruyor.
        # SEKME ADLARI KISA.
        #
        # Ayar sütunu 460 px; "● Hedefleme"/"○ Wait-hack" gibi uzun
        # başlıklarla 8 sekme şeride sığmıyor ve Tk onları kesiyordu
        # ("Bc | Gönder | ● Hedefle | ○ Toplan..."). ttk.Notebook ikinci
        # satıra taşmıyor, o yüzden çare adları kısaltmak.
        sk_bot      = sekme("Bot")
        sk_gonderim = sekme("Gönder")
        sk_hedef    = sekme("Hedef")
        sk_topla    = sekme("Topla")
        sk_hareket  = sekme("Hareket")
        sk_wh       = sekme("WH")
        sk_rota     = sekme("Rota")
        sk_market   = sekme("Market")

        # ── kuru çalışma ──
        k0 = self._kutu(sk_gonderim, "Gönderim")
        self.kuru_var = tk.BooleanVar(value=True)
        self._onay(k0, "Kuru çalışma — paket GÖNDERME, sadece logla",
                   self.kuru_var, self._kuru_degisti).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(k0, "Kapatınca gerçekten paket gönderilir.\n"
                          "Aşağıdaki dört anahtarın da açık olması gerekir.").pack(fill="x", padx=5, pady=(0, 2))

        # ── anahtarlar: tıklayınca APK tarafında açılır/kapanır ──
        ka = tk.Frame(k0, bg=PANEL)
        ka.pack(fill="x", padx=5, pady=(0, 3))
        self.anahtar_btn = {}
        anahtarlar = [
            ("paket", "Paket okuyucu",
             "Dünya verisi (konum, canavarlar) buradan gelir"),
            ("proxy", "Proxy",
             "Paket gönderebilmek için oyun bağlantısı proxy'den geçmeli"),
            ("enjeksiyon", "Enjeksiyon",
             "Gönderim ana şalteri"),
            ("kanal", "Kanal: Proxy",
             "Kuyruk çıkışı; Log iken hiçbir şey gönderilmez"),
        ]
        for i, (ad, etiket, ipucu) in enumerate(anahtarlar):
            b = tk.Button(ka, text="✗  " + etiket,
                          command=lambda a=ad: self._anahtar_degistir(a),
                          bg=CIZGI, fg=SOLUK, activebackground=VURGU,
                          activeforeground=KOYU, relief="flat", bd=0,
                          anchor="w", padx=6, pady=2,
                          font=("Segoe UI", 9), cursor="hand2")
            b.grid(row=i, column=0, sticky="ew", pady=1)
            self.anahtar_btn[ad] = b
        ka.columnconfigure(0, weight=1)

        self._btn(k0, "⚡  Hepsini aç (gönderime hazırla)",
                  self._hepsini_ac, UYARI).pack(fill="x", padx=5, pady=(2, 8))

        # ── hedefleme ──
        k1 = self._kutu(sk_hedef, "Hedefleme")
        self.mob_var = tk.BooleanVar(value=True)
        self.metin_var = tk.BooleanVar(value=False)
        self._onay(k1, "▸  HEDEFLEME AÇIK", self.modul_hedefleme_var).pack(
            fill="x", padx=5, pady=(3, 2))
        self.basit_hedefleme_var = tk.BooleanVar(value=True)
        self._onay(k1, "BASİT MOD — menzildeki en yakına vur, koşul arama",
                   self.basit_hedefleme_var).pack(fill="x", padx=5, pady=1)
        self._aciklama(k1,
                       "Açıkken yalnızca üç şeye bakılır: tip, menzil ve\n"
                       "canlı mı. Rota metin avı, av alanı yarıçapı, metin\n"
                       "tıklama onayı gibi kapılar hedeflemeyi ETKİLEMEZ —\n"
                       "rota kendi metin avını ayrıca sürdürür.").pack(
                           fill="x", padx=5, pady=(0, 2))
        self._onay(k1, "Canavarlar", self.mob_var).pack(fill="x", padx=5, pady=1)
        self._onay(k1, "Metin taşları", self.metin_var).pack(fill="x", padx=5, pady=1)

        g = tk.Frame(k1, bg=PANEL)
        g.pack(fill="x", padx=5, pady=2)
        self.tarama_var = tk.IntVar(value=6000)
        self.menzil_var = tk.IntVar(value=2500)
        self.vurus_var = tk.IntVar(value=50)
        for i, (etiket, var, mn, mx, adim) in enumerate([
                ("Arama menzili (ham)", self.tarama_var, 500, 30000, 500),
                ("Saldırı menzili (ham)", self.menzil_var, 300, 20000, 100),
                ("Vuruş aralığı (ms)", self.vurus_var, 50, 5000, 50)]):
            tk.Label(g, text=etiket, bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w", pady=2)
            self._sayi(g, var, mn, mx, adim).grid(row=i, column=1, sticky="e", padx=4)
        tk.Label(g, text="Tur başına vuruş (seri)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=4, column=0, sticky="w",
                                            pady=2)
        self.vurus_seri_var = tk.IntVar(value=4)
        self._sayi(g, self.vurus_seri_var, 1, 20, 1).grid(
            row=4, column=1, sticky="e", padx=4)
        g.columnconfigure(0, weight=1)

        self.coklu_var = tk.BooleanVar(value=True)
        self._onay(k1, "Çoklu hedef (en yakın N canavara birden vur)",
                   self.coklu_var).pack(fill="x", padx=5, pady=1)
        g7 = tk.Frame(k1, bg=PANEL)
        g7.pack(fill="x", padx=5, pady=2)
        tk.Label(g7, text="Aynı anda kaç hedef", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.max_hedef_var = tk.IntVar(value=10)
        self._sayi(g7, self.max_hedef_var, 1, 30, 1).grid(
            row=0, column=1, sticky="e", padx=4)
        g7.columnconfigure(0, weight=1)

        # ── PvP: oyunculara yavaş vur ──
        self.oyuncu_vur_var = tk.BooleanVar(value=False)
        self._onay(k1, "⚠ Vurulabilir OYUNCULARA da vur (PvP)",
                   self.oyuncu_vur_var).pack(fill="x", padx=5, pady=1)
        g9 = tk.Frame(k1, bg=PANEL)
        g9.pack(fill="x", padx=5, pady=2)
        tk.Label(g9, text="Oyuncuya vuruş aralığı (ms)",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.oyuncu_vurus_ms_var = tk.IntVar(value=500)
        self._sayi(g9, self.oyuncu_vurus_ms_var, 100, 10000, 100).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(g9, text="Oyuncu vuruş menzili (ham, 100 ham = 1 m)",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w")
        self.oyuncu_menzil_var = tk.IntVar(value=300)
        self._sayi(g9, self.oyuncu_menzil_var, 100, 5000, 100).grid(
            row=1, column=1, sticky="e", padx=4)
        tk.Label(g9, text="Kendine ve sahibine (üstteki oyuncu adı) VURMAZ. Canavarlar tam "
                          "hızda; oyuncular bu menzil+aralıkla tek tek — yavaş yavaş kesim. "
                          "300 ham = 3 m (gerçek vuruş menzili).",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left",
                 wraplength=300).grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        g9.columnconfigure(0, weight=1)

        self.kilit_var = tk.BooleanVar(value=False)
        self._onay(k1, "Hedef kilidi (ölene kadar bırakma)",
                   self.kilit_var).pack(fill="x", padx=5, pady=1)
        g5 = tk.Frame(k1, bg=PANEL)
        g5.pack(fill="x", padx=5, pady=2)
        tk.Label(g5, text="Kilit süresi (sn, 0 = ölene kadar)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.kilit_sure_var = tk.IntVar(value=0)
        self._sayi(g5, self.kilit_sure_var, 0, 300, 5).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(g5, text="Ev yarıçapı (ham, 0=sınırsız)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.ev_var = tk.IntVar(value=8000)
        self._sayi(g5, self.ev_var, 0, 50000, 1000).grid(
            row=1, column=1, sticky="e", padx=4)
        g5.columnconfigure(0, weight=1)
        self._aciklama(k1, "Rota KAPALIYKEN merkez: botun başladığı nokta.\n"
                          "Rota AÇIKKEN merkez: ROTANIN KENDİSİ — yani\n"
                          "'rotanın bu kadar yakınındaki her şeye saldır'.\n"
                          "Sabit noktaya bağlı kalsaydı rota 80 m'den uzağa\n"
                          "çıkınca bot hiçbir şeye saldırmazdı.").pack(fill="x", padx=5, pady=(0, 3))

        # ── toplama ──
        k2 = self._kutu(sk_topla, "Otomatik Toplama")
        self.topla_var = tk.BooleanVar(value=True)
        self.yang_var = tk.BooleanVar(value=True)
        self.benim_var = tk.BooleanVar(value=True)
        self._onay(k2, "Yerdeki eşyaları topla", self.topla_var).pack(fill="x", padx=5, pady=1)
        self._onay(k2, "Önce Yang", self.yang_var).pack(fill="x", padx=5, pady=1)
        self._onay(k2, "Yalnızca bana ait / sahipsiz olanı topla",
                   self.benim_var).pack(fill="x", padx=5, pady=1)

        g2 = tk.Frame(k2, bg=PANEL)
        g2.pack(fill="x", padx=5, pady=2)
        tk.Label(g2, text="Karakter adı (sahip filtresi)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.ad_var = tk.StringVar(value="")
        tk.Entry(g2, textvariable=self.ad_var, width=14, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat").grid(row=0, column=1,
                                                             sticky="e", padx=4)
        tk.Label(g2, text="Toplama menzili (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.topla_menzil_var = tk.IntVar(value=1500)
        self._sayi(g2, self.topla_menzil_var, 200, 10000, 100).grid(
            row=1, column=1, sticky="e", padx=4)
        g2.columnconfigure(0, weight=1)

        # ── eşya filtresi ──
        tk.Frame(k2, bg=CIZGI, height=1).pack(fill="x", padx=5, pady=2)
        fs = tk.Frame(k2, bg=PANEL)
        fs.pack(fill="x", padx=5, pady=(0, 2))
        tk.Label(fs, text="Filtre", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(side="left")
        self.filtre_mod_var = tk.StringVar(value="hepsi")
        for deger, etiket in (("hepsi", "Hepsi"),
                              ("beyaz", "Sadece bunlar"),
                              ("kara", "Bunlar hariç")):
            tk.Radiobutton(fs, text=etiket, value=deger,
                           variable=self.filtre_mod_var, bg=PANEL, fg=METIN,
                           selectcolor=KOYU, activebackground=PANEL,
                           activeforeground=VURGU, font=("Segoe UI", 8),
                           indicatoron=False, relief="flat",
                           padx=6, pady=2).pack(side="left", padx=2)

        self.filtre_var = tk.StringVar(value="")
        tk.Entry(k2, textvariable=self.filtre_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 font=("Consolas", 9)).pack(fill="x", padx=5, ipady=3)
        self._aciklama(k2, "vnum ya da isim parçası, virgülle:  "
                          "1, 27002, iksir, kolye\n"
                          "(1 = Yang.  \"iksir\" adında iksir geçen her şey.)").pack(fill="x", padx=5, pady=(2, 4))
        self._btn(k2, "Yerdekileri listele (filtreyi dene)",
                  self._filtre_dene).pack(fill="x", padx=5, pady=(0, 3))

        # ── yetenek ──
        k3 = self._kutu(sk_hedef, "Yetenek")
        self.yetenek_var = tk.BooleanVar(value=False)
        self._onay(k3, "Yetenek kullan", self.yetenek_var).pack(fill="x", padx=5, pady=1)
        g3 = tk.Frame(k3, bg=PANEL)
        g3.pack(fill="x", padx=5, pady=2)
        self.yvnum_var = tk.IntVar(value=1)
        self.yms_var = tk.IntVar(value=4000)
        tk.Label(g3, text="Yetenek vnum", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self._sayi(g3, self.yvnum_var, 1, 999, 1).grid(row=0, column=1, sticky="e", padx=4)
        tk.Label(g3, text="Bekleme (ms)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self._sayi(g3, self.yms_var, 500, 60000, 500).grid(row=1, column=1,
                                                           sticky="e", padx=4)
        g3.columnconfigure(0, weight=1)

        # ── wait-hack / devriye ──
        # ── Hareket sekmesi ──
        kh = self._kutu(sk_hareket, "Hareket")
        self.yaklas_var = tk.BooleanVar(value=True)
        self._onay(kh, "Hareket izni — rota / devriye",
                   self.yaklas_var).pack(fill="x", padx=5, pady=1)
        self.hedefe_yuru_var = tk.BooleanVar(value=False)
        self._onay(kh, "Menzil dışındaki HEDEFE yürü",
                   self.hedefe_yuru_var).pack(fill="x", padx=5, pady=1)
        self._aciklama(kh,
                       "Kapalıyken hedefleme karakteri KIMILDATMAZ:\n"
                       "yalnızca menzildekine vurur. Hareketi rota yapar.\n"
                       "\n"
                       "Açıkken menzil dışındaki hedefe 0x07 hareket paketi\n"
                       "gönderilir — haritada 'enjekte konum' olarak görünen\n"
                       "şey budur.\n"
                       "\n"
                       "Bu izin 'Hareket izni'nden AYRI: eskiden ikisi tek\n"
                       "kutuydu ve hedefe yürümeyi kapatmak rotayı da\n"
                       "kapatıyordu.").pack(fill="x", padx=5, pady=(0, 3))
        self.hizala_var = tk.BooleanVar(value=True)
        self._onay(kh, "İSTEMCİYİ de hizala (yol boyunca kademeli)",
                   self.hizala_var).pack(fill="x", padx=5, pady=1)
        my = tk.Frame(kh, bg=PANEL)
        my.pack(fill="x", padx=5, pady=(2, 0))
        self.hizala_yontem_var = tk.StringVar(value="senkron")
        for deger, etiket in (("senkron", "Sürükle (0x05) — çalışan"),
                              ("hareket", "GC_MOVE (0x03) — etkisiz")):
            tk.Radiobutton(my, text=etiket, value=deger,
                           variable=self.hizala_yontem_var, bg=PANEL, fg=METIN,
                           selectcolor=KOYU, activebackground=PANEL,
                           activeforeground=VURGU, font=("Segoe UI", 8),
                           indicatoron=False, relief="flat",
                           padx=6, pady=2).pack(side="left", padx=2)
        self._aciklama(kh, "İstemci kendi karakterinin hareketini KENDİ yönetir;\n"
                          "sunucudan gelen MOVE paketi ona uygulanmaz (canlı\n"
                          "denendi). Bu yüzden koşma animasyonu ağ üzerinden\n"
                          "tetiklenemiyor — karakter kayarak gider. 0x03\n"
                          "seçeneği başka bir istemci sürümü için duruyor.").pack(fill="x", padx=5, pady=(0, 2))

        gz = tk.Frame(kh, bg=PANEL)
        gz.pack(fill="x", padx=5, pady=2)
        tk.Label(gz, text="Hizalama adımı (ms) — sürükle modu", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0,
                                                      sticky="w")
        self.hizala_adim_var = tk.IntVar(value=150)
        self._sayi(gz, self.hizala_adim_var, 50, 1000, 50).grid(
            row=0, column=1, sticky="e", padx=4)
        gz.columnconfigure(0, weight=1)
        self._aciklama(kh, "Yalnızca sürükle modunda kullanılır. Küçük değer =\n"
                          "daha akıcı kayma, daha çok paket.").pack(fill="x", padx=5, pady=(0, 2))
        gn2 = tk.Frame(kh, bg=PANEL)
        gn2.pack(fill="x", padx=5, pady=2)
        tk.Label(gn2, text="Hizalama aralığı (ham, 0 = sadece bacak sonu)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.hizala_mesafe_var = tk.IntVar(value=800)
        self._sayi(gn2, self.hizala_mesafe_var, 0, 10000, 100).grid(
            row=0, column=1, sticky="e", padx=4)
        gn2.columnconfigure(0, weight=1)
        self._aciklama(kh, "800 ham = 8 m, yani ~2 saniyede bir hizalama.\n"
                          "BÜYÜTÜRSEN: karakter daha az düşer ama istemci\n"
                          "daha çok geride kalır. 0 yaparsan market gibi uzun\n"
                          "yollarda istemci hiç takip etmez.\n"
                          "KÜÇÜLTÜRSEN: daha yakın takip, ama hizalama paketi\n"
                          "yükseklik taşımadığı için karakter düşe düşe gider.\n"
                          "Hiç istemiyorsan 'İSTEMCİYİ de hizala'yı kapat.").pack(fill="x", padx=5, pady=(0, 2))

        self._btn(kh, "⏱  Hızımı ÖLÇ (elle koş)", self._hizimi_olc,
                  VURGU).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(kh, "Bas, sonra 10 saniye oyunda ELLE koş. Bot\n"
                          "konumunu örnekleyip gerçek hızını hesaplar ve\n"
                          "yukarıdaki alana yazar. Bineğin/hız iksirin\n"
                          "varsa bu şart: bot yavaş komut yollarsa ayaklar\n"
                          "hızlı, gövde yavaş gider — dışarıdan geriye\n"
                          "kayıyor gibi görünür.").pack(fill="x", padx=5, pady=(0, 2))

        ga = tk.Frame(kh, bg=PANEL)
        ga.pack(fill="x", padx=5, pady=(3, 1))
        tk.Label(ga, text="Karakter adın", bg=PANEL, fg=VURGU,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.karakter_adi_var = tk.StringVar(value="")
        tk.Entry(ga, textvariable=self.karakter_adi_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 font=("Segoe UI", 10)).pack(side="left", fill="x",
                                             expand=True)
        self._aciklama(kh, "EN KOLAY YOL. Oyundaki karakter adını buraya yaz;\n"
                          "vid'i tek eşleşmeyle bulur. vid her girişte\n"
                          "değişiyor, ad değişmiyor — bir kez yazman yeterli.\n"
                          "Kanal değişince yeni vid kendiliğinden bulunur.\n"
                          "Aşağıdaki iki yol yalnızca ad işe yaramazsa lazım.").pack(fill="x", padx=5, pady=(0, 3))

        self.istemci_esas_var = tk.BooleanVar(value=True)
        self._onay(kh, "İSTEMCİ ESAS — ekranda nerede isek orada sayıl",
                   self.istemci_esas_var).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(kh,
                       "Enjekte ettiğimiz konum bir NİYET, istemcinin\n"
                       "bildirdiği bir ÖLÇÜM. Karakter canavara takılınca\n"
                       "ikisi ayrışıyor: sunucuda metine \"varıyoruz\" ama\n"
                       "ekran başka yeri gösteriyor, OCR da etiket de\n"
                       "metini bulamıyor. Bu açıkken bot istemcinin\n"
                       "bulunduğu yere geri sabitlenip oradan devam eder.").pack(
                           fill="x", padx=5, pady=(0, 2))
        gi2 = tk.Frame(kh, bg=PANEL)
        gi2.pack(fill="x", padx=5, pady=2)
        for i, (etiket, degisken, mn, mx, adim) in enumerate((
                ("Sapma sınırı (ham)", None, 100, 10000, 100),
                ("İstemci sabrı (ms)", None, 500, 15000, 500))):
            tk.Label(gi2, text=etiket, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w")
        self.sapma_siniri_var = tk.IntVar(value=800)
        self._sayi(gi2, self.sapma_siniri_var, 100, 10000, 100).grid(
            row=0, column=1, sticky="e", padx=3)
        self.istemci_sabir_var = tk.IntVar(value=3000)
        self._sayi(gi2, self.istemci_sabir_var, 500, 15000, 500).grid(
            row=1, column=1, sticky="e", padx=3)
        gi2.columnconfigure(0, weight=1)

        self.duvar_kacin_var = tk.BooleanVar(value=True)
        self._onay(kh, "DUVARLARA GİRME — oyunun engel haritasını kullan",
                   self.duvar_kacin_var).pack(fill="x", padx=5, pady=(3, 1))
        gdp = tk.Frame(kh, bg=PANEL)
        gdp.pack(fill="x", padx=5, pady=2)
        tk.Label(gdp, text="Engel payı (m) — duvara bu kadar yaklaşma",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8)).grid(
                     row=0, column=0, sticky="w")
        self.duvar_payi_var = tk.IntVar(value=2)
        self._sayi(gdp, self.duvar_payi_var, 0, 8, 1).grid(
            row=0, column=1, sticky="e", padx=3)
        gdp.columnconfigure(0, weight=1)
        self._aciklama(kh,
                       "Yol duvarlara bu kadar yaklaşmıyor. 1 iken bot\n"
                       "engellerin dibinden geçip köşelerde takılıyordu.\n"
                       "Büyütmek dar geçitleri kapatabilir — o zaman\n"
                       "\"yol bulunamadı\" görürsün, bir tık düşür.").pack(
                           fill="x", padx=5, pady=(0, 2))
        self._aciklama(kh, "Oyunun kendi çarpışma verisi (harita/ dizini).\n"
                          "Hedefin önü kapalıysa bot dolanarak gider.\n"
                          "Veri yoksa:  python tools/harita_cikar.py\n"
                          "Yeni bir köyde rota kaydettikten sonra:\n"
                          "             python tools/harita_hizala.py").pack(fill="x", padx=5, pady=(0, 3))

        self._btn(kh, "🔎  Kendi vid'imi SAVAŞTAN bul", self._vid_bul,
                  VURGU).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(kh, "Bot SAVAŞIRKEN bas. 25 saniye gelen savaş\n"
                          "paketlerini dinler, vurduklarımızla eşleştirir\n"
                          "ve doğru vid'i aşağıya yazar. Kayıt almaya\n"
                          "gerek yok.").pack(fill="x", padx=5, pady=(0, 2))

        gv = tk.Frame(kh, bg=PANEL)
        gv.pack(fill="x", padx=5, pady=2)
        tk.Label(gv, text="Kendi vid (0 = otomatik)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.kendi_vid_elle_var = tk.IntVar(value=0)
        tk.Entry(gv, textvariable=self.kendi_vid_elle_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat", width=12,
                 font=("Consolas", 9)).grid(row=0, column=1, sticky="e", padx=4)
        gv.columnconfigure(0, weight=1)
        self._aciklama(kh, "Hizalama BU vid'e gider. Yanlışsa istemci senin\n"
                          "yerine yandaki canavarı/atı sürükler. Otomatik\n"
                          "bulma çoğunluk oyu kullanır; yine de şaşarsa\n"
                          "doğru vid'i buraya yaz.").pack(fill="x", padx=5, pady=(0, 2))
        self._aciklama(kh, "Kapalıyken bot HİÇBİR konum paketi göndermez;\n"
                          "sadece bulunduğu yerden vurur ve toplar.").pack(fill="x", padx=5, pady=(0, 2))

        g6 = tk.Frame(kh, bg=PANEL)
        g6.pack(fill="x", padx=5, pady=2)
        tk.Label(g6, text="Yürüme adımı (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.adim_var = tk.IntVar(value=12000)
        self._sayi(g6, self.adim_var, 300, 30000, 500).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(g6, text="Yürüme hızı (ham/sn)  ← burayı yükselt", bg=PANEL,
                 fg=VURGU,
                 font=("Segoe UI", 8, "bold")).grid(row=1, column=0,
                                                    sticky="w", pady=2)
        self.hiz_var = tk.IntVar(value=2150)
        self._sayi(g6, self.hiz_var, 200, 5000, 10).grid(
            row=1, column=1, sticky="e", padx=4)
        # "En az bekleme (ms)" kaldırıldı: akan yürüyüşe geçince _yuru artık
        # tek bir uyku hesaplamıyor, ritmi "Paket aralığı" belirliyor. Ayar
        # arayüzde durup hiçbir şey yapmasın istemedik.
        tk.Label(g6, text="Paket aralığı (ms) — akış ritmi", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=2, column=0,
                                                      sticky="w", pady=2)
        self.akis_var = tk.IntVar(value=155)
        self._sayi(g6, self.akis_var, 50, 1000, 5).grid(
            row=2, column=1, sticky="e", padx=4)
        tk.Label(g6, text="Bacağın % kaçını yürü (kesintisizlik)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=3, column=0,
                                                      sticky="w", pady=2)
        self.erken_var = tk.IntVar(value=85)
        self._sayi(g6, self.erken_var, 30, 100, 5).grid(
            row=3, column=1, sticky="e", padx=4)
        g6.columnconfigure(0, weight=1)
        self._aciklama(kh, "Bu iki değer GERÇEK İSTEMCİDEN ölçüldü (85 giden\n"
                          "paket): her 155 ms'de bir, ~70 ham ilerlemiş yeni\n"
                          "konum. Bot da aynı ritimde akıtır — tek bir 'şuraya\n"
                          "git' paketi yollamaz, çünkü o yürü-dur-yürü olarak\n"
                          "görünüyordu.\n"
                          "\n"
                          "Hız 430 = 0.43 ham/ms; binek/hız iksiri varsa yükselt\n"
                          "(o zaman adım başına mesafe de büyür).").pack(fill="x", padx=5, pady=(0, 2))

        # ── Rota sekmesi ──
        kr = self._kutu(sk_rota, "Rota Noktaları")
        self._onay(kr, "▸  ROTA AÇIK", self.modul_rota_var).pack(
            fill="x", padx=5, pady=(3, 1))
        self._aciklama(kr, "Oyunda gitmek istediğin yere yürü, sonra\n"
                          "\"Bulunduğum yeri ekle\" de. Noktalar sırayla\n"
                          "gezilir; sonuncudan sonra başa dönülür.").pack(fill="x", padx=5, pady=(3, 2))

        lc = tk.Frame(kr, bg=PANEL)
        lc.pack(fill="both", expand=True, padx=5, pady=2)
        self.rota_liste = tk.Listbox(
            lc, bg=KOYU, fg=METIN, selectbackground=VURGU,
            selectforeground=KOYU, relief="flat", height=8,
            font=("Consolas", 9), activestyle="none")
        cub = ttk.Scrollbar(lc, orient="vertical",
                            command=self.rota_liste.yview)
        self.rota_liste.configure(yscrollcommand=cub.set)
        cub.pack(side="right", fill="y")
        self.rota_liste.pack(side="left", fill="both", expand=True)

        self._btn(kr, "Bulunduğum yeri ekle",
                  self._rota_nokta_ekle, VURGU).pack(fill="x", padx=5, pady=(2, 1))
        sr = tk.Frame(kr, bg=PANEL)
        sr.pack(fill="x", padx=5, pady=2)
        self._btn(sr, "Seçiliyi sil", self._rota_nokta_sil).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        self._btn(sr, "Tümünü temizle", self._rota_temizle).pack(
            side="left", expand=True, fill="x", padx=(2, 0))

        gr = tk.Frame(kr, bg=PANEL)
        gr.pack(fill="x", padx=5, pady=2)
        tk.Label(gr, text="Nokta yarıçapı (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.rota_yaricap_var = tk.IntVar(value=500)
        self._sayi(gr, self.rota_yaricap_var, 100, 5000, 100).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(gr, text="Noktada bekleme (ms)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.rota_bekle_var = tk.IntVar(value=0)
        self._sayi(gr, self.rota_bekle_var, 0, 30000, 250).grid(
            row=1, column=1, sticky="e", padx=4)
        gr.columnconfigure(0, weight=1)

        tk.Label(kr, text="Rota sonuna varınca:", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(fill="x", padx=5, pady=(4, 0))
        mr = tk.Frame(kr, bg=PANEL)
        mr.pack(fill="x", padx=5, pady=(0, 2))
        self.rota_mod_var = tk.StringVar(value="oto")
        for deger, etiket in (("oto", "Otomatik"),
                              ("dongu", "Başa sar"),
                              ("gidis_donus", "Geri dön")):
            tk.Radiobutton(mr, text=etiket, value=deger,
                           variable=self.rota_mod_var, bg=PANEL, fg=METIN,
                           selectcolor=KOYU, activebackground=PANEL,
                           activeforeground=VURGU, font=("Segoe UI", 8),
                           indicatoron=False, relief="flat",
                           padx=6, pady=2).pack(side="left", padx=2)
        self._aciklama(kr, "Otomatik: son nokta ile ilk nokta yan yanaysa (halka\n"
                          "rota) başa sarar, uzaksa geldiği yoldan geri döner.\n"
                          "Düz bir hat kaydettiysen başa sarmak duvardan geçmek\n"
                          "demektir — o yüzden geri dönmesi doğru olandır.").pack(fill="x", padx=5, pady=(0, 2))

        kk = self._kutu(sk_rota, "Rota Kitaplığı")
        self._aciklama(kk, "Gezdiğin rotayı bir adla sakla, sonra listeden\n"
                          "seçip geri yükle. Her harita/köy için ayrı rota\n"
                          "tutabilirsin. Çift tıklamak da yükler.").pack(fill="x", padx=5, pady=(3, 2))

        lk = tk.Frame(kk, bg=PANEL)
        lk.pack(fill="both", expand=True, padx=5, pady=2)
        self.kitaplik_liste = tk.Listbox(
            lk, bg=KOYU, fg=METIN, selectbackground=VURGU,
            selectforeground=KOYU, relief="flat", height=6,
            font=("Consolas", 9), activestyle="none")
        cuk = ttk.Scrollbar(lk, orient="vertical",
                            command=self.kitaplik_liste.yview)
        self.kitaplik_liste.configure(yscrollcommand=cuk.set)
        cuk.pack(side="right", fill="y")
        self.kitaplik_liste.pack(side="left", fill="both", expand=True)
        self.kitaplik_liste.bind("<<ListboxSelect>>", self._kitaplik_secildi)
        self.kitaplik_liste.bind("<Double-Button-1>",
                                 lambda e: self._kitaplik_yukle())

        gk = tk.Frame(kk, bg=PANEL)
        gk.pack(fill="x", padx=5, pady=(2, 1))
        tk.Label(gk, text="Ad", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        self.kitaplik_ad_var = tk.StringVar(value="")
        tk.Entry(gk, textvariable=self.kitaplik_ad_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)

        bk = tk.Frame(kk, bg=PANEL)
        bk.pack(fill="x", padx=5, pady=(1, 3))
        self._btn(bk, "Bu adla kaydet", self._kitaplik_kaydet, VURGU).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        self._btn(bk, "Yükle", self._kitaplik_yukle).pack(
            side="left", expand=True, fill="x", padx=2)
        self._btn(bk, "Sil", self._kitaplik_sil).pack(
            side="left", expand=True, fill="x", padx=(2, 0))

        km = self._kutu(sk_rota, "Rotada Metin Avı")
        self.rota_metin_var = tk.BooleanVar(value=True)
        self._onay(km, "Rotada METİN ara — bulunca git ve kır",
                   self.rota_metin_var).pack(fill="x", padx=5, pady=(3, 1))
        gi = tk.Frame(km, bg=PANEL)
        gi.pack(fill="x", padx=5, pady=2)
        tk.Label(gi, text="Metin adları (boş = hepsi)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self.rota_metin_adlari_var = tk.StringVar(value="")
        tk.Entry(gi, textvariable=self.rota_metin_adlari_var, bg=KOYU,
                 fg=METIN, insertbackground=METIN, relief="flat",
                 font=("Consolas", 9)).pack(fill="x", ipady=3)
        self._aciklama(gi, "ör: karanlik, kiskanclik, siyah\n"
                         "Türkçe-duyarsız, parça eşleşmesi.").pack(fill="x", pady=(0, 2))

        ge = tk.Frame(km, bg=PANEL)
        ge.pack(fill="x", padx=5, pady=2)
        tk.Label(ge, text="Ekran genişlik / yükseklik", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.ekran_genislik_var = tk.IntVar(value=1080)
        self._sayi(ge, self.ekran_genislik_var, 320, 4000, 40).grid(
            row=0, column=1, sticky="e", padx=2)
        self.ekran_yukseklik_var = tk.IntVar(value=1920)
        self._sayi(ge, self.ekran_yukseklik_var, 320, 4000, 40).grid(
            row=0, column=2, sticky="e", padx=2)
        ge.columnconfigure(0, weight=1)

        kd = self._kutu(sk_rota, "Saldırı Düğmesi")
        self._aciklama(kd,
                       "METİNE VURMANIN TEK YOLU BU.\n"
                       "Metin SEÇİM PAKETİYLE seçilir (vid zaten elimizde),\n"
                       "sonra sağ alttaki kılıç düğmesine basılır. Düğme\n"
                       "SABİT yerde olduğu için nişan alma derdi hiç yok;\n"
                       "vuruşlar da istemcinin kendi zamanlamasıyla gidiyor.\n"
                       "Yerini bir kez kaydet:\n"
                       "    python tools/saldiri_dugmesi.py\n"
                       "0,0 ise klasik paket saldırısı kullanılır.").pack(
                           fill="x", padx=5, pady=(3, 2))
        gd = tk.Frame(kd, bg=PANEL)
        gd.pack(fill="x", padx=5, pady=2)
        for i, (etiket, ad, mn, mx, adim) in enumerate((
                ("Düğme dokunma X", "saldiri_dugme_x_var", 0, 4000, 10),
                ("Düğme dokunma Y", "saldiri_dugme_y_var", 0, 4000, 10),
                ("Kaç kez bas", "saldiri_basma_var", 1, 20, 1),
                ("Basışlar arası (ms)", "saldiri_basma_ms_var", 50, 3000,
                 10))):
            tk.Label(gd, text=etiket, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w")
            v = tk.IntVar(value={"saldiri_basma_var": 5,
                                 "saldiri_basma_ms_var": 220}.get(ad, 0))
            setattr(self, ad, v)
            self._sayi(gd, v, mn, mx, adim).grid(row=i, column=1,
                                                 sticky="e", padx=3)
        gd.columnconfigure(0, weight=1)
        self._btn(kd, "Düğmeye ŞİMDİ bas (deneme)",
                  self._saldiri_dugmesi_dene).pack(fill="x", padx=5,
                                                   pady=(2, 3))

        self.metin_paket_secim_var = tk.BooleanVar(value=True)
        self._onay(km, "SEÇİM PAKETİ + DÜĞME",
                   self.metin_paket_secim_var).pack(fill="x", padx=5,
                                                    pady=(3, 1))
        self._aciklama(km,
                       "Metinin vid'i zaten elimizde ve yanına kadar\n"
                       "yürüyoruz: seçimi paketle gönderip saldırı\n"
                       "düğmesine basmak yetiyor.\n"
                       "\n"
                       "Kalibrasyon, OCR ve ekrana tıklama KALDIRILDI —\n"
                       "üçü de aynı soruyu çözmeye çalışıyordu: 'hangi\n"
                       "piksele basayım'. Üçü de değişken bir hedefe nişan\n"
                       "alıyordu ve hiçbiri güvenilir olmadı. Düğme sabit.\n"
                       "\n"
                       "DUGME VE PAKET BIRLIKTE: dugme vurusu istemciye\n"
                       "baslatir, paketler hizi verir. Dugmeye her turda\n"
                       "degil, 3 saniyede bir basilir - 5 basis ~1.1 sn\n"
                       "suruyor ve her turda yapilinca hizli vurusun\n"
                       "onunu tikiyordu.").pack(
                           fill="x", padx=5, pady=(0, 3))
        self.sadece_metin_canavari_var = tk.BooleanVar(value=True)
        self._onay(km, "SADECE metinden çıkan canavarlara vur",
                   self.sadece_metin_canavari_var).pack(
                       fill="x", padx=5, pady=1)
        self.rota_kendi_saldiri_var = tk.BooleanVar(value=True)
        self._onay(km, "Rotanın KENDİ vuruşu (Hedefleme kapalı olsa da)",
                   self.rota_kendi_saldiri_var).pack(
                       fill="x", padx=5, pady=1)
        gm = tk.Frame(km, bg=PANEL)
        gm.pack(fill="x", padx=5, pady=2)
        tk.Label(gm, text="Metin arama menzili (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.rota_metin_menzil_var = tk.IntVar(value=6000)
        self._sayi(gm, self.rota_metin_menzil_var, 500, 30000, 500).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(gm, text="Yaklaşma mesafesi (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.metin_yaklasma_var = tk.IntVar(value=300)
        self._sayi(gm, self.metin_yaklasma_var, 50, 3000, 50).grid(
            row=1, column=1, sticky="e", padx=4)
        tk.Label(gm, text="Canavar penceresi (sn)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=4, column=0, sticky="w",
                                            pady=2)
        self.metin_savas_suresi_var = tk.IntVar(value=30)
        self._sayi(gm, self.metin_savas_suresi_var, 5, 300, 5).grid(
            row=4, column=1, sticky="e", padx=4)
        tk.Label(gm, text="Can %0 sabrı (sn, 0=süresiz)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=5, column=0,
                                                      sticky="w", pady=2)
        self.sifir_can_sabri_var = tk.IntVar(value=20)
        self._sayi(gm, self.sifir_can_sabri_var, 0, 120, 5).grid(
            row=5, column=1, sticky="e", padx=4)
        gm.columnconfigure(0, weight=1)
        self._aciklama(km, "HEDEFLEME SEKMESİNDEN BAĞIMSIZDIR.\n"
                          "Rota metini arar ve kırar; metinden çıkan\n"
                          "canavarları Hedefleme sekmesi halleder.\n"
                          "Yani Hedefleme'de 'Canavarlar' AÇIK kalsın,\n"
                          "'Metin taşları' KAPALI olsun — yoksa bot metin\n"
                          "peşinde rotayı bırakır.\n"
                          "\n"
                          "Metin varken rota ilerlemez; metin bitince\n"
                          "kaldığı noktadan devam eder.\n"
                          "\n"
                          "YAKLAŞMA MESAFESİ: hedefin kaç ham yakınına\n"
                          "kadar yürünecek. Saldırı menzili sunucunun\n"
                          "gerçek vuruş alanından geniş olabiliyor;\n"
                          "'menzile girdim' deyip durmak yetmiyordu.\n"
                          "300 = 3 m. Hâlâ vuramıyorsa 150'ye indir.\n"
                          "\n"
                          "TIKLAMA: gerçek oyuncu metine tıklayarak saldırı\n"
                          "başlatır (0x1A). Bot doğrudan hedefle+saldır\n"
                          "yollayınca trafik deseni ayrışıyordu. Yalnızca\n"
                          "hedef değiştiğinde ve yenileme süresi dolunca\n"
                          "gönderilir.\n"
                          "\n"
                          "SADECE METİN CANAVARI: metin kırılınca içinden\n"
                          "çıkanlara vurulur, yolda rastlananlara vurulmaz.\n"
                          "Metin kırılınca yok olduğu için 'yakında metin\n"
                          "var mı' diye bakılamaz; onun yerine metine son\n"
                          "vuruştan sonraki CANAVAR PENCERESİ kullanılır.\n"
                          "\n"
                          "CAN %0 SABRI: can sıfırlanınca metin ÖLMÜŞ\n"
                          "sayılmaz — hâlâ ayakta olabilir ve vurulmaya\n"
                          "devam etmesi gerekir. Gerçek ölüm işareti varlığın\n"
                          "listeden düşmesi. Bu süre yalnızca takılı kalmış\n"
                          "bir cesede sonsuza kadar vurmamak için.\n"
                          "\n"
                          "ROTANIN KENDİ VURUŞU: rota metini bulup tıklayınca\n"
                          "saldırıyı kendi açar. Hedefleme sekmesindeki\n"
                          "kutular KAPALI olsa bile metine ve ondan çıkan\n"
                          "canavarlara vurulur; pencere kapanınca durur.").pack(fill="x", padx=5, pady=(0, 3))

        kk = self._kutu(sk_rota, "Tur Bitince Kanal Değiştir")
        self.kanal_degistir_var = tk.BooleanVar(value=False)
        self._onay(kk, "Rota turu bitince sıradaki kanala geç",
                   self.kanal_degistir_var).pack(fill="x", padx=5, pady=(3, 1))
        self.metin_ara_var = tk.BooleanVar(value=False)
        self._onay(kk, "METİN ARA — metin yoksa kanal değiştir, görürse kal",
                   self.metin_ara_var).pack(fill="x", padx=5, pady=1)
        gma = tk.Frame(kk, bg=PANEL)
        gma.pack(fill="x", padx=5, pady=2)
        tk.Label(gma, text="Metin kaybolunca kanal değişimi (sn)", bg=PANEL,
                 fg=SOLUK, font=("Segoe UI", 8)).grid(row=0, column=0,
                                                      sticky="w")
        self.metin_ara_sure_var = tk.IntVar(value=20)
        self._sayi(gma, self.metin_ara_sure_var, 5, 600, 5).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(gma, text="Yeni kanalda metin yoksa geç (sn)", bg=PANEL,
                 fg=SOLUK, font=("Segoe UI", 8)).grid(row=1, column=0,
                                                      sticky="w", pady=(2, 0))
        self.metin_ara_yeni_sure_var = tk.IntVar(value=3)
        self._sayi(gma, self.metin_ara_yeni_sure_var, 1, 60, 1).grid(
            row=1, column=1, sticky="e", padx=4, pady=(2, 0))
        gma.columnconfigure(0, weight=1)
        self._aciklama(kk,
                       "METİN ARA açıkken bot görünen metinlere bakar\n"
                       "(Metin adları filtresi geçerli). Metin varsa\n"
                       "kanalda kalır. Yeni girdiği kanalda metin yoksa\n"
                       "'yeni kanalda' süresi sonunda, metin kırılıp\n"
                       "kaybolunca üstteki süre sonunda sıradaki kanala\n"
                       "geçer. Dövüşürken kanal değiştirmez.\n"
                       "Açıkken 'tur bitince kanal değiştir' devre dışı\n"
                       "kalır. Kanalı aşağıdaki dokunma dizisi değiştirir.\n"
                       "\n"
                       "Metin Süre Tutucu açıksa (Bot sekmesi) sayacı süren\n"
                       "(turuncu) kanalları ATLAR, önce süresi dolanlara\n"
                       "(yeşil) gider. Hepsi turuncuysa ilk dolacak olanı\n"
                       "bekler. Boş kanala kendisi sayaç başlatmaz."
                       ).pack(fill="x", padx=5, pady=(0, 3))
        gk = tk.Frame(kk, bg=PANEL)
        gk.pack(fill="x", padx=5, pady=2)
        tk.Label(gk, text="Kanallar", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.kanallar_var = tk.StringVar(value="1,2,3,4,5,6,7,8")
        tk.Entry(gk, textvariable=self.kanallar_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat", width=16,
                 font=("Consolas", 9)).grid(row=0, column=1, sticky="e", padx=4)
        tk.Label(gk, text="Elle geçmen için bekleme (ms)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.kanal_bekleme_var = tk.IntVar(value=120000)
        self._sayi(gk, self.kanal_bekleme_var, 30000, 600000, 30000).grid(
            row=1, column=1, sticky="e", padx=4)
        tk.Label(gk, text="Tur için en az nokta (0 = kapalı)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=2, column=0,
                                                      sticky="w", pady=2)
        self.tur_en_az_nokta_var = tk.IntVar(value=0)
        self._sayi(gk, self.tur_en_az_nokta_var, 0, 500, 10).grid(
            row=2, column=1, sticky="e", padx=4)
        tk.Label(gk, text="Menü beklemesi en fazla (ms, 0 = kayıttaki)",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8)).grid(
                     row=3, column=0, sticky="w", pady=2)
        self.kanal_menu_bekle_var = tk.IntVar(value=1000)
        self._sayi(gk, self.kanal_menu_bekle_var, 0, 10000, 100).grid(
            row=3, column=1, sticky="e", padx=4)
        gk.columnconfigure(0, weight=1)
        self.kanal_bekle_var = tk.BooleanVar(value=True)
        self._onay(kk, "Elle geçmemi BEKLE (kapalıysa botu durdurur)",
                   self.kanal_bekle_var).pack(fill="x", padx=5, pady=1)
        tk.Label(kk, text="Kanal menüsü dokunma dizisi", bg=PANEL,
                 fg=VURGU, font=("Segoe UI", 8, "bold")).pack(
                     fill="x", padx=5, pady=(6, 0))
        self.kanal_dokunma_kutu = tk.Text(
            kk, height=6, bg=KOYU, fg=METIN, insertbackground=METIN,
            relief="flat", font=("Consolas", 9), wrap="none")
        self.kanal_dokunma_kutu.pack(fill="x", padx=5, pady=2)
        self._btn(kk, "▶  Dokunma dizisini DENE", self._dokunma_dene,
                  VURGU).pack(fill="x", padx=5, pady=2)
        self._aciklama(kk, "Satır başına bir komut:\n"
                          "    tap 540 1180\n"
                          "    bekle 800\n"
                          "    tus 4\n"
                          "\n"
                          "Koordinatta {..} içinde k = kanal numarası:\n"
                          "    tap 320 {700+k*90}   -> ch3 icin 970\n"
                          "\n"
                          "Kaydetmek için:  python tools/dokunma_kaydet.py\n"
                          "Sen elle kanal değiştirirken dokunuşlarını\n"
                          "yakalar ve buraya yapıştırılacak diziyi verir.\n"
                          "\n"
                          "Koordinatlar BU CİHAZA özeldir; çözünürlük ya\n"
                          "da menü değişirse yeniden kaydet.").pack(fill="x", padx=5, pady=(0, 2))
        self._aciklama(kk, "Kanal değişimi PAKETLE YAPILAMIYOR — ölçüldü:\n"
                          "kanallar ayrı sunucular, port = 30000 + 4×kanal\n"
                          "(ch1=30004, ch2=30008 ... ch8=30032). İstemcinin\n"
                          "yeniden bağlanması gerekiyor, bunu bot yapamaz.\n"
                          "\n"
                          "Bot tur bitince DURUR ve hangi kanala geçmen\n"
                          "gerektiğini söyler. Sen elle geçince bunu\n"
                          "ALGILAR ve kendiliğinden devam eder.").pack(fill="x", padx=5, pady=(1, 3))

        self.rota_gez_var = tk.BooleanVar(value=False)
        self._onay(kr, "Hedef yokken ROTADA GEZ",
                   self.rota_gez_var).pack(fill="x", padx=5, pady=(2, 1))
        self.sadece_rota_var = tk.BooleanVar(value=False)
        self._onay(kr, "Sadece rota — savaşma, toplama yapma",
                   self.sadece_rota_var).pack(fill="x", padx=5, pady=(0, 3))

        # ── kayıt ──
        kk = self._kutu(sk_rota, "Rota Kaydı")
        self._aciklama(kk, "Kayda bas, oyunda GEZ. Bot belirli aralıklarla\n"
                          "konumunu alıp nokta ekler. Aynı yerde durursan\n"
                          "nokta eklenmez — sadece yeterince ilerleyince.").pack(fill="x", padx=5, pady=(3, 2))
        gk = tk.Frame(kk, bg=PANEL)
        gk.pack(fill="x", padx=5, pady=2)
        tk.Label(gk, text="Örnekleme (ms)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.kayit_aralik_var = tk.IntVar(value=1000)
        self._sayi(gk, self.kayit_aralik_var, 200, 10000, 100).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(gk, text="En az mesafe (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.kayit_mesafe_var = tk.IntVar(value=800)
        self._sayi(gk, self.kayit_mesafe_var, 100, 10000, 100).grid(
            row=1, column=1, sticky="e", padx=4)
        gk.columnconfigure(0, weight=1)
        self.kayit_btn = self._btn(kk, "⏺  Rota kaydına başla",
                                   self._rota_kayit_degistir, UYARI)
        self.kayit_btn.pack(fill="x", padx=5, pady=(4, 8))

        # ── çalıştır ──
        kc = self._kutu(sk_rota, "Çalıştır")
        self.rota_basla_btn = self._btn(kc, "▶  ROTADA GEZMEYE BAŞLA",
                                        self._rotada_gez_basla, OK)
        self.rota_basla_btn.pack(fill="x", padx=5, pady=(6, 8))

        # ── Market sekmesi ──
        km = self._kutu(sk_market, "Markete Sat")
        tk.Label(km, text="Envanteri GÖREMİYORUZ — sunucu envanter durumunu\n"
                          "bildirmiyor. Hangi slotların satılacağını sen seç.\n"
                          "Boş slot zararsız, ama DOLU ve değerli slot satılır!",
                 bg=PANEL, fg=UYARI, justify="left",
                 font=("Segoe UI", 8)).pack(fill="x", padx=5, pady=(3, 2))

        gm = tk.Frame(km, bg=PANEL)
        gm.pack(fill="x", padx=5, pady=2)
        alanlar = [("NPC vid (0 = en yakın)", "npc_vid_var", 0, 0, 99999999, 1),
                   ("İlk slot", "slot_bas_var", 25, 0, 255, 1),
                   ("Son slot", "slot_son_var", 45, 0, 255, 1),
                   ("Her slottan adet", "satis_adet_var", 1, 1, 200, 1),
                   ("Satışlar arası (ms)", "satis_gecikme_var", 250, 50, 3000, 50)]
        for i, (etiket, ad, vars_, mn, mx, adim) in enumerate(alanlar):
            tk.Label(gm, text=etiket, bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w", pady=1)
            v = tk.IntVar(value=vars_)
            setattr(self, ad, v)
            self._sayi(gm, v, mn, mx, adim).grid(row=i, column=1, sticky="e", padx=4)
        gm.columnconfigure(0, weight=1)

        self._btn(km, "Son tıkladığım NPC`nin vid`ini al",
                  self._npc_vid_ogren, VURGU).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(km, "Dükkân NPC`leri hareket etmediği için bot onları\n"
                          "çoğu zaman göremez. Oyunda NPC`ye bir kez TIKLA,\n"
                          "sonra bu düğmeye bas — vid otomatik dolar.").pack(fill="x", padx=5, pady=(0, 2))

        self._btn(km, "NPC`ye git ve dükkânı aç",
                  self._markete_git).pack(fill="x", padx=5, pady=(3, 1))
        self._btn(km, "Seçili slotları SAT",
                  self._satisa_basla, UYARI).pack(fill="x", padx=5, pady=2)
        self._btn(km, "Dükkânı kapat",
                  self._dukkani_kapat).pack(fill="x", padx=5, pady=(2, 8))

        ku = self._kutu(sk_market, "Envanter Uyarısı")
        self.uyari_izle_var = tk.BooleanVar(value=True)
        self._onay(ku, "Sistem uyarısını izle (envanter dolu)",
                   self.uyari_izle_var).pack(fill="x", padx=5, pady=(3, 1))
        gu = tk.Frame(ku, bg=PANEL)
        gu.pack(fill="x", padx=5, pady=2)
        tk.Label(gu, text="Aranan metin parçası", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.uyari_metin_var = tk.StringVar(value="fazla eşya")
        tk.Entry(gu, textvariable=self.uyari_metin_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 width=18).grid(row=0, column=1, sticky="e", padx=4)
        gu.columnconfigure(0, weight=1)
        self._aciklama(ku, "Sunucu envanter durumunu bildirmiyor; tek\n"
                          "göstergemiz bu sistem mesajı. Görülünce bot\n"
                          "durur ve seni uyarır.").pack(fill="x", padx=5, pady=(0, 2))
        self._btn(ku, "Son sistem mesajlarını göster",
                  self._sistem_mesajlari).pack(fill="x", padx=5, pady=(1, 3))

        kn = self._kutu(sk_market, "Market Noktası")
        gn = tk.Frame(kn, bg=PANEL)
        gn.pack(fill="x", padx=5, pady=(3, 1))
        tk.Label(gn, text="Market X (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.market_x_var = tk.IntVar(value=0)
        self._sayi(gn, self.market_x_var, 0, 30000000, 100, gen=11).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(gn, text="Market Y (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.market_y_var = tk.IntVar(value=0)
        self._sayi(gn, self.market_y_var, 0, 30000000, 100, gen=11).grid(
            row=1, column=1, sticky="e", padx=4)
        gn.columnconfigure(0, weight=1)
        self._btn(kn, "Bulunduğum yeri market noktası yap",
                  self._market_noktasi_al, VURGU).pack(fill="x", padx=5, pady=2)

        self._btn(kn, "🏪  MARKETE GİT — şimdi", self._markete_git,
                  VURGU).pack(fill="x", padx=5, pady=(3, 1))
        self._aciklama(kn, "Envanter uyarısını beklemez. Bot çalışıyorsa\n"
                          "sıradaki turda gider; kapalıysa tek seferlik\n"
                          "gidip satar ve bulunduğun yere döner.").pack(fill="x", padx=5, pady=(0, 2))

        self.oto_market_var = tk.BooleanVar(value=False)
        self._onay(kn, "Uyarı gelince OTOMATİK markete git, sat, dön",
                   self.oto_market_var).pack(fill="x", padx=5, pady=(4, 1))
        self._aciklama(kn, "Kapalıyken bot sadece durur ve seni uyarır.\n"
                          "Açıksa: markete yürür, NPC`ye tıklar, seçili\n"
                          "slotları satar, dükkânı kapatır ve av yerine döner.\n"
                          "NPC vid ve slot aralığı DOĞRU olmalı.").pack(fill="x", padx=5, pady=(0, 8))

        k4 = self._kutu(sk_wh, "Wait-hack")
        self.wh_var = tk.BooleanVar(value=False)   # bu sunucuda çalışmıyor
        self._onay(k4, "Wait-hack (ışınlan-vur-dön)", self.wh_var).pack(
            fill="x", padx=5, pady=1)
        tk.Label(k4,
                 text="⚠ Bu sunucuda ÇALIŞMIYOR — iki ayrı sebepten.\n"
                      "\n"
                      "1) Sunucu IŞINLAMIYOR: hareketi kabul eder ama\n"
                      "   yürüterek götürür (~13 m/s, ölçüldü).\n"
                      "\n"
                      "2) SALDIRI MENZİLİ 4 m. 6 Eyl 2026'da 756 vuruş\n"
                      "   örneklendi (tools/wh_teshis.py):\n"
                      "     0-1 m  %98-100 isabet\n"
                      "     2-3 m  %71-90\n"
                      "     4 m    son isabet\n"
                      "     5 m+   HİÇ isabet yok\n"
                      "\n"
                      "WH'nin bütün fikri uzaktan vurmaktı; sunucu buna\n"
                      "izin vermiyor. Bunun yerine \"hedefe yürü\" kullan.\n"
                      "Menzil ayarını 400 hamın üstüne çıkarmak yalnızca\n"
                      "boşa paket gönderir.",
                 bg=PANEL, fg=UYARI, justify="left",
                 font=("Segoe UI", 8)).pack(fill="x", padx=5, pady=(0, 2))
        g4 = tk.Frame(k4, bg=PANEL)
        g4.pack(fill="x", padx=5, pady=2)
        tk.Label(g4, text="WH menzili (ham)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.wh_menzil_var = tk.IntVar(value=6000)
        self._sayi(g4, self.wh_menzil_var, 500, 30000, 500).grid(
            row=0, column=1, sticky="e", padx=4)
        tk.Label(g4, text="Pencere bekleme (ms)", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.wh_bekleme_var = tk.IntVar(value=400)
        self._sayi(g4, self.wh_bekleme_var, 0, 3000, 50).grid(
            row=1, column=1, sticky="e", padx=4)
        g4.columnconfigure(0, weight=1)

        self.wh_pencere_var = tk.BooleanVar(value=True)
        self._onay(k4, "Pencere bekle (istemcinin sessiz anını kolla)",
                   self.wh_pencere_var).pack(fill="x", padx=5, pady=1)
        self.wh_dur_var = tk.BooleanVar(value=False)
        self._onay(k4, "WH dizisine DUR paketi ekle (şüpheli)",
                   self.wh_dur_var).pack(fill="x", padx=5, pady=1)
        self.wh_donus_var = tk.BooleanVar(value=False)
        self._onay(k4, "Vurduktan sonra eski konuma dön",
                   self.wh_donus_var).pack(fill="x", padx=5, pady=1)
        self._aciklama(k4, "Sunucu kendi hareketini sana geri yollamaz; istemci\n"
                      "kendi konumunu tekrar bildirince enjekte ettiğin konum\n"
                      "silinir. Bu seçenek, istemcinin sessiz olduğu ana\n"
                      "denk getirir.  KARAKTERİ ELLE OYNATMA — dururken\n"
                      "istemci saniyelerce susar, pencere çok büyür.").pack(fill="x", padx=5, pady=(0, 2))
        self.devriye_var = tk.BooleanVar(value=False)
        self._onay(kh, "Hedef yoksa rotada devriye gez",
                   self.devriye_var).pack(fill="x", padx=5, pady=(1, 3))

        # ── BOT sekmesi: her oturum dokunulan ayarlar ──
        #
        # Denetimler diğer sekmelerdekiyle AYNI tk değişkenlerine bağlı,
        # kopya değil: Tk aynı değişkene bağlı iki kutuyu kendiliğinden
        # eşler, dolayısıyla ikinci bir durum yok ve ayrışmaları mümkün
        # değil. Burada yeni hiçbir ayar tanımlanmıyor.
        # MODÜL LİSTESİ — her satır bir sekmeyi açıp kapatıyor.
        #
        # Beş modülden yalnızca istediklerini çalıştırabilirsin: sadece
        # hedefleme, ya da sadece rota. Anahtarlar sekmelerin KENDİ ana
        # anahtarları; burada ikinci bir kopya yok.
        kmod = self._kutu(sk_bot, "Modüller")
        for etiket, sekme_adi, degisken, aciklama in (
                ("Hedefleme", "Hedef", self.modul_hedefleme_var,
                 "canavar ve metin döv"),
                ("Toplama", "Topla", self.topla_var, "yerdeki eşyaları al"),
                ("Rota", "Rota", self.modul_rota_var, "kaydedilen yolu gez"),
                ("Market", "Market", self.oto_market_var, "dolunca satmaya git"),
                ("Wait-hack", "WH", self.wh_var, "ışınlanma penceresi")):
            sr = tk.Frame(kmod, bg=PANEL)
            sr.pack(fill="x", padx=5, pady=1)
            self._onay(sr, etiket, degisken).pack(side="left")
            tk.Label(sr, text="— " + aciklama, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 8)).pack(side="left", padx=4)
            # Kutu etiketi UZUN, sekme basligi KISA: sekme seridine
            # sigsin diye kisaltildi ama listede tam adi okumak daha iyi.
            self._sekme_anahtari(sekme_adi, degisken)
        self._aciklama(kmod,
                       "Kapalı modül hiç çalışmaz; altındaki ayarlar da\n"
                       "kapalı sayılır. Sekme başlığındaki ● açık, ○ kapalı\n"
                       "demek. Yalnızca Hedefleme açıksa bot yerinde durup\n"
                       "çevresini döver; yalnızca Rota açıksa savaşmadan\n"
                       "gezer.").pack(fill="x", padx=5, pady=(1, 3))

        kb = self._kutu(sk_bot, "Çalışma")
        self._onay(kb, "Kuru çalışma — paket GÖNDERME, sadece logla",
                   self.kuru_var, self._kuru_degisti).pack(
                       fill="x", padx=5, pady=(3, 1))
        gb = tk.Frame(kb, bg=PANEL)
        gb.pack(fill="x", padx=5, pady=(4, 6))
        tk.Label(gb, text="Karakter adın", bg=PANEL, fg=VURGU,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        tk.Entry(gb, textvariable=self.karakter_adi_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 font=("Segoe UI", 10)).pack(side="left", fill="x",
                                             expand=True)

        kv = self._kutu(sk_bot, "Neye Vursun")
        self._onay(kv, "Canavarlar", self.mob_var).pack(
            fill="x", padx=5, pady=(3, 1))
        self._onay(kv, "Metin taşları", self.metin_var).pack(
            fill="x", padx=5, pady=(1, 3))

        kx = self._kutu(sk_bot, "Rota")
        self._onay(kx, "Rotada METİN ara — bulunca git ve kır",
                   self.rota_metin_var).pack(fill="x", padx=5, pady=(3, 1))
        gx = tk.Frame(kx, bg=PANEL)
        gx.pack(fill="x", padx=5, pady=2)
        tk.Label(gx, text="Metin adları", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(anchor="w")
        tk.Entry(gx, textvariable=self.rota_metin_adlari_var, bg=KOYU,
                 fg=METIN, insertbackground=METIN, relief="flat",
                 font=("Segoe UI", 9)).pack(fill="x")
        self._onay(kx, "Tur bitince kanal değiştir",
                   self.kanal_degistir_var).pack(fill="x", padx=5, pady=1)
        self._onay(kx, "Metin ara — metin yoksa kanal değiştir",
                   self.metin_ara_var).pack(fill="x", padx=5, pady=1)
        self._onay(kx, "Duvarlara girme — engel haritasını kullan",
                   self.duvar_kacin_var).pack(fill="x", padx=5, pady=(1, 3))

        kma = self._kutu(sk_bot, "Metin Ara Tuşu")
        gta = tk.Frame(kma, bg=PANEL)
        gta.pack(fill="x", padx=5, pady=(3, 2))
        tk.Label(gta, text="Kanal aralığı", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(side="left")
        self.metin_ara_ch_bas_var = tk.IntVar(value=1)
        self.metin_ara_ch_son_var = tk.IntVar(value=8)
        self._sayi(gta, self.metin_ara_ch_son_var, 1, 8, 1, gen=3).pack(
            side="right", padx=(2, 4))
        tk.Label(gta, text="–", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(side="right")
        self._sayi(gta, self.metin_ara_ch_bas_var, 1, 8, 1, gen=3).pack(
            side="right", padx=(0, 2))
        self.metin_ara_btn = self._btn(kma, "▶ METİN ARA BAŞLAT",
                                       self._metin_ara_tus, OK)
        self.metin_ara_btn.pack(fill="x", padx=5, pady=(1, 2))
        gss = tk.Frame(kma, bg=PANEL)
        gss.pack(fill="x", padx=0, pady=(0, 1))
        self.metin_ara_ses_var = tk.BooleanVar(value=True)
        self._onay(gss, "Metin bulunca ses çal",
                   self.metin_ara_ses_var).pack(side="left", padx=5)
        self.metin_ara_ses_btn = self._btn(gss, "🔊 Dene",
                                           lambda: bildirim_sesi())
        self.metin_ara_ses_btn.pack(side="right", padx=5)
        self.metin_ara_etiket = tk.Label(kma, text="kapalı", bg=PANEL, fg=SOLUK,
                                         font=("Segoe UI", 8), anchor="w")
        self.metin_ara_etiket.pack(fill="x", padx=5, pady=(0, 1))
        self._aciklama(kma,
                       "Bot kapalıyken de çalışır. Aralıktaki kanalları\n"
                       "sırayla gezer (1–4: 1, 2, 3, 4, 1, ...). Metin\n"
                       "görürse o kanalda durur; metin kırılıp kaybolunca\n"
                       "devam eder. Süreler, metin adları ve dokunma\n"
                       "dizisi Rota sekmesindeki METİN ARA ayarlarından."
                       ).pack(fill="x", padx=5, pady=(0, 3))

        km_s = self._kutu(sk_bot, "Metin Süre Tutucu")
        self.metin_sure_var = tk.BooleanVar(value=True)
        self._onay(km_s, "Kırılan metin için kanal bazlı süre tut",
                   self.metin_sure_var).pack(fill="x", padx=5, pady=(3, 1))
        gs = tk.Frame(km_s, bg=PANEL)
        gs.pack(fill="x", padx=5, pady=2)
        tk.Label(gs, text="Metin yeniden doğma süresi (dk)", bg=PANEL,
                 fg=SOLUK, font=("Segoe UI", 8)).grid(row=0, column=0,
                                                      sticky="w")
        self.metin_sure_dk_var = tk.IntVar(value=15)
        self._sayi(gs, self.metin_sure_dk_var, 1, 180, 1).grid(
            row=0, column=1, sticky="e", padx=4)
        gs.columnconfigure(0, weight=1)
        self.metin_sure_oto_var = tk.BooleanVar(value=False)
        self._onay(km_s, "Kırılınca otomatik başlat (yakındaki metin)",
                   self.metin_sure_oto_var).pack(fill="x", padx=5, pady=1)
        self.metin_sure_tekrar_var = tk.BooleanVar(value=True)
        self._onay(km_s, "Süre bitince tekrar başlat (bir kez bas yeter)",
                   self.metin_sure_tekrar_var).pack(fill="x", padx=5, pady=1)
        # Sayaçlar kalıcı: uygulama kapanıp açılınca kaybolmasın.
        self.metin_sure_kayit_var = tk.StringVar(value="")
        gk_s = tk.Frame(km_s, bg=PANEL)
        gk_s.pack(fill="x", padx=5, pady=(2, 2))
        self.sure_etiketleri = {}
        self.sure_dugmeleri = {}
        for i in range(8):
            kanal = i + 1
            hucre = tk.Frame(gk_s, bg=PANEL)
            hucre.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=1)
            et = tk.Label(hucre, text="ch%d  —" % kanal, bg=KOYU, fg=SOLUK,
                          font=("Consolas", 10, "bold"), anchor="w",
                          padx=6, pady=2)
            et.pack(side="left", fill="x", expand=True)
            # ▶ bu kanalın sayacını başlat (çalışıyorsa baştan), ✕ sil
            b_bas = self._btn(hucre, "▶", lambda k=kanal: self._metin_sure_baslat(k),
                              VURGU, gen=2)
            b_bas.pack(side="left", padx=(2, 0))
            b_sil = self._btn(hucre, "✕", lambda k=kanal: self._metin_sure_temizle(k),
                              KOYU, gen=2)
            b_sil.pack(side="left", padx=(2, 0))
            self.sure_etiketleri[kanal] = et
            self.sure_dugmeleri[kanal] = (b_bas, b_sil)
        gk_s.columnconfigure(0, weight=1)
        gk_s.columnconfigure(1, weight=1)
        bs = tk.Frame(km_s, bg=PANEL)
        bs.pack(fill="x", padx=5, pady=(1, 3))
        self._btn(bs, "Bu kanalda kestim", self._metin_sure_elle,
                  VURGU).pack(side="left", expand=True, fill="x", padx=(0, 2))
        self._btn(bs, "Sıfırla", self._metin_sure_sifirla).pack(
            side="left", expand=True, fill="x", padx=(2, 0))
        self._aciklama(km_s,
                       "Metini kırınca o kanalın ▶ düğmesine bas: sayaç\n"
                       "yukarıdaki süreyle başlar (çalışıyorsa baştan).\n"
                       "✕ o kanalın sayacını siler. 'Bu kanalda kestim'\n"
                       "bulunduğun kanalınkini başlatır. ● bulunduğun kanal.\n"
                       "\n"
                       "'Süre bitince tekrar başlat' açıksa süre dolunca\n"
                       "sayaç kutudaki süreyle yeniden başlar; bir kez\n"
                       "basman yeter. YEŞİL: süre doldu, metin çıkmış\n"
                       "olmalı, o kanala henüz gidilmedi (gidince söner).\n"
                       "\n"
                       "'Kırılınca otomatik başlat' açıksa yakındaki metin\n"
                       "kırılınca sayaç kendiliğinden de başlar.\n"
                       "Metin ara boş kanaldan ayrılırken sayaç başlatmaz;\n"
                       "yalnızca 'Kırılınca otomatik başlat' açıksa başlatır."
                       ).pack(fill="x", padx=5, pady=(0, 3))

        kz = self._kutu(sk_bot, "Vuruş Hızı")
        gz = tk.Frame(kz, bg=PANEL)
        gz.pack(fill="x", padx=5, pady=(3, 3))
        for i, (etiket, degisken, mn, mx, adim) in enumerate((
                ("Vuruş aralığı (ms)", self.vurus_var, 10, 2000, 10),
                ("Tur başına seri", self.vurus_seri_var, 1, 20, 1),
                ("Menzil (ham)", self.menzil_var, 100, 20000, 100))):
            tk.Label(gz, text=etiket, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w",
                                                pady=2)
            self._sayi(gz, degisken, mn, mx, adim).grid(
                row=i, column=1, sticky="e", padx=4)
        gz.columnconfigure(0, weight=1)
        self._aciklama(kz,
                       "Buradaki her ayar konu sekmelerinde de var; ikisi\n"
                       "aynı ayardır, birini değiştirince öbürü de değişir.\n"
                       "Bu sekme yalnızca sık dokunulanları bir araya\n"
                       "topluyor. Geri kalan 70 ayar diğer sekmelerde.").pack(
                           fill="x", padx=5, pady=(0, 3))

        # Başlıklardaki ● / ○ işaretlerini ilk kez bas. Sonrakiler
        # değişkenlerin trace'inden geliyor.
        self._sekme_basliklari()

        # (BAŞLAT/DURDUR düğmeleri fonksiyonun başında, alta sabitlendi)

    def _istatistik(self, ana):
        c = tk.Frame(ana, bg=PANEL)
        c.pack(fill="x", pady=(0, 3))
        self.ist = {}
        alanlar = [("durum", "DURUM", VURGU), ("oldurulen", "ÖLDÜRÜLEN", HATA),
                   ("toplanan", "TOPLANAN", VURGU), ("yang", "YANG", ALTIN),
                   ("pencere", "WH PENCERE", UYARI),
                   ("isabet", "İSABET", OK),
                   ("gonderilen", "PAKET", OK), ("sure", "SÜRE", METIN)]
        for i, (ad, etiket, renk) in enumerate(alanlar):
            tk.Label(c, text=etiket, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 7, "bold")).grid(row=0, column=i,
                                                        padx=6, pady=(6, 0), sticky="w")
            e = tk.Label(c, text="—", bg=PANEL, fg=renk,
                         font=("Consolas", 11, "bold"))
            e.grid(row=1, column=i, padx=6, pady=(0, 3), sticky="w")
            self.ist[ad] = e
        self.ist["durum"].configure(font=("Consolas", 9, "bold"))

    def _log_paneli(self, ana):
        k = tk.LabelFrame(ana, text=" Günlük ", bg=PANEL, fg=VURGU,
                          font=("Segoe UI", 9, "bold"), bd=1, relief="solid",
                          labelanchor="nw")
        k.pack(fill="both", expand=True)

        ust = tk.Frame(k, bg=PANEL)
        ust.pack(fill="x", padx=6, pady=2)
        self.kuru_goster = tk.BooleanVar(value=True)
        self._onay(ust, "Kuru satırları göster", self.kuru_goster).pack(side="left")
        self._btn(ust, "Temizle", self._log_temizle).pack(side="right")

        self.log = scrolledtext.ScrolledText(
            k, bg=KOYU, fg=METIN, relief="flat", bd=0, font=("Consolas", 9),
            state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=6, pady=(0, 3))
        for ad, renk in (("bilgi", METIN), ("kuru", SOLUK), ("topla", ALTIN),
                         ("basari", OK), ("uyari", UYARI), ("hata", HATA)):
            self.log.tag_configure(ad, foreground=renk)

    def _alt(self):
        c = tk.Frame(self, bg=PANEL)
        c.pack(fill="x", padx=5, pady=(0, 8))
        self.alt_etiket = tk.Label(
            c, text="hazır — bağlan, ayarları seç, BAŞLAT'a bas "
                    "(kuru çalışma açıkken hiçbir paket gitmez)",
            bg=PANEL, fg=SOLUK, anchor="w", font=("Consolas", 9))
        self.alt_etiket.pack(fill="x", padx=6, pady=2)

    # ---- ayar kalıcılığı ----

    def _ayar_degiskenleri(self):
        """
        Arayüzdeki tüm ayar değişkenlerini verir.

        İsim kuralına dayanır: `self.<ad>_var` olan her tkinter değişkeni
        ayardır. Böylece yeni bir ayar eklendiğinde kaydetme/yükleme kodunu
        ayrıca güncellemek gerekmez.
        """
        for ad in dir(self):
            if not ad.endswith("_var") or ad in KAYDEDILMEZ:
                continue
            try:
                v = getattr(self, ad)
            except Exception:
                continue
            if isinstance(v, (tk.StringVar, tk.IntVar,
                              tk.BooleanVar, tk.DoubleVar)):
                yield ad, v

    def ayarlari_kaydet(self, sessiz=False):
        try:
            d = {}
            for ad, v in self._ayar_degiskenleri():
                try:
                    d[ad] = v.get()
                except Exception:
                    pass
            d["_rota"] = list(self.rota_noktalari)   # liste; tk değişkeni değil
            # Harita başına market noktaları — tk değişkeni değil, elle.
            d["_marketler"] = dict(self._marketler)
            # Dokunma dizisi bir Text kutusunda duruyor, tk değişkeni
            # DEĞİL — bu yüzden "_var" taramasına takılmıyor ve
            # kaydedilmiyordu. Bot yeniden açılınca kutu boş kalıyor,
            # kanal değişimi de sessizce atlanıyordu. Sahada tam bu oldu.
            try:
                d["_kanal_dokunma"] = self.kanal_dokunma_kutu.get(
                    "1.0", "end").strip()
            except Exception:
                pass
            with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)
            if not sessiz:
                self._bildir("bilgi", "ayarlar kaydedildi (%d alan)" % len(d))
            return True
        except Exception as e:                        # noqa: BLE001
            self._bildir("hata", "ayarlar kaydedilemedi: %s" % e)
            return False

    def ayarlari_yukle(self):
        if not os.path.exists(AYAR_DOSYASI):
            return
        try:
            with open(AYAR_DOSYASI, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:                        # noqa: BLE001
            self._bildir("uyari", "ayar dosyası okunamadı: %s" % e)
            return
        yuklenen = 0
        for ad, v in self._ayar_degiskenleri():
            if ad not in d:
                continue
            try:
                v.set(d[ad])
                yuklenen += 1
            except Exception:
                pass                                   # tip uyuşmazsa atla
        dizi = d.get("_kanal_dokunma")
        if isinstance(dizi, str) and dizi.strip():
            try:
                self.kanal_dokunma_kutu.delete("1.0", "end")
                self.kanal_dokunma_kutu.insert("1.0", dizi)
                yuklenen += 1
            except Exception:
                pass
        m = d.get("_marketler")
        if isinstance(m, dict):
            for ad, k in m.items():
                try:
                    if isinstance(k, (list, tuple)) and len(k) >= 2:
                        self._marketler[ad] = [int(k[0]), int(k[1]),
                                               int(k[2]) if len(k) > 2 else 0]
                except (TypeError, ValueError):
                    continue
        rota = d.get("_rota")
        if isinstance(rota, list):
            self.rota_noktalari = [[int(p[0]), int(p[1])] for p in rota
                                   if isinstance(p, (list, tuple)) and len(p) >= 2]
            try:
                self._rota_tazele()
            except Exception:
                pass
        self._bildir("bilgi", "ayarlar yüklendi (%d alan, %d rota noktası)"
                     % (yuklenen, len(self.rota_noktalari)))

    def ayarlari_sifirla(self):
        if not messagebox.askyesno(
                "Ayarları sıfırla",
                "Kayıtlı ayarlar silinsin ve varsayılanlara dönülsün mü?\n"
                "(Pencere yeniden açıldığında geçerli olur.)"):
            return
        try:
            if os.path.exists(AYAR_DOSYASI):
                os.remove(AYAR_DOSYASI)
            self._bildir("bilgi", "ayar dosyası silindi — yeniden başlat")
        except Exception as e:                        # noqa: BLE001
            self._bildir("hata", "silinemedi: %s" % e)

    # ---- günlük ----
    def _bildir(self, seviye, metin):
        self.kuyruk.put(("log", seviye, metin))

    def _log_yaz(self, seviye, metin):
        if seviye == "kuru" and not self.kuru_goster.get():
            return
        self.log.configure(state="normal")
        self.log.insert("end", time.strftime("%H:%M:%S  ") + metin + "\n", seviye)
        # log şişmesin
        if int(self.log.index("end-1c").split(".")[0]) > 800:
            self.log.delete("1.0", "200.0")
        self.log.see("end")
        self.log.configure(state="disabled")
        if seviye in ("uyari", "hata"):
            self.alt_etiket.configure(text=metin,
                                      fg=HATA if seviye == "hata" else UYARI)

    def _log_temizle(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ---- bağlantı ----
    def _adb_forward(self):
        def is_():
            try:
                p = subprocess.run([ADB, "forward", "tcp:30200", "tcp:30200"],
                                   capture_output=True, text=True, timeout=15)
                if p.returncode == 0:
                    self.kuyruk.put(("adres", VARSAYILAN_ADRES, None))
                    self._bildir("bilgi", "adb forward kuruldu (tcp:30200)")
                else:
                    self._bildir("hata", "adb forward başarısız: "
                                 + (p.stderr or "").strip())
            except FileNotFoundError:
                self._bildir("hata", "adb bulunamadı — ADB_YOLU değişkenini ayarla")
            except Exception as e:                    # noqa: BLE001
                self._bildir("hata", "adb hatası: %s" % type(e).__name__)
        threading.Thread(target=is_, daemon=True).start()

    def _baglan(self):
        self.api.adres = self.adres_var.get().strip() or VARSAYILAN_ADRES
        self.api.token = self.token_var.get().strip()
        self.api._sifirla()
        self._bildir("bilgi", "bağlanılıyor: %s" % self.api.adres)

    def _filtre_dene(self):
        """
        Yerdeki eşyaları çeker ve filtrenin hangisini alıp hangisini
        eleyeceğini gösterir. Bot başlatılmadan denenebilir — hiçbir
        paket gönderilmez.
        """
        self._ayarlari_al()

        def is_():
            esyalar = self.api.get("/api/esyalar", n=80)
            if not isinstance(esyalar, list):
                self._bildir("hata", "eşya listesi alınamadı: %s"
                             % (self.api.son_hata or "yanıt yok"))
                return
            if not esyalar:
                self._bildir("bilgi", "yerde eşya yok")
                return
            konum = (self.api.get("/api/konum") or {})
            bx, by = int(konum.get("x", 0)), int(konum.get("y", 0))

            alinan, elenen = [], []
            for e in esyalar:
                ad = e.get("ad", "?")
                uzak = mesafe_ham(bx, by, e.get("x", 0), e.get("y", 0)) / 100.0
                sahip = (e.get("sahip") or "").strip()
                satir = "%-26s vnum %-6s %5.0f m%s" % (
                    ad[:26], e.get("vnum", 0), uzak,
                    ("  sahip: " + sahip) if sahip else "")
                if not self.motor._filtre_gecer(e):
                    elenen.append(satir + "   [filtre]")
                elif uzak * 100 > self.ayar.topla_menzil:
                    elenen.append(satir + "   [menzil dışı]")
                elif not self.motor._esya_uygun(e, bx, by):
                    elenen.append(satir + "   [sahip filtresi]")
                else:
                    alinan.append(satir)

            self._bildir("bilgi", "── filtre denemesi: %d eşya ──" % len(esyalar))
            for s in alinan:
                self._bildir("topla", "  ALINIR   " + s)
            for s in elenen:
                self._bildir("kuru", "  elenir   " + s)
            self._bildir("bilgi", "── %d alınır, %d elenir ──"
                         % (len(alinan), len(elenen)))
        threading.Thread(target=is_, daemon=True).start()

    # ---- market ----

    def _son_tiklanan_npc(self):
        """
        Oyunda ELLE tıkladığın son NPC'nin vid'ini günlükten okur.

        <b>Neden gerekli:</b> dükkân NPC'leri hiç hareket etmez, bu yüzden
        0x03 MOVE göndermezler. Paket okuyucu açılmadan önce doğmuşlarsa
        0x01 doğuşlarını da kaçırmışızdır — bot onları hiç göremez.
        29 Ağu 2026'da tam bu yaşandı: bot "NPC" olarak yalnızca at ve
        midilli görüyordu, gerçek dükkân NPC'si (vid 12708) listede yoktu.

        Sen bir kez tıklayınca istemci CG_ON_CLICK (0x1A) yollar; onu
        günlükten yakalayıp vid'i öğreniriz.
        """
        kayitlar = self.api.get("/api/log", n=80)
        if not isinstance(kayitlar, list):
            self._bildir("hata", "günlük okunamadı: %s" % (self.api.son_hata or "?"))
            return None
        for k in kayitlar:                       # en yeni başta
            if not k.get("giden") or k.get("opcode") != 0x1A:
                continue
            hx = (k.get("hex") or "").split()
            if len(hx) < 5:
                continue
            try:
                vid = int(hx[4] + hx[3] + hx[2] + hx[1], 16)   # little-endian
            except ValueError:
                continue
            if 0 < vid < 100_000_000:
                return vid
        return None

    def _npc_vid_ogren(self):
        """'Son tıkladığım NPC' düğmesi."""
        def is_():
            vid = self._son_tiklanan_npc()
            if vid is None:
                self._bildir("uyari",
                             "Günlükte NPC tıklaması yok. Oyunda bir NPC'ye "
                             "TIKLA, sonra bu düğmeye bas. (Paket okuyucu ya da "
                             "proxy açık olmalı.)")
                return
            self.npc_vid_var.set(vid)
            self._bildir("bilgi", "son tıklanan NPC vid = %d — alana yazıldı" % vid)
        threading.Thread(target=is_, daemon=True).start()

    def _npc_bul(self):
        """Ayarda vid verilmişse onu, yoksa en yakın NPC'yi döndürür."""
        varliklar = self.api.get("/api/varliklar", n=80)
        if not isinstance(varliklar, list):
            return None
        istenen = int(self.npc_vid_var.get())
        if istenen:
            for v in varliklar:
                if v.get("vid") == istenen:
                    return v
            # Listede yok ama vid biliniyor: dükkân NPC'leri hareket etmediği
            # için çoğu zaman hiç görünmezler. Konumsuz da olsa tıklanabilir —
            # yürüme adımı atlanır, sadece tıklama gönderilir.
            self._bildir("uyari",
                         "vid %d varlık listesinde yok (hareketsiz NPC). "
                         "Yürüme atlanacak, doğrudan tıklanacak." % istenen)
            return {"vid": istenen, "ad": "NPC #%d" % istenen,
                    "x": 0, "y": 0, "mesafe": 0, "konumsuz": True}
        npcler = [v for v in varliklar if v.get("tip") == TIP_NPC]
        if not npcler:
            self._bildir("uyari", "yakında NPC yok")
            return None
        npcler.sort(key=lambda v: v.get("mesafe", 99999))
        return npcler[0]

    def _hizimi_olc(self):
        """
        Karakterin GERÇEK yürüme hızını ölçer — oyuncu elle koşarken.

        NEDEN GEREKLİ
        -------------
        Botun hareket paketleri, karakterin gerçek hızıyla aynı tempoda
        gitmeli. Yavaş yollarsak animasyon ile yer değiştirme uyuşmuyor:
        ayaklar hızlı koşuyor, gövde yavaş ilerliyor — dışarıdan bakan
        "geriye kayıyor" görüyor. Hızlı yollarsak da bot "vardım" sanıp
        rota noktalarını ıskalıyor.

        Temel hız 430 ham/s (0.43 ham/ms) olarak 163 gerçek GC_MOVE
        paketinden ölçülmüştü. Binek/hız iksiri bunu katlıyor; katsayıyı
        tahmin etmek yerine burada ÖLÇÜYORUZ.

        Yöntem: oyuncu elle koşarken /api/konum'daki ham x,y örneklenir.
        O alan yalnızca istemcinin kendi 0x07'siyle güncellendiği için
        gerçek hızı verir.
        """
        self._baglan()

        def is_():
            self._bildir("bilgi", "HIZ ÖLÇÜMÜ — 10 saniye boyunca "
                                  "oyunda ELLE KOŞ (durma!)")
            ornekler = []
            bitis = time.time() + 10.0
            while time.time() < bitis:
                k = self.api.get("/api/konum")
                if isinstance(k, dict) and k.get("bilinir"):
                    ornekler.append((time.time(),
                                     int(k.get("x", 0)), int(k.get("y", 0))))
                time.sleep(0.25)

            hizlar = []
            for i in range(1, len(ornekler)):
                t0, x0, y0 = ornekler[i - 1]
                t1, x1, y1 = ornekler[i]
                dt = t1 - t0
                d = mesafe_ham(x0, y0, x1, y1)
                # Durduğu ve ışınlandığı anları at
                if dt <= 0 or d < 20 or d > 20000:
                    continue
                hizlar.append(d / dt)
            if len(hizlar) < 4:
                self._bildir("hata",
                             "ölçüm başarısız — yeterli hareket yok. "
                             "Butona bastıktan sonra 10 saniye DURMADAN koş.")
                return
            hizlar.sort()
            orta = hizlar[len(hizlar) // 2]          # ortanca: sıçramalara dayanıklı
            kat = orta / 430.0
            self.hiz_var.set(int(round(orta)))
            self._ayarlari_al()
            self._bildir("bilgi",
                         "HIZIN: %.0f ham/sn  (%.1f m/sn, temel hızın %.1f katı) "
                         "— %d örnekten ölçüldü, alana yazıldı"
                         % (orta, orta / 100.0, kat, len(hizlar)))
        threading.Thread(target=is_, daemon=True).start()

    def _vid_bul(self):
        """
        "Kendi vid'imi SAVAŞTAN bul" — canlı arama, kayıt gerekmez.

        Doğru vid'i bulmanın yolu şuydu: pcap al, tools/kendi_vid_savastan.py
        çalıştır, çıkan sayıyı elle gir. Vid her oyun girişinde değiştiği
        için bu her seferinde tekrarlanacaktı. Gereken her şey zaten
        elimizde olduğu için bot bunu kendisi yapıyor.
        """
        self._baglan()
        self._ayarlari_al()

        def is_():
            self._bildir("bilgi", "vid aranıyor — bot SAVAŞMALI, 25 sn...")
            son = [None]

            def ilerleme(gorulen, en):
                if en and en != son[0]:
                    son[0] = en
                    self._bildir("bilgi", "  %d savaş paketi — önde: %d "
                                 "(%d isabet / %d ıska)"
                                 % (gorulen, en[0], en[1][0], en[1][1]))

            vid, isabet, iska, adaylar = self.motor._vid_ara(25.0, ilerleme)
            if not vid:
                self._bildir("hata", "vid bulunamadı — bot savaştı mı?")
                if adaylar:
                    self._bildir("bilgi", "adaylar (vid: isabet/ıska): %s"
                                 % ", ".join("%d: %d/%d" % (v, k[0], k[1])
                                             for v, k in adaylar[:6]))
                else:
                    self._bildir("uyari",
                                 "hiç savaş paketi görülmedi. Hedefleme "
                                 "sekmesinde 'Canavarlar' açık olmalı ve "
                                 "bot gerçekten vuruyor olmalı.")
                return
            self.kendi_vid_elle_var.set(vid)
            self._ayarlari_al()
            self._bildir("bilgi",
                         "KENDİ VİD BULUNDU: %d  (%d isabet / %d ıska) — "
                         "alana yazıldı, hizalama artık bunu kullanacak"
                         % (vid, isabet, iska))
        threading.Thread(target=is_, daemon=True).start()

    def _dokunma_dene(self):
        """Dokunma dizisini bir kez çalıştırır — koordinat doğrulamak için."""
        self._baglan()
        self._ayarlari_al()
        metin = self.ayar.kanal_dokunma.strip()
        if not metin:
            self._bildir("uyari", "dokunma dizisi boş — "
                                  "python tools/dokunma_kaydet.py ile kaydet")
            return

        def is_():
            self._bildir("uyari", "DOKUNMA DENEMESİ — telefona bak, "
                                  "oyun ön planda olmalı")
            self.motor.calisiyor = True
            try:
                ok = self.motor._dokunma_dizisi_calistir(metin, 2)
            finally:
                self.motor.calisiyor = False
            self._bildir("bilgi" if ok else "hata",
                         "dokunma dizisi %s" % ("tamamlandı" if ok
                                                else "BAŞARISIZ"))
        threading.Thread(target=is_, daemon=True).start()

    def _markete_git(self):
        """NPC'ye yürü, varınca tıkla (dükkânı aç)."""
        self._ayarlari_al()

        def is_():
            npc = self._npc_bul()
            if not npc:
                return
            ad = npc.get("ad", "?")
            vid = npc["vid"]
            konum = self.api.get("/api/konum") or {}
            durum = self.api.get("/api/durum") or {}
            bx, by = int(konum.get("x", 0)), int(konum.get("y", 0))
            uzak = mesafe_ham(bx, by, npc["x"], npc["y"])
            self._bildir("bilgi", "NPC: %s  #%d  %.0f m" % (ad, vid, uzak / 100.0))

            if npc.get("konumsuz"):
                uzak = 0                          # konumu bilinmiyor, yürüme
            if uzak > 300:                       # 3 m'den uzaksa yürü
                tik = int(durum.get("tik", 0))
                yb = yon_bayti(npc["x"] - bx, npc["y"] - by)
                self.motor._gonder(
                    paket_hareket(npc["x"], npc["y"], tik, bfunc=1, brot=yb),
                    "markete yürü (%.0f m)" % (uzak / 100.0))
                sure = uzak / max(200.0, self.ayar.yurume_hizi)
                self._bildir("bilgi", "yol ~%.1f sn — bekleniyor%s"
                             % (sure, " (KURU: yürümez)" if self.ayar.kuru else ""))
                time.sleep(min(sure + 0.5, 15.0))

            # Tıklamayı gerçek istemcinin gönderdiği gibi kur: CG_ON_CLICK +
            # CG_MOVE(DUR) tek segmentte. Konum bu arada değişmiş olabilir,
            # yeniden oku.
            konum = self.api.get("/api/konum") or konum
            durum = self.api.get("/api/durum") or durum
            bx, by = int(konum.get("x", bx)), int(konum.get("y", by))
            tik = int(durum.get("tik", 0))
            if npc.get("konumsuz"):
                brot = int(konum.get("yon", 0) / 5) % 72
            else:
                brot = yon_bayti(npc["x"] - bx, npc["y"] - by)
            self.motor._gonder(paket_tikla_tam(vid, bx, by, tik, brot),
                               "NPC'ye tıkla #%d (tıkla+dur, 21 bayt)" % vid)
            if self.ayar.kuru:
                self._bildir("uyari",
                             "KURU ÇALIŞMA — hiçbir paket GÖNDERİLMEDİ. "
                             "Oyunda dükkân açılmaz. Göndermek için "
                             "Gönderim sekmesinden kuru çalışmayı kapat.")
            else:
                self._bildir("bilgi", "tıklama gönderildi — dükkân açılmalı")
        threading.Thread(target=is_, daemon=True).start()

    def _satisa_basla(self):
        """Seçili slot aralığındaki eşyaları satar."""
        self._ayarlari_al()
        bas, son = self.ayar.slot_bas, self.ayar.slot_son
        if son < bas:
            bas, son = son, bas
        if not self.ayar.kuru and not messagebox.askyesno(
                "Satış",
                "Slot %d–%d aralığı SATILACAK (%d slot).\n\n"
                "Envanteri göremediğimiz için bu slotlarda ne olduğunu\n"
                "bilmiyoruz. Dolu ve değerli bir slot varsa SATILIR.\n\n"
                "Devam edilsin mi?" % (bas, son, son - bas + 1)):
            return

        def is_():
            adet = self.ayar.satis_adet
            gecikme = self.ayar.satis_gecikme / 1000.0
            n = 0
            for slot in range(bas, son + 1):
                if not self.motor._gonder(paket_sat(slot, adet),
                                          "SAT slot %d x%d" % (slot, adet)):
                    break
                n += 1
                time.sleep(gecikme)
            if self.ayar.kuru:
                self._bildir("uyari",
                             "KURU ÇALIŞMA — %d slot için satış paketi "
                             "SADECE LOGLANDI, gönderilmedi. Oyunda hiçbir şey "
                             "satılmaz." % n)
            else:
                self._bildir("bilgi", "%d slot için satış gönderildi" % n)
        threading.Thread(target=is_, daemon=True).start()

    def _dukkani_kapat(self):
        self._ayarlari_al()
        threading.Thread(
            target=lambda: self.motor._gonder(paket_dukkan_kapat(),
                                              "dükkânı kapat"),
            daemon=True).start()

    # ---- rota ----

    def _rota_tazele(self):
        """Liste kutusunu rota_noktalari'na göre yeniden çizer."""
        self.rota_liste.delete(0, "end")
        onceki = None
        for i, (x, y) in enumerate(self.rota_noktalari):
            if onceki is None:
                ek = ""
            else:
                ek = "  %+.0f m" % (mesafe_ham(onceki[0], onceki[1], x, y) / 100.0)
            self.rota_liste.insert(
                "end", "%2d.  %7.0f, %7.0f m%s" % (i + 1, x / 100.0, -y / 100.0, ek))
            onceki = (x, y)

    def _rota_nokta_ekle(self):
        def is_():
            k = self.api.get("/api/konum")
            if not isinstance(k, dict) or not k.get("bilinir"):
                self._bildir("uyari", "konum bilinmiyor — paket okuyucu/proxy açık mı?")
                return
            x, y = int(k.get("x", 0)), int(k.get("y", 0))
            self.rota_noktalari.append([x, y])
            self.kuyruk.put(("rota", None, None))
            self._bildir("bilgi", "rota noktası %d: %.0f, %.0f m"
                         % (len(self.rota_noktalari), x / 100.0, -y / 100.0))
        threading.Thread(target=is_, daemon=True).start()

    def _rota_nokta_sil(self):
        sec = self.rota_liste.curselection()
        if not sec:
            self._bildir("uyari", "önce listeden bir nokta seç")
            return
        i = sec[0]
        if 0 <= i < len(self.rota_noktalari):
            del self.rota_noktalari[i]
            self._rota_tazele()
            self._bildir("bilgi", "%d. nokta silindi" % (i + 1))

    def _rota_temizle(self):
        if not self.rota_noktalari:
            return
        if not messagebox.askyesno("Rota", "%d nokta silinsin mi?"
                                   % len(self.rota_noktalari)):
            return
        self.rota_noktalari.clear()
        self._rota_tazele()
        self._bildir("bilgi", "rota temizlendi")

    # ─── Rota Kitaplığı ───
    #
    # Rotalar ada göre tambot_rotalar.json içinde durur:
    #
    #     {"2. köy": {"noktalar": [[x, y], ...], "mod": "oto"}}
    #
    # Rota sonu davranışı (mod) rotanın KENDİ özelliği: düz bir hat geri
    # dönmeli, halka rota başa sarmalı. Adla birlikte saklanmasaydı bir
    # rotayı yükleyip öncekinin moduyla gezmek gerekirdi — düz hatta başa
    # sarmak duvardan geçmek demek.

    def _kitaplik_oku(self):
        """Kayıtlı rotaları döndürür. Dosya yoksa ya da bozuksa boş sözlük."""
        try:
            with open(ROTA_DOSYASI, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            return {}
        if not isinstance(d, dict):
            return {}
        temiz = {}
        for ad, kayit in d.items():
            if isinstance(kayit, list):        # yalın biçim: sadece noktalar
                kayit = {"noktalar": kayit}
            if not isinstance(kayit, dict):
                continue
            nok = [[int(q[0]), int(q[1])] for q in kayit.get("noktalar", [])
                   if isinstance(q, (list, tuple)) and len(q) >= 2]
            if nok:
                temiz[ad] = {"noktalar": nok,
                             "mod": kayit.get("mod", "oto"),
                             "metin_adlari": kayit.get("metin_adlari"),
                             "zaman": kayit.get("zaman", "")}
        return temiz

    def _kitaplik_yaz(self, d):
        try:
            with open(ROTA_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self._bildir("hata", "rota kitaplığı yazılamadı: %s" % e)
            return False

    def _kitaplik_tazele(self, sec_ad=None):
        """Liste kutusunu dosyadan yeniden çizer."""
        d = self._kitaplik_oku()
        self._kitaplik_adlar = sorted(d.keys(), key=lambda a: a.lower())
        self.kitaplik_liste.delete(0, "end")
        for ad in self._kitaplik_adlar:
            k = d[ad]
            met = (k.get("metin_adlari") or "").strip()
            self.kitaplik_liste.insert(
                "end", "%-18s %3d nokta  %-9s %s"
                % (ad[:18], len(k["noktalar"]),
                   {"dongu": "başa sar", "gidis_donus": "geri dön"}
                   .get(k.get("mod"), "otomatik"),
                   met[:24] if met else "tüm metinler"))
        if sec_ad and sec_ad in self._kitaplik_adlar:
            i = self._kitaplik_adlar.index(sec_ad)
            self.kitaplik_liste.selection_clear(0, "end")
            self.kitaplik_liste.selection_set(i)
            self.kitaplik_liste.see(i)

    def _kitaplik_secili_ad(self):
        sec = self.kitaplik_liste.curselection()
        adlar = getattr(self, "_kitaplik_adlar", [])
        if sec and 0 <= sec[0] < len(adlar):
            return adlar[sec[0]]
        return None

    def _kitaplik_secildi(self, olay=None):
        """Listeden seçince ad kutusunu doldur — üstüne yazmak kolay olsun."""
        ad = self._kitaplik_secili_ad()
        if ad:
            self.kitaplik_ad_var.set(ad)

    def _kitaplik_kaydet(self):
        ad = (self.kitaplik_ad_var.get() or "").strip()
        if not ad:
            self._bildir("uyari", "önce bir ad yaz (örn: 2. köy)")
            return
        if not self.rota_noktalari:
            self._bildir("uyari", "kaydedilecek rota yok — önce nokta ekle")
            return
        d = self._kitaplik_oku()
        if ad in d and not messagebox.askyesno(
                "Rota Kitaplığı",
                "\"%s\" zaten var (%d nokta).\n"
                "Şimdiki rotayla (%d nokta) değiştirilsin mi?"
                % (ad, len(d[ad]["noktalar"]), len(self.rota_noktalari))):
            return
        # METİN ADLARI DA ROTAYLA BİRLİKTE.
        #
        # Her köyde başka metinler var: 1. köyde "Dövüş / Savaş / Üzüntü",
        # 2. köyde "Karanlık / Kıskançlık / Siyah". Adlar rotadan ayrı
        # tutulsaydı, rotayı yükleyip metin adlarını elle değiştirmeyi
        # unutmak bota yanlış metinleri arattırırdı — hiçbirini bulamaz,
        # sessizce boş gezerdi.
        d[ad] = {"noktalar": [[int(x), int(y)] for x, y in self.rota_noktalari],
                 "mod": self.rota_mod_var.get(),
                 "metin_adlari": self.rota_metin_adlari_var.get(),
                 "zaman": time.strftime("%Y-%m-%d %H:%M")}
        if self._kitaplik_yaz(d):
            self._kitaplik_tazele(ad)
            self._bildir("basari", "\"%s\" kaydedildi (%d nokta, metin: %s)"
                         % (ad, len(self.rota_noktalari),
                            self.rota_metin_adlari_var.get().strip()
                            or "hepsi"))

    def _kitaplik_yukle(self):
        ad = self._kitaplik_secili_ad()
        if not ad:
            self._bildir("uyari", "önce listeden bir rota seç")
            return
        kayit = self._kitaplik_oku().get(ad)
        if not kayit:
            self._bildir("hata", "\"%s\" bulunamadı" % ad)
            self._kitaplik_tazele()
            return
        # Şimdiki rota kitaplıkta yoksa uyar: gezerek toplanan noktaları
        # sessizce silmek pahalı bir kayıp olurdu.
        if self.rota_noktalari and not messagebox.askyesno(
                "Rota Kitaplığı",
                "Şimdiki rota (%d nokta) \"%s\" ile değiştirilecek "
                "(%d nokta).\n\nDevam edilsin mi?"
                % (len(self.rota_noktalari), ad, len(kayit["noktalar"]))):
            return
        self.rota_noktalari = [list(q) for q in kayit["noktalar"]]
        mod = kayit.get("mod")
        if mod in ("oto", "dongu", "gidis_donus"):
            self.rota_mod_var.set(mod)
        # None = bu rota metin adları eklenmeden önce kaydedilmiş; şimdiki
        # ayara dokunma. Boş dizgi ise kullanıcının bilinçli tercihi
        # ("hepsi") ve uygulanır.
        met = kayit.get("metin_adlari")
        if met is not None:
            self.rota_metin_adlari_var.set(met)
        self.kitaplik_ad_var.set(ad)
        self._rota_tazele()
        self._bildir("basari", "\"%s\" yüklendi (%d nokta, metin: %s)"
                     % (ad, len(self.rota_noktalari),
                        self.rota_metin_adlari_var.get().strip() or "hepsi"))

    def _kitaplik_sil(self):
        ad = self._kitaplik_secili_ad()
        if not ad:
            self._bildir("uyari", "önce listeden bir rota seç")
            return
        d = self._kitaplik_oku()
        if ad not in d:
            self._kitaplik_tazele()
            return
        if not messagebox.askyesno(
                "Rota Kitaplığı",
                "\"%s\" (%d nokta) kitaplıktan silinsin mi?\n"
                "Şimdiki rota etkilenmez." % (ad, len(d[ad]["noktalar"]))):
            return
        del d[ad]
        if self._kitaplik_yaz(d):
            self._kitaplik_tazele()
            self._bildir("bilgi", "\"%s\" silindi" % ad)

    def _rota_kayit_degistir(self):
        """
        Rota kaydını başlatır/durdurur.

        Sen oyunda gezerken bot belirli aralıklarla konumu okur ve yeterince
        ilerlemişse nokta ekler. Tek tek "ekle" demeye gerek kalmaz. Aynı
        yerde durunca nokta eklenmez — yoksa yüzlerce üst üste nokta olurdu.
        """
        if getattr(self, "_kayit_calisiyor", False):
            self._kayit_calisiyor = False
            self.kayit_btn.configure(text="⏺  Rota kaydına başla", bg=UYARI)
            self._bildir("bilgi", "rota kaydı durduruldu — %d nokta"
                         % len(self.rota_noktalari))
            return

        self._baglan()
        self._kayit_calisiyor = True
        self.kayit_btn.configure(text="⏹  Kaydı durdur", bg=HATA)
        self._bildir("bilgi", "rota kaydı BAŞLADI — oyunda gez")

        def is_():
            aralik = max(0.2, self.kayit_aralik_var.get() / 1000.0)
            enaz = max(100, self.kayit_mesafe_var.get())
            son = self.rota_noktalari[-1] if self.rota_noktalari else None
            while getattr(self, "_kayit_calisiyor", False):
                time.sleep(aralik)
                k = self.api.get("/api/konum")
                if not isinstance(k, dict) or not k.get("bilinir"):
                    continue
                x, y = int(k.get("x", 0)), int(k.get("y", 0))
                if son is not None and mesafe_ham(son[0], son[1], x, y) < enaz:
                    continue                       # yeterince ilerlemedik
                self.rota_noktalari.append([x, y])
                son = [x, y]
                self.kuyruk.put(("rota", None, None))
                self._bildir("bilgi", "nokta %d: %.0f, %.0f m"
                             % (len(self.rota_noktalari), x / 100.0, -y / 100.0))
        threading.Thread(target=is_, daemon=True).start()

    def _rotada_gez_basla(self):
        """Rota devriyesini doğrudan başlatır."""
        self._ayarlari_al()
        if not self.rota_noktalari:
            messagebox.showwarning(
                "Rota", "Rota boş. Önce nokta ekle ya da kayıt yap.")
            return
        if getattr(self, "_kayit_calisiyor", False):
            self._rota_kayit_degistir()            # kaydı kapat
        # Rota yürümek demektir; gerekli anahtarları aç
        self.rota_gez_var.set(True)
        self.yaklas_var.set(True)
        self._ayarlari_al()
        self._bildir("bilgi", "rota başlıyor — %d nokta%s"
                     % (len(self.rota_noktalari),
                        " (sadece rota)" if self.ayar.sadece_rota else ""))
        self._basla()

    def _markete_git(self):
        """"MARKETE GİT" butonu — motora elle market isteği geçirir."""
        self._baglan()
        self._ayarlari_al()
        mesaj = self.motor.market_iste()
        self._bildir("bilgi", mesaj)

    def _harita_adi_ui(self, x, y):
        """Arayüz tarafında harita adı — motorun yüklediği veriyi kullanır."""
        try:
            if getattr(self, "_ui_dunya", None) is None:
                from harita_engel import Dunya
                self._ui_dunya = Dunya.yukle()
            h = self._ui_dunya.hangi(x, y) if self._ui_dunya else None
            return h.ad if h else ""
        except Exception:
            return ""

    def _market_haritadan_yukle(self, x, y):
        """
        Bulunduğumuz haritanın market noktasını alanlara yazar.

        Yoklama döngüsünden çağrılıyor: köy değiştirince kullanıcı hiçbir
        şey yapmadan doğru market yükleniyor. Kayıt yoksa var olana
        DOKUNMUYOR — kullanıcının elle girdiği değeri silmek kötü olurdu.
        """
        harita = self._harita_adi_ui(x, y)
        if not harita or harita == self._market_haritasi:
            return
        kayit = self._marketler.get(harita)
        if not kayit:
            return
        self._market_haritasi = harita
        self.market_x_var.set(int(kayit[0]))
        self.market_y_var.set(int(kayit[1]))
        if len(kayit) > 2 and kayit[2]:
            self.npc_vid_var.set(int(kayit[2]))
        self._bildir("bilgi",
                     "%s market noktası yüklendi: %.0f, %.0f m"
                     % (harita, kayit[0] / 100.0, -kayit[1] / 100.0))

    def _saldiri_dugmesi_dene(self):
        """
        Düğmeye bir kez basıp sonucu bildirir.

        Koordinatı doğrulamanın en hızlı yolu: oyunda karakterin
        saldırıya geçip geçmediğine bakmak. Yanlışsa yeniden kaydet.
        """
        def is_():
            self._baglan()
            self._ayarlari_al()
            x = int(self.saldiri_dugme_x_var.get())
            y = int(self.saldiri_dugme_y_var.get())
            if not (x or y):
                self._bildir("uyari",
                             "düğme yeri kayıtlı değil — "
                             "python tools/saldiri_dugmesi.py")
                return
            self.api.dokunma_ac(True)
            if self.api.dokun(x, y):
                self._bildir("basari",
                             "düğmeye basıldı (%d, %d) — oyunda karakter "
                             "saldırıya geçti mi?" % (x, y))
            else:
                self._bildir("hata",
                             "dokunma başarısız — APK'da dokunma açık mı, "
                             "root var mı?")
        threading.Thread(target=is_, daemon=True).start()

    def _market_noktasi_al(self):
        """Oyuncunun şu anki konumunu market noktası olarak kaydeder."""
        def is_():
            k = self.api.get("/api/konum")
            if not isinstance(k, dict) or not k.get("bilinir"):
                self._bildir("uyari", "konum bilinmiyor — paket okuyucu/proxy açık mı?")
                return
            x, y = int(k.get("x", 0)), int(k.get("y", 0))
            self.market_x_var.set(x)
            self.market_y_var.set(y)
            # HARİTA BAŞINA SAKLA.
            #
            # Tek bir market noktası köy değişince eskisinde kalıyordu:
            # 1. köydeyken kayıtlı market 2. köyün haritasındaydı, bot
            # oraya yürümeye çalışıp takılıyordu. Artık her harita kendi
            # noktasını tutuyor ve o haritaya girince kendiliğinden
            # yükleniyor.
            harita = self._harita_adi_ui(x, y)
            if harita:
                self._marketler[harita] = [x, y,
                                           int(self.npc_vid_var.get() or 0)]
                self._bildir("basari",
                             "market noktası kaydedildi: %s -> %d, %d "
                             "(%.0f, %.0f m)"
                             % (harita, x, y, x / 100.0, -y / 100.0))
            else:
                self._bildir("bilgi",
                             "market noktası: %d, %d  (%.0f, %.0f m) — "
                             "harita bilinmiyor, haritaya bağlanmadı"
                             % (x, y, x / 100.0, -y / 100.0))
        threading.Thread(target=is_, daemon=True).start()

    def _sistem_mesajlari(self):
        """Son sistem uyarılarını günlüğe döker — aranan metni bulmak için."""
        def is_():
            satirlar = self.api.get("/api/sohbet", n=30, tip=1)
            if not isinstance(satirlar, list):
                self._bildir("hata", "sohbet okunamadı: %s"
                             % (self.api.son_hata or "?"))
                return
            if not satirlar:
                self._bildir("bilgi", "henüz sistem mesajı yok "
                                      "(paket okuyucu/proxy açık mı?)")
                return
            self._bildir("bilgi", "── son %d sistem mesajı ──" % len(satirlar))
            for s in satirlar:
                self._bildir("kuru", "  " + str(s.get("metin", ""))[:90])
        threading.Thread(target=is_, daemon=True).start()

    # ---- gönderim anahtarları ----

    def _anahtar_durumu(self, d=None):
        """Dört anahtarın APK'daki güncel durumu."""
        d = d if d is not None else self.son_durum
        p = d.get("proxy") or {}
        k = d.get("kuyruk") or {}
        s = d.get("servisler") or {}
        return {
            "paket":      bool(s.get("paket")),
            "proxy":      bool(p.get("acik")),
            "enjeksiyon": bool(p.get("enjeksiyon")),
            "kanal":      "Proxy" in str(k.get("kanal", "")),
        }

    def _anahtar_degistir(self, ad):
        """Tek anahtarı ters çevirir. Çağrı arka planda yapılır."""
        acik = self._anahtar_durumu().get(ad, False)
        yeni = not acik

        if ad == "enjeksiyon" and yeni and not messagebox.askyesno(
                "Enjeksiyon",
                "Enjeksiyon AÇILIYOR.\n\n"
                "Bu, oyuna gerçekten paket gönderilmesinin ana şalteridir.\n"
                "Devam edilsin mi?"):
            return

        def is_():
            if ad == "paket":
                c = self.api.get("/api/servis", ad="paket", ac=1 if yeni else 0)
            elif ad == "proxy":
                c = self.api.get("/api/servis", ad="proxy", ac=1 if yeni else 0)
            elif ad == "enjeksiyon":
                c = self.api.get("/api/enjeksiyon", ac=1 if yeni else 0)
            elif ad == "kanal":
                c = self.api.get("/api/kanal", ad="proxy" if yeni else "log")
            else:
                return
            if c is None:
                self._bildir("hata", "%s → hata: %s" % (ad, self.api.son_hata))
            elif isinstance(c, dict) and c.get("ok") is False:
                self._bildir("uyari", "%s → %s" % (ad, c.get("hata")))
            else:
                self._bildir("bilgi", "%s → %s" % (ad, "açıldı" if yeni else "kapatıldı"))
        threading.Thread(target=is_, daemon=True).start()

    def _hepsini_ac(self):
        """Dört anahtarı sırayla açar — gönderime hazır hale getirir."""
        if not messagebox.askyesno(
                "Gönderime hazırla",
                "Paket okuyucu, proxy, enjeksiyon ve proxy kanalı AÇILACAK.\n\n"
                "Bundan sonra bot (kuru çalışma kapalıysa) oyuna gerçekten\n"
                "paket gönderebilir.\n\nDevam edilsin mi?"):
            return

        def is_():
            adimlar = [
                ("paket okuyucu", "/api/servis", {"ad": "paket", "ac": 1}),
                ("proxy",         "/api/servis", {"ad": "proxy", "ac": 1}),
                ("kanal",         "/api/kanal",  {"ad": "proxy"}),
                ("enjeksiyon",    "/api/enjeksiyon", {"ac": 1}),
            ]
            for etiket, yol, par in adimlar:
                c = self.api.get(yol, **par)
                if c is None:
                    self._bildir("hata", "%s açılamadı: %s" % (etiket, self.api.son_hata))
                elif isinstance(c, dict) and c.get("ok") is False:
                    self._bildir("uyari", "%s: %s" % (etiket, c.get("hata")))
                else:
                    self._bildir("bilgi", "%s açıldı" % etiket)
                time.sleep(0.4)   # servisler ayağa kalksın
            self._bildir("uyari",
                         "Anahtarlar açıldı. Proxy'nin oyuna BAĞLANMASI için "
                         "oyunun proxy üzerinden yeniden bağlanması gerekebilir.")
        threading.Thread(target=is_, daemon=True).start()

    def _anahtarlari_tazele(self, d):
        """Düğme yazılarını APK'daki gerçek duruma göre günceller."""
        durum = self._anahtar_durumu(d)
        p = d.get("proxy") or {}
        etiketler = {
            "paket": "Paket okuyucu",
            "proxy": "Proxy" + ("  [bağlı]" if p.get("bagli") else "  [bağlı değil]"),
            "enjeksiyon": "Enjeksiyon",
            "kanal": "Kanal: " + ("Proxy" if durum["kanal"] else "Log"),
        }
        for ad, b in self.anahtar_btn.items():
            acik = durum.get(ad, False)
            b.configure(
                text=("✓  " if acik else "✗  ") + etiketler[ad],
                bg=OK if acik else CIZGI,
                fg=KOYU if acik else SOLUK)

    # ---- ayarları motora aktar ----
    def _ayarlari_al(self):
        a = self.ayar
        a.kuru         = self.kuru_var.get()
        # MODÜL KAPALIYSA ALTINDAKİ HER ŞEY KAPALI.
        #
        # Kapatma burada, tek noktada yapılıyor — bot mantığına hiç
        # dokunulmuyor. Modül kapalıyken ayarlar sanki tek tek
        # kapatılmış gibi görünüyor, dolayısıyla yeni bir kod yolu ve
        # yeni bir hata ihtimali doğmuyor.
        hedefleme = self.modul_hedefleme_var.get()
        rota_acik = self.modul_rota_var.get()
        a.modul_hedefleme = hedefleme
        a.modul_rota   = rota_acik
        a.basit_hedefleme = self.basit_hedefleme_var.get()
        a.hedef_mob    = self.mob_var.get() and hedefleme
        a.hedef_metin  = self.metin_var.get() and hedefleme
        a.tarama       = int(self.tarama_var.get())
        a.menzil       = int(self.menzil_var.get())
        a.vurus_ms     = int(self.vurus_var.get())
        a.vurus_seri   = int(self.vurus_seri_var.get())
        a.yaklas       = self.yaklas_var.get()
        a.hedefe_yuru  = self.hedefe_yuru_var.get()
        a.adim_mesafe  = int(self.adim_var.get())
        a.duvar_kacin  = self.duvar_kacin_var.get()
        a.duvar_payi   = int(self.duvar_payi_var.get())
        a.erken_donus  = int(self.erken_var.get())
        a.akis_aralik_ms = int(self.akis_var.get())
        a.yurume_hizi  = int(self.hiz_var.get())
        a.istemci_hizala = self.hizala_var.get()
        a.kendi_vid_elle = int(self.kendi_vid_elle_var.get())
        a.karakter_adi  = self.karakter_adi_var.get()
        a.hizala_adim_ms = int(self.hizala_adim_var.get())
        a.hizala_mesafe = int(self.hizala_mesafe_var.get())
        a.hizala_yontem = self.hizala_yontem_var.get()
        a.wh_dur_paketi = self.wh_dur_var.get()
        a.hedef_kilit  = self.kilit_var.get()
        a.coklu_hedef  = self.coklu_var.get()
        a.max_hedef    = int(self.max_hedef_var.get())
        a.oyuncu_vur      = self.oyuncu_vur_var.get()
        a.oyuncu_vurus_ms = max(50, int(self.oyuncu_vurus_ms_var.get()))
        a.oyuncu_menzil   = max(100, int(self.oyuncu_menzil_var.get()))
        a.kilit_sure   = int(self.kilit_sure_var.get())
        a.ev_yaricap   = int(self.ev_var.get())
        a.topla_acik   = self.topla_var.get()
        a.yang_oncelik = self.yang_var.get()
        a.sadece_benim = self.benim_var.get()
        a.oyuncu_adi   = self.ad_var.get().strip()
        a.topla_menzil = int(self.topla_menzil_var.get())
        a.filtre_mod   = self.filtre_mod_var.get()
        a.filtre_metin = self.filtre_var.get()
        a.yetenek_acik = self.yetenek_var.get() and hedefleme
        a.yetenek_vnum = int(self.yvnum_var.get())
        a.yetenek_ms   = int(self.yms_var.get())
        a.wait_hack    = self.wh_var.get()
        a.wh_menzil    = int(self.wh_menzil_var.get())
        a.wh_pencere   = self.wh_pencere_var.get()
        a.wh_donus     = self.wh_donus_var.get()
        a.wh_bekleme_ms = int(self.wh_bekleme_var.get())
        a.devriye      = self.devriye_var.get() and rota_acik
        a.rota_gez     = self.rota_gez_var.get() and rota_acik
        a.rota_yaricap = int(self.rota_yaricap_var.get())
        a.rota_mod     = self.rota_mod_var.get()
        # ROTANIN SAHİPLENDİĞİ AYARLAR DA MODÜLE BAĞLI.
        #
        # Bunlar unutulunca Rota kapalıyken HEDEFLEME ÖLÜYORDU:
        # rota_metin açık kaldığı için _hedef_uygun metinleri "rotanın
        # işi" diye eliyor, sadece_metin_canavari de canavarları "metin
        # başında değiliz" diye eliyordu. Rota hiç çalışmadığından da
        # hiçbir metin onaylanmıyor, yani bot hiçbir şeye vurmuyordu.
        a.rota_metin   = self.rota_metin_var.get() and rota_acik
        a.rota_metin_menzil = int(self.rota_metin_menzil_var.get())
        a.rota_metin_adlari = self.rota_metin_adlari_var.get()
        a.tur_en_az_nokta = int(self.tur_en_az_nokta_var.get())
        a.kanal_degistir = (self.kanal_degistir_var.get()
                            and rota_acik)
        a.kanallar     = self.kanallar_var.get()
        a.kanal_bekle  = self.kanal_bekle_var.get()
        a.kanal_dokunma = self.kanal_dokunma_kutu.get("1.0", "end").strip()
        a.kanal_menu_bekle = int(self.kanal_menu_bekle_var.get())
        a.kanal_bekleme = int(self.kanal_bekleme_var.get())
        a.metin_ara    = self.metin_ara_var.get()
        a.metin_ara_sure = int(self.metin_ara_sure_var.get())
        a.metin_ara_yeni_sure = int(self.metin_ara_yeni_sure_var.get())
        a.metin_ara_ses = self.metin_ara_ses_var.get()
        a.metin_sure_tutucu = self.metin_sure_var.get()
        a.metin_sure_dk = int(self.metin_sure_dk_var.get())
        a.metin_sure_otomatik = self.metin_sure_oto_var.get()
        a.metin_sure_tekrar = self.metin_sure_tekrar_var.get()
        self._sure_tutucu_esitle()
        a.metin_yaklasma = int(self.metin_yaklasma_var.get())
        a.ekran_genislik = int(self.ekran_genislik_var.get())
        a.ekran_yukseklik = int(self.ekran_yukseklik_var.get())
        a.istemci_esas = self.istemci_esas_var.get()
        a.sapma_siniri = int(self.sapma_siniri_var.get())
        a.istemci_sabir_ms = int(self.istemci_sabir_var.get())
        a.saldiri_dugme_x = int(self.saldiri_dugme_x_var.get())
        a.saldiri_dugme_y = int(self.saldiri_dugme_y_var.get())
        a.saldiri_basma = int(self.saldiri_basma_var.get())
        a.saldiri_basma_ms = int(self.saldiri_basma_ms_var.get())
        a.metin_paket_secim = self.metin_paket_secim_var.get()
        a.sadece_metin_canavari = (self.sadece_metin_canavari_var.get()
                                   and rota_acik)
        a.rota_kendi_saldiri = (self.rota_kendi_saldiri_var.get()
                                and rota_acik)
        a.metin_savas_suresi = int(self.metin_savas_suresi_var.get())
        a.sifir_can_sabri = int(self.sifir_can_sabri_var.get())
        a.rota_bekle   = int(self.rota_bekle_var.get())
        a.sadece_rota  = self.sadece_rota_var.get() and rota_acik
        # Rota modülü kapalıysa nokta listesi BOŞ gider. Rotayla ilgili
        # her kod yolu zaten "nokta yoksa çık" diye başlıyor, o yüzden
        # tek bu satır bütün rota davranışını kapatıyor.
        a.rota         = list(self.rota_noktalari) if rota_acik else []
        a.npc_vid      = int(self.npc_vid_var.get())
        a.slot_bas     = int(self.slot_bas_var.get())
        a.slot_son     = int(self.slot_son_var.get())
        a.satis_adet   = int(self.satis_adet_var.get())
        a.satis_gecikme = int(self.satis_gecikme_var.get())
        a.uyari_izle   = self.uyari_izle_var.get()
        a.uyari_metin  = self.uyari_metin_var.get()
        a.market_x     = int(self.market_x_var.get())
        a.market_y     = int(self.market_y_var.get())
        a.otomatik_market = self.oto_market_var.get()

    def _kuru_degisti(self):
        self.ayar.kuru = self.kuru_var.get()
        if not self.ayar.kuru:
            if not messagebox.askyesno(
                    "Gerçek gönderim",
                    "Kuru çalışma KAPATILIYOR.\n\n"
                    "Bundan sonra bot gerçekten oyuna paket gönderir "
                    "(proxy + enjeksiyon + kanal açıksa).\n\nDevam edilsin mi?"):
                self.kuru_var.set(True)
                self.ayar.kuru = True
                return
            self._bildir("uyari", "GERÇEK GÖNDERİM açıldı")
        else:
            self._bildir("bilgi", "kuru çalışmaya dönüldü")

    # ---- başlat / durdur ----
    def _basla(self):
        self._ayarlari_al()
        if not (self.ayar.hedef_mob or self.ayar.hedef_metin
                or self.ayar.topla_acik or self.ayar.devriye
                or self.ayar.rota_gez or self.ayar.sadece_rota):
            messagebox.showwarning(
                "Ayar",
                "En az bir iş seç: canavar, metin, toplama, rota ya da devriye.")
            return
        self.ayarlari_kaydet(sessiz=True)
        self._baglan()
        self.motor.basla()
        self.basla_btn.configure(state="disabled", bg=CIZGI, fg=SOLUK)
        self.dur_btn.configure(state="normal", bg=HATA, fg=KOYU)

    def _dur(self):
        self.motor.dur()
        self.basla_btn.configure(state="normal", bg=OK, fg=KOYU)
        self.dur_btn.configure(state="disabled", bg=CIZGI, fg=SOLUK)

    def _kapat(self):
        # Kapanış işareti: zamanlayıcılar kendilerini yeniden kurmasın,
        # yoksa pencere yok edildikten sonra "invalid command name" çıkar.
        self._kapaniyor = True
        self._kayit_calisiyor = False
        self.ayarlari_kaydet(sessiz=True)
        self.motor.dur()
        self.metin_arayici.durdur()
        self.after(150, self.destroy)

    # ---- yoklama (durum göstergesi) ----
    def _yoklayici(self):
        while True:
            time.sleep(0.6)
            d = self.api.get("/api/durum")
            self.kuyruk.put(("durum", d, None))
            # ayarlar canlı güncellensin
            try:
                self._ayarlari_al()
            except Exception:                          # noqa: BLE001
                pass
            # METİN SÜRE TUTUCU — otomatik tespit (ayar açıksa).
            try:
                self._sure_tespit(d)
            except Exception as e:                     # noqa: BLE001
                print("süre tutucu hatası:", e)

    def _durum_goster(self, d):
        if not d:
            self.baglanti_etiket.configure(
                text="● hata: %s" % (self.api.son_hata or "yanıt yok"), fg=HATA)
            self.kapi_etiket.configure(text="")
            return
        self.son_durum = d
        self.baglanti_etiket.configure(text="● bağlı", fg=OK)

        self._anahtarlari_tazele(d)

        p = d.get("proxy") or {}
        k = d.get("kuyruk") or {}
        kapilar = [
            ("proxy", bool(p.get("acik")) and bool(p.get("bagli"))),
            ("enjek", bool(p.get("enjeksiyon"))),
            ("kanal", "Proxy" in str(k.get("kanal", ""))),
        ]
        metin = "  ".join(("%s:%s" % (a, "✓" if v else "✗")) for a, v in kapilar)
        hepsi = all(v for _, v in kapilar)
        self.kapi_etiket.configure(
            text=metin + ("   GÖNDERİM AÇIK" if hepsi else "   gönderim kapalı"),
            fg=HATA if hepsi else SOLUK)

    def _istatistik_tazele(self):
        m = self.motor
        self.ist["durum"].configure(text=m.durum_metni[:34])
        self.ist["oldurulen"].configure(text=str(m.oldurulen))
        self.ist["toplanan"].configure(text=str(m.toplanan))
        self.ist["yang"].configure(text=str(m.yang_toplanan))
        self.ist["gonderilen"].configure(text=str(m.gonderilen))
        self.ist["pencere"].configure(
            text="%d/%d/%d" % (m._pencere_taze, m._pencere_bos, m._pencere_kacti))
        top = m.isabet + m.iskaladi
        self.ist["isabet"].configure(
            text=("%d/%d  %%%.0f" % (m.isabet, top, 100.0 * m.isabet / top))
            if top else "—")
        if m.calisiyor and m.baslangic:
            g = int(time.time() - m.baslangic)
            s, kal = divmod(g, 3600)
            dk, sn = divmod(kal, 60)
            self.ist["sure"].configure(text="%02d:%02d:%02d" % (s, dk, sn))
        self._metin_sure_tazele()
        self._metin_ara_tus_tazele()

    # ---- metin ara tuşu ----

    def _metin_ara_tus(self):
        """Başlat / durdur."""
        g = self.metin_arayici
        if g.calisiyor:
            g.durdur()
        else:
            self._ayarlari_al()
            self._baglan()
            g.ch_bas = int(self.metin_ara_ch_bas_var.get())
            g.ch_son = int(self.metin_ara_ch_son_var.get())
            g.basla()
            if self.motor.calisiyor and self.ayar.metin_ara:
                self._log_yaz("uyari",
                              "bot da metin arıyor — bot çalışırken tuş bekler")
        self._metin_ara_tus_tazele()

    def _metin_ara_tus_tazele(self):
        g = getattr(self, "metin_arayici", None)
        if g is None or not hasattr(self, "metin_ara_btn"):
            return
        # Aralık çalışırken de değiştirilebilsin.
        try:
            g.ch_bas = int(self.metin_ara_ch_bas_var.get())
            g.ch_son = int(self.metin_ara_ch_son_var.get())
        except Exception:                              # noqa: BLE001
            pass
        if g.calisiyor:
            a = g.aralik()
            self.metin_ara_btn.configure(text="■ METİN ARA DURDUR", bg=HATA)
            self.metin_ara_etiket.configure(
                text=("ch%d–ch%d  %s" % (a[0], a[-1], g.durum_metni))[:60],
                fg=METIN)
        else:
            self.metin_ara_btn.configure(text="▶ METİN ARA BAŞLAT", bg=OK)
            self.metin_ara_etiket.configure(text="kapalı", fg=SOLUK)

    # ---- metin süre tutucu ----

    def _su_anki_kanal(self):
        p = (self.son_durum or {}).get("proxy") or {}
        return port_kanali(p.get("port", 0))

    def _sure_kaydet(self):
        """Sayaçlar değişince hemen diske: uygulama kapanınca kaybolmasın."""
        try:
            self.metin_sure_kayit_var.set(json.dumps(self.sure_tutucu.disari()))
            self.ayarlari_kaydet(sessiz=True)
        except Exception as e:                         # noqa: BLE001
            print("süre kaydı hatası:", e)

    def _metin_kesildi(self, kanal, ad):
        dk = int(self.metin_sure_dk_var.get())
        if kanal:
            self._log_yaz("basari", "METİN KESİLDİ: %s — ch%d için %d dk "
                          "sayaç başladı" % (ad, kanal, dk))
        else:
            self._log_yaz("uyari", "METİN KESİLDİ: %s — kanal bilinmiyor, "
                          "sayaç 'ch?' olarak tutulamadı" % ad)
        self._sure_kaydet()
        self._sure_etiket_zaman = 0.0
        self._metin_sure_tazele()

    def _metin_sure_elle(self):
        """'Bu kanalda kestim': bulunduğun kanalın sayacını başlatır."""
        kanal = self._su_anki_kanal()
        if not kanal:
            self._log_yaz("uyari", "bulunduğun kanal bilinmiyor — proxy bağlı mı?")
            return
        self._metin_sure_baslat(kanal)

    def _metin_sure_baslat(self, kanal):
        """Kanal satırındaki ▶: o kanalın sayacını başlatır (çalışıyorsa baştan)."""
        dk = int(self.metin_sure_dk_var.get())
        self.sure_tutucu.baslat(kanal, dk)
        self._log_yaz("bilgi", "ch%d için %d dk sayaç başlatıldı" % (kanal, dk))
        self._sure_kaydet()
        self._sure_etiket_zaman = 0.0
        self._metin_sure_tazele()

    def _metin_sure_temizle(self, kanal):
        """Kanal satırındaki ✕: yalnızca o kanalın sayacını siler."""
        self.sure_tutucu.sifirla(kanal)
        self._log_yaz("bilgi", "ch%d sayacı silindi" % kanal)
        self._sure_kaydet()
        self._sure_etiket_zaman = 0.0
        self._metin_sure_tazele()

    def _sure_tespit(self, d):
        """
        Yakındaki metin kırılınca sayacı kendiliğinden başlatır.

        Yalnızca 'Kırılınca otomatik başlat' açıksa çalışır. Kapalıyken
        izleme sıfırlanır; açıldığında arada kaybolan metinler "kırıldı"
        sanılmasın.

        Döner: [(kanal, metin adı), ...]
        """
        if not (self.ayar.metin_sure_tutucu and self.ayar.metin_sure_otomatik):
            self.sure_tutucu.izlemeyi_sifirla()
            return []
        if not isinstance(d, dict):
            return []
        v = self.api.get("/api/varliklar", n=120)
        if not isinstance(v, list):
            return []
        olaylar = self.sure_tutucu.guncelle(d, v, self.ayar.metin_sure_dk)
        for kanal, ad in olaylar:
            self.kuyruk.put(("metin_kesildi", kanal, ad))
        return olaylar

    def _metin_sure_sifirla(self):
        self.sure_tutucu.sifirla()
        self._log_yaz("bilgi", "metin süre sayaçları sıfırlandı")
        self._sure_kaydet()
        self._sure_etiket_zaman = 0.0
        self._metin_sure_tazele()

    def _metin_sure_tazele(self):
        simdi = time.time()
        if simdi - self._sure_etiket_zaman < 1.0:
            return
        self._sure_etiket_zaman = simdi
        if not self._sure_yuklendi:
            self._sure_yuklendi = True
            try:
                self.sure_tutucu.iceri(
                    json.loads(self.metin_sure_kayit_var.get() or "{}"))
            except Exception:                          # noqa: BLE001
                pass
        self._sure_tutucu_esitle()
        aktif = self.metin_sure_var.get()
        su_an = self._su_anki_kanal()
        if su_an:
            # Bulunduğun kanal "gidildi" sayılır: süresi dolduysa yeşil söner.
            self.sure_tutucu.goruldu(su_an, simdi)
        # Tur yenilenmesini günlüğe yazmak için son dolma anları. İlk
        # tazelemede (uygulama açılışı) kapalıyken geçen turlar yazılmaz.
        son_dogus = getattr(self, "_sure_son_dogus", None)
        ilk = son_dogus is None
        if ilk:
            son_dogus = self._sure_son_dogus = {}
        yenilenen = []
        for kanal, et in self.sure_etiketleri.items():
            kalan = self.sure_tutucu.kalan(kanal, simdi)
            dogus = self.sure_tutucu.doguslar.get(kanal)
            if not ilk and dogus is not None and dogus != son_dogus.get(kanal):
                yenilenen.append(kanal)
            son_dogus[kanal] = dogus
            if kalan is None:
                metin, renk = "ch%d  —" % kanal, SOLUK
            elif kalan > 0:
                dk, sn = divmod(int(math.ceil(kalan)), 60)
                metin = "ch%d  %d:%02d" % (kanal, dk, sn)
                renk = OK if self.sure_tutucu.hazir_mi(kanal, simdi) else UYARI
            else:
                metin, renk = "ch%d  HAZIR" % kanal, OK
            if kanal == su_an:
                metin = "● " + metin
            et.configure(text=metin, fg=renk if aktif else SOLUK)
        if yenilenen:
            tur_dk = self.sure_tutucu.tekrar_dk or 0
            for kanal in yenilenen:
                self._log_yaz("bilgi",
                              "ch%d süresi doldu — metin çıkmış olmalı; sayaç "
                              "%d dk yeniden başladı" % (kanal, tur_dk))
            self._sure_kaydet()

    def _sure_tutucu_esitle(self):
        """Tekrar ayarını ve süreyi sayaca geçirir (bot da aynı sayacı okur)."""
        try:
            self.sure_tutucu.tekrar = bool(self.metin_sure_tekrar_var.get())
            self.sure_tutucu.tekrar_dk = max(1, int(self.metin_sure_dk_var.get()))
        except Exception:                              # noqa: BLE001
            pass

    def _kuyrugu_isle(self):
        try:
            while True:
                tip, a, b = self.kuyruk.get_nowait()
                if tip == "log":
                    self._log_yaz(a, b)
                elif tip == "durum":
                    self._durum_goster(a)
                    # Köy değiştiyse O HARİTANIN market noktasını yükle.
                    # Kullanıcı hiçbir şey yapmadan doğru market gelsin.
                    try:
                        k = (a or {}).get("konum") or {}
                        if k.get("bilinir"):
                            self._market_haritadan_yukle(int(k.get("x", 0)),
                                                         int(k.get("y", 0)))
                    except Exception:               # noqa: BLE001
                        pass
                elif tip == "adres":
                    self.adres_var.set(a)
                elif tip == "rota":
                    self._rota_tazele()
                elif tip == "metin_kesildi":
                    self._metin_kesildi(a, b)
                elif tip == "sure_kaydet":
                    self._sure_kaydet()
                    self._sure_etiket_zaman = 0.0
        except queue.Empty:
            pass
        except Exception as e:                         # noqa: BLE001
            print("UI hatası:", e)
        if getattr(self, "_kapaniyor", False):
            return
        self._istatistik_tazele()
        self.after(100, self._kuyrugu_isle)


if __name__ == "__main__":
    TamBot().mainloop()
