.class final Lcom/abdulkadir/metin/OverlayServisi$Surukle;
.super Ljava/lang/Object;
.source "OverlayServisi.java"

# interfaces
.implements Landroid/view/View$OnTouchListener;


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/abdulkadir/metin/OverlayServisi;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x12
    name = "Surukle"
.end annotation


# instance fields
.field private bx:I

.field private by:I

.field private dx:F

.field private dy:F

.field final synthetic this$0:Lcom/abdulkadir/metin/OverlayServisi;


# direct methods
.method private constructor <init>(Lcom/abdulkadir/metin/OverlayServisi;)V
    .locals 0
    .annotation system Ldalvik/annotation/MethodParameters;
        accessFlags = {
            0x1010
        }
        names = {
            null
        }
    .end annotation

    .line 513
    iput-object p1, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method synthetic constructor <init>(Lcom/abdulkadir/metin/OverlayServisi;Lcom/abdulkadir/metin/OverlayServisi-IA;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/abdulkadir/metin/OverlayServisi$Surukle;-><init>(Lcom/abdulkadir/metin/OverlayServisi;)V

    return-void
.end method


# virtual methods
.method public onTouch(Landroid/view/View;Landroid/view/MotionEvent;)Z
    .locals 5
    .param p1, "v"    # Landroid/view/View;
    .param p2, "e"    # Landroid/view/MotionEvent;

    .line 517
    invoke-virtual {p2}, Landroid/view/MotionEvent;->getAction()I

    move-result v0

    const/4 v1, 0x1

    packed-switch v0, :pswitch_data_0

    .line 528
    :pswitch_0
    const/4 v0, 0x0

    return v0

    .line 523
    :pswitch_1
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v0}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;

    move-result-object v0

    iget v2, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->bx:I

    invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawX()F

    move-result v3

    iget v4, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->dx:F

    sub-float/2addr v3, v4

    float-to-int v3, v3

    sub-int/2addr v2, v3

    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    const/4 v4, 0x0

    invoke-static {v3, v2, v4}, Lcom/abdulkadir/metin7x/OverlayDragSupport;->clamp(Landroid/content/Context;IZ)I

    move-result v2

    iput v2, v0, Landroid/view/WindowManager$LayoutParams;->x:I

    .line 524
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v0}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;

    move-result-object v0

    iget v2, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->by:I

    invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawY()F

    move-result v3

    iget v4, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->dy:F

    sub-float/2addr v3, v4

    float-to-int v3, v3

    add-int/2addr v2, v3

    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    const/4 v4, 0x1

    invoke-static {v3, v2, v4}, Lcom/abdulkadir/metin7x/OverlayDragSupport;->clamp(Landroid/content/Context;IZ)I

    move-result v2

    iput v2, v0, Landroid/view/WindowManager$LayoutParams;->y:I

    .line 525
    :try_start_0
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v0}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetwm(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager;

    move-result-object v0

    iget-object v2, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v2}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetdisKok(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/widget/LinearLayout;

    move-result-object v2

    iget-object v3, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v3}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;

    move-result-object v3

    invoke-interface {v0, v2, v3}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v0

    .line 526
    :goto_0
    return v1

    .line 519
    :pswitch_2
    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v0}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;

    move-result-object v0

    iget v0, v0, Landroid/view/WindowManager$LayoutParams;->x:I

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->bx:I

    iget-object v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->this$0:Lcom/abdulkadir/metin/OverlayServisi;

    invoke-static {v0}, Lcom/abdulkadir/metin/OverlayServisi;->-$$Nest$fgetpencere(Lcom/abdulkadir/metin/OverlayServisi;)Landroid/view/WindowManager$LayoutParams;

    move-result-object v0

    iget v0, v0, Landroid/view/WindowManager$LayoutParams;->y:I

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->by:I

    .line 520
    invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawX()F

    move-result v0

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->dx:F

    invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawY()F

    move-result v0

    iput v0, p0, Lcom/abdulkadir/metin/OverlayServisi$Surukle;->dy:F

    .line 521
    return v1

    nop

    :pswitch_data_0
    .packed-switch 0x0
        :pswitch_2
        :pswitch_0
        :pswitch_1
    .end packed-switch
.end method
