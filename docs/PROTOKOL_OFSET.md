# Romia2 Paket Ofsetleri (byte düzenleri)

Her paketin **nasıl gönderildiği/alındığı** — byte byte. Tümü **little-endian**.
Tip kısaltmaları: `u8`=1 bayt, `u16`=2, `u32`=4, `i32`=4 işaretli, `f32`=4 float,
`char[n]`=n baytlık isim (null biten).

**Doğrulama durumu:**
- ✅ **CANLI** — bizim yakalamalarımızda byte byte doğrulandı.
- ◐ **STANDART** — Metin2 ailesi düzeni + metadata'da alan adı doğrulandı;
  byte değeri/ofset canlı yakalama ile teyit edilmeli.

> Opcode byte değerleri enum ordinal'ından gelir. Canlı doğrulananlar dışındaki
> `header` baytları **?** ile işaretli — `PC_CAPTURE.bat` + `tools/` ile doğrulanır.

---

## 📋 ÖZET — bilinen her şey (29 Ağu 2026 itibarıyla)

### Kapsam

| Yön | Önce | Sonra |
|---|---|---|
| GELEN | %87 | **%97.6** |
| GİDEN | %53.1 | **%99.9** |

### Gelen paketler (sunucu → istemci)

| Opcode | Boy | Paket | Durum |
|---|---|---|---|
| 0x01 | 38 | CHARACTER_ADD (doğuş) | ✅ |
| 0x02 | 5 | CHARACTER_DEL (varlık sil) | ✅ |
| 0x03 | 24 | MOVE (varlık hareketi) | ✅ |
| 0x04 | değişken | CHAT | ✅ |
| **0x05** | **değişken** | **SYNC_POSITION (toplu konum)** | ✅ |
| 0x0D | 5 | ölüm animasyonu | ✅ |
| 0x0E | 5 | ölüm animasyonu | ✅ |
| 0x11 | 14 | kendi puan/durum tiki (+1 = KENDİ vid'imiz, çoğunluk oyuyla okunur) | ✅ |
| 0x13 | 43 | karakter güncelleme | ✅ |
| **0x1A** | **21** | **ITEM_GROUND_ADD (yere düşen eşya)** | ✅ |
| **0x1B** | **5** | **ITEM_GROUND_DEL (eşya kalktı)** | ✅ |
| **0x1F** | **30** | **eşya sahibi** | ✅ |
| 0x26 | değişken | GC_SHOP (pazar) | ✅ |
| 0x3E | 9 | savaş vuruşu | ✅ |
| **0x3F** | **14** | **CAN (vid, can%, can, maksCan)** | ✅ |
| 0x46 | 10 | ölüm bildirimi | ✅ |
| 0x47 | 17 | ? | ◐ |
| 0x6F | 6 | ? | ◐ |
| 0x72 | 6 | ? | ◐ |
| 0x87 | 10 | puan değişimi | ✅ |
| **0x88** | **62** | **VARLIK İSMİ** | ✅ |
| 0xB3 | 8 | ? | ◐ |

### Giden paketler (istemci → sunucu)

Tam tablo için "GİDEN AKIŞ" bölümüne bakın. Özet: `0x02` saldırı,
`0x03` sohbet, `0x07` hareket, `0x08` toplu konum, `0x0B` ?,
`0x0F` eşya topla, `0x34` yetenek, `0x3D` hedef seç.

### Bu turda çözülenlerin etkisi

Aynı yakalama, aynı akışlar — yalnızca tablo tamamlanarak:

| | Önce | Sonra |
|---|---|---|
| doğuş (0x01) | 51 | **245** |
| ölüm (0x02) | 55 | **206** |
| hareket (0x03) | 345 | **859** |
| benzersiz varlık | 114 | **217** |
| yer eşyası | — | **48** (38'i Yang) |
| varlık ismi | — | 5 (oyuncu/binek) |

### Kritik dersler

1. **Aynı bayt yöne göre farklı pakettir.** `0x02` gelen=varlık sil / giden=saldırı.
   `0x1A` gelen=yere düşen eşya (21 bayt) / giden=CG_ON_CLICK (5 bayt).
   Bu ikincisi parser'da 5 bayt sanıldığı için her eşya paketinde 16 bayt kayıyordu.

2. **Length-prefix heuristiği bu protokolde zararlı.** Savaş paketleri
   (`0x3E`/`0x3F`/`0x87`/`0x46`) sabit boyludur, uzunluk öneki taşımaz.
   Heuristik VID baytlarını uzunluk sanıp gerçek paketleri yutuyordu
   (tek yakalamada 1280 bayt).

3. **Eksik tablo yalnızca paket kaçırmaz, sahte paket de üretir.**
   Giden akışta `0x0F` 82 sayılıyordu, doğrusu 24.

4. **Kapsam yüzdesi yanıltıcı ölçüttür.** Doğru paket eklendiğinde ham
   "çözülen bayt" oranı bir akışta %95.6'dan %93.1'e *düştü* — çünkü önceden
   parser çöp veriyi geçerli paket sanıp oranı şişiriyordu. Doğru ölçüt
   yakalanan varlık olaylarıdır.

5. **İstemci her eylemi ayrı TCP segmentinde gönderir.** Giden paketleri
   çözmenin en hızlı yolu bu (`tools/eylem_bul.py`).

6. **Bazı eylemler yanlarındaki konum paketiyle birlikte gitmek zorunda.**
   Paketi doğru kurmak yetmiyor; istemcinin gönderdiği SEGMENTİN tamamı
   gerekiyor:
   - `0x02 CG_ATTACK` tek başına sayılmıyor, `0x08 SYNC_POSITION` şart
   - `0x1A CG_ON_CLICK` tek başına dükkânı açmıyor, `0x07 (bFunc=0 DUR)` şart
   İkisi de canlı denemeyle bulundu. Kural: bir eylem çalışmıyorsa
   yakalamada o eylemin SEGMENT BOYUNA bak — paketinden büyükse yanında
   başka paket vardır.

### Araçlar

| Araç | İşi |
|---|---|
| `PC_YAKALA.bat` | Temiz kayıt (otomatik arayüz, `-U` şart) |
| `PC_EYLEM.bat` | Tek bir eylemin paketini bulur |
| `tools/yakalama_kalite.py` | Kayıt analiz için uygun mu |
| `tools/teshis.py` | Arayüz/IP/root teşhisi |
| `tools/parser_dogrula.py` | Paket seviyesinde doğruluk ölçümü |
| `tools/parser_canli_test.py` | Retransmit/kayıp altında dayanıklılık |
| `tools/toplu_konum_ara.py` | Toplu konum paketi arayıcı |
| `tools/opcode_uzunluk_coz.py` | Bilinmeyen opcode boyu çözücü |
| `tools/eylem_bul.py` | Eylem → paket eşleştirici |
| `tools/akis_analiz.py` | Akış bazlı çerçeveleme analizi |

## ✅ Doğrulanmış çerçeve tablosu (23 Ağu 2026, `r2_20260823_012800.pcap`)

Bu tabloyla gelen akışın **%98.6'sı** temiz çerçevelenir. Parser artık imza
taraması yerine akışı mesaj mesaj yürür (`PaketAyristirici.besle`).

| Yön | Opcode | Boy | Paket |
|---|---|---|---|
| GELEN | 0x01 | 38 sabit | CHARACTER_ADD (doğuş) |
| GELEN | 0x02 | 5 sabit | CHARACTER_DEL (varlık sil) |
| GELEN | 0x03 | 24 sabit | MOVE (varlık hareketi) |
| GELEN | 0x04 | değişken | CHAT (04 \| u16 boy \| tip \| metin) |
| GELEN | 0x11 | 14 sabit | kendi puan/durum tiki |
| GİDEN | 0x07 | 16 sabit | MOVE (kendi konumun) |
| GİDEN | 0x02 | 6 sabit | ATTACK (02 \| tip \| vid) |
| GİDEN | 0x3D | 5 sabit | TARGET (hedef seç) |
| GİDEN | 0x34 | 9 sabit | USE_SKILL (vnum \| vid) |
| GİDEN | 0x0F | 5 sabit | ITEM_PICKUP (yerden al) |

## ✅ TOPLU KONUM ve İSİM — ÇÖZÜLDÜ (29 Ağu 2026, `r2_20260829_070117.pcap`)

Bu ikisi **"gri varlık"** sorununun çözümüydü: okuyucu oyunun ortasında
açıldığında sahada zaten duran varlıklar `0x01 CHARACTER_ADD` göndermez.

### GELEN — GC_SYNC_POSITION (toplu konum)  ✅ CANLI (değişken)
```
+0  u8   header = 0x05
+1  u16  wSize        toplam boy (başlık dahil) = 3 + 12*N
+3  [ u32 dwVID | i32 lX | i32 lY ] x N     (her eleman 12 bayt)
```
> Doğrulama: 79 paket bulundu, **78'inde (%99)** paket bittiği yerde geçerli
> bir opcode başlıyor; gövde her seferinde tam 12'nin katı.
> Örnek: `05 27 00 | 02CD5300 CCBF0C00 7E180400 | ...` → wSize=39 = 3+12×3.

### GELEN — VARLIK İSMİ  ✅ CANLI (62 bayt, header=0x88)
```
+0  u8       header = 0x88
+1  u32      dwVID
+5  char[25] isim (null ile biter, null'la doldurulur)
+30 ...      seviye/lonca vb. (henüz çözülmedi)
```
> Yakalanan isimler: `Kylian`, `KylianAt`, `yusuf1999`, `DOMALTAN`, `RaKBorN`
> — oyuncu ve binek isimleri. Bunlar **katalogda yoktur**, yalnızca bu
> paketten öğrenilir.
>
> Boy tespiti: 30–89 arası her boy denendi, her örnekten sonra akışın kaç
> mesaj temiz çerçevelendiği sayıldı. **Altı örneğin altısında da 62 kazandı.**

### Kazanç (aynı yakalama, aynı akışlar)

| | 0x05/0x88 yokken | varken |
|---|---|---|
| doğuş (0x01) | 51 | **146** |
| ölüm (0x02) | 55 | **101** |
| hareket (0x03) | 345 | **614** |
| toplu konum | 0 | **90** |
| benzersiz varlık | 114 | **177** |

> ⚠️ **Kapsam yüzdesi yanıltıcı bir ölçüttür.** Bu iki paket eklenince ham
> "çözülen bayt" oranı bir akışta %95.6'dan %93.1'e *düştü* — çünkü önceden
> parser bayt bayt kayarken çöp veriyi geçerli paket sanıp oranı şişiriyordu.
> Doğru ölçüt yukarıdaki varlık olaylarıdır.

---

## ✅ Savaş/durum paketleri — ÇÖZÜLDÜ (29 Ağu 2026, `log/*.pcap` 5 yakalama)

Çapa yöntemiyle çözüldü: 0x01/0x03/0x04/0x11 güçlü alan doğrulamasıyla çapa
kabul edildi, iki çapa arasındaki boşlukların ham baytları incelendi.
Boşluklar bu tabloyla **tam** bölünüyor (örn. 24 baytlık boşluk =
`0x3E`(9) + `0x87`(10) + `0x0D`(5)).

| Opcode | Boy | Yapı | Anlam |
|---|---|---|---|
| 0x3E |  9 | `3E \| saldıran(u32) \| hedef(u32)` | savaş vuruşu (saldıran 0 olabilir) |
| 0x3F | 14 | `3F \| vid(u32) \| can%(u8) \| can(i32) \| maksCan(i32)` | **CAN** |
| 0x46 | 10 | `46 \| alt(u8) \| kurban(u32) \| öldüren(u32)` | ölüm bildirimi |
| 0x47 | 17 | `47 \| vid(u32) \| vid(u32) \| u32 \| u32` | ? |
| 0x87 | 10 | `87 \| vid(u32) \| tip(u8) \| değer(i32)` | puan değişimi |
| 0x0D |  5 | `0D \| vid(u32)` | ölüm animasyonu |
| 0x0E |  5 | `0E \| vid(u32)` | ölüm animasyonu |
| 0x1B |  5 | `1B \| vid(u32)` | ? |
| 0x6F |  6 | `6F \| vid(u32) \| bayrak(u8)` | ? |
| 0x72 |  6 | `72 \| alt(u8) \| vid(u32)` | ? |
| 0x13 | 43 | `13 \| vid(u32) \| ...` | karakter güncelleme |

> **0x3F doğrulaması:** 3 yakalamadaki 39 paketin 39'unda
> `round(100*can/maksCan) == can%`. Ofsetler kesin.
>
> **0x46/0x0D/0x0E** ölüm çevresinde gelir ama gerçek kaldırma yine `0x02`'dir
> (12 vid'in 10'unda ikisi de görüldü). Parser bunları yalnızca çerçeveleme
> için tüketir.

Bu tabloyla gelen akış kapsamı **%87 → %98.6**. Ölçüm (5 yakalama, 45 KB):

| | 0x01 doğuş | 0x02 ölüm | 0x03 hareket | hayalet olay |
|---|---|---|---|---|
| eski (length-prefix heuristikli) | %100 | %93.8 | %94.3 | 106 |
| şimdiki (tablo, heuristiksiz) | **%100** | **%100** | **%100** | **0** |

> ⚠️ **length-prefix heuristiği KALDIRILDI.** Bu protokolün savaş paketleri
> sabit boyludur, uzunluk öneki taşımaz. Heuristik VID baytlarını uzunluk
> sanıp gerçek paketleri yutuyordu (tek yakalamada 1280 bayt).

Analiz araçları: `tools/opcode_coz.py` (uzunluk çözücü + döküm),
`tools/reframe.py` (kapsam ölçer), `tools/coz2.py` (alan çözümü).

---

## ✅ GİDEN AKIŞ — TAMAMEN ÇÖZÜLDÜ (29 Ağu 2026)

`r2_20260829_070117.pcap`, 56 KB giden akış. Kapsam **%53.1 → %99.9**
(atlanan bayt 27.002 → 53).

### Yöntem: segment sınırı

İstemci her eylemi **ayrı bir TCP segmentinde** gönderir. Bu, giden paketleri
çözmeyi çok kolaylaştırır — segmentin ilk baytı opcode, uzunluğu paket boyudur.
4101 giden segmentin dağılımı:

| ilk bayt / boy | adet | paket |
|---|---|---|
| `0x02` / 21 | 1648 | ATTACK + ekli SYNC |
| `0x3D` / 5 | 1619 | TARGET |
| `0x07` / 16 | 736 | MOVE |
| `0x07` / 32, 48 | 24 | 2–3 MOVE arka arkaya |
| `0x02` / 6 | 9 | ATTACK (eksiz) |
| `0x0B` / 4 | 7 | ? |

> Bu yöntem `tools/eylem_bul.py` içinde araca dönüştürüldü: bir eylemi N kez
> yaparsan, o eyleme ait `(opcode, boy)` çifti tam N kez görünen nadir satır
> olarak ayrışır.

### GİDEN — CG_SYNC_POSITION (toplu konum)  ✅ CANLI (değişken)
```
+0  u8   header = 0x08
+1  u16  wSize        toplam boy = 3 + 12*N
+3  [ u32 dwVID | i32 lX | i32 lY ] x N
```
> Gelen `0x05`'in aynası. Saldırıya **eklenerek** gönderilir; 21 baytlık
> saldırı segmentinin yapısı şudur:
> ```
> 02 00 0D4E2600 | 08 0F 00 | 0D4E2600 9EC90C00 51050400
> CG_ATTACK (6)    wSize=15   vid       x        y
> ```
> `08 1B 00` (wSize=27 = 3+12×2) iki elemanlı örnekte de doğrulandı.

### GİDEN — CG_CHAT / komut  ✅ CANLI (değişken)
```
+0  u8   header = 0x03
+1  u16  wSize        toplam boy
+3  u8   bType        (yakalamada 0)
+4  ...  metin        UTF-8, null ile biter
```
> Yakalanan: `03 16 00 00 "/change_channel 6\0"` — kanal değiştirme komutu.

### GİDEN — 0x0B  ◐ yapı kısmen (4 bayt)
```
+0  u8   header = 0x0B
+1  u8   (yakalamada hep 0x01)
+2  u16  değer        (3 ve 6 görüldü)
```
> 7 örnek; anlamı henüz belirlenmedi.

### Giden tam tablo

| Opcode | Boy | Paket | Durum |
|---|---|---|---|
| 0x02 | 6 | CG_ATTACK | ✅ |
| 0x03 | değişken | CG_CHAT / komut | ✅ |
| 0x07 | 16 | CG_MOVE | ✅ |
| 0x08 | değişken | CG_SYNC_POSITION | ✅ |
| 0x0B | 4 | ? | ◐ |
| 0x0F | 5 | CG_ITEM_PICKUP | ✅ |
| 0x34 | 9 | CG_USE_SKILL | ✅ |
| 0x3D | 5 | CG_TARGET | ✅ |

> ⚠️ Eski (eksik) tabloyla `0x0F` 82 kez sayılıyordu; doğru çerçevelemede
> **24**. Aradaki 58 tanesi hizasız baytların yanlış okunmasıydı. Aynı şekilde
> `0x34` 46 → 2. Eksik tablo yalnızca paket kaçırmaz, **sahte paket de üretir.**

---

## ⚖️ SUNUCU NEYİ DOĞRULUYOR — ölçüm sonuçları (29 Ağu 2026)

Paketin doğru olması yetmiyor; sunucu bazılarını doğruluyor. Canlı oyunda
ölçüldü. **Bu bölüm, neyin mümkün olduğunu belirler.**

### Hareket: kabul ediliyor ama IŞINLANMA DEĞİL — YÜRÜME

| Mesafe | Sonuç | Çevre ne zaman oturdu | Hız |
|---|---|---|---|
| 30 m | ✅ kabul | ~2 sn | — |
| 50 m | ✅ kabul | ~4 sn | 12.5 m/s |
| 80 m | ✅ kabul | ~6 sn | 13 m/s |
| 120 m | ✅ kabul | ~9 sn | 13 m/s |

80 m denemesinde çevre **kademeli** değişti (37→29→19→18→35→36). Işınlanma
olsaydı tek adımda değişirdi. Yani sunucu `0x07 bfunc=1`'i "oraya gitmek
istiyorum" olarak kabul edip bizi **yürüterek** götürüyor.

> ⚠️ Bu bölümde daha önce "150 m red" yazıyordu. O ölçüm yanlıştı: yalnızca
> 7 saniye beklenmişti, oysa 150 m ~11 saniye sürer. Ayrıca o sırada
> `enjekte()` konumu da güncelliyordu ve ölçüm kirlenmişti.

**Sunucunun reddettiği**, mesafe değil "**anında vardım**" iddiasıdır:
`bfunc=1` (yürü) + `bfunc=0` (dur) ardışık gönderilince kabul edilmiyor.
Wait-hack'in çalışmamasının sebebi budur.

**Botun buradan çıkardığı:** her yere gidebilir ama yol **zaman alır**.
Sunucu kendi hareketimizi bize geri yollamadığı için (859 gelen `0x03`'ün
sıfırı bizim vid'imiz) bot vardığını anlayamaz — süreyi mesafeden tahmin
eder: `süre = mesafe / 1300 ham-birim-saniye`.

> **Ölçüm yöntemi — önemli:** `/api/konum`'a bakmak YETMEZ, çünkü panel
> enjekte edilen konumu da gösterebiliyor. Güvenilir sinyal ÇEVREDİR:
> sunucu bizi gerçekten taşırsa yeni bölge için `0x01` doğuş, geride
> kalanlar için `0x02` silme gönderir. Çevre değişmiyorsa taşınmamışız.
> Aracı: `tools/hareket_testi.py`

Sonuç: uzun yol, sınırın altında **adımlara bölünerek** alınabilir.
Anlık ışınlanma (wait-hack) bu sunucuda çalışmaz.

### Saldırı: çalışıyor

3 m'deki hedefe tek dizi gönderildi:
```
0x3F | vid | 0x64 (=%100) | 614 | 614      ← saldırıdan önce
hedefin canı: %62                           ← saldırıdan sonra
```
Dizi: `0x07(yürü) + 0x3D(hedefle) + 0x02(saldır) + 0x08(konum senkronu)`

> `0x08` ŞART: 1648 gerçek saldırı segmentinin **hepsi** 21 bayttı, yani
> istemci `0x02` ile `0x08`'i her zaman birlikte gönderiyor.

### Toplama: çalışıyor

`0x0F | vid` — canlı testte Yang ve iksirler toplandı.

### Genel kural

| Sunucu istemciye güveniyor mu | Örnek | Bot yapabilir mi |
|---|---|---|
| Kısmen — konum, sınırlı mesafede | `0x07` | ✅ adım adım |
| Evet — niyet bildirimleri | `0x3D`, `0x02`, `0x0F` | ✅ |
| **Hayır** — envanter, eşya, buff, Yang, statlar | `CG_ITEM_USE` | ❌ |

Olmayan bir eşyanın etkisini istemek mümkün değildir: `CG_ITEM_USE` yalnızca
**slot numarası** taşır, eşyanın kendisini değil. Sunucu o slotta ne olduğunu
kendi veritabanından bilir.

### ⚠️ Uzunluk-önekli paketlerde ÜST SINIR kritiktir

`0x26 GC_SHOP` kuralı önce `4 ≤ boy ≤ 32000` idi. Bu ÇOK GEVŞEKTİ: rastgele
bir `26` baytı, ardından makul görünen iki bayt gelince kilobaytlarca veri
tek "paket" sanılıp yutuluyordu.

29 Ağu 2026 ölçümü — iki blok böyle yutulmuştu (8238 + 16338 bayt, akışın
%22'si). İçlerinde kaybolanlar:

| | Yutulan blokların içinde |
|---|---|
| doğuş | 29 |
| ölüm | 35 |
| hareket | 94 |
| yer eşyası | 8 |

Sıkılaştırma: `boy ≤ 4096` (80 slot × 43 bayt + 9 ≈ 3.5 KB gerçek üst sınır)
ve alt başlık `≤ 0x0F`. Sonuç:

| | Gevşek | Sıkı |
|---|---|---|
| doğuş | 245 | **301** |
| ölüm | 206 | **262** |
| hareket | 859 | **1085** |
| benzersiz varlık | 217 | **232** |

> Ders: uzunluk-önekli her pakette üst sınır, o paketin GERÇEK azami
> boyutuna göre konmalı. Gevşek sınır sessizce veri yutar ve kapsam
> yüzdesi bunu gizler — oran yüksek görünür çünkü "çözülen bayt" sayılır.

### 🔑 İSTEMCİYİ HİZALAMA — `0x05` istemciye yazılır (29 Ağu 2026)

Oturumun en önemli eksiği buydu: **sunucu kendi hareketimizi bize geri
yollamıyor** (859 gelen `0x03`'ün sıfırı bizim vid'imizi taşıyor). Bot
sunucuda ilerlediğinde istemci eski konumda kalıyor ve ilk fırsatta kendi
konumunu bildirip bizi geri çekiyordu.

Proxy ortada olduğu için **İSTEMCİYE de** paket yazılabilir. Üç aday
sırayla denendi (`tools/istemci_hizala.py`):

| Aday | Sonuç |
|---|---|
| `0x01` CHARACTER_ADD (kendi vid) | istemci kımıldamadı |
| `0x03` MOVE (kendi vid) | kımıldamadı |
| **`0x05` SYNC_POSITION (kendi vid)** | **KARAKTER TAŞINDI** |

```
05 0F 00 | B1A22A00 | 48960D00 | C77A0400
   wSize=15  kendi vid    x          y
```

Yani gelen `0x05` toplu konum paketinin **tek elemanlı hâli**, kendi
vid'imizle istemciye yazılınca karakteri taşıyor.

> Bu yalnızca istemcinin GÖRÜNTÜSÜNÜ hizalar. Sunucudaki gerçeği
> değiştirmez — envanter, eşya, stat hepsi sunucuda tutulur.
> Amaç yeni bir şey kazanmak değil, bot ilerlediğinde istemcinin geri
> çekmesini önlemek.

**Kendi vid'imiz** `0x11` paketinden öğrenilir ve `/api/konum` →
`kendiVid` alanında sunulur. **Ama körü körüne değil** — aşağıya bak.

#### Kendi vid'i güvenilir okumak (29 Ağu 2026, sahada bulunan hata)

Belirti: bot yürürken istemci karakteri değil, **yanındaki başka bir varlığı
sürükledi**. Sebep hizalama paketinin (`0x05`) yanlış vid'e gitmesiydi.

`tools/kendi_vid_dogrula.py` önce imza taramasıyla baktı ve 0x11 için 64
farklı vid buldu — ama bu ölçüm yanıltıcıydı, hizasız okumadan doğan
hayaletlerdi. `tools/kendi_vid_cerceve.py` **doğrulanmış uzunluk tablosuyla
gerçek çerçeveleme** yapınca tablo netleşti:

| kayıt | 0x11 aday sayısı | baskın vid | doğrulama |
|---|---|---|---|
| `ornek_bekleme` | 1 | 9525679 | başka pakette geçmiyor |
| `r2_20260822_202956` | 1 | 5090706 (x87) | başka pakette geçmiyor |
| `r2_20260823_012800` | 1 | 10925029 (x92) | başka pakette geçmiyor |
| `eylem_satis` | 1 | 2856518 (x5) | başka pakette geçmiyor |
| `r2_20260829_070117` | **4** | 2528459 (x531) | `0x88` isim = **DOMALTAN** |

Yani 0x11 **gerçekten** kendi vid'imizi taşıyor — isim paketiyle çapraz
doğrulandı. Sorun paketin kendisinde değil, **okuma kuralındaydı**:

```java
// ESKİ — hatalı
public void kendiVidBildir(int vid) { if (vid > 0) kendiVid = vid; }
```

"Son gelen kazanır". Büyük kayıtta 531 oyluk gerçek vid'in yanında üç
hayalet vardı (`5486899` x2, `15` x1, `263680` x1); akışın nadiren kaydığı
anlarda doğuyorlar. Tek bir hayalet en sona düşünce kendi vid'imizi çalıyor
ve hizalama o vid'e gidiyordu. `5486899`, isimleri `Kylian` / `KylianAt`
olan varlıklarla aynı aralıkta — istemcinin **bir atı sürüklemesi** buradan
geliyor.

```java
// YENİ — çoğunluk oyu
// Aday, tahttakinden DAHA ÇOK oy alana ve en az 3 kez görülene kadar
// seçilmez. 531 oyluk gerçek vid 1-2 oyluk hayalete karşı dokunulmaz.
```

##### 0x11 BAZI OTURUMLARDA HİÇ GELMİYOR — ikinci kaynak şart

29 Ağu 2026 21:46 kaydı: 179 saniye, 5771 gelen paket, **0 adet 0x11**.
Önceki kayıtlarda 87 / 92 / 535 geliyordu. Vid öğrenilemeyince istemci
hizalaması hiç çalışmadı.

Kendi konumumuzu gelen akıştan çıkarmak da mümkün değil: aynı kayıtta
gelen `0x03`/`0x05` ile izlenen **180 varlığın hiçbiri** bizim `0x07`
güzergahımızla örtüşmüyor (en yakını 91 ham medyan, 8 noktalı bir canavar;
güzergah 6538 ham uzunluğunda). Sunucu gerçekten kendi hareketimizi bize
yollamıyor.

**İkinci kaynak: `0x3E` savaş vuruşu.** İki vid taşır — vuran ve vurulan.
Biz bir canavara saldırınca sunucu `3E | BİZ | canavar` yolluyor. Giden
`0x02`/`0x3D` hedeflerimizi tutup gelen `0x3E`'de eşleştirince kendi
vid'imiz düşüyor. `tools/kendi_vid_savastan.py` ile doğrulandı:

| vuran vid | vuruş | kurban | hedeflerimizle örtüşme | isim |
|---|---|---|---|---|
| **2528459** | **724** | **71** | **%100** | **DOMALTAN** |
| 0 | 189 | 91 | %74 | (çevresel hasar) |
| 5491843 | 154 | 11 | %0 | Kylian |
| 2496914 | 77 | 9 | %0 | RaKBorN |
| 5398864 | 51 | 6 | %0 | yusuf1999 |

Ayrım keskin: bizim %100, başka oyuncular %0. Aynı kayıtta `0x11` de
bağımsız olarak 2528459 diyor — **iki yöntem birbirini doğruluyor**.

APK artık her iki kaynağı da çoğunluk oyuna besliyor:
`gidenCoz` ve `ProxyServisi.enjekteyiDunyayaBildir` saldırı hedeflerini
kaydediyor, parser `0x3E`'yi `DunyaDurumu.savasVurusuBildir()`'e veriyor.
Hedefler 6 saniye yaşıyor — eskiyenler yanlış eşleşme yapar.

Yan düzeltme: `enjekteyiDunyayaBildir` eskiden yalnızca `paket[0]`'a
bakıyordu. Wait-hack tek atışta `0x07 + 0x3D + 0x02 + 0x08` (42 bayt)
yolluyor; dizinin içindeki saldırı görülmüyordu. Artık tampon bilinen giden
uzunluklarıyla taranıyor.

**Sınır:** bot yalnızca yürüyorsa (sadece rota modu) hiçbir yöntem
çalışmaz — ne 0x11 gelir ne saldırı olur. O durumda vid Hareket
sekmesinden elle girilmeli.

`/api/konum` artık `kendiVidOyu` ve `kendiVidAday` alanlarını da veriyor;
`tambot.py` üç oydan az alan bir vid'e hizalama **göndermiyor**, ayrıca
vid varlık listesinde canavar/metin olarak görünüyorsa hizalamayı durdurup
uyarıyor. Hareket sekmesinden vid elle de girilebilir.

**Ders:** bir alanın "hep X taşır" olduğu tek bir kayıtta doğrulanabilir ama
**hangi okumanın kazandığı** ayrı bir sorudur. Nadir bir hayalet, "son gelen
kazanır" kuralıyla birleşince kalıcı hataya dönüşür. Sayım her zaman son
değerden güvenlidir.

#### İstemciyi ANİMASYONLU yürütmek — `0x03` GC_MOVE (29 Ağu 2026)

`0x05 SYNC_POSITION` işe yarıyor ama bir **konum düzeltmesi**: istemci
karakteri oraya oturtur, hareket durum makinesini hiç çalıştırmaz. Arka
arkaya küçük adımlarla gönderilince karakter koşmadan **sürüklenir**.
Sahada görülen buydu — "gidip geliyor ama animasyon yok, kayıyor".

Başkalarının yürüyüşünü ekranda çizdiren paket `0x03 GC_MOVE`. 23 Ağu 2026
kaydındaki **163 gerçek paket** `tools/hareket_paketi_incele.py` ile
dökülüp alanları ölçüldü:

```
+0  u8   header = 0x03
+1  u8   bFunc       0 = hedefe yürü   (155/176 paket böyle; 2 -> 13, 1 -> 8)
+2  u8   bArg        HEPSİNDE 0
+3  u8   bRot        yön (derece/5, 0-71)
+4  u32  dwVID
+8  i32  lX
+12 i32  lY
+16 u32  dwTime      sunucu tiki
+20 u32  dwDuration  hareket KAÇ MS sürecek   <-- ANİMASYONUN ANAHTARI
```

`dwDuration` ölçümü — mesafe/süre oranı **her pakette aynı**:

| mesafe | süre | oran |
|---|---|---|
| 401 ham | 942 ms | 0.43 ham/ms |
| 1250 ham | 2937 ms | 0.43 ham/ms |

Yani istemcinin yürüme animasyon hızı sabit **0.43 ham/ms = 430 ham/s =
4.3 m/s**. Süre = mesafe / 0.43. Paketlerin %93'ünde süre > 0.

**Neden ilk denemede çalışmadı.** `tools/istemci_hizala.py` bu paketi 29
Ağu'da denemiş ve "istemci kımıldamadı" sonucuna varmıştı — ama paketi
şöyle kuruyordu:

```python
p = [0x03, 0, 0, 0] + u32(vid) + u32(x) + u32(y) + u32(0) + u32(0)
#                                                   dwTime^   dwDuration^
```

`dwDuration = 0`. Süresi sıfır olan bir hareketin gidecek zamanı yok. Alan
doğru doldurulunca paket çalışıyor. **Ders:** bir aday paket "çalışmadı"
dendiğinde, paketin yanlış olduğu değil, ALANLARIN yanlış doldurulduğu da
mümkündür — reddedilen adayı gerçek örnekle karşılaştırmadan eleme.

#### CANLI SONUÇ: `0x03` kendi karakterimizde ETKİSİZ  ✕ (29 Ağu 2026)

Alanlar doğru doldurulup (`bFunc=0`, `bArg=0`, `bRot=18`, `dwTime` =
`/api/durum` tiki, `dwDuration=3488`) canlı denendi
(`tools/animasyon_testi.py`):

```
03 00 00 12 DC 52 2A 00 E8 97 0D 00 13 08 04 00 66 4C 90 1A A0 0D 00 00
```

**İstemci hiç kımıldamadı.** Aynı oturumda `0x05` ile gönderilen 10 adım
karakteri taşıdı ama animasyonsuz (kayarak).

Sebep protokolde değil, istemcinin mimarisinde: **Metin2 istemcisi kendi
karakterinin hareket durumunu KENDİSİ yönetir.** Sunucudan gelen GC_MOVE
yalnızca başka varlıklara uygulanır; kendi karakterin için gelen MOVE
yok sayılır. Kendi karakterin sunucu tarafından oynatılmaz — sen oynatırsın,
istemci de sunucuya bildirir. `SYNC_POSITION` bu mimaride bir *düzeltme*
kanalıdır, hareket kanalı değil; o yüzden konumu değiştirir ama animasyon
tetiklemez.

Başka bir paket olabilir mi diye çözülmemiş TÜM küçük opcode'lar tarandı
(`tools/bilinmeyen_incele.py`):

| opcode | boy | +1 alanı | ne olduğu |
|---|---|---|---|
| 0x0D | 5 | vid (90/99 bilinen) | varlık durum bildirimi |
| 0x0E | 5 | vid (88/93 bilinen) | varlık durum bildirimi |
| 0x6F | 6 | vid + u8 bayrak | varlık bayrağı |
| 0x72 | 6 | vid DEĞİL | çözülmedi |
| 0x3E | 9 | **iki vid** (saldıran + kurban) | savaş vuruşu |
| 0x87 | 10 | vid + tip + değer | puan/etki değişimi |
| 0x47 | 17 | vid | çözülmedi |

Hiçbiri hareket/animasyon taşımıyor. **Sonuç: kendi karakterinin koşma
animasyonu ağ üzerinden tetiklenemiyor.** Karakter kayarak gider; bu
kozmetik bir sınır, sunucu tarafındaki hareket tamamen geçerlidir.

`tambot.py` Hareket sekmesinde iki yöntem var; varsayılan **Sürükle**:

| yöntem | paket | sonuç |
|---|---|---|
| **Sürükle (0x05)** ← varsayılan | SYNC_POSITION ×N | çalışır, animasyonsuz |
| GC_MOVE (0x03) | MOVE ×1 + varışta düzeltme | bu istemcide etkisiz |

0x03 seçeneği başka bir istemci/sunucu sürümünde işe yarayabileceği için
duruyor.

#### Başkalarının ekranında animasyon VAR — kesiklik BOTUN RİTMİNDEN

29 Ağu 2026, başka bir oyuncunun ekranından bakıldı: karakter **animasyonlu
yürüyor**. Sunucu hareketimizi çevredekilere düzgün `GC_MOVE` olarak
yayınlıyor. Animasyon eksikliği yalnızca kendi ekranımızda (yukarıdaki
mimari sınır).

Ama dışarıdan bakan "durup durup yürüyor, bot gibi" dedi. Önce beklemeyi
kısaltmayı denedik — **işe yaramadı**. Sorun bekleme değilmiş.

##### GİDEN 0x07 deseni — gerçek istemci ne yapıyor

21 Ağu 2026 kaydındaki 85 giden `0x07` paketi ölçüldü
(`tools/giden_hareket_deseni.py`):

```
#    Δt(ms)  func  rot   x        y        Δmesafe  hız(ham/s)
2    178     1     68    935994   263399   69       387
3    161     1     68    935968   263472   77       481
4    165     1     68    935944   263537   69       419
5    152     1     68    935918   263610   77       510
...
11   67      0     69    935817   263990   39       580   <- DUR paketi
```

| ölçüm | değer |
|---|---|
| paketler arası süre | **ortanca 155 ms** (%99'u 1 sn'den kısa) |
| paketler arası mesafe | **ortanca 70 ham** |
| bFunc | yürürken **1** (81 paket), dururken **0** (4 paket) |
| bArg | hepsinde 0 |

**İstemci tek bir "şuraya git" paketi YOLLAMIYOR.** Her ~155 ms'de bir,
~70 ham ilerlemiş yeni bir konumla AKAN bir dizi yolluyor.

Bot ise bir bacak için TEK paket yollayıp yolun bitmesini bekliyordu.
Sunucu bizi oraya yürütüyor, varıyoruz, **duruyoruz**; sonra bot bir
sonrakini yolluyor. Dışarıdan yürü-dur-yürü-dur. Bekleme oranıyla oynamak
bunu çözemezdi çünkü sorun bekleme değil **paket sayısıydı**: bacak başına
1 paket yerine ~12 paket olmalı.

`_yuru` artık yolu `hız × aralık` boyunda adımlara bölüp aynı ritimde
akıtıyor. 8 m'lik bir bacak için ölçülen çıktı:

```
11 hareket paketi, 1.71 sn, adım başına 61-62 ham, bFunc=1, tik her pakette artıyor
```

Gerçek istemcinin aynı mesafe için yollayacağı paket sayısı: ~11.

Ayarlar (Hareket sekmesi): **"Paket aralığı (ms)"** = 155,
**"Bacağın % kaçını yürü"** = 85 (son adımı atlayıp sıradaki bacağı erken
başlatır, böylece bacaklar arasında da boşluk kalmaz).

**Ders:** "bot gibi görünüyor" bir zamanlama ayarı sorunu değil, **trafik
deseni** sorunuydu. Gerçek istemcinin giden akışını ölçmeden doğru cevabı
bulmak mümkün değildi — iki tur tahminle kaybedildi.

### KANAL DEĞİŞTİRME — ağdan yapılamaz, dokunmayla yapılır  ✅ ÇÖZÜLDÜ

#### 1. Kanallar ayrı sunucular

`tools/kanal_bul.py` ile ölçüldü (29 Ağu 2026). Elle kanal değiştirilirken
alınan kayıtta **7 yeni TCP bağlantısı** ve şu portlar görüldü:

```
30001  giriş/kimlik sunucusu
30004  ch1     30020  ch5
30008  ch2     30024  ch6
30012  ch3     30028  ch7
30016  ch4     30032  ch8
```

Kural: **port = 30000 + 4 × kanal**

Kanal değişimi yeni bir bağlantı açtığı için tek paket enjekte ederek
yapılamaz — proxy yalnızca var olan bağlantıya yazabiliyor. Bu bir
protokol eksiği değil, mimarinin sonucu.

APK bağlandığı portu `ProxyServisi.SON_PORT` içinde tutuyor ve
`/api/durum → proxy.kanal` alanında sunuyor. Proxy şeffaf yönlendirme
(`gercekHedefPort`) kullandığı için her kanalda çalışmayı sürdürüyor.

**Yeni bağlantı = yeni oturum = YENİ VİD.** Kanal değişince
`DunyaDurumu.kendiVidSifirla()` çağrılıyor: vid, oy tabloları, savaş
kanıtı, varlık listesi ve isim önbelleği temizleniyor. Yapılmazsa eski
vid binlerce oyuyla tahtta kalıyor ve yenisi onu asla geçemiyor —
sahada "ch değişince vidi kaybettik" olarak görüldü.

#### 2. `input tap` uygulama içinden ÇALIŞMIYOR (sessiz başarısızlık)

Geriye oyunun kendi menüsüne basmak kalıyor. İlk deneme `su -c input tap`
ile yapıldı ve **çıkış 0 döndü ama ekranda hiçbir şey olmadı.** 30 Ağu
2026'da cihazda ölçüldü; logcat ikisini yan yana gösterdi:

```
R2_DOKUN: tap 1011,1828 OK
cmd: avc: denied { call } scontext=u:r:su:s0
                          tcontext=u:r:system_server:s0
```

`input`, `cmd input` üzerinden **binder**'a gidiyor; uygulama
bağlamındaki `su` için o çağrı engelleniyor. Komut yine de 0 dönüyor.
adb kabuğundan çalışıp uygulamadan çalışmamasının sebebi bu.

> **Ders:** çıkış kodu 0, "iş yapıldı" demek değil. Etkiyi ayrıca
> doğrulamak gerekiyor.

#### 3. Çözüm: `sendevent` — kernel seviyesi

`sendevent` doğrudan `/dev/input/eventN`'e yazıyor: binder yok,
InputManager yok, izin sorunu yok. Aynı cihazda denendi, üretilen kernel
olayları gerçek parmakla birebir aynı:

```
ABS_MT_TRACKING_ID 000003e7      3 57 <iz>
ABS_MT_POSITION_X  0000012c      3 53 <x>
ABS_MT_POSITION_Y  00000190      3 54 <y>
BTN_TOUCH          DOWN          1 330 1
SYN_REPORT                       0 0 0
ABS_MT_TRACKING_ID ffffffff      3 57 -1
BTN_TOUCH          UP            1 330 0
SYN_REPORT                       0 0 0
```

`Dokunma.java` bunu uyguluyor. Dokunmatik aygıt `getevent -pl` çıktısında
`ABS_MT_POSITION_X` bildiren aygıttır (test cihazında `/dev/input/event4`,
eksenler 0-1080 / 0-1920, ekranla birebir). Sekiz olay TEK `su`
çağrısında zincirleniyor — ayrı ayrı olsaydı dokunuş milisaniyelere
yayılıp uzun basma sayılabilirdi.

**Saha doğrulaması (30 Ağu 2026): ch2'ye başarıyla geçildi.**

#### 4. Koordinatlar — kayıt ve düzen

`tools/dokunma_kaydet.py` her kanalı ayrı ayrı sorup `getevent`'ten
dokunuşları yakalıyor. Test cihazında 8 kanalın menü satırları düzenli
çıktı:

| ch | menü satırı Y | ch | menü satırı Y |
|---|---|---|---|
| 1 | 696 | 5 | 1008 |
| 2 | 779 | 6 | 1094 |
| 3 | 834 | 7 | 1151 |
| 4 | 927 | 8 | 1258 |

Doğrusal uydurma: **y = 612 + 79.2 × k**, en büyük sapma 16 px (satır
yüksekliği ~79 px). Yani sekiz ayrı kayıt yerine tek satır da yazılabilir:

```
tap 1008 1830
bekle 1200
tap 887 {612+79*k}
bekle 12000
```

`{...}` içinde `k` kanal numarasıdır; ayrıştırıcı yalnızca rakam ve
`+ - * / ( )` kabul eder.

**Sınır:** koordinatlar cihaza ve arayüze özeldir. Çözünürlük, oyun
sürümü ya da menü düzeni değişirse yeniden kaydedilmeleri gerekir.

#### 5. Bir tuzak: bilinmeyen uç sessizce "ok" dönüyor

`ApiSunucu`'nun yönlendirmesinde `default: return durumJson();` var ve o
JSON `{"ok":true,...}` ile başlıyor. Eski APK'da `/api/dokun` yolu
yokken bot bu yanıta bakıp **"dokunma tamamlandı"** diyordu. `tambot.py`
artık yanıtta gerçek dokunma alanı (`acik`) var mı diye bakıyor; yoksa
"APK bu isteği tanımıyor — ESKİ SÜRÜM" diyor.

#### dwTime GERÇEK SAATİ TAKİP ETMELİ — "yürü-dur"un asıl sebebi

Akan paketlere ve düzeltilmiş bRot'a rağmen karakter dışarıdan hâlâ
durup durup yürüyordu. Önce paket akışında boşluk arandı — YOKTU:

| | ortanca | %95 | en büyük | 300 ms üstü boşluk |
|---|---|---|---|---|
| BOT (965 paket) | 173 ms | 217 | **235** | **0** |
| GERÇEK OYUNCU (85) | 155 ms | 172 | 1683 | 1 |

Bot akışı gerçek oyuncudan bile daha sürekliydi. Koordinatlar da temizdi:
965 pakette **0 kez aynı yerde**, 8 kez (%0.8) geri dönüş.

Sorun `dwTime` (+12) alanındaydı:

```
      gerçek geçen süre    gönderilen dwTime artışı
BOT           210 ms       hep tam 155        <- YANLIŞ
BOT           173 ms       hep tam 155
GERÇEK         150 ms      149
GERÇEK         164 ms      165
GERÇEK        1683 ms     1650
```

**Gerçek istemcinin dwTime'ı gerçek zamanla birebir ilerliyor.** Bizimki
her pakette sabit `aralik_ms` (155) sayıyordu; oysa bir tur `sleep` +
enjeksiyon HTTP'si ~210 ms sürüyordu. Saat her pakette ~55 ms geri
kalıyor, bacak sonunda `/api/durum`'dan tazelenince **741-818 ms ileri
sıçrıyordu** — testere dişi bir zaman çizgisi.

Sunucu hareket hızını dwTime farkından denetler. Saat böyle savrulunca
bizi kâh geçiriyor kâh tutuyor; dışarıdan yürü-dur olarak görünen buydu.

Çözüm: akış **adım güdümlü değil ZAMAN GÜDÜMLÜ** oldu. Hem konum hem
dwTime `time.monotonic()`'ten türetiliyor, döngü uykusundan geçen işlem
süresi düşülüyor. Ölçüm (55 ms'lik enjeksiyon gecikmesi taklit edilerek,
86 m'lik yol, 111 paket):

```
gerçek aralık : 155 ms   (eskiden 210)
dwTime sapması: 0 paket 40 ms'yi aştı
17115 ms gerçek zamanda dwTime 17114 ms ilerledi  -> sapma 1 ms
```

**Ders:** üç tur boyunca yanlış yerde arandı — bekleme oranı, paket
sıklığı, paket boşlukları. Hepsi ölçülüp elendikten sonra geriye tek
alan kaldı. Doğru soru "ne kadar sık gönderiyoruz" değil, **"gönderdiğimiz
zaman gerçek mi"** idi.

#### bRot (yön baytı) formülü YANLIŞTI — ayna hatası

Akan yürüyüşe geçtikten sonra karakter dışarıdan "kendi etrafında dönüyor"
göründü. Sebep hareket paketinin +3 baytı: `bRot`.

`tools/yon_bayti_dogrula.py` kayıttan doğruladı. Yöntem: ardışık `0x07`
paketlerinin konum farkından yön hesaplanıp pakette YAZAN `bRot` ile
karşılaştırıldı. 5 kayıt, **938 gerçek yürüme çifti**:

| formül | ortalama sapma | ±1 içinde |
|---|---|---|
| **`atan2(dx, dy) / 5`** | **1.4 birim (7°)** | **%84** |
| `atan2(-dx, dy) / 5` | 15.0 birim | %6 |
| `atan2(dy, dx) / 5` | 19.5 birim | %2 |
| eski: `(90 - atan2(-dy, dx)) / 5` | 21.0 birim (105°) | %1 |

Nokta doğrulaması:

```
dx=-23 dy=65 -> hesap 68, pakette 68
dx=-20 dy=67 -> hesap 69, pakette 69
dx=-26 dy=73 -> hesap 68, pakette 68
```

**Hata neden dönmeye yol açıyordu.** θ = `atan2(dy, dx)` dersek:

```
doğru : 90 - θ
eski  : 90 + θ
```

Yani sapma sabit bir kayma değil, **2θ** — yöne bağlı bir AYNA yansıması.
Rota üzerinde yön değiştikçe bakış açısı iki katı savruluyordu. Tek paket
yollanırken göze batmıyordu çünkü karakter zaten çoğu zaman duruyordu;
akan paketlere geçince ortaya çıktı.

**Ders:** aynı hata iki farklı belirtiyle saklanabilir. "Durup durup
yürüme" düzeltilmeden bu hiç görünmeyecekti.

#### Yan bulgu: gerçek yürüme hızı 430 ham/s, 1300 değil

163 GC_MOVE paketinin hepsinde mesafe/süre = **0.43 ham/ms**. Eski
`yurume_hizi = 1300` varsayılanı tek bir kaba ölçümden ("80 m ~6 sn")
geliyordu ve üç kat yüksekti. Fazla yüksek hız, botun "vardım" sanıp erken
ilerlemesine ve rota noktalarını ıskalamasına yol açar. Varsayılan **430**
yapıldı; binek/hız iksiri varsa yükseltilebilir.

**Altyapı:** `ProxyServisi.asagiAkis` + `enjekteIstemciye()` +
`/api/enjekte_istemci`. Sunucuya yazan yolla aynı üç kapıdan geçer.

---

## HAREKET / KONUM

### GİDEN — CG_MOVE (kendi hareketin)  ✅ CANLI (16 bayt)
```
+0  u8   header   = 0x07
+1  u8   bFunc    hareket tipi: 0=dur(WAIT), 1=yürü(MOVE), 3=saldırı(ATTACK), 0x80|slot=skill
+2  u8   bArg     alt argüman (skill/combo); yürümede 0
+3  u8   bRot     yön: derece = (90 - bRot*5) mod 360   (aralık 0..71)
+4  i32  lX       ham X
+8  i32  lY       ham Y   (normalde negatif; ekranY = -lY/100)
+12 u32  dwTime   istemci tik (ms, uptime)
```
> Kendi hareketinde `dwVID` yok — gönderen zaten sensin.

### GELEN — GC_MOVE (başka varlığın hareketi)  ✅ CANLI (24 bayt sabit)
```
+0  u8   header   = 0x03
+1  u8   bFunc    (yakalamada 0)
+2  u8   bArg     (yakalamada 0)
+3  u8   bRot     yön
+4  u32  dwVID    kim hareket ediyor
+8  i32  lX
+12 i32  lY
+16 u32  dwTime   istemci tik
+20 u32  süre/arg  hareketin süresi/mesafesi (ör. 0x0717)
```
> Parser 0x03'ü `id@+4, x@+8, y@+12` okur; çerçeve için bFunc=bArg=0 doğrulanır.
> vnum taşımaz — isim yalnızca 0x01 doğuşundan gelir.

### GELEN — GC_CHARACTER_ADD (doğuş)  ✅ CANLI (38 bayt sabit)
```
+0  u8   header    = 0x01
+1  u32  dwVID     varlık örnek kimliği
+5  f32  angle     bakış açısı (0..360)
+9  i32  lX
+13 i32  lY
+17 i32  lZ        yükseklik (yakalamada 0)
+21 u8   bType     CHAR_TYPE (0 canavar,1 npc,2 metin,6 oyuncu…)
+22 u16  wRaceNum  **vnum** (tür no — isim bundan çözülür)
+24 u16  (0)       ayrılmış/durum
+26 u8   bMovingSpeed   hareket hızı (ör. 100)
+27 u8   bAttackSpeed   saldırı hızı (ör. 80)
+28..37  bStateFlag, guild vb. (yakalamada 0)
```
> 23 Ağu 2026 yakalaması: ardışık doğuşlar tam **38 bayt** aralıklı
> (216−178=38, 452−414=38 …). vnum değerleri 105/106/110/173/175 = u16.
> Parser artık 0x01'i tam 38 bayt olarak çerçeveler: `id@+1, x@+9, y@+13,
> vnum(u16)@+22`.

### GELEN — GC_CHARACTER_DEL (varlık sil)  ✅ CANLI (5 bayt)
```
+0  u8   header = 0x02
+1  u32  dwVID    silinecek varlık
```

### GELEN — GC_CHAT (sohbet)  ✅ CANLI (değişken, uzunluk önekli)
```
+0  u8   header  = 0x04
+1  u16  wSize   TOPLAM mesaj boyu (04 dahil)
+3  u8   bType   sohbet tipi (0x06 gözlemlendi — dükkân/duyuru)
+4  ...  metin   UTF-8, biçim: |Jx|j|N<isim>|n <mesaj>
```
> Parser bunu çerçeveler ama içeriği şu an kullanmaz (çoğu dükkân spam'i);
> uzunluk önekini bilmek akışın senkron kalması için ŞART.

### GELEN — kendi puan/durum  ✅ CANLI (14 bayt, header=0x11)
```
+0  u8   header = 0x11
+1  u32  dwVID    kendi vid'in (kayıtlarda 9525679 / 5090706 /
                  10925029 / 2856518 / 2528459='DOMALTAN')
                  NOT: son değeri değil, EN ÇOK GEÇEN değeri al —
                  akış nadiren kayınca hayalet vid'ler doğuyor
+5  u8   bType    puan/durum tipi
+6  ...  değer    artan sayaç (tecrübe/dayanıklılık adayı)
```
> Kendi karakterinin periyodik durum tiki. Haritayı etkilemez, yalnızca
> çerçeveleme için tüketilir. Alan anlamı henüz kesin değil.

### GELEN — GC_SYNC_POSITION (çoklu konum senkronu)  ✅ ÇÖZÜLDÜ → `0x05`

Tahmin edilen yapı doğru çıktı, header **0x05**. Tam ayrıntı ve doğrulama
için yukarıdaki "TOPLU KONUM ve İSİM" bölümüne bakın.
```
+0  u8   header = 0x05
+1  u16  wSize        toplam boy = 3 + 12*N
+3  [ u32 dwVID | i32 lX | i32 lY ] x N
```
> Giden yöndeki aynası `0x08`'dir (bkz. "GİDEN AKIŞ").

### GELEN — GC_NPC_POSITION (toplu NPC konumu)  ✕ AYRI PAKET GÖRÜLMEDİ

5 yakalamada bu yapıya uyan ayrı bir paket bulunamadı. Toplu konum işini
`0x05` görüyor; isim ise ayrı bir pakette (`0x88`) geliyor. Bu sunucuda
NPC_POSITION'ın kullanılmadığı, ikisinin ayrıldığı anlaşılıyor.

### GELEN — GC_MAIN_CHARACTER (kendi karakterin ilk bilgisi)  ◐ STANDART
```
+0  u8   header = ?
+1  u32  dwVID       SENİN vid'in
+5  char[…] sName
    ... wRaceNum, lX, lY, lZ, empire ...
```

### GELEN — GC_WARP (ışınlanma)  ◐ STANDART
```
+0  u8   header = ?
+1  i32  lX          yeni konum
+5  i32  lY
+9  i32  lAddr       yeni sunucu adresi (ip)
+13 u16  wPort       yeni port   ← kanal/harita geçişi burada yeni porta bağlanır
```

---

## SAVAŞ / HEDEF

### GELEN — GC_SET_TARGET_INFO (hedef bilgisi)  ◐ STANDART
```
+0  u8   header = ?
+1  u32  dwVID           hedef
+5  u8   bLevel          seviye
+6  u8   bRacePercent    **can %'si** (0..100)
```

### GELEN — GC_DAMAGE_INFO (hasar)  ◐ STANDART
```
+0  u8   header = ?
+1  u32  dwVID       hasar alan
+5  u8   bType       0=normal,1=kritik,2=zehir,...
+6  i32  iDamage     hasar miktarı
```

### GELEN — GC_CHARACTER_POINT_CHANGE (stat değişimi)  ◐ STANDART
```
+0  u8   header = ?
+1  u32  dwVID
+5  u8   bType       POINT tipi (0=seviye,1=tecrübe, HP/MP...)
+6  i64  value       yeni değer
+14 i64  amount      değişim
```

### GİDEN — CG_ATTACK (saldır)  ✅ CANLI (6 bayt)
```
+0  u8   header = 0x02   (giden yön: saldırı — DİKKAT: gelen 0x02 = varlık sil)
+1  u8   bType           saldırı tipi (0=normal)
+2  u32  dwVID           hedef
```
> 23 Ağu 2026 OUT yakalaması: `02 00 <vid>`. Aynı bayt (0x02) yöne göre farklı
> paket: gelen=CHARACTER_DEL, giden=ATTACK. Parser ikisini ayrı yollarda okur.

### GİDEN — CG_USE_SKILL (yetenek kullan)  ✅ CANLI (9 bayt)
```
+0  u8   header = 0x34
+1  u32  dwSkillVnum     yetenek vnum
+5  u32  dwTargetVID     hedef (0 = kendine/hedefsiz)
```
> OUT yakalaması: `34 02 00 00 00 <vid>` = vnum 2, hedef vid.

### GİDEN — CG_TARGET (hedef seç)  ✅ CANLI (5 bayt)
```
+0  u8   header = 0x3D
+1  u32  dwVID           hedef (0 = temizle)
```
> OUT yakalaması: `3D <vid>` ve `3D 00 00 00 00` (temizle) görüldü.

### GİDEN — CG_SHOOT (ok/mermi at)  ◐ STANDART
```
+0  u8   header = ?
+1  u8   bType
```

---

## EŞYA

### GELEN — GC_ITEM_GROUND_ADD (yere düşen eşya)  ✅ CANLI (21 bayt)
```
+0  u8   header = 0x1A
+1  i32  lX
+5  i32  lY
+9  i32  lZ          (yakalamada hep 0)
+13 u32  dwVID       yerdeki eşyanın örnek kimliği
+17 u32  dwVnum      eşya türü — **1 = Yang**
```
> Doğrulama (29 Ağu 2026, `r2_20260829_070117.pcap`): 81 aday bulundu,
> **81'inin de (%100)** vnum alanı `items_tr.txt` kataloğunda mevcut.
> Yakalananlar: Yang ×38, Kırmızı İksir(O), Mavi İksir(B/K/O), Havuç,
> YeşimTaşı Çan+0 — toplam 48 benzersiz eşya.
>
> ⚠️ **0x1A yöne göre farklı pakettir**: giden yönde CG_ON_CLICK (5 bayt).
> Parser gelen akışta bunu 5 bayt sayarken her eşya paketinde 16 bayt
> kayıyordu. 0x02 ile aynı durum (gelen=varlık sil, giden=saldırı).

### GELEN — GC_ITEM_GROUND_DEL (eşya kalktı)  ✅ CANLI (5 bayt)
```
+0  u8   header = 0x1B
+1  u32  dwVID
```
> 60 kez eşya vid'i taşıdığı görüldü (alınma / süre dolması).

### GELEN — eşya sahibi (kimin alabileceği)  ✅ CANLI (30 bayt)
```
+0  u8   header = 0x1F
+1  u32  dwVID       yerdeki eşya
+5  char[] isim      null ile biter
```
> 12 örneğin 12'sinde de boy 30 çıktı. Örnek: `1F | vid | "Kylian"`.

### GİDEN — CG_ITEM_PICKUP (yerden al)  ✅ CANLI (5 bayt)
```
+0  u8   header = 0x0F
+1  u32  dwVID       alınacak yer-eşyası
```
> ⚠️ **Bu belgede önceden `0x0D` yazıyordu — YANLIŞTI.** `Paket.topla()` o
> tahmini kullandığı için bu komut hiç çalışmamış olmalı. 29 Ağu 2026
> yakalamasında düzeltildi.
>
> Doğrulama: giden akışta `0x0F` taşıyan **22 konumun hepsinde** vid alanı,
> gelen `0x1A` paketlerinden bilinen GERÇEK bir yer-eşyası kimliğiydi
> (Yang ve iksirler). Ardışık iki `0x0F` arasındaki mesafe 17 çiftin
> **15'inde tam 5 bayt**; `0x0F`'ten 5 bayt sonra **22/22** durumda geçerli
> bir giden opcode başlıyor (`0x0F` ×16, `0x07` ×3, `0x3D` ×2, `0x02` ×1).
>
> Oyun loot toplarken arka arkaya gönderir:
> `0F vid1 | 0F vid2 | 0F vid3 | 07 <hareket>`

### GİDEN — CG_ITEM_USE (eşya kullan)  ◐ STANDART
```
+0  u8   header = ?
+1  u8   bCell_window
+2  u16  wCell       envanter slotu
```

---

## NPC ETKİLEŞİM / DİYALOG

### GİDEN — CG_ON_CLICK (NPC'ye tıkla / dükkânı aç)  ✅ CANLI (5 bayt)
```
+0  u8   header = 0x1A
+1  u32  dwVID       tıklanan varlık (vnum DEĞİL — sahnedeki örnek kimliği)
```
> Doğrulama (29 Ağu 2026, `eylem_npc_tikla_*.pcap`): bir NPC'ye 5 kez
> tıklandı, giden akışta **tam 5 kez** göründü; vid her seferinde aynı
> (12708), yalnızca tik alanı değişti.
>
> ⚠️ **TEK BAŞINA GÖNDERİLİRSE ÇALIŞMAZ.** Canlı denendi: yalnızca
> `1A vid` (5 bayt) gönderildiğinde sunucu dükkânı açmadı. İstemci bunu
> ASLA tek başına yollamıyor; hep `CG_MOVE(bFunc=0 = DUR)` ile **tek
> segmentte** gönderiyor — "durdum ve ona döndüm":
> ```
> 1A A4310000 | 07 00 00 24 <x> <y> <tik>     = 5 + 16 = 21 bayt
> ^CG_ON_CLICK  ^CG_MOVE (bFunc=0)
> ```
> Buradaki `x,y` **oyuncunun kendi konumudur** (hedefin değil), `bRot` ise
> NPC'ye bakan yön. 21 baytlık tam segment gönderilince dükkân açıldı.
>
> Bu, `0x02 CG_ATTACK`'in `0x08 CG_SYNC_POSITION` olmadan çalışmamasıyla
> aynı desen: **bazı eylemler yanlarındaki konum paketiyle birlikte
> gönderilmek zorunda.** Bir paket tek başına doğru olsa bile sunucu
> reddedebilir.
>
> ⚠️ **GELEN yönde 0x1A farklı bir pakettir**: ITEM_GROUND_ADD, 21 bayt.
> Aynı bayt, yöne göre iki ayrı paket.

### GİDEN — CG_SCRIPT_ANSWER (diyalog cevabı)  ◐ STANDART (2 bayt)
```
+0  u8   header = 0x1D
+1  u8   bAnswer     0 tabanlı seçim; 254 = kapat/onayla
```

### GİDEN — CG_SCRIPT_BUTTON  ◐ STANDART (2 bayt)
```
+0  u8   header = ?
+1  u8   bIdx
```

---

## TİCARET (özet)

### GİDEN — CG_SHOP (dükkân işlemi)  ✅ CANLI
```
+0  u8   header = 0x32
+1  u8   bSubHeader   0=KAPAT, 1=SATIN AL, 2=SAT, 3=SAT2
   SAT2 (0x03):  +2 u8 slot   +3 u8 adet        -> toplam 4 bayt
   KAPAT (0x00): gövde yok                       -> toplam 2 bayt
```
> Doğrulama (29 Ağu 2026, `eylem_satis_*.pcap`): 5 eşya satıldı, giden
> akışta **tam 5 kez** göründü. Değişen tek alan +2 (slot); +3 hep 01.
> ```
> 32 03 19 01   slot 25      32 03 2E 01   slot 46
> 32 03 1A 01   slot 26      32 03 33 01   slot 51
> 32 03 2D 01   slot 45
> ```
> Dükkânı kapatma tıklama kaydında ayrıca görüldü: her tıklamadan ~1.6 sn
> sonra `32 00`.
>
> ⚠️ Belgede önceden "0=SATIN AL, +2 u16 wCell, +4 u8 bCount" yazıyordu —
> **yanlıştı**. Doğrusu standart Metin2 enum'u: 0=END, 1=BUY, 2=SELL,
> 3=SELL2; slot ve adet birer BAYT.

### GİDEN — CG_EXCHANGE / SAFEBOX  ◐ STANDART
```
+0 u8 header  |  +1 u8 bSubHeader  |  ...alt komuta göre değişir
```

---

## SİSTEM / OTURUM

### GC_PING ↔ CG_PONG  ◐ STANDART
```
GELEN GC_PING:  +0 u8 header
GİDEN CG_PONG:  +0 u8 header        (cevap — bağlantı canlılık)
```

### GC_PHASE (oyun fazı)  ◐ STANDART
```
+0 u8 header  |  +1 u8 bPhase   (login/select/loading/game)
```

### GC_TIME_SYNC / CG_TIME_SYNC  ◐ STANDART
```
+0 u8 header  |  +1 u32 dwTime
```

---

## Notlar

- **Alt-başlıklı paketler** (GUILD, EXCHANGE, PARTY, FISHING, BIOLOG…): tek ana
  `header` + `bSubHeader(u8)` + alt komuta özel gövde. Metadata'daki
  `*_SUBHEADER_GC/CG_*` isimleri alt komutları listeler.
- **Uzunluk önekli paketler** (değişken boy — CHAT, SYNC_POSITION, listeler):
  `header(1) + wSize(u16) + gövde`. Sabit boylular önek taşımaz.
- Bir paketin **byte header değerini** kesinleştirmek için: `PC_CAPTURE.bat` ile
  o eylemi yaparken yakala, `tools/remove_bul.py` mantığıyla imzayı bul.
- Tüm 199 paketin **kesin ofset tablosu** ancak Il2CppDumper (v39 destekli) ile
  `libil2cpp.so`'nun FieldOffsets tablosundan çıkar. Bu yüzden ◐ işaretliler
  "standart M2 + alan adı doğrulandı, byte'ı teyit edilecek" demektir.
