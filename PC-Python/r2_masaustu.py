"""
R2 Panel — Masaüstü Kontrol Paneli
==================================

APK içindeki ApiSunucu'ya (varsayılan :30200) HTTP ile bağlanır.

    python r2_masaustu.py

Bağlanma yolları
----------------
1) USB / emülatör (önerilen):  "adb forward" düğmesine bas, sonra Bağlan.
2) Aynı Wi-Fi ağı:  adres alanına telefonun IP'sini yaz.
"""

import http.client
import json
import math
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from tkinter import messagebox, ttk

# ─── Renkler ───────────────────────────────────────────────────────────
KOYU  = "#0e0f13"
PANEL = "#171922"
CIZGI = "#262a36"
METIN = "#e6e8ef"
SOLUK = "#9aa0b4"
VURGU = "#33aaff"
UYARI = "#ffd166"
HATA  = "#e05050"
OK    = "#00c878"
ENJEKTE   = "#ff44aa"   # bot`un enjekte ettigi konum
ESYA      = "#7fd4ff"   # yerdeki esya
ESYA_YANG = "#ffcc33"   # Yang (para)

# varlık tipi → (renk, kısa ad)
TIPLER = {
    0:  ("#ff6b6b", "CANAVAR"),
    1:  ("#4dd0e1", "NPC"),
    2:  ("#ffd166", "METİN"),
    3:  ("#a78bfa", "GEÇİŞ"),
    4:  ("#6b7280", "KAPI"),
    5:  ("#6b7280", "BİNA"),
    6:  ("#00c878", "OYUNCU"),
    8:  ("#c084fc", "AT"),
    9:  ("#374151", "İŞARET"),
    -1: ("#9aa0b4", "?"),
}

VARSAYILAN_ADRES = "127.0.0.1:30200"
LOG_MAX_SATIR   = 600   # konsol en fazla bu kadar satır tutar


# ─── ADB yolu ──────────────────────────────────────────────────────────
def _adb_bul():
    if os.environ.get("ADB_YOLU"):
        return os.environ["ADB_YOLU"]
    adaylar = [
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%ProgramFiles%\Android\platform-tools\adb.exe"),
        r"C:\Android\platform-tools\adb.exe",
        "/usr/bin/adb",
        "/usr/local/bin/adb",
    ]
    for p in adaylar:
        if os.path.isfile(p):
            return p
    return "adb"

ADB = _adb_bul()


# ─── HTTP istemcisi (keep-alive, thread-local bağlantı) ───────────────
class Api:
    def __init__(self):
        self.adres       = VARSAYILAN_ADRES
        self.token       = ""
        self.zaman_asimi = 0.8   # localhost için 0.8s yeterli
        self.son_hata    = ""
        self._yerel      = threading.local()  # her thread kendi bağlantısını tutar

    def _baglanti(self):
        """Thread-local persistent HTTP bağlantısı döner."""
        conn = getattr(self._yerel, "conn", None)
        host = self.adres
        if conn is None or getattr(self._yerel, "host", None) != host:
            if conn:
                try: conn.close()
                except Exception: pass
            self._yerel.host = host
            self._yerel.conn = http.client.HTTPConnection(host, timeout=self.zaman_asimi)
        return self._yerel.conn

    def _baglantiyiSifirla(self):
        conn = getattr(self._yerel, "conn", None)
        if conn:
            try: conn.close()
            except Exception: pass
        self._yerel.conn = None

    def _sorgu(self, params):
        p = dict(params or {})
        if self.token:
            p["t"] = self.token
        return ("?" + urllib.parse.urlencode(p)) if p else ""

    def cagir(self, yol, **params):
        for deneme in range(2):
            try:
                conn = self._baglanti()
                basliklar = {"Connection": "keep-alive"}
                if self.token:
                    basliklar["X-R2-Token"] = self.token
                conn.request("GET", yol + self._sorgu(params), headers=basliklar)
                r = conn.getresponse()
                ham = r.read().decode("utf-8", "replace")
                self.son_hata = ""
                return json.loads(ham)
            except Exception as e:
                self._baglantiyiSifirla()
                if deneme == 1:
                    self.son_hata = type(e).__name__
        return None

    def gonder(self, yol, govde, **params):
        veri = govde.encode("utf-8")
        for deneme in range(2):
            try:
                conn = self._baglanti()
                basliklar = {
                    "Content-Type": "application/json",
                    "Content-Length": str(len(veri)),
                    "Connection": "keep-alive",
                }
                if self.token:
                    basliklar["X-R2-Token"] = self.token
                conn.request("POST", yol + self._sorgu(params), body=veri, headers=basliklar)
                r = conn.getresponse()
                ham = r.read().decode("utf-8", "replace")
                self.son_hata = ""
                return json.loads(ham)
            except Exception as e:
                self._baglantiyiSifirla()
                if deneme == 1:
                    self.son_hata = type(e).__name__
        return None


