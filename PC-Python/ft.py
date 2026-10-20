import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
os.environ["TAMBOT_SESSIZ"]="1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pazar_firsat as pf, pazar_tara as pz, pazar_paket as pp

adlar = pz.EsyaAdlari()
import tempfile
g = pf.FiyatGecmisi(yol=os.path.join(tempfile.gettempdir(), "test_fiyat.json"))
g.tablo = {}
kurallar = [pf.Kural(ad="iksir", azami=15000),
            pf.Kural(efsun="ortalama hasar", en_az=10)]
vurus = []
av = pf.FirsatAvcisi(adlar, g, kurallar, bildir=lambda f: vurus.append(f))

esyalar = [
  {"slot":0,"vnum":27006,"fiyat":35000,"adet":200,"efsunlar":[]},
  {"slot":1,"vnum":27006,"fiyat":12000,"adet":200,"efsunlar":[]},
  {"slot":2,"vnum":290,"fiyat":350000,"adet":1,
   "efsunlar":[{"tur":71,"ad":"Ortalama hasar %","deger":14}]},
]
print("1. tur:", av.dukkan(111, "Test Marketi", esyalar), "firsat")
for f in vurus: print("   %-9s %-22s %10d  %s" % (f["tur"], f["esya"][:22], f["fiyat"], f["dukkan"]))

vurus.clear()
print("\n2. tur (ayni fiyatlar):", av.dukkan(111, "Test Marketi", esyalar), "firsat  <- tekrar olmamali")

vurus.clear()
ucuz = [{"slot":5,"vnum":27006,"fiyat":8000,"adet":200,"efsunlar":[]}]
print("\n3. tur (27006 8.000'e dustu):", av.dukkan(222, "Ucuz Marketi", ucuz), "firsat")
for f in vurus:
    print("   %-9s %-22s %10d  eski en dusuk: %s" % (f["tur"], f["esya"][:22], f["fiyat"], f["eski_fiyat"]))
