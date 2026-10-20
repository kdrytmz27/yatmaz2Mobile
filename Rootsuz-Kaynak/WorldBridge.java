package com.abdulkadir.metin7x;

import android.content.Context;
import android.util.Log;
import dalvik.system.DexClassLoader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Uses only the packet parser, entity model and catalog packaged from the reference APK. */
final class WorldBridge {
    static final class Target {
        final int vid;
        final boolean player;
        final long distance;
        Target(int vid, boolean player, long distance) {
            this.vid = vid;
            this.player = player;
            this.distance = distance;
        }
    }

    static final class GroundItem {
        final int vid, vnum;
        final long distance;
        final String name, owner;
        final boolean yang;
        GroundItem(int vid, int vnum, long distance, String name, String owner) {
            this.vid = vid;
            this.vnum = vnum;
            this.distance = distance;
            this.name = name;
            this.owner = owner;
            this.yang = vnum == 1;
        }
    }

    /** Harita/radar için oyuncuya göre bağıl konumdaki varlıklar. */
    static final class HaritaVeri {
        boolean var;
        // her nokta: {tur, dx, dy} — tur: 0 mob, 2 metin, 6 oyuncu, 9 eşya, 10 yang
        final List<int[]> noktalar = new ArrayList<>();
        // noktalar ile AYNI sırada ad (metin/canavar/oyuncu ismi; eşyada "").
        final List<String> adlar = new ArrayList<>();
    }

    private static volatile WorldBridge instance;
    private final Object world;
    private final Constructor<?> parserCtor;
    private final Method feedIn;
    private final Method feedOut;
    private final Method hasPosition;
    private final Method getX;
    private final Method getY;
    private final Method getEntities;
    private final Method getLastUpdate;
    private final Method getOwnVid;
    private final Method getGround;
    private final Method effectiveType;
    private final Method adMethod;
    private final Method itemName;
    private Method eskileriTemizle;        // parser'da varsa: bayat varlıkları at
    private Method varliklariTemizleM;     // kanal değişince: tüm varlıkları sil
    private Method kendiVidSifirlaM;       // kanal değişince: kendi vid'i unut
    private final Field vid;
    private final Field vnum;
    private final Field x;
    private final Field y;
    private Field varlikSon;               // Varlik.sonGorulme (ms) — tazelik filtresi
    private final Field itemVid, itemVnum, itemX, itemY, itemOwner, itemSeen;

    // Kanal değişince eski kanalın canavar/metinleri kalmasın: bu süreden eski
    // (son görülme) varlıklar haritada/hedefte GÖSTERİLMEZ. Görünür varlıklar
    // sunucudan sürekli tazelendiği için bu pencere onları etkilemez.
    private static final long TAZE_MS = 10000;
    private long sonTemizlik;

    static WorldBridge init(Context context) {
        if (instance == null) {
            synchronized (WorldBridge.class) {
                if (instance == null) instance = new WorldBridge(context);
            }
        }
        // VPN başlar başlamaz: oynadığın GERÇEK karakterin konumunu panele
        // gönderen istemciyi başlat (harita overlay'i açık olmasa da çalışsın).
        try { TahtaIstemci.get(context).baslat(); } catch (Throwable ignored) { }
        return instance;
    }

    static WorldBridge get() {
        WorldBridge bridge = instance;
        if (bridge == null) throw new IllegalStateException("Paket ayrıştırıcı başlatılmadı");
        return bridge;
    }

