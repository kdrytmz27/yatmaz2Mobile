# -*- coding: utf-8 -*-
"""
İstemci eşitleme neden çalışmıyor? — ZİNCİRİ baştan sona sınar.

Hizalamanın çalışması için altı halkanın hepsi sağlam olmalı. Bu betik
her birini tek tek dener ve HANGİSİNİN koptuğunu söyler:

    1. API'ye ulaşılıyor mu           (/api/durum)
    2. Proxy oyuna BAĞLI mı
    3. ENJEKSİYON açık mı
    4. Kendi vid'imiz biliniyor mu, kaç oy aldı
    5. Vid bir canavara mı denk geliyor
    6. CANLI TEST: hizalama paketi gönderilince istemci gerçekten taşınıyor mu

Son adım gerçek testtir: karakteri 10 m yana gönderir, sonra istemcinin
kendi konum bildirimini bekler. İstemci taşındıysa /api/konum'daki x,y
değişir ve istemciHareketYas tazelenir.

KULLANIM
--------
    python tools/sync_teshis.py

ÖNCE: oyun açık, proxy bağlı. Karakteri elle oynatma.
"""

import http.client
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ADRES = "127.0.0.1:30200"
TIP_MOB, TIP_METIN = 0, 2


def adb_forward():
    for aday in ['adb',
                 os.path.expanduser(
                     r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe')]:
        try:
            subprocess.run([aday, 'forward', 'tcp:30200', 'tcp:30200'],
                           capture_output=True, timeout=10)
            return
        except Exception:
            continue


def get(yol):
    try:
        c = http.client.HTTPConnection(ADRES, timeout=4)
        c.request("GET", yol)
        r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
        c.close()
        return r
    except Exception as e:
        return {"_hata": str(e)}


def post(yol, govde):
    try:
        c = http.client.HTTPConnection(ADRES, timeout=4)
        c.request("POST", yol, body=govde.encode("utf-8"))
        r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
        c.close()
        return r
    except Exception as e:
        return {"_hata": str(e)}


def u32(v):
    return list((int(v) & 0xFFFFFFFF).to_bytes(4, "little"))


def sync_paketi(vid, x, y):
    govde = u32(vid) + u32(x) + u32(y)
    boy = 3 + len(govde)
    return bytes([0x05, boy & 0xFF, (boy >> 8) & 0xFF] + govde)


def basari(n, ad, detay=""):
    print("  [%d] OK   %s%s" % (n, ad, ("  — " + detay) if detay else ""))


def hata(n, ad, cozum):
    print("  [%d] KOPUK %s" % (n, ad))
    print()
    print("  " + "-" * 62)
    print("  ÇÖZÜM:")
    for satir in cozum.strip().split("\n"):
        print("    " + satir)
    print("  " + "-" * 62)


def main():
    adb_forward()
    print("=" * 70)
    print("İSTEMCİ EŞİTLEME TEŞHİSİ")
    print("=" * 70)
    print()

    # --- 1 ---
    d = get("/api/durum")
    if "_hata" in d:
        hata(1, "API'ye ulaşılamıyor (%s)" % d["_hata"],
             "• Telefon USB ile bağlı mı?  adb devices\n"
             "• APK açık mı, paket okuyucu çalışıyor mu?\n"
             "• Port yönlendirme: adb forward tcp:30200 tcp:30200")
        input("\nEnter..."); return
    basari(1, "API'ye ulaşıldı")

    # --- 2 ---
    p = d.get("proxy") or {}
    if not p.get("bagli"):
        hata(2, "Proxy oyuna BAĞLI DEĞİL",
             "• Oyunu KAPAT, APK'da proxy'yi aç, sonra oyunu aç.\n"
             "• Oyun proxy üzerinden bağlanmalı; doğrudan bağlanırsa\n"
             "  istemciye paket yazamayız.")
        input("\nEnter..."); return
    basari(2, "Proxy oyuna bağlı")

    # --- 3 ---
    if not p.get("enjeksiyon"):
        hata(3, "ENJEKSİYON KAPALI",
             "• APK'da enjeksiyon anahtarını AÇ.\n"
             "• Kapalıyken paketler yalnızca loglanır, gönderilmez.")
        input("\nEnter..."); return
    basari(3, "Enjeksiyon açık")

    # --- 4 ---
    k = get("/api/konum")
    vid = int(k.get("kendiVid", 0) or 0)
    oy = k.get("kendiVidOyu", None)
    aday = k.get("kendiVidAday", None)
    if oy is None:
        hata(4, "APK oy bilgisi vermiyor — ESKİ SÜRÜM",
             "• Yeni APK'yı kur:\n"
             "  adb install -r app\\build\\outputs\\apk\\debug\\app-debug.apk")
        input("\nEnter..."); return
    if not vid:
        hata(4, "Kendi vid'imiz BİLİNMİYOR",
             "Vid iki kaynaktan öğrenilir:\n"
             "  • 0x11 durum tiki — bazı oturumlarda HİÇ gelmiyor\n"
             "  • 0x3E savaş vuruşu — bir CANAVARA saldırınca gelir\n"
             "\n"
             "Yani: BOTU CANAVARLA SAVAŞTIR. Sadece metin kırmak\n"
             "yetmeyebilir; Hedefleme sekmesinde 'Canavarlar' açık olsun.\n"
             "3 vuruş sonra öğrenilir.\n"
             "\n"
             "İzlemek için: python tools/vid_izle.py")
        input("\nEnter..."); return
    if oy < 3:
        hata(4, "Vid var (%d) ama sadece %d oy — güvenilmez" % (vid, oy),
             "Bot güvenmediği bir vid'e paket göndermiyor (yanlışsa\n"
             "istemci başka bir varlığı taşır). Biraz daha savaş,\n"
             "oy 3'e çıkınca hizalama başlar.")
        input("\nEnter..."); return
    isabet = k.get("savasIsabet", None)
    iska = k.get("savasIska", None)
    ek = "%d oy, %d aday" % (oy, aday)
    if isabet is not None:
        ek += "  |  savaş kanıtı: %d isabet / %d ıska" % (isabet, iska)
    basari(4, "Kendi vid: %d" % vid, ek)
    # Savaş kanıtı oranı: BİZ yalnızca kendi hedeflerimize vururuz.
    # Iska yüksekse aday büyük olasılıkla başka bir oyuncu.
    if isabet and iska is not None and iska * 4 > isabet:
        print()
        print("      !! ŞÜPHELİ: bu vid %d kez BİZİM hedefimize, %d kez"
              % (isabet, iska))
        print("         BAŞKA şeye vurmuş. Biz yalnızca kendi hedefimize")
        print("         vururuz — bu aday muhtemelen başka bir oyuncu.")
        print("      adaylar (vid:isabet/ıska): %s"
              % k.get("savasAdaylari", "?"))

    # --- 5 ---
    varliklar = get("/api/varliklar?n=150")
    isim = ""
    if isinstance(varliklar, list):
        for v in varliklar:
            if int(v.get("vid", 0) or 0) == vid:
                isim = v.get("ad") or ""
                if v.get("tip") in (TIP_MOB, TIP_METIN):
                    hata(5, "Vid %d bir CANAVAR/METİN (%s)" % (vid, isim),
                         "Bu biz değiliz. Bot bilerek paket göndermiyor —\n"
                         "yoksa istemci o varlığı sürüklerdi.\n"
                         "\n"
                         "tambot > Hareket > 'Kendi vid' alanına doğru\n"
                         "vid'i elle gir, ya da botu yeniden başlatıp\n"
                         "vid'in yeniden öğrenilmesini bekle.")
                    input("\nEnter..."); return
                break
    basari(5, "Vid bir canavar değil",
           ("isim: %s" % isim) if isim else "listede yok (normal)")

    # --- 6 CANLI TEST ---
    print()
    print("  [6] CANLI TEST")
    bx, by = int(k.get("x", 0)), int(k.get("y", 0))
    hx, hy = bx + 1000, by                       # 10 m yan
    print("      şu anki konum : %d, %d" % (bx, by))
    print("      hedef         : %d, %d  (10 m yan)" % (hx, hy))
    paket = sync_paketi(vid, hx, hy)
    print("      paket         : %s" % " ".join("%02X" % b for b in paket))
    input("      Enter'a bas, gönderilsin (EKRANA BAK)...")

    c = post("/api/enjekte_istemci", " ".join("%02X" % b for b in paket))
    if not (isinstance(c, dict) and c.get("ok")):
        hata(6, "Paket gönderilemedi: %s" % c,
             "Enjeksiyon açık görünüyor ama yazma başarısız.\n"
             "Proxy bağlantısı kopmuş olabilir — oyunu yeniden bağla.")
        input("\nEnter..."); return
    print("      gönderildi, istemcinin cevabı bekleniyor...")

    tasindi = False
    for _ in range(12):
        time.sleep(0.5)
        y2 = get("/api/konum")
        nx, ny = int(y2.get("x", 0)), int(y2.get("y", 0))
        if (nx, ny) != (bx, by):
            tasindi = True
            print("      istemci bildirdi: %d, %d  (%.0f m yer değiştirdi)"
                  % (nx, ny, ((nx - bx) ** 2 + (ny - by) ** 2) ** 0.5 / 100.0))
            break

    print()
    print("=" * 70)
    if tasindi:
        print("SONUÇ: EŞİTLEME ÇALIŞIYOR. Zincirin altı halkası da sağlam.")
        print()
        print("Yine de oyunda hareket etmiyor gibi görünüyorsa:")
        print("  • Hareket sekmesi > 'İSTEMCİYİ de hizala' işaretli mi?")
        print("  • 'Hizalama aralığı' 0 ise sadece bacak sonunda gider;")
        print("    800 yap.")
        print("  • 'Sürükle (0x05)' seçili mi? 'GC_MOVE (0x03)' bu")
        print("    sunucuda etkisiz.")
        print("  • Kuru çalışma KAPALI olmalı.")
    else:
        print("SONUÇ: Paket gitti ama istemci konum bildirmedi.")
        print()
        print("İki ihtimal:")
        print("  1. Karakter EKRANDA taşındı ama istemci sunucuya kendi")
        print("     konumunu bildirmedi. Bu NORMAL — istemci yalnızca sen")
        print("     hareket ettirince 0x07 yollar. Ekrana baktın mı,")
        print("     karakter yer değiştirdi mi?")
        print("  2. Karakter HİÇ KIMILDAMADIYSA vid yanlış.")
        print("     Adaylar (vid:isabet/ıska): %s"
              % (get("/api/konum") or {}).get("savasAdaylari", "?"))
        print()
        print("     Kesin vid'i kayıttan bul:")
        print("       PC_YAKALA.bat 60          (bot SAVAŞIRKEN)")
        print("       python tools/kendi_vid_savastan.py")
        print("     Çıkan vid'i tambot > Hareket > 'Kendi vid' alanına yaz.")
    print("=" * 70)
    input("\nEnter...")


if __name__ == '__main__':
    main()
