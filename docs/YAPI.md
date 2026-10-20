# Proje Yapısı

`C:\Users\Abdulkadir\romia2BOT` — R2 Panel. 29 Java dosyası (~3.500 satır),
4 PC scripti, 1 Python çözümleyici, 4 doküman.

---

## Ağaç

```
romia2BOT/
├── BUILD.bat                    APK derle
├── PC_LOG.bat                   canlı trafik logu  (OUT + IN + varlık)
├── PC_VARLIK.bat                sadece tanınan canavar / metin / NPC
├── PC_CAPTURE.bat               N saniye pcap yakala → indir → çözümle
├── adb_bul.bat                  adb.exe'yi otomatik bulur (diğer üçü çağırır)
│
├── .gitignore                   build / log / local.properties haric tutulur
│
├── build.gradle.kts             AGP 9.0.1
├── settings.gradle.kts          modül tanımı
├── gradle.properties            AndroidX kapalı, UTF-8
├── local.properties             Android SDK yolu (paylaşılmaz)
├── gradlew / gradlew.bat        Gradle 9.1 sarmalayıcı
├── gradle/wrapper/              sarmalayıcı jar + ayarları
│
├── docs/
│   ├── NASIL_CALISIYOR.md       tcpdump'tan bayta tüm zincir  (722 satır)
│   ├── PAKET_AKISI.md           opcode tablosu, filtreler, bulgular (358)
│   ├── TEST.md                  adım adım test + sorun giderme (271)
│   └── YAPI.md                  bu dosya
│
├── tools/
│   └── analiz.py                pcap çözümleyici, PC tarafı (206 satır)
│
├── log/                         yakalamalar ve loglar (git'e girmez)
│   ├── ornek_bekleme.pcap       karakter dururken — 0x03 var, doğuş yok
│   └── ornek_hareket.pcap       hareket hâlinde
│
└── app/
    ├── build.gradle.kts         minSdk 26, compileSdk 36, Java 17
    └── src/main/
        ├── AndroidManifest.xml  3 servis + 1 aktivite, izinler
        │
        ├── assets/
        │   ├── entities_tr.txt     2.857 satır  vnum⇥tip⇥rank⇥seviye⇥ad
        │   ├── metins_tr.txt         195 satır  vnum⇥ad
        │   └── items_tr.txt       28.655 satır  vnum⇥ad
        │
        ├── res/
        │   ├── values/styles.xml            koyu tema
        │   └── xml/network_security_config  yalnız 127.0.0.1 cleartext
        │
        └── java/com/abdulkadir/r2panel/     29 dosya
```

---

## Java katmanları

Dosyalar beş katmana ayrılıyor. Ok yönü bağımlılığı gösterir; **hiçbir alt
katman üst katmanı tanımaz**.

```
  ARAYÜZ      MainActivity · OverlayServisi · *Sekmesi · HaritaView · PanelStil
                                    │
  MANTIK      KomutKuyrugu · RotaYurutucu · KomutKanali/LogKanali
                                    │
  MODEL       DunyaDurumu · Varlik · Rota · Nokta · Komut · RotaDeposu
                                    │
  AĞ          PaketServisi · PaketAyristirici · PaketKaydi · TrafikLog
                                    │
  ALTYAPI     Koordinat · OyunKatalogu · KatalogKaydi · Bildirim · Sekme
```

### Ağ katmanı — baytların girdiği yer

| Dosya | Satır | Görevi |
|---|---|---|
| `PaketServisi.java` | 267 | Foreground servis. root tcpdump'ı başlatır, pcap borusunu okur, IPv4/TCP başlıklarını ayrıştırır, yönü belirler. **Hiçbir şey göndermez.** |
| `PaketAyristirici.java` | 213 | Yükü anlama çevirir. İki yol: `mesajCoz()` sınırı bilinen tek mesaj için, `akisiTara()` biriken akışta imza araması için. Bayt okuma temelleri (`u8`, `u16be`, `i32le`, `f32le`) burada. |
| `PaketKaydi.java` | 66 | Panelde ve logda görünen tek satır: saat, yön, adres, opcode, boy, hex, çözüm. |
| `TrafikLog.java` | 83 | PC'den `adb logcat` ile izlenen günlük. `R2_OUT`, `R2_IN`, `R2_VARLIK` etiketleri. |

### Model katmanı — durum ve kalıcılık

