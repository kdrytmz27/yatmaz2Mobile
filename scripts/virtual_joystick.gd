extends Control
# Sol alttaki sanal joystick. Dokunduğun yerde taban oluşur, parmağı sürükledikçe
# GameState.touch_move değerini doldurur (Player bunu okur).

var radius := 95.0
var _base_center := Vector2(150, 150)
var _knob := Vector2(150, 150)
var _active := false


func _ready() -> void:
    anchor_left = 0.0
    anchor_right = 0.0
    anchor_top = 1.0
    anchor_bottom = 1.0
    offset_left = 24.0
    offset_top = -324.0
    offset_right = 324.0
    offset_bottom = -24.0
    mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(event: InputEvent) -> void:
    if event is InputEventScreenTouch or event is InputEventMouseButton:
        if event.pressed:
            _active = true
            _base_center = event.position
            _knob = event.position
        else:
            _active = false
            GameState.touch_move = Vector2.ZERO
            _base_center = Vector2(150, 150)
            _knob = _base_center
        queue_redraw()
    elif (event is InputEventScreenDrag or event is InputEventMouseMotion) and _active:
        var off: Vector2 = event.position - _base_center
        if off.length() > radius:
            off = off.normalized() * radius
        _knob = _base_center + off
        GameState.touch_move = off / radius
        queue_redraw()


func _draw() -> void:
    draw_circle(_base_center, radius, Color(0, 0, 0, 0.3))
    draw_arc(_base_center, radius, 0, TAU, 48, Color(0.8, 0.6, 0.3, 0.6), 3.0, true)
    draw_circle(_knob, 38, Color(0.7, 0.5, 0.25, 0.75))
    draw_arc(_knob, 38, 0, TAU, 32, Color(0.95, 0.8, 0.4, 0.9), 2.0, true)
