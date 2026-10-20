# İstemci Ölçümü — enjekte ettiğimiz seçim istemciye ulaşıyor mu?

**6 Eylül 2026.** Aylardır dolaylı yoldan tahmin ettiğimiz soru doğrudan
ölçüldü. Araç: [`frida/okuma_modu.py`](../frida/okuma_modu.py).

## Soru

Bot `0x3D` (hedef seç) paketini **giden** akışa enjekte ediyor. Paket
sunucuya gidiyor — bu kesin. Peki **istemcinin kendi seçili hedefi**
değişiyor mu?

Bu önemliydi çünkü saldırı düğmesi istemcinin **kendi** seçtiğine vuruyor.
İstemci bizim seçtiğimizi seçmiyorsa düğmeye basmanın anlamı yok.

`konum.hedef` alanına bakmak **kanıt değildi**: o değer bizim enjekte
ettiğimiz paketten de doluyor, çünkü ayrıştırıcı proxy'den geçen her şeyi
görüyor. Kendi gönderdiğimizi geri okuyup "oldu" demiş oluyorduk.

## Yöntem

Emülatör oyunu Houdini ile ARM64'ten çeviriyor; Frida bu süreçte x86_64
olarak çalıştığı için istemcinin fonksiyonlarını **çağıramıyoruz**. Ama
belleği **okuyabiliyoruz**. Ölçüm buna dayanıyor.

1. Oyunda bir hedefe dokunuldu, istemcinin seçtiği vid proxy'den okundu.
2. O sayı süreç belleğinde arandı → **139 aday adres** (1.2 GB, 1.6 sn).
3. Başka bir hedefe dokunuldu, aday listesi yeni değere göre daraltıldı →
   **1 adres**: `0x7e1845f5b840`.
4. Dump'tan biliyoruz: `ClientPlayer.m_dwTargetVID` sınıfın `0x174`
   ofsetinde. Nesne tabanı `0x7e1845f5b6cc`.

## Sonuç

Oyuna **hiç dokunmadan** `0x3D` enjekte edildi ve o adres okundu:

```
enjeksiyondan ÖNCE : 0
enjeksiyondan SONRA: 5725797        <- enjekte ettiğimiz vid
```

**İstemcinin kendi hedefi değişiyor.** Yol: paket sunucuya gidiyor, sunucu
istemciye hedef paketi yolluyor, istemci onu işleyip kendi alanını
dolduruyor.

### Gecikme

6 farklı hedefle tekrarlandı, alan 20 ms aralıkla yoklandı:

| hedef | gecikme |
|---|---|
| Siyah Rüzgar Okçusu | 125 ms |
| Kötü Siy. Fırtına Okçusu | 123 ms |
| Siyah Rüzgar Okçusu | 104 ms |
| Siyah Rüzgar Delisi | 150 ms |
| Siyah Rüzgar Okçusu | 101 ms |
| Kötü Siy. Fırtına Okçusu | 94 ms |

**6/6 tuttu. En düşük 94, ortanca 123, en yüksek 150 ms.**

## Koda etkisi

Bu ölçüm bir hatayı ortaya çıkardı: `_metin_secip_dugmeye_bas` seçim
paketini gönderip **hemen** düğmeye basıyordu. İlk basış istemci hedefi
almadan düşüyor, yani o an ne seçiliyse ona vuruyordu. Sahada "seçtiğimiz
metine vurmuyor" olarak görülen şey buydu.

`Motor.SECIM_GECIKMESI = 0.25` eklendi — ölçülen en yüksek gecikmenin
üstünde, pay bırakılmış.

## Neden Frida'yı ileri götüremiyoruz

APK yalnızca `lib/arm64` yerli kütüphanelerini içeriyor. x86_64
emülatörde oyun Houdini çeviri katmanıyla çalışıyor:

- `libil2cpp.so` Frida'nın modül listesinde görünmüyor (Houdini kendi
  yükleyicisini kullanıyor). `/proc/<pid>/maps` içinde duruyor.
- Adresi bilinse bile **çağrılamaz**: Frida bu süreçte `x64`, oradaki kod
  ARM64.

İstemcinin kendi fonksiyonlarını çağırma yolu
([`frida/istemci_kopru.py`](../frida/istemci_kopru.py)) yazıldı ve hazır
duruyor — **root'lu gerçek bir ARM64 telefonda** çalışır. O yolda
`ClientPlayer.SetTarget()` doğrudan çağrılabildiği için sunucu turu da,
bu 123 ms de ortadan kalkar.

## Araçlar

| dosya | ne yapar |
|---|---|
| `frida/okuma_modu.py` | Bellek taraması + daraltma + enjeksiyon deneyi |
| `frida/istemci_kopru.py` | İstemcinin kendi fonksiyonlarını çağırır (ARM64 cihaz gerekir) |
| `frida/FRIDA_BASLAT.bat` | frida-server'ı cihaza kurar ve başlatır |

`okuma_modu.py` adresi bir kez bulduktan sonra `--adres 0x...` ile
daraltmayı atlayabilirsin; IL2CPP'nin Boehm çöp toplayıcısı nesneleri
taşımadığı için adres oturum boyunca sabit kalıyor.

**Dikkat:** frida-server root ister ve `adb root` çalıştırınca adbd
yeniden başlar, `adb forward tcp:30200` yönlendirmesi düşer. Panel
"TimeoutError" verirse yönlendirmeyi geri kur.

---

# Saldırı Menzili — WH neden çalışmıyor

**6 Eylül 2026.** Araç: [`tools/wh_teshis.py`](../tools/wh_teshis.py) ve
mesafe-başına isabet dağılımı.

## Ölçüm

Hareket paketi **olmadan**, bulunduğumuz yerden çevredeki canavarlara
vuruldu. Her vuruştan hemen önceki mesafe kaydedildi, sonra canın düşüp
düşmediğine bakıldı. **756 örnek.**

| mesafe | isabet | ıska | oran |
|---|---|---|---|
| 0 m | 4 | 0 | %100 |
| 1 m | 43 | 1 | %98 |
| 2 m | 42 | 17 | %71 |
| 3 m | 9 | 1 | %90 |
| 4 m | 2 | 0 | %100 |
| 5 m ve ötesi | 0 | 700+ | %0 |

**Sunucunun saldırı menzili 4 m.** Ötesinde tek bir vuruş bile işlemedi.

## Kontrol

Ölçümün gerçekten bir şey ölçtüğü ayrıca doğrulandı: 1 m'deki bir
canavara vurulunca can `61 → 42 → 22 → 3 → ölü` sırasıyla düştü. Yani
düzenek sağlam, sorun mesafede.

## Bir ölçüm hatası (ve düzeltilmesi)

İlk denemede ölçüt "canın **bilinir olması**" idi ve dört hedefte de
"İSABET" çıktı. Yanlıştı: hedefi seçince sunucu zaten canı bildiriyor,
can %100'de duruyordu. Tek geçerli kanıt canın **düşmesi**. Ölçüt
düzeltilince tablo tersine döndü.

## Sonuç

Wait-hack'in bütün fikri "uzaktakine yerinden kımıldamadan vurmak".
Bu sunucuda iki ayrı duvar var:

1. Sunucu ışınlamıyor — hareketi kabul edip yürüterek götürüyor.
2. Saldırı menzili 4 m — uzaktan vuruş hiçbir koşulda işlemiyor.

`menzil` ayarını 400 hamın (4 m) üstüne çıkarmak yalnızca boşa paket
gönderir. Kod varsayılanı **2500** (25 m), yani ölçülenin altı katı.
