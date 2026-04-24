# Phase 5 — Polish, Explosion FX & UI Animations
## Development Guidelines

---

## Purpose of This Phase

After Phases 1–4, the game is mechanically complete and visually presentable. Phase 5 is about the gap between "it works" and "it feels great." That gap is almost entirely filled by visual feedback: animations, particle effects, dynamic UI responses, and screen reactions to impactful events.

These additions change nothing about how the game plays. Removing them would leave the game fully functional. But their presence transforms how the experience *feels* — explosions become satisfying, damage lands with weight, the power bar communicates urgency, and the screen shakes with each blast. These micro-moments of feedback are what players remember.

---

## The Philosophy of Game Feel

### Feedback Loops

The core psychological mechanism behind good game feel is the **feedback loop**: the player takes an action, the game responds visibly and audibly, and the player feels that their action had consequence. In a tank battle game, the feedback loop for firing a shot is: aim → charge → fire → watch bullet travel → explosion → crater carved → damage shown → turn changes.

Every step in that chain is an opportunity to add feedback. Phase 5 primarily enriches the explosion and damage steps, which are the emotional climax of each turn.

### The 200ms Window

Human perception of cause and effect requires that the visual response to an action begins within roughly 200 milliseconds. Effects that start within this window feel instant — caused by the player's action. Effects that start later feel like coincidences — disconnected from what the player did.

For a turn-based game with a clearly visible bullet trajectory, the timing constraint is relaxed — players watch the bullet and expect the explosion at a natural point. But other effects must still be immediate: button click feedback, turn indicator updates, and hit flashes should all appear in the same frame as their trigger event.

---

## Core Technology: pygame Sprites and Pixel Manipulation

### How Sprite Sheets Work

An explosion animation is stored as a **sprite sheet**: multiple animation frames laid out in a single image file, typically in a horizontal row. This approach exists for two practical reasons: it reduces the number of file load operations (one file instead of eight), and it keeps related animation frames together as a single asset.

To use a sprite sheet, load it as a single surface, then slice it into individual frame surfaces using `Surface.subsurface()`. This method creates a view into a region of the parent surface — importantly, it does not copy the pixel data. The frame surfaces share memory with the parent sheet, which means slicing is fast and memory-efficient.

### Alpha and Transparency in Animations

Explosion frames should be RGBA images — the background of each frame is transparent, and only the fireball and smoke pixels are opaque. This allows the explosion to appear cleanly over any background without a rectangular black box behind it.

