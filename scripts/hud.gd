extends CanvasLayer
# Ekran arayüzü: sol üstte seviye/can/mana/XP/altın, sağ üstte çanta,
# sol altta joystick, sağ altta SALDIR ve İKSİR tuşları.

var _hp_bar: ProgressBar
var _mp_bar: ProgressBar
var _xp_bar: ProgressBar
var _level_lbl: Label
var _gold_lbl: Label
var _inv_panel: Panel
var _inv_list: VBoxContainer


func _ready() -> void:
    _build_stats()
    _build_controls()
    _build_inventory()
    GameState.stats_changed.connect(_refresh)
    GameState.inventory_changed.connect(_refresh_inventory)
    GameState.leveled_up.connect(_on_level_up)
    _refresh()
    _refresh_inventory()


# ---------- üst sol istatistikler ----------
func _build_stats() -> void:
    var root := VBoxContainer.new()
    root.position = Vector2(18, 16)
    root.custom_minimum_size = Vector2(320, 0)
    root.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(root)

    _level_lbl = _mk_label("Seviye 1")
    root.add_child(_level_lbl)
    _hp_bar = _mk_bar(Color(0.8, 0.1, 0.1))
    root.add_child(_hp_bar)
    _mp_bar = _mk_bar(Color(0.15, 0.35, 0.95))
    root.add_child(_mp_bar)
    _xp_bar = _mk_bar(Color(0.9, 0.7, 0.1))
    root.add_child(_xp_bar)
    _gold_lbl = _mk_label("Altın: 0")
    root.add_child(_gold_lbl)


func _mk_label(text: String) -> Label:
    var l := Label.new()
    l.text = text
    l.mouse_filter = Control.MOUSE_FILTER_IGNORE
    l.add_theme_font_size_override("font_size", 22)
    l.add_theme_color_override("font_color", Color(1, 1, 0.9))
    l.add_theme_color_override("font_outline_color", Color(0, 0, 0))
    l.add_theme_constant_override("outline_size", 4)
    return l


func _mk_bar(color: Color) -> ProgressBar:
    var b := ProgressBar.new()
    b.custom_minimum_size = Vector2(300, 22)
    b.max_value = 100
    b.value = 100
    b.show_percentage = false
    b.mouse_filter = Control.MOUSE_FILTER_IGNORE
    var fill := StyleBoxFlat.new()
    fill.bg_color = color
    fill.set_corner_radius_all(4)
    b.add_theme_stylebox_override("fill", fill)
    var bg := StyleBoxFlat.new()
    bg.bg_color = Color(0, 0, 0, 0.5)
    bg.set_corner_radius_all(4)
    b.add_theme_stylebox_override("background", bg)
    return b


# ---------- joystick + tuşlar ----------
func _build_controls() -> void:
    var joystick := Control.new()
    joystick.set_script(load("res://scripts/virtual_joystick.gd"))
    add_child(joystick)

    var atk := Button.new()
    atk.text = "SALDIR"
    _place_br(atk, -180, -180, -30, -30)
    _style_round_button(atk, Color(0.45, 0.08, 0.1), Color(0.72, 0.16, 0.16), 75)
    atk.button_down.connect(func(): GameState.touch_attack = true)
    atk.button_up.connect(func(): GameState.touch_attack = false)
    add_child(atk)

    var pot := Button.new()
    pot.text = "İKSİR"
    _place_br(pot, -170, -360, -40, -300)
    _style_round_button(pot, Color(0.12, 0.35, 0.16), Color(0.2, 0.55, 0.25), 18)
    pot.pressed.connect(_use_potion)
    add_child(pot)


func _place_br(c: Control, ol: float, ot: float, orr: float, ob: float) -> void:
    # sağ-alt köşeye göre offsetlerle yerleştir
    c.anchor_left = 1.0
    c.anchor_top = 1.0
    c.anchor_right = 1.0
    c.anchor_bottom = 1.0
    c.offset_left = ol
    c.offset_top = ot
    c.offset_right = orr
    c.offset_bottom = ob


