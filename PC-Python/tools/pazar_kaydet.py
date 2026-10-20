# -*- coding: utf-8 -*-
"""
PAZAR (oyuncu dükkânları) paket kaydı — 0x26 GC_SHOP'u çözmek için.

Amaç: haritadaki oyuncu dükkânlarını tarayıp içindeki eşya + fiyatları
BİLDİREN bir bot yazmak (satın alma YOK). Bunun için dükkân içeriğini taşıyan
`0x26 GC_SHOP` paketinin yapısını bilmemiz gerekiyor; şu an yalnızca "var ve
uzunluk önekli" olduğunu biliyoruz (docs/PROTOKOL_OFSET.md).

Neden paket, neden ekran değil: eşya ADI ve FİYATI metin. Kralı Yakala'da
renkleri okumak kolaydı, ama metni OCR'lamak hataya açık. 0x26 bu veriyi
yapısal taşıyor (vnum/adet/fiyat), okuması çok daha güvenilir.

KULLANIM
--------
    python tools/pazar_kaydet.py --sure 120
      1) Enter'a bas (kayıt başlar)
      2) Pazara git, BİRKAÇ FARKLI oyuncu dükkânını aç
         - her dükkânda birkaç saniye bekle ki içerik tam gelsin
         - mümkünse İÇİNDE FARKLI SAYIDA eşya olanları seç (1 eşyalı,
           çok eşyalı) — alan sınırlarını böyle çözeriz
      3) Kayıt bitince döküm ekrana + log/pazar_XXXX.txt dosyasına yazılır

    python tools/pazar_kaydet.py --dosya log/pazar_XXXX.pcap   # var olanı çöz

Not: Şifre/kişisel veri oyun paketlerinde geçmez. Bu araç hiçbir şey
göndermez, yalnızca dinler.
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                   # noqa: BLE001
        pass

import kanal_bul as kb                                  # noqa: E402

UZAK_YOL = '/sdcard/r2_pazar.pcap'
OYUN_ALT, OYUN_UST = 30000, 30100

# Dükkân akışıyla ilgisiz, sürekli akan paketler.
GURULTU = {0x01, 0x02, 0x03, 0x05, 0x0D, 0x0E, 0x11, 0x13, 0x2C, 0x3E,
           0x3F, 0x87, 0xFC, 0xFD, 0xFE}


def _varliklari_topla(sure, cikti):
    """Kayıt boyunca /api/varliklar anlık görüntüleri — dükkân nasıl görünüyor?"""
    try:
        _sp = importlib.util.spec_from_file_location(
            'tambot', os.path.join(_KOK, 'tambot.py'))
        tb = importlib.util.module_from_spec(_sp)
        _sp.loader.exec_module(tb)
        api = tb.Api()
    except Exception as e:                              # noqa: BLE001
        cikti.append({'hata': 'tambot yüklenemedi: %s' % type(e).__name__})
        return
    bitis = time.time() + sure
    gorulen = {}
    while time.time() < bitis:
        try:
            vs = api.get('/api/varliklar', n=80)
            if isinstance(vs, list):
                for v in vs:
                    vid = v.get('vid')
                    if vid and vid not in gorulen:
                        gorulen[vid] = v
        except Exception:                               # noqa: BLE001
            pass
        time.sleep(1.0)
    cikti.extend(gorulen.values())


def kaydet(sure):
    adb = kb.adb_bul()
    if not adb:
        print('X adb bulunamadı.')
        return None, []
    dev = subprocess.run([adb, 'devices'], capture_output=True,
                         timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in dev:
        print('X Cihaz bağlı değil.')
        return None, []
    if 'uid=0' not in kb.kabuk(adb, "su -c 'id'"):
        print('X root (su) çalışmıyor.')
        return None, []
    arayuz = kb.arayuz_bul(adb)
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    pcap = os.path.join(_KOK, 'log',
                        'pazar_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    print('arayüz: %s' % arayuz)
    print('-' * 70)
    print('  1. Enter -> kayıt başlar')
    print('  2. PAZARA git ve BİRKAÇ FARKLI oyuncu dükkânını AÇ')
    print('     - her dükkânda 2-3 sn bekle (içerik tam gelsin)')
    print('     - az eşyalı ve çok eşyalı dükkânlar karışık olsun')
    print('  3. Kayıt bitince döküm gelir')
    print('-' * 70)
    input('Hazırsan Enter...')
    kb.kabuk(adb, "su -c 'pkill -f r2_pazar.pcap'")
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    varliklar = []
    ip = threading.Thread(target=_varliklari_topla,
                          args=(sure, varliklar), daemon=True)
    ip.start()
    print('>>> KAYIT BAŞLADI (%d sn) — şimdi dükkânları aç <<<' % sure)
    kb.kabuk(adb, "su -c 'timeout %d tcpdump -i %s -U -s 0 -w %s tcp'"
             % (sure, arayuz, UZAK_YOL), sure=sure + 30)
    print('>>> KAYIT BİTTİ <<<')
    ip.join(timeout=3)
    subprocess.run([adb, 'pull', UZAK_YOL, pcap], capture_output=True, timeout=180)
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    if not os.path.exists(pcap) or os.path.getsize(pcap) < 100:
        print('X Kayıt alınamadı ya da boş.')
        return None, varliklar
    print('kayıt : %s  (%.1f KB)' % (pcap, os.path.getsize(pcap) / 1024.0))
    return pcap, varliklar


def _yon(kport, hport):
    if OYUN_ALT <= hport <= OYUN_UST:
        return 'C>S'
    if OYUN_ALT <= kport <= OYUN_UST:
        return 'S>C'
    return None


def _metin(b):
    p = ''.join(chr(x) if 32 <= x < 127 else '.' for x in b)
    return p if any(c != '.' for c in p) else ''


def _u32(b, i):
    return int.from_bytes(b[i:i + 4], 'little') if i + 4 <= len(b) else None


def _shop_cerceveler(b):
    """Segment içindeki 0x26 çerçevelerini ayıkla: 26 | boy(u16 LE) | gövde."""
    out = []
    i = 0
    while i + 3 <= len(b):
        if b[i] == 0x26:
            boy = int.from_bytes(b[i + 1:i + 3], 'little')
            # Üst sınır kritik (docs): gevşek bırakınca kilobaytlar yutuluyor.
            if 4 <= boy <= 4096 and i + boy <= len(b):
                out.append(b[i:i + boy])
                i += boy
                continue
        i += 1
    return out


def analiz(yol, varliklar=None):
    cikti = ['=' * 78, 'PAZAR — %s' % os.path.basename(yol), '=' * 78]
    paketler = kb.pcap_tcp(yol)
    if not paketler:
        print('X paket okunamadı')
        return
    t0 = paketler[0][0]

    # 1) Başlık histogramı
    hist = {}
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        y = _yon(kport, hport)
        if not yuk or not y:
            continue
        hist[(y, yuk[0])] = hist.get((y, yuk[0]), 0) + 1
    cikti.append('\n1) PAKET BAŞLIKLARI (yön / 0xNN / adet)')
    for (y, h), n in sorted(hist.items(), key=lambda kv: -kv[1])[:24]:
        isaret = ''
        if h == 0x26 and y == 'S>C':
            isaret = '   <-- DÜKKÂN İÇERİĞİ (çözeceğimiz)'
        elif h in (0x1A, 0x32) and y == 'C>S':
            isaret = '   <-- dükkân açma / işlem'
        cikti.append('   %s  0x%02x  x%-5d%s' % (y, h, n, isaret))

    # 2) Dükkân akışı: ne tıkladık, ne geldi
    cikti.append('\n2) DÜKKÂN AKIŞI (giden tıklama / gelen 0x26)')
    shop_no = 0
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        y = _yon(kport, hport)
        if not yuk or not y:
            continue
        b = bytes(yuk)
        t = (z - t0) / 1e6
        if y == 'C>S' and b[0] == 0x1A and len(b) >= 5:
            cikti.append('   +%7.2f  SEN   dükkâna tıkla (vid=%s)'
                         % (t, _u32(b, 1)))
        elif y == 'C>S' and b[0] == 0x32:
            cikti.append('   +%7.2f  SEN   CG_SHOP alt=%s  %s'
                         % (t, b[1] if len(b) > 1 else '?', b.hex(' ')))
        elif y == 'S>C':
            for cer in _shop_cerceveler(b):
                shop_no += 1
                cikti.append('   +%7.2f  OYUN  0x26 GC_SHOP  boy=%d  alt=%s'
                             % (t, len(cer), cer[3] if len(cer) > 3 else '?'))

    # 3) 0x26 ham dökümü — asıl çözeceğimiz yer
    cikti.append('\n3) 0x26 GC_SHOP HAM DÖKÜM (ilk 12 çerçeve, tam bayt)')
    sayac = 0
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        if _yon(kport, hport) != 'S>C' or not yuk:
            continue
        for cer in _shop_cerceveler(bytes(yuk)):
            sayac += 1
            if sayac > 12:
                break
            t = (z - t0) / 1e6
            cikti.append('\n   --- çerçeve %d  (+%.2f sn, %d bayt) ---'
                         % (sayac, t, len(cer)))
            for satir in range(0, min(len(cer), 320), 16):
                parca = cer[satir:satir + 16]
                cikti.append('   %04x  %-47s  %s'
                             % (satir, parca.hex(' '), _metin(parca)))
            if len(cer) > 320:
                cikti.append('   ... (%d bayt daha)' % (len(cer) - 320))
        if sayac > 12:
            break
    if not sayac:
        cikti.append('   (0x26 görülmedi — dükkân açıldı mı? proxy akışta mı?)')

    # 4) Varlık listesi: dükkânlar nasıl görünüyor
    if varliklar:
        cikti.append('\n4) KAYIT SIRASINDA GÖRÜLEN VARLIKLAR '
                     '(dükkân sahibi nasıl listeleniyor?)')
        for v in varliklar[:60]:
            cikti.append('   tip=%-2s vid=%-10s vnum=%-6s ad=%r'
                         % (v.get('tip'), v.get('vid'), v.get('vnum'),
                            v.get('ad') or v.get('isim')))

    metin = '\n'.join(cikti)
    print(metin)
    txt = os.path.splitext(yol)[0] + '.txt'
    try:
        with open(txt, 'w', encoding='utf-8') as f:
            f.write(metin + '\n')
        print('\n>>> Döküm dosyaya da yazıldı: %s' % txt)
        print('    Bu dosyayı bana yapıştır — 0x26 yapısını çözerim.')
    except Exception as e:                              # noqa: BLE001
        print('döküm yazılamadı: %s' % e)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pazar (oyuncu dükkânı) paket kaydı')
    ap.add_argument('--sure', type=int, default=120)
    ap.add_argument('--dosya')
    a = ap.parse_args(argv)
    varliklar = []
    if a.dosya:
        yol = a.dosya
        yan = os.path.splitext(yol)[0] + '_varliklar.json'
        if os.path.exists(yan):
            try:
                with open(yan, encoding='utf-8') as f:
                    varliklar = json.load(f)
            except Exception:                           # noqa: BLE001
                pass
    else:
        yol, varliklar = kaydet(a.sure)
        if yol and varliklar:
            try:
                with open(os.path.splitext(yol)[0] + '_varliklar.json', 'w',
                          encoding='utf-8') as f:
                    json.dump(varliklar, f, ensure_ascii=False, indent=1)
            except Exception:                           # noqa: BLE001
                pass
    if yol:
        analiz(yol, varliklar)


if __name__ == '__main__':
    main()
