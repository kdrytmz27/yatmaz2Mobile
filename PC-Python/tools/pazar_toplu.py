# -*- coding: utf-8 -*-
"""
PAZAR TOPLU TARAMA — tek geçişte bütün dükkânlar.

Neden böyle: sunucu dükkân içeriğini yalnız TIKLAYINCA gönderiyor (0x26,
3449 bayt). Toplu veren bir paket yok. Ama /api/log büyük paketleri kırpıyor,
o yüzden içeriği oradan okuyamıyoruz.

Çözüm: okumayı tcpdump'a yaptırıyoruz — senin ilk kaydındaki gibi paketler TAM
geliyor. Akış:

    1. Telefonda tcpdump'ı başlat
    2. Menzildeki bütün dükkânlara arka arkaya tıkla (~0.3 sn/dükkân)
    3. tcpdump'ı durdur, kaydı çek
    4. İçindeki BÜTÜN 0x26'ları tek seferde çöz → tam içerik

Tıklama iki yoldan olabilir:
    --enjekte  (varsayılan) bot kendi tıklar; enjeksiyon kapıları gerekir
    --elle     sen gezip tıklarsın, bot yalnız kaydeder ve çözer

SATIN ALMA YOK. Yalnız dükkân açma (0x1A+0x07) ve kapatma (0x32 00).

KULLANIM
--------
    python tools/pazar_toplu.py --menzil 1500
    python tools/pazar_toplu.py --elle --sure 180
"""

import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
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
import pazar_paket as pp                                # noqa: E402
import pazar_canli as pc                                # noqa: E402
import pazar_tara as pz                                 # noqa: E402

_sp = importlib.util.spec_from_file_location(
    'tambot', os.path.join(_KOK, 'tambot.py'))
tb = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(tb)

UZAK_YOL = '/sdcard/r2_pazar_toplu.pcap'


def _adb():
    a = kb.adb_bul()
    if not a:
        print('X adb bulunamadı.')
        return None
    dev = subprocess.run([a, 'devices'], capture_output=True,
                         timeout=20).stdout.decode('utf-8', 'replace')
    if '\tdevice' not in dev:
        print('X Cihaz bağlı değil.')
        return None
    if 'uid=0' not in kb.kabuk(a, "su -c 'id'"):
        print('X root (su) çalışmıyor — tcpdump için gerekli.')
        return None
    return a


def kayit_basla(adb, sure):
    """tcpdump'ı arka planda başlat (paketler TAM, kırpma yok)."""
    arayuz = kb.arayuz_bul(adb)
    kb.kabuk(adb, "su -c 'pkill -f r2_pazar_toplu.pcap'")
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    komut = ("su -c 'nohup timeout %d tcpdump -i %s -U -s 0 -w %s tcp portrange 30000-30100 "
             ">/dev/null 2>&1 &'" % (sure, arayuz, UZAK_YOL))
    kb.kabuk(adb, komut, sure=5)
    time.sleep(1.5)                 # tcpdump açılsın
    return arayuz


def kayit_bitir(adb):
    kb.kabuk(adb, "su -c 'pkill -f r2_pazar_toplu.pcap'")
    time.sleep(0.8)
    os.makedirs(os.path.join(_KOK, 'log'), exist_ok=True)
    yerel = os.path.join(_KOK, 'log',
                         'pazar_toplu_%s.pcap' % time.strftime('%Y%m%d_%H%M%S'))
    subprocess.run([adb, 'pull', UZAK_YOL, yerel], capture_output=True, timeout=300)
    kb.kabuk(adb, "su -c 'rm -f %s'" % UZAK_YOL)
    if not os.path.exists(yerel) or os.path.getsize(yerel) < 100:
        return None
    return yerel


def dukkanlari_listele(api, azami_ham):
    d = api.get('/api/durum') or {}
    k = d.get('konum') or {}
    bx, by = int(k.get('x', 0) or 0), int(k.get('y', 0) or 0)
    tik = int(d.get('tik', 0) or 0)
    vs = api.get('/api/varliklar', n=500) or []
    out = []
    for v in vs:
        if not (pp.dukkan_mi(v) and v.get('vid')):
            continue
        vx, vy = v.get('x'), v.get('y')
        if vx is None:
            continue
        m = math.hypot(int(vx) - bx, int(vy) - by)
        if azami_ham and m > azami_ham:
            continue
        out.append((m, int(v['vid']), v.get('ad') or '?', int(vx), int(vy)))
    out.sort()
    return bx, by, tik, out


def _konum(api):
    d = api.get('/api/durum') or {}
    k = d.get('konum') or {}
    return (int(k.get('x', 0) or 0), int(k.get('y', 0) or 0),
            int(d.get('tik', 0) or 0))


