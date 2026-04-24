# Phase 3 — Functional Settings Screen
## Development Guidelines

---

## Purpose of This Phase

The settings screen currently exists as a stub — a menu state that shows placeholder text and has no interactive controls. Phase 3 transforms it into a real, functional panel where players can adjust audio volumes, toggle fullscreen mode, and switch the interface language. All preferences must persist across game restarts, meaning they are saved to disk and reloaded at startup.

This phase also introduces the game's first persistent data — information that survives beyond a single session. Building this correctly requires thinking carefully about where data lives, how it is stored, and what happens when the stored data is malformed or missing.

---

## Core Technology: Python's json Module and File I/O

Preferences are stored as a JSON file in the `assets/save/` directory. JSON (JavaScript Object Notation) is the right choice for this use case for several reasons:

**Human readability.** A player who is curious about where the game saves settings can open the file in any text editor and see their preferences in plain English. They can also manually edit the file if they want to reset a specific setting. This transparency builds trust and makes support easier.

**Native Python support.** The `json` module is part of Python's standard library — no additional installation is required. It reads and writes Python dicts, lists, strings, numbers, and booleans directly, which maps naturally onto the shapes of game settings.

**Safe and explicit.** Unlike `pickle`, JSON can only represent its supported primitive types. A malformed or malicious settings file cannot execute arbitrary code when loaded.

The alternative approaches — SQLite for a full database, TOML for a more readable format, `configparser` for an INI-style file — are all valid but add complexity without meaningfully improving outcomes for a settings file with fewer than ten fields.

### File Path Strategy

The settings file belongs in `assets/save/settings.json`. This keeps all game data within the project's `assets/` directory, which is clean and self-contained. The `save/` directory must be created automatically by the save logic if it does not exist — never assume the directory is present, because the game might be running for the first time on a machine where the directory was never created.

Add `assets/save/` to the project's `.gitignore` file. Personal settings should not be committed to version control. Each developer (and each player) should have their own settings state that is never overwritten by repository updates.

---

## The SettingsStore: Design Philosophy

### Separation of Concerns

The settings store has exactly one job: reading and writing the settings file and providing typed access to setting values. It should not know about `AudioManager`, `MainMenu`, `GameManager`, or any other class. When a setting changes, the store updates its internal state and writes to disk. The caller is responsible for applying that change to whatever system needs it.

This separation means the settings store can be developed and tested completely independently. It also means the store can be used from any context without creating circular dependencies — the store does not depend on anything except the file system and the constants module.

### Defaults and Forward Compatibility

The settings file might be missing (first run), might contain an older version with fewer fields (player updated the game), or might contain corrupted data (file system error). The store must handle all three cases gracefully.

The correct approach is to define a complete set of defaults in code, then overlay the file's contents on top. Any key present in the file overwrites the default; any key absent from the file retains the default. This strategy means:
- First run: all defaults apply without error
- Older save without a new setting: new setting uses its default, old settings are preserved
- Corrupted file: on JSON parse failure, fall through to all defaults

Never crash on a bad settings file. Never require the settings file to be present. The game must always be able to start.

### Typed Property Access

Settings should be exposed through typed properties rather than raw dict access. Accessing a volume as `store.sfx_volume` (a float) is cleaner and more readable than accessing it as `store.data["sfx_volume"]` (untyped). It also makes IDE autocompletion work correctly and allows adding validation logic (for example, clamping a volume to 0.0–1.0 if a manually-edited file contains an out-of-range value) in a single place.

Setters for each property should immediately clamp or validate the value. If a player somehow saves a volume of 2.5 or -0.3, the setter should correct it to the nearest valid value rather than storing the invalid value and letting it cause problems downstream.

---

## UI Controls: What to Build and Why Each One Works

### Sliders for Volume

Volume is a continuous value between 0 and 100 percent. The appropriate control for a continuous value is a **slider** — a horizontal track with a draggable handle. Percentage text (like "80%") displays next to the slider to give an exact readout for players who want precision.

The slider interaction model is straightforward: when the player clicks anywhere on the track, the handle jumps to that position and the volume is updated immediately. As the player then drags, the volume continues to update in real time. This immediate feedback is important — the player should hear the volume change while dragging, not after releasing.

Avoid using plus/minus buttons for volume. Buttons require many clicks to traverse the full range and provide no sense of position relative to the maximum. They are appropriate for integer values that change in discrete steps, not for continuous percentages.

### Toggle for Fullscreen

Fullscreen is a binary state: on or off. The appropriate control is a **toggle switch** — a pill-shaped control where clicking it flips between two states, with the handle position indicating the current state. Toggles are visually clearer than checkboxes for binary settings because the state is immediately obvious from the handle position without needing to understand the checkbox metaphor.

The fullscreen toggle must take effect immediately when clicked, not after pressing "Save." Requiring the player to save before seeing the fullscreen change creates a confusing intermediate state where they cannot tell if the toggle worked. Apply the `pygame.display.toggle_fullscreen()` call the moment the toggle is clicked.

### Language Selector

