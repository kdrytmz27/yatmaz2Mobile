# -*- coding: utf-8 -*-
"""
METİN İZLEYİCİ — görüntüsüz Romia2 istemcisi.

Hesap, metin alanında bırakılmış karakteriyle oyuna GÖRÜNTÜSÜZ girer.
Emülatör, ekran ya da oyun istemcisi yok: yalnızca oyunun ağ protokolü.
Sunucu o karaktere çevresindeki varlıkları gönderdiği için kanalda metin
var mı yok mu anında bilinir.

İKİ ÇALIŞMA ŞEKLİ
-----------------
Sabit:   hesap tek kanalda durur  ("kanal": 3). Metin çıktığı / gittiği an
         saatiyle kaydedilir.
Tarama:  hesap kanalları sırayla gezer  ("tarama": [1, 2, ..., 8] ya da
         --tarama 1-8). Her kanalda birkaç saniye bakar, oyunun kendi kanal
         menüsünün gönderdiği "/change_channel N" komutuyla sonrakine geçer.
         Sunucu geri sayar ("3 saniye sonra..."), istemci ~3,1 sn sonra eski
         bağlantıyı KENDİSİ kapatır (sunucu kapatmaz) ve yeni kanalın
         harita sunucusuna AYNI giriş anahtarıyla bağlanır — şifre tekrar
         gönderilmez (log/kanal_20260829_234729.pcap: dört geçişte de anahtar
         aynı). Karakter her kanalda aynı noktada doğar.

NE GÖNDERİR
-----------
    0x6F LOGIN3     giriş sunucusuna kullanıcı adı + şifre + PIN
    0x6D LOGIN2     kanal sunucusuna kullanıcı adı + giriş anahtarı + PIN
    0x06            karakter seç
    0x0A            oyuna gir
    0x03            yalnızca "/change_channel N" (tarama)
    0xFF / 0xFC     el sıkışma / zaman eşleme cevabı
    0xFE            PONG

Hareket, saldırı, sohbet mesajı YOK — karakter olduğu yerde durur.

KESİLİYOR / KESİLDİ
-------------------
Sunucu çevredeki dövüşü izleyene de yollar (kayıtlarda 0x3E saldıran+hedef:
oyuncu->canavar 1525 paket; karakter hiç saldırmazken bile 306). Metne
vurulunca "KESİLİYOR" (vuran adı + mesafesi), 15 sn vuruş gelmezse
"BIRAKTI", metin kaybolunca / ölüm animasyonunda "KESİLDİ" yazılır.
Vuruş paketi gelmese bile 4 m içinde 3 sn duran oyuncu "YANINDA" diye
bildirilir. Metnin CAN paketi (0x3F) yalnızca onu hedefleyene gider, izleyene
gelmez — can düşüşü vuruşlardan anlaşılır.

PROTOKOL (şifresiz; 13 Eyl 2026'da gerçek sunucuda doğrulandı)
-------------------------------------------------------------
    sunucu:  FD 01 | FF hs t delta          faz=HANDSHAKE + el sıkışma
    istemci: FF hs (t + 2*delta) 0          delta 0 olana dek tekrar
    sunucu:  FD 0A (giriş sunucusu: faz=AUTH) / FD 02 (kanal: faz=LOGIN)
    istemci: 6F login[31] pwd[17] u32 pin   (giriş sunucusu 30001-30003)
    sunucu:  96 u32 anahtar | u8 sonuç      1 = başarılı
    istemci: 6D login[31] u32 anahtar u32 pin    (kanal k girişi: 30001 + 4k)
    sunucu:  5A (278 bayt) karakter listesi: yuva 0'da x@44 y@48
             lAddr@52 (ağ sırası) wPort@56 — karakterin harita sunucusu
    istemci: harita sunucusuna (30003 + 4k) yeniden bağlan, 6D tekrar
    istemci: 06 yuva  ->  sunucu yükleme verisi  ->  istemci: 0A
    oyunda:  sunucu 2C PING -> istemci FE ; sunucu FC -> istemci FC
    kanal:   istemci 03 | u16 boy | u8 0 | "/change_channel N\\0"

PIN: TPacketCGLogin2.iLoginPin (istemci dökümündeki alan adı).
Gelen akış APK'daki kanıtlanmış çerçevelemeyle bölünür
(app/.../PaketAyristirici.java). 0x01 CHARACTER_ADD: vid@1 x@9 y@13
tür@21 (2 = metin) vnum@22.

KULLANIM
--------
1) İlk çalıştırmada metin_izleyici.json oluşturulur; hesapları yaz.
2) Karakteri oyunda metin alanının ORTASINA bırak (görüş ~50 m, alan
   ~60x60 m) ve oyundan çık.
3) Çalıştır:

    python tools/metin_izleyici.py --kanal 1                # ch1'de dur
    python tools/metin_izleyici.py --kanal 1 --tarama 1-8   # ch1 hesabı 8 kanalı gezer
    python tools/metin_izleyici.py                          # dosyadaki bütün hesaplar
    ... --ayikla                                            # paket başlıkları + teşhis

Durum:  http://127.0.0.1:30210/durum   (JSON)
Olaylar: log/metin_izleyici_olaylar.jsonl  (ilk / cikti / gitti / tarama)

GÜVENLİK
--------
Şifre ve PIN yalnızca metin_izleyici.json'da durur ve yalnızca oyunun
sunucusuna gönderilir; ekrana ve günlüğe asla yazılmaz. Oyunun protokolü
şifresiz olduğu için (oyunun kendisinde de) şifre ağda açık gider.
Bir hesap aynı anda tek yerde oturum açabilir: izleyicinin kullandığı
hesapla oyuna girersen izleyici (ya da oyun) düşer.
"""

import argparse
import http.server
import json
import math
import os
import random
import socket
import struct
import sys
import threading
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
# EXE (PyInstaller) olarak paketlenince: kod _MEIPASS'ta (geçici), ama
# ayar/günlük EXE'nin yanında (kalıcı) tutulmalı. VERI_KOK bunu ayırır.
if getattr(sys, "frozen", False):
    VERI_KOK = os.path.dirname(sys.executable)
else:
    VERI_KOK = KOK
AYAR_DOSYASI = os.path.join(VERI_KOK, "metin_izleyici.json")
OLAY_DOSYASI = os.path.join(VERI_KOK, "log", "metin_izleyici_olaylar.jsonl")
KATALOG_KLASORU = os.path.join(KOK, "app", "src", "main", "assets")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                   # noqa: BLE001
        pass

VARSAYILAN = {
    "sunucu": "185.128.114.87",
    # Giriş (kimlik) sunucuları. 30004 DEĞİL: 13 Eyl 2026 denemesinde LOGIN3'e
    # hiç cevap vermedi; ölçüm kaydında da 2 dk boyunca bir haritada (Siyah
    # Metin) kalınan oyun sunucusu olarak görüldü. 30001/30002/30003 ise
    # kayıtta hep 1 sn görünüp ardından kanal giriş sunucusu geliyor.
    "giris_portlari": [30001, 30002, 30003],
    # Metin Tu-Young. Boş liste + tum_metinler=true -> her metin.
    "metin_vnumlari": [8026],
    "tum_metinler": False,
    "http_portu": 30210,
    "baslama_araligi_sn": 3,
    "zaman_asimi_sn": 15,
    "yeniden_baglan_sn": 10,
    "yeniden_baglan_tavan_sn": 120,
    "oyuna_giris_bekle_sn": 3,
    "yukleme_sonrasi_sn": 0.5,
    "sessizlik_sn": 300,
    "ilk_gorus_sn": 15,
    "hata_bekleme_carpani": 1.0,
    # TARAMA: her kanalda oyuna girdikten sonra bakma süresi (sn)
    "tarama_bakis_sn": 5,
    # /change_channel sonrası eski bağlantıyı bırakmadan önce bekleme (sn).
    # Sunucu kapatMAZ: kayıtta beş geçişin beşinde de sunucu 3,07 sn'de
    # çevredeki varlıkları sildi (0x02), istemci 3,08-3,12 sn'de KENDİSİ kapattı.
    "kanal_degisim_bekle_sn": 3.3,
    # Port düzeni değişirse: {"3": [giris_portu, harita_portu]}
    "kanal_portlari": {},
    # KESİLİYOR bu kadar sn vuruş gelmezse BIRAKTI olur
    "kesme_bitis_sn": 15,
    # Oyuncu metnin 4 m içinde bu kadar sn durursa YANINDA
    "yakin_bekle_sn": 3,
    # ÖLÜNCE YERİNDE CANLAN (paket gönderir — varsayılan kapalı)
    "olunce_canlan": False,
    "canlan_komut": "/restart_here",     # 13 Eyl 2026 kaydında doğrulandı
    "canlan_gecikme_sn": 1.5,
    # ÖLÜNCE KANALDAN ÇIKIP TEKRAR GİR (yeniden girişte canlı gelir).
    # /restart_here çalışmayan sunucularda güvenilir canlanma yolu.
    "olunce_yeniden_gir": False,
    "yeniden_gir_gecikme_sn": 1.5,       # ölümden sonra çık-gir'e kadar bekleme
    # KISA MESAFE YERİNE DÖN (paket gönderir — varsayılan kapalı)
    "yerine_don": False,
    "yerine_esik_m": 3,                  # bu kadar uzaklaşınca dönmeye başla
    "yerine_azami_m": 40,                # bundan uzaksa dönme (duvar/ölüm riski)
    "hareket_araligi_sn": 0.5,
    # BUFF'ÇI (paket gönderir — varsayılan kapalı). Rolü "buff" olan hesap,
    # buff_hedef adlı oyuncu buff_menzil_m içine gelince onu seçip yetenekleri
    # basar. vnum 0 = o yetenek kullanılmaz (yetenek vnum'unu bulmak için
    # tools/yetenek_kaydet.py).
    "buff_acik": False,
    "buff_hedef": "",                    # örn. "YIKAR"
    "buff_yardim_vnum": 94,              # Ejderha Yardımı (14 Eyl 2026 kaydından)
    "buff_guc_vnum": 96,                 # Ejderha Gücü
    "buff_menzil_m": 4,
    "buff_aralik_sn": 8,                 # aynı oyuncuya yeniden basma aralığı
    # İki yetenek arasındaki bekleme (sn). 0 = aynı anda (animasyon çakışır,
    # oyun ikinciyi atabilir). Şaman animasyonu ~sürsün diye varsayılan 5.
    "buff_skill_gecikme_sn": 5,
    "hesaplar": [],
}

