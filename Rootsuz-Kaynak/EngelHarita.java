package com.abdulkadir.metin7x;

import android.content.Context;
import android.graphics.Bitmap;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * ENGEL HARİTASI — tambot'un harita_engel.py'sinin Java portu.
 *
 * Oyunun çarpışma verisini (assets/harita/harita.json + *.engel) okur ve her
 * harita için bir ARAZİ bitmap'i üretir: yürünebilir hücre açık renk, duvar
 * saydam. Böylece HaritaOverlay radar değil, tambot'taki gibi gerçek arazi
 * zeminini çizebilir.
 *
 * Koordinatlar WorldBridge (DunyaDurumu) ile AYNI dünya birimindedir; bu
 * yüzden oyuncunun hamX/hamY'si doğrudan ızgaraya oturur.
 */
public final class EngelHarita {

    public static final int ARAZI = 0xFF2B3A56;   // yürünebilir zemin (belirgin mavi-gri)

    public static final class Harita {
        public final String ad;
        public final int tabanX, tabanY, g, y, hucre;
        final byte[] paket;                        // hücre başına 1 bit (1 = kapalı)
        private Bitmap zemin;                      // tembel üretilir
        // yürünebilir sınır (hücre) — çerçeveleme için
        public int minCx, minCy, maxCx, maxCy;

        Harita(String ad, int tabanX, int tabanY, int g, int y, int hucre, byte[] paket) {
            this.ad = ad; this.tabanX = tabanX; this.tabanY = tabanY;
            this.g = g; this.y = y; this.hucre = hucre; this.paket = paket;
        }

        public boolean icinde(int x, int yy) {
            int gx = x - tabanX, gy = yy - tabanY;
            return gx >= 0 && gy >= 0 && gx < g * hucre && gy < y * hucre;
        }

        boolean kapali(int cx, int cy) {
            if (cx < 0 || cy < 0 || cx >= g || cy >= y) return true;
            int i = cy * g + cx;
            return (paket[i >> 3] & (1 << (i & 7))) != 0;
        }

        /** Araziyi bir kez bitmap'e çizer (yürünebilir=ARAZI, duvar=saydam). */
        public synchronized Bitmap zemin() {
            if (zemin != null) return zemin;
            int[] px = new int[g * y];
            minCx = g; minCy = y; maxCx = 0; maxCy = 0;
            boolean acikVar = false;
            for (int cy = 0; cy < y; cy++) {
                int satir = cy * g;
                for (int cx = 0; cx < g; cx++) {
                    int i = satir + cx;
                    boolean kap = (paket[i >> 3] & (1 << (i & 7))) != 0;
                    if (!kap) {
                        px[i] = ARAZI; acikVar = true;
                        if (cx < minCx) minCx = cx; if (cx > maxCx) maxCx = cx;
                        if (cy < minCy) minCy = cy; if (cy > maxCy) maxCy = cy;
                    } else {
                        px[i] = 0;   // saydam
                    }
                }
            }
            if (!acikVar) { minCx = 0; minCy = 0; maxCx = g - 1; maxCy = y - 1; }
            Bitmap b = Bitmap.createBitmap(g, y, Bitmap.Config.ARGB_8888);
            b.setPixels(px, 0, g, 0, 0, g, y);
            zemin = b;
            return zemin;
        }

        public void serbestBirak() {
            if (zemin != null) { zemin.recycle(); zemin = null; }
        }

