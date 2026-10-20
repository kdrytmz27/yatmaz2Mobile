package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.SharedPreferences;

/** A single immutable settings snapshot is shared between the overlay and VPN worker. */
public final class BotSettings {
    public static final class Snapshot {
        public final boolean mobs, metins, multi, simple, pvp, collect, yangFirst, onlyOwn, autoBuff;
        public final boolean autoPot;
        public final boolean potXXL, potBuyuk, potOrta, potKucuk;
        public final int scanRange, attackRange, hitMs, series, maxTargets;
        public final int pvpMs, pvpRange, pickupRange, filterMode;
        public final int potEsik, potBekleMs;
        public final String playerName, filterText;

        private Snapshot(SharedPreferences p) {
            mobs = p.getBoolean("mobs", true);
            metins = p.getBoolean("metins", true);
            multi = p.getBoolean("multi", true);
            simple = p.getBoolean("simple", true);
            pvp = p.getBoolean("pvp", false);
            collect = p.getBoolean("collect", true);
            yangFirst = p.getBoolean("yangFirst", true);
            onlyOwn = p.getBoolean("onlyOwn", true);
            autoBuff = p.getBoolean("autoBuff", false);
            autoPot = p.getBoolean("autoPot", false);
            potEsik = bounded(p.getInt("potEsik", 99), 1, 100);
            potBekleMs = bounded(p.getInt("potBekleMs", 800), 200, 10000);
            potXXL = p.getBoolean("potXXL", false);
            potBuyuk = p.getBoolean("potBuyuk", false);
            potOrta = p.getBoolean("potOrta", false);
            potKucuk = p.getBoolean("potKucuk", true);   // varsayılan sadece küçük
            scanRange = bounded(p.getInt("scanRange", 300), 1, 30000);
            attackRange = bounded(p.getInt("attackRange", 200), 1, 30000);
            hitMs = bounded(p.getInt("hitMs", 10), 1, 5000);
            series = bounded(p.getInt("series", 30), 1, 30);
            maxTargets = bounded(p.getInt("maxTargets", 30), 1, 30);
            pvpMs = bounded(p.getInt("pvpMs", 150), 10, 5000);
            pvpRange = bounded(p.getInt("pvpRange", 300), 1, 30000);
            pickupRange = bounded(p.getInt("pickupRange", 700), 1, 10000);
            filterMode = bounded(p.getInt("filterMode", 0), 0, 2);
            playerName = p.getString("playerName", "YIKAR").trim();
            filterText = p.getString("filterText", "");
        }
    }

    private static volatile BotSettings singleton;
    private final SharedPreferences prefs;
    private volatile Snapshot current;

    private BotSettings(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences("metin7x_settings", 0);
        current = new Snapshot(prefs);
    }

    public static BotSettings get(Context context) {
        if (singleton == null) {
            synchronized (BotSettings.class) {
                if (singleton == null) singleton = new BotSettings(context);
            }
        }
        return singleton;
    }

    public Snapshot snapshot() { return current; }

    public boolean compact() { return prefs.getBoolean("compact", false); }

    public boolean okuBool(String key, boolean def) { return prefs.getBoolean(key, def); }

    public boolean miniOpen() { return prefs.getBoolean("miniOpen", true); }

    public void setMiniOpen(boolean value) {
        prefs.edit().putBoolean("miniOpen", value).apply();
    }

    public void setCompact(boolean compact) {
        prefs.edit().putBoolean("compact", compact).apply();
    }

    public synchronized void bool(String key, boolean value) {
        prefs.edit().putBoolean(key, value).apply();
        current = new Snapshot(prefs);
    }

    public synchronized void number(String key, int value) {
        prefs.edit().putInt(key, value).apply();
        current = new Snapshot(prefs);
    }

    public synchronized void string(String key, String value) {
        prefs.edit().putString(key, value).apply();
        current = new Snapshot(prefs);
    }

    private static int bounded(int value, int min, int max) {
        return Math.max(min, Math.min(value, max));
    }
}
