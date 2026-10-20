# Sunucudan Ne Veri Alıyoruz? (GC paketleri)

Kaynak: `re/global-metadata.dat` içindeki `TPacketGC*` (Game→Client = sunucu→istemci)
yapıları ve `Recv*Packet` işleyici adları. Bunlar oyunun **aldığı** tüm veri
tiplerini açıkça listeliyor. (Byte ofsetleri/opcode değerleri için Il2CppDumper
gerekir; isimler zaten ne olduğunu söylüyor.)

## Haritayı/botu ilgilendiren ana akışlar

| Paket (TPacketGC…) | İçerik | Bizde durum |
|---|---|---|
| **CharacterAdd** | Varlık doğdu: vid, konum, açı, tip, vnum | ✅ parse ediliyor (0x01) |
| **Move** | Varlık hareketi: vid, fonksiyon, yön, x, y, zaman | ✅ parse ediliyor (0x03) |
| **CharacterDelete** | Varlık sil: vid | ✅ parse ediliyor (0x02 — canlı bulduk) |
| **CharacterUpdate** | Görünüm/parça güncelleme | ⛔ parse edilmiyor |
| **CharacterAdditionalInfo** | İsim, lonca, seviye, kılık | ⛔ (isimleri katalogdan çözüyoruz) |
| **MainCharacter** | **BENİM** karakterim: vid, ilk konum, ırk | ⛔ (kendi vid'imizi buradan alabiliriz) |
| **NPCPosition** | NPC/mob konum **listesi** (harita açılışında toplu) | ⛔ **eklenebilir — zengin konum kaynağı** |
| **SyncPosition** (+Element) | Periyodik **çoklu varlık** konum senkronu/düzeltmesi | ⛔ **eklenebilir — akıcılık/doğruluk için değerli** |
| **Warp** | Işınlanma/kanal-harita geçişi | ✅ dolaylı (port değişiminden yakalıyoruz) |
| **Target / SetTargetInfo / TargetUpdate** | Hedef bilgisi, hedefin can %'si | ⛔ eklenebilir |
| **Points / PointChange** | Stat (can/mana/tecrübe…) | ⛔ eklenebilir |
| **ItemGroundAdd / ItemGroundDel** | Yerdeki eşya (drop) ekle/sil | ⛔ **eklenebilir — loot için** |
| **Chat / Whisper** | Sohbet / özel mesaj | ⛔ eklenebilir |
| **DamageInfo / Dead / Stun** | Hasar / ölüm / sersemleme | ⛔ eklenebilir |
| **AffectAdd / AffectRemove** | Buff/debuff ekle/çıkar | ⛔ eklenebilir |

## Kritik iki bulgu (akıcılık ve doğruluk)

1. **TPacketGCSyncPosition + SyncPositionElement** — sunucu, yakındaki varlıkların
   GERÇEK konumlarını periyodik olarak **tek pakette çoklu** gönderir (desync
   düzeltmesi). Bunu parse edersek mob konumları için ek, güvenilir bir kaynak
   olur — 0x03 hareket taramasının kaçırdıklarını doldurur.

2. **TPacketGCNPCPosition** — harita açılışında NPC/mob konumlarının toplu listesi.
   Radarı anında doldurmak için iyi.

## Kendi karakterinin akıcılığı hakkında (önemli)

`RecvCharacterMovePacket` / `TPacketGCMove` **başka** karakterlerin hareketidir.
**Kendi** konumun sunucudan sürekli GERİ gelmez — istemci senin karakterini yerelde
oynatır, sunucuya seyrek (~2 Hz) bildirir. `TPacketGCMainCharacter` yalnızca ilk
konumu verir. Yani kendi karakterinin oyun-kalitesinde akıcılığı ağdan elde
edilemez (bkz. radar akıcılık tartışması); ancak **diğer varlıklar** için
SyncPosition/Move/NPCPosition ile çok daha iyi veri toplayabiliriz.

## Sıradaki adım önerisi (okuma tarafı — hepsi meşru)

Öncelik sırası:
1. **SyncPosition** parse et → mob konum akıcılığı/doğruluğu artar.
2. **ItemGroundAdd/Del** parse et → yerdeki eşyalar (loot) radarda görünür.
3. **Target/Points** parse et → hedef can %'si, kendi can/mana.
4. **MainCharacter** parse et → kendi vid'imizi öğren (başka eşleştirmeler için).

Not: Bunların hepsi **aldığımız** veriyi çözmek (okuma). Byte düzenlerini canlı
yakalama (PC_CAPTURE) + `remove_bul.py` benzeri imza analiziyle doğrularız.