# ── başlıklar ────────────────────────────────────────────────────
H_PHASE = 0xFD
H_HANDSHAKE = 0xFF
H_TIME_SYNC = 0xFC
H_PING = 0x2C
H_PONG = 0xFE
H_CHAT = 0x03
H_LOGIN3 = 0x6F
H_AUTH_SUCCESS = 0x96
H_LOGIN2 = 0x6D
H_LOGIN_SUCCESS = 0x5A
H_LOGIN_FAILURE = 0x07
H_CHARACTER_SELECT = 0x06
H_ENTERGAME = 0x0A
H_HAREKET = 0x07
H_KENDI_DURUM = 0x11
H_OLUM = 0x46
# tambot.py'de 29 Ağu 2026 canlı yakalamasıyla doğrulandı:
H_HEDEF = 0x3D            # CG_TARGET  (5 bayt): 3D | vid
H_YETENEK = 0x34          # CG_USE_SKILL (9 bayt): 34 | vnum | vid
FUNC_DUR = 0
FUNC_YURU = 1

FAZ_HANDSHAKE, FAZ_LOGIN, FAZ_SELECT, FAZ_LOADING, FAZ_GAME = 1, 2, 3, 4, 5
# Giriş (kimlik) sunucusu el sıkışmadan sonra LOGIN'e değil AUTH'a geçer
# (13 Eyl 2026 denemesi: 30001-30003 hepsi "FD 0A" gönderdi).
FAZ_AUTH = 10
TIP_METIN = 2
TIP_ADLARI = {0: "canavar", 1: "npc", 2: "metin", 6: "oyuncu"}
TIP_OYUNCU = 6
YAKIN_HAM = 400           # 4 m: oyuncu metnin "yanında" (YANINDA olayı)
GORUNUR_OYUNCU_HAM = 400  # 4 m: metnin başında sayılıp "oyuncu var" gösterilir
KARAKTER_LISTESI_BOYU = 278

# Giriş fazında beklenen paketlerin boyları.
GIRIS_BOYLARI = {H_PHASE: 2, H_HANDSHAKE: 13, H_TIME_SYNC: 13, H_PING: 1,
                 H_AUTH_SUCCESS: 6, H_LOGIN_SUCCESS: KARAKTER_LISTESI_BOYU,
                 H_LOGIN_FAILURE: 10}

# Sunucunun giriş reddi (TPacketGCLoginFailure.szStatus) -> (açıklama, bekleme sn)
GIRIS_HATALARI = {
    "WRONGPWD": ("şifre yanlış", 3600),
    "NOID": ("böyle bir hesap yok", 3600),
    "ALREADY": ("hesap zaten açık (oyunda mı?)", 60),
    "BLOCK": ("hesap engelli", 3600),
    "FULL": ("sunucu dolu", 60),
    "SHUTDOWN": ("sunucu kapanıyor", 120),
    "BESAMEKEY": ("giriş anahtarı geçersiz", 10),
}


def kanal_giris_portu(kanal):
    return 30001 + 4 * int(kanal)


def kanal_harita_portu(kanal):
    return 30003 + 4 * int(kanal)


def tarama_coz(metin):
    """'1-8' / '1,3,5' / '2-4,7' -> kanal listesi (1..8, sıra korunur)."""
    liste = []
    for parca in str(metin).replace(" ", "").split(","):
        if not parca:
            continue
        if "-" in parca:
            a, b = parca.split("-", 1)
            a, b = int(a), int(b)
            adim = 1 if b >= a else -1
            aralik = range(a, b + adim, adim)
        else:
            aralik = [int(parca)]
        for k in aralik:
            if not 1 <= k <= 8:
                raise ValueError("kanal 1-8 arası olmalı: %d" % k)
            if k not in liste:
                liste.append(k)
    if not liste:
        raise ValueError("boş kanal listesi")
    return liste


# ── paket kurucular ──────────────────────────────────────────────

def _alan(metin, boy):
    """NUL ile biten, NUL ile doldurulmuş sabit alan."""
    b = (metin or "").encode("cp1254", "replace")[:boy - 1]
    return b + b"\x00" * (boy - len(b))


def ad_fold(s):
    """Ad karşılaştırması: Türkçe harfleri düzle + küçük harf (panel ile aynı)."""
    s = (s or "").strip()
    for a, b in (("İ", "i"), ("I", "i"), ("ı", "i"), ("Ş", "s"), ("ş", "s"),
                 ("Ğ", "g"), ("ğ", "g"), ("Ü", "u"), ("ü", "u"),
                 ("Ö", "o"), ("ö", "o"), ("Ç", "c"), ("ç", "c")):
        s = s.replace(a, b)
    return s.lower().replace("̇", "")


def pin_coz(deger):
    """Ayardaki PIN -> sayı; boş ya da rakam dışıysa None."""
    metin = str(deger if deger is not None else "").strip()
    if not metin.isdigit() or len(metin) > 9:
        return None
    return int(metin)


def paket_login3(kullanici, sifre, pin):
    return struct.pack("<B31s17sI", H_LOGIN3, _alan(kullanici, 31),
                       _alan(sifre, 17), int(pin) & 0xFFFFFFFF)


def paket_login2(kullanici, anahtar, pin):
    return struct.pack("<B31sII", H_LOGIN2, _alan(kullanici, 31),
                       int(anahtar) & 0xFFFFFFFF, int(pin) & 0xFFFFFFFF)


def paket_karakter_sec(yuva):
    return bytes([H_CHARACTER_SELECT, int(yuva) & 0xFF])


def paket_oyuna_gir():
    return bytes([H_ENTERGAME])


def paket_pong():
    return bytes([H_PONG])


def paket_hareket(func, rot, x, y, tik):
    """CG_MOVE: 07 | func | 00 | rot | x(i32) | y(i32) | tik(u32) — 16 bayt.

    13 Eyl 2026 kaydından: func=1 yürü, func=0 dur; rot 0..71 (5 derece adım).
    """
    return struct.pack("<BBBBiiI", H_HAREKET, int(func) & 0xFF, 0, int(rot) & 0xFF,
                       int(x), int(y), int(tik) & 0xFFFFFFFF)


def yon_rot(dx, dy):
    """(dx, dy) yönü -> rot baytı (oyun 5 derecelik adımlarla sayar)."""
    aci = math.degrees(math.atan2(dy, dx))
    return int(round((90 - aci) / 5.0)) % 72


def _tik():
    """İstemci saati (ms) — artan; sunucu monotonluğa bakar."""
    return int(time.time() * 1000) & 0xFFFFFFFF


def paket_sohbet(metin, tur=0):
    """CG_CHAT: 03 | u16 toplam boy | u8 tür | metin + NUL.

    Kayıt: '/change_channel 2' = 22 bayt, tür 0.
    """
    govde = (metin or "").encode("cp1254", "replace") + b"\x00"
    return struct.pack("<BHB", H_CHAT, 4 + len(govde), tur) + govde


def paket_hedef(vid):
    """CG_TARGET (5 bayt): 3D | vid(u32). Bir varlığı seçer."""
    return struct.pack("<BI", H_HEDEF, int(vid) & 0xFFFFFFFF)


def paket_yetenek(vnum, vid=0):
    """CG_USE_SKILL (9 bayt): 34 | vnum(u32) | vid(u32). vid=0 kendine."""
    return struct.pack("<BII", H_YETENEK, int(vnum) & 0xFFFFFFFF,
                       int(vid) & 0xFFFFFFFF)


def paket_zaman_cevabi(baslik, hs, zaman, delta):
    """El sıkışma / zaman eşleme cevabı: kayıtta istemci t + 2*delta döndü."""
    return struct.pack("<BIIi", baslik, hs & 0xFFFFFFFF,
                       (int(zaman) + 2 * int(delta)) & 0xFFFFFFFF, 0)


# ── çerçeveleme (oyun fazı) ──────────────────────────────────────

def _i32(d, o):
    return struct.unpack_from("<i", d, o)[0]


def _u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def _u16(d, o):
    return struct.unpack_from("<H", d, o)[0]


def _makul_id(v):
    return 0 < v < 100000000


def _makul_ham(v):
    return 0 < v < 30000000


# APK'daki sabit boylu paketler ve doğrulama ofseti (vid alanı; None = yok)
_SABIT = {
    0x11: (14, 1), 0x3E: (9, None), 0x3F: (14, 1), 0x46: (10, None),
    0x47: (17, 1), 0x87: (10, 1), 0x0D: (5, 1), 0x0E: (5, 1), 0x1B: (5, 1),
    0x6F: (6, 1), 0x72: (6, None), 0x13: (43, 1), 0xB3: (8, None),
}


