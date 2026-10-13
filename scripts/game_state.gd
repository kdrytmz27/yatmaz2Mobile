extends Node
# Oyunun kalıcı durumu: can/mana, seviye/XP, altın, envanter.
# Autoload (singleton) olarak yüklenir -> her yerden GameState.xxx ile erişilir.

signal stats_changed
signal inventory_changed
signal leveled_up(new_level)
signal player_respawned

var max_hp := 100.0
var hp := 100.0
var max_mp := 50.0
var mp := 50.0

var level := 1
var xp := 0
var xp_to_next := 20
var gold := 0

var inventory := {}  # "item adı" -> adet

# Mobil dokunmatik giriş: HUD doldurur, Player okur.
var touch_move := Vector2.ZERO
var touch_attack := false


func _ready() -> void:
    _setup_input()


func _setup_input() -> void:
    # Klavye kısayollarını kodda tanımlıyoruz (masaüstünde test için).
    _add_action("move_up", [KEY_W, KEY_UP])
    _add_action("move_down", [KEY_S, KEY_DOWN])
    _add_action("move_left", [KEY_A, KEY_LEFT])
    _add_action("move_right", [KEY_D, KEY_RIGHT])
    _add_action("attack", [KEY_SPACE, KEY_J])


func _add_action(action_name: String, keys: Array) -> void:
    if not InputMap.has_action(action_name):
        InputMap.add_action(action_name)
    for k in keys:
        var ev := InputEventKey.new()
        ev.physical_keycode = k
        InputMap.action_add_event(action_name, ev)


func add_xp(amount: int) -> void:
    xp += amount
    while xp >= xp_to_next:
        xp -= xp_to_next
        level += 1
        xp_to_next = int(xp_to_next * 1.35) + 10
        max_hp += 20.0
        max_mp += 8.0
        hp = max_hp
        mp = max_mp
        leveled_up.emit(level)
    stats_changed.emit()


func take_damage(amount: float) -> void:
    hp = max(0.0, hp - amount)
    stats_changed.emit()
    if hp <= 0.0:
        respawn()


func respawn() -> void:
    hp = max_hp
    mp = max_mp
    stats_changed.emit()
    player_respawned.emit()


func add_item(item_name: String, count := 1) -> void:
    inventory[item_name] = inventory.get(item_name, 0) + count
    inventory_changed.emit()


func use_item(item_name: String) -> bool:
    if inventory.get(item_name, 0) <= 0:
        return false
    inventory[item_name] -= 1
    if inventory[item_name] <= 0:
        inventory.erase(item_name)
    inventory_changed.emit()
    return true


func add_gold(amount: int) -> void:
    gold += amount
    stats_changed.emit()
