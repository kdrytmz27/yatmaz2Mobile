"""
Romia2 Bot Panel
Gereksinimler: pip install frida
Kullanım: python romia2_panel.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import frida
import threading
import subprocess
import os

# ─── Ayarlar ───────────────────────────────────────────────
def _adb_bul():
    """adb.exe'yi otomatik bul: once PATH, sonra bilinen Android SDK yollari."""
    import shutil
    p = shutil.which("adb")
    if p:
        return p
    adaylar = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
        r"C:\Android\platform-tools\adb.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "adb.exe"),
    ]
    for a in adaylar:
        if a and os.path.exists(a):
            return a
    return "adb"  # PATH'te oldugunu varsay; yoksa calistirinca hata verir

ADB        = _adb_bul()
BOT_JS     = os.path.join(os.path.dirname(__file__), "bot.js")
FRIDA_HOST = "127.0.0.1:27042"
OYUN_PKG   = "Romia2Mobil"

KOYU    = "#0e0f13"
PANEL   = "#1a1b20"
VURGU   = "#4f8ef7"
YESIL   = "#3ecf8e"
KIRMIZI = "#e05c5c"
TURUNCU = "#f59e0b"
METIN   = "#e2e8f0"
SOLUK   = "#6b7280"


class RomiaBot:
    def __init__(self, root):
        self.root    = root
        self.root.title("Romia2 Bot Panel")
        self.root.configure(bg=KOYU)
        self.root.resizable(True, True)

        self.session    = None
        self.script     = None
        self.bagli      = False
        self.farm_aktif = False

        self.cur_x     = tk.StringVar(value="0")
        self.cur_y     = tk.StringVar(value="0")
        self.cur_mx    = tk.StringVar(value="0 m")
        self.cur_my    = tk.StringVar(value="0 m")
        self.dist_var  = tk.StringVar(value="-")
        self.durum_var = tk.StringVar(value="Bağlı değil")
        self.mob_var   = tk.StringVar(value="Mob: 0")
        self.farm_var  = tk.StringVar(value="Farm: KAPALI")

        self.hedef_x = tk.IntVar(value=0)
        self.hedef_y = tk.IntVar(value=0)

        self._arayuz_olustur()

    # ─── Arayüz ─────────────────────────────────────────────

    def _arayuz_olustur(self):
        stil = ttk.Style()
        stil.theme_use("clam")
        for w in ("TLabel", "TFrame", "TLabelframe", "TLabelframe.Label"):
            stil.configure(w, background=PANEL, foreground=METIN,
                           font=("Segoe UI", 10))
        stil.configure("TLabelframe",       foreground=VURGU, font=("Segoe UI", 10, "bold"))
        stil.configure("TLabelframe.Label", foreground=VURGU, background=PANEL)
        stil.configure("TEntry", fieldbackground="#2a2b32", foreground=METIN,
                       font=("Segoe UI", 10))

        ana = tk.Frame(self.root, bg=KOYU, padx=12, pady=12)
        ana.pack(fill=tk.BOTH, expand=True)

        # ── Bağlantı ──
        bag = ttk.LabelFrame(ana, text=" Bağlantı ", padding=8)
        bag.pack(fill=tk.X, pady=(0, 6))

        self._dugme(bag, "Frida'ya Bağlan",  self.baglan,      YESIL, 20).pack(side=tk.LEFT, padx=(0, 6))
        self._dugme(bag, "Bağlantıyı Kes",   self.baglantiKes, KIRMIZI, 20).pack(side=tk.LEFT)
        tk.Label(bag, textvariable=self.durum_var, bg=PANEL, fg=VURGU,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT)

        # ── Konum ──
        kon = ttk.LabelFrame(ana, text=" Konum (ham / metre) ", padding=8)
        kon.pack(fill=tk.X, pady=(0, 6))

        for col, (lbl, var) in enumerate([("Ham X:", self.cur_x), ("Ham Y:", self.cur_y),
                                           ("Metre X:", self.cur_mx), ("Metre Y:", self.cur_my)]):
            tk.Label(kon, text=lbl, bg=PANEL, fg=SOLUK,
                     font=("Segoe UI", 9)).grid(row=0, column=col*2, sticky="w", padx=(0, 4))
            tk.Label(kon, textvariable=var, bg=PANEL, fg=METIN,
                     font=("Courier New", 10, "bold"), width=11).grid(row=0, column=col*2+1,
                                                                       sticky="w", padx=(0, 12))

        tk.Label(kon, textvariable=self.mob_var, bg=PANEL, fg=TURUNCU,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=8, sticky="e", padx=(8, 0))

        # ── Hareket ──
        har = ttk.LabelFrame(ana, text=" Hedefe Git (ham koordinat) ", padding=8)
        har.pack(fill=tk.X, pady=(0, 6))

        tk.Label(har, text="X:", bg=PANEL, fg=SOLUK).grid(row=0, column=0, sticky="w")
        ttk.Entry(har, textvariable=self.hedef_x, width=12).grid(row=0, column=1, padx=(4, 12))
        tk.Label(har, text="Y:", bg=PANEL, fg=SOLUK).grid(row=0, column=2, sticky="w")
        ttk.Entry(har, textvariable=self.hedef_y, width=12).grid(row=0, column=3, padx=(4, 12))
        self._dugme(har, "Git!", self.hareket, VURGU, 10).grid(row=0, column=4, padx=(0, 6))
        self._dugme(har, "Dur",  self.dur,     KIRMIZI, 10).grid(row=0, column=5)

        # ── Yönler ──
        yon = ttk.LabelFrame(ana, text=" Hızlı Yön (500 birim ≈ 5 m) ", padding=8)
        yon.pack(fill=tk.X, pady=(0, 6))
        yon.columnconfigure((0, 1, 2), weight=1)

        self._dugme(yon, "↑ Kuzey", lambda: self.yon_hareket(0, -500),  "#5b6af0", 14).grid(row=0, column=1, pady=2, padx=4, sticky="ew")
        self._dugme(yon, "← Batı",  lambda: self.yon_hareket(-500, 0),  "#5b6af0", 14).grid(row=1, column=0, pady=2, padx=4, sticky="ew")
        self._dugme(yon, "● Dur",   self.dur,                            KIRMIZI,  14).grid(row=1, column=1, pady=2, padx=4, sticky="ew")
        self._dugme(yon, "→ Doğu",  lambda: self.yon_hareket(500, 0),   "#5b6af0", 14).grid(row=1, column=2, pady=2, padx=4, sticky="ew")
        self._dugme(yon, "↓ Güney", lambda: self.yon_hareket(0, 500),   "#5b6af0", 14).grid(row=2, column=1, pady=2, padx=4, sticky="ew")

        # ── Farm ──
        farm = ttk.LabelFrame(ana, text=" Farm (otomatik mob saldırı) ", padding=8)
        farm.pack(fill=tk.X, pady=(0, 6))

        self.farm_baslat_btn = self._dugme(farm, "▶ Farm Başlat", self.farm_baslat, YESIL, 18)
        self.farm_baslat_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.farm_durdur_btn = self._dugme(farm, "■ Farm Durdur", self.farm_durdur, KIRMIZI, 18)
        self.farm_durdur_btn.pack(side=tk.LEFT)

        tk.Label(farm, textvariable=self.farm_var, bg=PANEL, fg=TURUNCU,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT)

        # ── Log ──
        log_f = ttk.LabelFrame(ana, text=" Log ", padding=6)
        log_f.pack(fill=tk.BOTH, expand=True)

        self.log_alan = scrolledtext.ScrolledText(
            log_f, height=10, bg="#12131a", fg=METIN,
            font=("Courier New", 9), relief="flat", insertbackground=METIN)
        self.log_alan.pack(fill=tk.BOTH, expand=True)

        self._dugme(log_f, "Logu Temizle", self.log_temizle, "#374151", 16).pack(anchor="e", pady=(4, 0))

    def _dugme(self, parent, text, cmd, renk=VURGU, width=18):
        return tk.Button(parent, text=text, command=cmd,
                         bg=renk, fg="white", activebackground=renk,
                         font=("Segoe UI", 10, "bold"), relief="flat",
                         cursor="hand2", width=width, pady=6)

    # ─── Bağlantı ────────────────────────────────────────────

    def baglan(self):
        threading.Thread(target=self._baglan_thread, daemon=True).start()

    def _baglan_thread(self):
        try:
            self.log_yaz("ADB port forward açılıyor...")
            subprocess.run([ADB, "forward", "tcp:27042", "tcp:27042"],
                           capture_output=True, timeout=5)

            self.log_yaz("Frida'ya bağlanılıyor...")
            dev = frida.get_device_manager().add_remote_device(FRIDA_HOST)

            pid = None
            for proc in dev.enumerate_processes():
                if OYUN_PKG in proc.name:
                    pid = proc.pid
                    break

            if not pid:
                self.log_yaz("HATA: Oyun bulunamadı! Oyun çalışıyor mu?")
                return

            self.log_yaz(f"Oyun bulundu — PID={pid}")
            self.session = dev.attach(pid)

            with open(BOT_JS, encoding="utf-8") as f:
                src = f.read()

            self.script = self.session.create_script(src)
            self.script.on("message", self._mesaj_al)
            self.script.load()

            self.bagli = True
            self.durum_var.set("✓ Bağlı")
            self.log_yaz("Bağlantı başarılı! Oyunda birkaç adım yürü — konum dolsun.")

        except Exception as e:
            self.log_yaz(f"HATA: {e}")

    def baglantiKes(self):
        self.bagli = False
        self.farm_aktif = False
        for s in (self.script, self.session):
            if s:
                try:
                    (s.unload if hasattr(s, "unload") else s.detach)()
                except Exception:
                    pass
        self.script = self.session = None
        self.durum_var.set("Bağlı değil")
        self.farm_var.set("Farm: KAPALI")
        self.log_yaz("Bağlantı kesildi.")

    # ─── Mesaj alıcı ─────────────────────────────────────────

    def _mesaj_al(self, mesaj, veri):
        if mesaj.get("type") != "send":
            if mesaj.get("type") == "error":
                self.log_yaz(f"SCRIPT HATA: {mesaj.get('description', '')}")
            return

        p = mesaj.get("payload", {})
        if not isinstance(p, dict):
            return

        tip = p.get("tip", "")

        if tip == "konum":
            self.root.after(0, lambda: self._konum_guncelle(p))

        elif tip == "durum_tam":
            self.root.after(0, lambda: self._durum_tam_guncelle(p))

        elif tip == "farm":
            self.root.after(0, lambda: self.farm_var.set(
                f"Farm: AÇIK | Mob: {p.get('mobSayisi', 0)} | Hedef VID {p.get('vid', 0)} | {p.get('dist', 0)} m"))

        elif tip == "varlik":
            self.log_yaz(f"MOB #{p.get('id')}  vnum={p.get('vnum')}  {p.get('mesafe', '?')} m uzakta")

        elif tip == "log":
            self.log_yaz(p.get("mesaj", ""))

    def _konum_guncelle(self, p):
        self.cur_x.set(str(p.get("x", 0)))
        self.cur_y.set(str(p.get("y", 0)))
        self.cur_mx.set(f"{p.get('mx', 0)} m")
        self.cur_my.set(f"{p.get('my', 0)} m")
        d = p.get("dist", 0)
        self.dist_var.set(f"{d} birim" if d else "-")

    def _durum_tam_guncelle(self, p):
        self.cur_x.set(str(p.get("selfX", 0)))
        self.cur_y.set(str(p.get("selfY", 0)))
        self.cur_mx.set(f"{p.get('mx', 0)} m")
        self.cur_my.set(f"{p.get('my', 0)} m")
        self.mob_var.set(f"Mob: {p.get('mobSayisi', 0)}  |  Varlık: {p.get('toplamVarlik', 0)}")
        if not p.get("farmAktif", False):
            self.farm_var.set("Farm: KAPALI")

    # ─── Komutlar ────────────────────────────────────────────

    def _kontrol_et(self):
        if not self.bagli or not self.script:
            messagebox.showwarning("Uyarı", "Önce Frida'ya bağlan!")
            return False
        return True

    def hareket(self):
        if not self._kontrol_et(): return
        x, y = self.hedef_x.get(), self.hedef_y.get()
        if x == 0 and y == 0:
            messagebox.showwarning("Uyarı", "Hedef koordinat gir!")
            return
        self.script.post({"type": "hareket", "x": x, "y": y})
        self.log_yaz(f"Git -> ham ({x}, {y})")

    def dur(self):
        if self.script:
            self.script.post({"type": "dur"})
            self.farm_aktif = False
            self.farm_var.set("Farm: KAPALI")

    def yon_hareket(self, dx, dy):
        if not self._kontrol_et(): return
        try:
            x = int(self.cur_x.get()) + dx
            y = int(self.cur_y.get()) + dy
        except ValueError:
            self.log_yaz("Konum bilinmiyor — önce yürü.")
            return
        self.hedef_x.set(x)
        self.hedef_y.set(y)
        self.hareket()

    def farm_baslat(self):
        if not self._kontrol_et(): return
        x = int(self.cur_x.get())
        if x == 0:
            messagebox.showwarning("Uyarı", "Konum bilinmiyor!\nÖnce oyunda birkaç adım yürü.")
            return
        self.script.post({"type": "farm_baslat"})
        self.farm_aktif = True
        self.farm_var.set("Farm: AÇIK")
        self.log_yaz("Farm başladı.")

    def farm_durdur(self):
        if self.script:
            self.script.post({"type": "farm_durdur"})
        self.farm_aktif = False
        self.farm_var.set("Farm: KAPALI")
        self.log_yaz("Farm durduruldu.")

    # ─── Yardımcılar ─────────────────────────────────────────

    def log_yaz(self, mesaj):
        def _yaz():
            self.log_alan.insert(tk.END, f">> {mesaj}\n")
            self.log_alan.see(tk.END)
        self.root.after(0, _yaz)

    def log_temizle(self):
        self.log_alan.delete("1.0", tk.END)


# ─── Başlat ──────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("760x640")
    RomiaBot(root)
    root.mainloop()