def oyun_mesaj_boyu(d, i, hs=None, bak=True):
    """
    d[i]'de başlayan sunucu mesajının boyu.

    Döner: >0 boy; 0 geçersiz başlangıç (1 bayt kay); -1 gövde eksik.
    PING (0x2C) ve FAZ (0xFD) çok kısa olduğu için ancak arkalarından geçerli
    bir mesaj geliyorsa ya da akış orada bitiyorsa kabul edilir (bak=True).
    """
    n = len(d)
    kalan = n - i
    if kalan <= 0:
        return -1
    h = d[i]
    if h == 0x01:
        if kalan < 38:
            return -1
        if not _makul_id(_i32(d, i + 1)):
            return 0
        if not (_makul_ham(_i32(d, i + 9)) and _makul_ham(_i32(d, i + 13))):
            return 0
        return 38
    if h == 0x02:
        if kalan < 5:
            return -1
        return 5 if _makul_id(_i32(d, i + 1)) else 0
    if h == 0x03:
        if kalan < 24:
            return -1
        if not _makul_id(_i32(d, i + 4)):
            return 0
        if not (_makul_ham(_i32(d, i + 8)) and _makul_ham(_i32(d, i + 12))):
            return 0
        return 24
    if h == 0x04:
        if kalan < 3:
            return -1
        boy = _u16(d, i + 1)
        if boy < 4 or boy > 2000:
            return 0
        return boy if kalan >= boy else -1
    if h == 0x05:
        if kalan < 3:
            return -1
        boy = _u16(d, i + 1)
        govde = boy - 3
        if govde <= 0 or govde % 12 or boy > 1500:
            return 0
        if kalan < boy:
            return -1
        for k in range(i + 3, i + boy, 12):
            if not (_makul_id(_i32(d, k)) and _makul_ham(_i32(d, k + 4))
                    and _makul_ham(_i32(d, k + 8))):
                return 0
        return boy
    if h == 0x26:
        if kalan < 4:
            return -1
        boy = _u16(d, i + 1)
        if boy < 4 or boy > 4096 or d[i + 3] > 0x0F:
            return 0
        return boy if kalan >= boy else -1
    if h == 0x1A:
        if kalan < 21:
            return -1
        if _i32(d, i + 9) != 0 or not _makul_ham(_i32(d, i + 1)) \
                or not _makul_ham(_i32(d, i + 5)) or not _makul_id(_i32(d, i + 13)):
            return 0
        vnum = _i32(d, i + 17)
        return 21 if 0 < vnum <= 100000 else 0
    if h == 0x1F:
        if kalan < 30:
            return -1
        if not _makul_id(_i32(d, i + 1)) or not 32 <= d[i + 5] <= 126:
            return 0
        return 30
    if h == 0x88:
        if kalan < 62:
            return -1
        if not _makul_id(_i32(d, i + 1)) or not 32 <= d[i + 5] <= 126:
            return 0
        return 62
    if h in (H_HANDSHAKE, H_TIME_SYNC):
        if kalan < 13:
            return -1
        # El sıkışma kimliği oturum boyunca aynı: güçlü doğrulama.
        if hs is None or _u32(d, i + 1) != hs:
            return 0
        return 13
    if h in (H_PING, H_PHASE):
        boy = 1 if h == H_PING else 2
        if kalan < boy:
            return -1
        if h == H_PHASE and d[i + 1] > 10:
            return 0
        if not bak:
            return 0
        if kalan == boy or oyun_mesaj_boyu(d, i + boy, hs, bak=False) > 0:
            return boy
        return 0
    if h in _SABIT:
        boy, vid_ofset = _SABIT[h]
        if kalan < boy:
            return -1
        if h == 0x3E:
            saldiran = _i32(d, i + 1)
            if (saldiran != 0 and not _makul_id(saldiran)) or not _makul_id(_i32(d, i + 5)):
                return 0
        elif h == 0x46:
            if not (_makul_id(_i32(d, i + 2)) and _makul_id(_i32(d, i + 6))):
                return 0
        elif h == 0x47:
            if not (_makul_id(_i32(d, i + 1)) and _makul_id(_i32(d, i + 5))):
                return 0
        elif vid_ofset is not None and not _makul_id(_i32(d, i + vid_ofset)):
            return 0
        return boy
    return 0


def karakter_bilgisi(pkt, yuva, ip_bayt):
    """0x5A karakter listesinden yuvadaki karakterin (x, y, port); yoksa None."""
    konumlar = []
    if ip_bayt:
        konumlar = [i for i in range(1, len(pkt) - 5) if pkt[i:i + 4] == ip_bayt]
    if yuva < len(konumlar):
        o = konumlar[yuva]
    elif yuva == 0 and len(pkt) >= 58 and _u16(pkt, 56):
        o = 52
    else:
        return None
    if o < 9:
        return None
    x, y = struct.unpack_from("<ii", pkt, o - 8)
    return x, y, _u16(pkt, o + 4)


# ── katalog / olay kaydı ─────────────────────────────────────────

def katalog_yukle(klasor=None):
    """vnum -> ad (entities_tr: 'Ad (LvN)', metins_tr yedek)."""
    klasor = klasor or KATALOG_KLASORU
    adlar = {}
    try:
        with open(os.path.join(klasor, "entities_tr.txt"), encoding="utf-8") as f:
            for satir in f:
                p = satir.rstrip("\r\n").split("\t")
                if len(p) >= 5 and p[0].isdigit():
                    seviye = p[3].strip()
                    adlar[int(p[0])] = ("%s (Lv%s)" % (p[4], seviye)
                                        if seviye.isdigit() and seviye != "0" else p[4])
    except OSError:
        pass
    try:
        with open(os.path.join(klasor, "metins_tr.txt"), encoding="utf-8") as f:
            for satir in f:
                p = satir.rstrip("\r\n").split("\t")
                if len(p) >= 2 and p[0].isdigit():
                    adlar.setdefault(int(p[0]), p[1])
    except OSError:
        pass
    return adlar


_olay_kilidi = threading.Lock()


def olay_yaz(kayit):
    yol = OLAY_DOSYASI
    with _olay_kilidi:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


# ── bağlantı ─────────────────────────────────────────────────────

class GirisHatasi(Exception):
    """Sunucu girişi reddetti. bekle: yeniden denemeden önce saniye."""

    def __init__(self, mesaj, bekle=300):
        super().__init__(mesaj)
        self.bekle = bekle


class Baglanti(object):
    def __init__(self, host, port, sure, ayikla=None):
        self.port = int(port)
        self.ayikla = ayikla
        self.s = socket.create_connection((host, self.port), timeout=sure)
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.tampon = bytearray()
        self.hs = None
        self.faz = 0

    def gonder(self, veri, ad):
        self.s.sendall(veri)
        if self.ayikla:
            # İçerik ASLA yazılmaz (LOGIN3 şifre taşır): yalnızca başlık ve boy.
            self.ayikla("  -> %-12s 0x%02x %d bayt (port %d)"
                        % (ad, veri[0], len(veri), self.port))

    def al(self, sure):
        self.s.settimeout(max(0.05, sure))
        try:
            veri = self.s.recv(65536)
        except socket.timeout:
            return False
        if not veri:
            raise ConnectionError("sunucu bağlantıyı kapattı (port %d)" % self.port)
        self.tampon += veri
        if self.ayikla:
            self.ayikla("  <- %d bayt, ilk 0x%02x (port %d)"
                        % (len(veri), veri[0], self.port))
        return True

    def kapat(self):
        try:
            self.s.close()
        except OSError:
            pass


# ── izleyici ─────────────────────────────────────────────────────

