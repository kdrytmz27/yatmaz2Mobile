package com.abdulkadir.metin7x;

import com.github.megatronking.netbare.gateway.Interceptor;
import com.github.megatronking.netbare.gateway.Request;
import com.github.megatronking.netbare.gateway.RequestChain;
import com.github.megatronking.netbare.gateway.Response;
import com.github.megatronking.netbare.gateway.ResponseChain;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/** One parser and outgoing TCP tunnel for each intercepted game connection. */
public final class Attack7x implements Interceptor<Request, RequestChain, Response, ResponseChain> {
    private static final String GAME_IP = "185.128.114.87";
    private static final ExecutorService ATTACK_LOOP = Executors.newSingleThreadExecutor();
    private static final ExecutorService COLLECT_LOOP = Executors.newSingleThreadExecutor();
    private static volatile Attack7x active;
    private static volatile boolean enabled;
    private static volatile boolean loopStarted;
    private static volatile long lastStatusLog;
    // Oto-buff-takip: en son buff'çıyı çektiğimiz kanal (port'tan çözülür).
    private static volatile int lastKanal = -1;
    // Oto-iksir: kendi canımız (puan paketinden) — güncel, azami (dinamik), yüzde.
    private static volatile int benimCan = -1;
    private static volatile int benimMaksCan = 0;
    private static volatile int benimCanYuzde = -1;
    private static volatile long sonPot;
    // HP kaydının vid'i pakketten öğrenilir (self-only format); bayatlarsa sıfırlanır.
    private static volatile int kilitVid = 0;
    private static volatile long sonCanZamani = 0;
    private byte[] canKuyruk = new byte[0];
    // TEŞHİS: nerede takıldığını görmek için sayaçlar.
    private static volatile int tSayac, desenSayac, gecerliSayac, sonVid, sonHp;
    private static volatile int interceptTum;      // her ResponseChain (oyun olmasa da)
    private static volatile String sonBaglanti = "-";
    private static volatile long potBekleSuresi = 150;   // güncel rastgele bekleme (100-200 ms)
    // İksir hızlı-slot paketleri: 0B 01 <slot> 00 (yakalandı 26-27 Eyl 2026).
    // Küçük=0x0F, orta=0x0D, büyük=0x10, XXL=0x11. Hangisi basılacağı ayardan.
    private static final byte[] IKSIR_XXL   = { 0x0b, 0x01, 0x11, 0x00 };
    private static final byte[] IKSIR_BUYUK = { 0x0b, 0x01, 0x10, 0x00 };
    private static final byte[] IKSIR_ORTA  = { 0x0b, 0x01, 0x0d, 0x00 };
    private static final byte[] IKSIR_KUCUK = { 0x0b, 0x01, 0x0f, 0x00 };

    public static int canYuzde() { return benimCanYuzde; }

    public static String canMetni() {
        if (benimCanYuzde < 0)
            return "okunamadı [ic" + interceptTum + " oyun" + tSayac + " d" + desenSayac
                    + " g" + gecerliSayac + "] " + sonBaglanti;
        return "%" + benimCanYuzde + " (" + benimCan + "/" + benimMaksCan + ")";
    }
    private static final Map<Integer, Long> PICKED_RECENTLY = new ConcurrentHashMap<>();
    private static final Map<Integer, Long> PLAYER_HITS = new ConcurrentHashMap<>();
    private final WorldBridge world;
    private final Object parser;
    private volatile Request request;
    private volatile boolean closed;
    private volatile long lastResponse;

    public Attack7x() {
        world = WorldBridge.get();
        parser = world.newParser();
        ensureLoop();
    }

    public static void setEnabled(boolean value) {
        enabled = value;
        if (value) ensureLoop();
    }

    public static void ensureLoop() {
        if (!loopStarted) {
            synchronized (Attack7x.class) {
                if (!loopStarted) {
                    loopStarted = true;
                    ATTACK_LOOP.execute(Attack7x::runAttackLoop);
                    COLLECT_LOOP.execute(Attack7x::runCollectLoop);
                }
            }
        }
    }
    public static boolean isEnabled() { return enabled; }

    private static boolean game(String ip, int port) {
        return GAME_IP.equals(ip) && port >= 30000 && port <= 30150;
    }

    @Override public void intercept(RequestChain chain, ByteBuffer buffer) throws IOException {
        if (game(chain.request().ip(), chain.request().port())) {
            request = chain.request();
            ByteBuffer copy = buffer.asReadOnlyBuffer();
            byte[] bytes = new byte[copy.remaining()];
            copy.get(bytes);
            world.feedOutgoing(parser, bytes);
        }
        chain.process(buffer);
    }

