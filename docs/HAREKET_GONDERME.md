# Hareket Paketi Gönderme — Proxy Yolu

## Neden "Sunucuya Bağlan → Hareket Et" çalışmıyordu

Eski `BasitGonderici` **sıfırdan yeni bir TCP soketi** açıp `0x07` yazıyordu.
Oyun sunucusu bağlantı bazında durum tutar:

```
handshake  →  CG_LOGIN (auth token)  →  karakter seçimi  →  oyun fazı  →  0x07 geçerli
```

Karakteri oynatan soket, oyun istemcisinin **kendi doğrulanmış soketi**. Yeni
açılan sokete yazılan hiçbir şey karakteri kıpırdatmaz; sunucu doğrulanmamış
bağlantıyı okumadan atar. Ama `connect()` ve `write()` yerelde başarılı olduğu
için buton yine "✅ Gönderildi" diyordu — yanıltıcı.

## Yeni yol: şeffaf proxy (araya girme)

Paketi, istemcinin **zaten açık ve doğrulanmış** akışına yazıyoruz.

```
oyun istemcisi ──┐                          ┌── oyun sunucusu
                 │  iptables REDIRECT       │  185.128.114.87:30004
                 └─► 127.0.0.1:30104 (biz) ─┘
```

`ProxyServisi` root ile `iptables -t nat OUTPUT` zincirine iki kural yazar:

```
# 1) muafiyet: proxy'nin kendi yukarı bağlantıları (kaynak port havuzu) atlanır
iptables -t nat -A OUTPUT -p tcp -d 185.128.114.87 --sport 30105:30136 -j RETURN
# 2) yönlendirme: oyunun trafiği yerel dinleyiciye alınır
iptables -t nat -A OUTPUT -p tcp -d 185.128.114.87 -j REDIRECT --to-ports 30104
```

Oyunun sunucuya giden TCP'si yerel dinleyiciye (30104) düşer. Proxy yukarı
yönde gerçek sunucuya **30105–30136 aralığındaki bir kaynak porttan**
bağlanır; 1. kural bu bağlantıları yönlendirmeden muaf tutar, böylece döngü
olmaz. Kurallar porta göre değil IP'ye göre eşleşir; giriş sunucusu (30001)
ve bütün kanallar (30000 + 4 × kanal) aynı yoldan geçer.

