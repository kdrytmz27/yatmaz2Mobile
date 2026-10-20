package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * Joystick kalibrasyonu (tam-ekran katman: merkez + kenar dokunuşu) ve yürü testi.
 * Kalibrasyon prefs'e yazılır ("jcx","jcy","jr"); YurumeServisi onu kullanır.
 */
public final class YurumeAyar {
    private YurumeAyar() { }

    public static void kalibreAc(final Context ctx) {
        if (!YurumeServisi.hazirMi()) {
            mesaj(ctx, "Önce Ayarlar > Erişilebilirlik'ten servisi AÇ!");
            return;
        }
        final WindowManager wm = (WindowManager) ctx.getSystemService(Context.WINDOW_SERVICE);
        final FrameLayout kat = new FrameLayout(ctx);
        kat.setBackgroundColor(0x55000000);
        final TextView bilgi = new TextView(ctx);
        bilgi.setText("1) JOYSTICK'in TAM ORTASINA dokun");
        bilgi.setTextColor(0xFFFFFFFF);
        bilgi.setTextSize(16f);
        bilgi.setPadding(40, 140, 40, 40);
        kat.addView(bilgi);

        final WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,   // dokunmaları alır, tuş odağı almaz
                PixelFormat.TRANSLUCENT);

        final int[] merkez = new int[2];
        final boolean[] asama = { false };   // false=merkez, true=kenar
        kat.setOnTouchListener(new View.OnTouchListener() {
            @Override public boolean onTouch(View v, MotionEvent e) {
                if (e.getActionMasked() != MotionEvent.ACTION_DOWN) return true;
                int x = (int) e.getRawX(), y = (int) e.getRawY();
                if (!asama[0]) {
                    merkez[0] = x; merkez[1] = y; asama[0] = true;
                    bilgi.setText("2) Joystick'i ittiğin KENARA dokun");
                } else {
                    int r = (int) Math.round(Math.hypot(x - merkez[0], y - merkez[1]));
                    if (r < 20) r = 120;
                    SharedPreferences p = ctx.getSharedPreferences("metin7x_settings", 0);
                    p.edit().putInt("jcx", merkez[0]).putInt("jcy", merkez[1]).putInt("jr", r).apply();
                    YurumeServisi.joystickAyarla(merkez[0], merkez[1], r);
                    try { wm.removeView(kat); } catch (Throwable ignored) { }
                    mesaj(ctx, "Joystick ayarlandı: " + merkez[0] + "," + merkez[1] + " r=" + r);
                }
                return true;
            }
        });
        try { wm.addView(kat, lp); }
        catch (Throwable t) { mesaj(ctx, "Katman açılamadı: " + t.getMessage()); }
    }

    /** 2 sn YUKARI yürüme testi. */
    public static void testYuru(Context ctx) {
        if (!YurumeServisi.hazirMi()) { mesaj(ctx, "Erişilebilirlik servisi KAPALI!"); return; }
        int[] j = YurumeServisi.joystick();
        if (j == null || j[2] <= 0) { mesaj(ctx, "Önce joystick'i ayarla (🎮)!"); return; }
        mesaj(ctx, "2 sn yukarı yürüyor...");
        YurumeServisi.yonVer((float) (-Math.PI / 2));          // yukarı (ekran -y)
        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            @Override public void run() { YurumeServisi.dur(); }
        }, 2000);
    }

    private static void mesaj(Context ctx, String s) {
        try {
            android.widget.Toast.makeText(ctx.getApplicationContext(), s,
                    android.widget.Toast.LENGTH_SHORT).show();
        } catch (Throwable ignored) { }
        android.util.Log.i("Metin7x", "yurume-ayar: " + s);
    }
}