    private WorldBridge(Context context) {
        try {
            File dex = new File(context.getCodeCacheDir(), "r2-parser.jar");
            if (!dex.exists()) {
                File tmp = new File(context.getCodeCacheDir(), "r2-parser.tmp");
                try (InputStream input = context.getAssets().open("r2-parser.jar");
                        FileOutputStream output = new FileOutputStream(tmp)) {
                    byte[] chunk = new byte[8192];
                    int count;
                    while ((count = input.read(chunk)) != -1) output.write(chunk, 0, count);
                }
                if (!tmp.setReadOnly() || !tmp.renameTo(dex)) {
                    throw new IllegalStateException("Ayrıştırıcı dosyası hazırlanamadı");
                }
            }
            ClassLoader loader = new DexClassLoader(dex.getAbsolutePath(),
                    context.getCodeCacheDir().getAbsolutePath(), null, context.getClassLoader());
            Class<?> parserClass = loader.loadClass("com.abdulkadir.r2panel.PaketAyristirici");
            Class<?> worldClass = loader.loadClass("com.abdulkadir.r2panel.DunyaDurumu");
            Class<?> entityClass = loader.loadClass("com.abdulkadir.r2panel.Varlik");
            Class<?> itemClass = loader.loadClass("com.abdulkadir.r2panel.YerEsyasi");
            Class<?> catalogClass = loader.loadClass("com.abdulkadir.r2panel.OyunKatalogu");
            catalogClass.getMethod("yukle", Context.class).invoke(catalogClass.getMethod("al").invoke(null), context);
            world = worldClass.getMethod("al").invoke(null);
            parserCtor = parserClass.getConstructor();
            feedIn = parserClass.getMethod("besle", byte[].class, int.class, int.class);
            feedOut = parserClass.getMethod("hareketTaraGiden", byte[].class, int.class, int.class);
            hasPosition = worldClass.getMethod("konumBilinir");
            getX = worldClass.getMethod("benimX");
            getY = worldClass.getMethod("benimY");
            getEntities = worldClass.getMethod("varlikKopyasi");
            getLastUpdate = worldClass.getMethod("sonGuncelleme");
            getOwnVid = worldClass.getMethod("kendiVid");
            getGround = worldClass.getMethod("yakinEsyalar", int.class);
            effectiveType = entityClass.getMethod("etkinTip");
            adMethod = entityClass.getMethod("ad");
            itemName = itemClass.getMethod("ad");
            vid = entityClass.getField("id");
            vnum = entityClass.getField("vnum");
            x = entityClass.getField("hamX");
            y = entityClass.getField("hamY");
            try { varlikSon = entityClass.getField("sonGorulme"); }
            catch (NoSuchFieldException ignore) { varlikSon = null; }
            try { eskileriTemizle = worldClass.getMethod("eskileriTemizle"); }
            catch (NoSuchMethodException ignore) { eskileriTemizle = null; }
            try { varliklariTemizleM = worldClass.getMethod("varliklariTemizle"); }
            catch (NoSuchMethodException ignore) { varliklariTemizleM = null; }
            try { kendiVidSifirlaM = worldClass.getMethod("kendiVidSifirla"); }
            catch (NoSuchMethodException ignore) { kendiVidSifirlaM = null; }
            itemVid = itemClass.getField("id");
            itemVnum = itemClass.getField("vnum");
            itemX = itemClass.getField("hamX");
            itemY = itemClass.getField("hamY");
            itemOwner = itemClass.getField("sahip");
            itemSeen = itemClass.getField("sonGorulme");
        } catch (ReflectiveOperationException | java.io.IOException error) {
            throw new IllegalStateException("R2 paket ayrıştırıcısı yüklenemedi", error);
        }
    }

    Object newParser() {
        try { return parserCtor.newInstance(); }
        catch (ReflectiveOperationException error) { throw new IllegalStateException(error); }
    }

    void feedIncoming(Object parser, byte[] bytes) {
        if (bytes.length == 0) return;
        try { feedIn.invoke(parser, bytes, 0, bytes.length); }
        catch (ReflectiveOperationException error) { Log.w("Metin7x", "Gelen paket çözümlenemedi", error); }
    }

    void feedOutgoing(Object parser, byte[] bytes) {
        if (bytes.length == 0) return;
        try { feedOut.invoke(parser, bytes, 0, bytes.length); }
        catch (ReflectiveOperationException error) { Log.w("Metin7x", "Giden hareket çözümlenemedi", error); }
    }

    boolean hasPosition() {
        try { return (Boolean) hasPosition.invoke(world); }
        catch (ReflectiveOperationException error) { return false; }
    }

    long lastUpdate() {
        try { return (Long) getLastUpdate.invoke(world); }
        catch (ReflectiveOperationException error) { return 0; }
    }

    /** Kendi karakterimizin sunucu vid'i (0x3F can paketini eşlemek için). */
    int ownVid() {
        try { return (Integer) getOwnVid.invoke(world); }
        catch (ReflectiveOperationException error) { return 0; }
    }

