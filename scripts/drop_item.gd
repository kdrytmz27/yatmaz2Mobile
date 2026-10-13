class_name DropItem
extends Area3D
# Yerde duran, oyuncu üstüne gelince envantere eklenen eşya.

var item_name := "İksir"


static func create(name: String) -> DropItem:
    var d := DropItem.new()
    d.item_name = name
    return d


func _ready() -> void:
    monitoring = true
    var col := CollisionShape3D.new()
    var shape := SphereShape3D.new()
    shape.radius = 1.0
    col.shape = shape
    add_child(col)

    var mesh := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = Vector3(0.4, 0.4, 0.4)
    mesh.mesh = bm
    mesh.position = Vector3(0, 0.3, 0)
    var mat := StandardMaterial3D.new()
    mat.albedo_color = _color_for(item_name)
    mat.emission_enabled = true
    mat.emission = mat.albedo_color
    mat.emission_energy_multiplier = 0.7
    mesh.material_override = mat
    add_child(mesh)

    var t := mesh.create_tween().set_loops()
    t.tween_property(mesh, "rotation:y", TAU, 1.6).from(0.0)

    body_entered.connect(_on_body_entered)


func _color_for(n: String) -> Color:
    match n:
        "İksir":
            return Color(0.3, 0.9, 0.4)
        "Altın Kese":
            return Color(0.95, 0.8, 0.2)
        "Kılıç Parçası":
            return Color(0.7, 0.75, 0.85)
        "Yün":
            return Color(0.85, 0.85, 0.75)
        _:
            return Color(0.8, 0.5, 1.0)


func _on_body_entered(body: Node) -> void:
    if body.is_in_group("player"):
        GameState.add_item(item_name, 1)
        FloatingText.spawn(get_tree().current_scene, global_position + Vector3(0, 1, 0), "+" + item_name, Color(0.6, 1, 0.6))
        queue_free()
