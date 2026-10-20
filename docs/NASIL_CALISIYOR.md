# Yakalamadan Bayta — Paket Okuyucu Nasıl Çalışıyor

Bu doküman, bir oyun paketinin ağ kablosundan çıkıp panelde
"Kurt (Lv3) @ 9472,-2897 m" satırına dönüşene kadar geçtiği **her adımı**
anlatır. Tüm örnek baytlar bu projeyle yapılmış gerçek yakalamalardan
alınmıştır, uydurma değildir.

İlgili kaynak dosyalar: `PaketServisi.java`, `PaketAyristirici.java`,
`PaketKaydi.java`, `Koordinat.java`.

---

## 0. Kuşbakışı

```
   Romia2 sunucusu 185.128.114.87:30004
              │  düz TCP (TLS yok)
              ▼
   ┌──────────────────────────────────────────┐
   │ 1. tcpdump          root, wlan0, BPF     │  ham çerçeveler
   ├──────────────────────────────────────────┤
   │ 2. pcap çözümü      24 + 16 baytlık başlık│  tek tek paketler
   ├──────────────────────────────────────────┤
   │ 3. link katmanı     14 bayt (Ethernet)   │
   ├──────────────────────────────────────────┤
   │ 4. IPv4 başlığı     IHL×4, proto=6       │  kaynak/hedef IP
   ├──────────────────────────────────────────┤
   │ 5. TCP başlığı      dataOffset×4         │  portlar + yük sınırı
   ├──────────────────────────────────────────┤
   │ 6. yön tespiti      sunucu IP'sine göre  │  OUT / IN
   ├──────────────────────────────────────────┤
   │ 7. bayt okuma       LE int32 / float     │  alanlar
   ├──────────────────────────────────────────┤
   │ 8. anlamlandırma    opcode + ofset       │  konum / varlık / can
   ├──────────────────────────────────────────┤
   │ 9. katalog          vnum -> ad           │  "Kurt (Lv3)"
   └──────────────────────────────────────────┘
```

Her aşama bir öncekinin çıktısını daraltır. Hata genelde **aşama 3'te**
olur (link başlığı yanlış varsayılır) ve sonuç sessizce çöp olur.

---

## 1. Aşama: tcpdump

```
su -c "exec tcpdump -i wlan0 -U -s 0 -w - 'tcp and not port 443'"
```

| Parça | Ne yapar | Neden gerekli |
|---|---|---|
| `su -c` | root kabuğu | ham soket açmak `CAP_NET_RAW` ister; normal uygulama alamaz |
| `exec` | kabuk sürecinin üstüne biner | `destroy()` çağrıldığında gerçek tcpdump ölür, kabuk değil |
| `-i wlan0` | arayüz seçimi | emülatörde oyun trafiği bu arayüzden akar (`10.0.2.15`) |
| `-U` | tamponsuz yaz | varsayılan 4 KB tampon dolmayı bekler → 2-3 saniye gecikme |
| `-s 0` | tam yakalama | varsayılan kesme uzun paketleri budar, alanlar kaybolur |
| `-w -` | pcap'i stdout'a | Java `Process.getInputStream()` ile boruyu okur |
| `'tcp and not port 443'` | BPF filtresi | çekirdek düzeyinde eleme; kullanıcı alanına daha az veri gelir |

**`exec` neden önemli:** `su -c "tcpdump ..."` yazarsanız süreç ağacı
`su → sh → tcpdump` olur. `Process.destroy()` yalnızca `su`'yu öldürür,
tcpdump root olarak arkada kalmaya devam eder. `exec` ile `sh` kendini
tcpdump ile değiştirir, ağaç `su → tcpdump` olur ve tek sinyal yeter.
Yine de `onDestroy()` içinde `pkill tcpdump` yedeği vardır.

**BPF filtresi neyi eler:**

| Trafik | Durum |
|---|---|
| TCP 30004 (oyun) | geçer — hedef bu |
| TCP 443 (HTTPS) | elenir — zaten şifreli, sadece gürültü |
| TCP 80 / 8080 | geçer — istenmeyen gürültü, aşama 6'da elenir |
| UDP'nin tamamı | elenir (`tcp` şartı) |
| ICMP / ARP | elenir |