class Izleyici(threading.Thread):
    """Tek hesap: bir kanalda bekler ya da kanalları sırayla tarar."""

    def __init__(self, hesap, ayar, adlar, bildir, ayikla=False):
        super().__init__(daemon=True)
        self.tarama = [int(k) for k in (hesap.get("tarama") or [])]
        self.kanal = self.tarama[0] if self.tarama else int(hesap["kanal"])
        self.name = ("izleyici-tarama" if self.tarama else "izleyici-ch%d" % self.kanal)
        self._kullanici = (hesap.get("kullanici") or "").strip()
        self._sifre = hesap.get("sifre") or ""
        self._pin = pin_coz(hesap.get("pin")) or 0
        self.yuva = int(hesap.get("karakter_yuvasi", 0) or 0)
        self._giris_portu = hesap.get("giris_portu")
        self._harita_portu = hesap.get("harita_portu")
        self.ayar = ayar
        self.adlar = adlar or {}
        self._bildir = bildir
        self._ayikla = ayikla
        self.host = ayar.get("sunucu", VARSAYILAN["sunucu"])
        try:
            self.ip_bayt = socket.inet_aton(socket.gethostbyname(self.host))
        except OSError:
            self.ip_bayt = b""
        self.sure = float(ayar.get("zaman_asimi_sn", 15))
        self.taban = float(ayar.get("yeniden_baglan_sn", 10))
        self.tavan = float(ayar.get("yeniden_baglan_tavan_sn", 120))
        self.giris_bekle = float(ayar.get("oyuna_giris_bekle_sn", 3))
        self.giris_gecikme = float(ayar.get("yukleme_sonrasi_sn", 0.5))
        self.sessizlik = float(ayar.get("sessizlik_sn", 300))
        self.ilk_pencere = float(ayar.get("ilk_gorus_sn", 15))
        self.carpan = float(ayar.get("hata_bekleme_carpani", 1.0))
        self.bakis_sn = float(hesap.get("bakis_sn") or ayar.get("tarama_bakis_sn", 5))
        self.degisim_bekle = float(ayar.get("kanal_degisim_bekle_sn", 3.3))
        self.kesme_bitis = float(ayar.get("kesme_bitis_sn", 15))
        self.yakin_sure = float(ayar.get("yakin_bekle_sn", 3))
        self.olunce_canlan = bool(ayar.get("olunce_canlan"))
        self.olunce_yeniden_gir = bool(ayar.get("olunce_yeniden_gir"))
        self.canlan_komut = ayar.get("canlan_komut") or "/restart_here"
        self.canlan_gecikme = float(ayar.get("canlan_gecikme_sn", 1.5))
        self.yeniden_gir_gecikme = float(ayar.get("yeniden_gir_gecikme_sn", 1.5))
        self.yerine_don = bool(ayar.get("yerine_don"))
        self.yerine_esik = float(ayar.get("yerine_esik_m", 3)) * 100.0
        self.yerine_azami = float(ayar.get("yerine_azami_m", 40)) * 100.0
        self.hareket_araligi = float(ayar.get("hareket_araligi_sn", 0.5))
        self.vnumlar = set(int(v) for v in ayar.get("metin_vnumlari", []) or [])
        self.tum_metinler = bool(ayar.get("tum_metinler"))
        # BUFF'ÇI rolü (paket gönderir). Rol hesapta; parametreler global ayar.
        self.rol = (hesap.get("rol") or "izleyici").strip().lower()
        self.buff_acik = bool(ayar.get("buff_acik"))
        self.buff_hedef = ad_fold(ayar.get("buff_hedef") or "")
        self.buff_vnumlar = [int(v) for v in (ayar.get("buff_yardim_vnum", 0),
                                              ayar.get("buff_guc_vnum", 0)) if int(v) > 0]
        self.buff_menzil = float(ayar.get("buff_menzil_m", 4)) * 100.0
        self.buff_aralik = float(ayar.get("buff_aralik_sn", 8))
        self.buff_skill_gecikme = float(ayar.get("buff_skill_gecikme_sn", 5))
        self._son_buff = {}        # vid -> son basma anı (oyuncuya göre bekleme)
        self._buff_sira = []       # [(zaman, vnum, vid)] gecikmeli yetenek kuyruğu
        self.istek_kanal = None    # panelden "bu kanala çek" isteği

        self.calisiyor = True
        self.durum = "başlamadı"
        self.oyunda = False
        self.oturum = 0
        self.tur_sayisi = 0
        self.konum = None
        self.metinler = {}
        # Teşhis: görülen BÜTÜN varlıklar (vid -> [tip, vnum, x, y]). "Metin
        # yok" dendiğinde karakterin çevresinde ne olduğunu gösterir.
        self.varliklar = {}
        self.ag_adlari = {}        # vid -> oyuncu adı (0x88)
        self.son_kirilma = 0.0     # bu kanalda en son metin kırıldığı an (epoch)
        self.kendi_vid = 0         # 0x11 ya da spawn konumundan
        self._kendi_vid_kesin = False   # konumdan doğrulandıysa 0x11 ezmesin
        self.kendi_konum = None    # kendi karakterin canlı konumu (0x03/0x05)
        self.yer = None            # park noktası (girişteki konum) — dönülecek yer
        self._oldu = False
        self._canlan_at = 0.0
        self._yeniden_gir = False       # ölünce ch'den çık-gir isteği
        self._yeniden_gir_at = 0.0
        self._son_hareket = 0.0
        self._durdu_bildir = False
        self._son_denetim = 0.0
        # Tarama: kanal -> {"zaman", "saat", "vidler", "metinler"}
        self.kanal_durumu = {}
        self.pong_sayisi = 0
        self.zaman_sayisi = 0
        self._kilit = threading.Lock()
        self._b = None
        self._secim = 0.0
        self._giris = 0.0         # oyuna girildiği an (0 = henüz değil)
        self._faz4 = 0.0
        self._son_pong = 0.0
        self._sira = 0
        self._gecis = False       # kanal değişim geri sayımı: varlıkları sayma

    # -- yardımcılar --
    def bildir(self, seviye, metin):
        try:
            self._bildir(self.kanal, seviye, metin)
        except Exception:                               # noqa: BLE001
            pass

    def _ayikla_fn(self):
        if not self._ayikla:
            return None
        return lambda metin: self.bildir("paket", metin)

    def _uyu(self, sn):
        bitis = time.time() + max(0.0, sn)
        while self.calisiyor:
            kalan = bitis - time.time()
            if kalan <= 0:
                break
            time.sleep(min(0.2, kalan))

    def durdur(self):
        self.calisiyor = False
        b = self._b
        if b is not None:
            b.kapat()

    def _mesafe_m(self, m):
        if not self.konum:
            return None
        return round(math.hypot(m["x"] - self.konum[0], m["y"] - self.konum[1]) / 100.0, 1)

    def harita_verisi(self):
        """
        Kanalın etrafındaki varlıklar — panel radar penceresi için.

        Karakter (konum) merkez; metin/oyuncu/canavar/npc ham koordinatlarıyla.
        Kendi karakterimiz (konumla aynı yerdeki oyuncu) elenir.
        """
        with self._kilit:
            konum = tuple(self.konum) if self.konum else None
            metinler = [{"x": m["x"], "y": m["y"], "ad": m.get("ad", "metin"),
                         "mesafe_m": self._mesafe_m(m),
                         "kesiliyor": bool(m.get("kesiliyor")),
                         "oyuncu": m.get("oyuncu")}
                        for m in self.metinler.values()]
            oyuncular, canavarlar, npcler = [], [], []
            for vid, (tip, vnum, x, y) in self.varliklar.items():
                if konum and (x, y) == konum:
                    continue
                if tip == TIP_OYUNCU:
                    oyuncular.append({"x": x, "y": y, "ad": self.ag_adlari.get(vid)})
                elif tip == 0:
                    canavarlar.append({"x": x, "y": y})
                elif tip == 1:
                    npcler.append({"x": x, "y": y})
        return {"kanal": self.kanal, "oyunda": self.oyunda, "durum": self.durum,
                "konum": list(konum) if konum else None, "metinler": metinler,
                "oyuncular": oyuncular, "canavarlar": canavarlar, "npcler": npcler}

    def _oyuncu_listesi(self):
        """Haritada görünen oyuncular (kendi karakterimiz elenir), yakından uzağa."""
        oyuncular = []
        for vid, (tip, vnum, x, y) in self.varliklar.items():
            if tip != TIP_OYUNCU:
                continue
            if self.konum and (x, y) == tuple(self.konum):
                continue
            oyuncular.append({"vid": vid, "ad": self._oyuncu_adi(vid),
                              "mesafe_m": self._mesafe_m({"x": x, "y": y})})
        oyuncular.sort(key=lambda o: (o["mesafe_m"] is None, o["mesafe_m"] or 0))
        return oyuncular

    def ozet(self):
        with self._kilit:
            metinler = [dict(m, mesafe_m=self._mesafe_m(m)) for m in self.metinler.values()]
            varliklar = list(self.varliklar.items())
            kanal_durumu = dict(self.kanal_durumu)
            oyuncular = self._oyuncu_listesi()
        sayim = {}
        tum_metinler = []
        for vid, (tip, vnum, x, y) in varliklar:
            ad = TIP_ADLARI.get(tip, "tip %d" % tip)
            sayim[ad] = sayim.get(ad, 0) + 1
            if tip == TIP_METIN:
                tum_metinler.append({"vid": vid, "vnum": vnum,
                                     "ad": self.adlar.get(vnum, "metin %d" % vnum),
                                     "x": x, "y": y,
                                     "mesafe_m": self._mesafe_m({"x": x, "y": y})})
        tum_metinler.sort(key=lambda m: (m["mesafe_m"] is None, m["mesafe_m"] or 0))
        # Ölüm / konum sapması (panel ve web net göstersin).
        sapma_ham = None
        sapma_m = None
        if self.yer and self.kendi_konum:
            sapma_ham = math.hypot(self.kendi_konum[0] - self.yer[0],
                                   self.kendi_konum[1] - self.yer[1])
            sapma_m = round(sapma_ham / 100.0, 1)
        # "yerinde": canlı konum yok (hiç kıpırdamadık) ya da eşik içindeysek.
        yerinde = (sapma_ham is None or sapma_ham <= self.yerine_esik)
        # "dönüyor": SADECE botun gerçekten yürüdüğü aralıkta (eşik..azami).
        # Daha uzağı (ör. 10843 m) ışınlanma/duvar/hatalı vid sayılır; bot
        # dokunmaz, o yüzden "dönüyor" da demeyiz.
        donuyor = bool(self.yerine_don and sapma_ham is not None
                       and self.yerine_esik < sapma_ham <= self.yerine_azami)
        ozet = {"kanal": self.kanal, "durum": self.durum, "oyunda": self.oyunda,
                "oturum": self.oturum, "metinler": metinler, "oyuncular": oyuncular,
                "konum": list(self.konum) if self.konum else None,
                "son_kirilma": self.son_kirilma or None, "rol": self.rol,
                "oldu": bool(self._oldu),
                "canlan_acik": bool(self.olunce_canlan or self.olunce_yeniden_gir),
                "don_acik": bool(self.yerine_don), "sapma_m": sapma_m,
                "yerinde": yerinde, "donuyor": donuyor,
                "kendi_vid": self.kendi_vid or None,
                "kendi_ad": self.ag_adlari.get(self.kendi_vid) if self.kendi_vid else None,
                "gorulen": sayim, "yakin_metinler": tum_metinler[:10]}
        if self.tarama:
            simdi = time.time()
            ozet["tarama"] = {str(k): {"son_bakis": v["saat"],
                                       "yas_sn": int(simdi - v["zaman"]),
                                       "metinler": v["metinler"],
                                       "oyuncular": v.get("oyuncular", [])}
                              for k, v in sorted(kanal_durumu.items())}
            ozet["tur"] = self.tur_sayisi
        return ozet

    # -- giriş fazı --
    def _zaman_cevapla(self, b, baslik, pkt):
        hs, t, delta = struct.unpack_from("<IIi", pkt, 1)
        if b.hs is None:
            b.hs = hs
        b.gonder(paket_zaman_cevabi(baslik, hs, t, delta),
                 "el sıkışma" if baslik == H_HANDSHAKE else "zaman eşle")
        if baslik == H_TIME_SYNC:
            self.zaman_sayisi += 1

    def _pong(self, b):
        simdi = time.time()
        if simdi - self._son_pong >= 1.0:
            self._son_pong = simdi
            b.gonder(paket_pong(), "pong")
            self.pong_sayisi += 1

    def _giris_gecerli_mi(self, b, i):
        """Giriş fazında d[i] geçerli bir paket başı mı? (True/False/None=eksik)"""
        d = b.tampon
        h = d[i]
        boy = GIRIS_BOYLARI.get(h)
        if boy is None:
            return False
        if len(d) - i < boy:
            return None
        if h == H_PHASE:
            return d[i + 1] <= 10
        if h in (H_HANDSHAKE, H_TIME_SYNC):
            return b.hs is None or _u32(d, i + 1) == b.hs
        if h == H_AUTH_SUCCESS:
            return d[i + 5] in (0, 1)
        if h == H_LOGIN_FAILURE:
            return 65 <= d[i + 1] <= 90
        if h == H_LOGIN_SUCCESS:
            return karakter_bilgisi(bytes(d[i:i + boy]), 0, self.ip_bayt) is not None \
                or _u32(d, i + 1) == 0
        return True

    def _giris_bekle(self, b, istenen, sure):
        """
        Giriş fazında paket okur; el sıkışma/zaman/ping kendiliğinden cevaplanır.

        istenen: başlık kümesi ya da ("faz", N) / ("faz", (N, M)).
        Döner: (başlık, paket).
        """
        fazlar = ()
        if isinstance(istenen, tuple):
            fazlar = istenen[1] if isinstance(istenen[1], tuple) else (istenen[1],)
            if b.faz in fazlar:
                return H_PHASE, bytes([H_PHASE, b.faz])
        bitis = time.time() + sure
        bilinmeyen = []
        while True:
            while b.tampon:
                gecerli = self._giris_gecerli_mi(b, 0)
                if gecerli is None:
                    break
                if not gecerli:
                    # Tanınmayan paket: bir sonraki geçerli başa kadar at.
                    bilinmeyen.append("0x%02x" % b.tampon[0])
                    i = 1
                    while i < len(b.tampon) and self._giris_gecerli_mi(b, i) is False:
                        i += 1
                    del b.tampon[:i]
                    continue
                h = b.tampon[0]
                boy = GIRIS_BOYLARI[h]
                pkt = bytes(b.tampon[:boy])
                del b.tampon[:boy]
                if h in (H_HANDSHAKE, H_TIME_SYNC):
                    self._zaman_cevapla(b, h, pkt)
                elif h == H_PHASE:
                    b.faz = pkt[1]
                    if pkt[1] in fazlar:
                        return h, pkt
                elif h == H_PING:
                    self._pong(b)
                elif h == H_LOGIN_FAILURE:
                    kod = pkt[1:10].split(b"\x00")[0].decode("ascii", "replace")
                    aciklama, bekle = GIRIS_HATALARI.get(kod, ("giriş reddedildi", 300))
                    raise GirisHatasi("%s (%s)" % (aciklama, kod), bekle)
                if isinstance(istenen, set) and h in istenen:
                    return h, pkt
            kalan = bitis - time.time()
            if kalan <= 0:
                ek = ("; tanınmayan: " + ", ".join(bilinmeyen[-6:])) if bilinmeyen else ""
                raise TimeoutError("sunucu beklenen cevabı vermedi (port %d, faz %d%s)"
                                   % (b.port, b.faz, ek))
            b.al(min(1.0, kalan))

    def _baglan(self, port):
        b = Baglanti(self.host, port, self.sure, self._ayikla_fn())
        self._b = b
        return b

    def _auth(self):
        portlar = [int(p) for p in self.ayar.get("giris_portlari", VARSAYILAN["giris_portlari"])]
        random.shuffle(portlar)
        son_hata = None
        for port in portlar:
            try:
                b = self._baglan(port)
            except OSError as e:
                son_hata = e
                continue
            try:
                self.durum = "giriş sunucusu (%d)" % port
                self._giris_bekle(b, ("faz", (FAZ_AUTH, FAZ_LOGIN)), self.sure)
                b.gonder(paket_login3(self._kullanici, self._sifre, self._pin), "LOGIN3")
                _, pkt = self._giris_bekle(b, {H_AUTH_SUCCESS}, self.sure)
                anahtar, sonuc = struct.unpack_from("<IB", pkt, 1)
                if sonuc != 1 or not anahtar:
                    raise GirisHatasi("giriş reddedildi (sonuç %d)" % sonuc, 300)
                return anahtar
            except OSError as e:
                son_hata = e
            finally:
                b.kapat()
        raise ConnectionError("giriş sunucusuna ulaşılamadı: %s" % son_hata)

    def _karakter_listesi(self, b, anahtar):
        self._giris_bekle(b, ("faz", FAZ_LOGIN), self.sure)
        b.gonder(paket_login2(self._kullanici, anahtar, self._pin), "LOGIN2")
        _, pkt = self._giris_bekle(b, {H_LOGIN_SUCCESS}, self.sure)
        bilgi = karakter_bilgisi(pkt, self.yuva, self.ip_bayt)
        if bilgi is None:
            raise GirisHatasi("karakter yuvası %d boş" % self.yuva, 3600)
        return bilgi

    def _portlar(self, kanal):
        """(giriş portu, harita portu): ayar > formül; sabit hesapta hesap ayarı öncelikli."""
        ozel = (self.ayar.get("kanal_portlari") or {}).get(str(kanal)) or []
        giris = ozel[0] if len(ozel) > 0 and ozel[0] else kanal_giris_portu(kanal)
        harita = ozel[1] if len(ozel) > 1 and ozel[1] else kanal_harita_portu(kanal)
        if not self.tarama:
            giris = self._giris_portu or giris
            harita = self._harita_portu or harita
        return int(giris), int(harita)

    def _kanala_gir(self, anahtar, kanal, gecis=False):
        """
        Kanala girip karakter listesini alır. Döner: harita sunucusu bağlantısı.

        gecis=True (kanal değiştirme): gerçek istemci gibi önce doğrudan harita
        sunucusuna bağlanır; ilk girişte önce kanalın giriş sunucusuna.
        """
        giris, harita = self._portlar(kanal)
        portlar = []
        for p in ((harita, giris) if gecis else (giris, harita)):
            if p not in portlar:
                portlar.append(p)
        son_hata = None
        for port in portlar:
            try:
                b = self._baglan(port)
            except OSError as e:
                son_hata = e
                continue
            try:
                self.durum = "ch%d girişi (%d)" % (kanal, port)
                x, y, hport = self._karakter_listesi(b, anahtar)
                if hport and hport != port:
                    b.kapat()
                    self.durum = "ch%d harita sunucusu (%d)" % (kanal, hport)
                    b = self._baglan(hport)
                    x, y, _ = self._karakter_listesi(b, anahtar)
                self.konum = (x, y)
                return b
            except OSError as e:
                son_hata = e
                b.kapat()
            except GirisHatasi:
                b.kapat()
                raise
        raise ConnectionError("ch%d sunucusuna girilemedi: %s" % (kanal, son_hata))

    # -- oyun fazı --
    def _aranan_mi(self, tip, vnum):
        if tip != TIP_METIN or vnum <= 0:
            return False
        return self.tum_metinler or vnum in self.vnumlar

    def _olay(self, olay, m, aralik=None):
        mesafe = m.get("mesafe_m") if "mesafe_m" in m else self._mesafe_m(m)
        kayit = {"t": round(time.time(), 1), "saat": time.strftime("%H:%M:%S"),
                 "kanal": self.kanal, "olay": olay, "vid": m["vid"], "vnum": m["vnum"],
                 "ad": m["ad"], "x": m["x"], "y": m["y"], "mesafe_m": mesafe}
        if aralik:
            kayit["aralik"] = aralik
        ek = ""
        if olay == "cikti" and m.get("dogma_dk") is not None:
            # Kırıldıktan sonra kaç dakikada yeniden çıktı (kanalda beklerken ölçüldü)
            kayit["dogma_dk"] = m["dogma_dk"]
            ek = "  — %.1f dk sonra çıktı" % m["dogma_dk"]
        if olay in ("kesiliyor", "kesildi", "birakti") and m.get("vuran"):
            kayit["vuran"] = m["vuran"]
            kayit["vuran_mesafe_m"] = m.get("vuran_mesafe_m")
            ek = "  — %s: %s%s" % (
                "kesen" if olay == "kesildi" else "vuran", m["vuran"],
                "  (%.0f m)" % m["vuran_mesafe_m"] if m.get("vuran_mesafe_m") is not None else "")
        elif olay == "yaninda":
            kayit["oyuncu"] = m.get("yakin_oyuncu")
            kayit["oyuncu_mesafe_m"] = m.get("yakin_mesafe_m")
            ek = "  — oyuncu: %s (%.0f m)" % (m.get("yakin_oyuncu"), m.get("yakin_mesafe_m") or 0)
        olay_yaz(kayit)
        self.bildir(olay, "%s%s%s%s" % (
            m["ad"], "  (%.0f m)" % mesafe if mesafe is not None else "", ek,
            "  [arada: %s - %s]" % tuple(aralik) if aralik else ""))

    def _mesaj(self, b, d, i, boy):
        h = d[i]
        if h == 0x01:
            if self._gecis:
                return
            vid, tip, vnum = _i32(d, i + 1), d[i + 21], _u16(d, i + 22)
            x0, y0 = _i32(d, i + 9), _i32(d, i + 13)
            with self._kilit:
                self.varliklar[vid] = (tip, vnum, x0, y0)
            # KENDİ VID: spawn konumumuzdaki oyuncu biziz. 0x11 bazen yanlış
            # vid veriyordu (10843 m sapması bundandı) — konum eşleşmesi kesin.
            if (tip == TIP_OYUNCU and not self._kendi_vid_kesin and self.konum
                    and (x0, y0) == tuple(self.konum)):
                self.kendi_vid = vid
                self.kendi_konum = (x0, y0)
                self._kendi_vid_kesin = True
                ad_ben = self.ag_adlari.get(vid)
                self.bildir("bilgi", "kendi karakterim: %s (vid %d — konumdan)"
                            % (ad_ben or "adı bekleniyor", vid))
            if not self._aranan_mi(tip, vnum):
                return
            m = {"vid": vid, "vnum": vnum, "ad": self.adlar.get(vnum, "metin %d" % vnum),
                 "x": _i32(d, i + 9), "y": _i32(d, i + 13), "gorulme": round(time.time(), 1)}
            with self._kilit:
                yeni = vid not in self.metinler
                self.metinler[vid] = m
            if yeni and not self.tarama:
                # Oyuna girişte sunucu çevredeki her şeyi yollar: bunlar yeni
                # çıkmış değil, zaten oradaydı. Pencere GİRİŞ anından sayılır
                # (yükleme birkaç sn sürebilir).
                ilk = not self._giris or time.time() - self._giris < self.ilk_pencere
                if not ilk and self.son_kirilma:
                    # Bu kanalda önce bir metin kırılmıştı: yeniden doğma süresi.
                    m["dogma_dk"] = round((time.time() - self.son_kirilma) / 60.0, 1)
                self._olay("ilk" if ilk else "cikti", m)
        elif h == 0x02:
            if self._gecis:
                return
            vid02 = _i32(d, i + 1)
            with self._kilit:
                self.varliklar.pop(vid02, None)
                m = self.metinler.pop(vid02, None)
            if m is not None:
                # İzleyici ve metin yerinden oynamaz: kaybolan metin kırılmıştır.
                self._kesildi_bildir(m)
            elif self._kendi_mi(vid02):
                self._olum_sinyali("0x02 (kaldırıldı)", d, i, boy)
        elif h in (0x0D, 0x0E):                         # ölüm animasyonu
            if self._gecis:
                return
            vid0d = _i32(d, i + 1)
            with self._kilit:
                m = self.metinler.pop(vid0d, None)
            if m is not None:
                self._kesildi_bildir(m)
            elif self._kendi_mi(vid0d):
                self._olum_sinyali("0x%02x (ölüm animasyonu)" % h, d, i, boy)
        elif h == 0x3E:                                 # saldıran | hedef
            if self._gecis:
                return
            self._vurus(_i32(d, i + 1), _i32(d, i + 5))
        elif h == H_KENDI_DURUM:                        # 0x11 hep kendi vid
            if not self._kendi_vid_kesin:               # konumdan bulunduysa dokunma
                self.kendi_vid = _i32(d, i + 1)
        elif h == 0x03:                                 # varlık hareketi
            if self._gecis:
                return
            vid = _i32(d, i + 4)
            x, y = _i32(d, i + 8), _i32(d, i + 12)
            if vid == self.kendi_vid:
                self.kendi_konum = (x, y)
            with self._kilit:
                v = self.varliklar.get(vid)
                if v is not None:
                    self.varliklar[vid] = (v[0], v[1], x, y)
        elif h == 0x05:                                 # toplu konum
            if self._gecis:
                return
            with self._kilit:
                for k in range(i + 3, i + boy, 12):
                    vid = _i32(d, k)
                    x, y = _i32(d, k + 4), _i32(d, k + 8)
                    if vid == self.kendi_vid:
                        self.kendi_konum = (x, y)
                    v = self.varliklar.get(vid)
                    if v is not None:
                        self.varliklar[vid] = (v[0], v[1], x, y)
        elif h == H_OLUM:                               # 46 | bayrak | kurban(4) | öldüren(4)
            # Çevredeki HER ölümde gelir (çoğu canavar). Kurban == kendi vid
            # ise BİZ öldük. Yalnız konumdan kilitli kendi_vid'e güven.
            if self._kendi_mi(_u32(d, i + 2)):
                self._oldum()
        elif h == 0x88:                                 # varlık adı
            ad = bytes(d[i + 5:i + 30]).split(b"\x00")[0].decode("utf-8", "replace")
            if ad:
                self.ag_adlari[_i32(d, i + 1)] = ad
        elif h in (H_HANDSHAKE, H_TIME_SYNC):
            self._zaman_cevapla(b, h, bytes(d[i:i + 13]))
        elif h == H_PING:
            self._pong(b)
        elif h == H_PHASE:
            b.faz = d[i + 1]
            if b.faz == FAZ_LOADING and not self._faz4:
                self._faz4 = time.time()

    def _oyuncu_adi(self, vid):
        return self.ag_adlari.get(vid) or "oyuncu #%d" % vid

    def _vurus(self, saldiran, hedef):
        """0x3E: hedef izlenen bir metinse KESİLİYOR (ilk vuruşta bildirilir)."""
        with self._kilit:
            m = self.metinler.get(hedef)
            if m is None:
                return
            s = self.varliklar.get(saldiran)
            m["son_vurus"] = time.time()
            m["vuran"] = self._oyuncu_adi(saldiran)
            m["vuran_mesafe_m"] = (round(math.hypot(s[2] - m["x"], s[3] - m["y"]) / 100.0, 1)
                                   if s else None)
            basladi = not m.get("kesiliyor")
            m["kesiliyor"] = True
        if basladi:
            self._olay("kesiliyor", m)

    def _kesildi_bildir(self, m):
        """Metin gitti: son vuruş yakın zamandaysa vuranı, yoksa yanındakini yaz."""
        if not (m.get("son_vurus") and time.time() - m["son_vurus"] <= self.kesme_bitis + 5):
            if m.get("yaninda"):
                m["vuran"] = m.get("yakin_oyuncu")
                m["vuran_mesafe_m"] = m.get("yakin_mesafe_m")
            else:
                m.pop("vuran", None)
        # Bir sonraki metnin yeniden doğma süresini ölçmek için an'ı sakla.
        self.son_kirilma = time.time()
        self._olay("kesildi", m)

    def _kesme_denetle(self):
        """Saniyede bir: 4 m içindeki oyuncular (YANINDA) ve vuruşu kesilenler (BIRAKTI)."""
        simdi = time.time()
        if simdi - self._son_denetim < 1.0:
            return
        self._son_denetim = simdi
        bildirilecek = []
        with self._kilit:
            oyuncular = [(vid, v) for vid, v in self.varliklar.items()
                         if v[0] == TIP_OYUNCU
                         and not (self.konum and (v[2], v[3]) == tuple(self.konum))]
            for m in self.metinler.values():
                sirali = sorted((math.hypot(v[2] - m["x"], v[3] - m["y"]), vid)
                                for vid, v in oyuncular)
                # GÖSTERİM: metnin 4 m içindeki en yakın oyuncu — "metin var +
                # oyuncu var" tek satırda görünsün (YANINDA'daki 3 sn beklemesiz).
                gorunur = [(uz, vid) for uz, vid in sirali if uz <= GORUNUR_OYUNCU_HAM]
                if gorunur:
                    m["oyuncu"] = self._oyuncu_adi(gorunur[0][1])
                    m["oyuncu_mesafe_m"] = round(gorunur[0][0] / 100.0, 1)
                else:
                    m.pop("oyuncu", None)
                    m.pop("oyuncu_mesafe_m", None)
                # OLAY: 4 m içinde 3 sn duran oyuncu -> YANINDA bildirimi.
                yakin = [(uz, vid) for uz, vid in sirali if uz <= YAKIN_HAM]
                if yakin:
                    if not m.get("yakin_ilk"):
                        m["yakin_ilk"] = simdi
                    m["yakin_son"] = simdi
                    m["yakin_oyuncu"] = self._oyuncu_adi(yakin[0][1])
                    m["yakin_mesafe_m"] = round(yakin[0][0] / 100.0, 1)
                    if (not m.get("yaninda") and not m.get("kesiliyor")
                            and simdi - m["yakin_ilk"] >= self.yakin_sure):
                        m["yaninda"] = True
                        bildirilecek.append(("yaninda", m))
                elif m.get("yakin_ilk") and simdi - m.get("yakin_son", 0) > 10:
                    m["yakin_ilk"] = 0
                    m["yaninda"] = False
                if m.get("kesiliyor") and simdi - m.get("son_vurus", 0) > self.kesme_bitis:
                    m["kesiliyor"] = False
                    bildirilecek.append(("birakti", m))
        for olay, m in bildirilecek:
            self._olay(olay, m)

    # -- ölünce canlanma / yerine dönme (paket gönderir) --
    def _paket_gonder(self, veri, ad):
        b = self._b
        if b is not None:
            b.gonder(veri, ad)
            return True
        return False

    def _kendi_mi(self, vid):
        """vid bizim karakterimiz mi? YALNIZ konumdan kilitlenmişse güven —
        0x11 yedeği bazen vid=4 gibi çöp veriyor, yanlış ölüm tetikliyordu."""
        return bool(self._kendi_vid_kesin and self.kendi_vid and vid == self.kendi_vid)

    def _olum_sinyali(self, kaynak, d, i, boy):
        """Kendi vid'imizle gelen ölüm işareti (0x02/0x0D/0x0E). Az gürültü:
        yalnız kendi vid için, ölüm başına bir kez."""
        if not self._oldu:
            self.bildir("bilgi", "kendi vid ölüm sinyali: %s  ham: %s"
                        % (kaynak, bytes(d[i:i + min(boy, 16)]).hex(" ")))
        self._oldum()

    def _oldum(self):
        if self._oldu:
            return
        self._oldu = True
        if self.olunce_yeniden_gir and not self.tarama:
            # Kanaldan çıkıp aynı kanala tekrar gir: yeniden girişte karakter
            # zaten canlı gelir (kullanıcının ölçtüğü davranış).
            self._yeniden_gir_at = time.time() + self.yeniden_gir_gecikme
            self.bildir("oldu", "ÖLDÜN — %.1f sn sonra ch%d'den çıkıp tekrar girilecek"
                        % (self.yeniden_gir_gecikme, self.kanal))
        elif self.olunce_canlan:
            self._canlan_at = time.time() + self.canlan_gecikme
            self.bildir("oldu", "ÖLDÜN — %.1f sn sonra '%s' ile yerinde canlanılıyor"
                        % (self.canlan_gecikme, self.canlan_komut))
        else:
            self.bildir("oldu", "ÖLDÜN (canlanma kapalı)")

    def _canlanma_denetle(self):
        """Ölüm sonrası zamanı gelince canlanma komutunu gönderir."""
        if self._canlan_at and time.time() >= self._canlan_at:
            self._canlan_at = 0.0
            if self._paket_gonder(paket_sohbet(self.canlan_komut), "canlan"):
                self.bildir("bilgi", "canlanma komutu gönderildi (%s)" % self.canlan_komut)
            self._oldu = False        # canlanınca konum güncellenince yerine döner

    def _yerine_don_denetle(self):
        """
        Kısa mesafede park noktasına döndürür (paket gönderir).

        Yalnızca esik..azami arasında; daha uzaksa (ölüm/ışınlanma/duvar)
        dokunmaz. Duvar/yol bulma yok — açık alanda birkaç metrelik kayma için.
        """
        if not (self.yerine_don and self.yer and self.kendi_konum) or self._oldu:
            return
        simdi = time.time()
        if simdi - self._son_hareket < self.hareket_araligi:
            return
        cx, cy = self.kendi_konum
        hx, hy = self.yer
        uzak = math.hypot(hx - cx, hy - cy)
        if uzak <= self.yerine_esik:
            if not self._durdu_bildir:
                self._durdu_bildir = True
                self._son_hareket = simdi
                self._paket_gonder(paket_hareket(FUNC_DUR, 0, cx, cy, _tik()), "dur")
            return
        self._durdu_bildir = False
        if uzak > self.yerine_azami:
            return                     # çok uzak: yürütme (duvara toslar / ölmüş)
        self._son_hareket = simdi
        rot = yon_rot(hx - cx, hy - cy)
        self._paket_gonder(paket_hareket(FUNC_YURU, rot, hx, hy, _tik()), "yerine dön")

    # -- buff'çı (paket gönderir): hedefi seç + yetenekleri bas --
    def kanala_cek(self, kanal):
        """Panelden 'bu kanala geç' isteği (buff'çı canlı kanal değiştirir)."""
        try:
            k = int(kanal)
        except (TypeError, ValueError):
            return
        if 1 <= k <= 8:
            self.istek_kanal = k

    def _buff_hedef_bul(self):
        """buff_hedef adlı, menzil içindeki oyuncunun (vid, ham_mesafe)'si."""
        konum = self.kendi_konum or (tuple(self.konum) if self.konum else None)
        if not konum:
            return None
        en_yakin = None
        with self._kilit:
            for vid, (tip, vnum, x, y) in self.varliklar.items():
                if tip != TIP_OYUNCU:
                    continue
                if ad_fold(self.ag_adlari.get(vid)) != self.buff_hedef:
                    continue
                uz = math.hypot(x - konum[0], y - konum[1])
                if uz <= self.buff_menzil and (en_yakin is None or uz < en_yakin[1]):
                    en_yakin = (vid, uz)
        return en_yakin

    def _buff_sirayi_isle(self):
        """Zamanı gelen gecikmeli yetenekleri sırayla basar (animasyon için aralıklı)."""
        if not self._buff_sira:
            return
        simdi = time.time()
        while self._buff_sira and self._buff_sira[0][0] <= simdi:
            _, vnum, vid = self._buff_sira.pop(0)
            if self._paket_gonder(paket_yetenek(vnum, vid), "yetenek %d" % vnum):
                # Gerçek istemci her yetenekten sonra "dur" (CG_MOVE func=0)
                # gönderiyor (kayıtta doğrulandı) — animasyon oturması için taklit et.
                konum = self.kendi_konum or (tuple(self.konum) if self.konum else None)
                if konum:
                    self._paket_gonder(paket_hareket(FUNC_DUR, 0, konum[0], konum[1], _tik()),
                                       "yetenek sonrası dur")
                self.bildir("buff", "yetenek %d basıldı (hedef vid %d)" % (vnum, vid))

    def _buff_denetle(self):
        """buff_hedef menzile girince onu seçip yetenekleri ARALIKLA basar."""
        if self.rol != "buff":
            return
        self._buff_sirayi_isle()                 # önce bekleyen yetenekler
        if not (self.buff_acik and self.buff_hedef and self.buff_vnumlar and self.oyunda):
            return
        if self._buff_sira:
            return                               # bir dizi sürüyor, yeni tetikleme yok
        bulunan = self._buff_hedef_bul()
        if bulunan is None:
            return
        vid, uz = bulunan
        simdi = time.time()
        if simdi - self._son_buff.get(vid, 0.0) < self.buff_aralik:
            return
        self._son_buff[vid] = simdi
        # eski girdileri temizle (menzilden çıkanlar birikmesin)
        for eski in [v for v, t in self._son_buff.items()
                     if simdi - t > self.buff_aralik * 4]:
            self._son_buff.pop(eski, None)
        # Hedefi bir kez seç; yetenekleri gecikmeyle sıraya diz (ilki hemen).
        self._paket_gonder(paket_hedef(vid), "hedef seç")
        self._buff_sira = [(simdi + n * self.buff_skill_gecikme, vnum, vid)
                           for n, vnum in enumerate(self.buff_vnumlar)]
        self.bildir("buff", "%s (%.1f m) seçildi — %d yetenek %.0f sn arayla basılacak"
                    % (self._oyuncu_adi(vid), uz / 100.0,
                       len(self.buff_vnumlar), self.buff_skill_gecikme))
        self._buff_sirayi_isle()                 # ilk yeteneği hemen gönder

    def _akisi_isle(self, b):
        d = b.tampon
        i = 0
        while i < len(d):
            boy = oyun_mesaj_boyu(d, i, b.hs)
            if boy < 0:
                break
            if boy == 0:
                i += 1
                continue
            self._mesaj(b, d, i, boy)
            i += boy
        del d[:i]
        if len(d) > 65536:
            del d[:len(d) - 65536]

    def _oyna(self, b, sure=None):
        """Karakteri seçip oyuna girer; sure verilirse girişten o kadar sn sonra döner."""
        b.tampon.clear()
        with self._kilit:
            self.metinler.clear()
            self.varliklar.clear()
            self.ag_adlari.clear()
        self._gecis = False
        self._oldu = False
        self._canlan_at = 0.0
        self._yeniden_gir = False
        self._yeniden_gir_at = 0.0
        self._durdu_bildir = False
        self.kendi_konum = None
        self._kendi_vid_kesin = False   # yeni girişte kendi vid'i yeniden doğrula
        # Park noktası: girişteki konum (kullanıcı karakteri buraya bıraktı).
        # Sabit modda ilk oturumda sabitlenir; sonraki oturumlarda korunur.
        if self.yer is None and self.konum and not self.tarama:
            self.yer = tuple(self.konum)
        b.gonder(paket_karakter_sec(self.yuva), "karakter seç")
        self.durum = "ch%d yükleniyor" % self.kanal
        self._secim = time.time()
        self._faz4 = 0.0
        self._giris = 0.0
        girildi = False
        son_veri = time.time()
        while self.calisiyor:
            if not girildi:
                simdi = time.time()
                if ((self._faz4 and simdi - self._faz4 >= self.giris_gecikme)
                        or simdi - self._secim >= self.giris_bekle):
                    b.gonder(paket_oyuna_gir(), "oyuna gir")
                    girildi = True
                    self._giris = time.time()
                    self.oyunda = True
                    self.durum = "oyunda" if not self.tarama else "ch%d bakılıyor" % self.kanal
                    if not self.tarama:
                        self.bildir("bilgi", "oyuna girildi")
            elif sure is not None and time.time() - self._giris >= sure:
                return
            elif (girildi and self._yeniden_gir_at
                    and time.time() >= self._yeniden_gir_at):
                self._yeniden_gir_at = 0.0
                self._yeniden_gir = True   # öldük: run() ch'den çıkıp tekrar girsin
                return
            elif (girildi and self.istek_kanal is not None
                    and self.istek_kanal != self.kanal):
                return                    # panelden başka kanala çekme isteği
            # buff'çı hızlı tepki versin: veri geldikçe kısa, boşta düşük bekleme
            bekle = 0.05 if self.rol == "buff" else 0.5
            if b.al(bekle):
                son_veri = time.time()
            elif time.time() - son_veri > self.sessizlik:
                raise ConnectionError("%d sn veri gelmedi" % self.sessizlik)
            self._akisi_isle(b)
            self._kesme_denetle()
            self._canlanma_denetle()
            self._yerine_don_denetle()
            self._buff_denetle()

    # -- tarama --
    def _ziyaret_kaydet(self, kanal):
        """Kanalda görülenleri kaydeder; önceki ziyaretle karşılaştırır."""
        simdi = time.time()
        saat = time.strftime("%H:%M:%S")
        with self._kilit:
            mevcut = {vid: dict(m, mesafe_m=self._mesafe_m(m))
                      for vid, m in self.metinler.items()}
            oyuncular = self._oyuncu_listesi()
            onceki = self.kanal_durumu.get(kanal)
            self.kanal_durumu[kanal] = {"zaman": simdi, "saat": saat,
                                        "vidler": list(mevcut),
                                        "metinler": list(mevcut.values()),
                                        "oyuncular": oyuncular}
        if onceki is not None:
            aralik = [onceki["saat"], saat]
            for vid, m in mevcut.items():
                if vid not in onceki["vidler"]:
                    self._olay("cikti", m, aralik=aralik)
            for m in onceki["metinler"]:
                if m["vid"] not in mevcut:
                    self._olay("gitti", m, aralik=aralik)
        olay_yaz({"t": round(simdi, 1), "saat": saat, "kanal": kanal, "olay": "tarama",
                  "metin_sayisi": len(mevcut),
                  "metinler": [{"vid": m["vid"], "vnum": m["vnum"], "ad": m["ad"],
                                "x": m["x"], "y": m["y"], "mesafe_m": m["mesafe_m"]}
                               for m in mevcut.values()]})
        if mevcut:
            self.bildir("tarama_var", ", ".join(
                "%s%s" % (m["ad"], "  (%.0f m)" % m["mesafe_m"] if m["mesafe_m"] is not None else "")
                for m in mevcut.values()))
        else:
            self.bildir("tarama_yok", "metin yok")

    def _kanal_degistir(self, b, hedef):
        """
        Oyunun kanal menüsü gibi: /change_channel N, geri sayımı bekle, kapat.

        Sunucu bağlantıyı kapatmaz; gerçek istemci geri sayım bitince (~3,1 sn)
        kendisi kapatıp yeni kanala bağlanıyor. Sunucu erken kapatırsa beklemeden
        devam edilir. Döner: sunucu mu kapattı.
        """
        self._gecis = True
        self.oyunda = False
        self.durum = "ch%d -> ch%d geçiliyor" % (self.kanal, hedef)
        b.gonder(paket_sohbet("/change_channel %d" % hedef), "kanal değiştir")
        bitis = time.time() + self.degisim_bekle
        kapandi = False
        try:
            while self.calisiyor and time.time() < bitis:
                b.al(0.5)
                self._akisi_isle(b)       # ping/zaman cevapları sürsün
        except OSError:
            kapandi = True                # geri sayım bitti, sunucu kapattı
        b.kapat()
        self._b = None
        return kapandi

    def run(self):
        bekleme = self.taban
        while self.calisiyor:
            b = None
            try:
                self.durum = "giriş yapılıyor"
                anahtar = self._auth()
                if not self.calisiyor:
                    break
                kanal = self.tarama[self._sira] if self.tarama else self.kanal
                self.kanal = kanal
                b = self._kanala_gir(anahtar, kanal)
                bekleme = self.taban
                if len(self.tarama) <= 1:
                    while self.calisiyor:
                        self.oturum += 1
                        self._oyna(b)
                        # _oyna yalnız (a) durunca (b) kanal çekme (c) ölünce
                        # yeniden giriş isteğiyle döner; hata zaten dışarı fırlar.
                        if not self.calisiyor:
                            break
                        if self._yeniden_gir:
                            # ÖLDÜK: kanaldan çık, aynı kanala tekrar gir (canlanır).
                            self._yeniden_gir = False
                            self.bildir("bilgi", "ch%d: çıkılıp tekrar giriliyor (canlanma)"
                                        % self.kanal)
                            try:
                                self._kanal_degistir(b, self.kanal)
                            except OSError:
                                pass
                            b = None
                            b = self._kanala_gir(anahtar, self.kanal, gecis=True)
                            continue
                        hedef = self.istek_kanal
                        if hedef is None or hedef == self.kanal:
                            break
                        self.istek_kanal = None
                        self._kanal_degistir(b, hedef)
                        b = None
                        self.kanal = hedef
                        b = self._kanala_gir(anahtar, hedef, gecis=True)
                else:
                    while self.calisiyor:
                        self.oturum += 1
                        self._oyna(b, sure=self.bakis_sn)
                        if not self.calisiyor:
                            break
                        self._ziyaret_kaydet(kanal)
                        self._sira = (self._sira + 1) % len(self.tarama)
                        if self._sira == 0:
                            self.tur_sayisi += 1
                        hedef = self.tarama[self._sira]
                        self._kanal_degistir(b, hedef)
                        b = None
                        self.kanal = kanal = hedef
                        b = self._kanala_gir(anahtar, hedef, gecis=True)
            except GirisHatasi as e:
                self.durum = "giriş hatası: %s" % e
                self.bildir("hata", str(e))
                self._uyu(e.bekle * self.carpan)
                continue
            except Exception as e:                      # noqa: BLE001
                if self.calisiyor:
                    self.durum = "bağlantı yok: %s" % e
                    self.bildir("uyari", "bağlantı koptu: %s — %d sn sonra yeniden"
                                % (e, bekleme))
            finally:
                self.oyunda = False
                self._gecis = False
                if b is not None:
                    b.kapat()
                self._b = None
                with self._kilit:
                    self.metinler.clear()
                    self.varliklar.clear()
            self._uyu(bekleme)
            bekleme = min(self.tavan, bekleme * 2)
        self.durum = "durdu"