def yuru(api, hx, hy, sure=12.0, yakin=400):
    """Hedefe yürü. Döner: varıldı mı.

    Pazar düz ve açık alan; tambot'un duvar kaçınmalı rotasına gerek yok.
    CG_MOVE (bFunc=1) gönderip konumu izliyoruz."""
    t0 = time.time()
    son = None
    takildi = 0
    while time.time() - t0 < sure:
        bx, by, tik = _konum(api)
        if not (bx and by):
            return False
        m = math.hypot(hx - bx, hy - by)
        if m <= yakin:
            api.enjekte(tb.paket_hareket(bx, by, tik, bfunc=0,
                                         brot=tb.yon_bayti(hx - bx, hy - by)))
            return True
        if son is not None and math.hypot(bx - son[0], by - son[1]) < 60:
            takildi += 1
            if takildi >= 6:
                return False                    # ilerlemiyor
        else:
            takildi = 0
        son = (bx, by)
        brot = tb.yon_bayti(hx - bx, hy - by)
        api.enjekte(tb.paket_hareket(hx, hy, tik, bfunc=1, brot=brot))
        time.sleep(0.45)
    return False


def _shop_cevabi_var(api, onceki):
    """Log'da YENİ bir gelen 0x26 belirdi mi? İçerik kırpık olabilir; burada
    yalnız 'sunucu cevapladı mı' sinyali arıyoruz (asıl veri tcpdump'ta)."""
    simdi = set()
    for r in (api.get('/api/log', n=120) or []):
        if r.get('opcode') == pp.BASLIK and not r.get('giden'):
            simdi.add((r.get('zaman'), r.get('boy')))
    return bool(simdi - onceki), simdi


def _shop_anahtarlari(api):
    out = set()
    for r in (api.get('/api/log', n=120) or []):
        if r.get('opcode') == pp.BASLIK and not r.get('giden'):
            out.add((r.get('zaman'), r.get('boy')))
    return out


def _tikla_dogrula(api, vid, hx, hy, ara, deneme=2):
    """Dükkâna tıkla; cevap gelmezse konumu TAZELEYİP bir kez daha dene."""
    for n in range(deneme):
        bx, by, tik = _konum(api)
        if not (bx and by):
            return False
        onceki = _shop_anahtarlari(api)
        brot = tb.yon_bayti(hx - bx, hy - by)
        api.enjekte(tb.paket_tikla_tam(vid, bx, by, tik, brot=brot))
        time.sleep(ara)
        var, _ = _shop_cevabi_var(api, onceki)
        api.enjekte(tb.paket_dukkan_kapat())
        if var:
            return True
        time.sleep(0.1)
    return False


def tur_tara(api, adb, a, adlar, bulundu=None, gunluk=None):
    """Yürü-tara-yürü + CANLI okuma. Döner: {vid: {ad, esyalar}}.

    Okuma tcpdump AKIŞINDAN yapılır (dosyaya yazıp sonda çekmek yerine), böylece
    her dükkân okunur okunmaz elimize geçer ve TCP birleştirmesi sayesinde
    parçalara bölünmüş paketler de yakalanır."""
    taranan = set()
    isimler = {}
    toplanan = {}
    bulundu = bulundu or (lambda vid, ad, n: None)
    # İlerleme panele gitsin; print yalnız konsola yazıyordu.
    yaz = gunluk or print

    def _shop(d):
        vid = d['sahip_vid']
        if vid and d['esyalar'] and vid not in toplanan:
            toplanan[vid] = d['esyalar']
            # Eşyaları da veriyoruz ki dinleyen (panel) tur bitmeden
            # listesine ekleyebilsin.
            bulundu(vid, isimler.get(vid, 'vid %d' % vid), d['esyalar'])

    okuyucu = pc.CanliOkuyucu(_shop, yaz)
    if not okuyucu.basla():
        return {}, {}

    sure = a.sure or 900
    yaz('tur başladı — canlı okuma açık')
    t0 = time.time()
    durak = 0
    try:
        while time.time() - t0 < sure:
            bx, by, tik, liste = dukkanlari_listele(api, 0)
            if not liste:
                yaz('  dükkân görünmüyor — pazarda mısın?')
                break
            for _m, vid, ad, _x, _y in liste:
                isimler[vid] = ad
            menzilde = [t for t in liste
                        if t[0] <= a.menzil and t[1] not in taranan]
            if menzilde:
                durak += 1
                yaz('[durak %d] %d dükkân menzilde   okunan: %d'
                    % (durak, len(menzilde), len(toplanan)))
                for i, (m, vid, ad, hx, hy) in enumerate(menzilde, 1):
                    bx2, by2, tik2 = _konum(api)
                    if not (bx2 and by2):
                        break
                    brot = tb.yon_bayti(hx - bx2, hy - by2)
                    api.enjekte(tb.paket_tikla_tam(vid, bx2, by2, tik2,
                                                   brot=brot))
                    time.sleep(a.ara)
                    api.enjekte(tb.paket_dukkan_kapat())
                    taranan.add(vid)
                continue
            kalan = [t for t in liste if t[1] not in taranan]
            if not kalan:
                yaz('görünen bütün dükkânlar tarandı')
                break
            m, vid, ad, hx, hy = kalan[0]
            yaz('→ %s yönüne yürüyorum (%.1f m)' % (ad[:26], m / 100.0))
            if not yuru(api, hx, hy):
                yaz('   varamadım, atlıyorum')
                taranan.add(vid)
            time.sleep(0.3)
    except KeyboardInterrupt:
        yaz('elle durduruldu')
    time.sleep(1.5)                     # son paketler gelsin
    okuyucu.dur()
    basari = (100.0 * len(toplanan) / len(taranan)) if taranan else 0
    yaz('tur bitti: %d tıklama, %d dükkân okundu (%%%.0f)'
        % (len(taranan), len(toplanan), basari))
    return toplanan, isimler


