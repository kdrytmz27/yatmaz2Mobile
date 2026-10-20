# -*- coding: utf-8 -*-
"""
TELEGRAM BİLDİRİMİ — metin izleyici olaylarını Telegram botuyla telefona yollar.

KURULUM (2 dakika)
------------------
1) Telegram'da @BotFather'ı aç, /newbot yaz, bota bir ad ver.
   BotFather bir TOKEN verir:  123456789:AAH...
2) BotFather'ın verdiği bağlantıdan KENDİ botunu aç ve "Başlat"a bas
   (ya da herhangi bir mesaj yaz). Bot sana ancak bundan sonra yazabilir.
3) Metin İzleyici panelinde token'ı yapıştır, "Bul"a bas -> sohbet kimliği
   gelir. "Kaydet", sonra "Test mesajı".

Bot API: https://api.telegram.org/bot<TOKEN>/sendMessage  (resmî, ücretsiz)

GÜVENLİK
--------
Token botu yöneten anahtardır. Hata mesajlarına, günlüğe ve ekrana ASLA
yazılmaz; yalnızca metin_izleyici.json'da durur.
"""

import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org/bot%s/%s"
AZAMI_UZUNLUK = 4000          # Telegram sınırı 4096 karakter
_TOKEN_DESENI = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")

HATA_ACIKLAMALARI = {
    401: "token geçersiz — BotFather'ın verdiği token'ı kontrol et",
    404: "token geçersiz — BotFather'ın verdiği token'ı kontrol et",
    403: "bot sohbete yazamıyor — Telegram'da botunu açıp Başlat'a bas",
    409: "bot başka bir yerde (webhook) kullanılıyor — yeni bir bot aç",
    429: "çok sık mesaj — Telegram bekletiyor",
}


class TelegramHatasi(Exception):
    def __init__(self, mesaj, kod=None, bekle=None):
        super().__init__(mesaj)
        self.kod = kod
        self.bekle = bekle


def token_gecerli_mi(token):
    return bool(_TOKEN_DESENI.match((token or "").strip()))


