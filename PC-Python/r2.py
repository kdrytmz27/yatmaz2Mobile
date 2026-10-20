# -*- coding: utf-8 -*-
"""
R2 Panel — tek pencere başlatıcı.

Sade bir menü: iki büyük düğme. Biri Tam Bot'u (farm/savaş), diğeri Metin
İzleyici panelini (izleme/buff) açar. Her biri kendi penceresinde çalışır;
tüm ayarlar o pencerelerden yönetilir.

    python r2.py            -> başlatıcı menü
    python r2.py --tambot   -> doğrudan Tam Bot
    python r2.py --panel    -> doğrudan Metin İzleyici paneli

EXE olarak paketlemek için: exe_yap.bat  (R2Panel.exe üretir).
"""
import os
import subprocess
import sys
import tkinter as tk

KOYU = "#0f1117"
PANEL = "#171922"
CIZGI = "#262a36"
METIN = "#e6e8ef"
SOLUK = "#9aa0b4"
VURGU = "#33aaff"
YESIL = "#37d67a"
OK = "#00c878"


def calistir_tambot():
    import tambot
    tambot.TamBot().mainloop()


def calistir_panel():
    import metin_izleyici_panel as mip
    mip.Panel().mainloop()


def calistir_kral():
    import kral_panel
    kral_panel._main_gui()


def _kendini_ac(bayrak):
    """Aynı programı yeni bir pencerede (ayrı süreç) açar."""
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable, bayrak])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), bayrak])


def _adb_bul():
    """adb.exe: ADB_YOLU, Android SDK, yaygın konumlar, sonra PATH."""
    for a in (os.environ.get("ADB_YOLU"),
              os.path.expanduser(
                  r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
              r"C:\Program Files\platform-tools\adb.exe",
              r"C:\platform-tools\adb.exe"):
        if a and os.path.exists(a):
            return a
    return "adb"


def _adb_forward(etiket):
    adb = _adb_bul()
    try:
        p = subprocess.run([adb, "forward", "tcp:30200", "tcp:30200"],
                           capture_output=True, text=True, timeout=15)
        if p.returncode == 0:
            etiket.configure(text="adb forward TAMAM (tcp:30200)", fg=OK)
        else:
            etiket.configure(text="adb forward olmadı — telefon/USB bağlı mı?", fg="#e05050")
    except FileNotFoundError:
        etiket.configure(text="adb bulunamadı (ADB_YOLU değişkenini ayarla)", fg="#e05050")
    except Exception as e:                                 # noqa: BLE001
        etiket.configure(text="adb hatası: %s" % type(e).__name__, fg="#e05050")


def _dugme(ana, baslik, altyazi, komut, renk):
    d = tk.Frame(ana, bg=PANEL, highlightbackground=CIZGI, highlightthickness=1,
                 cursor="hand2")
    d.pack(fill="x", pady=6)
    tk.Label(d, text=baslik, bg=PANEL, fg=renk, font=("Segoe UI", 15, "bold"),
             anchor="w").pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(d, text=altyazi, bg=PANEL, fg=SOLUK, font=("Segoe UI", 9),
             anchor="w", justify="left").pack(fill="x", padx=14, pady=(0, 10))
    for w in (d,) + tuple(d.winfo_children()):
        w.bind("<Button-1>", lambda e, k=komut: k())
    return d


def _pencere_kur(kok):
    kok.title("R2 Panel")
    kok.configure(bg=KOYU)
    kok.geometry("430x420")
    kok.minsize(400, 380)
    tk.Label(kok, text="R2 Panel", bg=KOYU, fg=METIN,
             font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 0))
    tk.Label(kok, text="Ne açmak istersin?", bg=KOYU, fg=SOLUK,
             font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(0, 8))
    govde = tk.Frame(kok, bg=KOYU)
    govde.pack(fill="both", expand=True, padx=12)
    _dugme(govde, "🎮  Tam Bot",
           "Farm / savaş / toplama — oyunun içindeki bot.\n"
           "Açılınca adb forward (tcp:30200) kendiliğinden denenir.",
           lambda: _kendini_ac("--tambot"), VURGU)
    _dugme(govde, "👁  Metin İzleyici",
           "8 hesapla metin/oyuncu izleme, buff'çı, telefon paneli.",
           lambda: _kendini_ac("--panel"), YESIL)
    _dugme(govde, "👑  Kralı Yakala",
           "Etkinliği otomatik oynar (APK enjeksiyon; kart masasında aç).",
           lambda: _kendini_ac("--kral"), "#ffcc33")
    alt = tk.Frame(kok, bg=KOYU)
    alt.pack(fill="x", padx=16, pady=(0, 12))
    durum = tk.Label(alt, text="", bg=KOYU, fg=SOLUK, font=("Segoe UI", 8),
                     anchor="w")
    durum.pack(side="bottom", fill="x", pady=(6, 0))
    tk.Button(alt, text="adb forward (Tam Bot için)", bg=CIZGI, fg=METIN,
              activebackground=VURGU, relief="flat", bd=0, padx=10, pady=5,
              cursor="hand2", font=("Segoe UI", 9),
              command=lambda: _adb_forward(durum)).pack(side="left")


def launcher():
    kok = tk.Tk()
    _pencere_kur(kok)
    kok.mainloop()


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--tambot":
        calistir_tambot()
    elif arg == "--panel":
        calistir_panel()
    elif arg == "--kral":
        calistir_kral()
    else:
        launcher()


if __name__ == "__main__":
    main()
