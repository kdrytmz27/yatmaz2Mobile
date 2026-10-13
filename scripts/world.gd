extends Node3D
# Dünyayı kurar: zemin, ışık, oyuncu, kamera, metin taşları, canavarlar, HUD.
# Canavar popülasyonunu belirli bir üst sınırda tutar.

var player: CharacterBody3D
var _spawn_accum := 0.0
var _monster_cap := 10


func _ready() -> void:
    randomize()
    _build_environment()
    _spawn_player()
    _spawn_camera()
    _spawn_hud()
    _spawn_content()
    GameState.player_respawned.connect(_on_player_respawned)


func _process(delta: float) -> void:
    _spawn_accum += delta
    if _spawn_accum >= 3.0:
        _spawn_accum = 0.0
        if get_tree().get_nodes_in_group("monster").size() < _monster_cap:
            _spawn_monster()


func _build_environment() -> void:
    # Zemin
    var ground := StaticBody3D.new()
    var mesh := MeshInstance3D.new()
    var plane := PlaneMesh.new()
    plane.size = Vector2(90, 90)
    mesh.mesh = plane
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.22, 0.28, 0.16)
    mesh.material_override = mat
    ground.add_child(mesh)
    var col := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(90, 0.2, 90)
    col.shape = shape
    col.position = Vector3(0, -0.1, 0)
    ground.add_child(col)
    add_child(ground)

    # Birkaç dekor ağaç/kaya
    for i in 24:
        _add_decor()

    # Güneş
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-55, -45, 0)
    sun.light_energy = 1.1
    sun.shadow_enabled = true
    add_child(sun)

    # Ortam / gökyüzü rengi + sis
    var env := WorldEnvironment.new()
    var e := Environment.new()
    e.background_mode = Environment.BG_COLOR
    e.background_color = Color(0.46, 0.56, 0.72)
    e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    e.ambient_light_color = Color(0.5, 0.5, 0.55)
    e.ambient_light_energy = 0.7
    e.fog_enabled = true
    e.fog_light_color = Color(0.46, 0.56, 0.72)
    e.fog_density = 0.004
    env.environment = e
    add_child(env)


func _add_decor() -> void:
    var p := _random_ground(6, 42)
    p.y = 0.0
    var trunk := MeshInstance3D.new()
    var cyl := CylinderMesh.new()
    cyl.top_radius = 0.25
    cyl.bottom_radius = 0.35
    cyl.height = 2.4
    trunk.mesh = cyl
    trunk.position = p + Vector3(0, 1.2, 0)
    var tm := StandardMaterial3D.new()
    tm.albedo_color = Color(0.3, 0.2, 0.12)
    trunk.material_override = tm
    add_child(trunk)

    var leaves := MeshInstance3D.new()
    var sph := SphereMesh.new()
    sph.radius = 1.3
    sph.height = 2.6
    leaves.mesh = sph
    leaves.position = p + Vector3(0, 3.0, 0)
    var lm := StandardMaterial3D.new()
    lm.albedo_color = Color(0.16, 0.4, 0.18)
    leaves.material_override = lm
    add_child(leaves)


func _spawn_player() -> void:
    player = CharacterBody3D.new()
    player.name = "Player"
    player.set_script(load("res://scripts/player.gd"))
    add_child(player)
    player.position = Vector3(0, 1, 0)


func _spawn_camera() -> void:
    var rig := Node3D.new()
    rig.set_script(load("res://scripts/camera_rig.gd"))
    rig.target = player
    add_child(rig)


func _spawn_hud() -> void:
    var hud := CanvasLayer.new()
    hud.set_script(load("res://scripts/hud.gd"))
    add_child(hud)


func _spawn_content() -> void:
    for i in 6:
        var s := StaticBody3D.new()
        s.set_script(load("res://scripts/metin_stone.gd"))
        add_child(s)
        var p := _random_ground(8, 34)
        p.y = 0.0
        s.position = p
    for i in 8:
        _spawn_monster()


func _spawn_monster() -> void:
    var m := CharacterBody3D.new()
    m.set_script(load("res://scripts/monster.gd"))
    add_child(m)
    m.position = _random_ground(12, 38)


func _random_ground(min_r: float, max_r: float) -> Vector3:
    var ang := randf() * TAU
    var r := randf_range(min_r, max_r)
    return Vector3(cos(ang) * r, 1.0, sin(ang) * r)


func _on_player_respawned() -> void:
    if player and is_instance_valid(player):
        player.global_position = Vector3(0, 1, 0)
