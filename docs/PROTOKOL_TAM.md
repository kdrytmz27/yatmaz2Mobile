# Romia2 Ağ Protokolü — Tam Paket Envanteri

Kaynak: `re/global-metadata.dat` (Unity IL2CPP). Oyun **standart Metin2 ailesi**
protokolü kullanıyor — paket adları (`HEADER_GC_*`, `TPacketGC*`) ve alan adları
(`dwVID, lX, lY, bFunc…`) bunu birebir doğruluyor.

- **GC** = Game→Client = **sunucudan bize gelen** (118 tip)
- **CG** = Client→Game = **bizim gönderebildiğimiz** (81 tip)
- Byte değerleri (opcode sayıları) enum sırasından gelir; kesin sayı için
  Il2CppDumper gerekir, ama isim ve içerik burada.

Görülen ortak alan adları: `dwVID` (varlık örnek kimliği), `wRaceNum` (tür/vnum),
`sName` (isim), `bFunc`/`bArg` (hareket fonksiyonu/argümanı), `lX/lY/lZ` (konum),
`bType`, `bStateFlag`, `dwTime` (istemci tik), `dwTargetVID` (hedef), `fDistance`,
`bCount`.

---

## 1) Karakter & Hareket (sunucudan — GC)

| Paket | Ne alıyoruz |
|---|---|
| `CHARACTER_ADD` | Bir varlık görüş alanına girdi: vid, konum, açı, tür (vnum), hız |
| `CHARACTER_DEL` | Varlık gitti/öldü: vid |
| `CHARACTER_UPDATE` | Görünüm/kılık/parça değişimi: vid + ekipman |
| `CHAR_ADDITIONAL_INFO` | İsim, lonca, seviye, kılık — varlık detayları |
| `MOVE` | Varlık hareketi: vid, `bFunc` (yürü/dur/saldırı), yön, x, y, tik |
| `MAIN_CHARACTER` (+3_BGM, +4_BGM_VOL) | **Senin** karakterin: vid, ilk konum, ırk, harita |
| `NPC_POSITION` | Haritadaki NPC/mob konumlarının **toplu listesi** |
| `SYNC_POSITION` | Yakın varlıkların gerçek konumlarının **periyodik çoklu** senkronu |
| `CHARACTER_POSITION` | Tek varlık konum bildirimi |
| `WALK_MODE` | Yürüme/koşma modu değişimi |
| `CHANGE_SPEED` | Hız değişimi (hızlanma efekti vb.) |
| `CHANGE_NAME` | İsim değişimi |
| `WARP` | Işınlanma (harita/kanal geçişi — yeni sunucu portu) |
| `OWNERSHIP` | Bir varlığın/eşyanın sahiplik bilgisi |

## 2) Savaş & Efektler (GC)

| Paket | Ne alıyoruz |
|---|---|
| `DAMAGE_INFO` | Hasar: kaynak/hedef vid, hasar miktarı, tür (kritik vb.) |
| `DEAD` | Bir varlık öldü |
| `STUN` | Sersemleme |
| `AFFECT_ADD` / `AFFECT_REMOVE` | Buff/debuff ekle/çıkar (tip, süre) |
| `SPECIAL_EFFECT` / `SPECIFIC_EFFECT` | Görsel efekt tetikleme |
| `CREATE_FLY` / `ADD_FLY_TARGETING` / `FLY_TARGETING` | Ok/mermi uçuşu ve hedefleme |
| `DIG_MOTION` | Kazma animasyonu |
| `PVP` / `DUEL_START` | PvP durumu / düello |

## 3) Hedef (GC)

| Paket | Ne alıyoruz |
|---|---|
| `TARGET` / `TARGET_CREATE` / `TARGET_UPDATE` / `TARGET_DELETE` | Hedef göstergesi |
| `SET_TARGET_INFO` | Hedefin **can %'si**, seviyesi (hedef seçince gelir) |

## 4) Puanlar / Stat (GC)