    /** Sunucu tiki (0x07 hareket paketinin dwTime alanı için). */
    public int tahminiTik() {
        try {
            Object v = worldClass().getMethod("tahminiTik").invoke(world);
            return v instanceof Number ? ((Number) v).intValue() : 0;
        } catch (ReflectiveOperationException error) {
            return 0;
        }
    }

    private Class<?> worldClass() { return world.getClass(); }

    /** Oyuncunun MUTLAK dünya konumu {x, y} ya da null (konum yoksa). */
    public int[] benimKonum() {
        try {
            if (!(Boolean) hasPosition.invoke(world)) return null;
            return new int[]{(Integer) getX.invoke(world),
                             (Integer) getY.invoke(world)};
        } catch (ReflectiveOperationException error) {
            return null;
        }
    }

    List<Target> targets(BotSettings.Snapshot settings) {
        List<Target> selected = new ArrayList<>();
        try {
            if (!(Boolean) hasPosition.invoke(world)) return selected;
            long simdi = System.currentTimeMillis();
            int px = (Integer) getX.invoke(world);
            int py = (Integer) getY.invoke(world);
            int ownVid = (Integer) getOwnVid.invoke(world);
            for (Object entity : (List<?>) getEntities.invoke(world)) {
                int kind = (Integer) effectiveType.invoke(entity);
                boolean player = kind == 6;
                if (!(kind == 0 && settings.mobs || kind == 2 && settings.metins ||
                        player && settings.pvp) ||
                        (!player && vnum.getInt(entity) <= 0)) continue;
                int id = vid.getInt(entity);
                if (id <= 0 || id == ownVid) continue;
                if (!taze(entity, simdi)) continue;   // bayat (eski kanal) hedefe saldırma
                long dx = (long) x.getInt(entity) - px;
                long dy = (long) y.getInt(entity) - py;
                long distance = dx * dx + dy * dy;
                int max = player ? settings.pvpRange : settings.attackRange;
                if (distance <= (long) max * max)
                    selected.add(new Target(id, player, distance));
            }
            Collections.sort(selected, Comparator.comparingLong(t -> t.distance));
        } catch (ReflectiveOperationException error) {
            Log.w("Metin7x", "Hedef seçilemedi", error);
        }
        return selected;
    }

    /** Radar için: menzilCap kadar yakındaki metin/mob/oyuncu + yer eşyaları (oyuncuya bağıl). */
    HaritaVeri harita(int menzilCap) {
        HaritaVeri hv = new HaritaVeri();
        try {
            if (!(Boolean) hasPosition.invoke(world)) return hv;
            hv.var = true;
            long simdi = System.currentTimeMillis();
            belkiTemizle(simdi);
            int px = (Integer) getX.invoke(world);
            int py = (Integer) getY.invoke(world);
            int ownVid = (Integer) getOwnVid.invoke(world);
            for (Object entity : (List<?>) getEntities.invoke(world)) {
                int kind = (Integer) effectiveType.invoke(entity);
                if (kind != 0 && kind != 2 && kind != 6) continue;
                int id = vid.getInt(entity);
                if (id <= 0 || id == ownVid) continue;
                if (kind != 6 && vnum.getInt(entity) <= 0) continue;
                if (!taze(entity, simdi)) continue;   // bayat (eski kanal) varlığı gösterme
                int dx = x.getInt(entity) - px;
                int dy = y.getInt(entity) - py;
                if (Math.abs(dx) > menzilCap || Math.abs(dy) > menzilCap) continue;
                hv.noktalar.add(new int[]{kind, dx, dy});
                hv.adlar.add((String) adMethod.invoke(entity));   // metin/canavar/oyuncu adı
            }
            long now = System.currentTimeMillis();
            for (Object item : (List<?>) getGround.invoke(world, 100)) {
                int id = itemVid.getInt(item);
                if (id <= 0 || now - itemSeen.getLong(item) > 120000) continue;
                int dx = itemX.getInt(item) - px;
                int dy = itemY.getInt(item) - py;
                if (Math.abs(dx) > menzilCap || Math.abs(dy) > menzilCap) continue;
                hv.noktalar.add(new int[]{itemVnum.getInt(item) == 1 ? 10 : 9, dx, dy});
                hv.adlar.add("");                                 // eşyada isim gösterilmez
            }
        } catch (ReflectiveOperationException error) {
            Log.w("Metin7x", "Harita verisi alınamadı", error);
        }
        return hv;
    }

