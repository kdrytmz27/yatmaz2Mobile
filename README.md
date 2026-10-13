# yatmaz2Mobile

Metin2 Android/MuMu geliştirme kaynaklarının 13 Ekim 2026 tarihli çalışma kopyası.

## Klasörler

- `client/r10dev.net OPENGL-ITJA/android`: Android Java uygulaması, Gradle yapılandırması ve yerel test profilleri.
- `client/r10dev.net OPENGL-ITJA/clientsource`: C++ oyun istemcisi; Android slot çizimi ve Windows derleme düzeltmeleri dahil.
- `client/r10dev.net OPENGL-ITJA/server`: Android üzerinde gömülü sunucuyu derleyen adaptör.
- `server-source`: m2dev sunucu C++ kaynakları.
- `client-python`: çalışan istemcideki Python 2 UI modülleri ve UIScript ekranları.
- `client/r10dev.net OPENGL-ITJA/tools/data-overlay/modern-ui`: son UI değişikliklerinin oyun verilerine uygulanacak kopyaları.
- `local-tools`: önceki Windows çalışma alanındaki veri hazırlama/paketleme yardımcıları. Yolları eski çalışma düzenine bağlıdır; yeni ortam için uyarlamak gerekir.
- `handoff`: tasarım kapsamı ve test notları.

## Son uygulanan değişiklikler

Dairesel mobil savaş tuşları, portreli HP/MP paneli, koyu metal paneller, bordo başlıklar, envanter ve menü teması. Raise State alt solda, joystick alanının sağındadır. MuMu x86_64 üzerinde build 5 kurulup menü ve envanter sayfa geçişleri kontrol edildi. Giriş ve karakter seçimi ekranlarının yeniden tasarımı henüz tamamlanmadı.

UI değişikliği yaparken `client-python` ile `modern-ui` kopyalarını birlikte güncelleyin. `modernui.py` ortak tema; `uimobilehud.py` mobil kontroller; `uiInventory.py` ve `uiscript/inventorywindow.py` envanter içindir. Python 2 uyumluluğunu ve eski dosyaların karakter kodlamasını koruyun.

## Derleme

JDK 17, Gradle 8.1.1, Android SDK 33, Build Tools 33.0.1, NDK 25.2.9519653 ve CMake 3.22.1 kullanılan sürümlerdir. Android klasörüne yerel SDK yolunu belirten `local.properties` oluşturun. Önce Android altındaki README ve Gradle yapılandırmasını inceleyin.

Örnek (Gradle PATH üzerinde):

```powershell
gradle -p 'client/r10dev.net OPENGL-ITJA/android' assembleDebug -Pm2profile=local-mumu -Pm2build=5 '-Pm2serverSrc=<server-source mutlak yolu>' '-Pm2dataAssets=<m2data.zip bulunan klasör>'
```

Bu depo **kaynak kod devri** içindir: APK, SDK/toolchain, derleme önbellekleri, oyun grafik/ses/veri paketleri, çalışma veritabanı ve otomatik giriş bilgileri dahil değildir. Bu nedenle tek başına klonlamak çalışır oyun verisi sağlamaz. `local-mumu` profili ayrıca hazırlanmış `m2data.zip` gerektirir. Önceki bilgisayardaki veriler `work/m2stage` ve `work/bundle-assets` klasörlerindedir. Bazı eski Windows hedefleri için gereken derlenmiş üçüncü taraf kütüphaneler de dahil edilmemiştir.

## Kaynak kökenleri

Bu depo sıfırdan yazılmış bağımsız bir oyun motoru değildir. Çalışma kaynakları:

- https://github.com/cemreefe/metin2-android — `b6e28e41134fb9b793e5098ba3efbc0af71dc5f4`
- https://github.com/d1str4ught/m2dev-server-src — `66068c1` (kısa commit)
- https://github.com/cemreefe/OpenGr2ndma — `210f5c326531297495c24e7bb1e24dc1b1a77833`

Upstream kaynakların mevcut bildirim ve lisans dosyaları korunur. Bu çalışma kopyası için ek bir lisans verilmemiştir. OpenGr2ndma kaynakları bu kopyada normal klasör olarak bulunur; altındaki eski `.gitmodules` dosyası kaynak kökenini belgelemektedir.