| Paket | Ne alıyoruz |
|---|---|
| `CHARACTER_POINTS` | Tüm statlar (can, mana, güç, tecrübe, yang…) tek pakette |
| `CHARACTER_POINT_CHANGE` | Tek bir statın değişimi (ör. can azaldı) |

## 5) Eşya (GC)

| Paket | Ne alıyoruz |
|---|---|
| `ITEM_GROUND_ADD` / `ITEM_GROUND_DEL` | **Yerdeki eşya (drop)** düştü / kaldırıldı: vid, vnum, konum |
| `ITEM_SET` / `ITEM_UPDATE` / `ITEM_DEL` | Envanter slot doldur / güncelle / sil |
| `ITEM_USE` | Eşya kullanıldı |
| `ITEM_OWNERSHIP` | Yerdeki eşyanın kime ait olduğu (loot koruması) |
| `QUICKSLOT_ADD/DEL/SWAP` | Hızlı erişim çubuğu |

## 6) Yetenek (GC)

| Paket | Ne alıyoruz |
|---|---|
| `SKILL_LEVEL` | Yetenek seviyeleri |
| `SKILL_GROUP` | Sınıf/yetenek grubu seçimi |

## 7) Sohbet & Sosyal (GC)

| Paket | Ne alıyoruz |
|---|---|
| `CHAT` | Genel sohbet: tip (normal/GM/sistem/parti/lonca), vid, metin |
| `WHISPER` | Özel mesaj: gönderen, metin |
| `MESSENGER` (+ListElement, +LoginLogout) | Arkadaş listesi |
| `PARTY_*` (Add/Remove/Update/Link/Invite/Parameter…) | Parti sistemi |
| `GUILD*` (Info, War, Token, SubGrade…) | Lonca sistemi |
| `LOVER_INFO` / `LOVE_POINT_UPDATE` | Sevgili sistemi |

## 8) NPC Etkileşim / Ticaret / Görev (GC)

| Paket | Ne alıyoruz |
|---|---|
| `SCRIPT` | NPC diyalog metni/menüsü (quest/NPC konuşması) |
| `QUEST_INFO` / `QUEST_CONFIRM` | Görev bilgisi / onay penceresi |
| `SHOP` / `SHOP_SIGN` / `SHOP_START(Ex)` / `SHOP_UPDATE_ITEM` | NPC/oyuncu dükkânı |
| `EXCHANGE` | Takas penceresi |
| `SAFEBOX_*` | Kasa (depo) |
| `FISHING` | Balıkçılık |
| `REFINE_INFORMATION` / `DRAGON_SOUL_REFINE` | Geliştirme/ejder ruhu |
| `SET_CHEST_REWARDS` / `OPEN_CHEST` | Sandık ödülleri |
| `SET_ITEMSHOP_DATA` / `MALL_*` | Kalem/mağaza (item shop) |

## 9) Sistem / Oturum (GC)

| Paket | Ne alıyoruz |
|---|---|
| `HANDSHAKE` / `KEY_AGREEMENT(_COMPLETED)` | El sıkışma / anahtar anlaşması (oturum başı) |
| `AUTH_SUCCESS` / `LOGIN_SUCCESS_NEWSLOT` / `LOGIN_FAILURE` / `LOGIN_KEY` | Giriş |
| `CHANNEL` / `RESPOND_CHANNELSTATUS` | Kanal bilgisi/durumu |
| `PHASE` | Oyun fazı (login/select/loading/game) |
| `PING` / `TIME` / `TIME_SYNC` | Ağ tik / zaman senkronu |
| `EMPIRE` | Krallık bilgisi |
| `MARK_*` / `SYMBOL_DATA` | Lonca amblemi/sembol |
| `LAND_LIST` | Lonca arazileri |
| `MAINTENANCE` | Bakım bildirimi |
| `CHANGE_NAME` | İsim değiştirme sonucu |
| `AUTO_HUNTING` | Oto-avlanma durumu |
| `VIEW_EQUIP` | Başka oyuncunun ekipmanını görüntüleme |
| `DUNGEON` | Zindan bilgisi |
| `GLOBAL_RANKING` / `KYGN_EVENT` / `BIOLOG` / `WOF` | Sıralama/etkinlik sistemleri |

