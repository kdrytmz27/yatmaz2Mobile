# Mobile UI design — build 5

Implemented in the game client, using existing character/item art and native rendered UI:
- Circular attack/quick-slot controls, with four slots arranged around the attack button and four utility slots beside them.
- Removed desktop F-key captions from touch controls.
- Compact portrait, level, HP/MP and energy card.
- Dark metal panel palette, burgundy title bars, inset equipment/backpack sections and restrained corner ornament.
- Raise State remains bottom-left beside the joystick.

Known scope: login, kingdom/character selection layouts and detailed icon art have not been redesigned. Existing global theme also affects their panels. Physical-device/performance testing remains outstanding.

Source of truth: work/m2stage and tools/data-overlay/modern-ui. Older modernize_ui.py/design_ui.py scripts are historical transformations; rerunning them can overwrite later fixes.

Validation: Gradle build passed; installed build 5 on MuMu. Correct shaman portrait verified. Opened menu by touch, opened Bag, switched to inventory page II and back to I. No syserr entries during checks.