> **Neden tek port değil de havuz (12 Eyl 2026):** Eskiden tek kaynak port
> vardı (30105). Kapanan soket 60 sn TIME_WAIT'te kalıyor ve bu çekirdekte
> `tcp_tw_reuse = 2` (yeniden kullanım yalnızca loopback'te). Kanal değişimi
> her seferinde giriş sunucusundan (30001) geçtiği için 60 sn içindeki ikinci
> değişim aynı bağlantı dörtlüsüne çarpıp "bağlantı hatası" veriyordu. Havuzla
> her bağlantı sıradaki porttan çıkar; biri meşgulse bir sonrakine geçilir.
> Aralık istemcinin geçici portlarıyla (32768–60999) çakışmaz.

> **Not — xt_owner:** İlk tasarım `-m owner ! --uid-owner` ile muafiyet
> yapıyordu, ama bu emülatörün çekirdeğinde `xt_owner` modülü yok
> (`Couldn't find match 'owner'`). Sabit kaynak port yöntemi hiç modül
> gerektirmez; bu cihazda test edilip çalıştığı doğrulandı.

Enjeksiyon = zaten açık olan yukarı akışa `write()`. Aradaki tüm bağlam
(handshake, login, karakter) gerçek istemci tarafından kurulmuş olur.

### Neden bu yol seçildi

| Yol | Durum |
|---|---|
| Native enjeksiyon (`libgfxcore.so` gibi) | En sağlam ama root + native hook + oyun güncellemesinde kırılan bellek ofseti. Ayrıca analiz edilen botun tasarımını kopyalar. |
| **Şeffaf proxy (seçildi)** | Java'da kalır, mevcut altyapıyı (root, ayrıştırıcı) kullanır, oyun güncellemesinden etkilenmez. 1. aşaması zaten çözülmemiş opcode gövdelerini temiz akışta çözmeyi sağlar. |
| Kendi oturumunu açmak | Başsız istemci yazmak demek; hesaba çift giriş. Pratik değil. |

## İki aşama

**1. Aşama — sadece aktar ve çöz (varsayılan).**
`ProxyServisi.ENJEKSIYON_ACIK = false`. Proxy trafiği aktarır, çözer, loglar
ama **hiçbir şey enjekte etmez**. Oyun proxy üzerinden normal oynanıyorsa
taşıma doğrulanmış olur. Ayrıca yön ayrımı yapılmış, sırayla, eksiksiz akış
elde edilir — tcpdump'ın parçalı segmentlerinden çok daha temiz. `0x1A / 0x1D /
0x32 / 0x34` gibi gövdesi çözülmemiş opcode'ları çözmek için doğru yer.

**2. Aşama — enjeksiyon.**
Panelden "Enjeksiyon aç/kapat". `enjekte()` baytları doğrulanmış akışa yazar.

## Adım adım test

1. Emülatörde root + iptables gerekir (MuMu genelde root'lu gelir).
2. Uygulamada **Proxy — aç/kapat** → aç. Bildirimde "hazır" görünmeli.
   - Kural yazılamazsa: root yok demektir (su reddedilmiş).
3. **Oyunu yeniden bağla** (karakteri çık-gir veya kanal değiştir) ki bağlantı
   proxy kuralı yazıldıktan sonra kurulsun.
4. Oyunda **birkaç adım yürü.** Bu iki işi yapar:
   - Proxy'nin senin konumunu ve yönünü öğrenmesini sağlar (panelde "konum" dolar).
   - `0x07` tik sayacının son değerini yakalar (`tahminiTik()` bunu ileri taşır).
5. **Enjeksiyon — aç.**
6. **İleri yürü**'ye bas. Karakter bakılan yönde ~2 m ilerideki noktaya doğru
   hareket etmeli.

## Doğrulama / sorun giderme

- **1. aşama testi:** enjeksiyon KAPALIYKEN oyunu proxy üzerinden oyna. Karakter
  normal oynanıyorsa proxy şeffaf çalışıyor demektir. Panelde giden/gelen
  sayaçları artmalı.
- "İleri yürü" **"oyun bağlantısı proxy'den geçmiyor"** diyorsa: 3. adımı
  atladın; oyunu proxy açıkken yeniden bağla.
- "İleri yürü" **"konum bilinmiyor"** diyorsa: 4. adımı yap, önce birkaç adım yürü.
- Karakter kıpırdamıyor ama "gönderildi" diyorsa: paket formatı yanlış olabilir.
  1. aşamada gerçek istemcinin `0x07` baytlarını yakala, `Paket.hareket()` ile
  karşılaştır (özellikle **tik** alanı ve **Y işareti** — ham Y normalde negatif).

## Değişen / eklenen dosyalar

| Dosya | Ne |
|---|---|
| `Paket.java` (yeni) | Düzeltilmiş paket kurucular. Taşıma içermez. |
| `ProxyServisi.java` (yeni) | Şeffaf proxy + `enjekte()`. |
| `BasitGonderici.java` (silindi) | Yanıltıcı yeni-soket göndericisi. |
| `MainActivity.java` | Test butonları proxy/enjeksiyon akışına bağlandı. |
| `AndroidManifest.xml` | `ProxyServisi` kaydı. |

## Düzeltilen paket hataları (`Paket.java`)

| Metot | Eski hata → düzeltme |
|---|---|
| `satis()` | `allocate(9)` iken 13 bayt yazıyordu → her çağrıda `BufferOverflowException`. 13'e çıkarıldı. |
| `yetenek()` | Alan sırası ters (`34 \| vid \| slot`). Doğrusu `34 \| slot \| hedefVid`. |
| `tikla()` | vnum (tür no) alıyordu; `0x1A` **vid** (örnek kimliği) ister. `npcVidBul()` ile çevriliyor. |
| `hareket()` tik | `System.currentTimeMillis()` (epoch) yerine istemci uptime sayacı — `ProxyServisi.tahminiTik()`. |

> Not: `docs/PAKET_AKISI.md`'de `0x1A/0x1D/0x32/0x34` için "gövde çözülmedi"
> yazıyor. Bu builder'lar Metin2 ailesi başlık numaralarına dayanan makul
> tahminler; canlı doğrulama 1. aşamada yapılmalı. `hareket`, `hedefle`,
> `saldir` canlı doğrulanmış kabul ediliyor.