Daraltmak isterseniz `PaketServisi.FILTRE` sabitini
`tcp and host 185.128.114.87 and port 30004` yapın; eleme çekirdekte olur,
CPU ve pil belirgin düşer.

---

## 2. Aşama: pcap akışının çözümü

tcpdump'ın stdout'u **libpcap dosya biçimidir**. Yapısı:

```
┌────────────────────────┐
│ global başlık  24 bayt │  bir kez, akışın başında
├────────────────────────┤
│ kayıt başlığı  16 bayt │┐
│ paket verisi   N bayt  ││ her paket için tekrar
├────────────────────────┤│
│ kayıt başlığı  16 bayt ││
│ paket verisi   M bayt  │┘
└────────────────────────┘
```

### 2.1 Global başlık (24 bayt)

| Ofset | Boy | Alan | Bu cihazda |
|---|---|---|---|
| 0 | 4 | magic | `D4 C3 B2 A1` |
| 4 | 2 | ana sürüm | 2 |
| 6 | 2 | alt sürüm | 4 |
| 8 | 8 | saat dilimi + hassasiyet | 0 |
| 16 | 4 | snaplen | 262144 |
| **20** | 4 | **link tipi** | **1 = Ethernet** |

`magic` bayt sırasını söyler. `D4 C3 B2 A1` little-endian, `A1 B2 C3 D4`
big-endian demektir. Kod ilk baytı okuyup karar verir:

```java
int magic = global[0] & 0xFF;
boolean le = magic == 0xD4 || magic == 0x4D;
```

`& 0xFF` şart: Java'da `byte` **işaretlidir**, `0xD4` doğrudan okunursa
`-44` çıkar. `& 0xFF` sonucu `int`'e yükseltip 0-255 aralığına getirir.
Bu maske dosya boyunca her bayt okumasında tekrarlanır.

### 2.2 Kayıt başlığı (16 bayt)

| Ofset | Boy | Alan |
|---|---|---|
| 0 | 4 | zaman damgası, saniye |
| 4 | 4 | zaman damgası, mikrosaniye |
| **8** | 4 | **yakalanan boy** — bundan sonraki bayt sayısı |
| 12 | 4 | kablodaki gerçek boy |

Kod yalnızca ofset 8'i kullanır:

```java
int boy = i32(kayitBaslik, 8, le);
if (boy <= 0 || boy > 262144) throw new IllegalStateException(...);
byte[] ham = new byte[boy];
tamOku(in, ham);
```

Sınır kontrolü keyfi değil: akış senkronu kaçarsa `boy` saçma bir sayı
olur ve `new byte[boy]` ya `OutOfMemoryError` atar ya da saatlerce bekler.
Erken patlamak, sessizce bozulmaktan iyidir.

### 2.3 `tamOku` neden var

```java
private static void tamOku(InputStream in, byte[] b) throws Exception {
    int o = 0;
    while (o < b.length) {
        int n = in.read(b, o, b.length - o);
        if (n < 0) throw new EOFException();
        o += n;
    }
}
```

`InputStream.read()` **istediğiniz kadar bayt vermek zorunda değildir**.
Boru üzerinden okurken 16 bayt isteyip 9 bayt almak olağandır. Tek bir
`read()` çağrısına güvenmek, pcap senkronunu ilk yoğun anda kaybettirir.
Bu döngü isteneni tam alana kadar okur.

---

## 3. Aşama: link katmanı

pcap kaydının ilk baytları IP değil, **link katmanı başlığıdır**.
Boyu link tipine bağlıdır:

| Link tipi | Ad | Başlık boyu |
|---|---|---|
| 1 | Ethernet | **14 bayt** |
| 113 | LINUX_SLL (`-i any`) | 16 bayt |

```java
int linkBaslik = linkTipi == 113 ? 16 : 14;
```

**Bu iki baytlık fark, sessiz başarısızlığın bir numaralı sebebidir.**
Yanlış varsayarsanız IP başlığı 2 bayt kaymış olur, sürüm alanı `4`
çıkmaz, her paket sessizce atılır ve panel "0 paket" gösterir. Hiçbir
hata mesajı görmezsiniz.

