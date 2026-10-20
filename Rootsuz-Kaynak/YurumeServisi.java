package com.abdulkadir.metin7x;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.os.Handler;
import android.os.Looper;
import android.view.accessibility.AccessibilityEvent;

/**
 * YURUME SERVISI — oyunun sanal joystick'ini root'suz sürer (dokunma enjekte eder).
 *
 * Çalışma: joystick merkezinden (jcx,jcy) verilen YÖN (radyan, ekran koordinatı:
 * 0=sağ, +π/2=aşağı) açısında jr yarıçaplı bir noktaya parmağı basılı tutar.
 * Sürekli stroke zinciriyle (continueStroke) basılı kalır; yön değişince parmağı
 * joystick halkası üzerinde yeni yöne kaydırır → karakter o yöne yürür (istemci de
 * animasyonu yapar, sunucuyla SENKRON).
 *
 * Kullanıcı Ayarlar > Erişilebilirlik'ten bu servisi açar (cihaz başına bir kez).
 */
public final class YurumeServisi extends AccessibilityService {

    private static volatile YurumeServisi instance;
    private final Handler el = new Handler(Looper.getMainLooper());

    private volatile boolean tutuyor;          // joystick basılı mı
    private volatile float yon;                // hedef yön (radyan)
    private volatile int jcx, jcy, jr;         // joystick merkez + yarıçap (piksel)

    private GestureDescription.StrokeDescription son;   // süren dokunuş (continueStroke zinciri)
    private float curX, curY;                           // parmağın şu anki yeri
    private boolean basildi;                            // parmak inik mi (zincir aktif mi)

    @Override public void onServiceConnected() {
        instance = this;
        try {
            android.content.SharedPreferences p = getSharedPreferences("metin7x_settings", 0);
            jcx = p.getInt("jcx", 0);
            jcy = p.getInt("jcy", 0);
            jr  = p.getInt("jr", 0);
        } catch (Throwable ignored) { }
    }
    @Override public void onAccessibilityEvent(AccessibilityEvent e) { }
    @Override public void onInterrupt() { }
    @Override public void onDestroy() { if (instance == this) instance = null; super.onDestroy(); }

    public static boolean hazirMi() { return instance != null; }

    /** Joystick kalibrasyonu (ekran pikseli: merkez + sürülecek yarıçap). */
    public static void joystickAyarla(int cx, int cy, int r) {
        YurumeServisi s = instance;
        if (s != null) { s.jcx = cx; s.jcy = cy; s.jr = r; }
    }

    public static int[] joystick() {
        YurumeServisi s = instance;
        return s == null ? null : new int[]{s.jcx, s.jcy, s.jr};
    }

    /** Verilen yönde (radyan) yürümeye başla / yönü güncelle. */
    public static void yonVer(float radyan) {
        YurumeServisi s = instance;
        if (s == null || s.jr <= 0) return;
        s.yon = radyan;
        if (!s.tutuyor) {
            s.tutuyor = true;
            s.el.post(s::adim);
        }
    }

    /** Joystick'i bırak (dur). */
    public static void dur() {
        YurumeServisi s = instance;
        if (s != null) s.tutuyor = false;   // bir sonraki adim() willContinue=false ile bırakır
    }

    private void adim() {
        if (!tutuyor || jr <= 0) return;
        float ex = jcx + (float) Math.cos(yon) * jr;
        float ey = jcy + (float) Math.sin(yon) * jr;
        // TEK stroke: offset noktasında ~700 ms basılı tut (YÜRÜYEN kanıtlı sürüm).
        Path p = new Path();
        p.moveTo(ex, ey);
        p.lineTo(ex + 1f, ey);
        GestureDescription g = new GestureDescription.Builder()
                .addStroke(new GestureDescription.StrokeDescription(p, 0, 700))
                .build();
        try {
            dispatchGesture(g, new AccessibilityService.GestureResultCallback() {
                @Override public void onCompleted(GestureDescription d) {
                    if (tutuyor) adim();                        // bitince hemen yeni stroke (yönü günceller)
                }
                @Override public void onCancelled(GestureDescription d) {
                    if (tutuyor) el.postDelayed(YurumeServisi.this::adim, 30);
                }
            }, el);
        } catch (Throwable t) {
            if (tutuyor) el.postDelayed(this::adim, 80);
        }
    }
}
