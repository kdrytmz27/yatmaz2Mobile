package com.abdulkadir.metin7x;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * HARİTA — tambot'un keşif haritasının APK karşılığı. RADAR DEĞİL: oyunun
 * gerçek ARAZİ zeminini (dağ/duvar) {@link EngelHarita} verisinden çizer,
 * üstüne o an görünen metin/mob/oyuncu/eşyaları ve oyuncuyu bindirir.
 *
 * Oyuncu merkezde; +/- ile yakınlaş/uzaklaş (menzil). Arazi verisi yoksa
 * (o harita assets'te yoksa) ızgara + noktalarla (radar gibi) gösterir.
 */
public final class HaritaOverlay {

    private static final int METIN  = 0xFFff4d4d;   // kırmızı (tambot canlı metin)
    private static final int MOB    = 0xFF8a90a0;   // gri
    private static final int OYUNCU = 0xFFaa3cff;   // mor
    private static final int ESYA   = 0xFFdfe4f0;   // beyaz
    private static final int YANG   = 0xFFffd23c;   // altın
    private static final int BEN    = 0xFFffffff;   // beyaz (merkez = sen)
    private static final int ZEMIN  = 0xE60a0d14;
    private static final int CIZGI  = 0xFF232838;

    private static volatile HaritaOverlay instance;

    private final Context context;
    private final WindowManager wm;
    private final WindowManager.LayoutParams pencere;
    private final LinearLayout kok;
    private final AraziGorunum gorunum;
    private final SharedPreferences pref;
    private final Handler el = new Handler(Looper.getMainLooper());
    private boolean calisiyor;
    private int menzil;                 // görünür yarıçap (dünya birimi)
    private boolean isimGoster;         // metin/canavar/oyuncu adlarını yaz
    private boolean tunelGoster;        // panel tünelinden gelen metin noktaları
    private boolean tunelCar;           // panelden gelen çar (oyuncu) noktaları aç/kapa
    private float tumZoom = 1f;         // tüm harita görünümünde yakınlaştırma (1 = tam sığdır)
    // ── Rota (waypoint) — haritaya tıklayarak oluşturulur, çizgi olarak çizilir ──
    private final java.util.ArrayList<int[]> rota = new java.util.ArrayList<>();  // {dünyaX, dünyaY}
    private final java.util.ArrayList<int[]> rotaYol = new java.util.ArrayList<>(); // A* ile engelsiz yol
    private boolean rotaModu;           // açıkken haritaya dokunma = waypoint ekler (pan yerine)

    /** Waypoint'ler arası engelden kaçan yolu (A*) hesaplar; bulunamazsa düz çizgi. */
    private void rotaYoluHesapla() {
        rotaYol.clear();
        if (rota.size() < 2) return;
        EngelHarita.Harita h = null;
        try { h = EngelHarita.al(context).hangi(rota.get(0)[0], rota.get(0)[1]); }
        catch (Throwable ignored) { }
        for (int i = 0; i + 1 < rota.size(); i++) {
            int[] a = rota.get(i), b = rota.get(i + 1);
            java.util.List<int[]> seg = null;
            if (h != null) { try { seg = h.yol(a[0], a[1], b[0], b[1]); } catch (Throwable ignored) { } }
            if (seg == null || seg.isEmpty()) {           // yol yok: düz
                if (rotaYol.isEmpty()) rotaYol.add(a);
                rotaYol.add(b);
            } else {
                int bas = rotaYol.isEmpty() ? 0 : 1;      // ortak ucu tekrarlama
                for (int k = bas; k < seg.size(); k++) rotaYol.add(seg.get(k));
            }
        }
    }
    private int haritaBoy;              // harita penceresinin ekran boyu (px) — ayarlanabilir

    private static final int MIN_MENZIL = 1000;
    private static final int MAX_MENZIL = 60000;

    // Akıcılık: tambot/proxy ~150 ms'de güncelliyordu. 100 ms (~10 fps) daha
    // akıcı; veri (konum/metinler) paket geldikçe (~155 ms) tazelendiği için
    // daha hızlısı ekstra pürüzsüzlük getirmez, sadece CPU yakar.
    private static final long YENILEME_MS = 100L;
    private final Runnable dongu = new Runnable() {
        @Override public void run() {
            if (!calisiyor) return;
            gorunum.invalidate();
            el.postDelayed(this, YENILEME_MS);
        }
    };

    private HaritaOverlay(Context service) {
        this.context = service;
        this.wm = (WindowManager) service.getSystemService(Context.WINDOW_SERVICE);
        this.pref = service.getSharedPreferences("metin7x_settings", 0);
        this.menzil = clampMenzil(pref.getInt("haritaMenzil", 8000));
        this.isimGoster = pref.getBoolean("haritaIsim", true);
        this.tunelGoster = pref.getBoolean("haritaTunel", true);   // VARSAYILAN açık: panel metinleri gelsin
        this.tunelCar = pref.getBoolean("haritaCar", true);        // panel çarları (oyuncu) göster
        this.tumZoom = clampZoom(pref.getFloat("haritaZoom", 1f));
        this.haritaBoy = clampBoy(pref.getInt("haritaBoy", dp(230)));

        kok = new LinearLayout(service);
        kok.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable arka = new GradientDrawable();
        arka.setColor(ZEMIN);
        arka.setCornerRadius(dp(10));
        arka.setStroke(dp(1), CIZGI);
        kok.setBackground(arka);
        int p = dp(4);
        kok.setPadding(p, p, p, p);

        kok.addView(baslikCubugu());

        gorunum = new AraziGorunum(service);
        kok.addView(gorunum, new LinearLayout.LayoutParams(haritaBoy, haritaBoy));
        // Haritanın GÖVDESİNDEN de sürüklenebilsin (sadece başlıktan değil).
        gorunum.setOnTouchListener(new View.OnTouchListener() {
            int bx, by; float dx, dy; boolean tasindi;
            @Override public boolean onTouch(View view, MotionEvent e) {
                switch (e.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        bx = pencere.x; by = pencere.y;
                        dx = e.getRawX(); dy = e.getRawY();
                        tasindi = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        if (Math.abs(e.getRawX() - dx) + Math.abs(e.getRawY() - dy) > dp(8))
                            tasindi = true;
                        if (tasindi) {
                            pencere.x = Math.max(0, bx - (int) (e.getRawX() - dx));
                            pencere.y = Math.max(0, by + (int) (e.getRawY() - dy));
                            try { wm.updateViewLayout(kok, pencere); } catch (Throwable ignored) { }
                        }
                        return true;
                    case MotionEvent.ACTION_UP:
                        // Rota modunda kısa dokunma (sürükleme değil) = waypoint ekle.
                        if (!tasindi && rotaModu) gorunum.rotaNoktaEkle(e.getX(), e.getY());
                        return true;
                    default:
                        return false;
                }
            }
        });

        pencere = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT);
        pencere.gravity = Gravity.TOP | Gravity.END;
        pencere.x = dp(6);
        pencere.y = dp(150);
    }

    // ── açık/kapa API (SolMenu / Overlay7xControls'tan) ──
    public static synchronized void ac(Context service) {
        if (instance != null) return;
        try {
            HaritaOverlay h = new HaritaOverlay(service);
            h.wm.addView(h.kok, h.pencere);
            h.calisiyor = true;
            h.el.post(h.dongu);
            instance = h;
            // URL ayarlıysa istemciyi başlat: konumu panele gönderir (tünel metni
            // kapalı olsa bile), tünel metni açıksa ayrıca onları da çeker.
            if (!h.pref.getString("tunelUrl", "").trim().isEmpty())
                TahtaIstemci.get(service).baslat();
        } catch (Throwable error) {
            android.util.Log.w("Metin7x", "Harita açılamadı", error);
        }
    }

    public static synchronized void kapat() {
        HaritaOverlay h = instance;
        instance = null;
        if (h == null) return;
        h.calisiyor = false;
        h.el.removeCallbacks(h.dongu);
        try { h.wm.removeView(h.kok); } catch (Throwable ignored) { }
        // NOT: TahtaIstemci'yi DURDURMUYORUZ — VPN açıkken konum gönderimi
        // (gerçek karakterin panelde görünmesi) harita kapalıyken de sürsün.
    }

    public static boolean acikMi() { return instance != null; }

    /** Rota takibi için aktif yol (A* yolu; yoksa ham waypoint'ler) — dünya noktaları kopyası. */
    public static java.util.ArrayList<int[]> aktifYol() {
        HaritaOverlay h = instance;
        java.util.ArrayList<int[]> kopya = new java.util.ArrayList<>();
        if (h == null) return kopya;
        java.util.ArrayList<int[]> kaynak = h.rotaYol.isEmpty() ? h.rota : h.rotaYol;
        for (int[] p : kaynak) kopya.add(new int[]{p[0], p[1]});
        return kopya;
    }

    /** URL kaydedilince çağrılır: açık haritada tünel metinlerini anında aç. */
    public static void tunelGosterAc() {
        HaritaOverlay h = instance;
        if (h != null) {
            h.tunelGoster = true;
            h.gorunum.invalidate();
        }
    }

    public static synchronized void degistir(Context service) {
        if (acikMi()) kapat(); else ac(service);
    }

    // ── başlık: Harita  −  +  ✕ ──
    private LinearLayout baslikCubugu() {
        LinearLayout satir = new LinearLayout(context);
        satir.setOrientation(LinearLayout.HORIZONTAL);
        satir.setGravity(Gravity.CENTER_VERTICAL);

        TextView baslik = new TextView(context);
        baslik.setText("Harita");
        baslik.setTextColor(0xFFc9cede);
        baslik.setTextSize(11f);
        baslik.setPadding(dp(4), 0, dp(4), 0);
        satir.addView(baslik, new LinearLayout.LayoutParams(0, -2, 1f));

        final TextView[] ib = new TextView[1];
        ib[0] = kucukDugme("A", v -> {
            isimGoster = !isimGoster;
            pref.edit().putBoolean("haritaIsim", isimGoster).apply();
            ib[0].setTextColor(isimGoster ? 0xFF37d67a : 0xFF6b7080);
            gorunum.invalidate();
        });
        ib[0].setTextColor(isimGoster ? 0xFF37d67a : 0xFF6b7080);
        satir.addView(ib[0]);

        // T: panel tünelinden metin noktaları (aç/kapa). Uzun bas → URL gir.
        final TextView[] tb = new TextView[1];
        tb[0] = kucukDugme("T", v -> {
            String url = pref.getString("tunelUrl", "");
            if (url.trim().isEmpty()) {
                TahtaIstemci.urlAyarla(context);        // önce URL gerekir
                return;
            }
            tunelGoster = !tunelGoster;
            pref.edit().putBoolean("haritaTunel", tunelGoster).apply();
            if (tunelGoster) TahtaIstemci.get(context).baslat();
            tb[0].setTextColor(tunelGoster ? 0xFF35c2ff : 0xFF6b7080);
            gorunum.invalidate();
        });
        tb[0].setTextColor(tunelGoster ? 0xFF35c2ff : 0xFF6b7080);
        tb[0].setOnLongClickListener(v -> { TahtaIstemci.urlAyarla(context); return true; });
        satir.addView(tb[0]);

        // Ç: panelden gelen çar (oyuncu) noktalarını aç/kapa
        final TextView[] cb = new TextView[1];
        cb[0] = kucukDugme("Ç", v -> {
            tunelCar = !tunelCar;
            pref.edit().putBoolean("haritaCar", tunelCar).apply();
            cb[0].setTextColor(tunelCar ? 0xFFb06bff : 0xFF6b7080);
            gorunum.invalidate();
        });
        cb[0].setTextColor(tunelCar ? 0xFFb06bff : 0xFF6b7080);
        satir.addView(cb[0]);

        // ⊟ / ⊞ : PENCERE boyunu küçült / büyüt (ekranı az/çok kaplasın).
        satir.addView(kucukDugme("⊟", v -> setBoy(Math.round(haritaBoy / 1.25f))));
        satir.addView(kucukDugme("⊞", v -> setBoy(Math.round(haritaBoy * 1.25f))));
        // − / ＋ : harita İÇERİĞİNİ (zoom) oyuncuya odaklı uzaklaş/yakınlaş.
        satir.addView(kucukDugme("－", v -> setZoom(tumZoom / 1.4f)));
        satir.addView(kucukDugme("＋", v -> setZoom(tumZoom * 1.4f)));
        // 🧭 : Rota modu aç/kapa — açıkken haritaya dokunma pan yerine waypoint ekler.
        final TextView[] rb = new TextView[1];
        rb[0] = kucukDugme("🧭", v -> {
            rotaModu = !rotaModu;
            rb[0].setTextColor(rotaModu ? 0xFF37d67a : 0xFF6b7080);
            gorunum.invalidate();
        });
        rb[0].setTextColor(rotaModu ? 0xFF37d67a : 0xFF6b7080);
        satir.addView(rb[0]);
        // ⌫ : son waypoint'i sil (UZUN BAS = rotayı tümüyle temizle).
        TextView rbx = kucukDugme("⌫", v -> {
            if (!rota.isEmpty()) rota.remove(rota.size() - 1);
            rotaYoluHesapla();
            gorunum.invalidate();
        });
        rbx.setOnLongClickListener(v -> { rota.clear(); rotaYol.clear(); gorunum.invalidate(); return true; });
        satir.addView(rbx);
        // 🗑 : tüm rotayı temizle (görünür buton)
        satir.addView(kucukDugme("🗑", v -> {
            rota.clear(); rotaYol.clear(); gorunum.invalidate();
        }));
        satir.addView(kucukDugme("✕", v -> kapat()));

        satir.setOnTouchListener(new View.OnTouchListener() {
            int bx, by; float dx, dy;
            @Override public boolean onTouch(View view, MotionEvent e) {
                switch (e.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        bx = pencere.x; by = pencere.y;
                        dx = e.getRawX(); dy = e.getRawY();
                        return false;
                    case MotionEvent.ACTION_MOVE:
                        pencere.x = Math.max(0, bx - (int) (e.getRawX() - dx));
                        pencere.y = Math.max(0, by + (int) (e.getRawY() - dy));
                        try { wm.updateViewLayout(kok, pencere); } catch (Throwable ignored) { }
                        return true;
                    default:
                        return false;
                }
            }
        });
        return satir;
    }

    private TextView kucukDugme(String yazi, View.OnClickListener tik) {
        TextView t = new TextView(context);
        t.setText(yazi);
        t.setTextColor(0xFFc9cede);
        t.setTextSize(12f);
        t.setGravity(Gravity.CENTER);
        t.setMinWidth(dp(26));
        int px = dp(4), py = dp(2);
        t.setPadding(px, py, px, py);
        GradientDrawable g = new GradientDrawable();
        g.setColor(0xFF1a1f2b);
        g.setCornerRadius(dp(5));
        t.setBackground(g);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.setMargins(dp(2), 0, 0, 0);
        t.setLayoutParams(lp);
        t.setOnClickListener(tik);
        return t;
    }

    private void setMenzil(int yeni) {
        menzil = clampMenzil(yeni);
        pref.edit().putInt("haritaMenzil", menzil).apply();
        gorunum.invalidate();
    }

    private static int clampMenzil(int v) {
        return Math.max(MIN_MENZIL, Math.min(MAX_MENZIL, v));
    }

    private void setZoom(float yeni) {
        tumZoom = clampZoom(yeni);
        pref.edit().putFloat("haritaZoom", tumZoom).apply();
        gorunum.invalidate();
    }

    private static float clampZoom(float v) {
        if (Float.isNaN(v) || v < 1f) return 1f;      // 1 = tüm harita (boşluksuz)
        return Math.min(v, 8f);                        // en çok 8x yakınlaş
    }

    private int clampBoy(int px) {
        return Math.max(dp(120), Math.min(dp(480), px));   // pencere boyu sınırları
    }

    private void setBoy(int yeni) {
        haritaBoy = clampBoy(yeni);
        pref.edit().putInt("haritaBoy", haritaBoy).apply();
        android.view.ViewGroup.LayoutParams lp = gorunum.getLayoutParams();
        lp.width = haritaBoy; lp.height = haritaBoy;
        gorunum.setLayoutParams(lp);
        try { wm.updateViewLayout(kok, pencere); } catch (Throwable ignored) { }
        gorunum.invalidate();
    }

    // ── arazi + canlı çizim ──
    private final class AraziGorunum extends View {
        private final Paint boya = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint yazi = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint bmpBoya = new Paint(Paint.FILTER_BITMAP_FLAG);
        // Son çizim dönüşümü: ekran(vx,vy) -> dünya = (son*)'dan geri hesaplanır.
        private float sonCx, sonCy, sonScale = 1f;
        private int sonPx, sonPy;
        private boolean sonGecerli;

        /** Ekran dokunuşunu (view-yerel) dünya koordinatına çevirip rotaya ekler. */
        void rotaNoktaEkle(float vx, float vy) {
            if (!sonGecerli || sonScale == 0f) return;
            int wx = sonPx + Math.round((vx - sonCx) / sonScale);
            int wy = sonPy + Math.round((vy - sonCy) / sonScale);
            rota.add(new int[]{wx, wy});
            rotaYoluHesapla();
            android.util.Log.i("Metin7x", "rota: waypoint " + rota.size() + " -> " + wx + "," + wy);
            invalidate();
        }

        AraziGorunum(Context c) {
            super(c);
            yazi.setTextSize(dp(9));
        }

        @Override protected void onDraw(Canvas canvas) {
            int w = getWidth(), h = getHeight();
            float cx = w / 2f, cy = h / 2f;
            float pad = dp(4);
            float R = Math.min(cx, cy) - pad;
            // Pencere boyuna göre yazı/işaret ölçeği (ref 230dp). Küçülünce her şey küçülür.
            float uiO = Math.max(0.45f, Math.min(1.4f, w / (float) dp(230)));

            int[] konum = null;
            try { konum = WorldBridge.get().benimKonum(); } catch (Throwable ignored) { }
            if (konum == null) {
                yazi.setColor(0xFF6b7080);
                yazi.setTextSize(dp(9) * uiO);
                yazi.setTextAlign(Paint.Align.CENTER);
                canvas.drawText("VPN kapalı / konum yok", cx, cy, yazi);
                yazi.setTextAlign(Paint.Align.LEFT);
                return;
            }
            int px = konum[0], py = konum[1];

            // 1) ARAZİ zemini — hangi harita?
            EngelHarita.Harita harita = null;
            try { harita = EngelHarita.al(context).hangi(px, py); } catch (Throwable ignored) { }
            float scale;                               // dünya birimi -> piksel
            boolean araziVar = false;

            if (harita != null) {
                // HER ZAMAN: oynanabilir alanı BOŞLUKSUZ sığdır (ölü bölge kırpılır).
                // tumZoom=1 → tüm harita; − / ＋ oyuncuya odaklı yakınlaş/uzaklaş.
                // Yakınlaşınca görüntü içerik kenarına kelepçelenir (kenarda boşluk olmaz).
                try {
                    Bitmap zemin = harita.zemin();     // minCx..maxCy burada hesaplanır
                    int hc = harita.hucre;
                    int mnx = harita.minCx, mny = harita.minCy, mxx = harita.maxCx, myy = harita.maxCy;
                    float ww = (mxx - mnx + 1) * (float) hc, wh = (myy - mny + 1) * (float) hc;
                    float olcek0 = Math.min((w - 2f * pad) / ww, (h - 2f * pad) / wh);
                    float olcek = olcek0 * tumZoom;
                    float wx0 = harita.tabanX + mnx * hc, wy0 = harita.tabanY + mny * hc;
                    float cpw = ww * olcek, cph = wh * olcek;   // içerik piksel boyutu
                    // içerik ekrandan küçükse ortala; büyükse oyuncuyu merkeze al + kelepçele
                    float dx0 = (cpw <= w) ? (w - cpw) / 2f
                            : Math.max(w - cpw, Math.min(0f, w / 2f - (px - wx0) * olcek));
                    float dy0 = (cph <= h) ? (h - cph) / 2f
                            : Math.max(h - cph, Math.min(0f, h / 2f - (py - wy0) * olcek));
                    canvas.drawBitmap(zemin,
                            new Rect(mnx, mny, mxx + 1, myy + 1),
                            new RectF(dx0, dy0, dx0 + cpw, dy0 + cph), bmpBoya);
                    scale = olcek;
                    cx = dx0 + (px - wx0) * olcek;      // oyuncunun gerçek ekran konumu
                    cy = dy0 + (py - wy0) * olcek;
                    araziVar = true;
                } catch (Throwable ignored) {
                    scale = R / (float) menzil;
                }
            } else {
                scale = R / (float) menzil;            // arazi verisi yok: basit plot
            }

            if (!araziVar) {
                // arazi verisi yok: hafif ızgara (yine de metinler çizilir)
                boya.setStyle(Paint.Style.STROKE);
                boya.setStrokeWidth(dp(1));
                boya.setColor(CIZGI);
                canvas.drawCircle(cx, cy, R, boya);
                canvas.drawLine(cx, cy - R, cx, cy + R, boya);
                canvas.drawLine(cx - R, cy, cx + R, cy, boya);
            }

            // Dönüşümü sakla: ekran(vx,vy) <-> dünya. Dokunma ters çevirir, rota çizer.
            sonCx = cx; sonCy = cy; sonScale = scale; sonPx = px; sonPy = py; sonGecerli = true;

            // 2) CANLI noktalar (WorldBridge.harita -> oyuncuya göre dx,dy)
            WorldBridge.HaritaVeri veri = null;
            try { veri = WorldBridge.get().harita(MAX_MENZIL); } catch (Throwable ignored) { }
            int metinSay = 0;
            float puls = 0.5f + 0.5f * (float) Math.sin(System.currentTimeMillis() / 250.0);
            if (veri != null && veri.var) {
                yazi.setTextAlign(Paint.Align.LEFT);
                float ts = dp(6) * uiO;              // daha küçük/kibar etiket
                for (int i = 0; i < veri.noktalar.size(); i++) {
                    int[] n = veri.noktalar.get(i);
                    int tur = n[0];
                    float sx = cx + n[1] * scale;           // +y AŞAĞI (arazi ile aynı)
                    float sy = cy + n[2] * scale;
                    if (sx < 0 || sy < 0 || sx > w || sy > h) continue;
                    int renk; float yaricap;
                    switch (tur) {
                        case 2:  renk = METIN;  yaricap = dp(5f) * uiO;   metinSay++; break;
                        case 6:  renk = OYUNCU; yaricap = dp(3f) * uiO;   break;
                        case 10: renk = YANG;   yaricap = dp(2.5f) * uiO; break;
                        case 9:  renk = ESYA;   yaricap = dp(2f) * uiO;   break;
                        default: renk = MOB;    yaricap = dp(2f) * uiO;   break;
                    }
                    // METİN: büyük + yanıp sönen halka (göz önünde olsun)
                    if (tur == 2) {
                        boya.setStyle(Paint.Style.STROKE);
                        boya.setStrokeWidth(dp(2) * uiO);
                        int a = (int) (80 + 140 * puls);
                        boya.setColor((a << 24) | 0x00FF4D4D);
                        canvas.drawCircle(sx, sy, yaricap + (dp(3) + dp(5) * puls) * uiO, boya);
                    }
                    boya.setStyle(Paint.Style.FILL);
                    boya.setColor(renk);
                    canvas.drawCircle(sx, sy, yaricap, boya);
                    boya.setStyle(Paint.Style.STROKE);
                    boya.setStrokeWidth(dp(1));
                    boya.setColor(0xFF000000);
                    canvas.drawCircle(sx, sy, yaricap, boya);
                    boya.setStyle(Paint.Style.FILL);
                    // İSİM: metin, canavar ve oyuncuya adını yaz (eşya hariç).
                    String ad = (i < veri.adlar.size()) ? veri.adlar.get(i) : "";
                    if (isimGoster && ad != null && !ad.isEmpty()
                            && (tur == 2 || tur == 0 || tur == 6)) {
                        yazi.setTextSize(ts);
                        float tx = sx + yaricap + dp(2), ty = sy + ts / 3f;
                        // güçlü siyah kontur (4 yöne) → her zemin üstünde okunur
                        yazi.setColor(0xFF000000);
                        canvas.drawText(ad, tx + 1, ty, yazi);
                        canvas.drawText(ad, tx - 1, ty, yazi);
                        canvas.drawText(ad, tx, ty + 1, yazi);
                        canvas.drawText(ad, tx, ty - 1, yazi);
                        yazi.setColor(tur == 2 ? 0xFFff6b6b      // metin: kırmızı
                                    : tur == 6 ? 0xFFc08cff      // oyuncu: mor
                                    : 0xFFeaf0f8);               // canavar: beyaz
                        canvas.drawText(ad, tx, ty, yazi);
                    }
                }
            }

            // 2b) TÜNEL metin noktaları (panelden): bilinen doğma yerleri, ch etiketli.
            //     Mutlak dünya konumu -> oyuncuya göre (arazi ile aynı ölçek).
            if (tunelGoster) {
                TahtaIstemci ti = TahtaIstemci.peek();
                if (ti != null) {
                    float ts2 = dp(6) * uiO;          // daha küçük/kibar etiket
                    float r0 = dp(3f) * uiO;
                    for (TahtaIstemci.Nokta n : ti.noktalar()) {
                        float sx = cx + (n.x - px) * scale;
                        float sy = cy + (n.y - py) * scale;
                        if (sx < 0 || sy < 0 || sx > w || sy > h) continue;
                        int renk = n.oyuncu ? 0xFFffb020 : 0xFF35c2ff;  // oyuncu varsa altın
                        // dış halka (canlı metinden ayrışsın: camgöbeği)
                        boya.setStyle(Paint.Style.STROKE);
                        boya.setStrokeWidth(dp(2) * uiO);
                        boya.setColor((0x66 << 24) | (renk & 0x00FFFFFF));
                        canvas.drawCircle(sx, sy, dp(6) * uiO, boya);
                        boya.setStyle(Paint.Style.FILL);
                        boya.setColor(renk);
                        canvas.drawCircle(sx, sy, r0, boya);
                        boya.setStyle(Paint.Style.STROKE);
                        boya.setStrokeWidth(dp(1));
                        boya.setColor(0xFF00121f);
                        canvas.drawCircle(sx, sy, r0, boya);
                        boya.setStyle(Paint.Style.FILL);
                        // ch etiketi HER ZAMAN yazılır (isim ayarından bağımsız) —
                        // tünel metninin hangi kanal(lar)da olduğu asıl bilgidir.
                        StringBuilder sb = new StringBuilder();
                        for (int ci = 0; ci < n.kanallar.length; ci++) {
                            if (ci > 0) sb.append(',');
                            sb.append("ch").append(n.kanallar[ci]);
                        }
                        if (n.kesiliyor) sb.insert(0, "⚔ ");
                        if (n.oyuncu) sb.append(" 👤");
                        if (isimGoster && n.ad != null && !n.ad.isEmpty()) {
                            sb.append("  ").append(n.ad);     // isim açıksa metin adı da
                        }
                        String et = sb.toString();
                        yazi.setTextSize(ts2);
                        float tx = sx + dp(6), ty = sy - dp(3);
                        yazi.setColor(0xFF000000);
                        canvas.drawText(et, tx + 1, ty, yazi);
                        canvas.drawText(et, tx - 1, ty, yazi);
                        canvas.drawText(et, tx, ty + 1, yazi);
                        canvas.drawText(et, tx, ty - 1, yazi);
                        yazi.setColor(0xFF9fe4ff);
                        canvas.drawText(et, tx, ty, yazi);
                    }
                    // İZLEYİCİ ÇARLARI: mor nokta + "chN" (Ç ile aç/kapa)
                    for (int[] car : (tunelCar ? ti.carlar() : new int[0][])) {
                        float sx = cx + (car[0] - px) * scale;
                        float sy = cy + (car[1] - py) * scale;
                        if (sx < 0 || sy < 0 || sx > w || sy > h) continue;
                        boolean buffcu = car.length > 3 && car[3] == 1;
                        boya.setStyle(Paint.Style.FILL);
                        boya.setColor(buffcu ? 0xFF37d67a : 0xFFb06bff);  // buffçı=yeşil, izleyici=mor
                        canvas.drawCircle(sx, sy, r0, boya);
                        boya.setStyle(Paint.Style.STROKE);
                        boya.setStrokeWidth(dp(1));
                        boya.setColor(0xFF000000);
                        canvas.drawCircle(sx, sy, r0, boya);
                        boya.setStyle(Paint.Style.FILL);
                        String cet = (buffcu ? "🛡ch" : "ch") + car[2];
                        yazi.setTextSize(ts2);
                        float ctx = sx + dp(5) * uiO, cty = sy + dp(3) * uiO;
                        yazi.setColor(0xFF000000);
                        canvas.drawText(cet, ctx + 1, cty, yazi);
                        canvas.drawText(cet, ctx - 1, cty, yazi);
                        canvas.drawText(cet, ctx, cty + 1, yazi);
                        canvas.drawText(cet, ctx, cty - 1, yazi);
                        yazi.setColor(0xFFd9b8ff);
                        canvas.drawText(cet, ctx, cty, yazi);
                    }
                }
            }

            // 2d) ROTA — haritaya tıklayarak oluşturulan waypoint çizgisi (yeşil)
            if (!rota.isEmpty()) {
                java.util.ArrayList<int[]> cizgi = rotaYol.isEmpty() ? rota : rotaYol;
                boya.setStyle(Paint.Style.STROKE);
                boya.setStrokeWidth(dp(1.5f) * uiO);
                boya.setColor(0xFF20E0B0);
                float prx = 0, pry = 0; boolean ilk = true;
                for (int[] wp : cizgi) {
                    float sx = cx + (wp[0] - px) * scale;
                    float sy = cy + (wp[1] - py) * scale;
                    if (!ilk) canvas.drawLine(prx, pry, sx, sy, boya);
                    prx = sx; pry = sy; ilk = false;
                }
                yazi.setTextAlign(Paint.Align.CENTER);
                float ts = dp(6) * uiO;
                for (int i = 0; i < rota.size(); i++) {
                    int[] wp = rota.get(i);
                    float sx = cx + (wp[0] - px) * scale;
                    float sy = cy + (wp[1] - py) * scale;
                    boya.setStyle(Paint.Style.FILL);
                    boya.setColor(0xFF20E0B0);
                    canvas.drawCircle(sx, sy, dp(2.5f) * uiO, boya);
                    boya.setStyle(Paint.Style.STROKE);
                    boya.setStrokeWidth(dp(1));
                    boya.setColor(0xFF00140f);
                    canvas.drawCircle(sx, sy, dp(2.5f) * uiO, boya);
                    yazi.setTextSize(ts);
                    yazi.setColor(0xFF000000);
                    canvas.drawText(String.valueOf(i + 1), sx, sy - dp(3), yazi);
                    yazi.setColor(0xFFaff7e6);
                    canvas.drawText(String.valueOf(i + 1), sx, sy - dp(3) - 1, yazi);
                }
                yazi.setTextAlign(Paint.Align.LEFT);
                boya.setStyle(Paint.Style.FILL);
            }

            // 3) merkez = ben
            float rben = dp(3.5f) * uiO;
            boya.setStyle(Paint.Style.FILL);
            boya.setColor(BEN);
            canvas.drawCircle(cx, cy, rben, boya);
            boya.setStyle(Paint.Style.STROKE);
            boya.setStrokeWidth(dp(1.5f));
            boya.setColor(0xFF000000);
            canvas.drawCircle(cx, cy, rben, boya);

            // 4) alt bilgi
            yazi.setColor(0xFF6b7080);
            yazi.setTextSize(dp(6) * uiO);
            yazi.setTextAlign(Paint.Align.LEFT);
            canvas.drawText((harita != null ? harita.ad : "arazi yok")
                            + (tumZoom > 1.01f ? String.format(java.util.Locale.US, "  %.1fx", tumZoom)
                                               : "  tüm harita"),
                            dp(2), h - dp(3), yazi);
            yazi.setColor(METIN);
            canvas.drawText("M" + metinSay, w - dp(28) * uiO, h - dp(3), yazi);
        }
    }

    private int dp(float v) {
        return Math.round(v * context.getResources().getDisplayMetrics().density);
    }
}

