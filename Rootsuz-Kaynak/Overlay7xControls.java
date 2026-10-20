package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import com.github.megatronking.netbare.NetBare;
import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import org.json.JSONArray;
import org.json.JSONObject;

/** The game overlay can show and control 7x without a PC or an R2 Panel API. */
public final class Overlay7xControls {
    private static volatile JSONObject lastData;
    private static volatile WeakReference<TextView> miniCollect = new WeakReference<>(null);
    private static TextView[] kanalBtns;      // 1-4 kanal düğmeleri (aktif olan yeşil)
    private static int aktifKanal;            // en son tıklanan (aktif) kanal, 0=yok
    private static TextView dolasBtn;         // otomatik dolaşım aç/kapat (açıkken yeşil)
    // Overlay servisi (komut/tünel sahibi). Attack7x oto-buff için buradan çeker.
    private static volatile WeakReference<Context> serviceRef = new WeakReference<>(null);
    private Overlay7xControls() { }

    // OverlayServisi ch hücre renkleri (smali'deki sabitlerle birebir).
    private static final int SONUK = 0xFF2a3040;
    private static final int SONUK_YAZI = 0xFF5a6072;
    private static final int ZEMIN = 0xE60a0d14;
    private static final int OYUNCU_MOR = 0xFFaa3cff;   // panel web oyuncu rengi (#aa3cff)

    /**
     * Ch hücresinin YAZI rengi. Kanalda oyuncu (adam) varsa numara MOR olur;
     * yoksa eski davranış (sönük hücrede sönük yazı, renkli hücrede koyu yazı).
     * OverlayServisi.ciz smali'sinden invoke-static ile çağrılır.
     */
    public static int yaziRengi(JSONObject ch, int hucreRengi) {
        int taban = (hucreRengi == SONUK) ? SONUK_YAZI : ZEMIN;
        if (ch != null) {
            JSONArray oyuncular = ch.optJSONArray("oyuncular");
            if (oyuncular != null && oyuncular.length() > 0) return OYUNCU_MOR;
        }
        return taban;
    }

    /** OverlayServisi detay panelini aç/kapat (ch ızgarasındaki eski ⚙ ile aynı iş). */
    static void detayAcKapa(Context context) {
        try {
            Method method = context.getClass().getDeclaredMethod("lambda$detayHucre$5", View.class);
            method.setAccessible(true);
            method.invoke(context, (View) null);
        } catch (Exception error) {
            android.util.Log.w("Metin7x", "Detay paneli açılamadı", error);
        }
    }

    /** Overlay servisini hatırla; komut'u olan bağlam buradan gelir. */
    private static void rememberService(Context context) {
        if (context != null) serviceRef = new WeakReference<>(context);
    }

    /** Oyun bağlantısının kanalını değiştirince Attack7x buradan buff'çıyı çeker. */
    static void otoBuffCek(int channel) {
        Context service = serviceRef.get();
        if (service == null || channel < 1 || channel > 8) return;
        try {
            JSONObject request = new JSONObject();
            request.put("komut", "buff_cek");
            request.put("kanal", channel);
            Method method = service.getClass().getDeclaredMethod("komut", JSONObject.class);
            method.setAccessible(true);
            method.invoke(service, request);
            android.util.Log.i("Metin7x", "oto-buff: ch" + channel);
        } catch (Exception error) {
            android.util.Log.w("Metin7x", "Oto-buff komutu gönderilemedi", error);
        }
    }

