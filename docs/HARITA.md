# Gidilemez Yerler (engel haritası)

**1 Eyl 2026** — oyunun kendi çarpışma verisi bulundu ve bota bağlandı.
Bot artık duvara girmiyor.

## Veri nerede

Romia2 bir Unity oyunu ama harita verisi **klasik Metin2 düzeninde**
duruyor. Oyunun indirdiği varlık paketlerinde (`UnityCache`) her arazi
sektörü için bir `attr.txt` metin varlığı var — orijinal Metin2'nin
`attr.atr` dosyası:

```
Assets/_DSoft/Map/metin2_map_c1/000000/attr.txt
```

**18 harita, 322 sektör.**

## Biçim

| ofset | tür | anlam |
|---|---|---|
| +0 | 2 bayt | imza `4A 0A` |
| +2 | u16 | genişlik = 256 |
| +4 | u16 | yükseklik = 256 |
| +6 | 65536 B | hücre başına 1 bayt öznitelik |

- 1 hücre = **100 ham birim** (1 m)
- 1 sektör = 256×256 hücre = **25600 ham birim**
- sektör klasörü = `%03d%03d` % (sektör_x, sektör_y)
- hücre indeksi = `cy * 256 + cx`
- **bit 0 (0x01) = ENGEL**

## Engel biti nasıl bulundu

Tahmin edilmedi, **ölçüldü**. Kullanıcının oyunda gerçekten yürüyerek
kaydettiği 241 rota noktası elde vardı; hepsi tanım gereği geçilebilir.
Bütün haritalar × sektör/hücre sıralamaları × ilk 4 bit denendi ve her
aday için **kazanç** hesaplandı — rotanın serbestlik oranı eksi
haritanın kendi serbestlik oranı:

| harita | bit | rota serbest | harita serbest | kazanç |
|---|---|---|---|---|
| metin2_map_c1 | 0 | **%100.0** | %41.8 | **+58.2** |
| metin2_map_c1 | 3 | %93.8 | %38.0 | +55.8 |
| metin2_map_a1 | 0 | %78.0 | %50.1 | +27.9 |

Kazanç ölçütü şart. İlk denemede yalnızca "rota %100 serbest"e
bakılmıştı ve `metin2_map_n_flame_01` üç ayrı bitle %100 aldı — o
bitler o haritada hiç set değildi, yani ölçüt hiçbir şey öğretmiyordu.

%58'i kapalı bir haritada 241 noktanın 241'inin de açık hücreye düşmesi
rastlantı değil.

## Taban konumu — `atlasinfo.txt`

Izgara tek başına yetmiyor: dünya konumu (935413, 237836) ızgaranın
neresine düşüyor?

Cevap oyunun kendi dosyasında: **`Assets/_DSoft/GameData/atlasinfo.txt`**
— Metin2'nin dünya atlası. Sekmeyle ayrılmış satırlar:

```
metin2_map_c1	921600	204800	4	5
(harita)	(taban x)	(taban y)	(sx)	(sy)
```

**18 haritanın hepsi buradan hizalanıyor**, gezmeye gerek yok.

### Çapraz doğrulama

Atlas bulunmadan önce taban, kayıtlı rotalardan ölçülüyordu
(`tools/harita_hizala.py`) ve iki harita hizalanabilmişti. Atlas o iki
değeri **birebir** doğruladı:

| harita | rotadan ölçülen | atlastan okunan |
|---|---|---|
| `metin2_map_c1` | 921600, 204800 (241 noktadan) | 921600, 204800 |
| `metin2_map_c3` | 819200, 204800 (145 noktadan) | 819200, 204800 |

İki bağımsız kaynağın aynı sayıyı vermesi hem atlas okumasını hem ölçüm
yöntemini doğruluyor.

### Ölçüm yöntemi neden yetmiyordu

`map_a2`'nin tabanı **999900, 999900** — sektör boyu 25600'ün katı
değil. Rotadan ölçme sektör ızgarasına oturtarak arıyor, dolayısıyla o
haritayı asla bulamazdı. Atlas olmasa 18 haritanın kaçının böyle
olduğunu da bilemezdik.

