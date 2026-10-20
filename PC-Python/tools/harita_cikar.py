# -*- coding: utf-8 -*-
"""
Oyunun GİDİLEMEZ YER haritasını çıkarır.

NE BULUNDU
----------
1 Eyl 2026: Romia2 bir Unity oyunu ama harita verisi klasik Metin2
düzeninde duruyor. Oyunun varlık paketinde her arazi sektörü için bir
`attr.txt` metin varlığı var — orijinal Metin2'nin `attr.atr` dosyası:

    Assets/_DSoft/Map/metin2_map_c1/000000/attr.txt

18 harita, 322 sektör. Biçim ölçüldü:

    +0  2 bayt   imza (4A 0A)
    +2  u16      genişlik = 256
    +4  u16      yükseklik = 256
    +6  65536 B  hücre başına 1 bayt öznitelik

Bir hücre 100 ham birim, bir sektör 256x256 hücre = 25600 ham birim.

    bit 0 (0x01) = ENGEL — buraya girilemez

ENGEL BİTİ NASIL DOĞRULANDI
---------------------------
Tahmin edilmedi, ÖLÇÜLDÜ. Kullanıcının oyunda gerçekten yürüyerek
kaydettiği 241 rota noktası elimizde; hepsi tanım gereği geçilebilir.
Bütün haritalar x bütün sektör/hücre sıralamaları x ilk 4 bit denendi
ve her aday için "rota serbestliği eksi haritanın kendi serbestliği"
(KAZANÇ) hesaplandı:

    metin2_map_c1  bit0   rota %100.0 serbest, harita %41.8  -> +58.2
    metin2_map_a1  bit0   rota  %78.0 serbest, harita %50.1  -> +27.9

Kazanç ölçütü şart: yalnızca "rota %100 serbest" bakılsaydı, o bitin
hiç set olmadığı bir harita da kazanırdı — nitekim ilk denemede
metin2_map_n_flame_01 üç ayrı bitle %100 aldı ve hepsi anlamsızdı.

%58'i kapalı bir haritada 241 noktanın 241'inin de açık hücreye
düşmesi rastlantı değil. 1. köy = metin2_map_c1.

KULLANIM
--------
    python tools/harita_cikar.py            # cihazdan çek ve çıkar
    python tools/harita_cikar.py --paket X  # elde duran paketten

ÇIKTI: harita/harita.json + harita/<harita>.engel (hücre başına 1 bit)
"""
import json
import os
import subprocess
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
_CIKTI = os.path.join(_KOK, 'harita')

OYUN_PAKETI = 'com.RGames.Romia2Mobil'
HUCRE = 100          # bir attr hücresi kaç ham birim
IZGARA = 256         # sektör başına hücre
SEKTOR = HUCRE * IZGARA
BASLIK = 6           # attr dosyasının başlık uzunluğu
ENGEL_BITI = 0x01

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def adb_bul():
    for a in (os.environ.get('ADB_YOLU'), 'adb',
              os.path.expanduser(
                  r'~\AppData\Local\Android\Sdk\platform-tools\adb.exe'),
              r'C:\Program Files\platform-tools\adb.exe'):
        if not a:
            continue
        try:
            if subprocess.run([a, 'version'], capture_output=True,
                              timeout=10).returncode == 0:
                return a
        except Exception:
            continue
    return None


def paketleri_cek(adb, hedef):
    """
    Cihazdaki Unity paketlerini indirir.

    Harita verisi APK'nın içinde değil, oyunun indirdiği paketlerde
    (UnityCache). Hangisinde olduğunu bilmiyoruz; hepsini alıp içine
    bakmak, adı tahmin etmekten güvenilir.
    """
    ortam = dict(os.environ, MSYS_NO_PATHCONV='1')
    kok = ('/sdcard/Android/data/%s/files/UnityCache' % OYUN_PAKETI)
    p = subprocess.run(
        [adb, 'shell', "su -c 'find %s -name __data -size +200k'" % kok],
        capture_output=True, timeout=120, env=ortam)
    yollar = [x.strip() for x in
              (p.stdout or b'').decode('utf-8', 'replace').splitlines()
              if x.strip().endswith('__data')]
    if not yollar:
        return []
    os.makedirs(hedef, exist_ok=True)
    yerel = []
    for i, uzak in enumerate(yollar):
        y = os.path.join(hedef, 'paket_%02d' % i)
        if not os.path.exists(y):
            subprocess.run([adb, 'pull', uzak, y],
                           capture_output=True, timeout=300, env=ortam)
        if os.path.exists(y):
            yerel.append(y)
    return yerel


