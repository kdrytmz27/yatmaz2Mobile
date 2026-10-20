# -*- coding: utf-8 -*-
"""
LOVA2 BELLEK DEĞER TARAYICI (Romia2 ISTEMCI_OLCUMU yöntemi)

Bir sayıyı oyun belleğinde bulur, sonra değeri değiştirip aday listesini
daraltır — tek adres kalana kadar. Frida arm64 belleği OKUYUP YAZABİLİYOR
(kanıtlandı), o yüzden kod çağırmaya gerek yok.

KULLANIM (kendi terminalinde):
  1) python tools/lova2_deger_tara.py 273
        -> 273'ü arar, adayları tools/lova2_adaylar.json'a yazar, sayıyı basar
  2) oyunda değeri DEĞİŞTİR (buff/iksir/ekipman ile saldırı hızını oynat)
  3) python tools/lova2_deger_tara.py 300     (yeni görünen değer)
        -> kayıtlı adaylardan yalnız 300 olanları tutar (daraltma)
  Tekrarla; aday 1-2'ye inince adres bulunmuş demektir.

Not: yalnız OKUR (yazma yapmaz). Değeri int32/int16/float olarak dener.
"""
import json
import os
import subprocess
import sys
import time

try:
    import frida
except ImportError:
    print('frida yok: pip install frida')
    sys.exit(1)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ADB = r'adb'
KAYIT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'lova2_adaylar.json')

JS = r"""
'use strict';
function tara(deger) {
    // int32, int16, float — üçünü de ayrı listede dene
    function patBytes(bytes) {
        var s = '';
        for (var i = 0; i < bytes.length; i++)
            s += ('0' + (bytes[i] & 0xff).toString(16)).slice(-2) + ' ';
        return s.trim();
    }
    var b32 = new Uint8Array(4); var dv = new DataView(b32.buffer);
    dv.setInt32(0, deger, true);
    var b16 = new Uint8Array(2); new DataView(b16.buffer).setInt16(0, deger, true);
    var bf = new Uint8Array(4); new DataView(bf.buffer).setFloat32(0, deger, true);
    var pat = { i32: patBytes(b32), i16: patBytes(b16), f32: patBytes(bf) };

    var sonuc = { i32: [], i16: [], f32: [] };
    var ranges = Process.enumerateRanges('rw-');
    var SINIR = 400000;
    ranges.forEach(function (r) {
        ['i32', 'i16', 'f32'].forEach(function (tip) {
            if (sonuc[tip].length >= SINIR) return;
            try {
                Memory.scanSync(r.base, r.size, pat[tip]).forEach(function (m) {
                    if (sonuc[tip].length < SINIR)
                        sonuc[tip].push(m.address.toString());
                });
            } catch (e) {}
        });
    });
    return sonuc;
}
rpc.exports = {
    tara: function (d) { return tara(d); },
    oku: function (adrLer, tip) {
        // verilen adreslerde şu anki değeri oku, tipine göre
        var out = [];
        adrLer.forEach(function (a) {
            try {
                var p = ptr(a);
                var v;
                if (tip === 'i16') v = p.readS16();
                else if (tip === 'f32') v = p.readFloat();
                else v = p.readS32();
                out.push([a, v]);
            } catch (e) { out.push([a, null]); }
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
        print('X Lova2 frida\'ya görünmüyor — frida-server çalışıyor mu?')
        print('  Başlat: adb shell "su -c \'/data/local/tmp/frida-server '
              '-l 0.0.0.0:27042 &\'"')
        sys.exit(1)
    ses = dev.attach(pid)
    sc = ses.create_script(JS)
    sc.load()
    return ses, sc


def main():
    if len(sys.argv) < 2:
        print('kullanım: python tools/lova2_deger_tara.py <deger>')
        return
    deger = int(sys.argv[1])
    ses, sc = baglan()

    if not os.path.exists(KAYIT):
        # İLK TUR: baştan tara
        print('%d aranıyor (int32/int16/float)...' % deger)
        t0 = time.time()
        sonuc = sc.exports_sync.tara(deger)
        print('süre %.1f sn' % (time.time() - t0))
        for tip in ('i32', 'i16', 'f32'):
            print('  %s: %d aday' % (tip, len(sonuc[tip])))
        json.dump({'deger': deger, 'adaylar': sonuc}, open(KAYIT, 'w'))
        toplam = sum(len(sonuc[t]) for t in sonuc)
        print('\n%d aday kaydedildi. Şimdi oyunda saldırı hızını DEĞİŞTİR '
              '(buff/iksir/ekipman), sonra:\n'
              '  python tools/lova2_deger_tara.py <yeni_deger>' % toplam)
    else:
        # DARALTMA: kayıtlı adaylardan yeni değere uyanları tut
        kayit = json.load(open(KAYIT))
        yeni = {'deger': deger, 'adaylar': {}}
        for tip in ('i32', 'i16', 'f32'):
            eski = kayit['adaylar'].get(tip, [])
            if not eski:
                yeni['adaylar'][tip] = []
                continue
            okunan = []
            for i in range(0, len(eski), 2000):
                okunan += sc.exports_sync.oku(eski[i:i + 2000], tip)
            tut = [a for a, v in okunan if v == deger]
            yeni['adaylar'][tip] = tut
            print('  %s: %d -> %d aday' % (tip, len(eski), len(tut)))
        json.dump(yeni, open(KAYIT, 'w'))
        toplam = sum(len(yeni['adaylar'][t]) for t in yeni['adaylar'])
        print('\nkalan toplam: %d aday' % toplam)
        if toplam <= 3:
            print('ADAYLAR:')
            for tip in yeni['adaylar']:
                for a in yeni['adaylar'][tip]:
                    print('   %s (%s) @ %s' % (deger, tip, a))
            print('Neredeyse bulundu! Bir kez daha değiştirip daralt, '
                  'ya da bunları 7x yamalamayı deneriz.')
        elif toplam > 3:
            print('Daha çok daraltma gerek: değeri tekrar değiştir + çalıştır.')
    ses.detach()


if __name__ == '__main__':
    main()
