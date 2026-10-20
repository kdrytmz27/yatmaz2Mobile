# -*- coding: utf-8 -*-
"""
PAZAR FIRSAT PANELİ — anlık. Ucuzlayanı ve aradığını hemen gösterir.

SATIN ALMA YOK: bot yalnız dükkânı açar, okur, kapatır.

Nasıl çalışır
-------------
  * Bot sürekli tur atar: yürü → menzildeki dükkânlara tıkla → yürü
  * Okuma tcpdump AKIŞINDAN yapılır, dükkân okunur okunmaz elimize geçer
    (/api/log 3449 baytlık dükkân paketini kırpıyor, oradan okunamıyor)
  * Gelen her eşya izleme kurallarına ve fiyat geçmişine bakılır
  * Uyan varsa ANINDA listeye düşer ve ses çalar

Fiyat geçmişi neden lazım: "ucuzladı" diyebilmek için eski fiyatı bilmek
gerekir. Geçmiş kıyas tabanıdır; gösterilen şey hep canlıdır.

    python pazar_panel.py
"""

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KOK, "tools"))

import pazar_firsat as pf                                # noqa: E402
import pazar_paket as pp                                 # noqa: E402
import pazar_tara as pt                                  # noqa: E402
import pazar_toplu as pzt                                # noqa: E402

KOYU, PANEL, CIZGI = "#0f1117", "#171922", "#262a36"
METIN, SOLUK, VURGU = "#e6e8ef", "#9aa0b4", "#33aaff"
OK, UYARI, HATA = "#37d67a", "#ffb020", "#ff5a5a"
SABIT = ("Consolas", 9)
KURAL_DOSYA = os.path.join(KOK, "veri", "pazar_kurallar.json")


