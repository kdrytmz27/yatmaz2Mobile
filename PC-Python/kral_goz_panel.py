# -*- coding: utf-8 -*-
"""
KRALI YAKALA — GÖZ PANELİ

BAKIŞ HER ZAMAN EKRANDAN (adb screencap): masa, kuru kafalar, Kartım, deste.
HAMLE iki yoldan gidebilir:
  * varsayılan — ekrana dokunarak (adb input tap)
  * "Hamleyi sunucudan gönder" işaretliyse — 0xe2 paketiyle (anında gider) ve
    ıskalanan kartın değeri 0xee paketinden YEDEK olarak okunur; ekran
    görüntüsü ~1.2 sn sürdüğü için kart bazen biz bakmadan geri kapanıyor.

NOT DEFTERİ: yakalanan kart ekranda durur, YAKALANAMAYAN kart geri kapanır.
Bu yüzden ekranı her turda sıfırdan okumak yetmez — görülen her değer kalıcı
deftere yazılır ve beyin masayı oradan görür.

    python kral_goz_panel.py

Oyunda "Pop-Up" kutusunun işareti KALDIRILMIŞ olmalı.
"""

import os
import queue
import sys
import threading
import tkinter as tk

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KOK, "tools"))

import kral_goz as goz                                   # noqa: E402
import kral_oyna as oy                                   # noqa: E402

KOYU, PANEL, CIZGI = "#0f1117", "#171922", "#262a36"
METIN, SOLUK, VURGU = "#e6e8ef", "#9aa0b4", "#33aaff"
OK, UYARI, HATA = "#37d67a", "#ffb020", "#ff5a5a"
# kart değeri -> renk (oyundaki renklerle aynı mantık)
DEGER_RENK = {1: "#5fbf4a", 2: "#e08a2a", 3: "#d4c02a",
              4: "#b04ab0", 5: "#3a7fd5", 6: "#d44a4a"}