def atlas_oku(paketler):
    """
    Haritaların TABAN KONUMUNU oyunun kendi atlasından okur.

    Assets/_DSoft/GameData/atlasinfo.txt — Metin2'nin dünya atlası.
    Satır biçimi sekmeyle ayrılmış:

        metin2_map_c1	921600	204800	4	5
        (harita adı)	(taban x)	(taban y)	(sx)	(sy)

    NEDEN ÖNEMLİ
    -----------
    Taban konumu olmadan ızgara işe yaramıyor: dünya konumunun ızgaranın
    neresine düştüğü bilinmiyor. Bir süre kayıtlı rotalardan ölçtük
    (tools/harita_hizala.py) ama o yöntem yalnızca gezilmiş haritalar
    için çalışıyor ve 18 haritanın 16'sı hizasız kalmıştı.

    DOĞRULAMA
    ---------
    Atlas, rotalardan ÖLÇTÜĞÜMÜZ iki değeri birebir doğruluyor:

        metin2_map_c1  921600, 204800   (241 rota noktasından ölçülen)
        metin2_map_c3  819200, 204800   (145 rota noktasından ölçülen)

    İki bağımsız kaynağın aynı sayıyı vermesi, hem atlas okumasının hem
    ölçüm yönteminin doğru olduğunu gösteriyor.
    """
    import UnityPy
    for yol in paketler:
        try:
            ortam = UnityPy.load(yol)
        except Exception:
            continue
        for kap, nesne in ortam.container.items():
            if 'atlasinfo' not in kap.lower():
                continue
            try:
                ham = nesne.read().m_Script
            except Exception:
                continue
            if isinstance(ham, str):
                ham = ham.encode('utf-8', 'surrogateescape')
            metin = bytes(ham).decode('utf-8', 'replace')
            atlas = {}
            for satir in metin.splitlines():
                parca = satir.replace('\t', ' ').split()
                if len(parca) < 5:
                    continue
                try:
                    tx, ty = int(parca[1]), int(parca[2])
                    sx, sy = int(parca[3]), int(parca[4])
                except ValueError:
                    continue
                # "season2/metin2_map_a2_1" gibi önekli adlar var; attr
                # yolları öneksiz olduğu için son parça alınıyor.
                #
                # ÖNEKSİZ OLAN KAZANIR: atlasta hem
                # "metin2_map_spiderdungeon_02" hem
                # "season1/metin2_map_spiderdungeon_02" var, farklı
                # tabanlarla. Son gelen kazansaydı season1 sürümü
                # öneksizini ezerdi ve o haritanın duvarları 102400 ham
                # (1024 m) kaymış çizilirdi.
                ham_ad = parca[0].replace('\\', '/')
                ad = ham_ad.split('/')[-1]
                onekli = '/' in ham_ad
                if ad in atlas and onekli:
                    continue
                atlas[ad] = (tx, ty, sx, sy)
            return atlas
    return {}


def attr_topla(paketler):
    """Paketlerden {harita: {sektör: gövde}} çıkarır."""
    import UnityPy
    toplam = {}
    for yol in paketler:
        try:
            ortam = UnityPy.load(yol)
        except Exception:
            continue
        for kap, nesne in ortam.container.items():
            if nesne.type.name != 'TextAsset':
                continue
            p = kap.replace('\\', '/').split('/')
            if len(p) < 3 or not p[-1].lower().startswith('attr'):
                continue
            harita, sektor = p[-3], p[-2]
            if not (len(sektor) == 6 and sektor.isdigit()):
                continue
            try:
                ham = nesne.read().m_Script
            except Exception:
                continue
            if isinstance(ham, str):
                ham = ham.encode('utf-8', 'surrogateescape')
            ham = bytes(ham)
            if len(ham) != BASLIK + IZGARA * IZGARA:
                continue
            toplam.setdefault(harita, {})[sektor] = ham[BASLIK:]
    return toplam