    @Override public void intercept(ResponseChain chain, ByteBuffer buffer) throws IOException {
        interceptTum++;
        sonBaglanti = chain.response().ip() + ":" + chain.response().port();
        if (game(chain.response().ip(), chain.response().port())) {
            ByteBuffer copy = buffer.asReadOnlyBuffer();
            byte[] bytes = new byte[copy.remaining()];
            copy.get(bytes);
            long before = world.lastUpdate();
            world.feedIncoming(parser, bytes);
            try { canTara(bytes); } catch (RuntimeException ignored) { }
            if (active == this) lastResponse = System.currentTimeMillis();
            if (world.lastUpdate() > before && request != null && world.hasPosition() &&
                    (active == null || active.closed ||
                     System.currentTimeMillis() - active.lastResponse > 10000)) {
                lastResponse = System.currentTimeMillis();
                active = this;
                kanalKontrol(request.port());
            }
        }
        chain.process(buffer);
    }

    /**
     * Oyun bağlantısının portundan aktif kanalı çözer (kanal = (port-30003)/4:
     * ch1=30007 … ch8=30035; login/karakter-seç portları elenir). Kanal değişince
     * ve "Beni takip et" açıksa metin izleyiciye buff_cek gönderir.
     */
    private static void kanalKontrol(int port) {
        int off = port - 30003;
        if (off <= 0 || off % 4 != 0) return;      // login (30003) / karakter-seç (30025) / diğer
        int ch = off / 4;
        if (ch < 1 || ch > 8 || ch == lastKanal) return;
        lastKanal = ch;
        try {
            if (BotSettings.get(App.current()).snapshot().autoBuff)
                Overlay7xControls.otoBuffCek(ch);
        } catch (RuntimeException ignored) { }
    }

    private static int le32(byte[] b, int o) {
        return (b[o] & 0xFF) | (b[o + 1] & 0xFF) << 8
                | (b[o + 2] & 0xFF) << 16 | (b[o + 3] & 0xFF) << 24;
    }

    /**
     * Gelen akışta kendi HP puan kaydını arar (26 Eyl 2026 yakalaması):
     * {@code vid(4) | 00 | 05 | 00 00 00 00 | HP(4 LE)} — tip=0x05 güncel can.
     * Puan formatı yalnız kendi karaktere gelir. Azami can ayrı paketle
     * gelmediğinden dinamik öğrenilir (görülen en yüksek HP = azami).
     */
    private void canTara(byte[] cur) {
        tSayac++;
        long now = System.currentTimeMillis();
        if (kilitVid != 0 && now - sonCanZamani > 4000) kilitVid = 0;  // bayat kilit → yeniden öğren
        // Önceki buffer'ın kuyruğunu ekle (paket sınırına bölünme için).
        byte[] b;
        if (canKuyruk.length == 0) {
            b = cur;
        } else {
            b = new byte[canKuyruk.length + cur.length];
            System.arraycopy(canKuyruk, 0, b, 0, canKuyruk.length);
            System.arraycopy(cur, 0, b, canKuyruk.length, cur.length);
        }
        for (int p = 0; p + 14 <= b.length; p++) {
            if ((b[p + 4] & 0xFF) != 0x00 || (b[p + 5] & 0xFF) != 0x05) continue;
            if (b[p + 6] != 0 || b[p + 7] != 0 || b[p + 8] != 0 || b[p + 9] != 0) continue;
            desenSayac++;
            int vid = le32(b, p);
            int hp = le32(b, p + 10);
            if (vid <= 0 || hp < 1 || hp > 2_000_000) continue;
            gecerliSayac++; sonVid = vid; sonHp = hp;
            if (kilitVid == 0) kilitVid = vid;         // self-only format → ilk kayda kilitlen
            else if (vid != kilitVid) continue;
            benimCan = hp;
            if (hp > benimMaksCan) benimMaksCan = hp;
            benimCanYuzde = benimMaksCan > 0 ? (int) (100L * hp / benimMaksCan) : -1;
            sonCanZamani = now;
        }
        int keep = Math.min(20, cur.length);
        canKuyruk = java.util.Arrays.copyOfRange(cur, cur.length - keep, cur.length);
    }

    private static void potKontrol(Attack7x session, BotSettings.Snapshot settings)
            throws IOException {
        if (!settings.autoPot || session.closed || active != session) return;
        int hp = benimCanYuzde;
        if (hp <= 0 || hp >= settings.potEsik) return;   // hp<=0: bilinmiyor/ölü
        long now = System.currentTimeMillis();
        if (now - sonPot < potBekleSuresi) return;
        boolean bir = false;
        if (settings.potXXL)   { session.request.process(ByteBuffer.wrap(IKSIR_XXL.clone()));   bir = true; }
        if (settings.potBuyuk) { session.request.process(ByteBuffer.wrap(IKSIR_BUYUK.clone())); bir = true; }
        if (settings.potOrta)  { session.request.process(ByteBuffer.wrap(IKSIR_ORTA.clone()));  bir = true; }
        if (settings.potKucuk) { session.request.process(ByteBuffer.wrap(IKSIR_KUCUK.clone())); bir = true; }
        if (!bir) return;   // hiç iksir seçilmemiş
        sonPot = now;
        potBekleSuresi = 100 + (long) (Math.random() * 101);   // 100-200 ms rastgele (insansı)
    }

