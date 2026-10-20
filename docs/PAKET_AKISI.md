# Romia2 — Paket Akışı, Yakalama Filtreleri ve Çözümlenen Alanlar

> Bu doküman **ne** olduğunu anlatır. **Nasıl** yapıldığını — tcpdump'tan
> tek tek baytlara kadar — [NASIL_CALISIYOR.md](NASIL_CALISIYOR.md) anlatır.

Bu doküman **hangi yolla ne yakalanıyor, hangi filtre neyi eliyor, yakalanan
baytın hangi alanı ne anlama geliyor** sorularını tek yerde toplar.

Kaynaklar: `Romia2Bot-Temiz/app/.../RootCaptureService.java`, `socket_hook.js`
(Frida), `analiz/BOT_DAVRANIS_ANALIZI.md`. Alan ofsetleri **gözlemlenmiştir**,
resmî bir şema değildir — her biri makuliyet kontrolüyle doğrulanır.

---

## 1. Sunucu ve taşıma

| Alan | Değer | Not |
|---|---|---|
| Oyun sunucusu | `185.128.114.87` | tek IP |
| Oyun portu | **TCP 30004** | düz TCP, TLS yok |
| Bayt sırası | **little-endian** (int32/float) | port alanları hariç (TCP başlığı big-endian) |
| Ölçek | 1 metre = **100 ham birim** | |
| Y ekseni | ham koordinatta **ters** (`ekranY = -hamY/100`) | |

Trafik TLS ile sarılmadığı için yük doğrudan okunabilir. Bu, aşağıdaki tüm
yakalama yollarının çalışmasının tek sebebidir.

---

## 2. Üç yakalama yolu — aynı baytlar, farklı görüntü

```
                    ┌──────────────────────────────────────────┐
   oyun süreci      │  send() / recv()   ← 2. yol: Frida hook  │
                    └────────────────┬─────────────────────────┘
                                     │ (mesaj sınırı KORUNUR)
                          çekirdek TCP yığını
                                     │ (mesaj sınırı KAYBOLUR)
                    ┌────────────────┴─────────────────────────┐
   ağ arayüzü       │  wlan0          ← 1. yol: tcpdump/pcap   │
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────┴─────────────────────────┐
   TUN cihazı       │  VpnService     ← 3. yol: yerel VPN      │
                    └──────────────────────────────────────────┘
```

Aradaki farkı anlamamak, bu protokolde en sık yapılan hatadır:

> **TCP bir akış protokolüdür.** Bir segmentte birden çok oyun mesajı olabilir,
> bir mesaj iki segmente bölünebilir. Bu yüzden `tcpdump` yolunda TCP yükünün
> **0. baytı çoğu zaman opcode DEĞİLDİR**. `send()` hook'unda ise uygulamanın
> yazdığı tampon görüldüğü için 0. bayt gerçek opcode'dur.

Bu projede iki yol da uygulanır ve **farklı çözümleyicilere** gider:

| Yol | Çözümleyici | Neden |
|---|---|---|
| tcpdump (gelen) | `PaketAyristirici.akisiTara()` | sınır yok → imza taraması |
| tcpdump (giden) | `PaketAyristirici.mesajCoz()` | giden mesajlar tek segmente sığacak kadar küçük |
| hook | `PaketAyristirici.mesajCoz()` | sınır korunuyor → doğrudan opcode |

---

## 3. Yol 1 — tcpdump / pcap (bu projede kullanılan)

Kod: `PaketServisi.java`

```
su -c "exec tcpdump -i wlan0 -U -s 0 -w - 'tcp and not port 443'"
```

| Parça | Anlamı | Neden böyle |
|---|---|---|
| `su -c` | root | ham arayüz okuma root ister |
| `-i wlan0` | arayüz | MuMu/emülatörde oyun trafiği buradan akar |
| `-U` | tamponsuz | her paket anında boruya düşer, gecikme olmaz |
| `-s 0` | tam yakalama | kesme yok; uzun paketler bozulmaz |
| `-w -` | stdout'a pcap | Java tarafı boruyu okur |
| `tcp and not port 443` | **BPF filtresi** | aşağıya bak |

### 3.1 `tcp and not port 443` filtresi ne yapar

| Trafik | Durum | Sonuç |
|---|---|---|
| TCP 30004 (oyun) | ✅ geçer | hedeflenen |
| TCP 443 (HTTPS) | ❌ elenir | zaten TLS, okunamaz — gürültü |
| TCP 80, 8080 vb. | ✅ geçer | istenmeyen gürültü |
| **UDP tamamı** | ❌ elenir | `tcp` şartı; ses/keşif trafiği görünmez |
| ICMP, ARP | ❌ elenir | |
| Saf ACK/SYN (yüksüz TCP) | ✅ geçer ama | `yukN <= 0` ile atılır |