Language selection should be presented as two mutually exclusive pill buttons — one for Vietnamese (VI) and one for English (EN). The currently active language has a highlighted appearance (brighter border, filled background). Clicking the inactive language immediately switches all interface text.

This approach works better than a dropdown for exactly two options. Dropdowns are appropriate when there are many choices; for a binary selection between two equally prominent options, side-by-side buttons communicate the choice more clearly.

### The "Save & Close" Button

Volume and language changes can take effect immediately, but having an explicit "Save & Close" button gives the player a clear action to confirm their changes and return to the main menu. This button should write the current state to disk and transition the menu state back to "home."

Without this button, players might not know their settings have been saved — the file is written on every change, but players expect an explicit save confirmation. The button also provides a clean exit from the settings screen.

---

## Applying Settings at Startup

The correct workflow at game startup is:

1. Initialize pygame and all subsystems (display, mixer)
2. Create the `SettingsStore` and call its `load()` method
3. Immediately apply the loaded settings to all relevant systems: set mixer volumes via `AudioManager`, apply fullscreen mode via the display module, set the active language in the string table

This sequence must happen before the first frame is rendered. A player who set the game to fullscreen last session and sees a brief windowed frame on startup before fullscreen is applied will find that jarring. Apply display settings before the window becomes visible.

The fullscreen setting in particular requires care because the pygame display is created before settings are loaded in the current `main.py` flow. The display initialization will need to be restructured so the display mode (windowed or fullscreen) is set only after the settings file has been read.

---

## Language System Architecture

### String Table Approach

Every piece of text the player sees (button labels, menu titles, HUD annotations, instructions) should be stored in a string table rather than hardcoded as string literals in the code. The string table is a nested dictionary: the outer key is the language code (`"vi"` or `"en"`), the inner key is a string identifier, and the value is the localized text.

A global helper function — traditionally named `t()` — looks up a key in the string table using the currently active language and returns the localized string. Any call site that currently reads `"Bat dau"` should instead read `t("menu_start")`, which returns `"Bat dau"` when Vietnamese is active and `"Start"` when English is active.

### Why This Matters Beyond Just English/Vietnamese

Building the string table now is an investment in maintainability. Even if English is never actually enabled in the shipped game, the discipline of routing all text through `t()` prevents the common problem of text being half in one language and half in another because a developer added a new label in a hurry. It also makes spelling corrections and rewording easy — you change one place in the string table rather than hunting through source files.

### What Not to Translate

Not everything needs translation. Numbers, mathematical symbols, unit abbreviations ("%", "km/h"), and brand names (the game title) do not go through the string table. Game mechanics values that are displayed to the player (HP, fuel, wind speed) should be formatted in code and never hardcoded as strings.

---

## Interaction Design Principles

### Immediate Feedback

Every interaction in the settings screen should produce immediate, visible feedback:
- Moving the volume slider changes the displayed percentage instantly
- Clicking the fullscreen toggle switches the display mode instantly
- Clicking the language toggle changes the button labels instantly

Requiring a separate "Apply" step creates a frustrating delay between action and confirmation. The only thing that requires an explicit action is writing to disk, which is covered by "Save & Close."

### Visual State Communication

The settings panel must visually communicate the current state of every control at a glance:
- The slider handle position and fill level show the current volume
- The toggle handle position shows whether fullscreen is on or off
- The highlighted language button shows which language is active

A player should be able to open the settings screen, read the current state of all settings, and close it without touching anything — the controls are informational as well as interactive.

### Mouse Interaction Model

For the slider, track the mouse's pressed state across frames. When the player presses down on the slider track, begin tracking slider drag mode. While the mouse button is held, update the slider value based on the mouse's horizontal position relative to the track, clamped to the track's boundaries. When the mouse button is released, exit drag mode. This is more robust than checking for individual click events, which can miss drags that start outside the slider area.

---

## Programming Approach for This Phase

### Build the SettingsStore Completely First

Write and test the `SettingsStore` class before touching any UI code. Specifically:
- Verify that the file is created on first save
- Verify that the file is read correctly on subsequent loads
- Verify that a missing file produces defaults, not an error
- Verify that a file with one extra unknown key does not crash
- Verify that a file with one missing key fills in the default for that key
- Verify that a corrupted JSON file produces defaults, not an error

These edge cases are easy to test with a simple test script that creates a store, writes a file, deletes the file, corrupts the file, etc. Testing them now prevents difficult-to-reproduce bugs in production.

### Integrate Settings Into GameManager Before Building UI

Once `SettingsStore` works correctly, integrate it into `GameManager` at startup — load settings and apply volumes to `AudioManager`. Verify this works before building the settings UI. The UI is only a way to change the values; the underlying plumbing must work first.

### Slider Implementation Strategy

Implement the slider state machine carefully. The most common bug in custom sliders is handling the edge case where the mouse button is pressed down on the slider, dragged off the slider area, and then released off the slider area. Without proper state tracking, the slider remains in "being dragged" mode indefinitely. The fix: when the mouse button is released anywhere on the screen (not just over the slider), exit drag mode for all sliders. Track drag state per interaction, not per position.