When fading an animation out (gradually reducing its opacity near the end), use `surface.set_alpha()` to apply a global alpha multiplier to the entire surface. This is different from per-pixel alpha (which is encoded in the surface's individual pixel data). `set_alpha()` is a quick uniform fade applied at blit time without modifying the surface itself.

### rotozoom vs. scale

When scaling explosion frames to match different explosion radii, `pygame.transform.scale()` resizes to exact pixel dimensions. `pygame.transform.rotozoom()` scales by a ratio and also supports simultaneous rotation. For explosion scaling where no rotation is needed, `scale()` is preferable because its output is more predictable — `rotozoom()` uses anti-aliased interpolation that can produce slightly blurry results at small scales and adds minor pixel-coordinate offsets that complicate positioning.

---

## Explosion Animation: Design and Implementation Thinking

### What Makes a Good Explosion

An explosion animation should convey three phases:

1. **Flash** (frames 1–2): A bright, near-white burst at the center of the impact. This represents the initial detonation wave. The flash should be immediate and brief — half-frames at most.
2. **Fireball** (frames 3–6): The expanding orange and yellow ball of fire. This is the visually dominant phase. The fireball should expand outward from the impact point.
3. **Smoke dissipation** (frames 7–8): Dark smoke dispersing. The fireball shrinks and transitions to gray/black smoke that fades to transparency.

The total duration should be short — between 0.5 and 0.8 seconds. Long explosions feel satisfying on the first viewing but become tedious after the hundredth. Err on the side of shorter.

### Scaling to Match the Crater

The game has three ammunition types with different explosion radii (Normal, HE, Armor-Pierce). The explosion animation should be scaled proportionally to the actual explosion radius so the visual matches the physical crater size. A large HE explosion should produce a visually larger fireball than a small armor-piercing round. This relationship reinforces the player's understanding of what each ammo type does.

### Positioning

The explosion should be centered on the bullet's impact point at the moment it hits terrain or a tank. The impact point is already computed in `_explode()` — it is the bullet's current x,y position. The animation center should match this position, adjusted by any active screen shake offset.

---

## Floating Damage Numbers

### Why They Matter

The damage numbers that float upward above a wounded tank are one of the most effective UI patterns in turn-based combat games. They answer the player's instinctive question after a shot lands: "How much damage did that do?" Without them, the player must read the HP bar, remember the previous HP value, and calculate the difference — a mental effort most players do not bother with. With them, the information is immediate and unambiguous.

### Motion Design

The classic floating damage number rises about 40–80 pixels over its lifetime, fades from fully opaque to fully transparent, and disappears after about one second. The upward motion and fade create visual priority — fresh damage numbers catch the eye immediately, and older ones (from earlier turns) have already faded, so there is no confusion about which damage is from the current turn.

Color coding adds additional information: red for high damage, yellow for moderate, and white for chip damage. The thresholds for these colors should be relative to `TANK_MAX_HP`: damage above 40% of max HP is red, above 20% is yellow, below that is white. Using absolute thresholds would make the colors feel arbitrary.

### Multiple Simultaneous Numbers

Splash damage from a large explosion can damage both tanks simultaneously. The FX manager must handle multiple floating numbers at the same time without them overlapping into an unreadable stack. If two damage numbers have overlapping positions, stagger them vertically — offset the second number upward by 30 pixels relative to the first.

---

## Screen Shake

### Calibrating Intensity

Screen shake communicates the physical impact of large explosions. It should be proportional to the explosion radius — a Normal round produces a small, brief shake; a large High-Explosive round produces a stronger, longer shake. The shake should feel like a physical consequence of a nearby blast, not like a camera malfunction.

Keep the shake short (0.15–0.35 seconds maximum) and the displacement modest (3–10 pixels). Excessive screen shake is one of the most commonly cited sources of player disorientation and frustration. When in doubt, use less shake than you think you need.

### What Shakes and What Does Not

The game world shakes — terrain, tanks, bullet, decorative elements all move together. The HUD does not shake. This maintains the player's ability to read health, fuel, and wind information even during or immediately after an explosion. Shaking the HUD would feel wrong because it suggests the information itself is uncertain, not just the camera position.

Implementation-wise, this means applying the shake offset to every world blit call in `render()`, but not to the HUD draw calls. The HUD draws last, on top of everything, without any offset. The shake offset is calculated once per frame in the FX manager and read by `GameManager.render()`.

---

## HUD Micro-Animations

### HP Bar Color Shift

A static green HP bar communicates nothing about urgency. A bar that smoothly transitions from green (healthy) to yellow (damaged) to red (critical) adds urgency without requiring the player to read a number. The color shift also makes the emotional stakes of each shot immediately visible: watching a bar go from green to red over two turns is more visceral than watching a number change.

The transition should be smooth — not a sudden jump from green to yellow when crossing 50%. Use linear interpolation between the color values, calculated from the current HP ratio. Players should never consciously notice the color changing; they should just instinctively feel more anxious as the bar shifts toward red.

### Power Bar Glow When Near Maximum

When the charge power oscillates above 80% of maximum, adding a pulsing glow effect around the power bar reinforces the sense that the cannon is "fully loaded" and ready for a powerful shot. The pulse should use a sine wave oscillating between dim and bright, giving it a living, breathing quality rather than a static flash.

The glow should draw attention to the power bar at the exact moment when the player's decision to release Space is most consequential. This is an example of UI design that serves gameplay — the animation communicates strategic information (shoot now for maximum power) while also being visually pleasing.

### Turn Indicator Blink

A small arrow that blinks above the active tank — alternating visible and invisible at about 2 Hz — draws the player's attention to which tank they are controlling. This is especially useful for new players who might lose track of whose turn it is. The blink rate (2 Hz, meaning 250 ms on and 250 ms off) is slow enough to be readable but fast enough to clearly read as a pulsing indicator rather than as a static sprite.

Implement the blink using `pygame.time.get_ticks()` — divide the elapsed milliseconds by 500 and take modulo 2 to alternate between 0 and 1. This ties the blink rate to wall-clock time rather than to game frames, so it appears consistent regardless of frame rate.

---

## The FxManager: Architecture

### Ownership and Lifecycle

The `FxManager` is created by `GameManager` and persists for the lifetime of the session. Individual effects (explosions, damage numbers) are created by calling methods on the manager and have their own lifetimes. Each effect is an object with an `alive` flag and a `timer`. The manager's `update()` method advances all timers and removes dead effects. This is the standard **object pool pattern** for temporary game effects.

Avoid allocating new list objects frequently — instead, maintain one list of active effects per type and remove dead ones at the end of each update cycle rather than during iteration (modifying a list while iterating it is a common source of bugs).

### Drawing Order

Effects must be drawn in the correct layer order. Explosions should appear above terrain and tanks (they are surface-level events) but below the HUD (which always sits on top). Damage numbers should be drawn above explosions — the numberis the informational layer, the explosion is the decorative layer.

The drawing order in `GameManager.render()`: background → terrain → tanks → bullet → explosion FX → damage number FX → HUD. This order ensures that informational elements are always readable regardless of what visual effects are happening underneath them.

---

## Programming Approach for This Phase

### Build FxManager in Isolation

Write the `FxManager` class and test it with a minimal script before integrating it into `GameManager`. Create a script that spawns explosions at random positions and verifies the animation plays correctly, the alphas fade correctly, and the objects are cleaned up after their lifetime expires. Only then integrate it into the main game.

### Visual Calibration Requires Playing the Game

Unlike functional features that can be verified by checking expected outputs, visual effects must be calibrated by playing the game and adjusting values based on feel. Expect to iterate:
- Run the game, trigger an explosion, observe the animation
- Adjust the duration, scale factor, or fade timing
- Repeat until the explosion feels satisfying

Keep a separate test level or shortcut that triggers large explosions immediately so this iteration cycle is fast. A calibration that takes 30 seconds per iteration will produce much better results than one that takes 5 minutes.

### Performance Vigilance

Visual effects that run every frame add CPU cost. For each frame, the FX manager iterates all active effects, updates timers, and blits scaled surfaces. At peak visual complexity (two tanks both exploding simultaneously with multiple damage numbers), this should still comfortably run within the 16ms frame budget at 60 FPS.

The main performance risk is `pygame.transform.scale()` called every frame on explosion frames. Pre-scale the frames once when the explosion is spawned (using the radius-based scale factor) rather than re-scaling on every draw call. The surface is the same size for the entire lifetime of that particular explosion — only pre-compute once.