---

## 10) Bizim gönderebildiklerimiz (CG) — özet

**Hareket/aksiyon:** `MOVE` (yürü/dur), `ATTACK` (saldır), `SHOOT` (ateş et),
`USE_SKILL` (yetenek), `SYNC_POSITION` (konum senkronu), `WARP` (ışınlanma isteği),
`CHARACTER_POSITION`.

**Hedef/etkileşim:** `TARGET` (hedef seç), `GET_TARGET_INFO` (hedef bilgisi iste),
`ON_CLICK` (NPC/varlığa tıkla), `SCRIPT_ANSWER` / `SCRIPT_BUTTON` /
`SCRIPT_SELECT_ITEM` (diyalog cevabı/butonu).

**Eşya:** `ITEM_PICKUP` (yerden al), `ITEM_DROP2` (yere at), `ITEM_MOVE` (taşı),
`ITEM_USE` / `ITEM_USE_TO_ITEM` (kullan), `ITEM_GIVE` (ver).

**Ticaret/depo:** `SHOP`, `MYSHOP`, `EXCHANGE`, `SAFEBOX_CHECKIN/CHECKOUT`,
`ITEMSHOP_BUY`.

**Sistem:** `HANDSHAKE`, `LOGIN/LOGIN2/LOGIN3`, `KEY_AGREEMENT`, `ENTERGAME`,
`CHARACTER_SELECT/CREATE/DELETE`, `PONG`, `TIME_SYNC`, `STATE_CHECKER`, `HACK`
(anti-cheat bildirimi), `TEXT`.

**Sosyal:** `CHAT`, `WHISPER`, `PARTY_*`, `GUILD*`, `MESSENGER`.

---

## 11) Önemli paket içerik düzenleri (Metin2 standart + doğrulanan)

Bu yapılar Metin2 ailesinde bilinir; alan adları metadata'da görüldü.

**MOVE (hareket) — sunucu ve istemci benzer:**
```
header(1) | bFunc(1) | bArg(1) | bRot(1) | dwVID(4)?  ...  lX(4) | lY(4) | dwTime(4)
```
> Bizim yakaladığımız GİDEN 0x07 (kendi hareketin) 16 bayt: `07|durum|00|yön|x|y|tik`
> — `dwVID` yok çünkü gönderen zaten sensin. GELEN move'da `dwVID` vardır (kimin).

**CHARACTER_ADD (doğuş):** `dwVID, angle, lX, lY, lZ, bType, wRaceNum(vnum), bMovingFlag, ...`
— vnum burada gelir, isim bu yüzden yalnızca doğuşta çözülür.

**CHARACTER_DEL:** `dwVID` (5 bayt: header + vid) — bizim bulduğumuz `02|vid`.

**SYNC_POSITION:** `header | wSize | [ Element{ dwVID, lX, lY } ... ]` — yakın
varlıkların gerçek konumlarını toplu düzeltir.

**SET_TARGET_INFO:** `dwVID, bLevel, bRacePercent(can %)` — hedefin can yüzdesi.

**DAMAGE_INFO:** `dwVID, bType(kritik/normal/…), iDamage`.

---

## 12) Byte değerleri nasıl kesinleşir

İsimler ve **sıra** metadata'da var; her `HEADER_GC_*` bir enum sabiti. Byte
karşılıkları (ör. `MOVE=0x03`, `CHARACTER_DEL=0x02`) enum **ordinal**'ından gelir:
- Kesin çıkarmak için Il2CppDumper (v39 desteği ile) veya
- Canlı yakalama + imza analizi (`PC_CAPTURE.bat` + `tools/*.py`) ile doğrulama.

Şu ana kadar canlı doğrulanan eşleşmeler: `CHARACTER_ADD=0x01`, `MOVE=0x03`,
`CHARACTER_DEL=0x02`. Diğerleri isim/işlev olarak kesin, byte değeri doğrulanacak.