# ── HTTP durum ───────────────────────────────────────────────────

def durum_ozeti(izleyiciler):
    kanallar = {}
    buff_kanallari = {}          # kanal -> buff'çının durumu (kartı sahiplenmez)
    for z in izleyiciler:
        o = z.ozet()
        if o.get("rol") == "buff":
            buff_kanallari[z.kanal] = o.get("durum")
            continue
        if len(z.tarama) > 1:
            t = o.get("tarama") or {}
            for k in z.tarama:
                v = t.get(str(k))
                kanallar[str(k)] = {"kanal": k, "tarama": True,
                                    "simdi_burada": bool(o["oyunda"] and o["kanal"] == k),
                                    "durum": o["durum"],
                                    "son_bakis": v["son_bakis"] if v else None,
                                    "yas_sn": v["yas_sn"] if v else None,
                                    "metinler": v["metinler"] if v else [],
                                    "oyuncular": v.get("oyuncular", []) if v else []}
        else:
            kanallar[str(z.kanal)] = o
    # Buff'çı işareti: izleyicinin kartını EZMEDEN o kanala "buff burada" ekle.
    for k, durum in buff_kanallari.items():
        girdi = kanallar.get(str(k))
        if girdi is None:
            kanallar[str(k)] = {"kanal": k, "durum": durum, "oyunda": False,
                                "metinler": [], "oyuncular": [],
                                "buff": True, "buff_durum": durum}
        else:
            girdi["buff"] = True
            girdi["buff_durum"] = durum
    return {"zaman": round(time.time(), 1), "kanallar": kanallar}


