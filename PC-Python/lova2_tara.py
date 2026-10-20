"""
Lova2 attack speed bellek tarayici
  python lova2_tara.py --tara 273
  python lova2_tara.py --daralt <yeni_deger>
  python lova2_tara.py --yaz <adres> <deger> [--tip float32]
  python lova2_tara.py --oku <adres>
  python lova2_tara.py --liste
"""

import frida, json, os, sys, argparse, time

ADB   = r"adb"
HOST  = "127.0.0.1:27042"
ISIM  = "Lova2 Mobile"
KAYIT = "lova2_adresler.json"

RPC_TARA = """
rpc.exports = {
  tara: function(hedefInt, hedefFloat) {
    var sonuclar = [];
    var bolgeler = Process.enumerateRangesSync({protection:'rw-', coalesce:true});
    for (var i = 0; i < bolgeler.length; i++) {
      var b = bolgeler[i];
      if (b.size > 128*1024*1024) continue;
      try {
        var buf = b.base.readByteArray(b.size);
        if (!buf) continue;
        var dv = new DataView(buf);
        for (var j = 0; j + 4 <= buf.byteLength; j += 4) {
          var iv = dv.getInt32(j, true);
          var fv = dv.getFloat32(j, true);
          if (iv === hedefInt)
            sonuclar.push({adres: b.base.add(j).toString(), tip:'int32', deger:iv});
          else if (Math.abs(fv - hedefFloat) < 0.5)
            sonuclar.push({adres: b.base.add(j).toString(), tip:'float32', deger:fv});
          if (sonuclar.length >= 5000) return sonuclar;
        }
      } catch(e) {}
    }
    return sonuclar;
  }
};
"""

RPC_DARALT = """
rpc.exports = {
  oku: function(adres, tip) {
    try {
      var p = ptr(adres);
      if (tip === 'int32')   return p.readS32();
      if (tip === 'float32') return p.readFloat();
    } catch(e) { return null; }
    return null;
  }
};
"""

RPC_YAZ = """
rpc.exports = {
  yaz: function(adres, deger, tip) {
    var p = ptr(adres);
    if (tip === 'int32')   p.writeS32(deger | 0);
    if (tip === 'float32') p.writeFloat(deger);
    return true;
  },
  oku: function(adres) {
    var p = ptr(adres);
    return {i: p.readS32(), f: p.readFloat()};
  }
};
"""

def baglan():
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = None
    for p in dev.enumerate_processes():
        if ISIM in p.name:
            pid = p.pid
            break
    if not pid:
        print(f"HATA: '{ISIM}' bulunamadi"); sys.exit(1)
    print(f"Baglandi PID={pid}")
    ses = dev.attach(pid)
    return ses

def tara(deger):
    ses = baglan()
    print(f"Taranıyor: int={int(deger)}  float≈{float(deger):.2f} ...")
    t0 = time.time()
    scr = ses.create_script(RPC_TARA)
    scr.load()
    sonuclar = scr.exports.tara(int(deger), float(deger))
    scr.unload()
    ses.detach()
    print(f"Bulundu: {len(sonuclar)} adres  ({time.time()-t0:.1f}s)")
    return sonuclar

def daralt(yeni):
    if not os.path.exists(KAYIT):
        print("Once --tara calistir"); sys.exit(1)
    with open(KAYIT) as f:
        eski = json.load(f)
    print(f"Daraltiliyor: {len(eski)} adres -> yeni deger={yeni}")
    ses = baglan()
    scr = ses.create_script(RPC_DARALT)
    scr.load()
    kalan = []
    for e in eski:
        v = scr.exports.oku(e["adres"], e["tip"])
        if v is None: continue
        if e["tip"] == "int32"   and int(v)   == int(yeni):             kalan.append(e)
        if e["tip"] == "float32" and abs(float(v) - float(yeni)) < 0.5: kalan.append(e)
    scr.unload()
    ses.detach()
    print(f"Kalan: {len(kalan)} adres")
    return kalan

def yaz_adres(adres, deger, tip):
    ses = baglan()
    scr = ses.create_script(RPC_YAZ)
    scr.load()
    onceki = scr.exports.oku(adres)
    scr.exports.yaz(adres, float(deger), tip)
    sonraki = scr.exports.oku(adres)
    scr.unload()
    ses.detach()
    print(f"{adres}  oncesi: i={onceki['i']} f={onceki['f']:.2f}  sonrasi: i={sonraki['i']} f={sonraki['f']:.2f}")

def oku_adres(adres):
    ses = baglan()
    scr = ses.create_script(RPC_YAZ)
    scr.load()
    v = scr.exports.oku(adres)
    scr.unload()
    ses.detach()
    print(f"{adres}  int32={v['i']}  float32={v['f']:.4f}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tara",   type=float)
    ap.add_argument("--daralt", type=float)
    ap.add_argument("--yaz",    nargs=2, metavar=("ADRES","DEGER"))
    ap.add_argument("--oku",    metavar="ADRES")
    ap.add_argument("--tip",    default="int32", choices=["int32","float32"])
    ap.add_argument("--liste",  action="store_true")
    args = ap.parse_args()

    if args.liste:
        if os.path.exists(KAYIT):
            with open(KAYIT) as f: lst = json.load(f)
            for e in lst[:50]: print(e)
            print(f"Toplam: {len(lst)}")
        return

    if args.tara is not None:
        s = tara(args.tara)
        with open(KAYIT, "w") as f: json.dump(s, f)
        for e in s[:20]: print(f"  {e['adres']}  {e['tip']}  {e['deger']}")
        if len(s) > 20: print(f"  ... ve {len(s)-20} tane daha")

    elif args.daralt is not None:
        k = daralt(args.daralt)
        with open(KAYIT, "w") as f: json.dump(k, f)
        for e in k: print(f"  {e['adres']}  {e['tip']}  {e['deger']}")

    elif args.yaz:
        yaz_adres(args.yaz[0], args.yaz[1], args.tip)

    elif args.oku:
        oku_adres(args.oku)

if __name__ == "__main__":
    main()
