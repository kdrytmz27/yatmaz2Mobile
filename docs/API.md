# R2 Panel HTTP API

APK içindeki `ApiSunucu` (`:30200`) telefondaki paneli dışarıya açar.
Masaüstü paneli (`r2_masaustu.py`) yalnızca bu uçları kullanır — cihaza
başka hiçbir bağımlılık yoktur.

---

## 1. Ne zaman açık

Sunucu, aşağıdakilerden **herhangi biri** çalışırken ayakta:

| Başlatan | Ne zaman |
|---|---|
| `MainActivity` | uygulama açılınca |
| `OverlayServisi` | panel açılınca |
| `PaketServisi` | paket okuyucu açılınca |
| `ProxyServisi` | proxy açılınca |

Hepsi kapanınca port bırakılır. Eskiden sunucu yalnızca `ProxyServisi`
içinde yaşıyordu; artık bağımsız, yani proxy olmadan da radar/durum okunur.

APK'nın Durum ekranında `API: 192.168.x.x:30200` satırı erişim adresini verir.

## 2. Bağlanma

**USB / emülatör (önerilen).** Trafik cihazdan çıkmaz:

```
adb forward tcp:30200 tcp:30200
curl http://127.0.0.1:30200/api/durum
```

**Aynı Wi-Fi ağı.** Telefonun IP'siyle doğrudan:

```
curl http://192.168.1.42:30200/api/durum
```

## 3. Güvenlik

Sunucu `0.0.0.0`'a bağlanır. `ApiSunucu.TOKEN` **boşsa kimlik doğrulama
yoktur** — aynı ağdaki herkes `/api/enjekte` çağırabilir. Açık Wi-Fi'da
kullanacaksan `ApiSunucu.java` içinde doldur:

```java
public static volatile String TOKEN = "gizli-bir-dize";
```

Doldurulunca her istek `?t=gizli-bir-dize` ya da `X-R2-Token` başlığı ister;
eşleşmezse **401** döner. Masaüstü panelindeki "Token" alanına aynısını yaz.

Yalnızca `adb forward` ile çalışacaksan token gerekmez; forward yalnızca
localhost'u açar.

Tüm yanıtlar `application/json; charset=utf-8` ve `Access-Control-Allow-Origin: *`.

---

## 4. Okuma uçları

### `GET /api/durum`
Tek çağrıda panelin tamamı.

```json
{
  "ok": true, "surum": "0.2.0", "zaman": 1756300000000,
  "servisler": {"panel": true, "paket": true, "kuyruk": false, "proxy": true},
  "proxy": {"acik": true, "durum": "bağlantı kuruldu :30004", "bagli": true,
            "enjeksiyon": false, "giden": 812, "gelen": 4410, "enjekte": 0},
  "konum":  {"bilinir": true, "x": 985412, "y": -270155,
             "mx": 9854.12, "my": 2701.55, "yon": 90, "hedef": 0},
  "sayac":  {"toplam": 5222, "giden": 812, "gelen": 4410},
  "varlik": {"toplam": 41, "canavar": 22, "metin": 3, "npc": 5, "isimsiz": 11},
  "katalog":{"hazir": true, "varlik": 2857, "esya": 28655},
  "kuyruk": {"servis": false, "calisiyor": false, "duraklatildi": false,
             "aralik": 350, "bekleyen": 0,
             "kanal": "Log (kuru çalışma)", "kanalHazir": true, "aktif": ""},
  "rota":   {"ad": "rota", "boyut": 6, "indeks": 2,
             "durum": "nokta 3/6 — 14 m", "calisiyor": true, "dongusel": true},
  "tik": 123456789
}
```

### `GET /api/konum`
Eski biçim korunur; `mx`, `my`, `bilinir`, `hedef` eklendi.

### `GET /api/varliklar?n=30`
Dizi döner. Eski alanlar (`vid`, `x`, `y`, `vnum`, `tip`) aynı; eklenenler:
`ad`, `tipAd`, `mx`, `my`, `mesafe` (metre), `can` (yüzde, bilinmiyorsa `-1`).
`n` en fazla 500.

### `GET /api/esyalar?n=60`
Yerde duran eşyalar, yakından uzağa sıralı.
Alanlar: `vid`, `vnum`, `ad`, `yang` (true ise para yığını), `x`, `y`,
`mx`, `my`, `mesafe`, `sahip` (alma hakkı olan oyuncu; boş olabilir).

> Kaynak paketler: `0x1A` ekle (21 bayt), `0x1B` kaldır (5 bayt),
> `0x1F` sahip (30 bayt). Bkz. docs/PROTOKOL_OFSET.md.

### `GET /api/tik`
`{"tik": 123456789}` — istemcinin uptime sayacının anlık tahmini.

### `GET /api/log?n=40`
Son paketler. `PaketServisi` ve `ProxyServisi` artık **aynı halkayı** besler,
yani proxy tek başına çalışırken de dolu gelir.
Alanlar: `giden`, `boy`, `opcode`, `cozum`, `hex`, `zaman`, `basli`.

