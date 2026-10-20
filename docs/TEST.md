# Test Adımları

`ADB` yolu (SDK'nınki MuMu'nunkinden daha güvenilir çalıştı):

```
adb
```

MuMu'nun kendi adb'si (`C:\Program Files\Netease\MuMuPlayer\nx_device\12.0\shell\adb.exe`)
aynı cihazı bazen `offline` görüyor; SDK adb'sini kullan.

### `adb` komutu tanınmıyorsa

Düz cmd penceresinde `adb` yazmak çalışmaz — PATH'te değil:

```
'adb' is not recognized as an internal or external command
```

Üç çözüm var, kolaydan zora:

**1. Hazır script kullan (önerilen).** `PC_LOG.bat`, `PC_VARLIK.bat` ve
`PC_CAPTURE.bat` adb'yi kendileri bulur (`adb_bul.bat`); çift tıklaman yeter.

**2. Tam yolu yaz.** Bu dokümandaki `adb` yerine:

```
"adb" logcat -s R2_VARLIK:D
```

**3. PATH'e kalıcı ekle.** Bir kez çalıştır, sonra **yeni** bir cmd aç:

```
setx PATH "%PATH%;C:\Users\Abdulkadir\AppData\Local\Android\Sdk\platform-tools"
```

`setx` kullanıcı PATH'ini kalıcı değiştirir; açık pencerelerde etkili olmaz,
yeni pencere gerekir.

Başka bir adb kullanmak istersen script'lere şunu söyleyebilirsin:

```
set R2_ADB=C:\yol\adb.exe
```


---

## 0. Ön kontrol — cihaz hazır mı

```
adb devices
adb shell getprop ro.build.version.release
adb shell "su -c id"
adb shell "su -c 'which tcpdump'"
adb shell "su -c 'ip -o addr show'"
```

Beklenen:

| Kontrol | Beklenen | Bu cihazda |
|---|---|---|
| cihaz | `emulator-5554  device` | ✅ |
| Android | 12 | ✅ |
| root | `uid=0(root)` | ✅ |
| tcpdump | `/system/bin/tcpdump` | ✅ |
| arayüz | `wlan0` | ✅ 10.0.2.15 |

`wlan0` yoksa `PaketServisi.ARAYUZ` sabitini oradaki arayüz adıyla değiştir.

---

## 1. Derle ve kur

