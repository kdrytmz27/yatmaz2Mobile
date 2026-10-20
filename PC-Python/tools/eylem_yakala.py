# -*- coding: utf-8 -*-
"""
Bir EYLEMİN paketini bul — yakalama + analiz tek adımda.

PC_EYLEM.bat'ın yerini alır. Batch dosyasındaki tırnak/değişken kırılganlığı
yüzünden kayıt bazen hiç başlamadan pencere kapanıyordu; burada her adım
kontrol edilir ve TÜM ÇIKTI bir rapor dosyasına da yazılır, böylece pencere
kapansa bile sonuç kaybolmaz.

KULLANIM
--------
    python tools/eylem_yakala.py npc_tikla 5
    python tools/eylem_yakala.py satis 5 --sure 60

    <eylem_adı>  raporda ve dosya adında görünür
    <kaç_kez>    eylemi kaç kez yapacaksın (analiz bunu arar)
    --sure N     kayıt süresi, saniye (varsayılan 45)

YÖNTEM
------
Oyun istemcisi her eylemi AYRI bir TCP segmentinde gönderir. Normal oyun
üç şeyle dolu: 0x02 saldırı, 0x3D hedef, 0x07 hareket. Bir eylemi N kez
yaparsan, o eyleme ait (opcode, boy) çifti tam N kez görünen NADİR satır
olarak ayrışır.

KAYIT SIRASINDA
---------------
  • YÜRÜME, SALDIRMA, başka tuşa BASMA — akışı doldurur
  • Botu kapat
  • Her tekrar arasında 3-4 saniye bekle
"""

import os
import re
import subprocess
import sys
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

OYUN_IP = '185.128.114.87'
UZAK_YOL = '/sdcard/r2_eylem.pcap'


class Yaz:
    """Ekrana ve rapor dosyasına aynı anda yazar."""
    def __init__(self, yol):
        self.f = open(yol, 'w', encoding='utf-8')
        self.yol = yol
    def __call__(self, *p):
        s = ' '.join(str(x) for x in p)
        print(s)
        self.f.write(s + '\n')
        self.f.flush()
    def kapat(self):
        self.f.close()


