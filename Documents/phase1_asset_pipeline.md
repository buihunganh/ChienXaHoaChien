# Phase 1 — Asset Pipeline & Asset Manager
## Development Guidelines

---

## Purpose of This Phase

The first phase is not about adding features — it is about building the **visual foundation** the entire rest of the game depends on. Every phase that follows (audio, maps, visual effects) assumes that images can be reliably loaded and accessed from anywhere in the codebase. Getting this infrastructure right before touching gameplay is critical. A poorly designed asset system creates coupling problems that ripple through every module.

The secondary objective of this phase is to replace all `pygame.draw` primitive rendering with real artwork. The game currently draws everything using colored rectangles, circles, and polygons — this is perfectly functional for prototyping but sets a low visual ceiling. Players' first impressions are almost entirely visual, and a game that looks hand-drawn in code will feel unfinished regardless of how polished the mechanics are.

---

## Core Technology: pygame's Image and Font Systems

Pygame provides two distinct subsystems for displaying graphical content: the **image module** for raster graphics (PNG, JPG, BMP) and the **font module** for text rendering. Understanding how each one works at a low level is essential before building a layer on top of them.

When pygame loads an image from disk, it produces a `Surface` object — a rectangular grid of pixels stored in memory. The key decision at load time is the **pixel format**: calling `.convert()` optimizes the surface's color format to match the display, which dramatically speeds up blitting (copying pixels to the screen). Calling `.convert_alpha()` does the same but also preserves the alpha (transparency) channel. Any image that has transparent regions — every tank sprite, every UI icon, every cloud — must use `.convert_alpha()`. Forgetting this causes those images to have black backgrounds instead of transparent ones.

Fonts work differently. A font file (`.ttf` or `.otf`) is loaded once by specifying both the file path and the desired pixel size. The result is a `Font` object, not a surface. To produce renderable text, you call the font's `render()` method with a string, an anti-aliasing flag, and a color. Each call to `render()` creates a new surface — this is relatively expensive, so frequently-updated text (like HP values) should be re-rendered only when the underlying value changes, not every frame.

### Why Custom Fonts Matter

The default pygame font (accessed by passing `None` as the font path) is a basic monospace face with no personality. Using a custom font from the `assets/fonts/` directory immediately gives the game a visual identity. The Baloo 2 family (available from Google Fonts) is a strong choice for a tank battle game: it is rounded, friendly, slightly heavy, and reads well at both large (menu titles) and small (HUD labels) sizes. All font rendering throughout the codebase should use consistent size variants — define font sizes as named constants rather than scattering magic numbers across files.

---

## The AssetManager: Design Philosophy

### Why a Dedicated Manager Exists

Without a central loader, every class that needs a sprite would call `pygame.image.load()` directly. This creates several problems:

1. **Redundant loading.** If both the Tank class and the HUD class need the same icon, without a cache they each load it from disk separately. Disk I/O is orders of magnitude slower than memory access.

2. **No single point of failure.** If an asset is missing, the error appears deep inside whatever class tried to load it — not at startup where you expect it. A manager that loads all assets at initialization gives you a clean crash with a useful message before the first frame is rendered.

3. **Scattered path knowledge.** Without a manager, every class must know where assets live on disk. Moving a file to a different subfolder requires finding every file that references it.

4. **Impossible to swap implementations.** If you later want to load assets from a ZIP archive, a content delivery network, or a texture atlas, you change one class rather than dozens of call sites.

### The Singleton Pattern and When to Use It

The AssetManager should be implemented as a **module-level singleton** — a single instance created at import time, accessible from any file via a simple import. This is different from passing the manager as a constructor argument to every class that needs it (dependency injection) or storing it as a global variable in `constants.py`.

Module-level singletons work well for services that are truly global — things that every part of the program needs with no variation. An asset manager fits this profile perfectly. Every class draws something; every class needs the same pool of assets. There is no scenario where you need two different asset managers with different configurations running simultaneously.