**Daralttığınızda ne kazanırsınız:** filtreyi

```
tcp and host 185.128.114.87 and port 30004
```

yaparsanız çekirdek düzeyinde eleme olur; Java tarafı yalnızca oyun paketlerini
görür, CPU ve pil belirgin düşer. Bu projede geniş filtre bilinçli tercihtir —
sunucu IP'si değişirse trafik yine de görünür kalır; daraltma
`PaketServisi.FILTRE` sabitinden yapılır.

### 3.2 pcap akışının yapısı

| Bölüm | Boy | İçerik |
|---|---|---|
| Global başlık | 24 bayt | magic (bayt sırası), link tipi @20 |
| Kayıt başlığı | 16 bayt | zaman damgası, yakalanan boy @8 |
| Link katmanı | 14 veya **16** bayt | Ethernet = 14, `LINUX_SLL` (tip 113) = 16 |
| IPv4 başlığı | IHL×4 | protokol @9 (6 = TCP), src IP @12, dst IP @16 |
| TCP başlığı | data-offset×4 | src port @0, dst port @2 (big-endian) |
| Yük | kalan | oyun baytları |

Link tipi yanlış varsayılırsa **her paket 2 bayt kayar** ve hiçbir alan
tutmaz — sessiz başarısızlığın en yaygın sebebi budur.

### 3.3 Yön tespiti

Eski yaklaşım kaynak IP'nin ilk baytına bakıyordu (`10.x` = giden). Bu, ağ
`192.168.x` olduğunda çalışmaz. Bu projede yön **sunucu IP'sine göre**
belirlenir:

* `hedefIP == 185.128.114.87` → **OUT** (istemci → sunucu)
* `kaynakIP == 185.128.114.87` → **IN** (sunucu → istemci)
* ikisi de değilse paket tamamen atlanır

Bu, geniş BPF filtresinin bıraktığı gürültüyü uygulama katmanında temizler.

---

## 4. Yol 2 — Frida `send()` / `recv()` hook (referans)

Kaynak: `socket_hook.js`. Bu projede kod olarak yok; ofsetlerin çıkarıldığı
yer olduğu için belgelenmiştir.

| Hook | Filtre | Yakalanan |
|---|---|---|
| `connect()` | `family==AF_INET && ip==185.128.114.87 && port==30004` | oyun soket fd'si |
| `send()` | `fd == gameFd && 0 < len < 4096` | giden mesaj, **sınırı korunmuş** |
| `recvfrom()` | `2 <= n < 65536` | gelen mesaj, **sınırı korunmuş** |

Avantajı: opcode ofset 0'da kesin. Dezavantajı: root + Frida server gerektirir
ve oyun sürecine müdahale eder (tespit yüzeyi büyür). tcpdump yolu tamamen
pasiftir; süreç dışından okur.

## 5. Yol 3 — VpnService / TUN (bu projede yok, notu önemli)

`VpnService.establish()` çağırıp TCP/UDP forwarder yazmazsanız **oyunun
interneti kesilir**. TUN'a alınan paketi kullanıcı alanında yeniden
bağlamak gerekir. Yakalama için tcpdump yolu çok daha ucuzdur; VPN yolu ancak
root yoksa anlamlıdır.

---

## 6. Opcode tablosu

Doğrulama sütunu: **T** = tcpdump akışında imza taramasıyla, **H** = hook'ta
doğrudan, **?** = trafikte görülüyor ama gövdesi çözülmedi.

### 6.1 Giden — istemci → sunucu (`OUT`, dst 30004)

| Op | Ad | Min boy | Alanlar | Doğrulama |
|---|---|---|---|---|
| `0x07` | hareket / durum | 16 | `state` u8 @1 · `yön` u8 @3 · `x` i32le @4 · `y` i32le @8 | H + T |
| `0x02` | hedef seç | 6 | `00` @1 · `id` i32le @2 | T |

`0x07` yön baytı **5 derecelik adımlar** kullanır:

```
derece = ((90 - yönBaytı * 5) mod 360 + 360) mod 360
```

`state` gözlemi: `0x00` ve `0x01` konum senkronu taşır (hook bu ikisinde
konumu yazar); diğer değerler farklı hareket durumları olabilir — çözülmedi.

### 6.2 Gelen — sunucu → istemci (`IN`, src 30004)

| Op | Ad | Min boy | Alanlar | Doğrulama |
|---|---|---|---|---|
| `0x01` | varlık doğdu | 26 | `id` i32le @1 · `rot` f32le @5 · `x` i32le @9 · `y` i32le @13 · `tip` i32le @22 | T |
| `0x03` | varlık hareketi | 24 | `00 00` @1 · `id` i32le @4 · `x` i32le @8 · `y` i32le @12 | T |
| `0x3F` | can güncellemesi | 13 | `id` i32le @1 · `can` i32le @5 · `maks` i32le @9 | T |
| `0x68` | varlık senkronu | 32 | gövde @16: `vnum` u32 · `x` f32 · `y` f32 · `tip` u32 | H |
| `0x07` | konum yankısı | 16 | `x` i32le @4 · `y` i32le @8 | H |
| `0x0F` `0x1A` `0x1D` `0x32` `0x34` `0x3D` | — | — | trafikte var, gövde çözülmedi | ? |

