# -*- coding: utf-8 -*-
"""
LOVA2 "DEĞİŞEN DEĞER" TARAYICI (ham saldırı hızı / animasyon çarpanı)

Ekrandaki saldırı hızı (273) bellekte doğrudan tutulmuyor — türetilmiş
değer. Gerçek kaynak farklı bir sayı/ölçekte. Bu araç, değeri BİLMEDEN,
saldırı hızını değiştirince DEĞİŞEN adresleri bulur; iteratif kesişimle
tek adaya iner.

Tüm büyük RW bölgeleri tarar; gürültüyü azaltmak için makul aralık:
  i32: 1..5000   (ham hız/cooldown makul)
  f32: 0.3..30   (animasyon çarpanı makul)

KULLANIM (karakter SABİT dursun, saldırmasın — sadece silah değiştir):
  1) python tools/lova2_diff.py snapshot        (273 iken)
  2) silahı değiştir  -> saldırı hızı 273'ten başka olsun
  3) python tools/lova2_diff.py degisti         (değişenleri tutar)
  4) silahı GERİ tak  -> 273'e dönsün
  5) python tools/lova2_diff.py degisti         (yine değişenleri tutar =
                                                 kesişim, gürültü elenir)
  Tekrarla; aday 1-3'e inince gerçek değişkeni bulduk.
"""
import json
import os
import subprocess
import sys

try:
    import frida
except ImportError:
    print('frida yok: pip install frida')
    sys.exit(1)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ADB = r'adb'
BURA = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(BURA, 'lova2_snapshot.json')

JS = r"""
function bolgeler() {
    var out = [];
    Process.enumerateRanges('rw-').forEach(function (r) {
        if (r.size >= 0x40000) out.push([r.base, r.size]);  // >=256KB
    });
    return out;
}
rpc.exports = {
    // tüm büyük bölgelerde makul i32/f32 değerleri: {adr: [i32, f32]}
    snapshot: function () {
        var out = {};
        var bl = bolgeler();
        bl.forEach(function (br) {
            var base = ptr(br[0]); var size = br[1];
            for (var o = 0; o + 4 <= size; o += 4) {
                try {
                    var a = base.add(o);
                    var iv = a.readS32();
                    var fv = a.readFloat();
                    var iyi = (iv >= 1 && iv <= 5000) ||
                              (fv >= 0.3 && fv <= 30 && fv === fv);
                    if (iyi) out[a.toString()] = [iv, fv];
                } catch (e) {}
            }
        });
        return out;
    },
    // verilen adreslerin şu anki [i32, f32] değerleri
    oku_coklu: function (adrLer) {
        var out = {};
        adrLer.forEach(function (a) {
            try {
                var p = ptr(a);
                out[a] = [p.readS32(), p.readFloat()];
            } catch (e) { out[a] = null; }
        });
        return out;
    }
};
"""


def baglan():
    subprocess.run([ADB, 'forward', 'tcp:27042', 'tcp:27042'],
                   capture_output=True)
    dev = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
    pid = None
    for p in dev.enumerate_processes():
        if 'lova' in (p.name or '').lower():
            pid = p.pid
            break
    if not pid:
        print('X Lova2 görünmüyor — frida-server?')
        sys.exit(1)
    ses = dev.attach(pid)
    sc = ses.create_script(JS)
    sc.load()
    return ses, sc


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else 'snapshot'
    ses, sc = baglan()

    if mod == 'snapshot':
        print('tüm büyük RW bölgeler taranıyor (makul aralık)...')
        import time
        t0 = time.time()
        snap = sc.exports_sync.snapshot()
        print('%d değer, %.1f sn' % (len(snap), time.time() - t0))
        json.dump(snap, open(SNAP, 'w'))
        print('Şimdi silahı DEĞİŞTİR (saldırı hızı 273\'ten başka olsun), '
              'sonra: python tools/lova2_diff.py degisti')
    elif mod == 'degisti':
        if not os.path.exists(SNAP):
            print('X önce snapshot al')
            return
        eski = json.load(open(SNAP))
        adrLer = list(eski.keys())
        # değişenleri bul: şu an OKUNAN != eski
        degisen = {}
        for i in range(0, len(adrLer), 3000):
            parca = adrLer[i:i + 3000]
            yeni = sc.exports_sync.oku_coklu(parca)
            for a in parca:
                y = yeni.get(a)
                if y is None:
                    continue
                ei, ef = eski[a]
                if y[0] != ei:                 # i32 değişti
                    degisen[a] = y
        print('DEĞİŞEN %d değer (yeni snapshot bu oldu):' % len(degisen))
        # göster (az kaldıysa detaylı)
        gost = list(degisen.items())
        for a, (yi, yf) in gost[:40]:
            ei, ef = eski[a]
            print('  %s : i32 %s->%s   f32 %.3f->%.3f' % (a, ei, yi, ef, yf))
        json.dump(degisen, open(SNAP, 'w'))
        if len(degisen) <= 6:
            print('\n>>> AZ ADAY KALDI! Bunları 7x test edeceğiz. '
                  'Adresleri bana getir.')
        else:
            print('\nDaha daralt: silahı GERİ tak (273\'e dön), '
                  'sonra tekrar: python tools/lova2_diff.py degisti')
    ses.detach()


if __name__ == '__main__':
    main()