Bu cihazda `link=1` doğrulandı (logcat: `pcap açıldı, link=1 başlık=14`).
`-i any` ile yakalarsanız 113 olur.

---

## 4. Aşama: IPv4 başlığı

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Sürüm|  IHL  |  ToS  |         Toplam Uzunluk                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Kimlik            |Bayrak|    Parça Ofseti            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   TTL     |  Protokol   |       Başlık Sağlaması              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Kaynak IP  (ofset 12)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Hedef IP   (ofset 16)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Kod:

```java
if (((b[o] >>> 4) & 0x0F) != 4) return;   // sürüm nibble'ı: IPv4 mü
int ihl = (b[o] & 0x0F) * 4;              // alt nibble: başlık boyu / 4
if (ihl < 20 || n < ihl + 20) return;
if ((b[o + 9] & 0xFF) != 6) return;       // protokol 6 = TCP
```

Üç ince nokta:

**İlk bayt iki alan taşır.** Üst 4 bit sürüm, alt 4 bit IHL. `>>> 4`
(işaretsiz kaydırma) üst nibble'ı alta indirir; `& 0x0F` alt nibble'ı
yalıtır. `>>` (işaretli kaydırma) kullanılsaydı negatif baytlarda üstten
1'ler dolar ve sonuç bozulurdu.

**IHL kelime sayısıdır.** Değer 5 ise başlık 5×4 = 20 bayttır. IP
seçenekleri varsa 6, 7… olabilir. Sabit 20 varsaymak, seçenekli
paketlerde TCP başlığını kaydırır.

**IP adresi 4 ham bayttır**, metin değil:

```java
private static String ip(byte[] b, int o) {
    return (b[o] & 0xFF) + "." + (b[o+1] & 0xFF) + "."
         + (b[o+2] & 0xFF) + "." + (b[o+3] & 0xFF);
}
```

---

## 5. Aşama: TCP başlığı ve yükün sınırı

| Ofset (TCP başlangıcından) | Boy | Alan | Bayt sırası |
|---|---|---|---|
| 0 | 2 | kaynak port | **big-endian** |
| 2 | 2 | hedef port | **big-endian** |
| 4 | 4 | sıra numarası | big-endian |
| 8 | 4 | onay numarası | big-endian |
| **12** | 1 | üst nibble = **veri ofseti** | — |

```java
int tcp = o + ihl;
int thl = ((b[tcp + 12] >>> 4) & 0x0F) * 4;   // veri ofseti × 4
int yukO = tcp + thl;                          // yük burada başlar
int yukN = o + n - yukO;                       // yük bu kadar uzun
if (yukN <= 0) return;                         // saf ACK/SYN, veri yok
```

**Bayt sırası tuzağı:** TCP/IP başlıkları **her zaman big-endian**
(ağ sırası), oyun yükü ise **little-endian**. Aynı fonksiyonda iki farklı
sıra kullanılır. Portlar için:

```java
public static int u16be(byte[] b, int o) {
    return ((b[o] & 0xFF) << 8) | (b[o + 1] & 0xFF);
}
```

Yük için (aşağıda) `ByteBuffer` + `LITTLE_ENDIAN`. Karıştırılırsa
port 30004 yerine 13429 okunur ve hiçbir paket eşleşmez.

**Yüksüz paketler:** TCP el sıkışması ve onaylar veri taşımaz. Yakalanan
paketlerin yarısından fazlası budur; `yukN <= 0` ile hemen atılır.

---

## 6. Aşama: yön tespiti

```java
boolean gidenMi = hedefIp.equals(OYUN_IP);
boolean gelenMi = kaynakIp.equals(OYUN_IP);
if (!gidenMi && !gelenMi) return;   // oyun trafiği değil
```

Geniş BPF filtresinin bıraktığı 80/8080 gürültüsü burada temizlenir.

Devralınan kodda yön `kaynakIP'nin ilk baytı == 10` ile belirleniyordu.
Emülatör ağı `10.0.2.15` olduğu için çalışıyordu ama ağ `192.168.x`
olsaydı **her paket ters yönde** etiketlenirdi. Sunucu IP'sine bakmak
ağdan bağımsızdır.