| Dosya | Satır | Görevi |
|---|---|---|
| `DunyaDurumu.java` | 180 | Süreç içi **tek gerçek**. Konum, varlık listesi, sayaçlar. Paket okuyucu yazar, panel okur; tüm erişim kilitli. 60 sn görülmeyen varlığı düşürür. |
| `Varlik.java` | 103 | Tek varlık: id, vnum, tip, konum, can. `etkinTip()` önce kataloğa bakar. CHAR_TYPE sabitleri burada. |
| `Rota.java` | 91 | Sıralı waypoint listesi, döngüsel olabilir. JSON'a çevrilir. |
| `Nokta.java` | 45 | Tek waypoint: ham koordinat, varış yarıçapı, bekleme süresi, etiket. |
| `RotaDeposu.java` | 121 | Rotaların kalıcı deposu. Tümü tek JSON dizisi olarak SharedPreferences'a yazılır. |
| `Komut.java` | 105 | Kuyruğa giren iş birimi: YÜRÜ, HEDEFLE, SALDIR, YETENEK, TOPLA, BEKLE, ROTA_NOKTASI, HAM. |

### Mantık katmanı — karar verme

| Dosya | Satır | Görevi |
|---|---|---|
| `KomutKuyrugu.java` | 210 | Öncelikli kuyruk + tek işçi thread. Eşit öncelikte FIFO. Ayarlanabilir hız sınırı. `tekilEkle()` aynı tipteki eski komutu iptal eder. |
| `RotaYurutucu.java` | 131 | "Şu an hangi noktaya gitmeliyim" kararı. Konumu izler, varış yarıçapına girince bekler, sıradakine geçer. Kendisi paket üretmez. |
| `KomutKanali.java` | 27 | Çıkış katmanının arayüzü. Kuyruk mantığını gönderim mekanizmasından ayırır. |
| `LogKanali.java` | 46 | Varsayılan kanal: **kuru çalışma**. Komutu yalnızca kaydeder, hiçbir yere göndermez. |
| `KuyrukServisi.java` | 63 | Kuyruğu ve rota yürütücüyü panel kapansa da canlı tutan foreground servis. |

### Arayüz katmanı — panel

| Dosya | Satır | Görevi |
|---|---|---|
| `OverlayServisi.java` | 224 | Taşınabilir overlay penceresi. `TYPE_APPLICATION_OVERLAY` + `FLAG_NOT_FOCUSABLE` — panel dışına dokunmalar oyuna gider. Başlıktan sürüklenir, sekmeleri yönetir, 500 ms'de bir tazeler. |
| `HaritaView.java` | 264 | Oyuncu merkezli radar. Izgara, menzil çemberi, tip renkleri, can çubukları, rota çizgileri, isim etiketleri. Dokunmayı dünya koordinatına çevirir. |
| `MainActivity.java` | 131 | Başlatıcı ekran: izin akışı ve servis anahtarları. |
| `PanelStil.java` | 104 | Tüm renkler, ölçüler ve widget fabrikası tek yerde. XML layout yok, her şey kodla kurulur. |
| `Sekme.java` | 10 | Sekme arayüzü: `ad()`, `gorunum()`, `tazele()`. |
| `DurumSekmesi.java` | 121 | Konum, paket sayaçları, servis anahtarları, en yakın **isimli** varlıklar. |
| `HaritaSekmesi.java` | 108 | Harita + zum + dokunma modu (Bak / Rota ekle / Git) + isim aç-kapa. |
| `RotaSekmesi.java` | 228 | Rota editörü. Overlay'de klavye kırılgan olduğu için düzenleme tamamen dokunmayla: dokun = bekleme döngüle, uzun bas = sil. |
| `KuyrukSekmesi.java` | 128 | Kuyruk durumu, bekleyenler, geçmiş, duraklat, aralık. |
| `PaketSekmesi.java` | 109 | Canlı paket logu, OUT/IN/çözülen süzgeçleri, hex dökümü. |

### Altyapı katmanı

| Dosya | Satır | Görevi |
|---|---|---|
| `Koordinat.java` | 54 | Ham ↔ metre dönüşümü ve Y ekseni tersliği. 1 m = 100 birim. Mesafe hesapları. |
| `OyunKatalogu.java` | 173 | vnum → ad/tip/rank/seviye sözlüğü. Üç assets dosyasını arka planda `SparseArray`'e yükler (67-200 ms). |
| `KatalogKaydi.java` | 38 | Katalog satırının çözülmüş hâli. `rankAdi()`, `etiket()`. |
| `Bildirim.java` | 34 | Foreground servis bildirimleri için tek kanal. |

---

## PC tarafı