func _style_round_button(b: Button, normal: Color, pressed: Color, radius: int) -> void:
    var sb := StyleBoxFlat.new()
    sb.bg_color = normal
    sb.set_corner_radius_all(radius)
    sb.set_border_width_all(4)
    sb.border_color = Color(0.85, 0.65, 0.35)
    var sbp := sb.duplicate()
    sbp.bg_color = pressed
    b.add_theme_stylebox_override("normal", sb)
    b.add_theme_stylebox_override("hover", sb)
    b.add_theme_stylebox_override("pressed", sbp)
    b.add_theme_stylebox_override("focus", sb)
    b.add_theme_font_size_override("font_size", 26)
    b.add_theme_color_override("font_color", Color(1, 0.92, 0.72))


func _use_potion() -> void:
    if GameState.use_item("İksir"):
        GameState.hp = min(GameState.max_hp, GameState.hp + 40.0)
        GameState.stats_changed.emit()


# ---------- çanta ----------
func _build_inventory() -> void:
    var btn := Button.new()
    btn.text = "Çanta"
    btn.anchor_left = 1.0
    btn.anchor_right = 1.0
    btn.offset_left = -150
    btn.offset_right = -20
    btn.offset_top = 20
    btn.offset_bottom = 66
    _style_round_button(btn, Color(0.2, 0.18, 0.22), Color(0.3, 0.28, 0.32), 10)
    btn.pressed.connect(_toggle_inv)
    add_child(btn)

    _inv_panel = Panel.new()
    _inv_panel.anchor_left = 1.0
    _inv_panel.anchor_right = 1.0
    _inv_panel.offset_left = -330
    _inv_panel.offset_right = -20
    _inv_panel.offset_top = 76
    _inv_panel.offset_bottom = 420
    _inv_panel.visible = false
    var ps := StyleBoxFlat.new()
    ps.bg_color = Color(0.08, 0.07, 0.09, 0.92)
    ps.set_corner_radius_all(8)
    ps.set_border_width_all(3)
    ps.border_color = Color(0.6, 0.45, 0.25)
    _inv_panel.add_theme_stylebox_override("panel", ps)
    add_child(_inv_panel)

    var vb := VBoxContainer.new()
    vb.anchor_right = 1.0
    vb.anchor_bottom = 1.0
    vb.offset_left = 14
    vb.offset_top = 12
    vb.offset_right = -14
    vb.offset_bottom = -12
    _inv_panel.add_child(vb)

    vb.add_child(_mk_label("Envanter"))
    _inv_list = VBoxContainer.new()
    vb.add_child(_inv_list)


func _toggle_inv() -> void:
    _inv_panel.visible = not _inv_panel.visible


# ---------- güncellemeler ----------
func _refresh() -> void:
    _level_lbl.text = "Seviye %d" % GameState.level
    _hp_bar.max_value = GameState.max_hp
    _hp_bar.value = GameState.hp
    _mp_bar.max_value = GameState.max_mp
    _mp_bar.value = GameState.mp
    _xp_bar.max_value = GameState.xp_to_next
    _xp_bar.value = GameState.xp
    _gold_lbl.text = "Altın: %d" % GameState.gold


func _refresh_inventory() -> void:
    if _inv_list == null:
        return
    for c in _inv_list.get_children():
        c.queue_free()
    if GameState.inventory.is_empty():
        _inv_list.add_child(_mk_label("(boş)"))
    else:
        for k in GameState.inventory:
            _inv_list.add_child(_mk_label("%s  x%d" % [k, GameState.inventory[k]]))


func _on_level_up(lv: int) -> void:
    var l := _mk_label("SEVİYE ATLADIN!   %d" % lv)
    l.add_theme_font_size_override("font_size", 46)
    l.add_theme_color_override("font_color", Color(1, 0.85, 0.3))
    l.anchor_left = 0.5
    l.anchor_right = 0.5
    l.anchor_top = 0.38
    l.anchor_bottom = 0.38
    l.offset_left = -280
    l.offset_right = 280
    l.offset_top = -40
    l.offset_bottom = 40
    l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    add_child(l)
    var t := l.create_tween()
    t.tween_interval(0.9)
    t.tween_property(l, "modulate:a", 0.0, 0.8)
    t.tween_callback(l.queue_free)