def onbellege_yaz(toplanan, isimler, adlar, kanal=0):
    """Toplananı önbelleğe ekle. Döner: (dükkân, eşya) sayısı."""
    t = pz.PazarTarayici.__new__(pz.PazarTarayici)
    t.adlar = adlar
    t.dukkanlar = {}
    t.ONBELLEK = pz.PazarTarayici.ONBELLEK
    t.gunluk = print
    t.onbellek_yukle()
    esya = 0
    for vid, esyalar in toplanan.items():
        t.dukkanlar[(kanal, vid)] = {
            'vid': vid, 'kanal': kanal,
            'ad': isimler.get(vid, 'vid %d' % vid),
            'esyalar': esyalar, 'zaman': time.time()}
        esya += len(esyalar)
    t.onbellek_kaydet()
    return len(toplanan), esya


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pazar toplu tarama (tcpdump)')
    ap.add_argument('--menzil', type=int, default=1500,
                    help='ham birim; 0 = sınırsız (1500 = 15 m)')
    ap.add_argument('--ara', type=float, default=0.3,
                    help='tıklamalar arası (sn)')
    ap.add_argument('--elle', action='store_true',
                    help='bot tıklamasın; sen gez ve tıkla, bot kaydetsin')
    ap.add_argument('--tur', action='store_true',
                    help='YÜRÜ-TARA-YÜRÜ: pazarın tamamını gez (önerilen)')
    ap.add_argument('--sure', type=int, default=0,
                    help='kayıt süresi (sn); 0 = otomatik hesapla')
    ap.add_argument('--dosya', help='var olan pcap\'i çöz (tarama yapma)')
    a = ap.parse_args(argv)

    adlar = pz.EsyaAdlari()
    print('eşya tablosu: %s (%d eşya)'
          % (os.path.basename(adlar.yol or 'YOK'), len(adlar.tablo)))

    if a.dosya:
        return coz_ve_yaz(a.dosya, adlar, {})

    adb = _adb()
    if not adb:
        return
    api = tb.Api()

    isimler = {}
    if a.tur:
        d = api.get('/api/durum') or {}
        p = d.get('proxy') or {}
        if not (p.get('acik') and p.get('bagli') and p.get('enjeksiyon')):
            print('X Enjeksiyon kapıları kapalı (tur için gerekli).')
            return
        toplanan, isimler = tur_tara(api, adb, a, adlar)
        if not toplanan:
            print('X Hiç dükkân okunamadı.')
            return
        kanal = 0
        try:
            pr = (api.get('/api/durum') or {}).get('proxy') or {}
            kanal = int(pr.get('kanal', 0) or 0) or tb.port_kanali(
                int(pr.get('port', 0) or 0))
        except Exception:                               # noqa: BLE001
            pass
        nd, ne = onbellege_yaz(toplanan, isimler, adlar, kanal)
        print('ch%s: %d dükkân, %d eşya önbelleğe yazıldı.'
              % (kanal or '?', nd, ne))
        print('\nArama için: python pazar_panel.py')
        return
    if a.elle:
        sure = a.sure or 180
        print('ELLE mod: %d sn kayıt. Pazarda gez ve dükkânlara TIKLA.' % sure)
        kayit_basla(adb, sure + 10)
        try:
            t0 = time.time()
            while time.time() - t0 < sure:
                time.sleep(2.0)
                for v in (api.get('/api/varliklar', n=200) or []):
                    if pp.dukkan_mi(v) and v.get('vid'):
                        isimler[int(v['vid'])] = v.get('ad') or '?'
                kalan = sure - (time.time() - t0)
                print('\r  kalan %3.0f sn   (bilinen dükkân adı: %d)'
                      % (kalan, len(isimler)), end='')
        except KeyboardInterrupt:
            yaz('elle durduruldu')
        print()
    else:
        d = api.get('/api/durum') or {}
        p = d.get('proxy') or {}
        if not (p.get('acik') and p.get('bagli') and p.get('enjeksiyon')):
            print('X Enjeksiyon kapıları kapalı. --elle ile de çalışabilirsin.')
            return
        bx, by, tik, liste = dukkanlari_listele(api, a.menzil)
        if not liste:
            print('X Menzilde dükkân yok (menzili büyüt ya da aralarına yürü).')
            return
        isimler = {vid: ad for _m, vid, ad, _x, _y in liste}
        sure = a.sure or int(len(liste) * (a.ara + 0.25)) + 15
        print('%d dükkân, ~%d sn sürecek. tcpdump başlıyor...' % (len(liste), sure))
        kayit_basla(adb, sure + 15)
        for i, (m, vid, ad, hx, hy) in enumerate(liste, 1):
            brot = tb.yon_bayti(hx - bx, hy - by)
            api.enjekte(tb.paket_tikla_tam(vid, bx, by, tik, brot=brot))
            time.sleep(a.ara)
            api.enjekte(tb.paket_dukkan_kapat())
            print('\r  [%3d/%3d] %-28s %5.1f m' % (i, len(liste), ad[:28],
                                                   m / 100.0), end='')
            time.sleep(0.05)
        print()

    print('kayıt kapatılıyor...')
    yerel = kayit_bitir(adb)
    if not yerel:
        print('X Kayıt alınamadı.')
        return
    print('kayıt: %s (%.1f KB)' % (yerel, os.path.getsize(yerel) / 1024.0))
    coz_ve_yaz(yerel, adlar, isimler)


