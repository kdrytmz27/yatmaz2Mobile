package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.text.InputType;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

/**
 * TÜNEL METİN İSTEMCİSİ — Metin İzleyici panelinin (PC) web sunucusundan,
 * cloudflared TÜNEL URL'si üzerinden {@code /api/tahta} verisini çeker: hangi
 * DÜNYA konumlarında, hangi kanallarda metin olduğunu. {@link HaritaOverlay}
 * bu noktaları gerçek haritanın üstüne (oyuncuya göre) işler.
 *
 * Yalnız OKUMA yapar (HTTP GET). Oyun paketlerine dokunmaz; VPN sadece oyunu
 * (addAllowedApplication) yakaladığı için bu istek normal ağdan gider.
 */
final class TahtaIstemci {

    static final class Nokta {
        final int x, y;
        final String ad;
        final int[] kanallar;
        final boolean oyuncu, kesiliyor;
        Nokta(int x, int y, String ad, int[] kanallar, boolean oyuncu, boolean kesiliyor) {
            this.x = x; this.y = y; this.ad = ad; this.kanallar = kanallar;
            this.oyuncu = oyuncu; this.kesiliyor = kesiliyor;
        }
    }

    private static volatile TahtaIstemci instance;
    private static final long YENILEME_MS = 1500L;

    private final Context context;
    private final SharedPreferences pref;
    private volatile boolean calis;
    private volatile List<Nokta> noktalar = new ArrayList<>();
    private volatile int[] carKanallari = new int[0];
    private volatile int[][] carlarKonum = new int[0][];   // {x,y,ch} — izleyici çarları haritaya çiz
    private volatile boolean dolasimAcik;      // panelde otomatik dolaşım açık mı
    private volatile int dolasimHedef;         // dolaşımda şu an geçilen hedef kanal
    private volatile String harita = "";
    private volatile String durum = "bekliyor";
    private Thread th;

    private TahtaIstemci(Context c) {
        this.context = c.getApplicationContext();
        this.pref = context.getSharedPreferences("metin7x_settings", 0);
    }

    static synchronized TahtaIstemci get(Context c) {
        if (instance == null) instance = new TahtaIstemci(c);
        return instance;
    }

    static TahtaIstemci peek() { return instance; }

    static boolean acikMi() { return instance != null && instance.calis; }

    synchronized void baslat() {
        if (calis) return;
        calis = true;
        th = new Thread(this::dongu, "tahta-istemci");
        th.setDaemon(true);
        th.start();
    }

    synchronized void durdur() {
        calis = false;
        if (th != null) { th.interrupt(); th = null; }
    }

    List<Nokta> noktalar() { return noktalar; }
    String durum() { return durum; }
    String harita() { return harita; }

    private void dongu() {
        // Konumu ~400 ms'de bir panele GÖNDER (canlı görünsün), metin tahtasını
        // ~1.6 sn'de bir ÇEK. Tünel gecikmesi kadar hızlı olur.
        int sayac = 0;
        while (calis) {
            try { gonderKonum(); } catch (Throwable e) { /* konum yoksa geç */ }
            if (sayac % 4 == 0) {
                try { cek(); } catch (Throwable e) { durum = "hata: " + e.getClass().getSimpleName(); }
            }
            sayac++;
            try { Thread.sleep(400); } catch (InterruptedException e) { break; }
        }
    }

