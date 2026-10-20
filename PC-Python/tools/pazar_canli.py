# -*- coding: utf-8 -*-
"""
PAZAR CANLI OKUYUCU — dükkânlar tarandıkça ANINDA görünsün.

Neden gerekliydi: dükkân içeriği 3449 bayt ve /api/log bunu kırpıyor, oradan
canlı okunamıyor. tcpdump'ı telefonda dosyaya yazdırıp sonunda çekmek de
sonuçları tur bitene kadar bekletiyordu.

Çözüm: tcpdump'ı dosyaya değil STANDART ÇIKIŞA yazdırıp akışı doğrudan
okuyoruz (adb exec-out ... -w -). pcap kayıtları geldikçe çözülüyor, her
dükkân okunur okunmaz geri bildiriliyor.

    tcpdump -U -s0 -w -   →  adb boru hattı  →  burada çözülür  →  panel
"""

import os
import struct
import subprocess
import sys
import threading
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BURASI)

import kanal_bul as kb                                  # noqa: E402
import pazar_paket as pp                                # noqa: E402

OYUN_ALT, OYUN_UST = 30000, 30100


class CanliOkuyucu:
    """tcpdump akışını okuyup 0x26 dükkân paketlerini anında çözer.

    Kullanım:
        o = CanliOkuyucu(lambda d: print(d['sahip_vid']))
        o.basla();  ... ;  o.dur()
    """

    def __init__(self, bulundu=None, gunluk=None):
        self.bulundu = bulundu or (lambda d: None)
        self.gunluk = gunluk or (lambda s: None)
        self._p = None
        self._iplik = None
        self._calis = False
        self.paket_say = 0
        self.dukkan_say = 0

    # ── akış ────────────────────────────────────────────────────────────
    UZAK = '/sdcard/r2_pazar_canli.pcap'

    def basla(self, arayuz=None):
        """tcpdump'ı dosyaya yazdırıp dosyayı canlı takip et.

        Doğrudan `tcpdump -w -` denendi: pcap başlığı geliyor ama paket
        gelmiyordu (telefon tarafında tamponlanıyor). Dosyaya yazma yolu ise
        kanıtlanmış; onu 'tail -c +1 -f' ile takip ediyoruz."""
        adb = kb.adb_bul()
        if not adb:
            self.gunluk('X adb yok')
            return False
        if 'uid=0' not in kb.kabuk(adb, "su -c 'id'"):
            self.gunluk('X root (su) çalışmıyor — tcpdump gerekiyor')
            return False
        arayuz = arayuz or kb.arayuz_bul(adb)
        # eskisini temizle, yenisini arka planda başlat
        kb.kabuk(adb, "su -c 'pkill -f r2_pazar_canli.pcap'")
        kb.kabuk(adb, "su -c 'rm -f %s'" % self.UZAK)
        kb.kabuk(adb, "su -c 'nohup tcpdump -i %s -U -s 0 -w %s tcp portrange 30000-30100 "
                      ">/dev/null 2>&1 &'" % (arayuz, self.UZAK), sure=5)
        time.sleep(1.2)                       # dosya oluşsun
        komut = [adb, 'exec-out', 'su', '-c',
                 'tail -c +1 -f %s' % self.UZAK]
        try:
            self._p = subprocess.Popen(komut, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, bufsize=0)
        except Exception as e:                          # noqa: BLE001
            self.gunluk('X akış açılamadı: %s' % type(e).__name__)
            return False

        def _hata_oku():
            try:
                for satir in iter(self._p.stderr.readline, b''):
                    m = satir.decode('utf-8', 'replace').strip()
                    if m and 'listening on' not in m:
                        self.gunluk('akış: %s' % m)
            except Exception:                           # noqa: BLE001
                pass
        threading.Thread(target=_hata_oku, daemon=True).start()
        self._calis = True
        self._adb = adb
        self._iplik = threading.Thread(target=self._dongu, daemon=True)
        self._iplik.start()
        self.gunluk('canlı okuma başladı (%s)' % arayuz)
        return True

    def dur(self):
        self._calis = False
        if self._p:
            try:
                self._p.kill()
            except Exception:                           # noqa: BLE001
                pass
            self._p = None
        adb = getattr(self, '_adb', None)
        if adb:
            try:
                kb.kabuk(adb, "su -c 'pkill -f r2_pazar_canli.pcap'")
                kb.kabuk(adb, "su -c 'rm -f %s'" % self.UZAK)
            except Exception:                           # noqa: BLE001
                pass

    # ── pcap akışını ayrıştır ───────────────────────────────────────────
    def _tam_oku(self, n):
        """Akıştan tam n bayt oku (parça parça gelebilir)."""
        parcalar = []
        kalan = n
        while kalan > 0 and self._calis:
            p = self._p.stdout.read(kalan)
            if not p:
                return None
            parcalar.append(p)
            kalan -= len(p)
        return b''.join(parcalar) if kalan == 0 else None

    def _dongu(self):
        bas = self._tam_oku(24)                          # pcap genel başlığı
        if not bas or len(bas) < 24:
            self.gunluk('X akış açılmadı — tcpdump çalışmıyor olabilir '
                        '(root/su ve arayüzü kontrol et: '
                        'python tools/pazar_akis_testi.py)')
            return
        en = '<' if bas[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1') else '>'
        baglanti = struct.unpack_from(en + 'I', bas, 20)[0]
        lh = 16 if baglanti == 113 else (14 if baglanti == 1 else 0)

        # TCP akışını yeniden birleştirmek gerekiyor: dükkân paketi 3449 bayt,
        # tek segmente sığmaz. Bağlantı başına tampon tutuyoruz.
        tampon = {}
        while self._calis:
            kayit = self._tam_oku(16)
            if not kayit:
                break
            _sn, _us, cap, _orig = struct.unpack_from(en + 'IIII', kayit, 0)
            if cap <= 0 or cap > 262144:
                break
            pkt = self._tam_oku(cap)
            if pkt is None:
                break
            self.paket_say += 1
            if len(pkt) < lh + 40:
                continue
            ip = lh
            if (pkt[ip] >> 4) != 4 or pkt[ip + 9] != 6:
                continue
            ihl = (pkt[ip] & 0xF) * 4
            tcp = ip + ihl
            kport = (pkt[tcp] << 8) | pkt[tcp + 1]
            hport = (pkt[tcp + 2] << 8) | pkt[tcp + 3]
            if not (OYUN_ALT <= kport <= OYUN_UST):      # yalnız sunucudan gelen
                continue
            veri = tcp + (((pkt[tcp + 12] >> 4) & 0xF) * 4)
            yuk = pkt[veri:cap]
            if not yuk:
                continue
            anahtar = (kport, hport)
            tampon[anahtar] = tampon.get(anahtar, b'') + bytes(yuk)
            self._tamponu_isle(tampon, anahtar)

    def _tamponu_isle(self, tampon, anahtar):
        """Birikmiş akışta tam 0x26 çerçevesi var mı?"""
        b = tampon[anahtar]
        # 0x26 dışındaki baytları atarak başa hizala (akışın ortasına düşmüş
        # olabiliriz; oyun başka paketler de gönderiyor).
        while b:
            i = b.find(b'\x26')
            if i < 0:
                b = b''
                break
            if i:
                b = b[i:]
            if len(b) < 3:
                break
            boy = int.from_bytes(b[1:3], 'little')
            if boy not in (pp.ICERIK_BOY, 4):
                b = b[1:]                                # yanlış hizalama
                continue
            if len(b) < boy:
                break                                    # daha gelecek
            d = pp.coz(b[:boy])
            b = b[boy:]
            if d and d['alt'] == pp.ALT_ICERIK and d['esyalar']:
                self.dukkan_say += 1
                try:
                    self.bulundu(d)
                except Exception:                        # noqa: BLE001
                    pass
        # tamponu makul tut
        tampon[anahtar] = b[-8192:] if len(b) > 8192 else b


def _test():
    """Akışı 20 sn dinle, gelen dükkânları yaz (sen elle tıkla)."""
    import time
    say = [0]

    def bulundu(d):
        say[0] += 1
        print('  dükkân vid=%-9s %d eşya' % (d['sahip_vid'], len(d['esyalar'])))

    o = CanliOkuyucu(bulundu, print)
    if not o.basla():
        return
    print('20 sn dinliyorum — oyunda dükkânlara tıkla...')
    time.sleep(20)
    o.dur()
    print('bitti: %d paket, %d dükkân' % (o.paket_say, say[0]))


if __name__ == '__main__':
    _test()