### `GET /api/gunluk`
Paket başına logcat yazımını açar/kapatır. **Varsayılan kapalı.**

```
/api/gunluk?paket=1&hex=1   → aç (hata ayıklama)
/api/gunluk?paket=0         → kapat
/api/gunluk                 → durumu oku
```

> ⚠️ Açık bırakmayın. Her pakette `Log.d` çağrısı bir sistem çağrısıdır ve
> hex ile birlikte paket başına ~1.5 KB metin üretir. Saniyede yüzlerce
> pakette bu, pcap okuyucuyu yavaşlatır, tcpdump'ın çekirdek tamponu taşar
> ve akışta delik oluşur — doğuş/ölüm paketleri kaçar.

### `GET /api/kuyruk?n=20`
`bekleyen` ve `gecmis` listeleri, kanal adı, aralık.

### `GET /api/rotalar`
Tüm rotalar, noktalarıyla; `aktif` alanı aktif rotanın adı.

---

## 5. Yazma uçları

Hepsi `GET` ile de çağrılabilir (parametreler sorgu dizesinde);
`/api/enjekte` ayrıca `POST` gövdesi kabul eder.

| Uç | Parametre | Ne yapar |
|---|---|---|
| `/api/enjekte` | gövde ya da `hex=` | Ham baytları doğrulanmış akışa yazar |
| `/api/enjeksiyon` | `ac=1\|0` | Enjeksiyon bayrağı; parametresiz çağrı sadece okur |
| `/api/kanal` | `ad=log\|proxy` | Kuyruğun çıkış kanalı |
| `/api/komut` | `tip=` + alanlar | Kuyruğa komut ekler |
| `/api/kuyruk/ayar` | `duraklat=`, `aralik=`, `temizle=1` | Kuyruk ayarı |
| `/api/servis` | `ad=panel\|paket\|proxy\|kuyruk`, `ac=1\|0` | Servis aç/kapat |
| `/api/rota/yeni` | `ad=` | Yeni rota, aktif yapar |
| `/api/rota/aktif` | `ad=`, `dongusel=` | Aktif rotayı değiştirir |
| `/api/rota/nokta` | `x=`, `y=`, `bekle=`, `yaricap=`, `etiket=` | Nokta ekler; x/y yoksa oyuncunun konumu |
| `/api/rota/sil` | `i=` (nokta) ya da `ad=` (rota) | Siler |
| `/api/rota/bosalt` | — | Aktif rotanın noktalarını siler |
| `/api/rota/takip` | `ac=1\|0` | Rota yürütücüsünü başlatır/durdurur |

`/api/komut` tipleri:

```
tip=yuru    &x=985412&y=-270155   [&tekil=1]
tip=hedefle &id=9428902
tip=saldir  &id=9428902            (id=0 → mevcut hedef)
tip=yetenek &slot=1
tip=topla   &id=9428902
tip=bekle   &ms=1000
```

`tekil=1` aynı tipteki bekleyen komutları iptal edip bunu koyar — yeni
yürüme hedefi verirken kullanılır.

Başarı `{"ok":true, ...}`, hata `{"ok":false,"hata":"..."}` döner.

---

## 6. Hiçbir şey kazara gönderilmez

Bir komutun oyuna ulaşması için **üç ayrı anahtar** açık olmalı:

1. `ProxyServisi` açık ve oyun bağlantısı proxy'den geçiyor,
2. `ENJEKSIYON_ACIK` = true (`/api/enjeksiyon?ac=1`),
3. kuyruk kanalı `ProxyKanali` (`/api/kanal?ad=proxy`).

Varsayılan üçünde de kapalı/kuru. Kanal `LogKanali` iken kuyruk yalnızca
kaydeder; enjeksiyon kapalıyken `enjekte()` baytları loglar ve
`"enjeksiyon kapalı (kuru çalışma)"` döndürür.

---

## 7. Örnekler

```bash
# durum
curl -s http://127.0.0.1:30200/api/durum | python -m json.tool

# 20 en yakın varlık
curl -s "http://127.0.0.1:30200/api/varliklar?n=20"

# paket okuyucuyu aç
curl -s "http://127.0.0.1:30200/api/servis?ad=paket&ac=1"

# bir noktaya yürü (kanal proxy + enjeksiyon açıkken gerçekten yürür)
curl -s "http://127.0.0.1:30200/api/kanal?ad=proxy"
curl -s "http://127.0.0.1:30200/api/enjeksiyon?ac=1"
curl -s "http://127.0.0.1:30200/api/komut?tip=yuru&x=985412&y=-270155&tekil=1"

# ham paket
curl -s -X POST --data "07 01 00 00 44 09 0F 00 B5 E0 FB FF 15 CD 5B 07" \
     http://127.0.0.1:30200/api/enjekte
```