def coz_ve_yaz(yol, adlar, isimler):
    """pcap'teki bütün 0x26'ları çöz, önbelleğe ekle, özet yaz."""
    dukkanlar = pp.pcap_coz(yol)
    benzersiz = {}
    for d in dukkanlar:
        if d['esyalar']:
            benzersiz[d['sahip_vid']] = d
    print('\n' + '=' * 70)
    print('ÇÖZÜLEN: %d dükkân (%d ham paket)' % (len(benzersiz), len(dukkanlar)))
    print('=' * 70)
    if not benzersiz:
        print('Hiç dükkân içeriği yakalanmadı.')
        print('  - Enjekte modunda: tıklama sunucuya geçmiyor olabilir')
        print('  - --elle ile dene: sen tıkla, bot kaydetsin')
        return

    t = pz.PazarTarayici.__new__(pz.PazarTarayici)
    t.adlar = adlar
    t.dukkanlar = {}
    t.ONBELLEK = pz.PazarTarayici.ONBELLEK
    t.gunluk = print
    t.onbellek_yukle()
    kanal = 0
    try:
        api = tb.Api()
        pr = (api.get('/api/durum') or {}).get('proxy') or {}
        kanal = int(pr.get('kanal', 0) or 0) or tb.port_kanali(
            int(pr.get('port', 0) or 0))
    except Exception:                                   # noqa: BLE001
        pass

    esya_say = 0
    for vid, d in benzersiz.items():
        t.dukkanlar[(kanal, vid)] = {
            'vid': vid, 'kanal': kanal,
            'ad': isimler.get(vid, 'vid %d' % vid),
            'esyalar': d['esyalar'], 'zaman': time.time()}
        esya_say += len(d['esyalar'])
    t.onbellek_kaydet()
    print('ch%s: %d dükkân, %d eşya önbelleğe yazıldı.'
          % (kanal or '?', len(benzersiz), esya_say))

    sayim = {}
    for d in benzersiz.values():
        for e in d['esyalar']:
            ad = adlar.ad(e['vnum'])
            n, ucuz = sayim.get(ad, (0, e['fiyat']))
            sayim[ad] = (n + 1, min(ucuz, e['fiyat']))
    print('\nEN ÇOK BULUNAN 15 EŞYA           adet   en ucuz')
    for ad, (n, ucuz) in sorted(sayim.items(), key=lambda kv: -kv[1][0])[:15]:
        print('   %-32s %4d   %12s' % (ad[:32], n, pp._yang(ucuz)))
    print('\nArama için: python pazar_panel.py')


if __name__ == '__main__':
    main()
