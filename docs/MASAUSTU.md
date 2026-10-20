# Masaüstü Kontrol Paneli (`r2_masaustu.py`)

Telefondaki paneli PC'den yönetir. `r2_masaustu.py` yalnızca Python standart
kütüphanesini kullanır — `pip install` gerekmez, frida gerekmez.

```
python r2_masaustu.py
```

Eski `romia2_panel.py` frida ile oyun sürecine bağlanıyordu; bu panel APK'nın
kendi HTTP API'sine bağlanır. İkisi birbirinin yerine geçmez, yan yana durur.

---

## Bağlanma

1. Telefonda/emülatörde **R2 Panel uygulamasını aç.** API uygulama açılır
   açılmaz başlar.
2. PC'de **"adb forward"** düğmesine bas (arka planda
   `adb forward tcp:30200 tcp:30200` çalışır), sonra **Bağlan**.
   * `adb` PATH'te değilse `ADB_YOLU` ortam değişkenini tam yola ayarla:
     `set ADB_YOLU=C:\...\platform-tools\adb.exe`
3. Alternatif: aynı Wi-Fi ağındaysan adres alanına telefonun IP'sini yaz
   (APK'nın Durum ekranında `API: 192.168.x.x:30200` yazar).

Sağ üstteki nokta bağlantı durumunu gösterir; hata varsa nedeni yazar.

---

## Ekran

**Sol — radar.** Oyuncu merkezde, mesafe halkaları metre. Fare tekerleği
yakınlaştırır. Üstteki üç mod tıklamanın ne yapacağını belirler:

| Mod | Haritaya tıklayınca |
|---|---|
| **Bak** | koordinatı konsola yazar, hiçbir şey göndermez |
| **Git** | kuyruğa tekil YÜRÜ komutu koyar |
| **Rota ekle** | aktif rotaya nokta ekler (rota yoksa açar) |

**Sağ — sekmeler.**

| Sekme | İçerik |
|---|---|
| **Durum** | konum, sayaçlar, proxy, katalog, kuyruk, rota; servis ve gönderim düğmeleri |
| **Varlıklar** | en yakın varlıklar; seçip hedefle / saldır / yanına git / rotaya ekle |
| **Rota** | rota seç, nokta ekle/sil, boşalt, takibi başlat |
| **Kuyruk** | bekleyenler ve son yürütülenler; duraklat, boşalt, aralık |
| **Paket** | canlı paket akışı (kutucuğu işaretle), istersen hex |
| **Konsol** | ham hex enjeksiyonu + günlük |

Rota değişiklikleri iki yönlü görünür: masaüstünden eklenen nokta telefondaki
panelde de belirir (`RotaDeposu` sürüm takibi sayesinde), telefondan eklenen
de burada.

---

## Gönderim zinciri

Bir komutun gerçekten oyuna gitmesi için üç anahtar açık olmalı:

```
1) Proxy açık ve oyun bağlantısı proxy'den geçiyor   → Durum sekmesi, "Proxy"
2) Enjeksiyon açık                                    → "Enjeksiyon aç/kapat"
3) Kuyruk kanalı = Proxy                              → "Kanal: Log ⇄ Proxy"
```

Üçü de varsayılan olarak kapalıdır. Üst şeritte sürekli `ENJEKSİYON AÇIK` /
`enjeksiyon kapalı` ve geçerli kanal yazar.

Sıra önemli: proxy'yi **oyun bağlanmadan önce** aç, sonra oyunu yeniden bağla,
sonra oyunda birkaç adım yürü (konum ve tik sayacı öğrenilsin), ancak ondan
sonra enjeksiyonu aç. Ayrıntı: `docs/HAREKET_GONDERME.md`.

**Dur paketi** düğmesi (Konsol sekmesi) bulunduğun konumda `state=0` bir 0x07
üretir — karakter kaçarsa sabitlemek için.

---

## Sorun giderme

| Belirti | Sebep |
|---|---|
| `● hata: URLError` | API kapalı ya da forward yok. Uygulamayı aç, "adb forward"a bas. |
| `● hata: HTTP 401` | `ApiSunucu.TOKEN` dolu; Token alanına aynısını yaz. |
| Konum "bilinmiyor" | Paket okuyucu ya da proxy kapalı; ya da oyunda hiç yürümedin. |
| Komut "kanal hazır değil" | Kanal Proxy ama proxy bağlı değil. |
| Karakter kıpırdamıyor | Enjeksiyon kapalı, ya da paket formatı reddedildi — Paket sekmesinde `GERCEK 07` ile `BIZIM 07` satırlarını karşılaştır. |
| Karakter geri sekiyor | Beklenen sınır: istemcinin kendi belleğindeki konum değişmiyor. Bkz. `ProxyKanali` sınıf açıklaması. |