    private static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    private static TextView button(Context context, String title, int color) {
        TextView view = new TextView(context);
        view.setText(title);
        view.setTextColor(Color.WHITE);
        view.setTextSize(13);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(context, 10), dp(context, 7), dp(context, 10), dp(context, 7));
        GradientDrawable background = new GradientDrawable();
        background.setColor(color);
        background.setCornerRadius(dp(context, 7));
        view.setBackground(background);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(context, 44), 1);
        params.setMargins(dp(context, 3), 0, dp(context, 3), 0);
        view.setLayoutParams(params);
        return view;
    }

    public static void addRow(Context context, LinearLayout parent) {
        rememberService(context);
        LinearLayout row = new LinearLayout(context);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(context, 5), dp(context, 4), dp(context, 5), dp(context, 4));
        row.setLayoutParams(new LinearLayout.LayoutParams(dp(context, 340), -2));

        TextView title = new TextView(context);
        title.setText(Attack7x.isEnabled() ? "7x çalışıyor" : "7x vuruş");
        title.setTextColor(Color.WHITE);
        title.setTextSize(14);
        title.setLayoutParams(new LinearLayout.LayoutParams(0, dp(context, 44), 1));
        title.setGravity(Gravity.CENTER_VERTICAL);
        row.addView(title);

        TextView start = button(context, "▶ başlat", Color.rgb(19, 106, 68));
        TextView stop = button(context, "■ durdur", Color.rgb(119, 38, 39));
        start.setOnClickListener(view -> {
            if (NetBare.get().isActive()) {
                Attack7x.setEnabled(true);
                title.setText("7x çalışıyor");
            } else {
                Intent intent = new Intent(context, VpnActivity.class);
                intent.putExtra(VpnActivity.EXTRA_AUTO_START, true);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(intent);
            }
        });
        stop.setOnClickListener(view -> {
            Attack7x.setEnabled(false);
            title.setText("7x durdu");
        });
        row.addView(start);
        row.addView(stop);
        parent.addView(row);

        // SOLDAN AÇILIR MENÜ — ekranın solunda "☰"; 7x / Harita'yı ayrı ayrı
        // aç-kapa. (Overlay7xControls ile aynı eylemleri kullanır.)
        SolMenu.ac(context);
    }

    /** Stays in the always visible overlay, even when the gear panel is closed. */
    public static void addMiniRow(Context context, LinearLayout parent) {
        rememberService(context);
        // The smallest ch grid is two 20dp cells with 2dp margins on both sides.
        // Keeping this control at 48dp prevents it from widening the old overlay.
        BotSettings state = BotSettings.get(context);
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setLayoutParams(new LinearLayout.LayoutParams(dp(context, 48), -2));
        TextView title = new TextView(context);
        title.setText(state.miniOpen() ? "7x ▾" : "7x ▸");
        title.setTextColor(Attack7x.isEnabled() ? Color.rgb(104, 219, 151) : Color.WHITE);
        title.setTextSize(10);
        title.setGravity(Gravity.CENTER);
        title.setContentDescription("7x ve toplama panelini aç veya kapat");
        row.addView(title, new LinearLayout.LayoutParams(dp(context, 48), dp(context, 19)));

        // Her zaman görünür: ⚙ detay paneli (takip/harita/buff/kanallar) + ✕ kapat.
        // Ch ızgarasından çıkarıldı; böylece adalar eşit ve dikey modda düzgün.
        LinearLayout ustBtn = new LinearLayout(context);
        ustBtn.setOrientation(LinearLayout.HORIZONTAL);
        TextView gear = new TextView(context);
        gear.setText("⚙");
        gear.setTextColor(0xFF9aa0b4);
        gear.setTextSize(13);
        gear.setGravity(Gravity.CENTER);
        gear.setContentDescription("Detay panelini aç/kapat");
        gear.setOnClickListener(v -> detayAcKapa(context));
        TextView kapat = new TextView(context);
        kapat.setText("✕");
        kapat.setTextColor(0xFF6b7080);
        kapat.setTextSize(12);
        kapat.setGravity(Gravity.CENTER);
        kapat.setContentDescription("Çubuğu kapat");
        kapat.setOnClickListener(v -> {
            HaritaOverlay.kapat();
            if (context instanceof android.app.Service) ((android.app.Service) context).stopSelf();
        });
        ustBtn.addView(gear, new LinearLayout.LayoutParams(dp(context, 24), dp(context, 22)));
        ustBtn.addView(kapat, new LinearLayout.LayoutParams(dp(context, 24), dp(context, 22)));
        row.addView(ustBtn, new LinearLayout.LayoutParams(dp(context, 48), dp(context, 22)));

        LinearLayout controls = new LinearLayout(context);
        controls.setOrientation(LinearLayout.VERTICAL);
        LinearLayout buttons = new LinearLayout(context);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        TextView start = button(context, "▶", Color.rgb(19, 106, 68));
        TextView stop = button(context, "■", Color.rgb(119, 38, 39));
        start.setPadding(0, 0, 0, 0);
        stop.setPadding(0, 0, 0, 0);
        start.setTextSize(11);
        stop.setTextSize(11);
        buttons.addView(start, new LinearLayout.LayoutParams(dp(context, 24), dp(context, 28)));
        buttons.addView(stop, new LinearLayout.LayoutParams(dp(context, 24), dp(context, 28)));
        controls.addView(buttons);
        TextView collect = button(context, "", Color.rgb(19, 106, 68));
        collect.setTextSize(9);
        collect.setPadding(0, 0, 0, 0);
        controls.addView(collect, new LinearLayout.LayoutParams(dp(context, 48), dp(context, 32)));
        miniCollect = new WeakReference<>(collect);
        refreshCollectButton(context);
        collect.setOnClickListener(view -> {
            boolean next = !state.snapshot().collect;
            state.bool("collect", next);
            if (next) Attack7x.ensureLoop();
            refreshCollectButton(context);
            OverlaySettingsPanel.refreshCollectCheckbox(context);
        });
        // KANAL 1-4: basınca metin izleyicideki çarlar o kanala SIRALI (tek tek,
        // panel 'sıra sn' arayla, üstten alta) geçer. Tıklanan (aktif) kanal YEŞİL.
        final android.content.SharedPreferences chPref =
                context.getSharedPreferences("metin7x_settings", 0);
        aktifKanal = chPref.getInt("aktifKanal", 0);
        kanalBtns = new TextView[4];
        LinearLayout chSatir = null;
        for (int i = 0; i < 4; i++) {
            if (i % 2 == 0) {
                chSatir = new LinearLayout(context);
                chSatir.setOrientation(LinearLayout.HORIZONTAL);
                controls.addView(chSatir, new LinearLayout.LayoutParams(dp(context, 48), -2));
            }
            final int kanal = i + 1;
            TextView cb = new TextView(context);
            cb.setText(String.valueOf(kanal));
            cb.setTextColor(Color.WHITE);
            cb.setTextSize(11);
            cb.setGravity(Gravity.CENTER);
            cb.setContentDescription("Kanal " + kanal + " (sıralı geç)");
            cb.setBackground(kanalArka(context, 0));
            cb.setOnClickListener(v -> {
                aktifKanal = kanal;
                chPref.edit().putInt("aktifKanal", kanal).apply();
                kanalDurumTazele();            // tıklanınca hemen sarı (geçiş başladı)
                TahtaIstemci.kanalGonder(context, kanal);
            });
            kanalBtns[i] = cb;
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(dp(context, 22), dp(context, 24));
            clp.setMargins(i % 2 == 1 ? dp(context, 2) : 0, dp(context, 2), 0, 0);
            chSatir.addView(cb, clp);
        }
        // ⟳ Dolaş: otomatik kanal dolaşımı (ch yeşil olunca sonrakine) aç/kapat.
        TextView dolas = new TextView(context);
        dolas.setText("⟳ Dolaş");
        dolas.setTextColor(Color.WHITE);
        dolas.setTextSize(9);
        dolas.setGravity(Gravity.CENTER);
        dolas.setContentDescription("Otomatik kanal dolaşımı aç/kapat");
        dolas.setBackground(kanalArka(context, 0));
        dolas.setOnClickListener(v -> {
            boolean yeni = !chPref.getBoolean("dolasimIstek", false);
            chPref.edit().putBoolean("dolasimIstek", yeni).apply();
            TahtaIstemci.dolasimGonder(context, yeni);
            dolasBtn.setBackground(kanalArka(context, yeni ? 2 : 0));  // yerel: anında ve kalıcı
        });
        dolasBtn = dolas;
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(dp(context, 48), dp(context, 26));
        dlp.setMargins(0, dp(context, 3), 0, 0);
        controls.addView(dolas, dlp);

        kanalDurumTazele();                   // kayıtlı aktif kanalın rengini uygula
        controls.setVisibility(state.miniOpen() ? View.VISIBLE : View.GONE);
        row.addView(controls);
        title.setOnClickListener(view -> {
            boolean open = controls.getVisibility() != View.VISIBLE;
            state.setMiniOpen(open);
            controls.setVisibility(open ? View.VISIBLE : View.GONE);
            title.setText(open ? "7x ▾" : "7x ▸");
            row.post(() -> refreshDetailHeight(context));
        });
        start.setContentDescription("7x başlat");
        stop.setContentDescription("7x durdur");
        start.setOnClickListener(view -> {
            if (NetBare.get().isActive()) {
                Attack7x.setEnabled(true);
                title.setTextColor(Color.rgb(104, 219, 151));
            } else {
                Intent intent = new Intent(context, VpnActivity.class);
                intent.putExtra(VpnActivity.EXTRA_AUTO_START, true);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(intent);
            }
        });
        stop.setOnClickListener(view -> {
            Attack7x.setEnabled(false);
            title.setTextColor(Color.WHITE);
        });
        parent.addView(row);
    }

    // durum: 0=koyu (pasif), 1=sarı (çarlar geçiyor), 2=yeşil (hepsi geçti)
    private static GradientDrawable kanalArka(Context c, int durum) {
        int renk = durum == 2 ? Color.rgb(19, 106, 68)      // yeşil
                 : durum == 1 ? Color.rgb(201, 160, 32)      // sarı/altın (geçiş)
                 : Color.rgb(26, 31, 43);                    // koyu (pasif)
        GradientDrawable g = new GradientDrawable();
        g.setColor(renk);
        g.setCornerRadius(dp(c, 5));
        return g;
    }

    /** Aktif kanal düğmesi: tüm çarlar o kanaldaysa YEŞİL, değilse (geçiş) SARI. */
    static void kanalDurumTazele() {
        if (kanalBtns == null) return;
        Context c = serviceRef.get();
        if (c == null) return;
        TahtaIstemci t = TahtaIstemci.peek();
        int[] chs = (t == null) ? null : t.carKanallari();
        // Dolaşım açıkken 1-4 düğmeleri de o anki hedefi izlesin; değilse son tıklanan.
        int aktif = (t != null && t.dolasimAcik() && t.dolasimHedef() > 0)
                ? t.dolasimHedef() : aktifKanal;
        boolean hepsiAktifte = chs != null && chs.length > 0 && aktif > 0;
        if (hepsiAktifte) {
            for (int ch : chs) {
                if (ch != aktif) { hepsiAktifte = false; break; }
            }
        }
        for (int i = 0; i < kanalBtns.length; i++) {
            TextView b = kanalBtns[i];
            if (b == null) continue;
            int durum = ((i + 1) != aktif) ? 0 : (hepsiAktifte ? 2 : 1);
            b.setBackground(kanalArka(c, durum));
        }
        if (dolasBtn != null) {
            // Yerel istek (toggle) — çekim yarışından etkilenmesin, kalıcı yeşil.
            boolean dol = c.getSharedPreferences("metin7x_settings", 0)
                    .getBoolean("dolasimIstek", false);
            dolasBtn.setBackground(kanalArka(c, dol ? 2 : 0));
        }
    }

    static void refreshCollectButton(Context context) {
        TextView view = miniCollect.get();
        if (view == null) return;
        boolean active = BotSettings.get(context).snapshot().collect;
        view.setText(active ? "Topla\nAçık" : "Topla\nKapalı");
        view.setContentDescription(active ? "Toplama açık, kapat" : "Toplama kapalı, aç");
        GradientDrawable background = new GradientDrawable();
        background.setColor(active ? Color.rgb(19, 106, 68) : Color.rgb(119, 38, 39));
        background.setCornerRadius(dp(context, 5));
        view.setBackground(background);
    }

    private static void compactSize(Context context, int accountCount, boolean hasPanelData) {
        try {
            Field field = context.getClass().getDeclaredField("detayScroll");
            field.setAccessible(true);
            ScrollView scroll = (ScrollView) field.get(context);
            int content = dp(context, (hasPanelData ? 235 : 160) +
                    43 * Math.min(accountCount, 24));
            Field windowField = context.getClass().getDeclaredField("pencere");
            windowField.setAccessible(true);
            android.view.WindowManager.LayoutParams window =
                    (android.view.WindowManager.LayoutParams) windowField.get(context);
            Field gridField = context.getClass().getDeclaredField("kok");
            gridField.setAccessible(true);
            View grid = (View) gridField.get(context);
            int available = context.getResources().getDisplayMetrics().heightPixels -
                    (window == null ? 0 : window.y) -
                    (grid == null || grid.getVisibility() == View.GONE ? 0 : grid.getHeight()) -
                    OverlayWindowSizing.miniHeight(context) - dp(context, 32);
            if (scroll != null) scroll.setLayoutParams(new LinearLayout.LayoutParams(-1,
                    Math.min(content, Math.max(dp(context, 120), available))));
        } catch (ReflectiveOperationException ignored) { }
    }

    private static void expandedSize(Context context) {
        try {
            Method method = context.getClass().getDeclaredMethod("detayYukseklikAyarla");
            method.setAccessible(true);
            method.invoke(context);
        } catch (Exception ignored) { }
    }

    private static void refreshDetailHeight(Context context) {
        try {
            Field opened = context.getClass().getDeclaredField("detayAcik");
            opened.setAccessible(true);
            if (!opened.getBoolean(context)) return;
            JSONObject data = lastData;
            JSONArray accounts = data == null ? null : data.optJSONArray("hesaplar");
            if (BotSettings.get(context).compact())
                compactSize(context, accounts == null ? 0 : accounts.length(), data != null);
            else expandedSize(context);
        } catch (ReflectiveOperationException ignored) { }
    }

    private static void modeButton(Context c, LinearLayout parent, boolean compact) {
        TextView toggle = button(c, compact ? "⚙ Geniş ayarlar" : "Sadece ch izleme",
                Color.rgb(41, 68, 107));
        toggle.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(c, 42)));
        toggle.setOnClickListener(view -> {
            BotSettings.get(c).setCompact(!compact);
            if (!compact && lastData != null) renderCompactIfSelected(c, lastData, parent);
            else if (compact && lastData != null) {
                try {
                    Method method = c.getClass().getDeclaredMethod("detayCiz", JSONObject.class);
                    method.setAccessible(true);
                    method.invoke(c, lastData);
                    expandedSize(c);
                } catch (Exception ignored) { showLocal(c, parent); }
            } else showLocal(c, parent);
        });
        parent.addView(toggle);
    }

    private static void closeButton(Context context, LinearLayout parent) {
        TextView close = button(context, "✕ Küçült", Color.rgb(57, 63, 78));
        close.setTextSize(12);
        close.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 36)));
        close.setOnClickListener(view -> {
            try {
                Method toggle = context.getClass().getDeclaredMethod(
                        "lambda$detayHucre$5", View.class);
                toggle.setAccessible(true);
                toggle.invoke(context, (View) null);
            } catch (Exception error) {
                android.util.Log.w("Metin7x", "Overlay küçültülemedi", error);
            }
        });
        parent.addView(close, 0);
    }

    public static void appendExpanded(Context context, LinearLayout parent) {
        if (BotSettings.get(context).compact()) return;
        expandedSize(context);
        closeButton(context, parent);
        modeButton(context, parent, false);
        takipVeHaritaDugmeleri(context, parent);
        OverlaySettingsPanel.append(context, parent);
    }

    private static void channelCommand(Context service, String command, int idx) {
        try {
            JSONObject request = new JSONObject();
            request.put("komut", command);
            request.put("idx", idx);
            Method method = service.getClass().getDeclaredMethod("komut", JSONObject.class);
            method.setAccessible(true);
            method.invoke(service, request);
        } catch (Exception error) {
            android.util.Log.w("Metin7x", "Ch komutu gönderilemedi", error);
        }
    }

    /**
     * "Beni takip et" (oto-buff) ve "Harita" aç-kapa düğmeleri. Panel verisine
     * BAĞLI DEĞİL; hem kompakt hem geniş modda, panel bağlı olmasa da görünür.
     */
    static void takipVeHaritaDugmeleri(Context context, LinearLayout parent) {
        // Oto-takip: hangi ch'deysem buff'çı da oraya geçsin.
        BotSettings state = BotSettings.get(context);
        boolean follow = state.snapshot().autoBuff;
        TextView followBtn = button(context,
                follow ? "🔗 Beni takip et: AÇIK" : "🔗 Beni takip et: kapalı",
                follow ? Color.rgb(31, 98, 144) : Color.rgb(41, 53, 75));
        followBtn.setTextSize(12);
        followBtn.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        followBtn.setOnClickListener(view -> {
            boolean next = !state.snapshot().autoBuff;
            state.bool("autoBuff", next);
            followBtn.setText(next ? "🔗 Beni takip et: AÇIK" : "🔗 Beni takip et: kapalı");
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(next ? Color.rgb(31, 98, 144) : Color.rgb(41, 53, 75));
            bg.setCornerRadius(dp(context, 7));
            followBtn.setBackground(bg);
        });
        parent.addView(followBtn);

        // Radar/harita aç-kapa
        boolean harita = HaritaOverlay.acikMi();
        TextView mapBtn = button(context,
                harita ? "🗺 Harita: AÇIK" : "🗺 Harita: kapalı",
                harita ? Color.rgb(31, 98, 144) : Color.rgb(41, 53, 75));
        mapBtn.setTextSize(12);
        mapBtn.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        mapBtn.setOnClickListener(view -> {
            HaritaOverlay.degistir(context);
            boolean acik = HaritaOverlay.acikMi();
            mapBtn.setText(acik ? "🗺 Harita: AÇIK" : "🗺 Harita: kapalı");
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(acik ? Color.rgb(31, 98, 144) : Color.rgb(41, 53, 75));
            bg.setCornerRadius(dp(context, 7));
            mapBtn.setBackground(bg);
        });
        parent.addView(mapBtn);

        // Yürüme (joystick) — kalibrasyon + test, Harita'nın hemen altında
        TextView joyBtn = button(context, "🎮 Joystick ayarla", Color.rgb(41, 53, 75));
        joyBtn.setTextSize(12);
        joyBtn.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        joyBtn.setOnClickListener(view -> YurumeAyar.kalibreAc(context));
        parent.addView(joyBtn);

        TextView yuruBtn = button(context, "⬆ Yürü testi", Color.rgb(41, 53, 75));
        yuruBtn.setTextSize(12);
        yuruBtn.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        yuruBtn.setOnClickListener(view -> YurumeAyar.testYuru(context));
        parent.addView(yuruBtn);

        // Rotayı otomatik yürü / dur
        TextView rotaBtn = button(context, "▶ Rotayı yürü", Color.rgb(19, 106, 68));
        rotaBtn.setTextSize(12);
        rotaBtn.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        rotaBtn.setOnClickListener(view -> RotaYuru.basla(HaritaOverlay.aktifYol()));
        parent.addView(rotaBtn);

        TextView rotaDur = button(context, "■ Yürümeyi durdur", Color.rgb(119, 38, 39));
        rotaDur.setTextSize(12);
        rotaDur.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(context, 38)));
        rotaDur.setOnClickListener(view -> RotaYuru.dur());
        parent.addView(rotaDur);

        // (Oto iksir / eşik / iksir-chip bölümü bu APK sürümünde yok — BotSettings
        //  autoPot/potEsik alanları ve Attack7x.canMetni() mevcut olmadığından çıkarıldı.)
    }

    private static void buffCommands(Context context, LinearLayout parent, JSONObject data) {
        if (data == null) return;
        JSONObject buff = data.optJSONObject("buff");
        int current = buff == null ? -1 : buff.optInt("kanal", -1);
        boolean running = buff != null && buff.optBoolean("calisan", false);
        TextView heading = new TextView(context);
        heading.setText(running ? "Buff'çıyı çek (şu an ch" + current + ")" : "Buff'çıyı çek");
        heading.setTextColor(Color.LTGRAY);
        heading.setPadding(dp(context, 8), dp(context, 7), 0, dp(context, 3));
        parent.addView(heading);

        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        int width = Math.min(dp(context, 340),
                context.getResources().getDisplayMetrics().widthPixels - dp(context, 38));
        row.setLayoutParams(new LinearLayout.LayoutParams(Math.max(dp(context, 160), width), dp(context, 40)));
        for (int ch = 1; ch <= 4; ch++) {
            final int channel = ch;
            TextView action = button(context, String.valueOf(ch),
                    running && ch == current ? Color.rgb(31, 98, 144) : Color.rgb(41, 53, 75));
            row.addView(action, new LinearLayout.LayoutParams(0, dp(context, 35), 1));
            action.setOnClickListener(view -> {
                try {
                    JSONObject request = new JSONObject();
                    request.put("komut", "buff_cek");
                    request.put("kanal", channel);
                    Method method = context.getClass().getDeclaredMethod("komut", JSONObject.class);
                    method.setAccessible(true);
                    method.invoke(context, request);
                } catch (Exception error) {
                    android.util.Log.w("Metin7x", "Buff komutu gönderilemedi", error);
                }
            });
        }
        parent.addView(row);
    }

    public static boolean renderCompactIfSelected(Context context, JSONObject data,
                                                   LinearLayout parent) {
        rememberService(context);
        lastData = data;
        if (!BotSettings.get(context).compact()) return false;
        parent.removeAllViews();
        closeButton(context, parent);
        takipVeHaritaDugmeleri(context, parent);   // panel verisi olmasa da görünür
        JSONArray accounts = data == null ? null : data.optJSONArray("hesaplar");
        compactSize(context, accounts == null ? 0 : accounts.length(), data != null);
        buffCommands(context, parent, data);
        modeButton(context, parent, true);
        TextView heading = new TextView(context);
        heading.setText("Kanallar");
        heading.setTextColor(Color.LTGRAY);
        heading.setPadding(dp(context, 8), dp(context, 7), 0, dp(context, 3));
        parent.addView(heading);
        if (accounts != null) for (int i = 0; i < Math.min(accounts.length(), 24); i++) {
            JSONObject account = accounts.optJSONObject(i);
            if (account == null) continue;
            final int index = account.optInt("idx", -1);
            if (index < 0) continue;
            boolean running = account.optBoolean("calisiyor");
            String name = account.optBoolean("tarama") ? "gez " +
                    account.optString("tarama_metin", "") : "ch" + account.optInt("kanal", 0);
            LinearLayout row = new LinearLayout(context);
            row.setGravity(Gravity.CENTER_VERTICAL);
            int width = Math.min(dp(context, 340),
                    context.getResources().getDisplayMetrics().widthPixels - dp(context, 38));
            row.setLayoutParams(new LinearLayout.LayoutParams(Math.max(dp(context, 160), width), dp(context, 43)));
            TextView label = new TextView(context);
            label.setText(name);
            label.setTextColor(running ? Color.rgb(155, 235, 184) : Color.WHITE);
            label.setTextSize(14);
            row.addView(label, new LinearLayout.LayoutParams(0, -2, 1));
            TextView action = button(context, running ? "■ durdur" : "▶ başlat",
                    running ? Color.rgb(119, 38, 39) : Color.rgb(19, 106, 68));
            row.addView(action, new LinearLayout.LayoutParams(dp(context, 105), dp(context, 37)));
            action.setOnClickListener(view -> channelCommand(context,
                    running ? "durdur_hesap" : "baslat_hesap", index));
            parent.addView(row);
        }
        return true;
    }

    public static void showLocal(Context context, LinearLayout parent) {
        rememberService(context);
        parent.removeAllViews();
        if (BotSettings.get(context).compact()) {
            renderCompactIfSelected(context, lastData, parent);
            return;
        }
        expandedSize(context);
        closeButton(context, parent);
        modeButton(context, parent, false);
        takipVeHaritaDugmeleri(context, parent);
        OverlaySettingsPanel.append(context, parent);
        TextView label = new TextView(context);
        label.setText("Kanallar / yerel VPN");
        label.setTextColor(Color.LTGRAY);
        label.setPadding(dp(context, 8), dp(context, 5), 0, 0);
        parent.addView(label);
    }
}
