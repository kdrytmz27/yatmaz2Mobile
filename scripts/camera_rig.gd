extends Node3D
# Metin2 tarzı tepeden-açılı takip kamerası.
# Hedefi (oyuncu) yumuşakça izler. Masaüstünde sağ tık sürükle ile döner,
# tekerlek ile yakınlaşır/uzaklaşır.

var target: Node3D
var yaw := 45.0
var pitch := 42.0
var distance := 9.0
var height := 1.4
var _cam: Camera3D


func _ready() -> void:
    _cam = Camera3D.new()
    _cam.current = true
    _cam.fov = 60.0
    add_child(_cam)
    if target:
        global_position = target.global_position
    _update_camera()


func _process(delta: float) -> void:
    if target and is_instance_valid(target):
        var w := 1.0 - pow(0.001, delta)
        global_position = global_position.lerp(target.global_position, w)
    _update_camera()


func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
        yaw -= event.relative.x * 0.3
    elif event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP:
            distance = max(5.0, distance - 0.6)
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
            distance = min(16.0, distance + 0.6)


func _update_camera() -> void:
    if _cam == null:
        return
    var yr := deg_to_rad(yaw)
    var pr := deg_to_rad(pitch)
    var offset := Vector3(
        sin(yr) * cos(pr),
        sin(pr),
        cos(yr) * cos(pr)
    ) * distance
    var look := global_position + Vector3(0, height, 0)
    _cam.global_position = look + offset
    _cam.look_at(look, Vector3.UP)