The tradeoff is testability: module-level singletons are harder to replace with mock objects in unit tests. For this project that tradeoff is acceptable, but if the project grows into something requiring serious test coverage, switching to dependency injection is straightforward.

### Lazy Loading vs. Eager Loading

There are two strategies for when to load assets: **eager** (load everything at startup before the first frame) and **lazy** (load on first use).

For this game, **eager loading at startup is preferred**. The game has a small, fixed set of assets. Loading them all at once means:
- You discover missing assets immediately, before the player even sees the menu
- There are no frame-rate hitches when a new sprite is needed mid-gameplay
- Memory usage is predictable and bounded

The lazy loading pattern (cache on first `get()` call) is shown in many examples because it is simple to implement, but it can cause stutter if a large texture is loaded at an unexpected moment — for example, when a new map loads mid-game or when an explosion sprite sheet is first accessed during combat. For Phase 1, implement eager loading. If the game later needs downloadable content or very large asset sets, revisit.

### Graceful Degradation

The manager must distinguish between two categories of missing assets:

**Fatal missing assets** are those that make the game impossible to display correctly — the main menu background, the terrain image for the selected level, or the custom font. These should cause an immediate, clear error with the full file path. Attempting to run without them produces a broken visual state that is confusing to debug.

**Non-fatal missing assets** are those with reasonable fallbacks — for example, if a tank model image is missing, render the tank using the existing `pygame.draw` code as a placeholder. If a UI icon is missing, leave that space blank. This allows artists to work incrementally, adding assets one at a time, without the programmer having to block on their work.

---

## Asset Organization Strategy

### Directory Structure as API

The folder structure inside `assets/images/` is not just organization — it is part of the API. When you call the asset manager with a key like `"tanks/tank_green_body"`, the path separator communicates the category. This makes it possible to iterate over all images in a category (e.g., all terrain thumbnails) by scanning a specific subfolder.

Establish these conventions before adding any assets, and enforce them throughout the project:

- **`bg/`** — Full-screen background scenes, one per map theme. These are the largest images (1280×720) and are loaded as non-alpha surfaces since they always cover the entire screen.
- **`terrain/`** — Terrain collision masks. These must be RGBA where the alpha channel drives physics — fully transparent pixels are air, any opaque pixel is ground. The visual appearance (the colors players see) is contained in the RGB channels of the same image.
- **`tanks/`** — Individual tank component sprites, organized by color/skin. Each tank has three separate images: body, turret, and barrel. The separation allows independent rotation of each component.
- **`ui/`** — Every interface element: button skins, panel backgrounds, icons, the VS shield badge.
- **`fx/`** — Transient visual effects: explosion sprite sheets, particle images.

### Image Format Decisions

Use **PNG** for everything. PNG is lossless, supports alpha channels natively, and pygame handles it without additional libraries. JPG is tempting for backgrounds (smaller file size) but introduces compression artifacts on hard edges and does not support transparency — avoid it.

For the terrain mask specifically, the image must be saved in RGBA mode with no lossy compression. A single compressed artifact in the alpha channel creates a phantom solid pixel that a bullet might collide with unexpectedly. Always use a PNG editor (GIMP, LibreSprite, Aseprite) to verify the alpha channel looks correct before committing the file.

### Naming Conventions

Use `snake_case` for all filenames and folder names. Keys in the asset manager mirror the file path relative to `IMAGES_DIR`. Never abbreviate in ways that require memorization — `tank_green_body` is better than `tgb`. The extra characters cost nothing and eliminate ambiguity.

---

## Tank Rendering: The Three-Layer Approach

### Why Three Images Instead of One

The current code builds the tank sprite procedurally in `_build_sprite()` every frame and then rotates the whole sprite by the slope angle. This works but has a critical limitation: it rotates the barrel at the same angle as the body, which means the barrel always points at whatever angle it was at when the sprite was built, misaligned with the `aim_angle_deg`.