Yönün önemi: aynı opcode iki yönde farklı anlam taşıyabilir. `0x07`
giden yönde "ben buraya yürüyorum", gelen yönde "senin konumun bu".

---

## 7. Aşama: baytları sayıya çevirme

Dört temel okuyucu (`PaketAyristirici`):

```java
public static int u8(byte[] b, int o) { return b[o] & 0xFF; }

public static int u16be(byte[] b, int o) {
    return ((b[o] & 0xFF) << 8) | (b[o + 1] & 0xFF);
}

public static int i32le(byte[] b, int o) {
    return ByteBuffer.wrap(b, o, 4).order(ByteOrder.LITTLE_ENDIAN).getInt();
}

public static float f32le(byte[] b, int o) {
    return ByteBuffer.wrap(b, o, 4).order(ByteOrder.LITTLE_ENDIAN).getFloat();
}
```

### Little-endian ne demek

`0A 74 0E 00` dört baytı, LE'de **en düşük anlamlı bayt önce** yazılır:

```
bayt sırası:   0A    74    0E    00
ağırlık:      2^0   2^8   2^16  2^24
değer:      0x0E740A  =  947210
```

Elle hesabı: `0x00` `0x0E` `0x74` `0x0A` diye **ters okuyup** birleştirin
→ `0x000E740A` = 947210.

Big-endian olsaydı aynı baytlar `0x0A740E00` = 175,3 milyon olurdu — yani
makul koordinat aralığının çok dışında. Bayt sırasını yanlış seçtiğinizde
sayılar sadece "biraz yanlış" değil, **tanınmayacak kadar** yanlış çıkar.
Bu aslında iyi haberdir: hata sessiz kalmaz.

### `f32le` neden ayrı

Bazı alanlar tamsayı değil IEEE-754 tek duyarlıklı ondalıktır. `00 00 11 43`
LE'de `0x43110000` → **145.0**. Aynı baytları `i32le` ile okusaydınız
1125515264 çıkardı. Alan tipini bilmek zorunludur; tahmin yürütülemez.

---

## 8. Aşama: iki farklı çözüm yolu

Burası tasarımın kritik noktası.

> **TCP bir akış protokolüdür.** Gönderen tarafın "bir mesaj" olarak
> yazdığı baytlar, alıcıya aynı sınırlarla ulaşmaz. Bir TCP segmentinde
> üç mesaj olabilir; bir mesaj iki segmente bölünebilir.

Bu yüzden gelen yönde bir segmentin **0. baytı çoğu zaman opcode
değildir**. Kod iki ayrı yol kullanır:

| Yol | Metot | Kullanıldığı yer |
|---|---|---|
| Tek mesaj | `mesajCoz()` | giden yön (küçük, tek segmente sığıyor) ve sınırı bilinen mesajlar |
| Akış taraması | `akisiTara()` | gelen yön — imza arayarak tüm tamponu tarar |

### 8.1 Biriken tampon

```java
private void gelenAkisaEkle(byte[] b, int o, int n) {
    synchronized (gelenAkis) {
        gelenAkis.write(b, o, n);
        byte[] akis = gelenAkis.toByteArray();
        if (akis.length > AKIS_LIMIT) {              // 64 KB
            gelenAkis.reset();
            gelenAkis.write(akis, akis.length - AKIS_KORUNAN, AKIS_KORUNAN);  // son 32 KB
            akis = gelenAkis.toByteArray();
        }
        ayristirici.akisiTara(akis, akis.length);
    }
}
```

Neden biriktiriyoruz: iki segmente bölünmüş bir mesaj ancak birleşik
tamponda tam görünür. Tek segmenti tarasaydık o mesajı hiç göremezdik.

Neden kırpıyoruz: tampon sonsuz büyürse hem bellek şişer hem her tarama
yavaşlar. Son 32 KB, birkaç saniyelik trafiği kapsar; daha eskisi zaten
işlenmiştir.

