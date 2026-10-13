extends CharacterBody3D
# Oyuncu karakteri: kameraya göre hareket, yüzünü dönme, yakın dövüş saldırısı.

const SPEED := 6.0
const GRAVITY := 20.0
const ATTACK_RANGE := 2.8
const ATTACK_DAMAGE := 18.0
const ATTACK_COOLDOWN := 0.45

var _attack_timer := 0.0
var _mesh_root: Node3D


func _ready() -> void:
    add_to_group("player")
    _build_body()


func _build_body() -> void:
    var col := CollisionShape3D.new()
    var cap := CapsuleShape3D.new()
    cap.radius = 0.4
    cap.height = 1.8
    col.shape = cap
    col.position = Vector3(0, 0.9, 0)
    add_child(col)

    _mesh_root = Node3D.new()
    add_child(_mesh_root)

    var body := MeshInstance3D.new()
    var cm := CapsuleMesh.new()
    cm.radius = 0.4
    cm.height = 1.8
    body.mesh = cm
    body.position = Vector3(0, 0.9, 0)
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.9, 0.78, 0.35)
    body.material_override = mat
    _mesh_root.add_child(body)

    # Yüz yönünü gösteren "burun" (ileri = +Z)
    var nose := MeshInstance3D.new()
    var nm := BoxMesh.new()
    nm.size = Vector3(0.22, 0.22, 0.55)
    nose.mesh = nm
    nose.position = Vector3(0, 1.0, 0.45)
    var nmat := StandardMaterial3D.new()
    nmat.albedo_color = Color(0.85, 0.25, 0.2)
    nose.material_override = nmat
    _mesh_root.add_child(nose)


func _physics_process(delta: float) -> void:
    _attack_timer = max(0.0, _attack_timer - delta)

    var input := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    input += GameState.touch_move
    input = input.limit_length(1.0)

    var dir := Vector3.ZERO
    if input.length() > 0.08:
        var cam := get_viewport().get_camera_3d()
        if cam:
            var b := cam.global_transform.basis
            var forward := -b.z
            forward.y = 0.0
            forward = forward.normalized()
            var right := b.x
            right.y = 0.0
            right = right.normalized()
            dir = right * input.x - forward * input.y
        else:
            dir = Vector3(input.x, 0, input.y)
        dir.y = 0.0
        if dir.length() > 0.0:
            dir = dir.normalized()

    var vel := velocity
    vel.x = dir.x * SPEED
    vel.z = dir.z * SPEED
    if is_on_floor():
        vel.y = 0.0
    else:
        vel.y -= GRAVITY * delta
    velocity = vel
    move_and_slide()

    if dir.length() > 0.08:
        var target_yaw := atan2(dir.x, dir.z)
        _mesh_root.rotation.y = lerp_angle(_mesh_root.rotation.y, target_yaw, 14.0 * delta)

    if (Input.is_action_pressed("attack") or GameState.touch_attack) and _attack_timer <= 0.0:
        _do_attack()


func _do_attack() -> void:
    _attack_timer = ATTACK_COOLDOWN
    _play_attack_anim()

    var origin := global_position
    var facing := _mesh_root.global_transform.basis.z
    facing.y = 0.0
    facing = facing.normalized()

    for e in get_tree().get_nodes_in_group("enemy"):
        if not is_instance_valid(e):
            continue
        var to: Vector3 = e.global_position - origin
        var dist := to.length()
        if dist > ATTACK_RANGE:
            continue
        var flat := Vector3(to.x, 0, to.z)
        if flat.length() < 0.01 or facing.dot(flat.normalized()) > 0.05:
            if e.has_method("take_damage"):
                e.take_damage(ATTACK_DAMAGE, self)


func _play_attack_anim() -> void:
    var t := create_tween()
    t.tween_property(_mesh_root, "scale", Vector3(1.15, 0.9, 1.15), 0.08)
    t.tween_property(_mesh_root, "scale", Vector3.ONE, 0.14)