def _main():
    kok = tk.Tk()
    kok.title("Kralı Yakala — Göz")
    kok.configure(bg=KOYU)
    kok.geometry("620x700")
    kok.minsize(560, 620)

    durum = {"calisiyor": False, "oyuncu": None}
    kuyruk = queue.Queue()

    def btn(ana, metin, komut, renk=CIZGI):
        return tk.Button(ana, text=metin, command=komut, bg=renk,
                         fg=KOYU if renk in (VURGU, OK, HATA) else METIN,
                         activebackground=VURGU, relief="flat", bd=0,
                         padx=12, pady=6, font=("Segoe UI", 10, "bold"),
                         cursor="hand2")

    ust = tk.Frame(kok, bg=KOYU)
    ust.pack(fill="x", padx=12, pady=(12, 6))
    tk.Label(ust, text="Kralı Yakala — Göz", bg=KOYU, fg=METIN,
             font=("Segoe UI", 15, "bold")).pack(side="left")
    durum_et = tk.Label(ust, text="durduruldu", bg=KOYU, fg=SOLUK,
                        font=("Segoe UI", 10))
    durum_et.pack(side="right")

    ayar = tk.Frame(kok, bg=PANEL, highlightbackground=CIZGI,
                    highlightthickness=1)
    ayar.pack(fill="x", padx=12, pady=6)
    tk.Label(ayar, text="Hamle arası (sn)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w",
                                        padx=8, pady=5)
    bekle_var = tk.DoubleVar(value=1.0)
    tk.Spinbox(ayar, from_=0.3, to=5.0, increment=0.1, textvariable=bekle_var,
               width=6, bg=KOYU, fg=METIN, relief="flat",
               font=("Consolas", 9)).grid(row=0, column=1, padx=4)
    tk.Label(ayar, text="Oyun bitene kadar oynar", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=0, column=2, columnspan=2,
                                        sticky="w", padx=8)

    sunucu_var = tk.BooleanVar(value=False)
    tk.Checkbutton(ayar, text="Hamleyi sunucudan gönder (bakış yine ekrandan)",
                   variable=sunucu_var, bg=PANEL, fg=METIN, selectcolor=KOYU,
                   activebackground=PANEL, activeforeground=METIN,
                   font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=4,
                                              sticky="w", padx=8, pady=(0, 5))

    bilgi = tk.Label(kok, text="Kartım: -     Defter: 0     Alınan: 0",
                     bg=KOYU, fg=OK, font=("Segoe UI", 12, "bold"))
    bilgi.pack(anchor="w", padx=12, pady=(6, 0))

    izgara = tk.Frame(kok, bg=KOYU)
    izgara.pack(padx=12, pady=8)
    hucreler = {}
    for pos in range(25):
        h = tk.Label(izgara, text="?", width=4, height=2, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 12, "bold"), relief="flat",
                     highlightthickness=1, highlightbackground=CIZGI)
        h.grid(row=pos // 5, column=pos % 5, padx=3, pady=3)
        hucreler[pos] = h

    log = tk.Text(kok, bg=KOYU, fg=METIN, relief="flat",
                  font=("Consolas", 9), height=14, wrap="word",
                  state="disabled")
    log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def log_yaz(s):
        log.configure(state="normal")
        log.insert("end", s + "\n")
        log.see("end")
        log.configure(state="disabled")

    def tazele():
        o = durum.get("oyuncu")
        if o is not None:
            for pos, h in hucreler.items():
                if pos in o.yakalanan:
                    d = o.defter.get(pos)
                    h.configure(text=goz.AD.get(d, "·"), fg=KOYU,
                                bg=OK)                    # alınmış = yeşil
                elif pos in o.defter:
                    d = o.defter[pos]
                    h.configure(text=goz.AD.get(d, "·"), fg=KOYU,
                                bg=DEGER_RENK.get(d, METIN))
                elif pos in o.kafali:
                    h.configure(text="☠", fg=UYARI, bg=PANEL)
                else:
                    h.configure(text="?", fg=SOLUK, bg=PANEL)
            el = o.durum.get("el") if o.durum else None
            bilgi.configure(text="Kartım: %s     Defter: %d     Alınan: %d"
                                 % (goz.AD.get(el, "-"), len(o.defter),
                                    len(o.yakalanan)))
        durum_et.configure(text="oynuyor" if durum["calisiyor"] else "durduruldu",
                           fg=OK if durum["calisiyor"] else SOLUK)
        while True:
            try:
                log_yaz(kuyruk.get_nowait())
            except queue.Empty:
                break
        kok.after(250, tazele)

    def baslat(kuru=False):
        if durum["calisiyor"]:
            return
        durum["calisiyor"] = True
        o = oy.GozOyuncu(gunluk=kuyruk.put, bekle=bekle_var.get(), kuru=kuru,
                         sunucu=bool(sunucu_var.get()))
        durum["oyuncu"] = o
        kuyruk.put("== %s ==" % ("KURU deneme (tıklama yok)" if kuru
                                 else "oyun başladı"))

        def sarmal():
            try:
                o.oyna(lambda: durum["calisiyor"])   # bitene kadar
            except Exception as e:                       # noqa: BLE001
                kuyruk.put("HATA: %s: %s" % (type(e).__name__, e))
            finally:
                durum["calisiyor"] = False
                kuyruk.put("== durduruldu ==")

        threading.Thread(target=sarmal, daemon=True).start()

    def dur():
        durum["calisiyor"] = False

    def defter_sifirla():
        o = durum.get("oyuncu")
        if o and not durum["calisiyor"]:
            o.sifirla()
            kuyruk.put("not defteri sıfırlandı (yeni masa)")

    dug = tk.Frame(kok, bg=KOYU)
    dug.pack(fill="x", padx=12, pady=(0, 10))
    btn(dug, "▶ Oyna", lambda: baslat(False), OK).pack(side="left")
    btn(dug, "■ Durdur", dur, HATA).pack(side="left", padx=8)
    btn(dug, "🔍 Kuru deneme", lambda: baslat(True)).pack(side="left")
    btn(dug, "🗒 Defteri sıfırla", defter_sifirla).pack(side="left", padx=8)

    log_yaz("Hazır. Oyunda Kralı Yakala masasını aç, 'Pop-Up' işaretini "
            "KALDIR, sonra ▶ Oyna.")
    log_yaz("Bakış her zaman EKRANDAN. Hamle varsayılan olarak ekrana "
            "dokunarak gider; kutuyu işaretlersen sunucuya paketle gider "
            "(daha hızlı, ıskalanan kartın değerini de paketten okur).")
    tazele()
    kok.mainloop()


if __name__ == "__main__":
    _main()