**Dikkat — iki farklı koordinat birimi:** `0x01`/`0x03` alanları **ham
birimdir** (int32), `0x68` alanları **metredir** (float). `0x68` çözülürken
`×100` ile ham birime getirilir, yoksa harita 100 kat küçük çizilir.

### 6.3 `tip` alanı

| Değer | Anlam | Radar rengi |
|---|---|---|
| 0 | MOB | `#FF3232` |
| 1 | NPC | `#00FF00` |
| 2 | METIN | `#0050FF` |
| 6 | PC (oyuncu) | `#AA3CFF` |
| 9 | DROP | `#00E5E5` |

`0x01` paketindeki `tip` alanı ile `0x68`'deki `tip` aynı numaralandırmayı
kullanıyor gibi görünüyor, ancak `0x01`'de 8001–8099 aralığı metin taşı
vnum'ları olarak da gözlemlendi — **bu alan kesin çözülmedi**.

---

## 7. İmza taraması ve yanlış pozitifler

Gelen yönde mesaj sınırı bilinmediği için `akisiTara()` **her ofseti** dener.
Bu, kaçınılmaz olarak rastgele bayt dizilerini de eşleştirir. Elemek için her
alan bir aralık testinden geçer:

| Test | Aralık | Kod |
|---|---|---|
| varlık id | `1.000 < id < 100.000.000` | `PaketAyristirici.makulId` |
| ham koordinat | `1.000 < v < 10.000.000` | `Koordinat.makulHam` |
| tip | `0 < tip < 100.000` | — |
| rotasyon | `0 ≤ rot ≤ 360`, NaN değil | — |
| maks can | `1.000 < maks < 50.000.000` | — |
| can | `0 ≤ can ≤ maks × 1,05` | — |

Bu eşikler dar tutulmuştur; yine de tek bir eşleşmeye güvenilmemeli.
Pratikte doğru varlıklar **her tarama turunda tekrar** görünür, yanlış
pozitifler görünmez. `DunyaDurumu` bu yüzden 60 saniye görülmeyen varlığı
düşürür (`VARLIK_OMRU_MS`).

### 7.1 Akış tamponu

Gelen segmentler `ByteArrayOutputStream` içinde birikir; 64 KB'ı aşınca son
32 KB korunur. Sebep: iki segmente bölünmüş bir mesaj ancak birikmiş
tamponda tam görünür. Tampon her segmentte yeniden taranır — bu, aynı
varlığın birden çok kez raporlanmasına yol açar ama `DunyaDurumu` idempotent
olduğu için zararsızdır.

---

## 8. Ölçüm alma yöntemi (tek hareket testi)

Bir opcode'un anlamını doğrulamanın en temiz yolu:

1. Panelde **Paket** sekmesini aç, **Temizle**'ye bas.
2. Oyuna dön, **tek bir işlem** yap — sadece bir adım yürü.
3. Panele dön, **OUT** süzgecini aç, **IN**'i kapat.
4. Listedeki ilk kayıt neredeyse kesinlikle o işlemin paketidir.

Aynı işlemi 3–4 kez tekrarlayıp **değişen baytları** işaretleyin: sabit
kalanlar opcode/bayrak, değişenler koordinat/id'dir.

---

## 9. Bu projenin sınırı

`PaketServisi` yalnızca **okur**. Ne ham sokete yazar, ne oyun sürecine
enjeksiyon yapar, ne de sunucuya yapay paket üretir. Komut kuyruğunun
varsayılan kanalı `LogKanali`'dir — komutu yalnızca kaydeder.

Yürütme katmanı eklenecekse `KomutKanali` arayüzü uygulanır; kuyruk, rota
takibi ve harita mantığının hiçbiri değişmez. Bu ayrım bilinçlidir: karar
mantığı, gönderim mekanizmasından bağımsız olarak test edilebilir kalır.

---

## 10. Hızlı başvuru

```
sunucu     185.128.114.87:30004  (düz TCP)
arayüz     wlan0
BPF        tcp and not port 443          → daralt: tcp and host <ip> and port 30004
ölçek      1 m = 100 birim,  ekranY = -hamY/100
OUT        0x07 hareket(x@4,y@8) · 0x02 hedef(id@2)
IN         0x01 doğdu(id@1,x@9,y@13,tip@22) · 0x03 hareket(id@4,x@8,y@12)
           0x3F can(id@1,can@5,maks@9) · 0x68 sync(gövde@16, metre float)
tip        0 MOB · 1 NPC · 2 METIN · 6 PC · 9 DROP
```