def adb_bul():
    adaylar = [
        os.environ.get('ADB_YOLU'),
        'adb',
        os.path.expanduser(r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe'),
        r'C:\Program Files\platform-tools\adb.exe',
    ]
    for a in adaylar:
        if not a:
            continue
        try:
            p = subprocess.run([a, 'version'], capture_output=True, timeout=10)
            if p.returncode == 0:
                return a
        except Exception:
            continue
    return None


def kabuk(adb, komut, sure=20):
    try:
        p = subprocess.run([adb, 'shell', komut],
                           capture_output=True, timeout=sure)
        return ((p.stdout or b'') + (p.stderr or b'')).decode('utf-8', 'replace')
    except Exception as e:
        return '<hata: %s>' % e


def arayuz_bul(adb, yaz):
    cikti = kabuk(adb, "su -c 'ip route get %s'" % OYUN_IP)
    m = re.search(r'\bdev\s+(\S+)', cikti)
    if m:
        return m.group(1)
    cikti = kabuk(adb, "su -c 'ip -o addr show'")
    for aday in ('wlan0', 'wlan1', 'eth0', 'rmnet_data0'):
        if re.search(r'\s%s\b.*inet\s' % re.escape(aday), cikti):
            return aday
    yaz('  ! arayüz bulunamadı, wlan0 denenecek')
    return 'wlan0'


def main():
    args = [a for a in sys.argv[1:]]
    sure = 45
    if '--sure' in args:
        i = args.index('--sure')
        try: sure = int(args[i + 1])
        except Exception: pass
        del args[i:i + 2]

    eylem = args[0] if args else input('Eylemin adı (ör. npc_tikla): ').strip()
    eylem = re.sub(r'[^A-Za-z0-9_-]', '_', eylem or 'eylem')
    try:
        kez = int(args[1]) if len(args) > 1 else int(
            input('Kaç kez yapacaksın (önerilen 5): ') or '5')
    except Exception:
        kez = 5

    logd = os.path.join(_KOK, 'log')
    os.makedirs(logd, exist_ok=True)
    damga = time.strftime('%Y%m%d_%H%M%S')
    pcap = os.path.join(logd, 'eylem_%s_%s.pcap' % (eylem, damga))
    rapor = os.path.join(logd, 'eylem_%s_%s.txt' % (eylem, damga))

    yaz = Yaz(rapor)
    yaz('=' * 70)
    yaz('EYLEM YAKALAMA:  "%s"  x%d   (%d saniye)' % (eylem, kez, sure))
    yaz('=' * 70)

    adb = adb_bul()
    if not adb:
        yaz('X adb bulunamadı. ADB_YOLU ortam değişkenini ayarla.')
        yaz.kapat(); input('\nKapatmak için Enter...'); return
    yaz('adb   : %s' % adb)

    cihaz = subprocess.run([adb, 'devices'], capture_output=True, timeout=20)
    cikti = cihaz.stdout.decode('utf-8', 'replace')
    if '\tdevice' not in cikti:
        yaz('X Cihaz bağlı değil:\n%s' % cikti.strip())
        yaz.kapat(); input('\nKapatmak için Enter...'); return

    if 'uid=0' not in kabuk(adb, "su -c 'id'"):
        yaz('X root (su) çalışmıyor — tcpdump başlatılamaz.')
        yaz.kapat(); input('\nKapatmak için Enter...'); return
    yaz('root  : OK')

    arayuz = arayuz_bul(adb, yaz)
    yaz('arayüz: %s' % arayuz)

    yaz('')
    yaz('-' * 70)
    yaz('  ŞİMDİ NE YAPACAKSIN')
    yaz('-' * 70)
    yaz('  1. Enter\'a bas, kayıt başlasın')
    yaz('  2. İlk 8 saniye HİÇBİR ŞEY YAPMA')
    yaz('  3. Sonra "%s" eylemini %d KEZ yap' % (eylem, kez))
    yaz('     — her tekrar arasında 3-4 saniye bekle')
    yaz('  4. YÜRÜME, SALDIRMA, başka tuşa BASMA (akışı doldurur)')
    yaz('  5. Bot çalışıyorsa KAPAT')
    yaz('')
    input('Hazırsan Enter...')

    kabuk(adb, "su -c 'pkill -f r2_eylem.pcap'")
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)

    yaz('')
    yaz('>>> KAYIT BAŞLADI (%d sn) — önce 8 sn bekle, sonra %d kez yap <<<'
        % (sure, kez))
    # -U ŞART: onsuz tcpdump tamponda biriktirir, timeout öldürünce kaybolur
    kabuk(adb,
          "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s host %s'"
          % (sure, arayuz, UZAK_YOL, OYUN_IP),
          sure=sure + 30)
    yaz('>>> KAYIT BİTTİ <<<')

    subprocess.run([adb, 'pull', UZAK_YOL, pcap], capture_output=True, timeout=60)
    kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)

    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        yaz('')
        yaz('X Kayıt alınamadı ya da boş.')
        yaz('  tools/teshis.py çalıştırıp arayüz/IP/root kontrol et.')
        yaz.kapat(); input('\nKapatmak için Enter...'); return
    yaz('kayıt : %s  (%.1f KB)' % (pcap, os.path.getsize(pcap) / 1024.0))

    try:
        gercek = input('\nGerçekte kaç kez yaptın? [%d]: ' % kez).strip()
        kez = int(gercek) if gercek else kez
    except Exception:
        pass

    yaz('')
    import eylem_bul
    eski = sys.stdout
    class Ikili:
        def write(self, s):
            eski.write(s); yaz.f.write(s)
        def flush(self):
            eski.flush(); yaz.f.flush()
    sys.stdout = Ikili()
    try:
        eylem_bul.analiz(pcap, None, kez)
    finally:
        sys.stdout = eski

    yaz('')
    yaz('=' * 70)
    yaz('RAPOR DOSYASI: %s' % rapor)
    yaz('KAYIT DOSYASI: %s' % pcap)
    yaz('=' * 70)
    yaz.kapat()
    input('\nKapatmak için Enter...')


if __name__ == '__main__':
    main()