| Dosya | Ne için |
|---|---|
| `adb_bul.bat` | `R2_ADB` → PATH → Android SDK → MuMu sırasıyla adb arar. Diğer scriptler bunu `call` eder, böylece adb PATH'te olmasa da çalışırlar. |
| `PC_LOG.bat` | Tüm etiketleri ekrana basar **ve** `log/trafik_YYYYAAGG_SSDDss.txt` dosyasına kaydeder. |
| `PC_VARLIK.bat` | Yalnızca `R2_VARLIK` — "şu canavar var, şu metin var" satırları. |
| `PC_CAPTURE.bat` | `PC_CAPTURE.bat 30` → 30 sn pcap yakalar, indirir, `tools/analiz.py` çalıştırır. |
| `tools/analiz.py` | pcap → IN/OUT akışları → mesaj çerçeveleme → çözülemeyen bölge raporu → varlık taraması → katalogla isimlendirme. `--vnum 8005` ile belirli vnum aranabilir. |

Logcat etiketleri: `R2_OUT`, `R2_IN`, `R2_VARLIK`, `R2_PAKET`, `R2_KATALOG`,
`R2_KUYRUK`, `R2_ROTA_YUR`, `R2_KANAL`.

---

## Servisler ve bildirim numaraları

`AndroidManifest.xml` üç foreground servis tanımlar. Hepsi
`foregroundServiceType="specialUse"`; Android 14+ bunu şart koşuyor.

| Servis | Bildirim id | Ne yapar | Bağımsız mı |
|---|---|---|---|
| `OverlayServisi` | 1200 | paneli çizer | evet |
| `PaketServisi` | 1201 | trafiği okur | evet — panel kapalıyken de okur |
| `KuyrukServisi` | 1202 | komut kuyruğu + rota | evet |

Üçü birbirinden bağımsız açılıp kapanır. Yalnızca paket okuyucuyu açıp
PC'den log izleyebilirsiniz; panel gerekmez.

**Servisler kabuktan başlatılamaz** — `am start-foreground-service`
*Requires permission not exported* hatası verir. Uygulamadaki düğmeler
kullanılmalı.

---

## Veri akışı — hangi dosya hangisini besliyor

```
tcpdump (root)
   │
   ▼
PaketServisi ──────► PaketAyristirici ──────► DunyaDurumu
   │                      │                        ▲
   │                      ▼                        │
   │                 OyunKatalogu ◄── assets/*.txt │
   │                      │                        │
   ▼                      ▼                        │
PaketKaydi ─────────► TrafikLog                    │
   │                      │                        │
   ▼                      ▼                        │
PaketSekmesi         adb logcat (PC)               │
                                                   │
RotaDeposu ──► Rota ──► RotaYurutucu ──────────────┤ okur
                            │                      │
                            ▼                      │
                      KomutKuyrugu                 │
                            │                      │
                            ▼                      │
                      KomutKanali                  │
                     (LogKanali = kuru)            │
                                                   │
HaritaView · DurumSekmesi · KuyrukSekmesi ─────────┘ okur
```

Tek yönlü: **ağ yazar, arayüz okur.** Arayüzün `DunyaDurumu`'na yazma
yetkisi yok; bu yüzden panelde yapılan hiçbir işlem oyun durumunu
bozamaz.

---

## Sınır: ne yapmıyor

`KomutKanali` arayüzünün varsayılan uygulaması `LogKanali`'dir — komutu
yalnızca kaydeder. Kuyruk sırası, öncelik, hız sınırı ve rota ilerlemesi
bu hâliyle uçtan uca test edilebilir; **hiçbir paket üretilmez**.

Yürütme katmanı eklenecekse tek yapılacak `KomutKanali`'yi uygulayıp
`KomutKuyrugu.al().kanalAta(...)` demek. Kuyruk, rota, harita ve ağ
katmanlarının hiçbiri değişmez.

`PaketServisi` yalnızca okur: ham sokete yazmaz, oyun sürecine enjeksiyon
yapmaz, sunucuya yapay paket göndermez.

---

## Derleme

```
gradlew.bat assembleDebug
```

Çıktı: `app/build/outputs/apk/debug/app-debug.apk` (~900 KB).
Gereken: JDK 17, Android SDK 36, AGP 9.0.1 / Gradle 9.1.

`app/build/`, `.gradle/`, `log/` ve `local.properties` paylaşılmaz —
sırasıyla derleme çıktısı, önbellek, yakalama verisi ve makineye özgü
SDK yolu.
