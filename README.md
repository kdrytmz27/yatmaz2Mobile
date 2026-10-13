# Yatmaz2 Mobile

Metin2 **tarzı** (izometrik/tepeden-açılı, mobil dokunmatik kontrollü) bir aksiyon RPG.
**Sıfırdan, bağımsız ve yasal** olarak Godot 4 ile yazıldı. Metin2'nin hiçbir kodunu,
grafiğini, haritasını veya verisini içermez — sadece aynı türün oynanış hissini hedefler.

> Not: Bu depo `main` dalında ayrıca sızdırılmış Metin2 kaynakları barındırıyor.
> Bu proje (bu dal) onlardan **hiçbir dosya kullanmaz**; telif açısından temiz,
> tamamen senin olan bir temeldir.

## Şu an ne var (oynanabilir prototip)

- Tepeden-açılı takip kamerası (masaüstünde sağ tık sürükle = döndür, tekerlek = zoom)
- Mobil **sanal joystick** (sol alt) + **SALDIR** ve **İKSİR** tuşları (sağ alt)
- Klavye desteği (test için): `WASD` / ok tuşları = hareket, `Boşluk` / `J` = saldırı
- Kırılabilir **Metin Taşları** (vur, kır, ödül al, bir süre sonra yeniden doğar)
- Kovalayan, vuran **canavarlar** (dünya belli sayıda tutar)
- **Can / Mana / XP / Seviye / Altın** sistemi, seviye atladıkça güçlenme
- **Eşya düşme** + **envanter** (Çanta tuşu), İksir ile canlanma
- Havada yükselen **hasar/ödül yazıları**

## Nasıl çalıştırılır

1. [Godot Engine 4.3+](https://godotengine.org/download) (Standart sürüm) indir.
2. Godot'u aç → **Import** → bu klasördeki `project.godot` dosyasını seç.
3. Sağ üstte **Oynat (F5)** tuşuna bas. Masaüstünde fare joystick/tuşları taklit eder.

### Android'e (telefona) kurmak

1. Godot'ta **Editor → Manage Export Templates → Download** ile şablonları indir.
2. Android SDK + JDK 17 kurulu olmalı (Godot dökümanındaki adımlar).
3. **Project → Export → Add → Android**, keystore ayarla, **Export Project** ile `.apk` üret.
4. `.apk`'yı telefona yükle.

## Grafik / asset (sıradaki adım)

Şu an karakter ve nesneler basit geometrik şekiller (placeholder). Bir sonraki adımda
**ücretsiz ve yasal (CC0)** modellerle değiştirilecek. Önerilen kaynaklar:

- [Kenney.nl](https://kenney.nl/assets) — CC0, ticari kullanım serbest
- [Quaternius](https://quaternius.com/) — CC0 düşük poligon karakter/çevre paketleri
- [Poly Pizza](https://poly.pizza/) — CC0 model arama

Modelleri `assets/` klasörüne (`.glb`/`.gltf`) koy; entegrasyonu birlikte yaparız.

## Proje yapısı

```
project.godot          Godot proje ayarları (autoload, giriş, mobil ayarlar)
scenes/Main.tscn       Ana sahne (dünyayı world.gd kurar)
scripts/
  game_state.gd        Singleton: can/mana/XP/level/altın/envanter + giriş tanımları
  world.gd             Dünya kurulumu + canavar popülasyonu
  player.gd            Oyuncu: hareket, yönelme, saldırı
  camera_rig.gd        Metin2 tarzı takip kamerası
  metin_stone.gd       Kırılabilir metin taşı
  monster.gd           Canavar yapay zekâsı
  drop_item.gd         Yerdeki toplanabilir eşya
  floating_text.gd     Havada yükselen yazı yardımcısı
  hud.gd               Ekran arayüzü (barlar, joystick, tuşlar, çanta)
  virtual_joystick.gd  Dokunmatik joystick
assets/                CC0 modeller buraya (henüz boş)
```

## Yol haritası (fikir)

- CC0 karakter/çevre modelleri ve animasyonlar
- Karakter sınıfları (savaşçı/ninja/sura/şaman) ve beceriler
- Görev (quest) ve NPC sistemi
- Ekipman/zırh ve item güçlendirme
- Ses + müzik (CC0)
- İleride: çok oyunculu (Nakama/Colyseus ile)