    @Override public void onRequestFinished(Request finished) { close(); }
    @Override public void onResponseFinished(Response finished) { close(); }

    private void close() {
        closed = true;
        if (active == this) active = null;
    }

    private static void runAttackLoop() {
        Attack7x previous = null;
        long lastRound = 0;
        int previousInterval = -1;
        while (true) {
            try {
                Attack7x session = active;
                if (session != previous) {
                    previous = session;
                    lastRound = 0;
                    PLAYER_HITS.clear();
                }
                if (!enabled || session == null || session.closed || session.request == null) {
                    lastRound = 0;
                    if (enabled) statusLog("7x: oyun TCP baglantisi bekleniyor");
                    Thread.sleep(10);
                    continue;
                }
                BotSettings.Snapshot settings = BotSettings.get(App.current()).snapshot();
                if (settings.hitMs != previousInterval) {
                    previousInterval = settings.hitMs;
                    lastRound = 0;
                }
                long now = System.nanoTime();
                if (lastRound != 0 && now - lastRound < TimeUnit.MILLISECONDS.toNanos(settings.hitMs)) {
                    waitWhileRunning(session, 50);
                    continue;
                }
                // Preserve the requested all-target coverage. Match the reference R2
                // simple worker's select -> 10 ms -> hit sequence and 50 ms round pause.
                List<WorldBridge.Target> targets = session.world.targets(settings);
                if (targets.isEmpty()) {
                    statusLog("7x: saldiri menzilinde uygun hedef yok");
                    waitWhileRunning(session, 500);
                    continue;
                }
                Request tunnel = session.request;
                int sent = 0;
                for (WorldBridge.Target target : targets) {
                    if (!enabled || active != session || session.closed) break;
                    long tick = System.currentTimeMillis();
                    Long last = PLAYER_HITS.get(target.vid);
                    if (target.player && last != null && tick - last < settings.pvpMs) continue;
                    tunnel.process(ByteBuffer.wrap(R2AttackProtocol.select(target.vid)));
                    if (!waitWhileRunning(session, 10)) break;
                    tunnel.process(ByteBuffer.wrap(R2AttackProtocol.attack(target.vid)));
                    sent++;
                    if (target.player) PLAYER_HITS.put(target.vid, tick);
                }
                if (System.currentTimeMillis() - lastStatusLog >= 5000)
                    statusLog("7x: " + sent + " hedefe paket, aralik " + settings.hitMs + " ms");
                lastRound = now;
                waitWhileRunning(session, 50);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                return;
            } catch (IOException ex) {
                active = null;
            } catch (RuntimeException ex) {
                android.util.Log.e("Metin7x", "Vuruş döngüsü", ex);
                try { Thread.sleep(1000); } catch (InterruptedException stop) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }

    private static boolean waitWhileRunning(Attack7x session, int millis)
            throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(millis);
        while (enabled && active == session && !session.closed) {
            long left = end - System.nanoTime();
            if (left <= 0) return true;
            TimeUnit.NANOSECONDS.sleep(Math.min(left, 50_000_000L));
        }
        return false;
    }

    private static void statusLog(String message) {
        long now = System.currentTimeMillis();
        if (now - lastStatusLog >= 5000) {
            lastStatusLog = now;
            android.util.Log.i("Metin7x", message);
        }
    }

    private static void runCollectLoop() {
        while (true) {
            try {
                Attack7x session = active;
                BotSettings.Snapshot settings = BotSettings.get(App.current()).snapshot();
                if (session != null && !session.closed && session.request != null) {
                    if (settings.collect) collect(session, settings, session.request, 8);
                    potKontrol(session, settings);
                }
                Thread.sleep(100);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                return;
            } catch (IOException ex) {
                active = null;
            } catch (RuntimeException ex) {
                android.util.Log.e("Metin7x", "Toplama döngüsü", ex);
                try { Thread.sleep(100); } catch (InterruptedException stop) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }

    private static void collect(Attack7x session, BotSettings.Snapshot settings,
                                Request tunnel, int limit) throws IOException {
        if (!settings.collect || session.closed || active != session) return;
        long now = System.currentTimeMillis();
        int sent = 0;
        for (WorldBridge.GroundItem item : session.world.groundItems(settings)) {
            if (sent >= limit || !BotSettings.get(App.current()).snapshot().collect ||
                    active != session) break;
            Long previous = PICKED_RECENTLY.get(item.vid);
            if (previous != null && now - previous < 1500) continue;
            byte[] pickup = new byte[5];
            pickup[0] = 0x0f;
            for (int b = 0; b < 4; b++) pickup[b + 1] = (byte) (item.vid >>> (8 * b));
            tunnel.process(ByteBuffer.wrap(pickup));
            PICKED_RECENTLY.put(item.vid, now);
            sent++;
        }
        if (PICKED_RECENTLY.size() > 400)
            PICKED_RECENTLY.entrySet().removeIf(entry -> now - entry.getValue() > 1500);
    }

}