# ─── Radar ─────────────────────────────────────────────────────────────
class Radar(tk.Canvas):
    def __init__(self, ana, tiklama_cb):
        super().__init__(ana, bg=KOYU, highlightthickness=0)
        self.tiklama_cb  = tiklama_cb
        self.zoom        = 0.35
        self.durum       = {}
        self.varliklar   = []
        self.esyalar     = []
        self.rota        = None
        self.rota_indeks = -1
        self.isim_acik   = True
        self.bind("<Button-1>",    self._tikla)
        self.bind("<MouseWheel>",  self._tekerlek)
        self.bind("<Button-4>",    lambda e: self.yakinlastir(1.25))
        self.bind("<Button-5>",    lambda e: self.yakinlastir(0.8))
        self.bind("<Configure>",   lambda e: self.ciz())

    def _merkez(self):
        return self.winfo_width() / 2, self.winfo_height() / 2

    def _oyuncu_m(self):
        k = self.durum.get("konum") or {}
        return float(k.get("mx", 0.0)), float(k.get("my", 0.0))

    def m2p(self, mx, my):
        cx, cy = self._merkez()
        px, py = self._oyuncu_m()
        return cx + (mx - px) * self.zoom, cy - (my - py) * self.zoom

    def p2ham(self, sx, sy):
        cx, cy = self._merkez()
        px, py = self._oyuncu_m()
        mx = px + (sx - cx) / self.zoom
        my = py - (sy - cy) / self.zoom
        return int(round(mx * 100)), int(round(-my * 100))

    def yakinlastir(self, k):
        self.zoom = max(0.02, min(6.0, self.zoom * k))
        self.ciz()

    def _tekerlek(self, e):
        self.yakinlastir(1.25 if e.delta > 0 else 0.8)

    def _tikla(self, e):
        self.tiklama_cb(*self.p2ham(e.x, e.y))

    def ciz(self):
        self.delete("all")
        g, y = self.winfo_width(), self.winfo_height()
        if g < 10 or y < 10:
            return
        cx, cy = g / 2, y / 2

        # mesafe halkaları
        for metre in (10, 25, 50, 100, 200, 400):
            r = metre * self.zoom
            if r < 12 or r > max(g, y):
                continue
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=CIZGI)
            self.create_text(cx + 4, cy - r + 8, text="%d m" % metre,
                             fill=CIZGI, anchor="w", font=("Consolas", 8))
        self.create_line(cx, 0, cx, y, fill=CIZGI)
        self.create_line(0, cy, g, cy, fill=CIZGI)

        # rota çizgisi
        if self.rota and self.rota.get("noktalar"):
            noktalar = self.rota["noktalar"]
            ekran = [self.m2p(n.get("mx", 0), n.get("my", 0)) for n in noktalar]
            if len(ekran) > 1:
                duz = [k for xy in ekran for k in xy]
                if self.rota.get("dongusel") and len(ekran) > 2:
                    duz += list(ekran[0])
                self.create_line(*duz, fill=VURGU, width=1, dash=(4, 3))
            for i, (sx, sy) in enumerate(ekran):
                renk = UYARI if i == self.rota_indeks else VURGU
                self.create_rectangle(sx - 3, sy - 3, sx + 3, sy + 3,
                                      outline=renk, fill=KOYU)
                self.create_text(sx + 7, sy - 7, text=str(i + 1), fill=renk,
                                 anchor="w", font=("Consolas", 8))

        # yerdeki eşyalar (varlıkların ALTINDA kalsınlar)
        for e in self.esyalar:
            sx, sy = self.m2p(e.get("mx", 0), e.get("my", 0))
            if sx < -40 or sy < -40 or sx > g + 40 or sy > y + 40:
                continue
            yang = e.get("yang", False)
            renk = ESYA_YANG if yang else ESYA
            # küçük elmas: eşyaları varlık dairelerinden ayırır
            self.create_polygon(sx, sy - 4, sx + 4, sy, sx, sy + 4, sx - 4, sy,
                                fill=renk, outline="")
            if self.isim_acik and not yang:
                ad = e.get("ad", "")
                if ad:
                    self.create_text(sx + 6, sy, text=ad, fill=renk,
                                     anchor="w", font=("Consolas", 7))

        # varlıklar
        hedef = (self.durum.get("konum") or {}).get("hedef", 0)
        for v in self.varliklar:
            tip  = v.get("tip", -1)
            renk, _ = TIPLER.get(tip, TIPLER[-1])
            can  = v.get("can", -1)
            oldu = (can == 0)
            goster_renk = "#444455" if oldu else renk

            sx, sy = self.m2p(v.get("mx", 0), v.get("my", 0))
            if sx < -40 or sy < -40 or sx > g + 40 or sy > y + 40:
                continue

            r = 4 if tip in (0, 2) else 3
            self.create_oval(sx - r, sy - r, sx + r, sy + r,
                             fill=goster_renk, outline="")
            if v.get("vid") == hedef:
                self.create_oval(sx - 8, sy - 8, sx + 8, sy + 8, outline=UYARI)
            if self.isim_acik and tip in (0, 1, 2, 6) and not oldu:
                isim = v.get("ad", "")
                if isim:
                    self.create_text(sx + 6, sy, text=isim, fill=renk,
                                     anchor="w", font=("Consolas", 8))


        # ── enjekte edilen konum (bot ışınlaması) ──
        # Radar oyuncuyu HEP merkeze çizer; ışınlanma başka türlü görünmez
        # (nokta durur, dünya kayar). Bu işaret olmadan wait-hack'in
        # çalışıp çalışmadığı anlaşılamıyor.
        k = self.durum.get("konum") or {}
        yas = k.get("enjekteYas", -1)
        if isinstance(yas, (int, float)) and 0 <= yas <= 3000:
            emx, emy = k.get("enjekteMx", 0), k.get("enjekteMy", 0)
            if emx or emy:
                ex, ey = self.m2p(emx, emy)
                if -60 < ex < g + 60 and -60 < ey < y + 60:
                    self.create_oval(ex - 10, ey - 10, ex + 10, ey + 10,
                                     outline=ENJEKTE, width=2)
                    self.create_line(ex - 14, ey, ex + 14, ey, fill=ENJEKTE)
                    self.create_line(ex, ey - 14, ex, ey + 14, fill=ENJEKTE)
                    self.create_text(ex + 17, ey, text="enjekte", fill=ENJEKTE,
                                     anchor="w", font=("Consolas", 8))

        # oyuncu merkezi + yön oku
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=OK, outline="")
        yon = (self.durum.get("konum") or {}).get("yon", 0)
        a = math.radians(yon)
        self.create_line(cx, cy,
                         cx + math.cos(a) * 18,
                         cy - math.sin(a) * 18,
                         fill=OK, width=2)

        # alt sol bilgi
        self.create_text(8, y - 8, anchor="sw", fill=SOLUK, font=("Consolas", 8),
                         text="zoom %.2f px/m  •  tekerlek: yakınlaştır" % self.zoom)