---

## 11. Mesaj çerçeveleme — doğrulanmış bulgu (21 Ağustos 2026 yakalaması)

30 saniyelik gerçek yakalama (`log/ornek_bekleme.pcap`, 5088 bayt IN)
üzerinde çerçeveleme çözüldü. Akış **rastgele değil**, düzenli mesajlardan
oluşuyor ve iki farklı boy şeması var:

| Şema | Yapı | Doğrulanan opcode'lar |
|---|---|---|
| **Uzunluk önekli** | `opcode(1) + boy(u16 LE) + gövde` — `boy` toplam mesaj boyudur | `0x04` (sohbet/pazar) |
| **Sabit boylu** | opcode boyu ima eder | `0x03` = 24 bayt · `0x11` = 14 bayt |

Bu tabloyla IN akışının **%98'i** (5001/5088 bayt, 104 mesaj) çözülüyor.
Kalan 87 bayt boyu bilinmeyen üç opcode'a ait: `0x7F`, `0x13`.

`0x04` gövdesi düz ASCII sohbet/pazar metni taşıyor
(`|J3|j|NGARGOYL|n 1 K HP Lİ DUSUK LWL BİLEZİK ALINIR`).

**Neden önemli:** çerçeveleme tamamlanırsa §7'deki imza taraması tamamen
gereksiz hâle gelir — yanlış pozitif riski sıfırlanır ve her alan kesin
ofsetten okunur. Bugünkü kod hâlâ imza taraması kullanıyor; çerçeveleyici
PC tarafındaki `tools/analiz.py` içinde denenebilir durumda.

### 11.1 `0x01` doğuş paketi — DOĞRULANMADI

Aynı yakalamada `0x01` baytı akışta **toplam 1 kez** geçiyor ve imza
taraması hiçbir eşleşme bulmuyor. Yani bu yakalamada doğuş paketi yok.

Sebep basit: karakter sabit duruyordu. Doğuş paketleri yalnızca bir varlık
**görüş alanına ilk girdiğinde** gönderilir. Yakalama başladığında çevredeki
canavarlar çoktan doğmuştu.

Sonuç: `0x01 → id@+1, rot@+5, x@+9, y@+13, vnum@+22` yapısı devralınan
koddan gelmektedir ve **kendi ölçümümüzle doğrulanmamıştır**. Doğrulamak
için `PC_CAPTURE.bat` ile yakalama yapıp **yakalama sırasında yeni bir
alana yürümek** gerekir.

### 11.2 `0x03` yalnızca instance id taşır

Doğrulandı: 36 adet `0x03` kaydından 18 ayrı varlık çıktı, hepsi oyuncunun
±40 m çevresinde. Ama `0x03` gövdesinde **vnum yok** — sadece
`id / x / y`. Bu yüzden yalnızca `0x03` gören bir varlık haritada nokta
olarak çizilir ama **isimlendirilemez**.

İsim zinciri şöyle işler:

```
doğuş paketi → vnum   ──►  entities_tr.txt  ──►  ad + tip + rank + seviye
0x03           → id    ──►  yalnızca konum güncellemesi
```

Yani isimler ancak doğuş paketi çözüldüğünde görünür.

## 12. Katalog dosyaları

`app/src/main/assets/` altında, `OyunKatalogu` tarafından 67 ms'de yüklenir.

| Dosya | Satır | Biçim |
|---|---|---|
| `entities_tr.txt` | 2.857 | `vnum ⇥ tip ⇥ rank ⇥ seviye ⇥ ad` |
| `metins_tr.txt` | 195 | `vnum ⇥ ad` (entities'te olmayanları tamamlar) |
| `items_tr.txt` | 28.655 | `vnum ⇥ ad` |

`entities_tr.txt` 2. sütunu Metin2'nin `CHAR_TYPE` enum'udur. Dosyadaki
dağılım bunu doğruluyor:

| Değer | Anlam | Adet |
|---|---|---|
| 0 | canavar | 1.513 |
| 1 | NPC | 732 |
| 2 | metin taşı | 193 |
| 3 | bölge geçişi | 137 |
| 4 | kapı | 14 |
| 5 | bina | 56 |
| 9 | işaret (GOTO) | 212 |

**Düzeltme:** Frida betiğindeki `9 = DROP` etiketi yanlıştı. 9 = GOTO,
yani harita üzerindeki "şuraya git" işaretleri (`Kuzey-R.D. 415 136`,
`Ejderha kralına git` gibi kayıtlar bunu gösteriyor).

3. sütun rank'tır: 0 piyon … 4 boss, 5 kral. 4. sütun seviyedir.