Aynı varlığın her turda tekrar bulunması sorun değil — `DunyaDurumu`
idempotenttir, aynı veriyi tekrar yazmak durumu değiştirmez.

---

## 9. Gerçek örnekler — bayt bayt

Aşağıdaki dökümlerin hepsi bu projeyle yakalanmıştır.

### 9.1 `0x07` — giden hareket paketi (16 bayt)

Logcat satırı:

```
22:52:58.550  OUT  34772 -> 185.128.114.87:30004  op=0x07  len=16
    07 01 00 2F 5D BD 0E 00 AA 35 04 00 58 79 CE 25
```

Alan alan:

| Ofset | Bayt(lar) | Alan | Çözüm |
|---|---|---|---|
| 0 | `07` | opcode | hareket/durum |
| 1 | `01` | state | 1 = yürüyor |
| 2 | `00` | ? | çözülmedi |
| 3 | `2F` | yön baytı | 47 |
| 4-7 | `5D BD 0E 00` | x (int32 LE) | `0x000EBD5D` = **965981** |
| 8-11 | `AA 35 04 00` | y (int32 LE) | `0x000435AA` = **275882** |
| 12-15 | `58 79 CE 25` | ? | muhtemelen zaman damgası |

Yön hesabı — oyun 5 derecelik adımlarla sayar:

```java
derece = ((90 - yonBayti * 5) % 360 + 360) % 360;
      = ((90 - 47*5) % 360 + 360) % 360
      = ((90 - 235) % 360 + 360) % 360
      = (-145 + 360) % 360
      = 215
```

İki kez `% 360` ve `+ 360` var çünkü Java'da `%` **negatif sonuç
verebilir**: `-145 % 360` = `-145`, `145` değil. Python'un aksine bu
gerçek modülo değil kalan işlemidir. Ekleyip tekrar mod almak aralığı
`[0,360)` yapar.

Koordinat çevrimi:

```
metreX =  965981 / 100 =  9659.81  ->  9660
metreY = -275882 / 100 = -2758.82  -> -2759
```

Panel çıktısı: `hareket state=1 yon=215 965981,275882 (9660,-2759 m)` ✓

### 9.2 `0x01` — varlık doğuş paketi (38 bayt)

Bu, ismin geldiği pakettir. Gerçek örnek:

```
22:54:42.923  IN  185.128.114.87:30004 -> 34772  op=0x01  len=38
    01 FF B9 8E 00 00 00 11 43 0A 74 0E 00 CB 6B 04 00
    00 00 00 00 00 66 00 00 00 64 64 00 00 00 00 00 00 00 00 00 00
```

| Ofset | Bayt(lar) | Alan | Çözüm |
|---|---|---|---|
| 0 | `01` | opcode | doğuş |
| 1-4 | `FF B9 8E 00` | id (int32 LE) | `0x008EB9FF` = **9353727** |
| 5-8 | `00 00 11 43` | rot (float LE) | `0x43110000` = **145.0°** |
| 9-12 | `0A 74 0E 00` | x (int32 LE) | `0x000E740A` = **947210** |
| 13-16 | `CB 6B 04 00` | y (int32 LE) | `0x00046BCB` = **289739** |
| 17-21 | `00 00 00 00 00` | ? | çözülmedi |
| 22-25 | `66 00 00 00` | **vnum** (int32 LE) | `0x66` = **102** |
| 26-27 | `64 64` | ? | 100, 100 — ölçek/can olabilir |
| 28-37 | sıfırlar | ? | çözülmedi |

Katalog araması: `entities_tr.txt` içinde

```
102	0	0	3	Kurt
```

→ vnum 102, tip 0 (canavar), rank 0 (piyon), seviye 3, ad "Kurt".

Panel çıktısı:
`CANAVAR   Kurt (Lv3) [piyon]  #9353727 @ 9472,-2897 m  53 m uzakta` ✓

Her alan bağımsız olarak doğrulandı — id, koordinat ve vnum'un üçü de
paneldeki satırla birebir uyuştu. **`0x01`'in doğuş paketi olduğu, +22
alanının vnum taşıdığı böylece kendi ölçümümüzle kanıtlanmıştır.**

