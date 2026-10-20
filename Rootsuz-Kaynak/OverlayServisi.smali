.class public final Lcom/abdulkadir/metin/OverlayServisi;
.super Landroid/app/Service;
.source "OverlayServisi.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Lcom/abdulkadir/metin/OverlayServisi$Surukle;
    }
.end annotation


# static fields
.field private static final BILDIRIM_ID:I = 0x76c

.field private static final CIZGI:I = -0xdcd7c8

.field private static final KIRMIZI:I = -0xa5a6

.field private static final MAVI:I = -0xcc5501

.field private static final METIN:I = -0x363122

.field private static final SONUK:I = -0xd5cfc0

.field private static final SONUK_YAZI:I = -0xa59f8e

.field private static final TURUNCU:I = -0x4fe0

.field private static final YESIL:I = -0xc82986

.field private static final YOKLAMA_MS:J = 0x7d0L

.field private static final ZEMIN:I = -0x19f5f2ec


# instance fields
.field private boyut:I

.field private volatile calisiyor:Z

.field private detayAcik:Z

.field private detayKutu:Landroid/widget/LinearLayout;

.field private detayScroll:Landroid/widget/ScrollView;

.field private dikey:Z

.field private disKok:Landroid/widget/LinearLayout;

.field private final el:Landroid/os/Handler;

.field private final hucreler:Ljava/util/Map;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/Map<",
            "Ljava/lang/String;",
            "Landroid/widget/TextView;",
            ">;"
        }
    .end annotation
.end field

.field private k:Ljava/lang/String;

.field private kok:Landroid/widget/LinearLayout;

.field private pencere:Landroid/view/WindowManager$LayoutParams;

.field private sonVeri:Lorg/json/JSONObject;

.field private tekAda:Z

.field private tekSatir:Z

.field private url:Ljava/lang/String;

.field private wm:Landroid/view/WindowManager;

.field private yapiImzasi:Ljava/lang/String;

.field private yoklayici:Ljava/lang/Thread;