`tools/harita_hizala.py` ve `harita_hizala_canli.py` duruyor: atlasta
olmayan bir harita çıkarsa ya da atlas okuması şüpheliyse ölçüm yolu
hâlâ kullanılabilir.

### Öneksiz ad kazanır

Atlasta hem `metin2_map_spiderdungeon_02` hem
`season1/metin2_map_spiderdungeon_02` var, **farklı tabanlarla**. Son
gelen kazansaydı season1 sürümü öneksizini ezerdi ve o haritanın
duvarları 1024 m kaymış çizilirdi. attr yolları öneksiz olduğu için
öneksiz kayıt kazanıyor.

## Araçlar

```bash
python tools/harita_cikar.py     # cihazdan çek, harita/ dizinine yaz
python tools/harita_hizala.py    # kayıtlı rotalardan tabanı ölç
```

Çıktı `harita/` dizininde, **toplam 2.5 MB** (hücre başına 1 bit).
İndirilen ~145 MB Unity paketi işi bitince siliniyor.

## Botta kullanımı

`tools/harita_engel.py` → `Dunya.yukle()`, `engel_mi`, `gorus_acik`,
`yol_bul` (A*, 4 m ızgara, köşe kesmesiz, sonra görüş tabanlı
düzleştirme).

`tambot._yuru` her bacakta `_duvarsiz_hedef` çağırıyor:

1. Hedefin önü açıksa hedefe dokunulmuyor
2. Kapalıysa A* ile dolanılıyor, ara noktalar önbelleğe alınıyor
3. **Harita yoksa, hiza yoksa ya da yol bulunamazsa hedef aynen
   dönüyor** — bot en kötü ihtimalle eskisi kadar iyi çalışıyor

Üçüncüsü bilinçli: yanlış bir duvar verisi yüzünden botun durması,
duvara girmesinden daha kötü olurdu.

Ölçüm: yürünmüş 240 rota bacağının **hiçbiri** saptırılmıyor (gereksiz
yere devreye girmiyor), buna karşılık rastgele nokta çiftlerinin yalnızca
%12'sinin görüşü açık.

## R2 Panel radarında

Duvarlar radarın **arka planına** çiziliyor (`EngelHarita.java` +
`HaritaView.duvarCiz`). Harita sekmesinde **Duvar** düğmesiyle açılıp
kapanıyor, tercih kaydediliyor.

Veri APK'nın `assets/harita/` dizininde — 18 harita, sıkıştırılmış
hâliyle APK'ya **1.3 MB** ekliyor. `harita_cikar.py` ve
`harita_hizala.py` çıktıyı oraya da kopyalıyor ki masaüstü botuyla
telefon aynı veriyi görsün; ayrışırlarsa panel duvarları kaymış çizerdi
ve teşhisi zor olurdu. (Kopyalamak yetmiyor, APK yeniden derlenmeli.)

**Neden önbellek bitmap:** radar 60 fps çiziyor; her karede ~200×200
hücre boyamak çizim döngüsünü öldürürdü. Görüntüden 160 px geniş bir
bitmap bir kez üretilip her karede tek `drawBitmap` ile kaydırılıyor.
Oyuncu payı aşınca, zum ya da flip değişince yeniden üretiliyor.

Radarın sol üstünde katmanın durumu yazıyor: harita adı, "harita
hizasız" ya da "duvar yok". Üçünün çaresi farklı olduğu için tek bir
"çizilmiyor" mesajı yetmezdi.

`Math.floorDiv` şart: Java'nın `/` işleci negatifte sıfıra doğru
kırpıyor (`-50/100 = 0`), bu da taban konumunun solundaki bir noktayı
harita **içindeki** 0. hücreye düşürüp kenarın hemen dışını "açık"
gösterirdi. Python tarafı `//` ile aşağı yuvarlıyor; iki taraf aynı
hücreyi göstermeli.

## Kayıtlı rota ağı ne oldu

`_agdan_yuru` duruyor. İkisi çelişmiyor, tamamlıyor: engel haritası
"buradan geçilmez" der, kayıtlı rota "buradan geçmek **mantıklı**" der.
A* en kısa yolu arar ve en kısa yol dar geçitlerden sürtünerek geçebilir;
senin yürüdüğün yol daha iyi bir güzergâh.