### 9.3 `0x03` — varlık hareketi (24 bayt)

```
    03 00 00 3D 96 6C 90 00 5B 27 0F 00 0A 13 04 00 50 29 58 25 EA 04 00 00
```

| Ofset | Bayt(lar) | Alan | Çözüm |
|---|---|---|---|
| 0 | `03` | opcode | hareket |
| 1-2 | `00 00` | imza sabiti | tarama bunu şart koşar |
| 3 | `3D` | ? | çözülmedi |
| 4-7 | `96 6C 90 00` | id (int32 LE) | 9464982 |
| 8-11 | `5B 27 0F 00` | x (int32 LE) | `0x000F275B` = 993115 → 9931 m |
| 12-15 | `0A 13 04 00` | y (int32 LE) | `0x0004130A` = 267018 → -2670 m |
| 16-23 | … | ? | zaman/hız olabilir |

**Kritik nokta: `0x03` içinde vnum YOKTUR.** Yalnızca instance id vardır.
Bu yüzden sadece `0x03` görülen bir varlık haritada nokta olarak çizilir
ama isimlendirilemez. İsim zinciri tek yönlüdür:

```
0x01 doğuş   ->  vnum  ->  entities_tr.txt  ->  ad + tip + rank + seviye
0x03 hareket ->  id    ->  yalnızca konum güncellemesi
```

Okuyucuyu karakter dururken açarsanız çevredeki canavarlar zaten doğmuş
olduğu için yalnızca `0x03` akar ve panel `+ N isimsiz` yazar.

### 9.4 `0x04` — sohbet/pazar (uzunluk önekli)

```
22:54:42.926  IN  op=0x04  len=55
    04 37 00 06 00 00 00 00 03 7C 4A 33 7C 6A 7C 4E 41 6C 61 6D 75 74
    7C 6E 20 45 6C 6D 61 73 20 63 65 76 68 65 72 69 20 73 61 74 FD 6C
    FD 72 20 34 35 30 6B 20 64 61 6E
```

| Ofset | Bayt(lar) | Alan | Çözüm |
|---|---|---|---|
| 0 | `04` | opcode | sohbet |
| 1-2 | `37 00` | **boy (u16 LE)** | `0x0037` = **55** |
| 3 | `06` | kanal tipi | |
| 4-8 | … | id / bayrak | |
| 9+ | ASCII | metin | `Alamut: Elmas cevheri satılır 450k dan` |

`boy` alanı **toplam mesaj boyudur**, gövde boyu değil: 55 bayt okununca
sıradaki mesaj başlar. TCP yükü de tam 55 bayt geldi, yani bu segment tek
mesaj taşıyordu.

Metindeki `FD` baytları Türkçe `ı` harfidir — kodlama UTF-8 değil,
Windows-1254 / CP857 ailesinden. UTF-8 varsayarsanız Türkçe karakterler
bozulur.

### 9.5 `0x11` — durum güncellemesi (14 bayt)

```
    11 AF 59 91 00 12 00 00 00 00 46 00 00 00
    11 AF 59 91 00 5F 00 00 00 00 00 00 00 00
```

Art arda iki kayıt, ikisi de 14 bayt ve aynı id (`0x009159AF`). Sabit boy
buradan çıkarıldı: aynı opcode'un tekrar aralığı mesaj boyunu verir.

---

## 10. Çerçeveleme: iki şema bir arada

Yukarıdaki örnekler protokolün karma yapıda olduğunu gösteriyor:

| Şema | Boy nereden gelir | Doğrulanan opcode'lar |
|---|---|---|
| Uzunluk önekli | `opcode(1) + u16le boy` | `0x04` |
| Sabit boylu | opcode boyu ima eder | `0x01`=38 · `0x03`=24 · `0x07`=16 · `0x11`=14 |

Bu tabloyla gerçek yakalamalarda IN akışının **%98-100'ü** çözülüyor
(`tools/analiz.py` çıktısı). Yani protokol tamamen çerçevelenebilir
durumda — imza taraması aslında geçici bir çözümdür.

