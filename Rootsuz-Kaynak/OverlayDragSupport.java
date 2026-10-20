package com.abdulkadir.metin7x;

import android.content.Context;
import android.util.DisplayMetrics;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.WindowManager;
import android.widget.ScrollView;
import java.lang.reflect.Field;

/** Moves the overlay from unused space in its scrollable body. */
public final class OverlayDragSupport implements View.OnTouchListener {
    private final Context context;
    private final ScrollView scroll;
    private final View windowView;
    private final WindowManager manager;
    private final WindowManager.LayoutParams params;
    private final int slop;
    private float downX, downY;
    private int originalX, originalY;
    private boolean dragging, scrolling;

    private OverlayDragSupport(Context service, ScrollView scroll) throws ReflectiveOperationException {
        this.context = service;
        this.scroll = scroll;
        this.slop = ViewConfiguration.get(service).getScaledTouchSlop();
        Class<?> type = service.getClass();
        this.windowView = (View) field(type, "disKok").get(service);
        this.manager = (WindowManager) field(type, "wm").get(service);
        this.params = (WindowManager.LayoutParams) field(type, "pencere").get(service);
    }

    private static Field field(Class<?> type, String name) throws ReflectiveOperationException {
        Field field = type.getDeclaredField(name);
        field.setAccessible(true);
        return field;
    }

    public static void install(Context service, ScrollView scroll) {
        try {
            scroll.setOnTouchListener(new OverlayDragSupport(service, scroll));
        } catch (ReflectiveOperationException error) {
            android.util.Log.w("Metin7x", "Overlay sürükleme açılamadı", error);
        }
    }

    /** Leave a visible strip even after rotating the phone or dragging to an edge. */
    public static int clamp(Context context, int position, boolean vertical) {
        DisplayMetrics metrics = context.getResources().getDisplayMetrics();
        int visible = Math.round(56 * metrics.density);
        int span = vertical ? metrics.heightPixels : metrics.widthPixels;
        try {
            Field windowField = field(context.getClass(), "pencere");
            WindowManager.LayoutParams window =
                    (WindowManager.LayoutParams) windowField.get(context);
            if (window != null && window.width > 0) {
                if (vertical) visible = Math.round(200 * metrics.density);
                else visible = window.width + Math.round(8 * metrics.density);
            }
        } catch (ReflectiveOperationException ignored) { }
        return Math.max(0, Math.min(position, Math.max(0, span - visible)));
    }

    @Override public boolean onTouch(View view, MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downX = event.getRawX();
                downY = event.getRawY();
                originalX = params.x;
                originalY = params.y;
                dragging = false;
                scrolling = false;
                return false; // ScrollView keeps normal vertical scrolling.

            case MotionEvent.ACTION_MOVE:
                if (event.getPointerCount() != 1) return dragging;
                if (scrolling) return false;        // kaydırma başladıysa panel ASLA oynamaz
                float dx = event.getRawX() - downX;
                float dy = event.getRawY() - downY;
                if (!dragging) {
                    // Karar için eşik: küçük titremede hiçbir şey yapma.
                    if (Math.abs(dx) < slop && Math.abs(dy) < slop) return false;
                    // Dikey baskın hareket + içerik kaydırılabiliyorsa: bu bir KAYDIRMA.
                    // Süreye bakmıyoruz; yavaş kaydırma artık paneli oynatmaz.
                    if (Math.abs(dy) >= Math.abs(dx)
                            && (scroll.canScrollVertically(1) || scroll.canScrollVertically(-1))) {
                        scrolling = true;
                        return false;
                    }
                    // Buraya gelen: yatay baskın hareket YA DA hiç kaydırılamayan içerikte
                    // dikey hareket → paneli taşı.
                    dragging = true;
                    scroll.requestDisallowInterceptTouchEvent(true);
                }
                // Pencere sağ (END) hizalı: x sağ kenardan ölçülür, bu yüzden
                // parmak sağa gidince x AZALIR (ters işaret).
                params.x = clamp(context, originalX - Math.round(dx), false);
                params.y = clamp(context, originalY + Math.round(dy), true);
                try {
                    manager.updateViewLayout(windowView, params);
                } catch (IllegalArgumentException ignored) { }
                return true;

            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                boolean wasDragging = dragging;
                dragging = false;
                scrolling = false;
                scroll.requestDisallowInterceptTouchEvent(false);
                return wasDragging;
            default:
                return dragging;
        }
    }
}
