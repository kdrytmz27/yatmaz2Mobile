# -*- coding: utf-8 -*-
"""
LOVA2 HIZLI DEĞİŞEN-DEĞER (tek çalıştırma, agent-içi karşılaştırma)

Ekran saldırı hızı (273) türetilmiş; gerçek değer farklı ölçekte. Bunu
"değişen değer" ile buluruz. Karşılaştırma FRIDA İÇİNDE yapılır, host'a
yalnız değişen adresler (az) döner — bu yüzden hızlı.

Snapshot agent belleğinde tutulduğundan tüm akış TEK çalıştırmada olur;
ENTER ile ilerlersin.

KULLANIM:
  python tools/lova2_hizli.py
  - Karakter SABİT dursun (saldırmasın/yürümesin).
  - Yönergeye göre silahı değiştir/geri tak, ENTER'a bas.
"""
import subprocess
import sys

try:
    import frida
except ImportError:
    print('frida yok'); sys.exit(1)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ADB = r'adb'

JS = r"""
var snap = [];   // [ [baseStr, Int32Array], ... ]
var aday = null; // daraltma sonrası kalan adresler (Set gibi dizi)

function bolgeler() {
    var out = [];
    Process.enumerateRanges('rw-').forEach(function (r) {
        if (r.size >= 0x40000 && r.size <= 0x4000000) out.push([r.base, r.size]);
    });
    return out;
}
rpc.exports = {
    snapshot: function () {
        snap = [];
        bolgeler().forEach(function (br) {
            try {
                var buf = ptr(br[0]).readByteArray(br[1]);
                snap.push([br[0].toString(), br[1], new Int32Array(buf)]);
            } catch (e) {}
        });
        var n = 0; snap.forEach(function (s) { n += s[2].length; });
        return n;
    },
    // İlk daraltma: snapshot'a göre DEĞİŞEN + makul olan adresleri aday yap
    ilk_degisti: function () {
        aday = [];
        snap.forEach(function (s) {
            var base = ptr(s[0]); var arr = s[2];
            var yeni;
            try { yeni = new Int32Array(ptr(s[0]).readByteArray(s[1])); }
            catch (e) { return; }
            for (var i = 0; i < arr.length; i++) {
                if (arr[i] !== yeni[i] &&
                    ((yeni[i] >= 1 && yeni[i] <= 5000) ||
                     (arr[i] >= 1 && arr[i] <= 5000))) {
                    aday.push(base.add(i * 4).toString());
                }
            }
        });
        return aday.length;
    },
    // mevcut adayların şu anki i32 değerleri (referans)
    ref_al: function () {
        var r = {};
        aday.forEach(function (a) { try { r[a] = ptr(a).readS32(); } catch (e) {} });
        return r;
    },
    // referanstan bu yana DEĞİŞEN adayları tut (kesişimle daralt)
    daralt: function (ref) {
        var kalan = [];
        aday.forEach(function (a) {
            try {
                if (ref[a] !== undefined && ptr(a).readS32() !== ref[a])
                    kalan.push(a);
            } catch (e) {}
        });
        aday = kalan;
        return aday.length;
    },
    adaylar: function () {
        return aday.map(function (a) {
            var iv = null, fv = null;
            try { iv = ptr(a).readS32(); fv = ptr(a).readFloat(); } catch (e) {}
            return [a, iv, fv];
        });
    }
};
"""


def main():
    subprocess.run([ADB, 'forward', 'tcp:27042', 'tcp:27042'],
                   capture_output=True)
    try:
        dev = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
        pid = None
        for p in dev.enumerate_processes():
            if 'lova' in (p.name or '').lower():
                pid = p.pid
                break
    except Exception:
        pid = None
    if not pid:
        print('X Lova2/frida-server yok. Şu komutu çalıştır sonra tekrar dene:')
        print('  adb shell "su -c \'/data/local/tmp/frida-server '
              '-l 0.0.0.0:27042 &\'"')
        return
    ses = dev.attach(pid)
    sc = ses.create_script(JS)
    sc.load()

    print('\n=== Karakter SABİT dursun (saldırma/yürüme). Saldırı hızı 273 '
          'olsun. ===')
    input('Hazırsan ENTER...')
    print('anlık görüntü alınıyor...')
    n = sc.exports_sync.snapshot()
    print('  %d int32 değer alındı.' % n)

    input('\nŞimdi SİLAHI DEĞİŞTİR (saldırı hızı 273\'ten başka olsun), '
          'sonra ENTER...')
    k = sc.exports_sync.ilk_degisti()
    print('  değişen aday: %d' % k)

    tur = 0
    while k > 6 and tur < 8:
        tur += 1
        yon = 'GERİ TAK (273\'e dön)' if tur % 2 == 1 else 'tekrar DEĞİŞTİR'
        ref = sc.exports_sync.ref_al()            # şu anki değerleri sabitle
        input('\nSilahı %s, sonra ENTER...' % yon)
        k = sc.exports_sync.daralt(ref)           # değişenleri tut
        print('  kalan aday: %d' % k)

    print('\n=== KALAN ADAYLAR ===')
    for a, iv, fv in sc.exports_sync.adaylar():
        print('  %s : i32=%s  f32=%.3f' % (a, iv, fv))
    print('\nBu adresleri 7x test edeceğiz. Çıktıyı bana getir.')
    ses.detach()


if __name__ == '__main__':
    main()
