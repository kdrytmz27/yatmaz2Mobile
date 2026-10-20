package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.github.megatronking.netbare.NetBare;

/**
 * SOLDAN AÇILIR MENÜ — ekranın solunda duran küçük "☰" tutamağı; dokununca
 * modül listesi açılır/kapanır. Her modül (7x, Harita, ...) BAĞIMSIZ aç/kapa
 * edilir ve istenince ekrana getirilir.
 *
 * Kendi başına bir yüzen pencere (HaritaOverlay gibi); OverlayServisi'ni
 * değiştirmeye gerek yok. Overlay7xControls.addRow sonunda SolMenu.ac(context)
 * ile başlatılır.
 *
 * Mevcut modül API'leri:
 *   7x     -> Attack7x.setEnabled(true/false)  (VPN kapalıysa VpnActivity açar)
 *   Harita -> HaritaOverlay.degistir(context)  (radar aç/kapa)
 */
public final class SolMenu {

    private static final int ZEMIN   = 0xE60a0d14;
    private static final int CIZGI   = 0xFF232838;
    private static final int YAZI    = 0xFFc9cede;
    private static final int YESIL   = 0xFF136a44;
    private static final int KIRMIZI = 0xFF772627;
    private static final int KOYU    = 0xFF1a1f2b;
    private static final int VURGU   = 0xFF2f7bd6;

    private static volatile SolMenu instance;

    private final Context context;
    private final WindowManager wm;
    private final WindowManager.LayoutParams pencere;
    private final LinearLayout kok;        // tutamak + panel
    private final LinearLayout panel;      // açılır modül listesi
    private final TextView tutamak;
    private final Handler el = new Handler(Looper.getMainLooper());

    private boolean acikPanel;
    private TextView b7x, bHarita;

