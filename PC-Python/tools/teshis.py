# -*- coding: utf-8 -*-
"""
Yakalama TESHISI: hangi arayuz, hangi sunucu IP, root var mi?

"0 packets captured" hatasinin sebebini kesin bulur. Uc sey yanlis olabilir:
  1) Arayuz  - wlan0 sabit varsayimi emulatorde/mobil veride yanlis
  2) Sunucu IP - oyun sunucusu adresi degismis olabilir
  3) root    - su calismiyorsa tcpdump hic baslamaz

Her arayuzde kisa bir deneme yakalamasi yapip GERCEKTEN trafik akan arayuzu
bulur, ayrica acik TCP baglantilarindan oyun sunucusunu tespit eder.

Kullanim:  python tools/teshis.py [adb_yolu]
"""
import subprocess, sys, re, os, collections

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

BILINEN_IP = '185.128.114.87'
# Metin2 ailesi oyun portlari bu araliktadir
OYUN_PORT_ALT, OYUN_PORT_UST = 29000, 31000


def adb_bul(verilen=None):
    if verilen and os.path.exists(verilen):
        return verilen
    for aday in ['adb', 'adb.exe',
                 r'C:\Program Files\platform-tools\adb.exe',
                 os.path.expanduser(r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe')]:
        try:
            subprocess.run([aday, 'version'], capture_output=True, timeout=8)
            return aday
        except Exception:
            continue
    return None


def kabuk(adb, komut, sure=15):
    try:
        p = subprocess.run([adb, 'shell', komut], capture_output=True, timeout=sure)
        return ((p.stdout or b'') + (p.stderr or b'')).decode('utf-8', 'replace')
    except Exception as e:
        return '<hata: %s>' % e


def main():
    adb = adb_bul(sys.argv[1] if len(sys.argv) > 1 else None)
    if not adb:
        print('X adb bulunamadi. adb_bul.bat ile yolunu ayarlayin.')
        return
    print('adb: %s\n' % adb)

    # ---- 1) Cihaz ----
    print('=' * 70)
    print('[1] CIHAZ')
    print('=' * 70)
    cikti = subprocess.run([adb, 'devices'], capture_output=True, timeout=15)
    print(cikti.stdout.decode('utf-8', 'replace').strip())
    if 'device' not in cikti.stdout.decode('utf-8', 'replace').replace('devices', ''):
        print('X Cihaz bagli degil.')
        return

    # ---- 2) root ----
    print('\n' + '=' * 70)
    print('[2] ROOT (su)')
    print('=' * 70)
    su = kabuk(adb, "su -c 'id'")
    if 'uid=0' in su:
        print('  OK  root calisiyor')
    else:
        print('  X  root YOK ya da izin verilmedi:')
        print('     ' + su.strip()[:200])
        print('     -> Magisk/SuperSU`da shell icin izin verin.')

    # ---- 3) tcpdump var mi ----
    print('\n' + '=' * 70)
    print('[3] TCPDUMP')
    print('=' * 70)
    td = kabuk(adb, "su -c 'which tcpdump || ls /system/bin/tcpdump /data/local/tmp/tcpdump'")
    print('  ' + (td.strip()[:200] or '(cikti yok)'))

    # ---- 4) Arayuzler ----
    print('\n' + '=' * 70)
    print('[4] AG ARAYUZLERI')
    print('=' * 70)
    adres = kabuk(adb, "su -c 'ip -o addr show'")
    arayuzler = []
    for satir in adres.splitlines():
        m = re.match(r'\s*\d+:\s+(\S+)\s+inet\s+(\S+)', satir)
        if m and m.group(1) != 'lo':
            arayuzler.append((m.group(1), m.group(2)))
            print('  %-14s %s' % (m.group(1), m.group(2)))
    if not arayuzler:
        print('  (IP`li arayuz bulunamadi)')
        print(adres.strip()[:400])

    rota = kabuk(adb, "su -c 'ip route'")
    m = re.search(r'^default\s+.*\bdev\s+(\S+)', rota, re.M)
    print('\n  varsayilan rota arayuzu: %s' % (m.group(1) if m else '(yok)'))

    # ---- 5) Acik oyun baglantilari -> GERCEK sunucu IP ----
    print('\n' + '=' * 70)
    print('[5] ACIK TCP BAGLANTILARI (oyun sunucusunu bul)')
    print('=' * 70)
    baglantilar = kabuk(adb, "su -c 'ss -tn 2>/dev/null || netstat -tn 2>/dev/null'")
    adaylar = collections.Counter()
    for satir in baglantilar.splitlines():
        for ip, port in re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', satir):
            p = int(port)
            if ip.startswith(('127.', '0.0.0.0', '10.0.2.')): continue
            if OYUN_PORT_ALT <= p <= OYUN_PORT_UST:
                adaylar[(ip, p)] += 1
    if adaylar:
        print('  Oyun portu araliginda (%d-%d) baglantilar:' % (OYUN_PORT_ALT, OYUN_PORT_UST))
        for (ip, p), c in adaylar.most_common(10):
            isaret = '  <== BILINEN' if ip == BILINEN_IP else '  <== YENI IP!'
            print('    %s:%-6d%s' % (ip, p, isaret))
    else:
        print('  Oyun portu araliginda baglanti YOK.')
        print('  Tum dis baglantilar:')
        gorulen = set()
        for satir in baglantilar.splitlines():
            for ip, port in re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', satir):
                if ip.startswith(('127.', '0.0.0.0')): continue
                if (ip, port) in gorulen: continue
                gorulen.add((ip, port))
                print('    %s:%s' % (ip, port))
        if not gorulen:
            print('    (hic yok - oyun acik ve GIRIS YAPILMIS olmali)')

    # ---- 6) Her arayuzde deneme yakalamasi ----
    print('\n' + '=' * 70)
    print('[6] DENEME YAKALAMASI (her arayuzde 4 sn, filtresiz)')
    print('=' * 70)
    print('  Oyun ACIK ve hareket halinde olmali...\n')
    denenecek = [a for a, _ in arayuzler] or ['wlan0', 'eth0', 'rmnet_data0']
    if 'any' not in denenecek:
        denenecek.append('any')
    sonuc = []
    for ar in denenecek:
        c = kabuk(adb, "su -c 'timeout 4 tcpdump -i %s -c 200 -w /dev/null tcp' 2>&1" % ar, sure=25)
        m = re.search(r'(\d+)\s+packets captured', c)
        sayi = int(m.group(1)) if m else -1
        if 'not permitted' in c or 'No such device' in c:
            durum = 'ARAYUZ YOK / IZIN YOK'
        elif sayi < 0:
            durum = 'okunamadi'
        elif sayi == 0:
            durum = 'trafik yok'
        else:
            durum = '%d TCP paketi  <== TRAFIK BURADA' % sayi
        sonuc.append((ar, sayi))
        print('  %-14s %s' % (ar, durum))

    # ---- 7) Sonuc ----
    print('\n' + '=' * 70)
    print('SONUC')
    print('=' * 70)
    enIyi = max(sonuc, key=lambda x: x[1]) if sonuc else None
    if enIyi and enIyi[1] > 0:
        print('  Kullanilacak arayuz : %s' % enIyi[0])
    else:
        print('  X Hicbir arayuzde TCP trafigi yok.')
        print('    Oyun acik ve giris yapilmis olmali; root izni verilmeli.')
    if adaylar:
        ip, p = adaylar.most_common(1)[0][0]
        print('  Oyun sunucusu       : %s (port %d)' % (ip, p))
        if ip != BILINEN_IP:
            print('\n  ! SUNUCU IP DEGISMIS. Su iki yerde guncelleyin:')
            print('      app/src/main/java/com/abdulkadir/r2panel/PaketServisi.java  OYUN_IP')
            print('      PC_YAKALA.bat                                              OYUN_IP')
    else:
        print('  Oyun sunucusu       : tespit edilemedi (oyunda giris yapin, tekrar calistirin)')


if __name__ == '__main__':
    main()
