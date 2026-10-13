class_name FloatingText
extends RefCounted
# Hasar / toplama gibi olaylarda havada yükselip kaybolan 3B yazı.

static func spawn(parent: Node, pos: Vector3, text: String, color: Color) -> void:
    if parent == null or not is_instance_valid(parent):
        return
    var lbl := Label3D.new()
    lbl.text = text
    lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    lbl.no_depth_test = true
    lbl.modulate = color
    lbl.outline_modulate = Color(0, 0, 0, 1)
    lbl.outline_size = 8
    lbl.font_size = 44
    lbl.pixel_size = 0.012
    parent.add_child(lbl)
    lbl.global_position = pos
    var t := lbl.create_tween()
    t.set_parallel(true)
    t.tween_property(lbl, "global_position", pos + Vector3(0, 1.6, 0), 0.7)
    t.tween_property(lbl, "modulate:a", 0.0, 0.7)
    t.set_parallel(false)
    t.tween_callback(lbl.queue_free)