        // ── A* yol bulma (engelden kaçan rota) ──────────────────────────────
        /** A(ax,ay) -> B(bx,by) dünya noktaları arası engelsiz yol (hücre merkezleri,
         *  dünya koordinatı). Yol yoksa / harita çok büyükse boş liste döner. */
        public java.util.List<int[]> yol(int ax, int ay, int bx, int by) {
            java.util.ArrayList<int[]> sonuc = new java.util.ArrayList<>();
            int n = g * y;
            if (n <= 0 || n > 4_000_000) return sonuc;          // çok büyük ızgara: düz çizgiye düş
            int sc = acikHucre((ax - tabanX) / hucre, (ay - tabanY) / hucre);
            int tc = acikHucre((bx - tabanX) / hucre, (by - tabanY) / hucre);
            if (sc < 0 || tc < 0) return sonuc;
            int tcx = tc % g, tcy = tc / g;
            int[] gelen = new int[n];
            int[] gsk = new int[n];
            java.util.Arrays.fill(gelen, -2);                    // -2 görülmedi
            java.util.Arrays.fill(gsk, Integer.MAX_VALUE);
            gsk[sc] = 0; gelen[sc] = -1;
            java.util.PriorityQueue<int[]> pq =
                    new java.util.PriorityQueue<>((p, q) -> p[1] - q[1]);
            pq.add(new int[]{sc, 0});
            int[] ddx = {1, -1, 0, 0, 1, 1, -1, -1};
            int[] ddy = {0, 0, 1, -1, 1, -1, 1, -1};
            int patla = 0; boolean bulundu = false;
            while (!pq.isEmpty()) {
                if (++patla > 600_000) break;
                int ci = pq.poll()[0];
                if (ci == tc) { bulundu = true; break; }
                int cx = ci % g, cy = ci / g;
                for (int d = 0; d < 8; d++) {
                    int nx = cx + ddx[d], ny = cy + ddy[d];
                    if (nx < 0 || ny < 0 || nx >= g || ny >= y) continue;
                    if (kapali(nx, ny)) continue;
                    if (d >= 4 && (kapali(cx + ddx[d], cy) || kapali(cx, cy + ddy[d]))) continue;
                    int ni = ny * g + nx;
                    int yeni = gsk[ci] + (d >= 4 ? 14 : 10);
                    if (yeni < gsk[ni]) {
                        gsk[ni] = yeni; gelen[ni] = ci;
                        int hdx = Math.abs(nx - tcx), hdy = Math.abs(ny - tcy);
                        int h = 10 * (hdx + hdy) - 6 * Math.min(hdx, hdy);   // octile
                        pq.add(new int[]{ni, yeni + h});
                    }
                }
            }
            if (!bulundu) return sonuc;
            java.util.ArrayList<Integer> ters = new java.util.ArrayList<>();
            for (int ci = tc; ci != -1 && ci != -2; ci = gelen[ci]) ters.add(ci);
            for (int i = ters.size() - 1; i >= 0; i--) {
                int ci = ters.get(i), cx = ci % g, cy = ci / g;
                sonuc.add(new int[]{tabanX + cx * hucre + hucre / 2,
                                    tabanY + cy * hucre + hucre / 2});
            }
            return sonuc;
        }

        /** (cx,cy) kapalıysa yakın açık hücreyi bul; dizi indeksi, yoksa -1. */
        private int acikHucre(int cx, int cy) {
            cx = Math.max(0, Math.min(g - 1, cx));
            cy = Math.max(0, Math.min(y - 1, cy));
            if (!kapali(cx, cy)) return cy * g + cx;
            for (int r = 1; r <= 16; r++) {
                for (int dy = -r; dy <= r; dy++) {
                    for (int dx = -r; dx <= r; dx++) {
                        if (Math.abs(dx) != r && Math.abs(dy) != r) continue;   // sadece halka
                        int nx = cx + dx, ny = cy + dy;
                        if (nx < 0 || ny < 0 || nx >= g || ny >= y) continue;
                        if (!kapali(nx, ny)) return ny * g + nx;
                    }
                }
            }
            return -1;
        }
    }

    private static volatile EngelHarita instance;
    public final Map<String, Harita> haritalar = new HashMap<>();
    public final int hucre;

    private EngelHarita(int hucre) { this.hucre = hucre; }

    public static synchronized EngelHarita al(Context c) {
        if (instance == null) instance = yukle(c);
        return instance;
    }

    private static EngelHarita yukle(Context c) {
        try {
            String ham = assetOku(c, "harita/harita.json");
            JSONObject d = new JSONObject(ham);
            int hucre = d.optInt("hucre", 100);
            EngelHarita eh = new EngelHarita(hucre);
            JSONObject hs = d.optJSONObject("haritalar");
            if (hs != null) {
                java.util.Iterator<String> it = hs.keys();
                while (it.hasNext()) {
                    String ad = it.next();
                    JSONObject h = hs.getJSONObject(ad);
                    org.json.JSONArray taban = h.optJSONArray("taban");
                    if (taban == null) continue;          // hizasız harita kullanılamaz
                    String dosya = h.optString("dosya", ad + ".engel");
                    byte[] paket;
                    try {
                        paket = assetBayt(c, "harita/" + dosya);
                    } catch (Throwable miss) { continue; }
                    eh.haritalar.put(ad, new Harita(ad,
                            taban.getInt(0), taban.getInt(1),
                            h.getInt("g"), h.getInt("y"), hucre, paket));
                }
            }
            return eh;
        } catch (Throwable e) {
            android.util.Log.w("Metin7x", "Engel haritası yüklenemedi", e);
            return new EngelHarita(100);
        }
    }

    /** Bu konum hangi haritada? Tek eşleşme yoksa null (tambot ile aynı kural). */
    public Harita hangi(int x, int y) {
        Harita bulunan = null;
        for (Harita h : haritalar.values()) {
            if (h.icinde(x, y)) {
                if (bulunan != null) return null;         // çakışma -> güvenme
                bulunan = h;
            }
        }
        return bulunan;
    }

    public boolean bos() { return haritalar.isEmpty(); }

    // ── assets yardımcıları ──
    private static byte[] assetBayt(Context c, String yol) throws Exception {
        InputStream in = c.getAssets().open(yol);
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] tmp = new byte[8192];
        int n;
        while ((n = in.read(tmp)) != -1) bos.write(tmp, 0, n);
        in.close();
        return bos.toByteArray();
    }

    private static String assetOku(Context c, String yol) throws Exception {
        return new String(assetBayt(c, yol), "UTF-8");
    }
}
