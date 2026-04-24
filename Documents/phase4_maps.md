# Phase 4 — Multi-Map Support
## Development Guidelines

---

## Purpose of This Phase

The Level Select screen already exists in the main menu and displays six cards. Currently, clicking any of them starts the same game: same flat terrain, same sky background, same default physics. Phase 4 makes the level select genuinely functional — each of the six levels loads a distinct environment with a unique terrain shape, sky background, and modified physics constants (wind strength, gravity, fuel cost).

This phase is also about making the codebase more **data-driven**. Instead of hardcoding map properties in game logic, each map is described by a configuration object. The game reads those properties and applies them. Adding a seventh map in the future should require no code changes — only a new data entry and the corresponding asset files.

---

## The Data-Driven Mindset

### What "Data-Driven" Means

A data-driven design separates **what** exists from **how it works**. In a code-driven design, you might write a special case in `GameManager` for each map: "if level is 5, reduce gravity by 30%." In a data-driven design, every map has a gravity field, and `GameManager` simply reads whatever value is stored there.

Data-driven code has several advantages:

- **Adding content does not require touching logic code.** New maps can be added by filling out a data structure and providing asset files.
- **Balancing is easier.** Tweaking wind strength for the desert level means changing a number in the map definition, not finding and editing a conditional branch in game logic.
- **The code becomes more general.** Logic that reads from data is cleaner than logic full of special cases.

### The Config Object Pattern

A map configuration object is an **immutable data container** that describes everything the game needs to know about a map at startup. It has no methods, no dependencies, no side effects — it is just structured data.

Using Python's `dataclass` with `frozen=True` is ideal for this. Frozen dataclasses cannot be modified after creation, which enforces the immutability contract. A map's configuration should never change at runtime. Keep configuration objects flat and simple — every field should be a primitive type (string, float, bool, int) or `None`. Avoid nesting configuration objects inside other configuration objects.

---

## Core Technology: How pygame Handles Multiple Surfaces

Each map has two large image components: a background (the sky, landscape backdrop) and a terrain mask (the destructible ground). Understanding how pygame manages these surfaces influences the implementation.

### Surfaces Are Memory

A `pygame.Surface` is a 2D array of pixels in memory. Loading a 1280×720 RGBA image consumes about 3.7 MB of RAM. For six maps, loading all terrain images simultaneously would consume significant memory. The better approach is to **load only the active map's assets** when a level is selected, and discard the previous level's surfaces when the game resets. Pygame does not have automatic garbage collection for surfaces — stop referencing a surface and Python's garbage collector reclaims the memory.

### Terrain Surface Requirements

The terrain image serves two functions simultaneously: it is what players see and it is the physics mask. Both are encoded in the same RGBA PNG file.

The **alpha channel** is the physics mask. A fully transparent pixel (alpha = 0) is air — bullets pass through it, tanks fall through it. Any pixel with non-zero alpha is solid ground. The RGB channels determine the color the player sees. Artists must treat the alpha channel as a hard binary mask with no anti-aliasing. Any partial transparency creates ambiguously solid pixels that cause inconsistent collision behavior.

---

## Designing the Six Maps

### Progression Philosophy

The six levels should form a progression curve: Level 1 is the most straightforward; Level 6 is the most chaotic. Physics modifiers should be introduced one at a time so players can understand each change individually before facing multiple simultaneous modifications. A sensible order:

- **Levels 1–2:** Only wind strength changes. Players learn that wind affects trajectory before anything else shifts.
- **Level 3:** Visual change only (night theme). No physics change, but reduced visibility changes battlefield reading.
- **Level 4:** Fuel cost changes (snow — slippery, less fuel burned per distance). Positioning strategy shifts.
- **Level 5:** Gravity changes. Shot arcs feel completely different; recalibration required.
- **Level 6:** Wind and gravity both extreme simultaneously. Everything feels chaotic.

### What the Physics Numbers Mean

`WIND_MIN` and `WIND_MAX` define the range of wind acceleration (in pixels per second squared) chosen randomly each turn. A `wind_multiplier` of 1.4 means both the minimum and maximum are scaled by 1.4 — possible wind values become 40% stronger. At `wind_multiplier = 2.0`, wind can be powerful enough that a perfectly aimed shot requires significant angle compensation.

`GRAVITY` (about 760 px/s²) controls how fast bullets drop. Reducing this to 70% makes shots arc higher and fly farther for the same power — the ballistics feel light and floaty. Increasing it to 120% makes shots drop faster, requiring more power to reach the same distance. Players feel gravity changes immediately.

Fuel cost modification is subtler. Reducing fuel cost (slippery snow) makes repositioning feel free; this changes positioning strategy more than it changes aiming strategy.

---

## Connecting Level Select to Game State

### The Return Value Problem

Currently, `MainMenu.handle_event()` returns the string `"start"` when a level is selected, and `GameManager` responds by starting a generic session. To support multiple maps, this return value must carry the level ID.

The cleanest solution changes the return type to a tuple: `("start", level_id)`. `GameManager` unpacks the tuple, looks up the corresponding `MapConfig` from the catalogue, and constructs the session with that configuration. This is a deliberately minimal interface change — the calling convention for the rest of the event system remains unchanged.

### Restart Behavior

When the player presses R to restart after a game-over, they should restart on **the same map** — not return to the menu or fall back to Level 1. This means `GameManager` must store the currently active `MapConfig` as an instance variable and explicitly pass it to the new session when restarting. This is a common oversight — test it explicitly.

---

## Level Select Card Design

### Information Hierarchy

Each level card should communicate: the map name, what makes it distinctive, and whether it is locked. The most effective approach uses a **thumbnail image** of the map as the card background — a scaled-down view of the actual terrain — with text overlay at the bottom.

Thumbnails communicate aesthetic character immediately and are far more expressive than colored placeholders. White text on a dark semi-transparent overlay bar ensures readability over any background color.

### Locked Levels

Locked cards should show a lock overlay and a "not unlocked" label. Clicking a locked card should do absolutely nothing — no transition, no error, no log output. Verify this explicitly during testing, as the most common bug is a locked level silently launching Level 1 by default.

---

## Physics Override Architecture

### Keeping Constants Pure

The `constants.py` file defines the game's base physics values and should remain unchanged. Map-specific overrides are applied locally when a session begins. `GameManager` stores override values as instance variables (e.g., `self._effective_gravity`, `self._effective_wind_min`) rather than overwriting the global constants. These local override values are reset each time a new map loads.

The bullet physics currently reads `GRAVITY` as a module-level constant. To support per-map gravity, the bullet update method must accept gravity as a parameter. Adding it as a parameter with the constant as its default value preserves backward compatibility while enabling per-session overrides.

---

## Programming Approach for This Phase

### Build MapConfig First, Integrate Later

Define the MapConfig dataclass and the full six-map catalogue before touching `Terrain`, `GameManager`, or `MainMenu`. Verify in a standalone script that each map config has all required fields and that the level-ID lookup works correctly. Only after this is solid should you integrate it into the systems that consume it.

### Integrate One Level Then Test All Six

Wire the map config into `Terrain` and `GameManager` and first verify that Level 1 still looks and plays identically to pre-Phase-4 behavior. Then test each subsequent level in order, verifying the physics modification is perceptible (wind feels stronger, shots feel floaty, etc.).

Phase 1's graceful degradation means you can test map configs before all terrain images are ready — the fallback to procedural terrain generation will activate automatically for any map whose image file is not yet present.
