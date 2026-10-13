# UI repair — build 4

This is a functional repair of the rejected v2, not a completed Romia2/Royale2-inspired redesign.

- Moved status and other game action buttons out of the Android joystick view's touch rectangle; kept original callbacks.
- Removed the orphaned desktop energy panel in mobile mode. Energy value remains in the player card.
- Quest notification glyph now uses explicit notification identity instead of inferring close buttons from texture filenames.
- Shifted HP/MP/ATK/DEF captions clear of stat plus buttons.

MuMu interaction evidence: tapping Raise State opened Character. Tapping VIT plus changed VIT 4 -> 5, remaining points 267 -> 266, HP 5117 -> 5157. This consumed one point on the local Test character.

Screenshots: ui-repair-stat-test.png and ui-repair-hud.png. HUD screenshot precedes the final quest-glyph correction. Broad visual redesign is still outstanding.