The correct model separates the tank into three independently rendered layers:

1. **The body** (rectangular hull + tracks) rotates with the terrain slope. Only the slope angle affects it.
2. **The turret** (circular cupola on top of the body) inherits the body's position but does not rotate — it always sits level relative to the world.
3. **The barrel** (cannon tube) rotates around the turret center by `aim_angle_deg`. Its pivot point is at the barrel's hinge end, not the tip.

This three-layer approach matches how all professional 2D tank games handle rendering. It allows the body to tilt on slopes while the turret and barrel remain independent. Critically, it also makes it visually clear to the player exactly which direction the cannon is aimed.

### The Barrel Pivot Problem

Rotating a sprite in pygame always rotates it around the image's geometric center. But the barrel should rotate around the hinge point — the end that attaches to the turret, not the middle of the barrel. To achieve this correctly, the barrel image must be **designed with extra transparent padding** on the hinge end so that the geometric center of the full image coincides with the hinge point.

Think of it this way: if the barrel tube itself is 38 pixels long, the full barrel image should be 76 pixels wide — 38 pixels of transparent space on the hinge side, then 38 pixels of actual barrel artwork. After rotation, the sprite is positioned so the image's center (pixel 38) lands on the turret center. The barrel appears to rotate around exactly that point.

This is an art-side responsibility. Communicate this requirement clearly in the art brief — the programmer cannot fix a badly constructed barrel image post-hoc without rewriting the rendering math.

---

## HUD Rendering Strategy

The HUD currently draws everything from scratch every frame using primitive shapes. The upgrade in Phase 1 is to use image panels as background frames, with dynamic values drawn on top.

The key insight is distinguishing between **static** and **dynamic** elements:

**Static elements** (panel frame, icon images, labels like "HP" and "Fuel") never change during gameplay. These should be blit from pre-rendered image surfaces. Never re-render a static text label every frame — render it once at initialization and cache it.

**Dynamic elements** (bar fill ratios, wind value, charge power percentage) change frequently. The fill portion of a HP bar, for example, must be redrawn every frame because the player's health changes. However, it should be drawn on top of the static panel frame, not redraw the frame itself.

A practical pattern: in `HUD.__init__()`, pre-render all static surfaces (icons, labels, panel backgrounds) and store them as instance attributes. In `HUD.draw()`, blit the pre-rendered surfaces first, then draw the dynamic portions on top using primitives. This approach is faster and cleaner than the current fully-procedural system.

---

## Programming Approach for This Phase

### Order of Operations

1. Write and test `AssetManager` with a minimal set of assets (one image, one font, one sound) before integrating it with any game module. Verify the cache works, verify missing files produce clear errors.
2. Update `constants.py` with all new directory paths. These paths are the contract between the asset manager and the rest of the codebase.
3. Integrate the font change across HUD and MainMenu. This is low-risk and immediately visible.
4. Integrate the background image. Replacing the `fill(SKY_BLUE)` call is the simplest visual upgrade.
5. Replace the tank drawing. This is the highest-risk change because it touches physics (the barrel tip position affects shot trajectory). Test carefully that `get_barrel_tip()` still returns the correct world-space coordinate after switching to sprite rendering.
6. Replace HUD elements last, since they depend on the font changes from step 3.

### Testing Mindset

For each rendering change, the test is visual — run the game and look. But also verify that game mechanics have not changed:
- After switching to sprite rendering, fire several shots and confirm the bullet originates from the barrel tip, not from the body center or some offset position.
- After switching the terrain image, verify that a tank placed at the left edge sits on solid ground, not floating in air.
- After switching fonts, verify that text does not overflow HUD panels or get clipped.

Regression is most likely in the barrel tip calculation. Keep the old `get_barrel_tip()` implementation available as a reference to compare against during development.
