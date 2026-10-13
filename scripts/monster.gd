extends CharacterBody3D
# Basit canavar: oyuncuyu görünce kovalar, yakınında vurur.
# Canı biter -> XP + altın + (şans ile) eşya düşürür ve yok olur.
# Dünya (world.gd) popülasyonu belirli sayıda tutar.

var max_hp := 60.0
var hp := 60.0
var speed := 3.2
var damage := 8.0
var xp_reward := 10
var aggro_range := 14.0
var attack_range := 1.9
var _atk_cd := 0.0
var _mesh_root: Node3D


func _ready() -> void:
    add_to_group("enemy")
    add_to_group("monster")
    _build()


func _build() -> void:
    var col := CollisionShape3D.new()
    var cap := CapsuleShape3D.new()
    cap.radius = 0.45
    cap.height = 1.4
    col.shape = cap
    col.position = Vector3(0, 0.7, 0)
    add_child(col)

    _mesh_root = Node3D.new()
    add_child(_mesh_root)

    var body := MeshInstance3D.new()
    var cm := CapsuleMesh.new()
    cm.radius = 0.45
    cm.height = 1.4
    body.mesh = cm
    body.position = Vector3(0, 0.7, 0)
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.72, 0.2, 0.2)
    body.material_override = mat
    _mesh_root.add_child(body)

    var lbl := Label3D.new()
    lbl.text = "Canavar"
    lbl.position = Vector3(0, 1.8, 0)
    lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    lbl.modulate = Color(1, 0.6, 0.6)
    lbl.outline_modulate = Color(0, 0, 0, 1)
    lbl.outline_size = 6
    lbl.font_size = 34
    lbl.pixel_size = 0.01
    add_child(lbl)


func _physics_process(delta: float) -> void:
    _atk_cd = max(0.0, _atk_cd - delta)
    var vel := velocity
    if is_on_floor():
        vel.y = 0.0
    else:
        vel.y -= 20.0 * delta

    var player := get_tree().get_first_node_in_group("player") as Node3D
    if player and is_instance_valid(player):
        var to: Vector3 = player.global_position - global_position
        var dist := Vector2(to.x, to.z).length()
        if dist < aggro_range and dist > attack_range:
            var d := Vector3(to.x, 0, to.z).normalized()
            vel.x = d.x * speed
            vel.z = d.z * speed
            _mesh_root.rotation.y = atan2(d.x, d.z)
        else:
            vel.x = move_toward(vel.x, 0.0, speed)
            vel.z = move_toward(vel.z, 0.0, speed)
            if dist <= attack_range and _atk_cd <= 0.0:
                _atk_cd = 1.0
                GameState.take_damage(damage)
                FloatingText.spawn(get_tree().current_scene, player.global_position + Vector3(0, 2.2, 0), str(int(damage)), Color(1, 0.3, 0.3))
    else:
        vel.x = move_toward(vel.x, 0.0, speed)
        vel.z = move_toward(vel.z, 0.0, speed)

    velocity = vel
    move_and_slide()


func take_damage(amount: float, _from) -> void:
    hp -= amount
    FloatingText.spawn(get_tree().current_scene, global_position + Vector3(0, 1.8, 0), str(int(amount)), Color(1, 0.9, 0.3))
    var t := create_tween()
    t.tween_property(_mesh_root, "scale", Vector3(1.2, 0.8, 1.2), 0.05)
    t.tween_property(_mesh_root, "scale", Vector3.ONE, 0.1)
    if hp <= 0.0:
        _die()


func _die() -> void:
    GameState.add_xp(xp_reward)
    GameState.add_gold(randi_range(1, 6))
    if randf() < 0.5:
        var d := DropItem.create(["İksir", "Altın Kese", "Yün", "Kılıç Parçası"].pick_random())
        get_tree().current_scene.add_child(d)
        d.global_position = global_position + Vector3(0, 0.3, 0)
    queue_free()
