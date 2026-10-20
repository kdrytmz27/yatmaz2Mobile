package com.abdulkadir.metin7x;

import android.os.Handler;
import android.os.Looper;
import java.util.ArrayList;

/**
 * ROTA YÜRÜ — haritadaki yolu joystick'i sürerek otomatik yürür.
 *
 * Kamera açısı paketlerde yok. Başta İKİ YÖN DENEMESİ (probe) yaparız:
 *   - joystick DOĞU (0°) ~0.9 sn → dünyada ne yöne gittik? (mE)
 *   - joystick GÜNEY (90°) ~0.9 sn → (mS)
 * Bu iki vektör joystick→dünya 2×2 matrisini (M) verir (dönüş+yansıma+ölçek).
 * Hedefe gitmek için D dünya yönünü joystick yönüne M⁻¹ ile çeviririz.
 * (Kamera sabit varsayılır; bocalama/ters yön sorununu bu kökten çözer.)
 */
public final class RotaYuru {
    private static final Handler el = new Handler(Looper.getMainLooper());
    private static volatile boolean calisiyor;

    private static ArrayList<int[]> yol;
    private static int hedefIdx;

    private static double mEx, mEy, mSx, mSy, det;   // M sütunları + determinant
    private static int faz;                          // 0=doğu probe, 1=güney probe, 2=takip
    private static long fazBas;
    private static int[] fazKonum;

    private static final long PROBE_MS = 900;
    private static double VARIS = 500;               // noktaya varış eşiği (dünya birimi) — logla & ayarla
    private static int sayac;

    private RotaYuru() { }

    public static boolean calisiyorMu() { return calisiyor; }

    public static void basla(ArrayList<int[]> waypointler) {
        if (waypointler == null || waypointler.isEmpty()) { log("yol boş"); return; }
        if (!YurumeServisi.hazirMi()) { log("erişilebilirlik servisi KAPALI"); return; }
        int[] j = YurumeServisi.joystick();
        if (j == null || j[2] <= 0) { log("joystick ayarlı DEĞİL (🎮)"); return; }
        yol = new ArrayList<>(waypointler);
        hedefIdx = 0; faz = 0; fazKonum = null;
        calisiyor = true;
        el.post(RotaYuru::adim);
        log("başladı, " + yol.size() + " nokta — önce kalibrasyon (doğu+güney)");
    }

    public static void dur() {
        calisiyor = false;
        YurumeServisi.dur();
        log("durdu");
    }

    private static void adim() {
        if (!calisiyor) { YurumeServisi.dur(); return; }
        int[] P = konum();
        if (P == null) { el.postDelayed(RotaYuru::adim, 300); return; }
        long now = System.currentTimeMillis();

        // ── KALİBRASYON: DOĞU denemesi ──
        if (faz == 0) {
            if (fazKonum == null) { fazKonum = P; fazBas = now; YurumeServisi.yonVer(0f); log("probe DOĞU (joy 0°)"); }
            if (now - fazBas >= PROBE_MS) {
                mEx = P[0] - fazKonum[0]; mEy = P[1] - fazKonum[1];
                log("DOĞU -> dünya dx=" + (int) mEx + " dy=" + (int) mEy);
                faz = 1; fazKonum = null;
            }
            el.postDelayed(RotaYuru::adim, 120); return;
        }
        // ── KALİBRASYON: GÜNEY denemesi ──
        if (faz == 1) {
            if (fazKonum == null) { fazKonum = P; fazBas = now; YurumeServisi.yonVer((float) (Math.PI / 2)); log("probe GÜNEY (joy 90°)"); }
            if (now - fazBas >= PROBE_MS) {
                mSx = P[0] - fazKonum[0]; mSy = P[1] - fazKonum[1];
                det = mEx * mSy - mSx * mEy;
                log("GÜNEY -> dünya dx=" + (int) mSx + " dy=" + (int) mSy + "  det=" + (int) det);
                if (Math.abs(det) < 1) {
                    log("KALİBRASYON BAŞARISIZ (hareket ölçülemedi/düz). AÇIK ALANDA tekrar dene.");
                    dur(); return;
                }
                faz = 2;
            }
            el.postDelayed(RotaYuru::adim, 120); return;
        }

        // ── TAKİP ──
        if (hedefIdx >= yol.size()) { log("rota bitti ✔"); dur(); return; }
        int[] W = yol.get(hedefIdx);
        double dx = W[0] - P[0], dy = W[1] - P[1];
        double mesafe = Math.hypot(dx, dy);
        if (mesafe < VARIS) {
            hedefIdx++;
            log("nokta " + hedefIdx + "/" + yol.size() + " geçildi");
            el.post(RotaYuru::adim); return;
        }
        // joy = M⁻¹ · D
        double jx = (mSy * dx - mSx * dy) / det;
        double jy = (-mEy * dx + mEx * dy) / det;
        double joyAci = Math.atan2(jy, jx);
        if (++sayac % 6 == 0)
            log("hedef#" + hedefIdx + " mesafe=" + (int) mesafe + " joy=" + (int) Math.toDegrees(joyAci) + "°");
        YurumeServisi.yonVer((float) joyAci);
        el.postDelayed(RotaYuru::adim, 120);
    }

    private static int[] konum() {
        try { return WorldBridge.get().benimKonum(); } catch (Throwable t) { return null; }
    }
    private static void log(String s) { android.util.Log.i("Metin7x", "rota-yuru: " + s); }
}
