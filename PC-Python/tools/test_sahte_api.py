"""ApiSunucu'nun yanıtlarını taklit eden sahte sunucu + masaüstü panelinin
veri yolunu GUI olmadan sınayan test. Sadece geliştirme içindir."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

DURUM = {
    "ok": True, "surum": "0.2.0", "zaman": 1756300000000,
    "servisler": {"panel": True, "paket": True, "kuyruk": False, "proxy": True},
    "proxy": {"acik": True, "durum": "bağlantı kuruldu :30004", "bagli": True,
              "enjeksiyon": False, "giden": 812, "gelen": 4410, "enjekte": 0},
    "konum": {"bilinir": True, "x": 985412, "y": -270155,
              "mx": 9854.12, "my": 2701.55, "yon": 90, "hedef": 9428902},
    "sayac": {"toplam": 5222, "giden": 812, "gelen": 4410},
    "varlik": {"toplam": 41, "canavar": 22, "metin": 3, "npc": 5, "isimsiz": 11},
    "katalog": {"hazir": True, "varlik": 2857, "esya": 28655},
    "kuyruk": {"servis": False, "calisiyor": False, "duraklatildi": False,
               "aralik": 350, "bekleyen": 0, "kanal": "Log (kuru çalışma)",
               "kanalHazir": True, "aktif": ""},
    "rota": {"ad": "rota", "boyut": 2, "indeks": 0,
             "durum": "nokta 1/2 — 14 m", "calisiyor": True, "dongusel": True},
    "tik": 123456789,
}
VARLIKLAR = [
    {"vid": 9428902, "x": 985900, "y": -270900, "vnum": 101, "tip": 0,
     "ad": "Alfa Kurt (Lv4)", "tipAd": "CANAVAR", "mx": 9859.0, "my": 2709.0,
     "mesafe": 9, "can": 80},
    {"vid": 7714221, "x": 984000, "y": -269000, "vnum": 8021, "tip": 2,
     "ad": "Kaplan Metini (Lv20)", "tipAd": "METIN", "mx": 9840.0, "my": 2690.0,
     "mesafe": 18, "can": -1},
]
ROTALAR = {"ok": True, "aktif": "rota", "rotalar": [
    {"ad": "rota", "boyut": 2, "dongusel": True, "uzunluk": 34, "noktalar": [
        {"x": 985412, "y": -270155, "mx": 9854.12, "my": 2701.55,
         "bekle": 0, "yaricap": 300},
        {"x": 986412, "y": -271155, "mx": 9864.12, "my": 2711.55,
         "bekle": 3000, "yaricap": 300}]}]}
KUYRUK = {"ok": True, "aralik": 350, "duraklatildi": False,
          "kanal": "Log (kuru çalışma)",
          "bekleyen": [{"id": 3, "ozet": "YÜRÜ 985412,-270155 (9854,2702 m)",
                        "oncelik": 0}],
          "gecmis": [{"id": 2, "ozet": "HEDEFLE #9428902", "durum": "BITTI",
                      "sonuc": "", "sure": 12}]}
LOG = [{"giden": True, "boy": 16, "opcode": 7, "cozum": "hareket state=1",
        "hex": "07 01 00 00", "zaman": 1756300000000,
        "basli": "20:41:03.114  OUT  op=0x07  len=16"}]


class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _yaz(self, veri):
        b = json.dumps(veri).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        yol = self.path.split("?")[0]
        self._yaz({"/api/durum": DURUM, "/api/varliklar": VARLIKLAR,
                   "/api/rotalar": ROTALAR, "/api/kuyruk": KUYRUK,
                   "/api/log": LOG}.get(yol, {"ok": True}))

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        self._yaz({"ok": True})


def calistir(port=30299):
    s = HTTPServer(("127.0.0.1", port), Isleyici)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def tkinter_taklidi():
    """Bu kapta tkinter yok. Modül düzeyindeki import ve sınıf tanımları
    geçsin diye iskelet bir tkinter yerleştirilir; GUI çalıştırılmaz."""
    import sys
    import types
    try:
        import tkinter  # noqa: F401
        return False
    except ImportError:
        pass

    class Widget:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, ad):
            return lambda *a, **k: None

    tk = types.ModuleType("tkinter")
    for ad in ("Tk", "Canvas", "Frame", "Label", "Button", "Entry", "Text",
               "Checkbutton", "Radiobutton", "LabelFrame", "StringVar",
               "BooleanVar", "IntVar"):
        setattr(tk, ad, type(ad, (Widget,), {}))
    tk.TclError = type("TclError", (Exception,), {})
    ttk = types.ModuleType("tkinter.ttk")
    for ad in ("Style", "Notebook", "Treeview", "Combobox"):
        setattr(ttk, ad, type(ad, (Widget,), {}))
    messagebox = types.ModuleType("tkinter.messagebox")
    messagebox.askyesno = lambda *a, **k: True
    messagebox.showwarning = lambda *a, **k: None
    tk.ttk, tk.messagebox = ttk, messagebox
    sys.modules["tkinter"] = tk
    sys.modules["tkinter.ttk"] = ttk
    sys.modules["tkinter.messagebox"] = messagebox
    return True


if __name__ == "__main__":
    if tkinter_taklidi():
        print("not: tkinter yok, taklit modül kullanılıyor (yalnızca test için)")
    calistir()
    time.sleep(0.3)

    import r2_masaustu as m
    api = m.Api()
    api.adres = "127.0.0.1:30299"

    for yol in ("/api/durum", "/api/varliklar", "/api/rotalar",
                "/api/kuyruk", "/api/log"):
        assert api.cagir(yol) is not None, yol
        print("ok", yol)
    assert api.gonder("/api/enjekte", "07 01 00 00")["ok"]
    print("ok POST /api/enjekte")

    # GUI kurmadan _durum_tazele'nin biçim dizesini sına
    class Sahte:
        pass
    kendi = Sahte()
    kendi.durum = DURUM
    for ad in ("durum_yazi", "enj_etiket", "rota_durum", "takip_dugme"):
        setattr(kendi, ad, type("W", (), {
            "configure": lambda self, **k: None,
            "delete": lambda self, *a: None,
            "insert": lambda self, *a: None})())
    m.Uygulama._durum_tazele(kendi)
    print("ok _durum_tazele biçimi")

    # radar dönüşümü: ham -> ekran -> ham gidiş-dönüş
    class SahteRadar(m.Radar):
        def __init__(self):
            self.durum = DURUM
            self.zoom = 0.35

        def winfo_width(self):
            return 800

        def winfo_height(self):
            return 600

    r = SahteRadar()
    sx, sy = r.m2p(9900.0, 2750.0)
    hx, hy = r.p2ham(sx, sy)
    print("gidiş-dönüş:", (hx, hy), "beklenen ~", (990000, -275000))
    assert abs(hx - 990000) < 500 and abs(hy + 275000) < 500
    print("ok radar dönüşümü")

    # kuyruk / paket / rota listelerini kuran metotlar sahte gereçlerle
    class Yazi:
        def __init__(self):
            self.icerik = ""

        def configure(self, **k):
            pass

        def delete(self, *a):
            self.icerik = ""

        def insert(self, nere, metin, *etiket):
            self.icerik += metin

        def see(self, *a):
            pass

    class Agac:
        def __init__(self):
            self.satirlar = []

        def selection(self):
            return ()

        def delete(self, *a):
            self.satirlar = []

        def get_children(self):
            return ()

        def insert(self, a, b, values=()):
            self.satirlar.append(values)
            return "i%d" % len(self.satirlar)

        def selection_set(self, *a):
            pass

        def configure(self, **k):
            pass

        def set(self, *a):
            pass

        def get(self):
            return "rota"

    kendi.kuyruk_yazi = Yazi()
    m.Uygulama._kuyruk_tazele(kendi, KUYRUK)
    assert "YÜRÜ" in kendi.kuyruk_yazi.icerik and "HEDEFLE" in kendi.kuyruk_yazi.icerik
    print("ok _kuyruk_tazele")

    kendi.paket_yazi = Yazi()
    kendi.paket_hex = type("V", (), {"get": lambda self: True})()
    m.Uygulama._paket_tazele(kendi, LOG)
    assert "OUT" in kendi.paket_yazi.icerik
    print("ok _paket_tazele")

    kendi.varlik_agac = Agac()
    kendi.varliklar = VARLIKLAR
    m.Uygulama._varliklar_tazele(kendi)
    assert kendi.varlik_agac.satirlar[0][0] == "CANAVAR"
    assert kendi.varlik_agac.satirlar[1][3] == "-"      # can bilinmiyor
    print("ok _varliklar_tazele")

    kendi.rota_agac = Agac()
    kendi.rota_secim = Agac()
    kendi.rotalar = {r["ad"]: r for r in ROTALAR["rotalar"]}
    kendi.aktif_rota = "rota"
    m.Uygulama._rota_tazele(kendi)
    assert len(kendi.rota_agac.satirlar) == 2
    assert kendi.rota_agac.satirlar[1][3] == "3.0 sn"
    print("ok _rota_tazele")

    print("\nTÜM TESTLER GEÇTİ")