def _istek(token, yontem, veri=None, zaman_asimi=15, acici=None):
    """Bot API çağrısı. Döner: 'result'. Hata mesajında token OLMAZ."""
    govde = json.dumps(veri).encode("utf-8") if veri is not None else None
    istek = urllib.request.Request(
        API % (token, yontem), data=govde,
        headers={"Content-Type": "application/json"} if govde is not None else {})
    acici = acici or urllib.request.urlopen
    try:
        with acici(istek, timeout=zaman_asimi) as cevap:
            js = json.loads(cevap.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            js = json.loads(e.read().decode("utf-8"))
        except Exception:                               # noqa: BLE001
            raise TelegramHatasi(HATA_ACIKLAMALARI.get(e.code, "Telegram HTTP %d" % e.code),
                                 kod=e.code)
    except urllib.error.URLError as e:
        raise TelegramHatasi("Telegram'a bağlantı yok: %s" % (getattr(e, "reason", "") or "ağ hatası"))
    except (OSError, ValueError) as e:
        raise TelegramHatasi("Telegram'a bağlantı hatası (%s)" % type(e).__name__)
    if not isinstance(js, dict) or not js.get("ok"):
        js = js if isinstance(js, dict) else {}
        kod = js.get("error_code")
        aciklama = str(js.get("description") or "")
        if kod == 400 and "chat not found" in aciklama.lower():
            mesaj = "sohbet bulunamadı — botuna Telegram'dan mesaj atıp Bul'a bas"
        else:
            mesaj = HATA_ACIKLAMALARI.get(kod, "Telegram reddetti (%s): %s" % (kod, aciklama[:120]))
        raise TelegramHatasi(mesaj, kod=kod,
                             bekle=(js.get("parameters") or {}).get("retry_after"))
    return js.get("result")


def mesaj_gonder(token, sohbet, metin, acici=None):
    return _istek(token, "sendMessage",
                  {"chat_id": str(sohbet), "text": (metin or "")[:AZAMI_UZUNLUK],
                   "disable_web_page_preview": True}, acici=acici)


class TelegramKumanda(threading.Thread):
    """
    Bota gelen komutları dinler (/durum, /durdur, /baslat...).

    Yalnızca `izinli_sohbet`ten gelen, '/' ile başlayan mesajlar `isle`
    geri çağrımına verilir. Başka sohbetlerden gelenler yok sayılır — böylece
    botu bulan biri bilgisayarındaki izleyiciyi kontrol edemez.

    Kısa yoklama (getUpdates timeout=0 + bekleme): uzun bağlantı ve 409
    çakışması yok. İlk yoklamadaki eski komutlar (program kapalıyken gelmiş)
    çalıştırılmaz, yalnızca sıradan atlanır.
    """

    def __init__(self, token, izinli_sohbet, isle, acici=None, gunluk=None, aralik=3.0):
        super().__init__(daemon=True)
        self._token = token
        self._izinli = str(izinli_sohbet)
        self._isle = isle
        self._acici = acici
        self._gunluk = gunluk or (lambda metin: None)
        self._aralik = aralik
        self.calisiyor = True
        self._offset = None
        self._ilk = True

    def durdur(self):
        self.calisiyor = False

    def _adim(self):
        veri = {"timeout": 0}
        if self._offset is not None:
            veri["offset"] = self._offset
        guncellemeler = _istek(self._token, "getUpdates", veri, acici=self._acici) or []
        for g in guncellemeler:
            self._offset = g.get("update_id", 0) + 1
            if self._ilk:
                continue
            mesaj = g.get("message") or g.get("edited_message") or {}
            sohbet = (mesaj.get("chat") or {}).get("id")
            metin = (mesaj.get("text") or "").strip()
            if metin.startswith("/") and str(sohbet) == self._izinli:
                try:
                    self._isle(metin, str(sohbet))
                except Exception:                       # noqa: BLE001
                    pass
        self._ilk = False

    def run(self):
        while self.calisiyor:
            try:
                self._adim()
                bekle = self._aralik
            except TelegramHatasi as e:
                self._gunluk("Telegram komut: %s" % e)
                bekle = min(30.0, self._aralik * 3)
            bitis = time.time() + bekle
            while self.calisiyor and time.time() < bitis:
                time.sleep(0.1)


def foto_gonder(token, sohbet, png, altyazi=None, acici=None):
    """PNG görüntüyü Telegram'a yollar (sendPhoto, multipart). Döner: result."""
    sinir = "----metinizleyici%d" % (int(time.time() * 1000) & 0xFFFFFFFF)
    cizgi = ("--" + sinir).encode("ascii")

    def alan(ad, deger):
        return (cizgi + b"\r\n"
                + ('Content-Disposition: form-data; name="%s"\r\n\r\n' % ad).encode("utf-8")
                + str(deger).encode("utf-8") + b"\r\n")

    govde = bytearray()
    govde += alan("chat_id", sohbet)
    if altyazi:
        govde += alan("caption", altyazi[:1024])
    govde += (cizgi + b"\r\n"
              + b'Content-Disposition: form-data; name="photo"; filename="ekran.png"\r\n'
              + b"Content-Type: image/png\r\n\r\n")
    govde += bytes(png)
    govde += b"\r\n" + cizgi + b"--\r\n"
    istek = urllib.request.Request(
        API % (token, "sendPhoto"), data=bytes(govde),
        headers={"Content-Type": "multipart/form-data; boundary=" + sinir})
    acici = acici or urllib.request.urlopen
    try:
        with acici(istek, timeout=30) as cevap:
            js = json.loads(cevap.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            js = json.loads(e.read().decode("utf-8"))
        except Exception:                               # noqa: BLE001
            raise TelegramHatasi(HATA_ACIKLAMALARI.get(e.code, "Telegram HTTP %d" % e.code),
                                 kod=e.code)
    except urllib.error.URLError as e:
        raise TelegramHatasi("Telegram'a bağlantı yok: %s" % (getattr(e, "reason", "") or "ağ"))
    except (OSError, ValueError) as e:
        raise TelegramHatasi("Telegram'a bağlantı hatası (%s)" % type(e).__name__)
    if not isinstance(js, dict) or not js.get("ok"):
        js = js if isinstance(js, dict) else {}
        raise TelegramHatasi(HATA_ACIKLAMALARI.get(js.get("error_code"),
                             "Telegram reddetti: %s" % str(js.get("description"))[:120]),
                             kod=js.get("error_code"))
    return js.get("result")


def sohbet_bul(token, acici=None):
    """
    Bota en son mesaj atan sohbetin (kimlik, ad).

    Kullanıcı botunu açıp Başlat'a basmış olmalı; yoksa TelegramHatasi.
    """
    guncellemeler = _istek(token, "getUpdates", {"timeout": 0}, acici=acici) or []
    for g in reversed(guncellemeler):
        mesaj = g.get("message") or g.get("edited_message") or {}
        sohbet = mesaj.get("chat") or (g.get("my_chat_member") or {}).get("chat")
        if sohbet and "id" in sohbet:
            ad = sohbet.get("first_name") or sohbet.get("title") or sohbet.get("username") or ""
            return str(sohbet["id"]), ad
    raise TelegramHatasi("bota henüz mesaj gelmemiş — Telegram'da botunu açıp Başlat'a bas, "
                         "sonra tekrar Bul")


class TelegramGonderici(object):
    """
    Arka planda mesaj yollar.

    - toplama_sn içinde gelen olaylar TEK mesajda birleşir
    - aynı metin tekrar_sn içinde yeniden gönderilmez
    - mesajlar arasında en az en_az_aralik sn (Telegram: sohbet başına ~1/sn)
    - 429 / ağ hatasında yeniden dener; token/sohbet hatasında denemez
    """

    def __init__(self, token, sohbet, toplama_sn=2.0, en_az_aralik=1.2,
                 yeniden_taban=2.0, acici=None, gunluk=None):
        self._token = token
        self.sohbet = str(sohbet)
        self.toplama_sn = toplama_sn
        self.en_az_aralik = en_az_aralik
        self.yeniden_taban = yeniden_taban
        self._acici = acici
        self._gunluk = gunluk or (lambda metin: None)
        self._kuyruk = queue.Queue()
        self._son = {}
        self._kilit = threading.Lock()
        self.gonderilen = 0
        self.son_hata = None
        self.calisiyor = True
        self._is = threading.Thread(target=self._dongu, daemon=True)
        self._is.start()

    def gonder(self, metin, tekrar_sn=60):
        """Kuyruğa ekler. Döner: eklendi mi (yakın zamanda aynısı gittiyse False)."""
        simdi = time.time()
        with self._kilit:
            if simdi - self._son.get(metin, 0) < tekrar_sn:
                return False
            self._son[metin] = simdi
            if len(self._son) > 500:
                for k in sorted(self._son, key=self._son.get)[:250]:
                    self._son.pop(k, None)
        self._kuyruk.put(metin)
        return True

    def durdur(self):
        self.calisiyor = False

    def _dongu(self):
        son_gonderim = 0.0
        while self.calisiyor:
            try:
                ilk = self._kuyruk.get(timeout=0.5)
            except queue.Empty:
                continue
            satirlar = [ilk]
            bitis = time.time() + self.toplama_sn
            while len(satirlar) < 20:
                kalan = bitis - time.time()
                if kalan <= 0:
                    break
                try:
                    satirlar.append(self._kuyruk.get(timeout=kalan))
                except queue.Empty:
                    break
            metin = "\n".join(satirlar)[:AZAMI_UZUNLUK]
            bekle = self.en_az_aralik - (time.time() - son_gonderim)
            if bekle > 0:
                time.sleep(bekle)
            for deneme in range(3):
                try:
                    mesaj_gonder(self._token, self.sohbet, metin, acici=self._acici)
                    self.gonderilen += 1
                    self.son_hata = None
                    break
                except TelegramHatasi as e:
                    self.son_hata = str(e)
                    if e.kod in (400, 401, 403, 404, 409):
                        self._gunluk("Telegram: %s" % e)
                        break
                    time.sleep(min(30.0, e.bekle or self.yeniden_taban * (deneme + 1)))
            else:
                self._gunluk("Telegram: mesaj gönderilemedi — %s" % self.son_hata)
            son_gonderim = time.time()