    private void cek() throws Exception {
        String istek = url("/api/tahta");
        if (istek == null) {
            durum = "URL yok (T'ye uzun bas)";
            noktalar = new ArrayList<>();
            return;
        }
        HttpURLConnection c = (HttpURLConnection) new URL(istek).openConnection();
        c.setConnectTimeout(5000);
        c.setReadTimeout(5000);
        c.setRequestProperty("Accept", "application/json");
        try {
            int kod = c.getResponseCode();
            if (kod != 200) { durum = "HTTP " + kod; return; }
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(
                    new InputStreamReader(c.getInputStream(), "UTF-8"))) {
                String ln;
                while ((ln = r.readLine()) != null) sb.append(ln);
            }
            JSONObject o = new JSONObject(sb.toString());
            harita = o.optString("harita", "");
            JSONArray ms = o.optJSONArray("metinler");
            List<Nokta> yeni = new ArrayList<>();
            if (ms != null) {
                for (int i = 0; i < ms.length(); i++) {
                    JSONObject m = ms.getJSONObject(i);
                    JSONArray ka = m.optJSONArray("kanallar");
                    int[] kl = new int[ka == null ? 0 : ka.length()];
                    for (int j = 0; j < kl.length; j++) kl[j] = ka.getInt(j);
                    yeni.add(new Nokta(m.getInt("x"), m.getInt("y"),
                            m.optString("ad", ""), kl,
                            m.optBoolean("oyuncu", false),
                            m.optBoolean("kesiliyor", false)));
                }
            }
            noktalar = yeni;
            // Tüm canlı çarların kanalı (7x düğmesi sarı=geçiyor / yeşil=hepsi geçti).
            JSONArray ck = o.optJSONArray("car_kanallari");
            int[] chs;
            if (ck != null) {
                chs = new int[ck.length()];
                for (int j = 0; j < chs.length; j++) chs[j] = ck.optInt(j, 0);
            } else {
                JSONArray cs = o.optJSONArray("carlar");
                chs = new int[cs == null ? 0 : cs.length()];
                for (int j = 0; j < chs.length; j++) chs[j] = cs.getJSONObject(j).optInt("ch", 0);
            }
            carKanallari = chs;
            // Çar konumları {x,y,ch,buff} — haritaya çiz (buffçı yeşil), ch yaz.
            JSONArray cx = o.optJSONArray("carlar");
            int[][] ck2 = new int[cx == null ? 0 : cx.length()][4];
            for (int j = 0; j < ck2.length; j++) {
                JSONObject cj = cx.getJSONObject(j);
                ck2[j][0] = cj.optInt("x", 0);
                ck2[j][1] = cj.optInt("y", 0);
                ck2[j][2] = cj.optInt("ch", 0);
                ck2[j][3] = cj.optBoolean("buff", false) ? 1 : 0;
            }
            carlarKonum = ck2;
            dolasimAcik = o.optBoolean("dolasim", false);
            dolasimHedef = o.optInt("dolasim_hedef", 0);
            durum = yeni.size() + " metin";
            // 7x panelindeki kanal düğmelerinin rengini tazele (UI thread).
            new android.os.Handler(android.os.Looper.getMainLooper())
                    .post(Overlay7xControls::kanalDurumTazele);
        } finally {
            c.disconnect();
        }
    }

    /** Çarların o anki kanalları (panelden). 7x düğme rengi için. */
    int[] carKanallari() { return carKanallari; }

    /** İzleyici çarlarının konumu+kanalı {x,y,ch} — haritaya çizmek için. */
    int[][] carlar() { return carlarKonum; }

    /** Panelde otomatik dolaşım açık mı (Dolaş düğmesi rengi için). */
    boolean dolasimAcik() { return dolasimAcik; }

    /** Dolaşımda şu an geçilen hedef kanal (1-4 düğme rengi dolaşımı izlesin). */
    int dolasimHedef() { return dolasimHedef; }

    /** Kayıtlı tünel URL'sinden {@code <taban><path>?k=parola} üretir (yoksa null). */
    private String url(String path) {
        String ham = pref.getString("tunelUrl", "").trim();
        if (ham.isEmpty()) return null;
        if (!ham.startsWith("http")) ham = "https://" + ham;
        try {
            URI u = URI.create(ham);
            String k = "";
            String q = u.getQuery();
            if (q != null) {
                for (String par : q.split("&")) {
                    if (par.startsWith("k=")) k = par.substring(2);
                }
            }
            String url = u.getScheme() + "://" + u.getAuthority() + path;
            if (!k.isEmpty()) url += "?k=" + k;
            return url;
        } catch (Throwable e) {
            return ham;
        }
    }

    /** APK 'Dolaşımı başlat/durdur': panele otomatik kanal dolaşımı komutu. */
    static void dolasimGonder(Context ctx, boolean ac) {
        komutGonder(ctx, "{\"komut\":\"dolasim\",\"ac\":" + ac + "}");
    }

    /** APK 1-4 düğmesi: panele "bu kanala SIRALI geç" komutu gönderir (POST /api/komut). */
    static void kanalGonder(Context ctx, int kanal) {
        komutGonder(ctx, "{\"komut\":\"kanal_sirali\",\"kanal\":" + kanal + "}");
    }

    private static void komutGonder(Context ctx, String govdeStr) {
        final TahtaIstemci t = get(ctx);
        new Thread(() -> {
            try {
                String hedef = t.url("/api/komut");
                if (hedef == null) return;
                byte[] govde = govdeStr.getBytes("UTF-8");
                HttpURLConnection c = (HttpURLConnection) new URL(hedef).openConnection();
                c.setConnectTimeout(4000);
                c.setReadTimeout(4000);
                c.setDoOutput(true);
                c.setRequestMethod("POST");
                c.setRequestProperty("Content-Type", "application/json");
                try {
                    c.getOutputStream().write(govde);
                    c.getResponseCode();
                } finally {
                    c.disconnect();
                }
            } catch (Throwable ignored) { }
        }, "kanal-gonder").start();
    }

    private static java.lang.reflect.Field kanalAlan;

    /** Oyuncunun o anki kanalı — Attack7x porttan çözüp lastKanal'da tutuyor. */
    static int benimKanal() {
        try {
            if (kanalAlan == null) {
                kanalAlan = Attack7x.class.getDeclaredField("lastKanal");
                kanalAlan.setAccessible(true);
            }
            int ch = kanalAlan.getInt(null);
            return ch >= 1 ? ch : 0;
        } catch (Throwable e) {
            return 0;
        }
    }

    /** APK ile bağlı GERÇEK oyuncunun konumunu panele gönderir (POST /api/apk). */
    private void gonderKonum() throws Exception {
        String hedef = url("/api/apk");
        if (hedef == null) return;
        int[] k;
        try { k = WorldBridge.get().benimKonum(); }
        catch (Throwable e) { return; }               // VPN kapalı / köprü yok
        if (k == null) return;                        // konum bilinmiyor
        String harita = "";
        try {
            EngelHarita.Harita h = EngelHarita.al(context).hangi(k[0], k[1]);
            if (h != null) harita = h.ad;
        } catch (Throwable ignored) { }
        int kanal = benimKanal();                     // Attack7x porttan çözüyor
        // Gördüğüm METİNLER (mutlak) — panel bunlara bakıp kestiklerimi tahtadan düşürür.
        StringBuilder mj = new StringBuilder("[");
        try {
            WorldBridge.HaritaVeri v = WorldBridge.get().harita(60000);
            boolean ilk = true;
            for (int[] n : v.noktalar) {
                if (n[0] != 2) continue;              // sadece metin (tip 2)
                if (!ilk) mj.append(',');
                mj.append('[').append(k[0] + n[1]).append(',').append(k[1] + n[2]).append(']');
                ilk = false;
            }
        } catch (Throwable ignored) { }
        mj.append(']');
        byte[] govde = ("{\"x\":" + k[0] + ",\"y\":" + k[1]
                + ",\"harita\":\"" + harita + "\",\"kanal\":" + kanal
                + ",\"metinler\":" + mj + "}").getBytes("UTF-8");
        HttpURLConnection c = (HttpURLConnection) new URL(hedef).openConnection();
        c.setConnectTimeout(4000);
        c.setReadTimeout(4000);
        c.setDoOutput(true);
        c.setRequestMethod("POST");
        c.setRequestProperty("Content-Type", "application/json");
        try {
            c.getOutputStream().write(govde);
            c.getResponseCode();                      // gönderimi tamamla
        } finally {
            c.disconnect();
        }
    }

    // ── URL giriş penceresi (ODAKLANABİLİR overlay; klavye açılır) ──
    static void urlAyarla(Context service) {
        try {
            final WindowManager wm =
                    (WindowManager) service.getSystemService(Context.WINDOW_SERVICE);
            final SharedPreferences pref =
                    service.getSharedPreferences("metin7x_settings", 0);

            LinearLayout kok = new LinearLayout(service);
            kok.setOrientation(LinearLayout.VERTICAL);
            GradientDrawable arka = new GradientDrawable();
            arka.setColor(0xF2101521);
            arka.setCornerRadius(dp(service, 10));
            arka.setStroke(dp(service, 1), 0xFF2f7bd6);
            kok.setBackground(arka);
            int p = dp(service, 12);
            kok.setPadding(p, p, p, p);

            TextView bil = new TextView(service);
            bil.setText("Tünel URL (Metin İzleyici panelinden kopyala):");
            bil.setTextColor(0xFFc9cede);
            bil.setTextSize(12f);
            kok.addView(bil);

            final EditText et = new EditText(service);
            et.setText(pref.getString("tunelUrl", ""));
            et.setHint("https://xxx.trycloudflare.com/?k=parola");
            et.setTextColor(0xFFffffff);
            et.setHintTextColor(0xFF6b7080);
            et.setTextSize(13f);
            et.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
            et.setSingleLine(true);
            kok.addView(et, new LinearLayout.LayoutParams(dp(service, 280), -2));

            TextView ipucu = new TextView(service);
            ipucu.setText("Panelde 'Tünel aç' → URL'yi kopyala. Harita 'T' ile aç/kapa.");
            ipucu.setTextColor(0xFF6b7080);
            ipucu.setTextSize(10f);
            kok.addView(ipucu);

            LinearLayout satir = new LinearLayout(service);
            satir.setOrientation(LinearLayout.HORIZONTAL);
            satir.setGravity(Gravity.END);

            final WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                    WindowManager.LayoutParams.FLAG_DIM_BEHIND,
                    PixelFormat.TRANSLUCENT);
            lp.dimAmount = 0.55f;
            lp.gravity = Gravity.CENTER;

            final LinearLayout pencere = kok;
            Button iptal = new Button(service);
            iptal.setText("İptal");
            iptal.setOnClickListener(v -> {
                try { wm.removeView(pencere); } catch (Throwable ignored) { }
            });
            Button kaydet = new Button(service);
            kaydet.setText("Kaydet");
            kaydet.setOnClickListener(v -> {
                pref.edit().putString("tunelUrl", et.getText().toString().trim())
                        .putBoolean("haritaTunel", true).apply();
                get(service).baslat();
                HaritaOverlay.tunelGosterAc();     // açık haritada anında göster
                try { wm.removeView(pencere); } catch (Throwable ignored) { }
            });
            satir.addView(iptal);
            satir.addView(kaydet);
            kok.addView(satir);

            wm.addView(kok, lp);
            et.requestFocus();
        } catch (Throwable e) {
            Log.w("Metin7x", "Tünel URL penceresi açılamadı", e);
        }
    }

    private static int dp(Context c, float v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }
}