    /** Varlık son TAZE_MS içinde görüldü mü (bayat=eski kanal varlığı mı)? */
    private boolean taze(Object entity, long simdi) {
        if (varlikSon == null) return true;       // alan yoksa filtreleme
        try {
            return simdi - varlikSon.getLong(entity) <= TAZE_MS;
        } catch (ReflectiveOperationException e) {
            return true;
        }
    }

    /** Ara sıra parser'ın bayat varlık temizliğini çağır (bellek şişmesin). */
    private void belkiTemizle(long simdi) {
        if (eskileriTemizle == null || simdi - sonTemizlik < 5000) return;
        sonTemizlik = simdi;
        try { eskileriTemizle.invoke(world); } catch (ReflectiveOperationException ignored) { }
    }

    /**
     * Kanal (ch) değişti: eski kanalın varlık listesini ve kendi vid'ini sıfırla.
     * Attack7x.kanalKontrol'den, port'tan çözülen kanal değiştiğinde çağrılır.
     * Böylece radar/harita eski kanalın canavar/metin/oyuncularını göstermez.
     */
    public void kanalDegisti() {
        try { if (varliklariTemizleM != null) varliklariTemizleM.invoke(world); }
        catch (ReflectiveOperationException ignored) { }
        try { if (kendiVidSifirlaM != null) kendiVidSifirlaM.invoke(world); }
        catch (ReflectiveOperationException ignored) { }
        sonTemizlik = System.currentTimeMillis();
        android.util.Log.i("Metin7x", "harita: kanal degisti -> varliklar sifirlandi");
    }

    private static String plain(String text) {
        String normalized = Normalizer.normalize(text == null ? "" : text, Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{M}", "").toLowerCase(Locale.ROOT).replace('ı', 'i');
    }

    private static boolean matches(GroundItem item, String text) {
        for (String raw : text.replace(';', ',').split(",")) {
            String term = raw.trim();
            if (term.isEmpty()) continue;
            if (term.equals(String.valueOf(item.vnum)) || plain(item.name).contains(plain(term))) return true;
        }
        return false;
    }

    List<GroundItem> groundItems(BotSettings.Snapshot settings) {
        List<GroundItem> selected = new ArrayList<>();
        try {
            if (!(Boolean) hasPosition.invoke(world)) return selected;
            int px = (Integer) getX.invoke(world);
            int py = (Integer) getY.invoke(world);
            long now = System.currentTimeMillis();
            for (Object item : (List<?>) getGround.invoke(world, 100)) {
                int id = itemVid.getInt(item);
                if (id <= 0 || now - itemSeen.getLong(item) > 120000) continue;
                long dx = (long) itemX.getInt(item) - px;
                long dy = (long) itemY.getInt(item) - py;
                long distance = dx * dx + dy * dy;
                if (distance > (long) settings.pickupRange * settings.pickupRange) continue;
                String owner = (String) itemOwner.get(item);
                if (owner == null) owner = "";
                if (settings.onlyOwn && !owner.trim().isEmpty() &&
                        (settings.playerName.isEmpty() ||
                         !owner.trim().equalsIgnoreCase(settings.playerName))) continue;
                GroundItem value = new GroundItem(id, itemVnum.getInt(item), distance,
                        (String) itemName.invoke(item), owner);
                boolean matched = matches(value, settings.filterText);
                if (!settings.filterText.trim().isEmpty() && settings.filterMode == 1 && !matched)
                    continue;
                if (!settings.filterText.trim().isEmpty() && settings.filterMode == 2 && matched)
                    continue;
                selected.add(value);
            }
            Collections.sort(selected, (a,b) -> {
                if (settings.yangFirst && a.yang != b.yang) return a.yang ? -1 : 1;
                return Long.compare(a.distance, b.distance);
            });
        } catch (ReflectiveOperationException error) {
            Log.w("Metin7x", "Yerdeki eşyalar çözümlenemedi", error);
        }
        return selected;
    }
}