def _main():
    kok = tk.Tk()
    kok.title("Pazar — fırsat takibi")
    kok.configure(bg=KOYU)
    kok.geometry("1040x740")
    kok.minsize(880, 620)

    kuyruk = queue.Queue()
    durum = {"calisiyor": False, "tur": 0, "dukkan": 0}
    adlar = pt.EsyaAdlari()
    gecmis = pf.FiyatGecmisi()
    kurallar = []

    def btn(ana, metin, komut, renk=CIZGI):
        return tk.Button(ana, text=metin, command=komut, bg=renk,
                         fg=KOYU if renk in (VURGU, OK, HATA) else METIN,
                         activebackground=VURGU, relief="flat", bd=0,
                         padx=10, pady=5, font=("Segoe UI", 10, "bold"),
                         cursor="hand2")

    # ── üst ─────────────────────────────────────────────────────────────
    ust = tk.Frame(kok, bg=KOYU)
    ust.pack(fill="x", padx=12, pady=(12, 4))
    tk.Label(ust, text="Pazar — fırsat takibi", bg=KOYU, fg=METIN,
             font=("Segoe UI", 15, "bold")).pack(side="left")
    durum_et = tk.Label(ust, text="durduruldu", bg=KOYU, fg=SOLUK,
                        font=("Segoe UI", 10))
    durum_et.pack(side="right")

    # ── izleme kuralları ────────────────────────────────────────────────
    kf = tk.Frame(kok, bg=PANEL, highlightbackground=CIZGI, highlightthickness=1)
    kf.pack(fill="x", padx=12, pady=4)
    tk.Label(kf, text="İZLEME LİSTESİ — bunlar çıkınca haber ver", bg=PANEL,
             fg=VURGU, font=("Segoe UI", 10, "bold")).grid(
        row=0, column=0, columnspan=9, sticky="w", padx=8, pady=(6, 2))

    def _gir(sut, etiket, genislik):
        tk.Label(kf, text=etiket, bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 9)).grid(row=1, column=sut * 2,
                                            sticky="w", padx=(8, 2))
        v = tk.StringVar()
        tk.Entry(kf, textvariable=v, bg=KOYU, fg=METIN, insertbackground=METIN,
                 relief="flat", width=genislik, font=SABIT).grid(
            row=1, column=sut * 2 + 1, padx=(0, 6))
        return v

    k_ad = _gir(0, "Eşya", 20)
    k_azami = _gir(1, "Azami fiyat", 12)
    k_efsun = _gir(2, "Efsun", 16)
    k_enaz = _gir(3, "en az", 6)

    kural_kutu = tk.Listbox(kf, bg=KOYU, fg=METIN, relief="flat", font=SABIT,
                            height=3, selectbackground=CIZGI,
                            highlightthickness=0)
    kural_kutu.grid(row=2, column=0, columnspan=8, sticky="ew",
                    padx=8, pady=(4, 8))
    kf.columnconfigure(7, weight=1)

    def kurallari_yaz():
        kural_kutu.delete(0, "end")
        for k in kurallar:
            kural_kutu.insert("end", "  " + k.metin())

    def kural_kaydet():
        try:
            os.makedirs(os.path.dirname(KURAL_DOSYA), exist_ok=True)
            with open(KURAL_DOSYA, "w", encoding="utf-8") as f:
                json.dump([k.sozluk() for k in kurallar], f, ensure_ascii=False)
        except Exception:                                # noqa: BLE001
            pass

    def kural_yukle():
        try:
            with open(KURAL_DOSYA, encoding="utf-8") as f:
                for d in json.load(f):
                    kurallar.append(pf.Kural(**d))
        except Exception:                                # noqa: BLE001
            pass

    def kural_ekle():
        try:
            azami = int((k_azami.get() or "0").replace(".", "").strip() or 0)
        except ValueError:
            azami = 0
        try:
            enaz = int((k_enaz.get() or "0").strip() or 0)
        except ValueError:
            enaz = 0
        if not (k_ad.get().strip() or k_efsun.get().strip() or azami):
            kuyruk.put("kural boş olamaz")
            return
        kurallar.append(pf.Kural(k_ad.get().strip(), azami,
                                 k_efsun.get().strip(), enaz))
        for v in (k_ad, k_azami, k_efsun, k_enaz):
            v.set("")
        kurallari_yaz()
        kural_kaydet()
        avci.kurallar = kurallar

    def kural_sil():
        s = kural_kutu.curselection()
        if s:
            kurallar.pop(s[0])
            kurallari_yaz()
            kural_kaydet()
            avci.kurallar = kurallar

    btn(kf, "+ Ekle", kural_ekle, OK).grid(row=1, column=8, padx=(6, 8))
    btn(kf, "− Sil", kural_sil).grid(row=2, column=8, padx=(6, 8), sticky="n")

    # ── fırsat akışı ────────────────────────────────────────────────────
    bilgi = tk.Label(kok, text="fırsat yok", bg=KOYU, fg=OK,
                     font=("Segoe UI", 11, "bold"))
    bilgi.pack(anchor="w", padx=12, pady=(6, 0))

    lf = tk.Frame(kok, bg=KOYU)
    lf.pack(fill="both", expand=True, padx=12, pady=4)
    kaydir = tk.Scrollbar(lf)
    kaydir.pack(side="right", fill="y")
    akis = tk.Text(lf, bg=KOYU, fg=METIN, relief="flat", font=SABIT,
                   wrap="none", state="disabled", yscrollcommand=kaydir.set)
    akis.pack(fill="both", expand=True)
    kaydir.config(command=akis.yview)
    akis.tag_configure("hedef", foreground=OK)
    akis.tag_configure("ucuz", foreground=UYARI)
    akis.tag_configure("efsun", foreground=VURGU)
    akis.tag_configure("okundu", foreground=SOLUK)
    akis.tag_configure("firsatli", foreground=METIN)

    log = tk.Text(kok, bg=KOYU, fg=SOLUK, relief="flat",
                  font=("Consolas", 8), height=6, wrap="word", state="disabled")
    log.pack(fill="x", padx=12, pady=(0, 4))

    def log_yaz(s):
        log.configure(state="normal")
        log.insert("end", s + "\n")
        log.see("end")
        log.configure(state="disabled")

    ses_var = tk.BooleanVar(value=True)

    def firsat_yaz(f):
        akis.configure(state="normal")
        etk = "hedef" if f["tur"] == "HEDEF" else "ucuz"
        bas = time.strftime("%H:%M:%S", time.localtime(f["zaman"]))
        ek = ""
        if f["tur"] == "UCUZLADI" and f.get("eski_fiyat"):
            ek = "   (önceki en düşük %s)" % pp._yang(f["eski_fiyat"])
        if f.get("efsunlar"):
            akis.insert("1.0", "%26s%s\n"
                        % ("", ", ".join("%s %+d" % (x["ad"], x["deger"])
                                         for x in f["efsunlar"])), "efsun")
        akis.insert("1.0", "%s  %-8s %14s  %-30s %3d ad.  %s%s\n"
                    % (bas, f["tur"], pp._yang(f["fiyat"]), f["esya"][:30],
                       f["adet"], f["dukkan"][:22], ek), etk)
        akis.configure(state="disabled")
        bilgi.configure(text="%d fırsat   |   %d dükkân okundu   |   tur %d"
                             % (len(avci.firsatlar), durum["dukkan"],
                                durum["tur"]))

    okunan_dukkanlar = {}          # vid -> (ad, esyalar)

    def dukkan_ac(vid):
        """Bir pazarın BÜTÜN eşyalarını ayrı pencerede göster."""
        kayit = okunan_dukkanlar.get(vid)
        if not kayit:
            return
        ad, esyalar = kayit
        p = tk.Toplevel(kok)
        p.title("%s — %d eşya" % (ad, len(esyalar)))
        p.configure(bg=KOYU)
        p.geometry("780x500")
        cf = tk.Frame(p, bg=KOYU)
        cf.pack(fill="both", expand=True, padx=8, pady=8)
        kd = tk.Scrollbar(cf)
        kd.pack(side="right", fill="y")
        t = tk.Text(cf, bg=KOYU, fg=METIN, relief="flat", font=SABIT,
                    wrap="none", yscrollcommand=kd.set)
        t.pack(fill="both", expand=True)
        kd.config(command=t.yview)
        t.tag_configure("efsun", foreground=VURGU)
        t.tag_configure("bas", foreground=SOLUK)
        t.insert("end", "%-36s %14s  %4s\n"
                 % ("EŞYA", "FİYAT", "ADET"), "bas")
        for e in sorted(esyalar, key=lambda x: -x.get("fiyat", 0)):
            t.insert("end", "%-36s %14s  %4d\n"
                     % (adlar.ad(e["vnum"])[:36], pp._yang(e["fiyat"]),
                        e.get("adet", 1)))
            ef = [x for x in (e.get("efsunlar") or []) if x.get("deger")]
            if ef:
                t.insert("end", "%38s%s\n"
                         % ("", ", ".join("%s %+d" % (x["ad"], x["deger"])
                                          for x in ef)), "efsun")
        t.configure(state="disabled")

    def _akis_cift_tik(olay):
        """Akıştaki dükkân satırına çift tık: içeriğini aç."""
        yer = akis.index("@%d,%d" % (olay.x, olay.y))
        for etk in akis.tag_names(yer):
            if etk.startswith("d") and etk[1:].isdigit():
                dukkan_ac(int(etk[1:]))
                return "break"

    akis.bind("<Double-Button-1>", _akis_cift_tik)

    def okundu_yaz(ad, esya, firsat, vid=0):
        """Okunan dükkânı akışa yaz (fırsat yoksa soluk)."""
        akis.configure(state="normal")
        etiketler = ["firsatli" if firsat else "okundu"]
        if vid:
            etiketler.append("d%d" % vid)
        akis.insert("1.0", "%s  okundu   %-34s %3d eşya%s\n"
                    % (time.strftime("%H:%M:%S"), ad[:34], esya,
                       "   ★ %d fırsat" % firsat if firsat else ""),
                    tuple(etiketler))
        # akış şişmesin
        if int(akis.index("end-1c").split(".")[0]) > 800:
            akis.delete("600.0", "end")
        akis.configure(state="disabled")
        bilgi.configure(text="%d fırsat   |   %d dükkân okundu   |   tur %d"
                             % (len(avci.firsatlar), durum["dukkan"],
                                durum["tur"]))

    def firsat_geldi(f):
        kok.after(0, lambda: firsat_yaz(f))
        if ses_var.get():
            try:
                pzt.tb.bildirim_sesi()
            except Exception:                            # noqa: BLE001
                pass

    avci = pf.FirsatAvcisi(adlar, gecmis, kurallar, bildir=firsat_geldi)

    # ── tarama ayarları ─────────────────────────────────────────────────
    class _Ayar:
        def __init__(self, menzil, ara, sure):
            self.menzil, self.ara, self.sure = menzil, ara, sure

    af = tk.Frame(kok, bg=PANEL, highlightbackground=CIZGI, highlightthickness=1)
    af.pack(fill="x", padx=12, pady=(0, 4))
    tk.Label(af, text="Dükkân arası (sn)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w",
                                        padx=8, pady=5)
    bekle_var = tk.DoubleVar(value=0.4)
    tk.Spinbox(af, from_=0.1, to=3.0, increment=0.1, textvariable=bekle_var,
               width=5, bg=KOYU, fg=METIN, relief="flat",
               font=SABIT).grid(row=0, column=1, padx=4)
    tk.Label(af, text="Menzil (m)", bg=PANEL, fg=SOLUK,
             font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(12, 4))
    menzil_var = tk.IntVar(value=15)
    tk.Spinbox(af, from_=5, to=40, textvariable=menzil_var, width=5, bg=KOYU,
               fg=METIN, relief="flat", font=SABIT).grid(row=0, column=3, padx=4)
    surekli_var = tk.BooleanVar(value=True)
    tk.Checkbutton(af, text="Sürekli tur (durmadan tara)",
                   variable=surekli_var, bg=PANEL, fg=METIN, selectcolor=KOYU,
                   activebackground=PANEL, activeforeground=METIN,
                   font=("Segoe UI", 9)).grid(row=0, column=4, sticky="w",
                                              padx=(12, 4))
    tk.Checkbutton(af, text="Ses", variable=ses_var, bg=PANEL, fg=METIN,
                   selectcolor=KOYU, activebackground=PANEL,
                   activeforeground=METIN,
                   font=("Segoe UI", 9)).grid(row=0, column=5, padx=(8, 8))

    def tara_bas():
        if durum["calisiyor"]:
            return
        durum["calisiyor"] = True
        avci.kurallar = kurallar
        kuyruk.put("== takip başladı ==")

        def sarmal():
            try:
                adb = pzt._adb()
                if not adb:
                    kuyruk.put("X adb/root yok — tcpdump gerekiyor.")
                    return
                api = pzt.tb.Api()
                while durum["calisiyor"]:
                    d = api.get("/api/durum") or {}
                    p = d.get("proxy") or {}
                    if not (p.get("acik") and p.get("bagli")
                            and p.get("enjeksiyon")):
                        kuyruk.put("X Enjeksiyon kapıları kapalı.")
                        break
                    durum["tur"] += 1
                    kuyruk.put("— tur %d —" % durum["tur"])

                    def _geldi(vid, ad, esyalar):
                        durum["dukkan"] += 1
                        n = avci.dukkan(vid, ad, esyalar)
                        okunan_dukkanlar[vid] = (ad, esyalar)
                        # Fırsat olmasa bile OKUNDUĞUNU göster: yoksa panel
                        # boş duruyor ve bot çalışmıyor sanılıyor.
                        kok.after(0, lambda: okundu_yaz(
                            ad, len(esyalar), n, vid))

                    a = _Ayar(menzil_var.get() * 100, bekle_var.get(), 900)
                    pzt.tur_tara(api, adb, a, adlar, bulundu=_geldi,
                                 gunluk=kuyruk.put)
                    gecmis.kaydet()
                    if not surekli_var.get():
                        break
                    # Yeni turda aynı dükkânlar TEKRAR okunmalı ki fiyat
                    # değişimi yakalanabilsin; "gördüm" kaydını sıfırlıyoruz.
                    avci._gorulen = set()
                    kuyruk.put("tur bitti — yeniden başlıyorum")
                    time.sleep(2.0)
            except Exception as e:                       # noqa: BLE001
                kuyruk.put("HATA: %s: %s" % (type(e).__name__, e))
            finally:
                durum["calisiyor"] = False
                gecmis.kaydet()
                kuyruk.put("== durduruldu ==")

        threading.Thread(target=sarmal, daemon=True).start()

    def dur():
        durum["calisiyor"] = False

    def temizle():
        avci.temizle()
        akis.configure(state="normal")
        akis.delete("1.0", "end")
        akis.configure(state="disabled")
        bilgi.configure(text="fırsat yok")

    dug = tk.Frame(kok, bg=KOYU)
    dug.pack(fill="x", padx=12, pady=(0, 10))
    btn(dug, "▶ Takibi başlat", tara_bas, OK).pack(side="left")
    btn(dug, "■ Durdur", dur, HATA).pack(side="left", padx=8)
    btn(dug, "🧹 Listeyi temizle", temizle).pack(side="left")

    def tik():
        durum_et.configure(
            text=("tarıyor — tur %d, %d dükkân"
                  % (durum["tur"], durum["dukkan"]))
            if durum["calisiyor"] else "durduruldu",
            fg=OK if durum["calisiyor"] else SOLUK)
        while True:
            try:
                log_yaz(kuyruk.get_nowait())
            except queue.Empty:
                break
        kok.after(250, tik)

    kural_yukle()
    kurallari_yaz()
    avci.kurallar = kurallar
    log_yaz("Eşya tablosu: %d eşya   |   fiyat geçmişi: %d eşya"
            % (len(adlar.tablo), len(gecmis.tablo)))
    log_yaz("İzleme listesine kural ekle, pazara git, kapıları aç, "
            "'Takibi başlat' de.")
    log_yaz("HEDEF = kuralına uyan.  UCUZLADI = gördüğüm en düşük fiyatın "
            "altına indi.  Satın alma YOK.")
    tik()
    kok.mainloop()


if __name__ == "__main__":
    _main()