**Neden hâlâ imza taraması kullanılıyor:** tablo henüz eksik. `0x13` ve
`0x7F` gibi opcode'ların boyu bilinmiyor; bilinmeyen tek bir opcode
senkronu kaybettirir ve sonraki tüm mesajlar çöp olur. İmza taraması
yavaş ve yanlış-pozitife açıktır ama **senkron kaybetmez**. Tablo
tamamlandığında çerçeveleyiciye geçilmelidir.

`tools/analiz.py` içindeki `cerceveler()` fonksiyonu senkron kaybında
bilinen bir opcode görene kadar ilerleyip devam eder ve hangi bölgelerin
çözülemediğini raporlar. Yeni opcode boyları böyle keşfedilir.

---

## 11. Makuliyet süzgeçleri

İmza taraması her ofseti denediği için rastgele baytlar da eşleşebilir.
Her alan bir aralık testinden geçer:

| Test | Aralık | Gerekçe |
|---|---|---|
| varlık id | `1.000 < id < 100.000.000` | gerçek id'ler ~9,3-9,5 milyon |
| ham koordinat | `1.000 < v < 10.000.000` | harita 0-100.000 m = 0-10M birim |
| vnum | `0 < v < 100.000` | katalogdaki en büyük vnum ~20.700 |
| rotasyon | `0 ≤ rot ≤ 360`, NaN değil | float alanın en güçlü testi |
| maks can | `1.000 < maks < 50.000.000` | |
| can | `0 ≤ can ≤ maks × 1,05` | %5 pay: buff'lı can maksı aşabiliyor |

Float alanın NaN testi özellikle güçlüdür: rastgele dört baytın hem
geçerli hem `[0,360]` aralığında bir float olma olasılığı çok düşüktür.

Tek bir eşleşmeye yine de güvenilmez. Pratikte doğru varlıklar **her
tarama turunda tekrar** görünür, yanlış pozitifler görünmez.
`DunyaDurumu` 60 saniye görülmeyen varlığı düşürür (`VARLIK_OMRU_MS`).

---

## 12. Koordinat matematiği

```java
public static final float BIRIM_METRE = 100.0f;

public static float hamXMetre(int hamX) { return hamX / BIRIM_METRE; }
public static float hamYMetre(int hamY) { return -hamY / BIRIM_METRE; }
```

İki dönüşüm var:

**Ölçek:** 1 metre = 100 ham birim. Oyun konumu tamsayı santimetre gibi
tutuyor — ondalık yok, yuvarlama hatası yok.

**Y ekseni tersliği:** ham Y **pozitif** iken harita Y'si **negatiftir**.
`hamYMetre` işareti çevirir. Örnek: ham `275882` → `-2758.82 m`.

Harita çizerken bu bir kez daha ters çevrilir, çünkü ekran Y'si aşağı
doğru büyür:

```java
private float ekranY(float metreY, float benimMY) {
    return getHeight() / 2f - (metreY - benimMY) * olcek();
}
```

Sonuçta kuzey yukarı bakar. İşaret hatası yaparsanız harita dikeyde
aynalanır — canavarlar doğru mesafede ama yanlış tarafta görünür, ki bu
fark etmesi en zor hatalardan biridir.

**Birim tuzağı:** `0x01` ve `0x03` alanları ham int32'dir; `0x68` alanları
**float ve metre** cinsindendir. `0x68` çözülürken `×100` ile ham birime
getirilir. Karıştırılırsa harita 100 kat şaşar.

---

## 13. Katalog araması

`OyunKatalogu` üç dosyayı `SparseArray` içine yükler (67-200 ms):

| Dosya | Satır | Biçim |
|---|---|---|
| `entities_tr.txt` | 2.857 | `vnum ⇥ tip ⇥ rank ⇥ seviye ⇥ ad` |
| `metins_tr.txt` | 195 | `vnum ⇥ ad` — entities'te olmayanları tamamlar |
| `items_tr.txt` | 28.655 | `vnum ⇥ ad` |

Yükleme arka planda yapılır: 28 bin satırlık `items_tr.txt` ana iş
parçacığında okunursa arayüz donar.

`tip` sütunu Metin2'nin `CHAR_TYPE` enum'udur:

| Değer | Anlam | Adet |
|---|---|---|
| 0 | canavar | 1.513 |
| 1 | NPC | 732 |
| 2 | metin taşı | 193 |
| 3 | bölge geçişi | 137 |
| 4 | kapı | 14 |
| 5 | bina | 56 |
| 9 | işaret (GOTO) | 212 |

`Varlik.etkinTip()` önce katalogdaki tipe bakar, yoksa pakette gelen tipe
düşer. Katalog daha güvenilirdir: paket alanı yanlış çözülmüş olabilir,
katalog dosyası oyunun kendi verisidir.

---

## 14. Nerede kırılır

| Belirti | Muhtemel sebep | Kontrol |
|---|---|---|
| Hiç paket yok | `su` reddedildi | logcat'te `pcap açıldı` satırı var mı |
| `pcap açıldı` var, sayaç 0 | sunucu IP değişti | `tcpdump -nn tcp port 30004` ile bak |
| Her paket atılıyor | link başlığı yanlış | `link=` değeri 1 mi 113 mü |
| Portlar saçma | big/little endian karıştı | `u16be` kullanıldığından emin ol |
| Koordinatlar milyonlarca | LE yerine BE okundu | `i32le` mi çağrılıyor |
| Harita dikeyde ters | Y işareti çevrilmemiş | `hamYMetre` negatifliyor mu |
| Varlık var, isim yok | doğuş paketi kaçırıldı | §9.3 — yürü, yeni varlık doğsun |
| İsim `vnum 12345` | vnum katalogda yok | `entities_tr.txt`'e ekle |
| Türkçe karakter bozuk | kodlama UTF-8 sanıldı | §9.4 — CP1254/CP857 |
| tcpdump arkada kaldı | servis düzgün kapanmadı | `adb shell "su -c 'pkill tcpdump'"` |

---

## 15. Özet akış — tek bakışta

```
tcpdump   →  pcap kaydı
             ├─ global başlık 24 B   → bayt sırası + link tipi
             └─ kayıt başlığı 16 B   → paket boyu (@8)
                  ↓
link katmanı 14 B (Ethernet) atlanır
                  ↓
IPv4:  sürüm == 4 ?   proto == 6 ?   ihl = (b[0] & 0x0F) * 4
       kaynak IP @12,  hedef IP @16
                  ↓
TCP:   thl = (b[12] >>> 4) * 4
       portlar @0 / @2   (BIG endian)
       yük = [tcp+thl ... paket sonu],  boş ise at
                  ↓
yön:   hedef == sunucu ? OUT : IN,  ikisi de değilse at
                  ↓
OUT → mesajCoz()    : opcode @0 güvenilir
IN  → akisiTara()   : biriken 32-64 KB tamponda imza ara
                  ↓
alanlar: i32le / f32le   (LITTLE endian)
                  ↓
makuliyet süzgeçleri  (id / koordinat / vnum / NaN)
                  ↓
DunyaDurumu.varlikBildir(id, vnum, tip, x, y, can, maks)
                  ↓
vnum ilk kez öğrenildiyse → OyunKatalogu → "Kurt (Lv3) [piyon]"
                  ↓
harita çizimi  ·  panel listesi  ·  R2_VARLIK logu
```

---

## 16. Kendin doğrula

Bu dokümandaki her sayıyı kendi cihazında yeniden üretebilirsin:

```
PC_CAPTURE.bat 30
```

Sayaç başlayınca **yürü** (doğuş paketleri için şart). Çıktı:
çerçeveleme yüzdesi, opcode dağılımı, çözülemeyen bölgeler ve
isimlendirilmiş doğuş adayları.

Tek bir opcode'un anlamını doğrulamak için:

1. Panelde **Paket** sekmesi → **Temizle**
2. **IN**'i kapat, sadece **OUT** açık kalsın
3. Oyunda **tek bir adım** yürü
4. Panele dön — ilk kayıt `op=0x07` olmalı

Aynı hareketi 3-4 kez tekrarlayıp hex'leri yan yana koy: sabit kalan
baytlar opcode/bayrak, değişenler koordinattır. Protokolün geri kalanı
da tam olarak böyle çözüldü.