    private SolMenu(Context service) {
        this.context = service;
        this.wm = (WindowManager) service.getSystemService(Context.WINDOW_SERVICE);

        kok = new LinearLayout(service);
        kok.setOrientation(LinearLayout.HORIZONTAL);
        kok.setGravity(Gravity.CENTER_VERTICAL);

        // ── tutamak (☰) — her zaman görünür ──
        tutamak = new TextView(service);
        tutamak.setText("☰");
        tutamak.setTextColor(YAZI);
        tutamak.setTextSize(18f);
        tutamak.setGravity(Gravity.CENTER);
        tutamak.setPadding(dp(8), dp(10), dp(8), dp(10));
        GradientDrawable tg = new GradientDrawable();
        tg.setColor(ZEMIN);
        tg.setCornerRadii(new float[]{0, 0, dp(10), dp(10), dp(10), dp(10), 0, 0});
        tg.setStroke(dp(1), CIZGI);
        tutamak.setBackground(tg);
        tutamak.setOnClickListener(v -> panelDegistir());
        tutamakSurukle();

        // ── panel (modüller) — başta gizli ──
        panel = new LinearLayout(service);
        panel.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable pg = new GradientDrawable();
        pg.setColor(ZEMIN);
        pg.setCornerRadius(dp(10));
        pg.setStroke(dp(1), CIZGI);
        panel.setBackground(pg);
        panel.setPadding(dp(6), dp(6), dp(6), dp(6));
        panel.setVisibility(View.GONE);

        baslik("MODÜLLER");
        b7x = modulDugme("7x", v -> {
            boolean acik = Attack7x.isEnabled();
            if (acik) {
                Attack7x.setEnabled(false);
            } else if (NetBare.get().isActive()) {
                Attack7x.setEnabled(true);
            } else {
                // VPN kapalı: izin ekranını aç, otomatik başlat.
                Intent i = new Intent(context, VpnActivity.class);
                i.putExtra(VpnActivity.EXTRA_AUTO_START, true);
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(i);
            }
            el.postDelayed(this::etiketleriTazele, 300);
        });
        bHarita = modulDugme("Harita", v -> {
            HaritaOverlay.degistir(context);
            etiketleriTazele();
        });
        // Tünel URL — tek yerden gir (panelden kopyala). Haritadaki metinler + "BEN"
        // telemetrisi bu URL'yi kullanır; bir kez girince kalıcı saklanır.
        modulDugme("🔗 Tünel URL", v -> TahtaIstemci.urlAyarla(context));
        // Yürüme (joystick) — kalibrasyon + test
        modulDugme("🎮 Joystick ayarla", v -> YurumeAyar.kalibreAc(context));
        modulDugme("⬆ Yürü testi", v -> YurumeAyar.testYuru(context));

        panel.addView(kapatDugme());

        kok.addView(tutamak);
        kok.addView(panel);

        pencere = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT);
        pencere.gravity = Gravity.TOP | Gravity.START;   // SOL
        pencere.x = 0;
        pencere.y = dp(220);
        etiketleriTazele();
    }

    // ── açık/kapa API ─────────────────────────────────────────────────────────
    public static synchronized void ac(Context service) {
        if (instance != null) return;
        try {
            SolMenu m = new SolMenu(service);
            m.wm.addView(m.kok, m.pencere);
            instance = m;
        } catch (Throwable error) {
            android.util.Log.w("Metin7x", "Sol menü açılamadı", error);
        }
    }

    public static synchronized void kapat() {
        SolMenu m = instance;
        instance = null;
        if (m == null) return;
        try { m.wm.removeView(m.kok); } catch (Throwable ignored) { }
    }

    public static boolean acikMi() { return instance != null; }

    // ── panel aç/kapa ──────────────────────────────────────────────────────────
    private void panelDegistir() {
        acikPanel = !acikPanel;
        panel.setVisibility(acikPanel ? View.VISIBLE : View.GONE);
        if (acikPanel) etiketleriTazele();
        try { wm.updateViewLayout(kok, pencere); } catch (Throwable ignored) { }
    }

    private void etiketleriTazele() {
        if (b7x != null) {
            boolean a = Attack7x.isEnabled();
            b7x.setText(a ? "■ 7x DURDUR" : "▶ 7x BAŞLAT");
            renk(b7x, a ? KIRMIZI : YESIL);
        }
        if (bHarita != null) {
            boolean a = HaritaOverlay.acikMi();
            bHarita.setText(a ? "🗺 Harita KAPAT" : "🗺 Harita AÇ");
            renk(bHarita, a ? KIRMIZI : KOYU);
        }
    }

    // ── küçük yapıcılar ────────────────────────────────────────────────────────
    private void baslik(String s) {
        TextView t = new TextView(context);
        t.setText(s);
        t.setTextColor(0xFF6b7080);
        t.setTextSize(10f);
        t.setPadding(dp(4), dp(2), dp(4), dp(4));
        panel.addView(t);
    }

    private TextView modulDugme(String s, View.OnClickListener tik) {
        TextView t = new TextView(context);
        t.setTextColor(Color.WHITE);
        t.setTextSize(13f);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(12), dp(9), dp(12), dp(9));
        t.setOnClickListener(tik);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(150), -2);
        lp.setMargins(0, dp(3), 0, 0);
        t.setLayoutParams(lp);
        renk(t, KOYU);
        panel.addView(t);
        return t;
    }

    private TextView kapatDugme() {
        TextView t = new TextView(context);
        t.setText("✕ Menüyü kapat");
        t.setTextColor(0xFF9aa0b4);
        t.setTextSize(11f);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(8), dp(7), dp(8), dp(4));
        t.setOnClickListener(v -> panelDegistir());
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(150), -2);
        lp.setMargins(0, dp(6), 0, 0);
        t.setLayoutParams(lp);
        return t;
    }

    private void renk(TextView t, int renk) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(renk);
        g.setCornerRadius(dp(7));
        t.setBackground(g);
    }

    private void tutamakSurukle() {
        tutamak.setOnTouchListener(new View.OnTouchListener() {
            int by; float dy; boolean tasindi;
            @Override public boolean onTouch(View view, MotionEvent e) {
                switch (e.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        by = pencere.y; dy = e.getRawY(); tasindi = false;
                        return false;
                    case MotionEvent.ACTION_MOVE:
                        if (Math.abs(e.getRawY() - dy) > dp(6)) tasindi = true;
                        pencere.y = Math.max(0, by + (int) (e.getRawY() - dy));
                        try { wm.updateViewLayout(kok, pencere); } catch (Throwable ignored) { }
                        return tasindi;
                    case MotionEvent.ACTION_UP:
                        if (!tasindi) view.performClick();   // dokunma = aç/kapa
                        return true;
                    default:
                        return false;
                }
            }
        });
    }

    private int dp(float v) {
        return Math.round(v * context.getResources().getDisplayMetrics().density);
    }
}
