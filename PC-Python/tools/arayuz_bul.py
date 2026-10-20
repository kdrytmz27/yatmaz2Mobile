# -*- coding: utf-8 -*-
"""
Cihazda oyun sunucusuna giden ag arayuzunun adini bulur ve STDOUT'a yazar.

PC_YAKALA.bat bunu cagirir. "wlan0" sabit varsayimi emulatorlerde ve bazi
telefonlarda yanlistir (eth0 / wlan1 / rmnet_data0 olabilir); yanlis arayuz
= bos yakalama.

Kullanim:  python tools/arayuz_bul.py <adb_yolu> [oyun_ip]
Cikti   :  tek satir arayuz adi (bulunamazsa "wlan0")
"""
import subprocess, sys, re

VARSAYILAN = 'wlan0'
ADAYLAR = ['wlan0', 'wlan1', 'eth0', 'eth1', 'rmnet0', 'rmnet_data0']


def calistir(adb, komut, sure=10):
    try:
        p = subprocess.run([adb, 'shell', komut],
                           capture_output=True, timeout=sure)
        return (p.stdout or b'').decode('utf-8', 'replace')
    except Exception:
        return ''


def bul(adb, ip):
    # 1) Rota sorgusu: "... dev wlan0 ..." doner
    cikti = calistir(adb, "su -c 'ip route get %s'" % ip)
    m = re.search(r'\bdev\s+(\S+)', cikti)
    if m:
        return m.group(1)

    # 2) Rota tablosunda varsayilan cikis
    cikti = calistir(adb, "su -c 'ip route'")
    m = re.search(r'^default\s+.*\bdev\s+(\S+)', cikti, re.M)
    if m:
        return m.group(1)

    # 3) Ayakta ve IP'si olan ilk aday arayuz
    cikti = calistir(adb, "su -c 'ip -o addr show'")
    for aday in ADAYLAR:
        if re.search(r'\d+:\s+%s\b.*inet\s' % re.escape(aday), cikti):
            return aday
    m = re.search(r'^\d+:\s+(\S+)\s+inet\s', cikti, re.M)
    if m and m.group(1) != 'lo':
        return m.group(1)

    return VARSAYILAN


def main():
    if len(sys.argv) < 2:
        print(VARSAYILAN)
        return
    adb = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else '185.128.114.87'
    ad = bul(adb, ip).strip()
    # Guvenlik: kabuk komutuna girecek, sadece makul karakterlere izin ver
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', ad or ''):
        ad = VARSAYILAN
    print(ad)


if __name__ == '__main__':
    main()