# ─── Ana pencere ───────────────────────────────────────────────────────
class Uygulama(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("R2 Panel")
        self.configure(bg=KOYU)
        self.geometry("1200x780")
        self.minsize(900, 600)

        self.api          = Api()
        self.bagli        = False
        self.kuyruk_ui    = queue.Queue()
        self.tiklama_modu = tk.StringVar(value="bak")
        self.durum        = {}
        self.varliklar    = []
        self.esyalar      = []
        self.rotalar      = {}
        self.aktif_rota   = None
        self.akis_acik    = False
        self._varlik_bos_sayac  = 0
        self._hata_sayac        = 0   # ardışık bağlantı hatası sayısı
        self._filtre_tip        = tk.StringVar(value="TÜMÜ")

        self._stil()
        self._ust_serit()
        self._govde()
        self._alt_serit()

        self.after(30, self._ui_kuyrugu_isle)  # 30ms → ~33fps UI güncelleme
        threading.Thread(target=self._yoklayici_hizli, daemon=True).start()
        threading.Thread(target=self._yoklayici,       daemon=True).start()

    # ── stil ──
    def _stil(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=KOYU, foreground=METIN, fieldbackground=PANEL)
        s.configure("TNotebook", background=KOYU, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=SOLUK,
                    padding=(14, 6), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", VURGU)],
              foreground=[("selected", KOYU)])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=METIN, borderwidth=0, rowheight=20)
        s.configure("Treeview.Heading", background=CIZGI, foreground=SOLUK,
                    borderwidth=0)
        s.map("Treeview",
              background=[("selected", VURGU)],
              foreground=[("selected", KOYU)])
        s.configure("Vertical.TScrollbar", background=CIZGI,
                    troughcolor=PANEL, arrowcolor=SOLUK)
        s.configure("TFrame", background=KOYU)
        s.configure("TLabel", background=KOYU, foreground=METIN)
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                    foreground=METIN, selectbackground=VURGU)

    def _dugme(self, ana, metin, komut, renk=PANEL, gen=None):
        b = tk.Button(ana, text=metin, command=komut,
                      bg=renk,
                      fg=KOYU if renk in (VURGU, OK, UYARI) else METIN,
                      activebackground=VURGU, activeforeground=KOYU,
                      relief="flat", bd=0, padx=10, pady=4,
                      font=("Segoe UI", 9), cursor="hand2")
        if gen:
            b.configure(width=gen)
        return b

    def _scrolllu_liste(self, ana, sutunlar, genislikler, yukseklik=18):
        """Scrollbar'lı Treeview döner."""
        cerceve = tk.Frame(ana, bg=KOYU)
        agac = ttk.Treeview(cerceve, columns=sutunlar, show="headings",
                            height=yukseklik)
        for s, g in zip(sutunlar, genislikler):
            agac.heading(s, text=s.upper())
            agac.column(s, width=g, anchor="w")
        sb = ttk.Scrollbar(cerceve, orient="vertical", command=agac.yview)
        agac.configure(yscrollcommand=sb.set)
        agac.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return cerceve, agac

    # ── üst şerit: bağlantı ──
    def _ust_serit(self):
        c = tk.Frame(self, bg=PANEL)
        c.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(c, text="Adres", bg=PANEL, fg=SOLUK).pack(side="left", padx=(10, 4))
        self.adres_var = tk.StringVar(value=VARSAYILAN_ADRES)
        tk.Entry(c, textvariable=self.adres_var, width=22, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat").pack(side="left", pady=6)

        tk.Label(c, text="Token", bg=PANEL, fg=SOLUK).pack(side="left", padx=(12, 4))
        self.token_var = tk.StringVar(value="")
        tk.Entry(c, textvariable=self.token_var, width=14, bg=KOYU, fg=METIN,
                 show="•", insertbackground=METIN, relief="flat").pack(side="left")

        self._dugme(c, "adb forward", self.adb_forward).pack(side="left", padx=8)
        self.bagla_dugme = self._dugme(c, "Bağlan", self.baglan_degistir, VURGU)
        self.bagla_dugme.pack(side="left", padx=4)

        self.bagli_etiket = tk.Label(c, text="● bağlı değil", bg=PANEL, fg=HATA,
                                     font=("Segoe UI", 9, "bold"))
        self.bagli_etiket.pack(side="left", padx=12)

        self.enj_etiket = tk.Label(c, text="", bg=PANEL, fg=SOLUK)
        self.enj_etiket.pack(side="right", padx=12)

    # ── gövde ──
    def _govde(self):
        kok = tk.Frame(self, bg=KOYU)
        kok.pack(fill="both", expand=True, padx=8, pady=4)

        # Sol: radar
        sol = tk.Frame(kok, bg=PANEL)
        sol.pack(side="left", fill="both", expand=True, padx=(0, 6))

        arac = tk.Frame(sol, bg=PANEL)
        arac.pack(fill="x", padx=6, pady=6)
        for deger, etiket in (("bak", "Bak"), ("git", "Git"), ("rota", "Rota ekle")):
            tk.Radiobutton(arac, text=etiket, value=deger,
                           variable=self.tiklama_modu,
                           bg=PANEL, fg=METIN, selectcolor=KOYU,
                           activebackground=PANEL, activeforeground=VURGU,
                           relief="flat", indicatoron=False, padx=10, pady=3,
                           font=("Segoe UI", 9)).pack(side="left", padx=2)
        self.isim_var = tk.BooleanVar(value=True)
        tk.Checkbutton(arac, text="İsim", variable=self.isim_var,
                       bg=PANEL, fg=METIN, selectcolor=KOYU,
                       activebackground=PANEL,
                       command=self._radar_tazele).pack(side="left", padx=10)
        self._dugme(arac, "−", lambda: self.radar.yakinlastir(0.8)).pack(side="right", padx=2)
        self._dugme(arac, "+", lambda: self.radar.yakinlastir(1.25)).pack(side="right", padx=2)

        self.radar = Radar(sol, self.haritaya_tiklandi)
        self.radar.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Sağ: sekmeler
        sag = tk.Frame(kok, bg=KOYU, width=440)
        sag.pack(side="right", fill="both")
        sag.pack_propagate(False)

        self.defter = ttk.Notebook(sag)
        self.defter.pack(fill="both", expand=True)
        self._sekme_durum()
        self._sekme_varliklar()
        self._sekme_rota()
        self._sekme_kuyruk()
        self._sekme_paket()
        self._sekme_konsol()

    # ── sekme: Durum ──
    def _sekme_durum(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Durum")

        self.durum_yazi = tk.Text(f, bg=PANEL, fg=METIN, relief="flat",
                                  font=("Consolas", 9), padx=10, pady=10,
                                  state="disabled")
        self.durum_yazi.pack(fill="both", expand=True, padx=4, pady=4)

        kutu = tk.LabelFrame(f, text=" Servisler ", bg=KOYU, fg=SOLUK,
                             bd=1, relief="solid", labelanchor="nw")
        kutu.pack(fill="x", padx=4, pady=(0, 4))
        satir = tk.Frame(kutu, bg=KOYU)
        satir.pack(fill="x", padx=6, pady=6)
        for ad, etiket in (("panel", "Panel"), ("paket", "Paket"),
                           ("proxy", "Proxy"), ("kuyruk", "Kuyruk")):
            self._dugme(satir, etiket,
                        lambda a=ad: self.servis_degistir(a)).pack(side="left", padx=3)

        kutu2 = tk.LabelFrame(f, text=" Gönderim ", bg=KOYU, fg=SOLUK,
                              bd=1, relief="solid", labelanchor="nw")
        kutu2.pack(fill="x", padx=4, pady=(0, 4))
        satir2 = tk.Frame(kutu2, bg=KOYU)
        satir2.pack(fill="x", padx=6, pady=6)
        self._dugme(satir2, "Enjeksiyon aç/kapat",
                    self.enjeksiyon_degistir, UYARI).pack(side="left", padx=3)
        self._dugme(satir2, "Kanal: Log ⇄ Proxy",
                    self.kanal_degistir).pack(side="left", padx=3)

    # ── sekme: Varlıklar ──
    def _sekme_varliklar(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Varlıklar")

        # Filtre satırı
        filtre_satir = tk.Frame(f, bg=KOYU)
        filtre_satir.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(filtre_satir, text="Filtre:", bg=KOYU, fg=SOLUK).pack(side="left")
        tip_secenekler = ["TÜMÜ"] + [v for _, v in sorted(TIPLER.items()) if v != "?"]
        self.filtre_combo = ttk.Combobox(filtre_satir, textvariable=self._filtre_tip,
                                         values=tip_secenekler, state="readonly", width=12)
        self.filtre_combo.pack(side="left", padx=6)
        self.filtre_combo.bind("<<ComboboxSelected>>", lambda _: self._varliklar_tazele())
        self.varlik_sayac = tk.Label(filtre_satir, text="", bg=KOYU, fg=SOLUK,
                                     font=("Consolas", 9))
        self.varlik_sayac.pack(side="left", padx=10)

        # Liste + scrollbar
        cerceve, self.varlik_agac = self._scrolllu_liste(
            f,
            sutunlar=("tip", "ad", "m", "can", "vid"),
            genislikler=(80, 160, 45, 40, 75),
            yukseklik=18)
        cerceve.pack(fill="both", expand=True, padx=4, pady=4)

        # Eylem butoanları
        satir = tk.Frame(f, bg=KOYU)
        satir.pack(fill="x", padx=4, pady=4)
        self._dugme(satir, "Hedefle",
                    lambda: self.secili_varlik_komut("hedefle")).pack(side="left", padx=3)
        self._dugme(satir, "Saldır",
                    lambda: self.secili_varlik_komut("saldir")).pack(side="left", padx=3)
        self._dugme(satir, "Yanına git",
                    self.secili_varliga_git).pack(side="left", padx=3)
        self._dugme(satir, "Rotaya ekle",
                    self.secili_varligi_rotaya_ekle).pack(side="left", padx=3)

    # ── sekme: Rota ──
    def _sekme_rota(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Rota")

        ust = tk.Frame(f, bg=KOYU)
        ust.pack(fill="x", padx=4, pady=4)
        tk.Label(ust, text="Aktif rota", bg=KOYU, fg=SOLUK).pack(side="left")
        self.rota_secim = ttk.Combobox(ust, state="readonly", width=22)
        self.rota_secim.pack(side="left", padx=6)
        self.rota_secim.bind("<<ComboboxSelected>>", self.rota_secildi)
        self._dugme(ust, "Yeni", self.rota_yeni).pack(side="left", padx=3)
        self._dugme(ust, "Sil",  self.rota_sil).pack(side="left", padx=3)

        cerceve, self.rota_agac = self._scrolllu_liste(
            f,
            sutunlar=("no", "x", "y", "bekle"),
            genislikler=(40, 90, 90, 70),
            yukseklik=14)
        cerceve.pack(fill="both", expand=True, padx=4, pady=4)

        satir = tk.Frame(f, bg=KOYU)
        satir.pack(fill="x", padx=4, pady=4)
        self._dugme(satir, "Buraya nokta",
                    self.rota_nokta_buraya).pack(side="left", padx=3)
        self._dugme(satir, "Noktayı sil",
                    self.rota_nokta_sil).pack(side="left", padx=3)
        self._dugme(satir, "Boşalt",
                    self.rota_bosalt).pack(side="left", padx=3)

        satir2 = tk.Frame(f, bg=KOYU)
        satir2.pack(fill="x", padx=4, pady=(0, 6))
        self.takip_dugme = self._dugme(satir2, "Takibi başlat", self.rota_takip, OK)
        self.takip_dugme.pack(side="left", padx=3)
        self.rota_durum = tk.Label(satir2, text="-", bg=KOYU, fg=SOLUK,
                                   font=("Consolas", 9))
        self.rota_durum.pack(side="left", padx=10)

    # ── sekme: Kuyruk ──
    def _sekme_kuyruk(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Kuyruk")

        satir = tk.Frame(f, bg=KOYU)
        satir.pack(fill="x", padx=4, pady=4)
        self._dugme(satir, "Duraklat/Devam",
                    self.kuyruk_duraklat).pack(side="left", padx=3)
        self._dugme(satir, "Boşalt",
                    self.kuyruk_bosalt).pack(side="left", padx=3)
        tk.Label(satir, text="Aralık", bg=KOYU, fg=SOLUK).pack(side="left", padx=(12, 4))
        self.aralik_secim = ttk.Combobox(satir, state="readonly", width=7,
                                         values=("150", "350", "700", "1500"))
        self.aralik_secim.set("350")
        self.aralik_secim.pack(side="left")
        self.aralik_secim.bind("<<ComboboxSelected>>", self.kuyruk_aralik)

        cerceve = tk.Frame(f, bg=KOYU)
        cerceve.pack(fill="both", expand=True, padx=4, pady=4)
        self.kuyruk_yazi = tk.Text(cerceve, bg=PANEL, fg=METIN, relief="flat",
                                   font=("Consolas", 9), padx=8, pady=8,
                                   state="disabled")
        sb = ttk.Scrollbar(cerceve, orient="vertical",
                           command=self.kuyruk_yazi.yview)
        self.kuyruk_yazi.configure(yscrollcommand=sb.set)
        self.kuyruk_yazi.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ── sekme: Paket ──
    def _sekme_paket(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Paket")

        satir = tk.Frame(f, bg=KOYU)
        satir.pack(fill="x", padx=4, pady=4)
        self.paket_akis = tk.BooleanVar(value=False)
        tk.Checkbutton(satir, text="Canlı akış", variable=self.paket_akis,
                       bg=KOYU, fg=METIN, selectcolor=PANEL,
                       activebackground=KOYU,
                       command=self._akis_degisti).pack(side="left")
        self.paket_hex = tk.BooleanVar(value=False)
        tk.Checkbutton(satir, text="Hex göster", variable=self.paket_hex,
                       bg=KOYU, fg=METIN, selectcolor=PANEL,
                       activebackground=KOYU).pack(side="left", padx=10)

        cerceve = tk.Frame(f, bg=KOYU)
        cerceve.pack(fill="both", expand=True, padx=4, pady=4)
        self.paket_yazi = tk.Text(cerceve, bg=PANEL, fg=SOLUK, relief="flat",
                                  font=("Consolas", 8), padx=8, pady=8,
                                  wrap="none", state="disabled")
        sb_y = ttk.Scrollbar(cerceve, orient="vertical",
                              command=self.paket_yazi.yview)
        sb_x = ttk.Scrollbar(cerceve, orient="horizontal",
                              command=self.paket_yazi.xview)
        self.paket_yazi.configure(yscrollcommand=sb_y.set,
                                  xscrollcommand=sb_x.set)
        sb_y.pack(side="right",  fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.paket_yazi.pack(side="left", fill="both", expand=True)
        self.paket_yazi.tag_configure("out", foreground=VURGU)
        self.paket_yazi.tag_configure("in",  foreground=OK)

    def _akis_degisti(self):
        self.akis_acik = self.paket_akis.get()

    # ── sekme: Konsol ──
    def _sekme_konsol(self):
        f = tk.Frame(self.defter, bg=KOYU)
        self.defter.add(f, text="Konsol")

        tk.Label(f, text="Ham hex paket (ör. 07 01 00 12 …)",
                 bg=KOYU, fg=SOLUK, anchor="w").pack(fill="x", padx=6, pady=(8, 2))
        self.hex_var = tk.StringVar()
        tk.Entry(f, textvariable=self.hex_var, bg=PANEL, fg=METIN,
                 insertbackground=METIN, relief="flat",
                 font=("Consolas", 10)).pack(fill="x", padx=6, ipady=5)
        satir = tk.Frame(f, bg=KOYU)
        satir.pack(fill="x", padx=6, pady=6)
        self._dugme(satir, "Enjekte et",
                    self.hex_enjekte, UYARI).pack(side="left")
        self._dugme(satir, "Dur paketi",
                    self.dur_gonder).pack(side="left", padx=6)
        self._dugme(satir, "Temizle",
                    self._konsol_temizle).pack(side="right", padx=6)

        cerceve = tk.Frame(f, bg=KOYU)
        cerceve.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.konsol_yazi = tk.Text(cerceve, bg=PANEL, fg=METIN, relief="flat",
                                   font=("Consolas", 9), padx=8, pady=8,
                                   state="disabled")
        sb = ttk.Scrollbar(cerceve, orient="vertical",
                           command=self.konsol_yazi.yview)
        self.konsol_yazi.configure(yscrollcommand=sb.set)
        self.konsol_yazi.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _alt_serit(self):
        c = tk.Frame(self, bg=PANEL)
        c.pack(fill="x", padx=8, pady=(0, 8))
        self.alt_etiket = tk.Label(c, text="hazır", bg=PANEL, fg=SOLUK,
                                   anchor="w", font=("Consolas", 9))
        self.alt_etiket.pack(fill="x", padx=10, pady=4)

    # ─── günlük ───────────────────────────────────────────────────────
    def log(self, metin, renk=None):
        def yaz():
            w = self.konsol_yazi
            w.configure(state="normal")
            # satır sınırı
            satirlar = int(w.index("end-1c").split(".")[0])
            if satirlar > LOG_MAX_SATIR:
                w.delete("1.0", "%d.0" % (satirlar - LOG_MAX_SATIR))
            w.insert("end", time.strftime("%H:%M:%S  ") + metin + "\n")
            w.see("end")
            w.configure(state="disabled")
            self.alt_etiket.configure(text=metin[:120], fg=renk or SOLUK)
        self.kuyruk_ui.put(yaz)

    def _konsol_temizle(self):
        self.konsol_yazi.configure(state="normal")
        self.konsol_yazi.delete("1.0", "end")
        self.konsol_yazi.configure(state="disabled")

    # ─── bağlantı ─────────────────────────────────────────────────────
    def adb_forward(self):
        def is_():
            try:
                p = subprocess.run(
                    [ADB, "forward", "tcp:30200", "tcp:30200"],
                    capture_output=True, text=True, timeout=15)
                if p.returncode == 0:
                    self.kuyruk_ui.put(
                        lambda: self.adres_var.set(VARSAYILAN_ADRES))
                    self.log("adb forward kuruldu (tcp:30200)", OK)
                else:
                    self.log("adb forward başarısız: " +
                             (p.stderr or "").strip(), HATA)
            except FileNotFoundError:
                self.log("adb bulunamadı — ADB yolu: %s" % ADB, HATA)
            except Exception as e:
                self.log("adb hatası: %s" % type(e).__name__, HATA)
        threading.Thread(target=is_, daemon=True).start()

    def baglan_degistir(self):
        if self.bagli:
            self.bagli = False
            self._hata_sayac = 0
            self.bagla_dugme.configure(text="Bağlan", bg=VURGU)
            self.bagli_etiket.configure(text="● bağlı değil", fg=HATA)
            self.log("bağlantı kesildi")
            return

        self.api.adres = self.adres_var.get().strip() or VARSAYILAN_ADRES
        self.api.token = self.token_var.get().strip()
        self.api._baglantiyiSifirla()  # eski keep-alive bağlantısını temizle
        self.bagli = True
        self._hata_sayac = 0
        self.bagla_dugme.configure(text="Kes", bg=HATA)
        self.log("bağlanılıyor: %s" % self.api.adres)

        # 127.x.x.x adresinde adb forward otomatik dene
        if self.api.adres.startswith("127."):
            threading.Thread(target=self._adb_forward_sessiz,
                             daemon=True).start()

    def _adb_forward_sessiz(self):
        try:
            subprocess.run(
                [ADB, "forward", "tcp:30200", "tcp:30200"],
                capture_output=True, timeout=10)
        except Exception:
            pass

    # ─── HIZLI thread: sadece varlıklar, 200 ms'de bir ─────────────────
    def _yoklayici_hizli(self):
        bos_sayac = 0
        esya_sayac = 0
        while True:
            try:
                time.sleep(0.05)
                if not self.bagli:
                    continue
                ham = self.api.cagir("/api/varliklar", n=80)
                if not isinstance(ham, list):
                    continue                         # hata → pas geç, eski liste kalır
                if len(ham) == 0:
                    bos_sayac += 1
                    if bos_sayac < 3:               # 3 ardışık boş gelmeden temizleme
                        continue
                else:
                    bos_sayac = 0
                varliklar = ham
                # Eşyalar varlıklardan yavaş değişir: her 4. turda çek (~5 Hz)
                esyalar = None
                esya_sayac += 1
                if esya_sayac >= 4:
                    esya_sayac = 0
                    e = self.api.cagir("/api/esyalar", n=80)
                    if isinstance(e, list):
                        esyalar = e
                self.kuyruk_ui.put(
                    lambda v=varliklar, s=esyalar: self._varliklar_guncelle(v, s))
            except Exception as e:
                self.kuyruk_ui.put(
                    lambda err=str(e): self.log("hızlı-yoklayıcı hatası: " + err, HATA))
                time.sleep(1)

    def _varliklar_guncelle(self, varliklar, esyalar=None):
        """Sadece varlik/esya listesi + radar günceller; durum sekmesine dokunmaz."""
        self.varliklar = varliklar
        if esyalar is not None:
            self.esyalar = esyalar
        self._varliklar_tazele()
        self._radar_tazele()

    # ─── NORMAL thread: durum + rotalar + kuyruk + log, 600 ms'de bir ──
    def _yoklayici(self):
        sayac = 0
        while True:
            try:
                time.sleep(0.60)
                if not self.bagli:
                    continue
                sayac += 1

                durum = self.api.cagir("/api/durum")
                if durum is None:
                    self._hata_sayac += 1
                    self.kuyruk_ui.put(
                        lambda h=self.api.son_hata, n=self._hata_sayac:
                        self._bagli_isaret(False, h, n))
                    continue

                self._hata_sayac = 0
                rotalar = self.api.cagir("/api/rotalar") if sayac % 3 == 1 else None
                kuyruk  = self.api.cagir("/api/kuyruk", n=15) if sayac % 2 == 0 else None
                log_    = self.api.cagir("/api/log", n=30) if self.akis_acik else None

                self.kuyruk_ui.put(
                    lambda d=durum, r=rotalar, k=kuyruk, g=log_:
                    self._durum_guncelle(d, r, k, g))

            except Exception as e:
                self.kuyruk_ui.put(
                    lambda err=str(e): self.log("yoklayıcı hatası: " + err, HATA))
                time.sleep(2)

    def _durum_guncelle(self, durum, rotalar, kuyruk, log):
        """Sadece durum/rota/kuyruk/log günceller; varlık listesine dokunmaz."""
        self._bagli_isaret(True)
        self.durum = durum or {}
        if isinstance(rotalar, dict) and rotalar.get("ok"):
            self.rotalar    = {r["ad"]: r for r in rotalar.get("rotalar", [])}
            self.aktif_rota = rotalar.get("aktif", "")
            self._rota_tazele()
        if isinstance(kuyruk, dict):
            self._kuyruk_tazele(kuyruk)
        if isinstance(log, list):
            self._paket_tazele(log)
        self._durum_tazele()

    def _bagli_isaret(self, iyi, hata="", hata_sayac=0):
        if iyi:
            self.bagli_etiket.configure(text="● bağlı", fg=OK)
        else:
            goster = "● hata: %s" % hata
            if hata_sayac > 1:
                goster += " (%dx)" % hata_sayac
            self.bagli_etiket.configure(text=goster, fg=HATA)

    # ─── görünüm tazeleme ─────────────────────────────────────────────
    def _durum_tazele(self):
        d  = self.durum
        k  = d.get("konum",    {}) or {}
        p  = d.get("proxy",    {}) or {}
        s  = d.get("sayac",    {}) or {}
        vr = d.get("varlik",   {}) or {}
        kt = d.get("katalog",  {}) or {}
        kq = d.get("kuyruk",   {}) or {}
        sv = d.get("servisler",{}) or {}
        rt = d.get("rota",     {}) or {}

        def ac(b): return "açık" if b else "kapalı"

        satirlar = [
            "KONUM   %s" % (
                "%.0f, %.0f m" % (k.get("mx", 0), k.get("my", 0))
                if k.get("bilinir") else "bilinmiyor — paket/proxy açık mı?"),
            "        ham %s, %s     yön %s°     hedef #%s" % (
                k.get("x", 0), k.get("y", 0), k.get("yon", 0), k.get("hedef", 0)),
            "",
            "SERVİS  panel:%s  paket:%s  proxy:%s  kuyruk:%s" % (
                ac(sv.get("panel")), ac(sv.get("paket")),
                ac(sv.get("proxy")), ac(sv.get("kuyruk"))),
            "",
            "PROXY   %s" % p.get("durum", "-"),
            "        bağlı:%s  enjeksiyon:%s" % (
                ac(p.get("bagli")), ac(p.get("enjeksiyon"))),
            "        giden:%s  gelen:%s  enjekte:%s" % (
                p.get("giden", 0), p.get("gelen", 0), p.get("enjekte", 0)),
            "",
            "PAKET   toplam %s • giden %s • gelen %s" % (
                s.get("toplam", 0), s.get("giden", 0), s.get("gelen", 0)),
            "VARLIK  %s  (canavar %s, metin %s, npc %s, isimsiz %s)" % (
                vr.get("toplam", 0), vr.get("canavar", 0), vr.get("metin", 0),
                vr.get("npc", 0), vr.get("isimsiz", 0)),
            "KATALOG %s varlık / %s eşya" % (
                kt.get("varlik", 0), kt.get("esya", 0)),
            "",
            "KUYRUK  %s • bekleyen %s • aralık %s ms" % (
                "duraklatıldı" if kq.get("duraklatildi")
                else ("çalışıyor" if kq.get("calisiyor") else "durdu"),
                kq.get("bekleyen", 0), kq.get("aralik", 0)),
            "        kanal: %s%s" % (
                kq.get("kanal", "-"),
                "" if kq.get("kanalHazir") else "  (hazır değil)"),
            "        aktif: %s" % (kq.get("aktif") or "-"),
            "",
            "ROTA    %s  (%s nokta, %s. noktada)" % (
                rt.get("ad") or "yok", rt.get("boyut", 0),
                (rt.get("indeks", 0) or 0) + 1),
            "        %s" % rt.get("durum", "-"),
            "",
            "TİK     %s" % d.get("tik", 0),
        ]
        metin = "\n".join(satirlar)
        self.durum_yazi.configure(state="normal")
        self.durum_yazi.delete("1.0", "end")
        self.durum_yazi.insert("1.0", metin)
        self.durum_yazi.configure(state="disabled")

        enj = p.get("enjeksiyon")
        self.enj_etiket.configure(
            text=("ENJEKSİYON AÇIK" if enj else "enjeksiyon kapalı")
                 + "   •   kanal: " + str(kq.get("kanal", "-")),
            fg=HATA if enj else SOLUK)
        self.rota_durum.configure(text=rt.get("durum", "-"))
        self.takip_dugme.configure(
            text="Takibi durdur" if rt.get("calisiyor") else "Takibi başlat")

    def _varliklar_tazele(self):
        filtre = self._filtre_tip.get()
        secili = self.varlik_agac.selection()
        secili_vid = (self.varlik_agac.item(secili[0])["values"][4]
                      if secili else None)

        self.varlik_agac.delete(*self.varlik_agac.get_children())
        gosterilen = 0
        for v in self.varliklar:
            tip = v.get("tip", -1)
            _, tipad = TIPLER.get(tip, TIPLER[-1])
            if filtre != "TÜMÜ" and tipad != filtre:
                continue
            can  = v.get("can", -1)
            oldu = (can == 0)
            gosterilen += 1
            iid = self.varlik_agac.insert("", "end", values=(
                ("†" + tipad) if oldu else tipad,
                v.get("ad", ""),
                v.get("mesafe", 0),
                can if can >= 0 else "-",
                v.get("vid", 0)))
            if oldu:
                self.varlik_agac.item(iid, tags=("oldu",))
            if secili_vid is not None and str(v.get("vid")) == str(secili_vid):
                self.varlik_agac.selection_set(iid)

        self.varlik_agac.tag_configure("oldu", foreground="#666677")
        self.varlik_sayac.configure(
            text="%d / %d" % (gosterilen, len(self.varliklar)))

    def _rota_tazele(self):
        adlar = list(self.rotalar.keys())
        self.rota_secim.configure(values=adlar)
        if self.aktif_rota and self.rota_secim.get() != self.aktif_rota:
            self.rota_secim.set(self.aktif_rota)
        r = self.rotalar.get(self.aktif_rota or "")
        self.rota_agac.delete(*self.rota_agac.get_children())
        if not r:
            return
        for i, n in enumerate(r.get("noktalar", [])):
            self.rota_agac.insert("", "end", values=(
                i + 1,
                "%.0f" % n.get("mx", 0),
                "%.0f" % n.get("my", 0),
                "-" if not n.get("bekle")
                else "%.1f sn" % (n["bekle"] / 1000)))

    def _kuyruk_tazele(self, k):
        satirlar = ["BEKLEYEN"]
        for b in k.get("bekleyen", []):
            satirlar.append("  %2d. %s  [ö%s]" % (
                b.get("id", 0), b.get("ozet", ""), b.get("oncelik", 0)))
        if not k.get("bekleyen"):
            satirlar.append("  kuyruk boş")
        satirlar += ["", "SON YÜRÜTÜLENLER"]
        for g in k.get("gecmis", []):
            im = "✗" if g.get("durum") == "HATA" else "✓"
            satirlar.append("  %s %s  %s ms  %s" % (
                im, g.get("ozet", ""), g.get("sure", 0), g.get("sonuc", "")))
        self.kuyruk_yazi.configure(state="normal")
        self.kuyruk_yazi.delete("1.0", "end")
        self.kuyruk_yazi.insert("1.0", "\n".join(satirlar))
        self.kuyruk_yazi.configure(state="disabled")

    def _paket_tazele(self, log):
        self.paket_yazi.configure(state="normal")
        self.paket_yazi.delete("1.0", "end")
        for k in log:
            etiket = "out" if k.get("giden") else "in"
            self.paket_yazi.insert("end", k.get("basli", "") + "\n", etiket)
            if self.paket_hex.get():
                self.paket_yazi.insert("end", "    " + k.get("hex", "") + "\n")
        self.paket_yazi.configure(state="disabled")

    def _radar_tazele(self):
        self.radar.durum       = self.durum
        self.radar.varliklar   = self.varliklar
        self.radar.esyalar     = self.esyalar
        self.radar.rota        = self.rotalar.get(self.aktif_rota or "")
        self.radar.rota_indeks = (self.durum.get("rota") or {}).get("indeks", -1)
        self.radar.isim_acik   = self.isim_var.get()
        self.radar.ciz()

    def _ui_kuyrugu_isle(self):
        try:
            while True:
                self.kuyruk_ui.get_nowait()()
        except queue.Empty:
            pass
        except Exception as e:
            print("UI hatası:", e)
        self.after(30, self._ui_kuyrugu_isle)

    # ─── eylemler ─────────────────────────────────────────────────────
    def _cagir(self, yol, **params):
        if not self.bagli:
            self.log("önce bağlan", UYARI)
            return

        def is_():
            c = self.api.cagir(yol, **params)
            if c is None:
                self.log("%s → hata: %s" % (yol, self.api.son_hata), HATA)
            elif isinstance(c, dict) and c.get("ok") is False:
                self.log("%s → %s" % (yol, c.get("hata", "bilinmeyen hata")), UYARI)
            else:
                self.log("%s → tamam" % yol, OK)
        threading.Thread(target=is_, daemon=True).start()

    def haritaya_tiklandi(self, ham_x, ham_y):
        mod = self.tiklama_modu.get()
        if mod == "git":
            self._cagir("/api/komut", tip="yuru", x=ham_x, y=ham_y, tekil=1)
        elif mod == "rota":
            self._cagir("/api/rota/nokta", x=ham_x, y=ham_y)
        else:
            self.log("nokta: ham %d,%d  (%.0f, %.0f m)"
                     % (ham_x, ham_y, ham_x / 100.0, -ham_y / 100.0))

    def servis_degistir(self, ad):
        acik = (self.durum.get("servisler") or {}).get(ad, False)
        self._cagir("/api/servis", ad=ad, ac=0 if acik else 1)

    def enjeksiyon_degistir(self):
        acik = (self.durum.get("proxy") or {}).get("enjeksiyon", False)
        if not acik and not messagebox.askyesno(
                "Enjeksiyon",
                "Enjeksiyon açılacak.\nKuyruk ve konsol gerçekten oyuna paket gönderir.\nDevam?"):
            return
        self._cagir("/api/enjeksiyon", ac=0 if acik else 1)

    def kanal_degistir(self):
        simdiki = (self.durum.get("kuyruk") or {}).get("kanal", "")
        self._cagir("/api/kanal", ad="log" if "Proxy" in simdiki else "proxy")

    def _secili_vid(self):
        s = self.varlik_agac.selection()
        if not s:
            self.log("önce listeden bir varlık seç", UYARI)
            return None
        try:
            return int(self.varlik_agac.item(s[0])["values"][4])
        except (IndexError, ValueError):
            return None

    def _secili_varlik(self):
        vid = self._secili_vid()
        if vid is None:
            return None
        for v in self.varliklar:
            if v.get("vid") == vid:
                return v
        return None

    def secili_varlik_komut(self, tip):
        vid = self._secili_vid()
        if vid is not None:
            self._cagir("/api/komut", tip=tip, id=vid)

    def secili_varliga_git(self):
        v = self._secili_varlik()
        if not v:
            return
        # ham koordinat: x/y varsa kullan, yoksa mx/my'den hesapla
        x = v.get("x") or int(v.get("mx", 0) * 100)
        y = v.get("y") or int(v.get("my", 0) * 100)
        self._cagir("/api/komut", tip="yuru", x=x, y=y, tekil=1)

    def secili_varligi_rotaya_ekle(self):
        v = self._secili_varlik()
        if not v:
            return
        x = v.get("x") or int(v.get("mx", 0) * 100)
        y = v.get("y") or int(v.get("my", 0) * 100)
        self._cagir("/api/rota/nokta", x=x, y=y, etiket=v.get("ad", ""))

    def rota_secildi(self, _=None):
        ad = self.rota_secim.get()
        if ad:
            self._cagir("/api/rota/aktif", ad=ad)

    def rota_yeni(self):
        self._cagir("/api/rota/yeni")

    def rota_sil(self):
        ad = self.rota_secim.get()
        if ad and messagebox.askyesno("Rota sil", "'%s' silinsin mi?" % ad):
            self._cagir("/api/rota/sil", ad=ad)

    def rota_nokta_buraya(self):
        self._cagir("/api/rota/nokta")

    def rota_nokta_sil(self):
        s = self.rota_agac.selection()
        if not s:
            self.log("önce nokta seç", UYARI)
            return
        try:
            i = int(self.rota_agac.item(s[0])["values"][0]) - 1
            self._cagir("/api/rota/sil", i=i)
        except (IndexError, ValueError):
            pass

    def rota_bosalt(self):
        self._cagir("/api/rota/bosalt")

    def rota_takip(self):
        calisiyor = (self.durum.get("rota") or {}).get("calisiyor", False)
        self._cagir("/api/rota/takip", ac=0 if calisiyor else 1)

    def kuyruk_duraklat(self):
        d = (self.durum.get("kuyruk") or {}).get("duraklatildi", False)
        self._cagir("/api/kuyruk/ayar", duraklat=0 if d else 1)

    def kuyruk_bosalt(self):
        self._cagir("/api/kuyruk/ayar", temizle=1)

    def kuyruk_aralik(self, _=None):
        self._cagir("/api/kuyruk/ayar", aralik=self.aralik_secim.get())

    def hex_enjekte(self):
        h = self.hex_var.get().strip()
        if not h:
            return
        if not self.bagli:
            self.log("önce bağlan", UYARI)
            return

        def is_():
            c = self.api.gonder("/api/enjekte", h)
            if c is None:
                self.log("enjekte → hata: %s" % self.api.son_hata, HATA)
            elif c.get("ok"):
                self.log("enjekte edildi: %s" % h, OK)
            else:
                self.log("enjekte → %s" % c.get("hata", "hata"), UYARI)
        threading.Thread(target=is_, daemon=True).start()

    def dur_gonder(self):
        k = self.durum.get("konum") or {}
        if not k.get("bilinir"):
            self.log("konum bilinmiyor", UYARI)
            return
        x, y   = int(k.get("x", 0)), int(k.get("y", 0))
        tik     = int(self.durum.get("tik", 0))
        yon     = int(k.get("yon", 0))
        yon_b   = ((90 - yon) % 360) // 5
        govde   = " ".join("%02X" % b for b in (
            [0x07, 0x00, 0x00, yon_b & 0xFF]
            + list((x   & 0xFFFFFFFF).to_bytes(4, "little"))
            + list((y   & 0xFFFFFFFF).to_bytes(4, "little"))
            + list((tik & 0xFFFFFFFF).to_bytes(4, "little"))))
        self.hex_var.set(govde)
        self.hex_enjekte()


if __name__ == "__main__":
    Uygulama().mainloop()