def bitlere_paketle(sektorler):
    """
    Sektörleri tek bir engel bit haritasına dizer.

    Bayt başına 1 hücre yerine BİT başına 1 hücre: 8 kat küçük.
    Bot her turda bakacağı için dosyanın bellekte durması gerekiyor.
    """
    sx = max(int(a[:3]) for a in sektorler) + 1
    sy = max(int(a[3:]) for a in sektorler) + 1
    g, y = sx * IZGARA, sy * IZGARA
    paket = bytearray((g * y + 7) // 8)
    for ad, govde in sektorler.items():
        bsx, bsy = int(ad[:3]), int(ad[3:])
        for cy in range(IZGARA):
            satir = govde[cy * IZGARA:(cy + 1) * IZGARA]
            temel = (bsy * IZGARA + cy) * g + bsx * IZGARA
            for cx, v in enumerate(satir):
                if v & ENGEL_BITI:
                    i = temel + cx
                    paket[i >> 3] |= 1 << (i & 7)
    return sx, sy, g, y, bytes(paket)


def assetlere_kopyala():
    """
    Çıkarılan haritayı APK'nın assets dizinine de yazar.

    R2 Panel'in radarı duvarları assets'ten okuyor. İki kopyanın elle
    eşitlenmesi unutulacak bir adım: hizalama yeniden ölçülünce masaüstü
    botu yeni tabanı görür, telefon eski dosyayla kalır ve duvarları
    kaymış çizer. Sessiz ve teşhisi zor bir hata olurdu.

    APK'yı yeniden derlemek yine gerekiyor — burada yapılan yalnızca
    dosyaları doğru yere koymak.
    """
    hedef = os.path.join(_KOK, 'app', 'src', 'main', 'assets', 'harita')
    if not os.path.isdir(os.path.dirname(hedef)):
        return 0                            # APK kaynağı yoksa sorun değil
    os.makedirs(hedef, exist_ok=True)
    import shutil
    n = 0
    for ad in os.listdir(_CIKTI):
        if not (ad.endswith('.engel') or ad == 'harita.json'):
            continue
        shutil.copy2(os.path.join(_CIKTI, ad), os.path.join(hedef, ad))
        n += 1
    return n


def main():
    args = sys.argv[1:]
    print('=' * 74)
    print('HARİTA ÇIKARMA — gidilemez yerler')
    print('=' * 74)

    gecici = os.path.join(_CIKTI, 'paket')
    if '--paket' in args:
        paketler = [args[args.index('--paket') + 1]]
    else:
        adb = adb_bul()
        if not adb:
            print('X adb bulunamadı.')
            return 1
        print('cihazdan paketler indiriliyor (ilk seferde birkaç dakika)...')
        paketler = paketleri_cek(adb, gecici)
        if not paketler:
            print('X Unity paketi bulunamadı. Oyun bir kez açılıp haritaya')
            print('  girmiş olmalı — paketler o zaman iniyor.')
            return 1
    print('paket: %d' % len(paketler))

    try:
        import UnityPy                      # noqa: F401
    except ImportError:
        print('X UnityPy yok.  pip install UnityPy')
        return 1

    print('attr varlıkları taranıyor...')
    toplam = attr_topla(paketler)
    if not toplam:
        print('X hiçbir pakette attr bulunamadı.')
        return 1

    atlas = atlas_oku(paketler)
    print('atlasinfo: %d harita' % len(atlas))

    os.makedirs(_CIKTI, exist_ok=True)
    dizin = {'hucre': HUCRE, 'izgara': IZGARA, 'sektor': SEKTOR,
             'engel_biti': ENGEL_BITI, 'haritalar': {}}
    # Taban konumları ayrı dosyada tutulur: kayıtlı rotalardan ölçülüyor
    # (tools/harita_hizala.py) ve yeniden çıkarınca silinmemeli.
    taban_yolu = os.path.join(_CIKTI, 'tabanlar.json')
    tabanlar = {}
    if os.path.exists(taban_yolu):
        try:
            tabanlar = json.load(open(taban_yolu, encoding='utf-8'))
        except Exception:
            tabanlar = {}

    print()
    print('%-30s %7s %11s %9s %16s' % ('harita', 'sektör', 'hücre', 'kapalı',
                                       'taban'))
    print('-' * 80)
    uyusmaz = []
    for harita in sorted(toplam):
        sektorler = toplam[harita]
        sx, sy, g, y, paket = bitlere_paketle(sektorler)
        with open(os.path.join(_CIKTI, harita + '.engel'), 'wb') as f:
            f.write(paket)
        kapali = sum(bin(b).count('1') for b in paket)

        # Taban ATLASTAN. Ölçümle çelişiyorsa sus kalma — ikisinden biri
        # yanlış demektir ve duvarlar kaymış çizilir.
        taban = tabanlar.get(harita)
        a = atlas.get(harita)
        if a:
            atlas_taban = [a[0], a[1]]
            if taban and list(taban) != atlas_taban:
                uyusmaz.append((harita, taban, atlas_taban))
            taban = atlas_taban
            if (a[2], a[3]) != (sx, sy):
                uyusmaz.append((harita + ' (sektör)', (sx, sy), (a[2], a[3])))
        dizin['haritalar'][harita] = {
            'sx': sx, 'sy': sy, 'g': g, 'y': y,
            'dosya': harita + '.engel',
            'taban': taban,
        }
        print('%-30s %7d %5dx%-5d %8.1f%% %16s'
              % (harita, len(sektorler), g, y, 100.0 * kapali / (g * y),
                 '%d, %d' % tuple(taban) if taban else 'YOK'))
    if uyusmaz:
        print()
        print('! ATLAS ile ÖLÇÜM UYUŞMUYOR:')
        for ad, olculen, atlastan in uyusmaz:
            print('    %-28s ölçüm %s  atlas %s' % (ad, olculen, atlastan))

    with open(os.path.join(_CIKTI, 'harita.json'), 'w',
              encoding='utf-8') as f:
        json.dump(dizin, f, ensure_ascii=False, indent=2, sort_keys=True)

    # İNDİRİLEN PAKETLERİ SİL.
    #
    # 16 Unity paketi ~145 MB tutuyor ve işi bitti: çıkardığımız engel
    # ızgaraları toplam 3 MB. Proje dizininde 145 MB'lık çöp bırakmak,
    # üstelik her çalıştırmada yeniden indirilmediği için bayatlayacak
    # bir kopya bırakmak olurdu. --paket ile dışarıdan verilen dosyaya
    # dokunulmuyor; o kullanıcının kendi dosyası.
    if '--paket' not in args and os.path.isdir(gecici):
        # DOSYA DOSYA sil, rmtree ile değil.
        #
        # UnityPy paketleri okuduktan sonra bazı tutamakları açık
        # bırakıyor; Windows'ta rmtree o yüzden komple başarısız oluyor
        # ve 145 MB olduğu gibi kalıyordu. Tek tek silince kilitli
        # olmayanlar temizleniyor, kalanı da bir sonraki çalıştırmada.
        kalan = 0
        for ad in os.listdir(gecici):
            try:
                os.remove(os.path.join(gecici, ad))
            except Exception:
                kalan += 1
        if not kalan:
            try:
                os.rmdir(gecici)
            except Exception:
                pass
            print('geçici paketler silindi')
        else:
            print('! %d geçici paket silinemedi (dosya kilitli) — '
                  'sonraki çalıştırmada temizlenir' % kalan)

    kopya = assetlere_kopyala()
    hizalanan = sum(1 for h in dizin['haritalar'].values() if h['taban'])
    print()
    print('%d harita yazıldı -> %s' % (len(dizin['haritalar']), _CIKTI))
    if kopya:
        print('%d dosya APK assets dizinine kopyalandı '
              '(panel radarı için — APK yeniden derlenmeli)' % kopya)
    print('taban konumu bilinen: %d / %d'
          % (hizalanan, len(dizin['haritalar'])))
    if hizalanan < len(dizin['haritalar']):
        print()
        print('Taban konumu olmayan haritalar KULLANILAMAZ — dünya')
        print('konumunun ızgaranın neresine düştüğü bilinmiyor. Ölçmek')
        print('için o haritada bir rota kaydedip şunu çalıştır:')
        print('    python tools/harita_hizala.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