def http_baslat(izleyiciler, port):
    class Isleyici(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/durum"):
                self.send_error(404)
                return
            govde = json.dumps(durum_ozeti(izleyiciler), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)

        def log_message(self, *a):
            pass

    sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", int(port)), Isleyici)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu


def ozet_satiri(izleyiciler):
    parcalar = []
    for z in sorted(izleyiciler, key=lambda z: z.kanal):
        o = z.ozet()
        if len(z.tarama) > 1:
            t = o.get("tarama") or {}
            ic = []
            for k in z.tarama:
                v = t.get(str(k))
                if v is None:
                    ic.append("ch%d ?" % k)
                else:
                    ic.append("ch%d %s" % (k, ("●%d" % len(v["metinler"])) if v["metinler"] else "○"))
            parcalar.append("tarama[tur %d] %s" % (o.get("tur", 0), " ".join(ic)))
        elif o["oyunda"]:
            parcalar.append("ch%d %s" % (z.kanal, ("● %d metin" % len(o["metinler"]))
                                         if o["metinler"] else "○ yok"))
        else:
            parcalar.append("ch%d … %s" % (z.kanal, o["durum"][:24]))
    return "   ".join(parcalar)


def teshis_satirlari(o):
    """--ayikla: karakterin konumu, çevrede görülenler, en yakın metinler."""
    satirlar = ["ch%d konum %s  görülen: %s" % (
        o["kanal"], o["konum"],
        ", ".join("%s %d" % kv for kv in sorted(o["gorulen"].items())) or "hiçbir şey")]
    for m in o["yakin_metinler"][:5]:
        satirlar.append("ch%d   metin vnum %d %s  %s" % (
            o["kanal"], m["vnum"], m["ad"],
            ("%.0f m" % m["mesafe_m"]) if m["mesafe_m"] is not None else "?"))
    return satirlar


# ── ayar ─────────────────────────────────────────────────────────

def ornek_ayar():
    a = dict(VARSAYILAN)
    a["hesaplar"] = [{"kanal": k, "kullanici": "", "sifre": "", "pin": "",
                      "karakter_yuvasi": 0}
                     for k in range(1, 9)]
    return a


def ayar_yukle(yol):
    """Ayarı okur; dosya yoksa örneğini yazar ve None döner."""
    if not os.path.exists(yol):
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(ornek_ayar(), f, ensure_ascii=False, indent=2)
        return None
    with open(yol, encoding="utf-8-sig") as f:
        veri = json.load(f)
    ayar = dict(VARSAYILAN)
    ayar.update(veri)
    # İlk sürümün yazdığı örnek dosyada 30004 de vardı (oyun sunucusu, cevap
    # vermez, her girişte 15 sn kaybettirir). Dosyaya dokunmadan düzelt:
    # içinde şifreler var.
    if [int(p) for p in ayar.get("giris_portlari") or []] == [30001, 30002, 30003, 30004]:
        ayar["giris_portlari"] = list(VARSAYILAN["giris_portlari"])
    return ayar


def _hesap_kanallari(h):
    tarama = h.get("tarama") or []
    try:
        return [int(k) for k in tarama] if tarama else [int(h.get("kanal", 0) or 0)]
    except (TypeError, ValueError):
        return [0]


def hesaplari_dogrula(hesaplar):
    hatalar = []
    kanallar = {}
    adlar = {}
    for h in hesaplar:
        liste = _hesap_kanallari(h)
        tarama = bool(h.get("tarama"))
        if not liste or any(not 1 <= k <= 8 for k in liste):
            hatalar.append("geçersiz kanal: %r" % (h.get("tarama") or h.get("kanal")))
            continue
        ada = int(h.get("ada", 1) or 1)
        etiket = (("%d. ada tarama %s" % (ada, ",".join(map(str, liste))))
                  if tarama else "%d. ada ch%d" % (ada, liste[0]))
        ad = (h.get("kullanici") or "").strip().lower()
        if ad in adlar:
            hatalar.append("aynı hesap %s ve %s'de — bir hesap aynı anda tek "
                           "yerde olabilir" % (adlar[ad], etiket))
        adlar[ad] = etiket
        # Buff'çı bir kanalı "işgal" etmez: izleyiciyle aynı kanalda durabilir.
        if not tarama and (h.get("rol") or "").lower() != "buff":
            # ADA ile birlikte anahtarla: 1. ada ch1 ile 2. ada ch1 ayrı kanaldır.
            anahtar = (ada, liste[0])
            if anahtar in kanallar:
                hatalar.append("%d. ada ch%d için birden fazla hesap var"
                               % (ada, liste[0]))
            kanallar[anahtar] = True
        if len((h.get("sifre") or "").encode("cp1254", "replace")) > 16:
            hatalar.append("%s: şifre 16 karakterden uzun — oyun alanına sığmaz" % etiket)
        if pin_coz(h.get("pin")) is None:
            hatalar.append("%s: PIN eksik ya da geçersiz (yalnızca rakam, "
                           "oyunda girdiğin giriş PIN'i)" % etiket)
    return hatalar


ETIKETLER = {"ilk": "VAR", "cikti": "ÇIKTI", "gitti": "GİTTİ", "hata": "HATA",
             "uyari": "UYARI", "bilgi": "bilgi", "paket": "paket",
             "tarama_var": "VAR", "tarama_yok": "yok",
             "kesiliyor": "KESİLİYOR", "kesildi": "KESİLDİ", "birakti": "BIRAKTI",
             "yaninda": "YANINDA", "oldu": "ÖLDÜ"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Görüntüsüz metin izleyici")
    ap.add_argument("--ayar", default=AYAR_DOSYASI)
    ap.add_argument("--kanal", type=int, action="append",
                    help="yalnızca bu kanalın hesabı (birden çok verilebilir)")
    ap.add_argument("--tarama",
                    help="seçilen hesap bu kanalları sırayla gezer: 1-8 ya da 1,3,5")
    ap.add_argument("--ayikla", action="store_true",
                    help="paket başlıklarını ve boylarını yaz (içerik yazılmaz)")
    a = ap.parse_args(argv)

    ayar = ayar_yukle(a.ayar)
    if ayar is None:
        print("Ayar dosyası oluşturuldu: %s" % a.ayar)
        print("Hesapları (kanal, kullanıcı, şifre, PIN, karakter yuvası) yazıp yeniden çalıştır.")
        return 2
    hesaplar = [h for h in ayar.get("hesaplar", [])
                if (h.get("kullanici") or "").strip() and h.get("sifre")]
    if a.kanal:
        hesaplar = [h for h in hesaplar if any(k in a.kanal for k in _hesap_kanallari(h))]
    if not hesaplar:
        print("%s içinde dolu hesap yok%s." % (os.path.basename(a.ayar),
                                              " (seçilen kanallarda)" if a.kanal else ""))
        return 2
    if a.tarama:
        try:
            liste = tarama_coz(a.tarama)
        except ValueError as e:
            print("TARAMA HATASI:", e)
            return 2
        if len(hesaplar) != 1:
            print("--tarama için tek bir hesap seç (ör. --kanal 1 --tarama 1-8).")
            return 2
        hesaplar = [dict(hesaplar[0], tarama=liste)]
    hatalar = hesaplari_dogrula(hesaplar)
    if hatalar:
        for hata in hatalar:
            print("AYAR HATASI:", hata)
        return 2

    adlar = katalog_yukle()
    kilit = threading.Lock()

    def bildir(kanal, seviye, metin):
        with kilit:
            print("%s  ch%d  %-6s %s" % (time.strftime("%H:%M:%S"), kanal,
                                         ETIKETLER.get(seviye, seviye), metin))

    izleyiciler = [Izleyici(h, ayar, adlar, bildir, ayikla=a.ayikla)
                   for h in sorted(hesaplar, key=lambda h: _hesap_kanallari(h)[0])]
    try:
        http_baslat(izleyiciler, ayar.get("http_portu", 30210))
        print("Durum: http://127.0.0.1:%s/durum" % ayar.get("http_portu", 30210))
    except OSError as e:
        print("HTTP durum sunucusu açılamadı: %s" % e)
    print("Olaylar: %s" % OLAY_DOSYASI)
    print("Durdurmak için Ctrl+C.\n")
    try:
        for i, z in enumerate(izleyiciler):
            if i:
                time.sleep(float(ayar.get("baslama_araligi_sn", 3)))
            z.start()
        while True:
            time.sleep(30)
            with kilit:
                print("%s  %s" % (time.strftime("%H:%M:%S"), ozet_satiri(izleyiciler)))
                if a.ayikla:
                    for z in izleyiciler:
                        for satir in teshis_satirlari(z.ozet()):
                            print("          " + satir)
    except KeyboardInterrupt:
        pass
    finally:
        for z in izleyiciler:
            z.durdur()
    return 0


if __name__ == "__main__":
    sys.exit(main())
