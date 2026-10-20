# -*- coding: utf-8 -*-
"""
İstemciyi sunucudaki konumumuza hizalayacak paketi ARAR.

SORUN
-----
Sunucu KENDİ hareketimizi bize geri yollamıyor — 29 Ağu 2026 ölçümünde
859 gelen 0x03 MOVE paketinin SIFIRI bizim vid'imizi taşıyordu. Bot bir
hareket enjekte edince sunucudaki konum değişiyor, ama istemcinin haberi
olmuyor. İstemci ilk fırsatta kendi (eski) konumunu tekrar bildirip bizi
geri çekiyor. Wait-hack'in ve uzun yürüyüşlerin asıl darboğazı bu.

ÇÖZÜM ADAYI
-----------
Proxy ortada olduğu için İSTEMCİYE de paket yazabiliriz — "sen artık
şuradasın" demek. Hangi paketin bunu yaptığını bilmiyoruz; bu betik
adayları sırayla dener.

Adaylar (mevcut yakalamalardan çıkarıldı):
  0x01  CHARACTER_ADD, kendi vid'imizle — giriş anında bir kez görüldü:
        01 <vid> <acı f32> <x> <y> <z> <bType=6> <vnum> ...
  0x03  MOVE, kendi vid'imizle — sunucu normalde göndermiyor ama istemci
        yine de işleyebilir
  0x05  SYNC_POSITION, tek elemanlı, kendi vid'imizle

NE YAPAR / NE YAPMAZ
--------------------
Bu YALNIZCA istemcinin gördüğünü hizalar. Sunucudaki gerçeği değiştirmez;
envanter, eşya, stat gibi her şey sunucuda tutulur ve bundan etkilenmez.
Amaç yeni bir şey kazanmak değil, istemci-sunucu ayrışmasını kapatmak.

KULLANIM
--------
    python tools/istemci_hizala.py            # 10 m yana dene
    python tools/istemci_hizala.py 25         # 25 m yana dene

ÖNCE: proxy açık ve oyuna BAĞLI, enjeksiyon açık olmalı.
Karakteri elle oynatma; ekranı izle.
"""

import http.client
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

ADRES = "127.0.0.1:30200"


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
    c = http.client.HTTPConnection(ADRES, timeout=4)
    c.request("GET", yol)
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def post(yol, govde):
    c = http.client.HTTPConnection(ADRES, timeout=4)
    c.request("POST", yol, body=govde.encode("utf-8"))
    r = json.loads(c.getresponse().read().decode("utf-8", "replace"))
    c.close()
    return r


def u32(v):
    return list((int(v) & 0xFFFFFFFF).to_bytes(4, "little"))


def kendi_vid():
    """0x11 paketi HEP kendi vid'imizi taşır; günlükten okunur."""
    try:
        kayitlar = get("/api/log?n=80")
    except Exception:
        return None
    for k in kayitlar:
        if k.get("giden") or k.get("opcode") != 0x11:
            continue
        hx = (k.get("hex") or "").split()
        if len(hx) < 5:
            continue
        try:
            return int(hx[4] + hx[3] + hx[2] + hx[1], 16)
        except ValueError:
            continue
    return None


def adaylar(vid, x, y):
    """Denenecek paketler: (ad, baytlar)."""
    liste = []

    # 0x01 CHARACTER_ADD — 38 bayt, kendi vid + konum + bType=6 (oyuncu)
    p = [0x01] + u32(vid) + [0, 0, 0, 0] + u32(x) + u32(y) + u32(0)
    p += [6, 0, 0, 0, 0, 100, 80]
    p += [0] * (38 - len(p))
    liste.append(("0x01 CHARACTER_ADD (kendi vid)", bytes(p[:38])))

    # 0x03 MOVE — 24 bayt
    p = [0x03, 0, 0, 0] + u32(vid) + u32(x) + u32(y) + u32(0) + u32(0)
    liste.append(("0x03 MOVE (kendi vid)", bytes(p[:24])))

    # 0x05 SYNC_POSITION — tek eleman
    govde = u32(vid) + u32(x) + u32(y)
    boy = 3 + len(govde)
    liste.append(("0x05 SYNC_POSITION (tek eleman)",
                  bytes([0x05, boy & 0xFF, (boy >> 8) & 0xFF] + govde)))
    return liste


def main():
    adb_forward()
    try:
        metre = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    except Exception:
        metre = 10

    print("=" * 68)
    print("İSTEMCİ HİZALAMA — aday paket arayışı")
    print("=" * 68)

    try:
        d = get("/api/durum")
    except Exception as e:
        print("X API'ye ulaşılamadı: %s" % e)
        input("\nEnter..."); return

    p = d.get("proxy") or {}
    if not p.get("bagli"):
        print("X Proxy oyuna BAĞLI değil — istemciye yazılamaz.")
        input("\nEnter..."); return
    if not p.get("enjeksiyon"):
        print("X Enjeksiyon kapalı.")
        input("\nEnter..."); return

    vid = kendi_vid()
    if not vid:
        print("X Kendi vid'imiz bulunamadı (0x11 paketi günlükte yok).")
        print("  Oyunda biraz bekle, sonra tekrar dene.")
        input("\nEnter..."); return

    k = get("/api/konum")
    bx, by = int(k["x"]), int(k["y"])
    hx, hy = bx + metre * 100, by
    print("kendi vid : %d" % vid)
    print("konum     : %d, %d" % (bx, by))
    print("hedef     : %d, %d   (%d m yan)" % (hx, hy, metre))
    print()
    print("Her aday için EKRANA BAK: karakter yer değiştiriyor mu?")
    print("-" * 68)

    for ad, paket in adaylar(vid, hx, hy):
        hexstr = " ".join("%02X" % b for b in paket)
        print("\n>>> %s  (%d bayt)" % (ad, len(paket)))
        print("    %s" % hexstr)
        input("    Enter'a bas, gönderilsin...")
        try:
            c = post("/api/enjekte_istemci", hexstr)
        except Exception as e:
            print("    X gönderilemedi: %s" % e)
            continue
        if not (isinstance(c, dict) and c.get("ok")):
            print("    X %s" % c)
            continue
        print("    gönderildi.")
        cevap = input("    Karakter EKRANDA yer değiştirdi mi? (e/h): ").strip().lower()
        if cevap.startswith("e"):
            print()
            print("=" * 68)
            print("BULUNDU: %s" % ad)
            print("Paket: %s" % hexstr)
            print("=" * 68)
            input("\nEnter..."); return

    print()
    print("Hiçbir aday istemciyi taşımadı.")
    print("Sonraki adım: karakteri gerçekten ışınlayan bir şey yap")
    print("(köye dönüş kağıdı, portal) ve tools/eylem_yakala.py ile kaydet —")
    print("o anda GELEN paketler arasında doğru olan bulunur.")
    input("\nEnter...")


if __name__ == '__main__':
    main()