```
cd C:\Users\Abdulkadir\romia2BOT
gradlew.bat assembleDebug
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

`Success` görmelisin.

## 2. İzinler

Uygulamayı aç, **Ekran üstü izni ver**'e bas ve listeden R2 Panel'i aç.

Kestirme yol (Android 12'de `appops` binary'si yok, `cmd appops` kullan):

```
adb shell cmd appops set com.abdulkadir.r2panel SYSTEM_ALERT_WINDOW allow
adb shell cmd appops get com.abdulkadir.r2panel SYSTEM_ALERT_WINDOW
```

Bildirim izni Android 13+ içindir; 12'de gerekmez (`POST_NOTIFICATIONS`
bu sürümde yok, `pm grant` hata verir — normal).

## 3. Paneli aç

Uygulamada **Panel — aç/kapat**. Doğrulama:

```
adb shell dumpsys activity services com.abdulkadir.r2panel
```

`OverlayServisi ... isForeground=true foregroundId=1200` görmelisin.

> Servisler kabuktan başlatılamaz (`am start-foreground-service` →
> *Requires permission not exported*). Uygulamadaki düğmeyi kullan.

## 4. Paket okuyucuyu başlat

Panelde **Durum** → **Paket okuyucu aç/kapat**. MuMu root izni sorarsa onayla.

```
adb logcat -d -s R2_PAKET:*
```

Beklenen iki satır:

```
R2_PAKET: yakalama komutu: exec tcpdump -i wlan0 -U -s 0 -w - 'tcp and not port 443'
R2_PAKET: pcap açıldı, link=1 başlık=14
```

`link=1` Ethernet demek → 14 baytlık link başlığı. `link=113` çıkarsa 16 bayt
kullanılır; kod ikisini de kendi ayarlar. **Bu satır gelmiyorsa** su reddedilmiş
veya tcpdump yok demektir.

Logcat'te `avc: denied ... permissive=1` satırları görürsün — SELinux izin
veren modda olduğu için engellemez, normaldir.

## 5. Oyunu aç ve doğrula

Romia2'yi başlat, karakterle oyuna gir. Panelin **başlığında** koordinat
belirmeli (örn. `R2 Panel  9895,-2735`).

**Durum** sekmesinde beklenen:

```
toplam 46 • giden 12 • gelen 34
paket: okunuyor — N varlık
```

Sayaçlar artmıyorsa sırayla bak:

| Belirti | Sebep | Çözüm |
|---|---|---|
| `pcap açıldı` yok | su reddedildi | MuMu root iznini ver |
| `pcap açıldı` var, sayaç 0 | sunucu IP değişmiş | §6'daki kontrolü yap |
| sayaç artıyor, konum yok | opcode kaymış | Paket sekmesinden OUT hex'ine bak |

## 6. Sunucu IP'si doğru mu

```
adb shell "su -c 'tcpdump -i wlan0 -c 20 -nn tcp and port 30004'"
```

Çıkan IP `PaketServisi.OYUN_IP` ile aynı olmalı (`185.128.114.87`).
Farklıysa sabiti güncelle ve yeniden derle. **Yön tespiti bu IP'ye bağlıdır** —
yanlışsa hiçbir paket sayılmaz.

## 7. Harita ve rota

1. **Harita** sekmesi → **Rota ekle**.
2. Haritaya 3–4 kez dokun. Noktalar mavi çizgiyle bağlanmalı, numaralanmalı.
3. **Rota** sekmesi → nokta listesi görünmeli, uzunluk metre olarak yazmalı.
4. Bir satıra dokun → `bekle=1 sn` olmalı. Uzun bas → satır silinmeli.
5. **Takibi başlat** → durum satırı `nokta 1/4 — N m` şeklinde ilerlemeli.
6. **Kuyruk** sekmesinde `YÜRÜ ...` komutları geçmişe düşmeli.

Kuyruk boşsa **Kuyruk aç/kapat** ile servisi başlattığından emin ol.

## 8. Paket sekmesi — opcode doğrulama

1. **Paket** sekmesi → **Temizle**.
2. **IN**'i kapat, sadece **OUT** açık kalsın.
3. Oyunda **tek bir adım** yürü.
4. Panele dön. İlk kayıt `op=0x07 len=16+` olmalı ve çözüm satırında
   `hareket state=... yön=...° x,y` yazmalı.

Aynı hareketi 3–4 kez yapıp değişen baytları karşılaştır — sabit kalanlar
opcode/bayrak, değişenler koordinattır. Ayrıntı: [PAKET_AKISI.md](PAKET_AKISI.md) §8.

---

## Temizlik

```
adb shell am force-stop com.abdulkadir.r2panel
adb shell "su -c 'pkill tcpdump'"
adb uninstall com.abdulkadir.r2panel
```

`pkill tcpdump` önemli: servis düzgün kapanmazsa tcpdump arka planda kalabilir.

---

## 9. İsimlendirmeyi test etme ("şu canavar var" satırları)

Bu en çok yanlış anlaşılan kısım, çünkü **yanlış anda başlatırsanız hiç isim
görmezsiniz** ve uygulama bozuk sanılır.

### Neden isim görünmüyor olabilir

İsim zinciri tek yönlü:

```
doğuş paketi  →  vnum  →  entities_tr.txt  →  ad + tip + rank + seviye
0x03 hareket  →  id    →  yalnızca konum,  vnum YOK  →  isim çıkmaz
```

Doğuş paketi bir varlık **görüş alanına ilk girdiğinde** gönderilir. Okuyucuyu
karakter durduğu yerdeyken açarsanız çevredeki canavarlar çoktan doğmuştur;
sunucudan yalnızca `0x03` hareket paketleri akar ve panel şunu yazar:

```
EN YAKIN VARLIKLAR
+ 34 isimsiz (doğuş paketi kaçırıldı)
```

Bu bir hata değil, doğru rapordur.

### Doğru test sırası

1. Oyunu aç, karakterle **oyuna gir**.
2. Paneli aç, **Paket okuyucu**'yu başlat.
3. Şimdi **yürü** — tercihen yeni bir alana veya canavar kalabalığına doğru.
4. PC'de bu pencereyi açık tut:

```
adb logcat -s R2_VARLIK:D
```

Birkaç saniye içinde satırlar akmaya başlar:

```
20:57:34.130  CANAVAR   Alfa Mavi Kurt (Lv9) [piyon]           #9527719 @ 9785,-2977 m  57 m uzakta
20:57:35.137  CANAVAR   Kırmızı Yaban Domuzu (Lv10) [s.piyon]  #9527718 @ 9785,-2974 m  56 m uzakta
20:57:37.165  CANAVAR   Aç Alfa Kurt (Lv4) [piyon]             #9508104 @ 9782,-2967 m  55 m uzakta
```

Aynı anda Durum sekmesindeki `canavar / metin / npc` sayaçları artar,
haritada isim etiketleri belirir.

### Hızlı kontrol tablosu

| Panelde gördüğün | Anlamı | Ne yap |
|---|---|---|
| `+ N isimsiz (doğuş paketi kaçırıldı)` | okuyucu geç başladı | yürü, yeni varlıklar doğsun |
| `katalog: yükleniyor…` | assets henüz okunmadı | 1 sn bekle (normalde 70-200 ms) |
| `canavar 0, metin 0, npc 0` ve isimsiz sayısı büyük | aynı sebep | yürü |
| hiç varlık yok | paket akmıyor | §5'e dön |
| `vnum 12345` (ad yerine) | vnum katalogda yok | `entities_tr.txt`'e ekle |

### Doğuş paketini pcap ile doğrulama

`0x01`'in gerçekten doğuş paketi olduğunu kendi verinle görmek için:

```
PC_CAPTURE.bat 30
```

Sayaç başlayınca **yürü**. Bitince çözümleyici doğuş adaylarını
isimlendirilmiş olarak listeler:

```
--- 0x01 imza taramasi (dogus adayi: id,rot,x,y,vnum) ---
  @1284  CANAVAR  Alfa Mavi Kurt   #9527719   9785,-2977 m
```

Hiç satır çıkmazsa yakalama sırasında yeni varlık doğmamıştır — tekrar dene.
