extends StaticBody3D
# Kırılabilir "Metin Taşı": vurdukça canı azalır, kırılınca XP + altın + eşya düşürür,
# bir süre sonra yeniden doğar.

var max_hp := 120.0
var hp := 120.0
var xp_reward := 15
var _mesh: MeshInstance3D
var _col: CollisionShape3D


func _ready() -> void:
    add_to_group("enemy")
    _build()


func _build() -> void:
    _col = CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(1.4, 2.0, 1.4)
    _col.shape = shape
    _col.position = Vector3(0, 1.0, 0)
    add_child(_col)

    _mesh = MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = Vector3(1.4, 2.0, 1.4)
    _mesh.mesh = bm
    _mesh.position = Vector3(0, 1.0, 0)
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.28, 0.18, 0.34)
    mat.emission_enabled = true
    mat.emission = Color(0.55, 0.12, 0.65)
    mat.emission_energy_multiplier = 0.5
    _mesh.material_override = mat
    add_child(_mesh)

    var lbl := Label3D.new()
    lbl.text = "Metin Taşı"
    lbl.position = Vector3(0, 2.7, 0)
    lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    lbl.modulate = Color(0.95, 0.55, 1.0)
    lbl.outline_modulate = Color(0, 0, 0, 1)
    lbl.outline_size = 8
    lbl.font_size = 42
    lbl.pixel_size = 0.01
    add_child(lbl)


func take_damage(amount: float, _from) -> void:
    hp -= amount
    FloatingText.spawn(get_tree().current_scene, global_position + Vector3(0, 2.2, 0), str(int(amount)), Color(1, 0.9, 0.3))
    var t := create_tween()
    t.tween_property(_mesh, "position", Vector3(0.12, 1.0, 0), 0.03)
    t.tween_property(_mesh, "position", Vector3(0, 1.0, 0), 0.06)
    if hp <= 0.0:
        _destroy()


func _destroy() -> void:
    GameState.add_xp(xp_reward)
    GameState.add_gold(randi_range(3, 12))
    _spawn_drops()
    _set_active(false)
    get_tree().create_timer(12.0).timeout.connect(_respawn)


func _respawn() -> void:
    hp = max_hp
    _set_active(true)


func _set_active(active: bool) -> void:
    visible = active
    _col.disabled = not active
    if active:
        add_to_group("enemy")
    else:
        remove_from_group("enemy")


func _spawn_drops() -> void:
    var pool := ["İksir", "Altın Kese", "Yün", "Kılıç Parçası"]
    var n := randi_range(1, 3)
    for i in n:
        var d := DropItem.create(pool.pick_random())
        get_tree().current_scene.add_child(d)
        d.global_position = global_position + Vector3(randf_range(-1.5, 1.5), 0.3, randf_range(-1.5, 1.5))