# direct methods
.method public static synthetic $r8$lambda$1eg5yWyXct-JObuR48AigvQArjI(Lcom/abdulkadir/metin/OverlayServisi;Landroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayCiz$8(Landroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$67LELwPtJlsnznGWhfCTzjqMUeM(Lcom/abdulkadir/metin/OverlayServisi;Landroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$kapatHucre$6(Landroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$D3AZUIrs3krlYiTEChNSM5SKcDg(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$komut$2(Lorg/json/JSONObject;)V

    return-void
.end method

.method public static synthetic $r8$lambda$Gs90djKq4vVIfT8I2AEDJN2i2RU(Lcom/abdulkadir/metin/OverlayServisi;ILandroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1, p2}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayCiz$11(ILandroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$JBOP7ddfOIi9AeTXGgeHK_xZE7k(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$basla$0(Lorg/json/JSONObject;)V

    return-void
.end method

.method public static synthetic $r8$lambda$NybrJ5FpHBLTtNEOh7s2GYsqmAM(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$komut$3(Lorg/json/JSONObject;)V

    return-void
.end method

.method public static synthetic $r8$lambda$Q-Ea_vF1T7LXAF6eZgXWegOPuy8(Lcom/abdulkadir/metin/OverlayServisi;Landroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayHucre$5(Landroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$T2YSVKhW636a5bkykOUe_D9y50U(Lcom/abdulkadir/metin/OverlayServisi;Landroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayCiz$7(Landroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$nXPoN7fQX404XrRFJblRpF_X6y0(Lcom/abdulkadir/metin/OverlayServisi;ILandroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1, p2}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayCiz$10(ILandroid/view/View;)V

    return-void
.end method

.method public static synthetic $r8$lambda$q9zG8cqQqA1ZyoydEEuNU7u_OqU(Lcom/abdulkadir/metin/OverlayServisi;)V
    .locals 0

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$basla$1()V

    return-void
.end method

.method public static synthetic $r8$lambda$u5AqHE2LXOa9kLkDBJZrK1xMF4I(Lcom/abdulkadir/metin/OverlayServisi;ILandroid/view/View;)V
    .locals 0

    invoke-direct {p0, p1, p2}, Lcom/abdulkadir/metin/OverlayServisi;->lambda$detayCiz$9(ILandroid/view/View;)V

    return-void
.end method

.method static bridge synthetic -$$Nest$fgetdisKok(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/widget/LinearLayout;
    .locals 0

    iget-object p0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    return-object p0
.end method

.method static bridge synthetic -$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;
    .locals 0

    iget-object p0, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    return-object p0
.end method

.method static bridge synthetic -$$Nest$fgetwm(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager;
    .locals 0

    iget-object p0, p0, Lcom/abdulkadir/metin/OverlayServisi;->wm:Landroid/view/WindowManager;

    return-object p0
.end method

.method public constructor <init>()V
    .locals 2

    .line 45
    invoke-direct {p0}, Landroid/app/Service;-><init>()V

    .line 65
    new-instance v0, Ljava/util/LinkedHashMap;

    invoke-direct {v0}, Ljava/util/LinkedHashMap;-><init>()V

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->hucreler:Ljava/util/Map;

    .line 66
    const-string v0, ""

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->yapiImzasi:Ljava/lang/String;

    .line 67
    const/4 v1, 0x0

    iput-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    .line 70
    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    .line 71
    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    .line 72
    const/4 v0, 0x1

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    .line 73
    iput-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekSatir:Z

    .line 74
    iput-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekAda:Z

    .line 75
    iput-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    .line 77
    new-instance v0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v1

    invoke-direct {v0, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->el:Landroid/os/Handler;

    return-void
.end method

.method private ayirac()Landroid/view/View;
    .locals 6

    .line 324
    new-instance v0, Landroid/view/View;

    invoke-direct {v0, p0}, Landroid/view/View;-><init>(Landroid/content/Context;)V

    .line 325
    .local v0, "v":Landroid/view/View;
    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    const/4 v2, 0x1

    if-eqz v1, :cond_0

    .line 326
    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->hx()I

    move-result v3

    add-int/lit8 v3, v3, -0x4

    invoke-direct {p0, v3}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v3

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    invoke-direct {v1, v3, v2}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    goto :goto_0

    .line 327
    :cond_0
    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->hy()I

    move-result v3

    add-int/lit8 v3, v3, -0x4

    invoke-direct {p0, v3}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v3

    invoke-direct {v1, v2, v3}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    :goto_0
    nop

    .line 328
    .local v1, "lp":Landroid/widget/LinearLayout$LayoutParams;
    const/4 v2, 0x3

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v3

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v4

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v5

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    invoke-virtual {v1, v3, v4, v5, v2}, Landroid/widget/LinearLayout$LayoutParams;->setMargins(IIII)V

    .line 329
    invoke-virtual {v0, v1}, Landroid/view/View;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 330
    const v2, -0xdcd7c8

    invoke-virtual {v0, v2}, Landroid/view/View;->setBackgroundColor(I)V

    .line 331
    return-object v0
.end method

.method private basla()V
    .locals 3

    .line 140
    iget-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->calisiyor:Z

    if-eqz v0, :cond_0

    return-void

    .line 141
    :cond_0
    const/4 v0, 0x1

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->calisiyor:Z

    .line 142
    new-instance v1, Ljava/lang/Thread;

    new-instance v2, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda10;

    invoke-direct {v2, p0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda10;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    invoke-direct {v1, v2}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V

    iput-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->yoklayici:Ljava/lang/Thread;

    .line 149
    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->yoklayici:Ljava/lang/Thread;

    invoke-virtual {v1, v0}, Ljava/lang/Thread;->setDaemon(Z)V

    .line 150
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->yoklayici:Ljava/lang/Thread;

    invoke-virtual {v0}, Ljava/lang/Thread;->start()V

    .line 151
    return-void
.end method

.method private boya(Landroid/widget/TextView;IIZ)V
    .locals 3
    .param p1, "t"    # Landroid/widget/TextView;
    .param p2, "arka"    # I
    .param p3, "yaziRenk"    # I
    .param p4, "buff"    # Z

    .line 504
    new-instance v0, Landroid/graphics/drawable/GradientDrawable;

    invoke-direct {v0}, Landroid/graphics/drawable/GradientDrawable;-><init>()V

    .line 505
    .local v0, "g":Landroid/graphics/drawable/GradientDrawable;
    invoke-virtual {v0, p2}, Landroid/graphics/drawable/GradientDrawable;->setColor(I)V

    .line 506
    const/4 v1, 0x6

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    int-to-float v1, v1

    invoke-virtual {v0, v1}, Landroid/graphics/drawable/GradientDrawable;->setCornerRadius(F)V

    .line 507
    if-eqz p4, :cond_0

    const/4 v1, 0x2

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    const v2, -0xcc5501

    invoke-virtual {v0, v1, v2}, Landroid/graphics/drawable/GradientDrawable;->setStroke(II)V

    .line 508
    :cond_0
    invoke-virtual {p1, v0}, Landroid/widget/TextView;->setBackground(Landroid/graphics/drawable/Drawable;)V

    .line 509
    invoke-virtual {p1, p3}, Landroid/widget/TextView;->setTextColor(I)V

    .line 510
    return-void
.end method

.method private buffUsteTasi()V
    .locals 5

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v0}, Landroid/widget/LinearLayout;->getChildCount()I

    move-result v1

    add-int/lit8 v1, v1, -0x2

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->getChildAt(I)Landroid/view/View;

    move-result-object v2

    add-int/lit8 v3, v1, 0x1

    invoke-virtual {v0, v3}, Landroid/widget/LinearLayout;->getChildAt(I)Landroid/view/View;

    move-result-object v4

    invoke-virtual {v0, v3}, Landroid/widget/LinearLayout;->removeViewAt(I)V

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->removeViewAt(I)V

    const/4 v1, 0x1

    invoke-virtual {v0, v2, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;I)V

    const/4 v1, 0x2

    invoke-virtual {v0, v4, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;I)V

    return-void
.end method

.method private chAnahtarlari(Lorg/json/JSONObject;Ljava/lang/String;)Ljava/util/List;
    .locals 4
    .param p1, "adalar"    # Lorg/json/JSONObject;
    .param p2, "an"    # Ljava/lang/String;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Lorg/json/JSONObject;",
            "Ljava/lang/String;",
            ")",
            "Ljava/util/List<",
            "Ljava/lang/String;",
            ">;"
        }
    .end annotation

    .line 300
    invoke-virtual {p1, p2}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    .line 301
    .local v0, "ks":Lorg/json/JSONObject;
    new-instance v1, Ljava/util/ArrayList;

    invoke-direct {v1}, Ljava/util/ArrayList;-><init>()V

    .line 302
    .local v1, "chl":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    if-eqz v0, :cond_0

    invoke-virtual {v0}, Lorg/json/JSONObject;->keys()Ljava/util/Iterator;

    move-result-object v2

    .local v2, "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :goto_0
    invoke-interface {v2}, Ljava/util/Iterator;->hasNext()Z

    move-result v3

    if-eqz v3, :cond_0

    invoke-interface {v2}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v3

    check-cast v3, Ljava/lang/String;

    invoke-interface {v1, v3}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    goto :goto_0

    .line 303
    .end local v2    # "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :cond_0
    new-instance v2, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda5;

    invoke-direct {v2}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda5;-><init>()V

    invoke-static {v1, v2}, Ljava/util/Collections;->sort(Ljava/util/List;Ljava/util/Comparator;)V

    .line 304
    return-object v1
.end method

.method private ciz(Lorg/json/JSONObject;)V
    .locals 14
    .param p1, "d"    # Lorg/json/JSONObject;

    .line 214
    iput-object p1, p0, Lcom/abdulkadir/metin/OverlayServisi;->sonVeri:Lorg/json/JSONObject;

    .line 215
    const-string v0, "adalar"

    invoke-virtual {p1, v0}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    .line 216
    .local v0, "adalar":Lorg/json/JSONObject;
    if-nez v0, :cond_1

    .line 217
    const-string v1, "kanallar"

    invoke-virtual {p1, v1}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v1

    .line 218
    .local v1, "kn":Lorg/json/JSONObject;
    new-instance v2, Lorg/json/JSONObject;

    invoke-direct {v2}, Lorg/json/JSONObject;-><init>()V

    move-object v0, v2

    .line 219
    :try_start_0
    const-string v2, "1"

    if-nez v1, :cond_0

    new-instance v3, Lorg/json/JSONObject;

    invoke-direct {v3}, Lorg/json/JSONObject;-><init>()V

    goto :goto_0

    :cond_0
    move-object v3, v1

    :goto_0
    invoke-virtual {v0, v2, v3}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_1

    :catchall_0
    move-exception v2

    .line 221
    .end local v1    # "kn":Lorg/json/JSONObject;
    :cond_1
    :goto_1
    new-instance v1, Ljava/util/ArrayList;

    invoke-direct {v1}, Ljava/util/ArrayList;-><init>()V

    .line 222
    .local v1, "adaAnahtar":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    invoke-virtual {v0}, Lorg/json/JSONObject;->keys()Ljava/util/Iterator;

    move-result-object v2

    .local v2, "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :goto_2
    invoke-interface {v2}, Ljava/util/Iterator;->hasNext()Z

    move-result v3

    if-eqz v3, :cond_2

    invoke-interface {v2}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v3

    check-cast v3, Ljava/lang/String;

    invoke-interface {v1, v3}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    goto :goto_2

    .line 223
    .end local v2    # "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :cond_2
    invoke-static {v1}, Ljava/util/Collections;->sort(Ljava/util/List;)V

    .line 225
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    .line 226
    .local v2, "imza":Ljava/lang/StringBuilder;
    invoke-interface {v1}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v3

    :goto_3
    invoke-interface {v3}, Ljava/util/Iterator;->hasNext()Z

    move-result v4

    if-eqz v4, :cond_3

    invoke-interface {v3}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v4

    check-cast v4, Ljava/lang/String;

    .line 227
    .local v4, "an":Ljava/lang/String;
    invoke-virtual {v2, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v5

    const/16 v6, 0x3a

    invoke-virtual {v5, v6}, Ljava/lang/StringBuilder;->append(C)Ljava/lang/StringBuilder;

    move-result-object v5

    invoke-direct {p0, v0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->chAnahtarlari(Lorg/json/JSONObject;Ljava/lang/String;)Ljava/util/List;

    move-result-object v6

    invoke-virtual {v5, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v5

    const/16 v6, 0x3b

    invoke-virtual {v5, v6}, Ljava/lang/StringBuilder;->append(C)Ljava/lang/StringBuilder;

    goto :goto_3

    .line 228
    .end local v4    # "an":Ljava/lang/String;
    :cond_3
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    iget-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->yapiImzasi:Ljava/lang/String;

    invoke-virtual {v3, v4}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-nez v3, :cond_4

    .line 229
    invoke-direct {p0, v0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->kur(Lorg/json/JSONObject;Ljava/util/List;)V

    .line 230
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    iput-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->yapiImzasi:Ljava/lang/String;

    .line 232
    :cond_4
    invoke-interface {v1}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v3

    :goto_4
    invoke-interface {v3}, Ljava/util/Iterator;->hasNext()Z

    move-result v4

    if-eqz v4, :cond_b

    invoke-interface {v3}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v4

    check-cast v4, Ljava/lang/String;

    .line 233
    .restart local v4    # "an":Ljava/lang/String;
    invoke-virtual {v0, v4}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v5

    .line 234
    .local v5, "ks":Lorg/json/JSONObject;
    if-nez v5, :cond_5

    goto :goto_4

    .line 235
    :cond_5
    invoke-virtual {v5}, Lorg/json/JSONObject;->keys()Ljava/util/Iterator;

    move-result-object v6

    .local v6, "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :goto_5
    invoke-interface {v6}, Ljava/util/Iterator;->hasNext()Z

    move-result v7

    if-eqz v7, :cond_a

    .line 236
    invoke-interface {v6}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v7

    check-cast v7, Ljava/lang/String;

    .line 237
    .local v7, "ch":Ljava/lang/String;
    iget-object v8, p0, Lcom/abdulkadir/metin/OverlayServisi;->hucreler:Ljava/util/Map;

    new-instance v9, Ljava/lang/StringBuilder;

    invoke-direct {v9}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v9, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v9

    const-string v10, ":"

    invoke-virtual {v9, v10}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v9

    invoke-virtual {v9, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v9

    invoke-virtual {v9}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v9

    invoke-interface {v8, v9}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v8

    check-cast v8, Landroid/widget/TextView;

    .line 238
    .local v8, "h":Landroid/widget/TextView;
    if-nez v8, :cond_6

    goto :goto_5

    .line 239
    :cond_6
    invoke-virtual {v5, v7}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v9

    .line 240
    .local v9, "o":Lorg/json/JSONObject;
    invoke-direct {p0, v9}, Lcom/abdulkadir/metin/OverlayServisi;->renk(Lorg/json/JSONObject;)I

    move-result v10

    .line 241
    .local v10, "r":I
    const/4 v11, 0x0

    if-eqz v9, :cond_7

    const-string v12, "buff"

    invoke-virtual {v9, v12, v11}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result v12

    if-eqz v12, :cond_7

    const/4 v11, 0x1

    .line 242
    .local v11, "buff":Z
    :cond_7
    if-eqz v11, :cond_8

    new-instance v12, Ljava/lang/StringBuilder;

    invoke-direct {v12}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v12, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    const-string v13, "\ud83d\udee1"

    invoke-virtual {v12, v13}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    invoke-virtual {v12}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v12

    goto :goto_6

    :cond_8
    move-object v12, v7

    :goto_6
    invoke-virtual {v8, v12}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 243
    invoke-static {v9, v10}, Lcom/abdulkadir/metin7x/Overlay7xControls;->yaziRengi(Lorg/json/JSONObject;I)I

    move-result v12

    invoke-direct {p0, v8, v10, v12, v11}, Lcom/abdulkadir/metin/OverlayServisi;->boya(Landroid/widget/TextView;IIZ)V

    .line 244
    .end local v7    # "ch":Ljava/lang/String;
    .end local v8    # "h":Landroid/widget/TextView;
    .end local v9    # "o":Lorg/json/JSONObject;
    .end local v10    # "r":I
    .end local v11    # "buff":Z
    goto :goto_5

    .line 245
    .end local v4    # "an":Ljava/lang/String;
    .end local v5    # "ks":Lorg/json/JSONObject;
    .end local v6    # "it":Ljava/util/Iterator;, "Ljava/util/Iterator<Ljava/lang/String;>;"
    :cond_a
    goto/16 :goto_4

    .line 246
    :cond_b
    invoke-static {p0}, Lcom/abdulkadir/metin7x/OverlayWindowSizing;->equalizeIslandCells(Landroid/content/Context;)V

    iget-boolean v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    if-eqz v3, :cond_c

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->detayCiz(Lorg/json/JSONObject;)V

    .line 247
    :cond_c
    return-void
.end method

.method private cizgiAyirac()Landroid/view/View;
    .locals 4

    .line 472
    new-instance v0, Landroid/view/View;

    invoke-direct {v0, p0}, Landroid/view/View;-><init>(Landroid/content/Context;)V

    .line 473
    .local v0, "v":Landroid/view/View;
    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    .line 474
    const/4 v2, 0x1

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    const/4 v3, -0x1

    invoke-direct {v1, v3, v2}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    .line 475
    .local v1, "lp":Landroid/widget/LinearLayout$LayoutParams;
    const/4 v2, 0x5

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    iput v2, v1, Landroid/widget/LinearLayout$LayoutParams;->topMargin:I

    .line 476
    invoke-virtual {v0, v1}, Landroid/view/View;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 477
    const v2, -0xdcd7c8

    invoke-virtual {v0, v2}, Landroid/view/View;->setBackgroundColor(I)V

    .line 478
    return-object v0
.end method

.method private cizgiYap()Landroid/widget/LinearLayout;
    .locals 2

    .line 293
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    .line 294
    .local v0, "s":Landroid/widget/LinearLayout;
    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 295
    const/16 v1, 0x11

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setGravity(I)V

    .line 296
    return-object v0
.end method

.method private dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;
    .locals 8
    .param p1, "yazi"    # Ljava/lang/String;
    .param p2, "arka"    # I
    .param p3, "yaziRenk"    # I
    .param p4, "tik"    # Landroid/view/View$OnClickListener;

    .line 432
    new-instance v0, Landroid/widget/TextView;

    invoke-direct {v0, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    .line 433
    .local v0, "t":Landroid/widget/TextView;
    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 434
    const/high16 v1, 0x41300000    # 11.0f

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setTextSize(F)V

    .line 435
    invoke-virtual {v0, p3}, Landroid/widget/TextView;->setTextColor(I)V

    .line 436
    const/16 v1, 0x11

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setGravity(I)V

    .line 437
    const/16 v1, 0x8

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    .local v1, "px":I
    const/4 v2, 0x5

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    .line 438
    .local v2, "py":I
    invoke-virtual {v0, v1, v2, v1, v2}, Landroid/widget/TextView;->setPadding(IIII)V

    .line 439
    new-instance v3, Landroid/graphics/drawable/GradientDrawable;

    invoke-direct {v3}, Landroid/graphics/drawable/GradientDrawable;-><init>()V

    .line 440
    .local v3, "g":Landroid/graphics/drawable/GradientDrawable;
    invoke-virtual {v3, p2}, Landroid/graphics/drawable/GradientDrawable;->setColor(I)V

    .line 441
    const/4 v4, 0x6

    invoke-direct {p0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v4

    int-to-float v4, v4

    invoke-virtual {v3, v4}, Landroid/graphics/drawable/GradientDrawable;->setCornerRadius(F)V

    .line 442
    invoke-virtual {v0, v3}, Landroid/widget/TextView;->setBackground(Landroid/graphics/drawable/Drawable;)V

    .line 443
    new-instance v4, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v5, -0x2

    invoke-direct {v4, v5, v5}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    .line 445
    .local v4, "lp":Landroid/widget/LinearLayout$LayoutParams;
    const/4 v5, 0x2

    invoke-direct {p0, v5}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v6

    const/4 v7, 0x0

    invoke-direct {p0, v5}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v5

    invoke-virtual {v4, v6, v7, v5, v7}, Landroid/widget/LinearLayout$LayoutParams;->setMargins(IIII)V

    .line 446
    invoke-virtual {v0, v4}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 447
    invoke-virtual {v0, p4}, Landroid/widget/TextView;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    .line 448
    return-object v0
.end method

.method private dEtiket(Ljava/lang/String;)Landroid/widget/TextView;
    .locals 5
    .param p1, "s"    # Ljava/lang/String;

    .line 463
    new-instance v0, Landroid/widget/TextView;

    invoke-direct {v0, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    .line 464
    .local v0, "t":Landroid/widget/TextView;
    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 465
    const/high16 v1, 0x41100000    # 9.0f

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setTextSize(F)V

    .line 466
    const v1, -0x948f80

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setTextColor(I)V

    .line 467
    const/4 v1, 0x4

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    const/4 v2, 0x6

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    const/4 v3, 0x2

    invoke-direct {p0, v3}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v3

    const/4 v4, 0x0

    invoke-virtual {v0, v1, v2, v4, v3}, Landroid/widget/TextView;->setPadding(IIII)V

    .line 468
    return-object v0
.end method

.method private dYazi(Ljava/lang/String;IF)Landroid/widget/TextView;
    .locals 4
    .param p1, "s"    # Ljava/lang/String;
    .param p2, "renk"    # I
    .param p3, "agirlik"    # F

    .line 452
    new-instance v0, Landroid/widget/TextView;

    invoke-direct {v0, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    .line 453
    .local v0, "t":Landroid/widget/TextView;
    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 454
    const/high16 v1, 0x41300000    # 11.0f

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setTextSize(F)V

    .line 455
    invoke-virtual {v0, p2}, Landroid/widget/TextView;->setTextColor(I)V

    .line 456
    const/4 v1, 0x4

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3, v1, v3}, Landroid/widget/TextView;->setPadding(IIII)V

    .line 457
    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v2, -0x2

    invoke-direct {v1, v3, v2, p3}, Landroid/widget/LinearLayout$LayoutParams;-><init>(IIF)V

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 459
    return-object v0
.end method

.method private detayCiz(Lorg/json/JSONObject;)V
    .locals 18
    .param p1, "d"    # Lorg/json/JSONObject;

    .line 351
    move-object/from16 v0, p0

    move-object/from16 v1, p1

    iget-object v2, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-static {v0, v1, v2}, Lcom/abdulkadir/metin7x/Overlay7xControls;->renderCompactIfSelected(Landroid/content/Context;Lorg/json/JSONObject;Landroid/widget/LinearLayout;)Z

    move-result v2

    if-eqz v2, :expanded_mode

    return-void

    :expanded_mode
    iget-object v2, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v2}, Landroid/widget/LinearLayout;->removeAllViews()V

    .line 352
    iget-object v2, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-direct {v0}, Lcom/abdulkadir/metin/OverlayServisi;->cizgiAyirac()Landroid/view/View;

    move-result-object v3

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    iget-object v2, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-static {v0, v2}, Lcom/abdulkadir/metin7x/Overlay7xControls;->appendExpanded(Landroid/content/Context;Landroid/widget/LinearLayout;)V

    .line 355
    invoke-direct {v0}, Lcom/abdulkadir/metin/OverlayServisi;->yatayCubuk()Landroid/widget/LinearLayout;

    move-result-object v2

    .line 356
    .local v2, "ust":Landroid/widget/LinearLayout;
    new-instance v3, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda0;

    invoke-direct {v3, v0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda0;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    const-string v4, "\u25b6 T\u00fcm\u00fc"

    const v5, -0xebc9e1

    const v6, -0xc82986

    invoke-direct {v0, v4, v5, v6, v3}, Lcom/abdulkadir/metin/OverlayServisi;->dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;

    move-result-object v3

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 357
    new-instance v3, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda1;

    invoke-direct {v3, v0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda1;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    const-string v4, "\u25a0 T\u00fcm\u00fc"

    const v7, -0xc9ebec

    const v8, -0xa5a6

    invoke-direct {v0, v4, v7, v8, v3}, Lcom/abdulkadir/metin/OverlayServisi;->dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;

    move-result-object v3

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 358
    iget-object v3, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v3, v2}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 361
    const-string v3, "hesaplar"

    invoke-virtual {v1, v3}, Lorg/json/JSONObject;->optJSONArray(Ljava/lang/String;)Lorg/json/JSONArray;

    move-result-object v3

    .line 362
    .local v3, "hesaplar":Lorg/json/JSONArray;
    const-string v9, "buff"

    const-string v10, "kanal"

    const/4 v11, -0x1

    const/4 v12, 0x0

    if-eqz v3, :cond_6

    invoke-virtual {v3}, Lorg/json/JSONArray;->length()I

    move-result v13

    if-lez v13, :cond_6

    .line 363
    iget-object v13, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    const-string v14, "Kanallar"

    invoke-direct {v0, v14}, Lcom/abdulkadir/metin/OverlayServisi;->dEtiket(Ljava/lang/String;)Landroid/widget/TextView;

    move-result-object v14

    invoke-virtual {v13, v14}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 364
    const/4 v13, 0x0

    .local v13, "i":I
    :goto_0
    invoke-virtual {v3}, Lorg/json/JSONArray;->length()I

    move-result v14

    if-ge v13, v14, :cond_5

    .line 365
    invoke-virtual {v3, v13}, Lorg/json/JSONArray;->optJSONObject(I)Lorg/json/JSONObject;

    move-result-object v14

    .line 366
    .local v14, "h":Lorg/json/JSONObject;
    if-nez v14, :cond_0

    move-object/from16 v17, v2

    move-object/from16 v16, v3

    move v2, v5

    move v3, v6

    goto/16 :goto_4

    .line 367
    :cond_0
    const-string v15, "idx"

    invoke-virtual {v14, v15, v11}, Lorg/json/JSONObject;->optInt(Ljava/lang/String;I)I

    move-result v15

    .line 368
    .local v15, "idx":I
    const-string v4, "calisiyor"

    invoke-virtual {v14, v4, v12}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result v4

    .line 369
    .local v4, "cal":Z
    const-string v11, "tarama"

    invoke-virtual {v14, v11, v12}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result v11

    .line 370
    .local v11, "tar":Z
    const-string v5, "rol"

    const-string v6, "izleyici"

    invoke-virtual {v14, v5, v6}, Lorg/json/JSONObject;->optString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v5

    .line 371
    .local v5, "rol":Ljava/lang/String;
    if-eqz v11, :cond_1

    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V

    const-string v7, "gez "

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    const-string v7, "tarama_metin"

    const-string v8, ""

    invoke-virtual {v14, v7, v8}, Lorg/json/JSONObject;->optString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v7

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v6

    goto :goto_1

    .line 372
    :cond_1
    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V

    const-string v7, "ch"

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v14, v10, v12}, Lorg/json/JSONObject;->optInt(Ljava/lang/String;I)I

    move-result v7

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v6

    :goto_1
    nop

    .line 373
    .local v6, "et":Ljava/lang/String;
    invoke-virtual {v9, v5}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v7

    if-eqz v7, :cond_2

    new-instance v7, Ljava/lang/StringBuilder;

    invoke-direct {v7}, Ljava/lang/StringBuilder;-><init>()V

    const-string v8, "\ud83d\udee1 "

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    invoke-virtual {v7, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v6

    .line 375
    :cond_2
    invoke-direct {v0}, Lcom/abdulkadir/metin/OverlayServisi;->yatayCubuk()Landroid/widget/LinearLayout;

    move-result-object v7

    .line 376
    .local v7, "satir":Landroid/widget/LinearLayout;
    if-eqz v4, :cond_3

    const v8, -0x363122

    goto :goto_2

    :cond_3
    const v8, -0xa59f8e

    :goto_2
    const/high16 v12, 0x3f800000    # 1.0f

    invoke-direct {v0, v6, v8, v12}, Lcom/abdulkadir/metin/OverlayServisi;->dYazi(Ljava/lang/String;IF)Landroid/widget/TextView;

    move-result-object v8

    invoke-virtual {v7, v8}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 377
    if-eqz v4, :cond_4

    .line 378
    new-instance v8, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda2;

    invoke-direct {v8, v0, v15}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda2;-><init>(Lcom/abdulkadir/metin/OverlayServisi;I)V

    const-string v12, "\u25a0 durdur"

    move-object/from16 v17, v2

    move-object/from16 v16, v3

    const v2, -0xc9ebec

    const v3, -0xa5a6

    .end local v2    # "ust":Landroid/widget/LinearLayout;
    .end local v3    # "hesaplar":Lorg/json/JSONArray;
    .local v16, "hesaplar":Lorg/json/JSONArray;
    .local v17, "ust":Landroid/widget/LinearLayout;
    invoke-direct {v0, v12, v2, v3, v8}, Lcom/abdulkadir/metin/OverlayServisi;->dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;

    move-result-object v8

    invoke-virtual {v7, v8}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    const v2, -0xebc9e1

    const v3, -0xc82986

    goto :goto_3

    .line 381
    .end local v16    # "hesaplar":Lorg/json/JSONArray;
    .end local v17    # "ust":Landroid/widget/LinearLayout;
    .restart local v2    # "ust":Landroid/widget/LinearLayout;
    .restart local v3    # "hesaplar":Lorg/json/JSONArray;
    :cond_4
    move-object/from16 v17, v2

    move-object/from16 v16, v3

    const v2, -0xc9ebec

    const v3, -0xa5a6

    .end local v2    # "ust":Landroid/widget/LinearLayout;
    .end local v3    # "hesaplar":Lorg/json/JSONArray;
    .restart local v16    # "hesaplar":Lorg/json/JSONArray;
    .restart local v17    # "ust":Landroid/widget/LinearLayout;
    new-instance v8, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda3;

    invoke-direct {v8, v0, v15}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda3;-><init>(Lcom/abdulkadir/metin/OverlayServisi;I)V

    const-string v12, "\u25b6 ba\u015flat"

    const v2, -0xebc9e1

    const v3, -0xc82986

    invoke-direct {v0, v12, v2, v3, v8}, Lcom/abdulkadir/metin/OverlayServisi;->dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;

    move-result-object v8

    invoke-virtual {v7, v8}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 383
    :goto_3
    iget-object v8, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v8, v7}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 364
    .end local v4    # "cal":Z
    .end local v5    # "rol":Ljava/lang/String;
    .end local v6    # "et":Ljava/lang/String;
    .end local v7    # "satir":Landroid/widget/LinearLayout;
    .end local v11    # "tar":Z
    .end local v14    # "h":Lorg/json/JSONObject;
    .end local v15    # "idx":I
    :goto_4
    add-int/lit8 v13, v13, 0x1

    move v5, v2

    move v6, v3

    move-object/from16 v3, v16

    move-object/from16 v2, v17

    const v7, -0xc9ebec

    const v8, -0xa5a6

    const/4 v11, -0x1

    const/4 v12, 0x0

    goto/16 :goto_0

    .end local v16    # "hesaplar":Lorg/json/JSONArray;
    .end local v17    # "ust":Landroid/widget/LinearLayout;
    .restart local v2    # "ust":Landroid/widget/LinearLayout;
    .restart local v3    # "hesaplar":Lorg/json/JSONArray;
    :cond_5
    move-object/from16 v17, v2

    move-object/from16 v16, v3

    .end local v2    # "ust":Landroid/widget/LinearLayout;
    .end local v3    # "hesaplar":Lorg/json/JSONArray;
    .restart local v16    # "hesaplar":Lorg/json/JSONArray;
    .restart local v17    # "ust":Landroid/widget/LinearLayout;
    goto :goto_5

    .line 362
    .end local v13    # "i":I
    .end local v16    # "hesaplar":Lorg/json/JSONArray;
    .end local v17    # "ust":Landroid/widget/LinearLayout;
    .restart local v2    # "ust":Landroid/widget/LinearLayout;
    .restart local v3    # "hesaplar":Lorg/json/JSONArray;
    :cond_6
    move-object/from16 v17, v2

    move-object/from16 v16, v3

    .line 388
    .end local v2    # "ust":Landroid/widget/LinearLayout;
    .end local v3    # "hesaplar":Lorg/json/JSONArray;
    .restart local v16    # "hesaplar":Lorg/json/JSONArray;
    .restart local v17    # "ust":Landroid/widget/LinearLayout;
    :goto_5
    invoke-virtual {v1, v9}, Lorg/json/JSONObject;->optJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v2

    .line 389
    .local v2, "buff":Lorg/json/JSONObject;
    if-eqz v2, :cond_7

    invoke-virtual {v2, v10}, Lorg/json/JSONObject;->isNull(Ljava/lang/String;)Z

    move-result v3

    if-nez v3, :cond_7

    const/4 v3, -0x1

    invoke-virtual {v2, v10, v3}, Lorg/json/JSONObject;->optInt(Ljava/lang/String;I)I

    move-result v11

    goto :goto_6

    :cond_7
    const/4 v3, -0x1

    move v11, v3

    .line 390
    .local v11, "buffKanal":I
    :goto_6
    const/4 v3, 0x1

    if-eqz v2, :cond_8

    const-string v4, "calisan"

    const/4 v5, 0x0

    invoke-virtual {v2, v4, v5}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result v4

    if-eqz v4, :cond_9

    move v4, v3

    goto :goto_7

    :cond_8
    const/4 v5, 0x0

    :cond_9
    move v4, v5

    .line 391
    .local v4, "buffVar":Z
    :goto_7
    iget-object v6, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    if-eqz v4, :cond_a

    new-instance v7, Ljava/lang/StringBuilder;

    invoke-direct {v7}, Ljava/lang/StringBuilder;-><init>()V

    const-string v8, "Buff\'\u00e7\u0131y\u0131 \u00e7ek  (\u015fu an ch"

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    invoke-virtual {v7, v11}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v7

    const-string v8, ")"

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v7

    goto :goto_8

    .line 392
    :cond_a
    const-string v7, "Buff\'\u00e7\u0131y\u0131 \u00e7ek"

    .line 391
    :goto_8
    invoke-direct {v0, v7}, Lcom/abdulkadir/metin/OverlayServisi;->dEtiket(Ljava/lang/String;)Landroid/widget/TextView;

    move-result-object v7

    invoke-virtual {v6, v7}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 393
    invoke-direct {v0}, Lcom/abdulkadir/metin/OverlayServisi;->yatayCubuk()Landroid/widget/LinearLayout;

    move-result-object v6

    .line 394
    .local v6, "bsatir":Landroid/widget/LinearLayout;
    const/4 v7, 0x1

    .local v7, "kn":I
    :goto_9
    const/16 v8, 0x8

    if-gt v7, v8, :cond_e

    .line 395
    move v8, v7

    .line 396
    .local v8, "kanal":I
    if-ne v7, v11, :cond_b

    move v9, v3

    goto :goto_a

    :cond_b
    move v9, v5

    .line 397
    .local v9, "burada":Z
    :goto_a
    invoke-static {v7}, Ljava/lang/String;->valueOf(I)Ljava/lang/String;

    move-result-object v10

    .line 398
    if-eqz v9, :cond_c

    const v12, -0xcc5501

    goto :goto_b

    :cond_c
    const v12, -0xe5e0d5

    .line 399
    :goto_b
    if-eqz v9, :cond_d

    const v13, -0x19f5f2ec

    goto :goto_c

    :cond_d
    const v13, -0x363122

    :goto_c
    new-instance v14, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda4;

    invoke-direct {v14, v0, v8}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda4;-><init>(Lcom/abdulkadir/metin/OverlayServisi;I)V

    .line 397
    invoke-direct {v0, v10, v12, v13, v14}, Lcom/abdulkadir/metin/OverlayServisi;->dBtn(Ljava/lang/String;IILandroid/view/View$OnClickListener;)Landroid/widget/TextView;

    move-result-object v10

    .line 401
    .local v10, "b":Landroid/widget/TextView;
    const/16 v12, 0x1a

    invoke-direct {v0, v12}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v12

    invoke-virtual {v10, v12}, Landroid/widget/TextView;->setMinWidth(I)V

    .line 402
    invoke-virtual {v6, v10}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 394
    .end local v8    # "kanal":I
    .end local v9    # "burada":Z
    .end local v10    # "b":Landroid/widget/TextView;
    add-int/lit8 v7, v7, 0x1

    goto :goto_9

    .line 404
    .end local v7    # "kn":I
    :cond_e
    iget-object v3, v0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v3, v6}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    invoke-direct {v0}, Lcom/abdulkadir/metin/OverlayServisi;->buffUsteTasi()V

    .line 405
    return-void
.end method

.method private detayHucre()Landroid/widget/TextView;
    .locals 3

    .line 308
    const/4 v0, 0x0

    const v1, -0x655f4c

    const-string v2, "\u2699"

    invoke-direct {p0, v2, v0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->hucre(Ljava/lang/String;II)Landroid/widget/TextView;

    move-result-object v0

    .line 309
    .local v0, "g":Landroid/widget/TextView;
    new-instance v1, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda9;

    invoke-direct {v1, p0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda9;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    .line 314
    return-object v0
.end method

.method private detayYukseklikAyarla()V
    .locals 5

    invoke-virtual {p0}, Lcom/abdulkadir/metin/OverlayServisi;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v0

    iget v0, v0, Landroid/util/DisplayMetrics;->heightPixels:I

    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    iget v1, v1, Landroid/view/WindowManager$LayoutParams;->y:I

    sub-int/2addr v0, v1

    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v1}, Landroid/widget/LinearLayout;->getVisibility()I

    move-result v2

    const/16 v3, 0x8

    if-ne v2, v3, :grid_height_visible

    const/4 v1, 0x0

    goto :grid_height_done

    :grid_height_visible
    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v1}, Landroid/widget/LinearLayout;->getHeight()I

    move-result v1

    :grid_height_done
    sub-int/2addr v0, v1

    invoke-static {p0}, Lcom/abdulkadir/metin7x/OverlayWindowSizing;->miniHeight(Landroid/content/Context;)I

    move-result v1

    sub-int/2addr v0, v1

    const/16 v1, 0x20

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    sub-int/2addr v0, v1

    const/16 v1, 0x78

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    invoke-static {v0, v1}, Ljava/lang/Math;->max(II)I

    move-result v0

    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v2, -0x1

    invoke-direct {v1, v2, v0}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    invoke-virtual {v2, v1}, Landroid/widget/ScrollView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    return-void
.end method

.method private dp(I)I
    .locals 2
    .param p1, "v"    # I

    .line 565
    int-to-float v0, p1

    invoke-virtual {p0}, Lcom/abdulkadir/metin/OverlayServisi;->getResources()Landroid/content/res/Resources;

    move-result-object v1

    invoke-virtual {v1}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v1

    iget v1, v1, Landroid/util/DisplayMetrics;->density:F

    mul-float/2addr v0, v1

    invoke-static {v0}, Ljava/lang/Math;->round(F)I

    move-result v0

    return v0
.end method

.method private getir()Lorg/json/JSONObject;
    .locals 8

    .line 155
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    const/4 v1, 0x0

    if-eqz v0, :cond_7

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    invoke-virtual {v0}, Ljava/lang/String;->isEmpty()Z

    move-result v0

    if-eqz v0, :cond_0

    goto/16 :goto_1

    .line 156
    :cond_0
    const/4 v0, 0x0

    .line 158
    .local v0, "c":Ljava/net/HttpURLConnection;
    :try_start_0
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    const-string v3, "/api/durum"

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    .line 159
    .local v2, "tam":Ljava/lang/String;
    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    const-string v4, "UTF-8"

    if-eqz v3, :cond_1

    :try_start_1
    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    invoke-virtual {v3}, Ljava/lang/String;->isEmpty()Z

    move-result v3

    if-nez v3, :cond_1

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v3, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    const-string v5, "?k="

    invoke-virtual {v3, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    iget-object v5, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    invoke-static {v5, v4}, Ljava/net/URLEncoder;->encode(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v5

    invoke-virtual {v3, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    move-object v2, v3

    .line 160
    :cond_1
    new-instance v3, Ljava/net/URL;

    invoke-direct {v3, v2}, Ljava/net/URL;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;

    move-result-object v3

    check-cast v3, Ljava/net/HttpURLConnection;

    move-object v0, v3

    .line 161
    const/16 v3, 0xfa0

    invoke-virtual {v0, v3}, Ljava/net/HttpURLConnection;->setConnectTimeout(I)V

    .line 162
    invoke-virtual {v0, v3}, Ljava/net/HttpURLConnection;->setReadTimeout(I)V

    .line 163
    const-string v3, "Cache-Control"

    const-string v5, "no-cache"

    invoke-virtual {v0, v3, v5}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    .line 164
    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->getResponseCode()I

    move-result v3
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    const/16 v5, 0xc8

    if-eq v3, v5, :cond_3

    .line 174
    if-eqz v0, :cond_2

    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->disconnect()V

    .line 164
    :cond_2
    return-object v1

    .line 165
    :cond_3
    :try_start_2
    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    .line 166
    .local v3, "sb":Ljava/lang/StringBuilder;
    new-instance v5, Ljava/io/BufferedReader;

    new-instance v6, Ljava/io/InputStreamReader;

    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->getInputStream()Ljava/io/InputStream;

    move-result-object v7

    invoke-direct {v6, v7, v4}, Ljava/io/InputStreamReader;-><init>(Ljava/io/InputStream;Ljava/lang/String;)V

    invoke-direct {v5, v6}, Ljava/io/BufferedReader;-><init>(Ljava/io/Reader;)V

    .line 168
    .local v5, "br":Ljava/io/BufferedReader;
    :goto_0
    invoke-virtual {v5}, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;

    move-result-object v4

    move-object v6, v4

    .local v6, "s":Ljava/lang/String;
    if-eqz v4, :cond_4

    invoke-virtual {v3, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    goto :goto_0

    .line 169
    :cond_4
    invoke-virtual {v5}, Ljava/io/BufferedReader;->close()V

    .line 170
    new-instance v4, Lorg/json/JSONObject;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v7

    invoke-direct {v4, v7}, Lorg/json/JSONObject;-><init>(Ljava/lang/String;)V
    :try_end_2
    .catchall {:try_start_2 .. :try_end_2} :catchall_0

    .line 174
    if-eqz v0, :cond_5

    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->disconnect()V

    .line 170
    :cond_5
    return-object v4

    .line 171
    .end local v2    # "tam":Ljava/lang/String;
    .end local v3    # "sb":Ljava/lang/StringBuilder;
    .end local v5    # "br":Ljava/io/BufferedReader;
    .end local v6    # "s":Ljava/lang/String;
    :catchall_0
    move-exception v2

    .line 172
    .local v2, "e":Ljava/lang/Throwable;
    nop

    .line 174
    if-eqz v0, :cond_6

    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->disconnect()V

    .line 172
    :cond_6
    return-object v1

    .line 155
    .end local v0    # "c":Ljava/net/HttpURLConnection;
    .end local v2    # "e":Ljava/lang/Throwable;
    :cond_7
    :goto_1
    return-object v1
.end method

.method private hesapKomut(Ljava/lang/String;I)Lorg/json/JSONObject;
    .locals 2
    .param p1, "ad"    # Ljava/lang/String;
    .param p2, "idx"    # I

    .line 408
    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->komutO(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    .line 409
    .local v0, "o":Lorg/json/JSONObject;
    :try_start_0
    const-string v1, "idx"

    invoke-virtual {v0, v1, p2}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v1

    .line 410
    :goto_0
    return-object v0
.end method

.method private ht()F
    .locals 2

    .line 484
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    if-nez v0, :cond_0

    const/high16 v0, 0x41100000    # 9.0f

    goto :goto_0

    :cond_0
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    const/4 v1, 0x2

    if-ne v0, v1, :cond_1

    const/high16 v0, 0x41500000    # 13.0f

    goto :goto_0

    :cond_1
    const/high16 v0, 0x41300000    # 11.0f

    :goto_0
    return v0
.end method

.method private hucre(Ljava/lang/String;II)Landroid/widget/TextView;
    .locals 8
    .param p1, "yazi"    # Ljava/lang/String;
    .param p2, "arka"    # I
    .param p3, "yaziRenk"    # I

    .line 487
    new-instance v0, Landroid/widget/TextView;

    invoke-direct {v0, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    .line 488
    .local v0, "t":Landroid/widget/TextView;
    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 489
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->ht()F

    move-result v1

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setTextSize(F)V

    .line 490
    const/16 v1, 0x11

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setGravity(I)V

    .line 491
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->hx()I

    move-result v1

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setWidth(I)V

    .line 492
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->hy()I

    move-result v1

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setHeight(I)V

    .line 493
    const/4 v1, 0x3

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    .line 494
    .local v1, "px":I
    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2, v1, v2}, Landroid/widget/TextView;->setPadding(IIII)V

    .line 495
    new-instance v3, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v4, -0x2

    invoke-direct {v3, v4, v4}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    .line 497
    .local v3, "lp":Landroid/widget/LinearLayout$LayoutParams;
    const/4 v4, 0x2

    invoke-direct {p0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v5

    invoke-direct {p0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v6

    invoke-direct {p0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v7

    invoke-direct {p0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v4

    invoke-virtual {v3, v5, v6, v7, v4}, Landroid/widget/LinearLayout$LayoutParams;->setMargins(IIII)V

    .line 498
    invoke-virtual {v0, v3}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 499
    invoke-direct {p0, v0, p2, p3, v2}, Lcom/abdulkadir/metin/OverlayServisi;->boya(Landroid/widget/TextView;IIZ)V

    .line 500
    return-object v0
.end method

.method private hucreEkle(Landroid/widget/LinearLayout;Ljava/lang/String;Ljava/lang/String;)V
    .locals 4
    .param p1, "cizgi"    # Landroid/widget/LinearLayout;
    .param p2, "an"    # Ljava/lang/String;
    .param p3, "ch"    # Ljava/lang/String;

    .line 287
    const v0, -0xd5cfc0

    const v1, -0xa59f8e

    invoke-direct {p0, p3, v0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->hucre(Ljava/lang/String;II)Landroid/widget/TextView;

    move-result-object v0

    .line 288
    .local v0, "h":Landroid/widget/TextView;
    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->hucreler:Ljava/util/Map;

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v2, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    const-string v3, ":"

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-interface {v1, v2, v0}, Ljava/util/Map;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    .line 289
    invoke-virtual {p1, v0}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 290
    return-void
.end method

.method private hx()I
    .locals 2

    .line 482
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    if-nez v0, :cond_0

    const/16 v0, 0x14

    goto :goto_0

    :cond_0
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    const/4 v1, 0x2

    if-ne v0, v1, :cond_1

    const/16 v0, 0x20

    goto :goto_0

    :cond_1
    const/16 v0, 0x1a

    :goto_0
    return v0
.end method

.method private hy()I
    .locals 2

    .line 483
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    if-nez v0, :cond_0

    const/16 v0, 0x11

    goto :goto_0

    :cond_0
    iget v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    const/4 v1, 0x2

    if-ne v0, v1, :cond_1

    const/16 v0, 0x1b

    goto :goto_0

    :cond_1
    const/16 v0, 0x16

    :goto_0
    return v0
.end method

.method private kanalKomut(Ljava/lang/String;I)Lorg/json/JSONObject;
    .locals 2
    .param p1, "ad"    # Ljava/lang/String;
    .param p2, "kanal"    # I

    .line 414
    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->komutO(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    .line 415
    .local v0, "o":Lorg/json/JSONObject;
    :try_start_0
    const-string v1, "kanal"

    invoke-virtual {v0, v1, p2}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v1

    .line 416
    :goto_0
    return-object v0
.end method

.method private kapatHucre()Landroid/widget/TextView;
    .locals 3

    .line 318
    const/4 v0, 0x0

    const v1, -0x948f80

    const-string v2, "\u00d7"

    invoke-direct {p0, v2, v0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->hucre(Ljava/lang/String;II)Landroid/widget/TextView;

    move-result-object v0

    .line 319
    .local v0, "kapat":Landroid/widget/TextView;
    new-instance v1, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda7;

    invoke-direct {v1, p0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda7;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    .line 320
    return-object v0
.end method

.method private komut(Lorg/json/JSONObject;)V
    .locals 2
    .param p1, "o"    # Lorg/json/JSONObject;

    .line 180
    new-instance v0, Ljava/lang/Thread;

    new-instance v1, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda6;

    invoke-direct {v1, p0, p1}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda6;-><init>(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V

    invoke-direct {v0, v1}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V

    .line 203
    invoke-virtual {v0}, Ljava/lang/Thread;->start()V

    .line 204
    return-void
.end method

.method private komutO(Ljava/lang/String;)Lorg/json/JSONObject;
    .locals 2
    .param p1, "ad"    # Ljava/lang/String;

    .line 207
    new-instance v0, Lorg/json/JSONObject;

    invoke-direct {v0}, Lorg/json/JSONObject;-><init>()V

    .line 208
    .local v0, "o":Lorg/json/JSONObject;
    :try_start_0
    const-string v1, "komut"

    invoke-virtual {v0, v1, p1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v1

    .line 209
    :goto_0
    return-object v0
.end method

.method private kur(Lorg/json/JSONObject;Ljava/util/List;)V
    .locals 9
    .param p1, "adalar"    # Lorg/json/JSONObject;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Lorg/json/JSONObject;",
            "Ljava/util/List<",
            "Ljava/lang/String;",
            ">;)V"
        }
    .end annotation

    .line 250
    .local p2, "adaAnahtar":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v0}, Landroid/widget/LinearLayout;->removeAllViews()V

    .line 251
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->hucreler:Ljava/util/Map;

    invoke-interface {v0}, Ljava/util/Map;->clear()V

    .line 252
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    const/4 v2, 0x1

    xor-int/2addr v1, v2

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 253
    move-object v0, p2

    .line 254
    .local v0, "adalarKul":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekAda:Z

    if-eqz v1, :cond_0

    invoke-interface {v0}, Ljava/util/List;->isEmpty()Z

    move-result v1

    if-nez v1, :cond_0

    const/4 v1, 0x0

    invoke-interface {v0, v1, v2}, Ljava/util/List;->subList(II)Ljava/util/List;

    move-result-object v0

    .line 256
    :cond_0
    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekSatir:Z

    if-eqz v1, :cond_5

    .line 257
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->cizgiYap()Landroid/widget/LinearLayout;

    move-result-object v1

    .line 258
    .local v1, "cizgi":Landroid/widget/LinearLayout;
    const/4 v2, 0x1

    .line 259
    .local v2, "ilkAda":Z
    invoke-interface {v0}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v3

    :goto_0
    invoke-interface {v3}, Ljava/util/Iterator;->hasNext()Z

    move-result v4

    if-eqz v4, :cond_4

    invoke-interface {v3}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v4

    check-cast v4, Ljava/lang/String;

    .line 260
    .local v4, "an":Ljava/lang/String;
    invoke-direct {p0, p1, v4}, Lcom/abdulkadir/metin/OverlayServisi;->chAnahtarlari(Lorg/json/JSONObject;Ljava/lang/String;)Ljava/util/List;

    move-result-object v5

    .line 261
    .local v5, "chl":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    invoke-interface {v5}, Ljava/util/List;->isEmpty()Z

    move-result v6

    if-eqz v6, :cond_1

    goto :goto_0

    .line 262
    :cond_1
    if-nez v2, :cond_2

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->ayirac()Landroid/view/View;

    move-result-object v6

    invoke-virtual {v1, v6}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 263
    :cond_2
    invoke-interface {v5}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v6

    :goto_1
    invoke-interface {v6}, Ljava/util/Iterator;->hasNext()Z

    move-result v7

    if-eqz v7, :cond_3

    invoke-interface {v6}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v7

    check-cast v7, Ljava/lang/String;

    .local v7, "ch":Ljava/lang/String;
    invoke-direct {p0, v1, v4, v7}, Lcom/abdulkadir/metin/OverlayServisi;->hucreEkle(Landroid/widget/LinearLayout;Ljava/lang/String;Ljava/lang/String;)V

    .end local v7    # "ch":Ljava/lang/String;
    goto :goto_1

    .line 264
    :cond_3
    const/4 v2, 0x0

    .line 265
    .end local v4    # "an":Ljava/lang/String;
    .end local v5    # "chl":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    goto :goto_0

    .line 266
    :cond_4
    .line 268
    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v3, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 269
    .end local v1    # "cizgi":Landroid/widget/LinearLayout;
    .end local v2    # "ilkAda":Z
    goto :goto_5

    .line 270
    :cond_5
    const/4 v1, 0x1

    .line 271
    .local v1, "ilk":Z
    invoke-interface {v0}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v2

    :goto_2
    invoke-interface {v2}, Ljava/util/Iterator;->hasNext()Z

    move-result v3

    if-eqz v3, :cond_a

    invoke-interface {v2}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v3

    check-cast v3, Ljava/lang/String;

    .line 272
    .local v3, "an":Ljava/lang/String;
    invoke-direct {p0, p1, v3}, Lcom/abdulkadir/metin/OverlayServisi;->chAnahtarlari(Lorg/json/JSONObject;Ljava/lang/String;)Ljava/util/List;

    move-result-object v4

    .line 273
    .local v4, "chl":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    invoke-interface {v4}, Ljava/util/List;->isEmpty()Z

    move-result v5

    if-eqz v5, :cond_6

    goto :goto_2

    .line 274
    :cond_6
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->cizgiYap()Landroid/widget/LinearLayout;

    move-result-object v5

    .line 275
    .local v5, "cizgi":Landroid/widget/LinearLayout;
    invoke-interface {v4}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    move-result-object v6

    :goto_3
    invoke-interface {v6}, Ljava/util/Iterator;->hasNext()Z

    move-result v7

    if-eqz v7, :cond_7

    invoke-interface {v6}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v7

    check-cast v7, Ljava/lang/String;

    .restart local v7    # "ch":Ljava/lang/String;
    invoke-direct {p0, v5, v3, v7}, Lcom/abdulkadir/metin/OverlayServisi;->hucreEkle(Landroid/widget/LinearLayout;Ljava/lang/String;Ljava/lang/String;)V

    .end local v7    # "ch":Ljava/lang/String;
    goto :goto_3

    .line 276
    :cond_7
    :cond_8
    new-instance v6, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v7, -0x2

    invoke-direct {v6, v7, v7}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    .line 280
    .local v6, "lp":Landroid/widget/LinearLayout$LayoutParams;
    iget-boolean v7, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    const/4 v8, 0x2

    if-eqz v7, :cond_9

    invoke-direct {p0, v8}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v7

    iput v7, v6, Landroid/widget/LinearLayout$LayoutParams;->leftMargin:I

    goto :goto_4

    :cond_9
    invoke-direct {p0, v8}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v7

    iput v7, v6, Landroid/widget/LinearLayout$LayoutParams;->topMargin:I

    .line 281
    :goto_4
    iget-object v7, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v7, v5, v6}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    .line 282
    .end local v3    # "an":Ljava/lang/String;
    .end local v4    # "chl":Ljava/util/List;, "Ljava/util/List<Ljava/lang/String;>;"
    .end local v5    # "cizgi":Landroid/widget/LinearLayout;
    .end local v6    # "lp":Landroid/widget/LinearLayout$LayoutParams;
    goto :goto_2

    .line 284
    .end local v1    # "ilk":Z
    :cond_a
    :goto_5
    return-void
.end method

.method private synthetic lambda$basla$0(Lorg/json/JSONObject;)V
    .locals 0
    .param p1, "d"    # Lorg/json/JSONObject;

    .line 145
    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->ciz(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$basla$1()V
    .locals 3

    .line 143
    nop

    :goto_0
    iget-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->calisiyor:Z

    if-eqz v0, :cond_1

    .line 144
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->getir()Lorg/json/JSONObject;

    move-result-object v0

    .line 145
    .local v0, "d":Lorg/json/JSONObject;
    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->el:Landroid/os/Handler;

    new-instance v2, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda11;

    invoke-direct {v2, p0, v0}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda11;-><init>(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V

    invoke-virtual {v1, v2}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    .line 146
    :cond_0
    const-wide/16 v1, 0x7d0

    :try_start_0
    invoke-static {v1, v2}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {:try_start_0 .. :try_end_0} :catch_0

    .line 147
    .end local v0    # "d":Lorg/json/JSONObject;
    goto :goto_0

    .line 146
    .restart local v0    # "d":Lorg/json/JSONObject;
    :catch_0
    move-exception v1

    .line 148
    .end local v0    # "d":Lorg/json/JSONObject;
    :cond_1
    return-void
.end method

.method static synthetic lambda$chAnahtarlari$4(Ljava/lang/String;Ljava/lang/String;)I
    .locals 2
    .param p0, "a"    # Ljava/lang/String;
    .param p1, "b"    # Ljava/lang/String;

    .line 303
    invoke-static {p0}, Lcom/abdulkadir/metin/OverlayServisi;->pint(Ljava/lang/String;)I

    move-result v0

    invoke-static {p1}, Lcom/abdulkadir/metin/OverlayServisi;->pint(Ljava/lang/String;)I

    move-result v1

    invoke-static {v0, v1}, Ljava/lang/Integer;->compare(II)I

    move-result v0

    return v0
.end method

.method private synthetic lambda$detayCiz$10(ILandroid/view/View;)V
    .locals 1
    .param p1, "idx"    # I
    .param p2, "v"    # Landroid/view/View;

    .line 382
    const-string v0, "baslat_hesap"

    invoke-direct {p0, v0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->hesapKomut(Ljava/lang/String;I)Lorg/json/JSONObject;

    move-result-object v0

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komut(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$detayCiz$11(ILandroid/view/View;)V
    .locals 1
    .param p1, "kanal"    # I
    .param p2, "v"    # Landroid/view/View;

    .line 400
    const-string v0, "buff_cek"

    invoke-direct {p0, v0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->kanalKomut(Ljava/lang/String;I)Lorg/json/JSONObject;

    move-result-object v0

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komut(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$detayCiz$7(Landroid/view/View;)V
    .locals 1
    .param p1, "v"    # Landroid/view/View;

    .line 356
    const-string v0, "baslat"

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komutO(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komut(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$detayCiz$8(Landroid/view/View;)V
    .locals 1
    .param p1, "v"    # Landroid/view/View;

    .line 357
    const-string v0, "durdur"

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komutO(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komut(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$detayCiz$9(ILandroid/view/View;)V
    .locals 1
    .param p1, "idx"    # I
    .param p2, "v"    # Landroid/view/View;

    .line 379
    const-string v0, "durdur_hesap"

    invoke-direct {p0, v0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->hesapKomut(Ljava/lang/String;I)Lorg/json/JSONObject;

    move-result-object v0

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->komut(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$detayHucre$5(Landroid/view/View;)V
    .locals 2
    .param p1, "v"    # Landroid/view/View;

    .line 310
    iget-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    xor-int/lit8 v0, v0, 0x1

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    .line 311
    iget-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    if-eqz v0, :cond_0

    const/4 v1, 0x1

    invoke-static {p0, v1}, Lcom/abdulkadir/metin7x/OverlayWindowSizing;->apply(Landroid/content/Context;Z)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->sonVeri:Lorg/json/JSONObject;

    if-eqz v0, :vpn_local

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->detayYukseklikAyarla()V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/widget/ScrollView;->setVisibility(I)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->sonVeri:Lorg/json/JSONObject;

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->detayCiz(Lorg/json/JSONObject;)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    const/4 v1, 0x0

    invoke-virtual {v0, v1, v1}, Landroid/widget/ScrollView;->scrollTo(II)V

    goto :goto_0

    :vpn_local
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->detayYukseklikAyarla()V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/widget/ScrollView;->setVisibility(I)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-static {p0, v0}, Lcom/abdulkadir/metin7x/Overlay7xControls;->showLocal(Landroid/content/Context;Landroid/widget/LinearLayout;)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    const/4 v1, 0x0

    invoke-virtual {v0, v1, v1}, Landroid/widget/ScrollView;->scrollTo(II)V

    goto :goto_0

    .line 312
    :cond_0
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    const/16 v1, 0x8

    invoke-virtual {v0, v1}, Landroid/widget/ScrollView;->setVisibility(I)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v0}, Landroid/widget/LinearLayout;->removeAllViews()V

    const/4 v0, 0x0

    invoke-static {p0, v0}, Lcom/abdulkadir/metin7x/OverlayWindowSizing;->apply(Landroid/content/Context;Z)V

    .line 313
    :goto_0
    return-void
.end method

.method private synthetic lambda$kapatHucre$6(Landroid/view/View;)V
    .locals 0
    .param p1, "v"    # Landroid/view/View;

    .line 319
    invoke-virtual {p0}, Lcom/abdulkadir/metin/OverlayServisi;->stopSelf()V

    return-void
.end method

.method private synthetic lambda$komut$2(Lorg/json/JSONObject;)V
    .locals 0
    .param p1, "d"    # Lorg/json/JSONObject;

    .line 202
    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi;->ciz(Lorg/json/JSONObject;)V

    return-void
.end method

.method private synthetic lambda$komut$3(Lorg/json/JSONObject;)V
    .locals 5
    .param p1, "o"    # Lorg/json/JSONObject;

    .line 181
    const/4 v0, 0x0

    .line 183
    .local v0, "c":Ljava/net/HttpURLConnection;
    :try_start_0
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "/api/komut"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    .line 184
    .local v1, "tam":Ljava/lang/String;
    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    const-string v3, "UTF-8"

    if-eqz v2, :cond_0

    :try_start_1
    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    invoke-virtual {v2}, Ljava/lang/String;->isEmpty()Z

    move-result v2

    if-nez v2, :cond_0

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    const-string v4, "?k="

    invoke-virtual {v2, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    iget-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    invoke-static {v4, v3}, Ljava/net/URLEncoder;->encode(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v2, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    move-object v1, v2

    .line 185
    :cond_0
    new-instance v2, Ljava/net/URL;

    invoke-direct {v2, v1}, Ljava/net/URL;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;

    move-result-object v2

    check-cast v2, Ljava/net/HttpURLConnection;

    move-object v0, v2

    .line 186
    const/16 v2, 0xfa0

    invoke-virtual {v0, v2}, Ljava/net/HttpURLConnection;->setConnectTimeout(I)V

    .line 187
    invoke-virtual {v0, v2}, Ljava/net/HttpURLConnection;->setReadTimeout(I)V

    .line 188
    const-string v2, "POST"

    invoke-virtual {v0, v2}, Ljava/net/HttpURLConnection;->setRequestMethod(Ljava/lang/String;)V

    .line 189
    const/4 v2, 0x1

    invoke-virtual {v0, v2}, Ljava/net/HttpURLConnection;->setDoOutput(Z)V

    .line 190
    const-string v2, "Content-Type"

    const-string v4, "application/json"

    invoke-virtual {v0, v2, v4}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    .line 191
    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->getOutputStream()Ljava/io/OutputStream;

    move-result-object v2

    .line 192
    .local v2, "os":Ljava/io/OutputStream;
    invoke-virtual {p1}, Lorg/json/JSONObject;->toString()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v4, v3}, Ljava/lang/String;->getBytes(Ljava/lang/String;)[B

    move-result-object v3

    invoke-virtual {v2, v3}, Ljava/io/OutputStream;->write([B)V

    .line 193
    invoke-virtual {v2}, Ljava/io/OutputStream;->close()V

    .line 194
    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->getResponseCode()I
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    .line 197
    nop

    .end local v1    # "tam":Ljava/lang/String;
    .end local v2    # "os":Ljava/io/OutputStream;
    if-eqz v0, :cond_1

    :goto_0
    invoke-virtual {v0}, Ljava/net/HttpURLConnection;->disconnect()V

    goto :goto_1

    .line 195
    :catchall_0
    move-exception v1

    .line 197
    if-eqz v0, :cond_1

    goto :goto_0

    .line 200
    :cond_1
    :goto_1
    const-wide/16 v1, 0x190

    :try_start_2
    invoke-static {v1, v2}, Ljava/lang/Thread;->sleep(J)V
    :try_end_2
    .catch Ljava/lang/InterruptedException; {:try_start_2 .. :try_end_2} :catch_0

    goto :goto_2

    :catch_0
    move-exception v1

    .line 201
    :goto_2
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->getir()Lorg/json/JSONObject;

    move-result-object v1

    .line 202
    .local v1, "d":Lorg/json/JSONObject;
    if-eqz v1, :cond_2

    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi;->el:Landroid/os/Handler;

    new-instance v3, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda8;

    invoke-direct {v3, p0, v1}, Lcom/abdulkadir/metin/OverlayServisi$$ExternalSyntheticLambda8;-><init>(Lcom/abdulkadir/metin/OverlayServisi;Lorg/json/JSONObject;)V

    invoke-virtual {v2, v3}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    .line 203
    :cond_2
    return-void
.end method

.method private onForegroundBaslat()V
    .locals 5

    .line 535
    const-string v0, "metin_overlay"

    .line 536
    .local v0, "kanal":Ljava/lang/String;
    nop

    .line 537
    const-class v1, Landroid/app/NotificationManager;

    invoke-virtual {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Landroid/app/NotificationManager;

    .line 538
    .local v1, "nm":Landroid/app/NotificationManager;
    const/4 v2, 0x1

    if-eqz v1, :cond_0

    invoke-virtual {v1, v0}, Landroid/app/NotificationManager;->getNotificationChannel(Ljava/lang/String;)Landroid/app/NotificationChannel;

    move-result-object v3

    if-nez v3, :cond_0

    .line 539
    new-instance v3, Landroid/app/NotificationChannel;

    const-string v4, "Metin \u00e7ubu\u011fu"

    invoke-direct {v3, v0, v4, v2}, Landroid/app/NotificationChannel;-><init>(Ljava/lang/String;Ljava/lang/CharSequence;I)V

    invoke-virtual {v1, v3}, Landroid/app/NotificationManager;->createNotificationChannel(Landroid/app/NotificationChannel;)V

    .line 543
    .end local v1    # "nm":Landroid/app/NotificationManager;
    :cond_0
    nop

    .line 544
    new-instance v1, Landroid/app/Notification$Builder;

    invoke-direct {v1, p0, v0}, Landroid/app/Notification$Builder;-><init>(Landroid/content/Context;Ljava/lang/String;)V

    .line 545
    nop

    .line 546
    .local v1, "b":Landroid/app/Notification$Builder;
    const-string v3, "Metin \u00e7ubu\u011fu a\u00e7\u0131k"

    invoke-virtual {v1, v3}, Landroid/app/Notification$Builder;->setContentTitle(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;

    move-result-object v3

    sget v4, Lcom/abdulkadir/metin/R$drawable;->ic_metin:I

    .line 547
    invoke-virtual {v3, v4}, Landroid/app/Notification$Builder;->setSmallIcon(I)Landroid/app/Notification$Builder;

    move-result-object v3

    .line 548
    invoke-virtual {v3, v2}, Landroid/app/Notification$Builder;->setOngoing(Z)Landroid/app/Notification$Builder;

    move-result-object v2

    .line 549
    invoke-virtual {v2}, Landroid/app/Notification$Builder;->build()Landroid/app/Notification;

    move-result-object v2

    .line 550
    .local v2, "n":Landroid/app/Notification;
    const/16 v3, 0x76c

    invoke-virtual {p0, v3, v2}, Lcom/abdulkadir/metin/OverlayServisi;->startForeground(ILandroid/app/Notification;)V

    .line 551
    return-void
.end method

.method private static pint(Ljava/lang/String;)I
    .locals 2
    .param p0, "s"    # Ljava/lang/String;

    .line 561
    :try_start_0
    invoke-virtual {p0}, Ljava/lang/String;->trim()Ljava/lang/String;

    move-result-object v0

    invoke-static {v0}, Ljava/lang/Integer;->parseInt(Ljava/lang/String;)I

    move-result v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    return v0

    :catchall_0
    move-exception v0

    .local v0, "e":Ljava/lang/Throwable;
    const/4 v1, 0x0

    return v1
.end method

.method private renk(Lorg/json/JSONObject;)I
    .locals 7
    .param p1, "ch"    # Lorg/json/JSONObject;

    .line 335
    const v0, -0xd5cfc0

    if-nez p1, :cond_0

    return v0

    .line 336
    :cond_0
    const-string v1, "metinler"

    invoke-virtual {p1, v1}, Lorg/json/JSONObject;->optJSONArray(Ljava/lang/String;)Lorg/json/JSONArray;

    move-result-object v1

    .line 337
    .local v1, "mt":Lorg/json/JSONArray;
    if-eqz v1, :cond_7

    invoke-virtual {v1}, Lorg/json/JSONArray;->length()I

    move-result v2

    if-nez v2, :cond_1

    goto :goto_3

    .line 338
    :cond_1
    const/4 v0, 0x0

    .line 339
    .local v0, "turuncu":Z
    const/4 v2, 0x0

    .local v2, "i":I
    :goto_0
    invoke-virtual {v1}, Lorg/json/JSONArray;->length()I

    move-result v3

    const/16 v4, -0x4fe0

    if-ge v2, v3, :cond_5

    .line 340
    invoke-virtual {v1, v2}, Lorg/json/JSONArray;->optJSONObject(I)Lorg/json/JSONObject;

    move-result-object v3

    .line 341
    .local v3, "m":Lorg/json/JSONObject;
    if-nez v3, :cond_2

    goto :goto_1

    .line 342
    :cond_2
    const-string v5, "kesiliyor"

    const/4 v6, 0x0

    invoke-virtual {v3, v5, v6}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result v5

    if-eqz v5, :cond_3

    return v4

    .line 343
    :cond_3
    const-string v4, "oyuncu"

    invoke-virtual {v3, v4}, Lorg/json/JSONObject;->opt(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v4

    .line 344
    .local v4, "oy":Ljava/lang/Object;
    if-eqz v4, :cond_4

    sget-object v5, Lorg/json/JSONObject;->NULL:Ljava/lang/Object;

    invoke-virtual {v5, v4}, Ljava/lang/Object;->equals(Ljava/lang/Object;)Z

    move-result v5

    if-nez v5, :cond_4

    const-string v5, ""

    invoke-virtual {v5, v4}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v5

    if-nez v5, :cond_4

    const/4 v0, 0x1

    .line 339
    .end local v3    # "m":Lorg/json/JSONObject;
    .end local v4    # "oy":Ljava/lang/Object;
    :cond_4
    :goto_1
    add-int/lit8 v2, v2, 0x1

    goto :goto_0

    .line 346
    .end local v2    # "i":I
    :cond_5
    if-eqz v0, :cond_6

    goto :goto_2

    :cond_6
    const v4, -0xc82986

    :goto_2
    return v4

    .line 337
    .end local v0    # "turuncu":Z
    :cond_7
    :goto_3
    return v0
.end method

.method private yatayCubuk()Landroid/widget/LinearLayout;
    .locals 4

    .line 420
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    .line 421
    .local v0, "s":Landroid/widget/LinearLayout;
    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 422
    const/16 v1, 0x10

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setGravity(I)V

    .line 423
    new-instance v1, Landroid/widget/LinearLayout$LayoutParams;

    const/4 v2, -0x1

    const/4 v3, -0x2

    invoke-direct {v1, v2, v3}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V

    .line 426
    .local v1, "lp":Landroid/widget/LinearLayout$LayoutParams;
    const/4 v2, 0x3

    invoke-direct {p0, v2}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v2

    iput v2, v1, Landroid/widget/LinearLayout$LayoutParams;->topMargin:I

    .line 427
    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 428
    return-object v0
.end method


# virtual methods
.method public onBind(Landroid/content/Intent;)Landroid/os/IBinder;
    .locals 1
    .param p1, "i"    # Landroid/content/Intent;

    .line 81
    const/4 v0, 0x0

    return-object v0
.end method

.method public onCreate()V
    .locals 11

    .line 84
    invoke-super {p0}, Landroid/app/Service;->onCreate()V

    .line 85
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->onForegroundBaslat()V

    .line 86
    const-class v0, Landroid/view/WindowManager;

    invoke-virtual {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Landroid/view/WindowManager;

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->wm:Landroid/view/WindowManager;

    .line 88
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    .line 89
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    const/4 v1, 0x1

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 90
    new-instance v0, Landroid/graphics/drawable/GradientDrawable;

    invoke-direct {v0}, Landroid/graphics/drawable/GradientDrawable;-><init>()V

    move-object v2, v0

    .line 91
    .local v2, "arka":Landroid/graphics/drawable/GradientDrawable;
    const v0, -0x19f5f2ec

    invoke-virtual {v2, v0}, Landroid/graphics/drawable/GradientDrawable;->setColor(I)V

    .line 92
    const/16 v0, 0xa

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v0

    int-to-float v0, v0

    invoke-virtual {v2, v0}, Landroid/graphics/drawable/GradientDrawable;->setCornerRadius(F)V

    .line 93
    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v0

    const v3, -0xdcd7c8

    invoke-virtual {v2, v0, v3}, Landroid/graphics/drawable/GradientDrawable;->setStroke(II)V

    .line 94
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v2}, Landroid/widget/LinearLayout;->setBackground(Landroid/graphics/drawable/Drawable;)V

    .line 95
    const/4 v0, 0x5

    invoke-direct {p0, v0}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v3

    .line 96
    .local v3, "p":I
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v3, v3, v3, v3}, Landroid/widget/LinearLayout;->setPadding(IIII)V

    .line 97
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    new-instance v4, Lcom/abdulkadir/metin/OverlayServisi$Surukle;

    const/4 v5, 0x0

    invoke-direct {v4, p0, v5}, Lcom/abdulkadir/metin/OverlayServisi$Surukle;-><init>(Lcom/abdulkadir/metin/OverlayServisi;Lcom/abdulkadir/metin/OverlayServisi-IA;)V

    invoke-virtual {v0, v4}, Landroid/widget/LinearLayout;->setOnTouchListener(Landroid/view/View$OnTouchListener;)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    invoke-static {p0, v0}, Lcom/abdulkadir/metin7x/Overlay7xControls;->addMiniRow(Landroid/content/Context;Landroid/widget/LinearLayout;)V

    .line 99
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    .line 100
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 101
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    iget-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 103
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    .line 104
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V

    .line 105
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setVisibility(I)V

    .line 106
    new-instance v4, Landroid/widget/ScrollView;

    invoke-direct {v4, p0}, Landroid/widget/ScrollView;-><init>(Landroid/content/Context;)V

    iput-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-virtual {v4, v0}, Landroid/widget/ScrollView;->addView(Landroid/view/View;)V

    const/16 v0, 0x8

    invoke-virtual {v4, v0}, Landroid/widget/ScrollView;->setVisibility(I)V

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v4}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    iget-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayKutu:Landroid/widget/LinearLayout;

    invoke-static {p0, v4}, Lcom/abdulkadir/metin7x/Overlay7xControls;->showLocal(Landroid/content/Context;Landroid/widget/LinearLayout;)V

    const/4 v4, 0x0

    iput-boolean v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayAcik:Z

    .line 108
    new-instance v5, Landroid/view/WindowManager$LayoutParams;

    const/16 v9, 0x208

    const/4 v10, -0x3

    const/4 v6, -0x2

    const/4 v7, -0x2

    const/16 v8, 0x7f6

    invoke-direct/range {v5 .. v10}, Landroid/view/WindowManager$LayoutParams;-><init>(IIIII)V

    iput-object v5, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    .line 115
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    const v4, 0x800035

    iput v4, v0, Landroid/view/WindowManager$LayoutParams;->gravity:I

    .line 116
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    const/4 v1, 0x6

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    iput v1, v0, Landroid/view/WindowManager$LayoutParams;->x:I

    .line 117
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    const/16 v1, 0x28

    invoke-direct {p0, v1}, Lcom/abdulkadir/metin/OverlayServisi;->dp(I)I

    move-result v1

    iput v1, v0, Landroid/view/WindowManager$LayoutParams;->y:I

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->detayScroll:Landroid/widget/ScrollView;

    invoke-static {p0, v0}, Lcom/abdulkadir/metin7x/OverlayDragSupport;->install(Landroid/content/Context;Landroid/widget/ScrollView;)V

    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->detayYukseklikAyarla()V

    .line 119
    new-instance v0, Landroid/widget/LinearLayout;

    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    move-object v1, v0

    .line 120
    .local v1, "satir":Landroid/widget/LinearLayout;
    const v0, -0xd5cfc0

    const v4, -0xa59f8e

    const-string v5, "\u2026"

    invoke-direct {p0, v5, v0, v4}, Lcom/abdulkadir/metin/OverlayServisi;->hucre(Ljava/lang/String;II)Landroid/widget/TextView;

    move-result-object v0

    invoke-virtual {v1, v0}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 121
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->kok:Landroid/widget/LinearLayout;

    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    .line 122
    :try_start_0
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->wm:Landroid/view/WindowManager;

    iget-object v4, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    iget-object v5, p0, Lcom/abdulkadir/metin/OverlayServisi;->pencere:Landroid/view/WindowManager$LayoutParams;

    invoke-interface {v0, v4, v5}, Landroid/view/WindowManager;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v0

    .line 123
    :goto_0
    return-void
.end method

.method public onDestroy()V
    .locals 2

    .line 554
    const/4 v0, 0x0

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->calisiyor:Z

    .line 555
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->yoklayici:Ljava/lang/Thread;

    if-eqz v0, :cond_0

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->yoklayici:Ljava/lang/Thread;

    invoke-virtual {v0}, Ljava/lang/Thread;->interrupt()V

    .line 556
    :cond_0
    :try_start_0
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    if-eqz v0, :cond_1

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->wm:Landroid/view/WindowManager;

    iget-object v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->disKok:Landroid/widget/LinearLayout;

    invoke-interface {v0, v1}, Landroid/view/WindowManager;->removeView(Landroid/view/View;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v0

    .line 557
    :cond_1
    :goto_0
    invoke-super {p0}, Landroid/app/Service;->onDestroy()V

    .line 558
    return-void
.end method

.method public onStartCommand(Landroid/content/Intent;II)I
    .locals 2
    .param p1, "i"    # Landroid/content/Intent;
    .param p2, "flags"    # I
    .param p3, "startId"    # I

    .line 126
    if-eqz p1, :cond_2

    .line 127
    const-string v0, "url"

    invoke-virtual {p1, v0}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    if-eqz v1, :cond_0

    invoke-virtual {p1, v0}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->url:Ljava/lang/String;

    .line 128
    :cond_0
    const-string v0, "k"

    invoke-virtual {p1, v0}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    if-eqz v1, :cond_1

    invoke-virtual {p1, v0}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->k:Ljava/lang/String;

    .line 129
    :cond_1
    const-string v0, "boyut"

    iget v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    invoke-virtual {p1, v0, v1}, Landroid/content/Intent;->getIntExtra(Ljava/lang/String;I)I

    move-result v0

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->boyut:I

    .line 130
    const-string v0, "tekSatir"

    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekSatir:Z

    invoke-virtual {p1, v0, v1}, Landroid/content/Intent;->getBooleanExtra(Ljava/lang/String;Z)Z

    move-result v0

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekSatir:Z

    .line 131
    const-string v0, "tekAda"

    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekAda:Z

    invoke-virtual {p1, v0, v1}, Landroid/content/Intent;->getBooleanExtra(Ljava/lang/String;Z)Z

    move-result v0

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->tekAda:Z

    .line 132
    const-string v0, "dikey"

    iget-boolean v1, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    invoke-virtual {p1, v0, v1}, Landroid/content/Intent;->getBooleanExtra(Ljava/lang/String;Z)Z

    move-result v0

    iput-boolean v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->dikey:Z

    .line 133
    const-string v0, ""

    iput-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi;->yapiImzasi:Ljava/lang/String;

    .line 135
    :cond_2
    invoke-direct {p0}, Lcom/abdulkadir/metin/OverlayServisi;->basla()V

    .line 136
    const/4 v0, 0x1

    return v0
.end method
