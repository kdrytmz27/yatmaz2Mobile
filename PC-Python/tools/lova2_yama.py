# -*- coding: utf-8 -*-
"""
LOVA2 SALDIRI HIZI YAMASI

lova2_deger_tara.py ile bulunan tek i32 adresine yazar. Frida arm64 belleğe
yazabildiği için (kanıtlandı) bu değeri değiştirince client kendi saldırı
temposunu ona göre ayarlar → hızlı vuruş, client kendi şifrelemesiyle.

KULLANIM (kendi terminalinde):
  python tools/lova2_yama.py            -> mevcut değeri OKUR (yazmaz)
  python tools/lova2_yama.py 500        -> adrese 500 yazar
  python tools/lova2_yama.py 500 sabit  -> 500 yazıp 20 sn boyunca her
                                           0.2 sn'de tekrar yazar (oyun
                                           değeri geri set ederse tutturur)

UYARI: bu bir bellek hile'sidir — oyun ToS'unu ihlal eder, BAN RİSKİ var.
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
var _timer = null;
rpc.exports = {
    oku: function (a) { try { return ptr(a).readS32(); } catch(e){ return null; } },
    yaz: function (a, v) {
        try { ptr(a).writeS32(v); return ptr(a).readS32(); }
        catch(e){ return 'HATA: ' + e.message; }
    },
    // JS içinde her 5 ms'de yaz — oyunun her-kare ezmesini yener,
    // RPC gecikmesi yok.
    kilitle: function (a, v) {
        if (_timer) clearInterval(_timer);
        var p = ptr(a);
        _timer = setInterval(function () {
            try { p.writeS32(v); } catch (e) {}
        }, 5);
        return 'kilitlendi';
    },
    birak: function () { if (_timer) { clearInterval(_timer); _timer = null; } return 'bırakıldı'; }
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
        print('X Lova2 görünmüyor — frida-server çalışıyor mu?')
        sys.exit(1)
    ses = dev.attach(pid)
    sc = ses.create_script(JS)
    sc.load()
    return ses, sc


def main():
    kayit = json.load(open(KAYIT))
    i32 = kayit['adaylar'].get('i32', [])
    if not i32:
        print('X i32 adayı yok — önce lova2_deger_tara.py ile daralt')
        return
    adr = i32[0]
    ses, sc = baglan()

    mevcut = sc.exports_sync.oku(adr)
    print('adres %s  mevcut değer: %s' % (adr, mevcut))

    if len(sys.argv) < 2:
        print('(sadece okundu; yazmak için: python tools/lova2_yama.py <deger>)')
        ses.detach()
        return

    deger = int(sys.argv[1])
    sabit = len(sys.argv) > 2 and sys.argv[2] == 'sabit'
    if sabit:
        sc.exports_sync.kilitle(adr, deger)
        print('%s adresine %d KİLİTLENDİ (her 5 ms yazılıyor).' % (adr, deger))
        print('OYUNDA SALDIR — 25 sn boyunca tempoyu izle...')
        try:
            for k in range(25):
                time.sleep(1)
                print('\r  %2d sn  (anlık okunan: %s)'
                      % (k + 1, sc.exports_sync.oku(adr)), end='')
        except KeyboardInterrupt:
            pass
        sc.exports_sync.birak()
        print('\nbırakıldı (değer artık oyunun kontrolünde)')
    else:
        sonuc = sc.exports_sync.yaz(adr, deger)
        print('yazıldı -> %s   OYUNDA SALDIR, tempoya bak.' % sonuc)
    ses.detach()


if __name__ == '__main__':
    main()
