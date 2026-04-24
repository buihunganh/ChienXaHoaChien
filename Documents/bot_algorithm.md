# Bot AI Algorithm — Complete Technical Reference
## Development Guidelines

---

## Overview and Design Intent

The bot AI in *Chien Xa Hoa Chien* is a **physics-aware trajectory planner** that selects a firing angle and power level each turn without any player input. It operates through three distinct difficulty tiers. Each tier applies a different strategy for deciding how to aim, and each is deliberately imperfect — a bot that plays perfectly would be neither fun nor instructive for players.

The design philosophy behind the difficulty tiers is not simply "use more computation at higher difficulty." It is about modeling different **levels of skill and knowledge**:

- An Easy bot knows rough rules but applies them inconsistently
- A Medium bot understands the relationship between distance and power, and can lead a moving target
- A Hard bot runs the same physics simulation the bullet will actually use, and optimizes against it

Understanding this intent is critical before making any changes to the AI. Every noise value, delay range, and fumble probability was chosen to model a believable skill level, not just to produce a numerically convenient miss rate.

---

## Shared Infrastructure: The Physics Foundation

All three difficulty tiers are built on a set of shared helper functions. These helpers represent the AI's understanding of the game's physics — knowledge that a skilled human player would develop through experience.

### Tracking Target Velocity (Exponential Moving Average)

The bot needs to predict *where* the opposing tank will be when the bullet arrives, not just where it is right now. A tank that is moving when the bot fires will have moved during the bullet's flight time. To make this prediction, the bot tracks the target's velocity over time.

The tracking mechanism is an **Exponential Moving Average (EMA)**. Instead of using the raw velocity measured since the last frame (which is noisy due to terrain snapping and collision resolution), EMA smooths the velocity estimate by blending a fraction of the new observation into a running average. With a smoothing factor of 0.22, the estimate responds to trends in about 4–5 frames but ignores single-frame spikes.

The choice of 0.22 as the smoothing factor is a balance between responsiveness and stability. A value closer to 1.0 would make the estimate track instantaneous velocity (very noisy); a value closer to 0.0 would make it nearly static (slow to respond to movement). 0.22 is calibrated for a tank moving at the game's defined speed across typical distances.

This tells us something important about the AI design philosophy: **the bot is not omniscient**. It estimates velocity like a skilled player would — by watching movement trends, not by reading internal state directly.

### Predicting Future Target Position

Given the smoothed velocity estimate, the bot predicts where the target will be at the moment the bullet arrives. The key parameter is **lead time** — an estimate of how many seconds the bullet will spend in the air.

Lead time is approximated from the distance and power. Bullets fired with more power travel faster horizontally and thus reach a given distance faster. Bullets fired at closer targets take less time to arrive. The formula clamps the lead time between 0.30 and 1.50 seconds — these bounds prevent the prediction from becoming absurd (negative lead time, or predicting a target 8 seconds into the future).

The predicted position is clamped to the screen boundaries. This handles edge cases where a target near the screen edge would be predicted to be off-screen.

An important design note: Medium and Hard difficulty use different power estimates for calculating lead time. Medium uses `SHOT_POWER_MAX` (maximum power), which overestimates the lead time. Hard uses 64% of maximum, which is a more realistic estimate of typical shot power. This means Hard leads targets more accurately than Medium — and it is intentional.

### The Angle Orientation Helper

All difficulty tiers express base angles as **left-facing templates** — angles calibrated for a shooter on the right firing toward the left. A helper function converts these into the correct orientation based on which side the shooter is on. If the target is to the right, the angle is mirrored horizontally.

This abstraction simplifies the lookup tables and heuristics. Instead of maintaining two sets of values (left-shooting and right-shooting), you maintain one set and flip as needed.

### The Trajectory Simulator

The Hard bot, and the scoring function used to evaluate its candidates, relies on a **lightweight trajectory simulation**. This simulation runs the same physics equations as the real bullet: horizontal velocity modified by wind each tick, vertical velocity modified by gravity each tick, position updated by velocity each tick. It runs at the game's real tick rate (1/60 second) for up to 360 steps (6 seconds of flight).

Because the simulation uses the same physics constants and the same wind value as the real bullet, it is not an approximation — it predicts the bullet's path with perfect accuracy (within floating-point precision). The simulation terminates when the bullet would leave the screen boundaries or hit solid terrain.

This is the most computationally expensive operation in the AI system, running potentially dozens of times per turn for the Hard bot. On modern hardware this is imperceptible, but it is important to understand what it is doing so you can reason about its performance if the team ever targets slower devices.

### The Error Metric

When the trajectory simulator produces an impact point, a scoring function measures how far that impact is from the desired target. The error is a weighted sum of horizontal and vertical miss distances — horizontal error is weighted more heavily (1.0 vs. 0.35) because in a physics game with an explosion radius, being in the right horizontal position matters far more than being at exactly the right height.

This asymmetric weighting is a design choice that reflects how explosions work in the game. An explosion centered 10 pixels horizontally from a tank will hit it. An explosion centered 10 pixels above a tank at the right horizontal position will also hit it. Weighting horizontal accuracy more heavily leads the optimizer toward solutions that are wide-area hits rather than narrow but perfectly vertical shots.

---

## Difficulty 1 — Easy

### The Skill Model

The Easy bot represents a player who has memorized very rough rules of thumb from limited experience: "if the enemy is close, use less power; if they are far, use more power." They aim in approximately the right direction but are inconsistent due to nerves and poor calibration.

### The Lookup Table Approach

The Easy bot uses a hard-coded table that maps distance ranges to approximate angle and power values. The table has six entries, each covering a range of distance ratios. The bot finds the applicable entry and uses those values as a starting point.

Why a lookup table instead of a formula? Lookup tables are a natural model for how a beginner actually learns — through memorized associations ("at this distance, I used roughly this power and it kind of worked"). The table values are calibrated for zero wind and flat terrain — ideal conditions the actual game rarely provides, which contributes to the bot's inconsistency.

### Noise as a Skill Model

"Noise" in this context means random error added to the planned angle and power. The Easy bot applies large noise: ±22 degrees of angle error and ±170 units of power error. These ranges are calibrated to produce a hit rate of roughly 30–40% at medium range — imperfect enough to feel like a beginner, consistent enough to occasionally score impressive shots that feel lucky.

The fumble roll (a 28% chance of a second, additional noise burst) represents the human experience of occasionally having a particularly bad turn — overthinking a shot, misjudging wind at the last moment, or just getting unlucky. It creates variance in the Easy bot's performance, so players do not experience it as a perfectly calibrated "30% hit rate machine" but as something that occasionally gets hot streaks and cold streaks.

### What the Easy Bot Does NOT Do

The Easy bot does not predict target movement, does not account for wind, and does not simulate trajectories. If wind is strong, the Easy bot will miss in the direction the wind pushes its shots, and it will repeat the same mistake every turn. This is intentional — beginners make predictable mistakes.

### Reaction Delay

The Easy bot waits 0.50 to 1.05 seconds before firing. This models hesitation and uncertainty. Beyond making the bot feel human, it also gives the player time to perceive the turn transition before the bot fires — preventing the jarring experience of a shot appearing the instant the turn changes.

---

## Difficulty 2 — Medium

### The Skill Model

The Medium bot represents an average experienced player who has developed real understanding of the game's mechanics. They know that closer targets need higher arcs and less power. They can see that a moving target needs to be led. They account for trends but still make mistakes, especially when wind is unusual.

### The Heuristic Approach

Instead of a lookup table, the Medium bot uses a **formula** to compute base angle and power from the distance ratio. Power scales linearly with distance across most of the power range; angle scales linearly from steep (for close targets, which need to clear terrain) to flat (for far targets, where a flatter arc covers more horizontal distance per degree of angle).

These formulas are heuristics — they produce approximately correct answers without solving the exact physics equations. The key insight is that the relationship between distance and power is roughly linear across the game's realistic shot range, and the same holds for angle. A formula captures this relationship more smoothly than a lookup table, which has sharp boundaries between entries.

### Target Leading

Unlike the Easy bot, the Medium bot uses the EMA-predicted target position rather than the current position. This means the Medium bot aims ahead of a moving tank — leading it, as a skilled sniper would lead a moving target. The lead prediction uses an overestimate of lead time (based on maximum power), which means the Medium bot sometimes over-leads a target that was not actually moving quickly.

### What the Medium Bot Still Gets Wrong

The Medium bot does not simulate trajectories. Its angle and power estimates come from the heuristic formulas, which are calibrated for average wind conditions. When wind is strong, the formulaic estimates produce shots that drift in the wind direction. A skilled human player would compensate by angling into the wind — the Medium bot does not.

The fumble roll remains (12% chance) but is smaller than the Easy bot's. The noise radius is also reduced. These changes reflect a player who is more consistent but still occasionally has a bad turn.

---

## Difficulty 3 — Hard

### The Skill Model

The Hard bot represents an expert player who works through the physics calculations mentally. They know from experience approximately how much power a certain distance needs, and they refine that estimate by thinking through the trajectory — checking whether their planned shot would be blocked by terrain, whether wind would push it too far left, whether a higher arc would avoid that ridge.

The key difference from Medium is that the Hard bot **verifies its plan** using a simulation of the actual trajectory. Rather than trusting a formula, it checks the predicted impact point and adjusts.

### Warm Starting from Medium Quality

The Hard bot begins its planning by calling the Medium bot's planning function and using that as an initial guess. This is **warm starting** — beginning an optimization from a point that is already reasonably close to the optimal answer. The alternative (starting from a random angle and power) would require far more iterations to converge.

Warm starting is a standard technique in numerical optimization. The initial guess does not need to be great — it just needs to be better than random so the optimizer spends its iterations refining rather than gross searching.

### Iterative Grid Search

The Hard bot improves its initial guess through 8 rounds of **grid search with geometric step decay**. In each round, it evaluates 9 (angle, power) candidates: the current best plus and minus a step size in angle, power, and all four diagonal combinations. It keeps the candidate with the lowest error score and shrinks the step sizes before the next round.

The step sizes shrink geometrically — multiplied by 0.58 (angle) and 0.62 (power) each round. This creates a double funnel effect: early rounds take large steps to escape local minima; later rounds take tiny steps to precisely converge on the best nearby solution. By round 8, the step size is less than one degree and a few power units — sub-pixel accuracy in terms of the trajectory simulation.

### Why 9 Candidates and 8 Rounds?

The 9-candidate grid covers the current best and all adjacent combinations of ±step in both dimensions. Fewer candidates (say, just ±step in one direction) would miss improvements in other directions and converge more slowly. More candidates per round (a larger grid) would be more thorough but computationally heavier.

8 rounds is sufficient for the step sizes to decay from "coarse adjustment" (13°, 95 power) to "fine tuning" (under 0.3°, under 4 power). The total number of trajectory simulations per bot turn is at most 9 × 8 = 72 simulations plus the initial Medium guess. Each simulation runs the same physics loop as the real bullet — this is the most computationally intensive thing the AI does.

### The Binary Search Fallback

When none of the 9 candidates in a round improves on the current best, the optimizer is stuck in a local minimum. Rather than giving up, the Hard bot applies a **proportional correction** to power based on how far the impact point missed horizontally. Too far right means reduce power slightly; too far left means increase power slightly. The correction magnitude is proportional to the miss distance, capped to prevent overcorrection.

This is a simplified form of **Newton's method** — using the gradient (direction and magnitude of the error) to make a targeted correction rather than exploring blindly.

### Intentional Imperfection

After the 8 rounds of optimization, the Hard bot adds a final small noise burst: ±4 degrees and ±34 power units. This is the only randomness in the Hard bot's planning, and it is deliberate.

Without this noise, the Hard bot would achieve near-perfect accuracy on every shot given enough physics simulation time. A bot that hits every shot regardless of what the player does teaches players helplessness — there is no way to beat it through skill, only through luck. The small noise makes the Hard bot beatable: a perfect player who positions well can survive several near-misses before the bot scores a direct hit.

The noise values (±4°, ±34 power) are calibrated to produce approximately a tankwidth of positional error — enough to occasionally miss entirely, often to deal splash damage from a near miss, and reliably to hit within a few meters of the target. This makes Hard feel genuinely difficult without feeling unfair.

---

## The Bot Turn Execution Flow

Understanding when and how the AI executes within the game loop is important for debugging and for adding new behavior.

### Planning Phase

At the start of the bot's turn, `bot_pending_shot` is `False`. On the first update frame of that turn, the bot calls its planning function. The planning function selects an angle and power, stores them internally, sets `bot_pending_shot = True`, and randomly selects a delay duration from the difficulty tier's delay range.

Planning happens exactly **once per turn**. After the plan is set, it is not updated even if the player's tank moves during the delay period. This means a player can sometimes dodge a planned Hard bot shot by repositioning during the delay — which is good design. It gives the player the satisfaction of outplaying the bot through awareness.

### Delay Phase

After planning, the bot waits for its delay timer to count down to zero. This delay serves three purposes: it makes the bot feel human (no player fires instantly), it gives the player a moment to see the turn changed before a shot appears, and it creates a brief window for the player to move and potentially change the ballistics of the planned shot.

### Firing Phase

When the delay expires, the bot fires using the planned angle and power. The fire action uses the same `_fire_charged_shot()` function as the human player — the bot does not bypass the physics or use special firing mechanics. At this point, the turn proceeds exactly as a player turn would: bullet travels, physics apply, explosion resolves, damage is dealt.

---

## Potential Improvements and Extension Points

The current AI architecture is designed to be extended cleanly. Here are directions for future development:

### Terrain Awareness

The current Hard bot occasionally plans a shot that is blocked by a ridge or hill between the shooter and the target. It has no mechanism to detect this — its simulation terminates when the bullet hits terrain, and it scores the miss as a normal error. A terrain-aware extension would detect when the planned shot hits terrain before reaching the target and specifically search for trajectories that clear the obstacle, for example by increasing the arc angle significantly.

### Multi-Turn Memory

The current bot treats each turn as independent. A memory extension would record where the last shot landed and add a correction factor to the next turn's initial guess. A human player who misses to the right would aim slightly left next turn — the bot could do the same, making it feel more adaptive and responsive to the current game state.

### Ammo Selection

The bot currently accepts whichever ammo type is randomly assigned each turn. A more sophisticated bot would consider which ammo type is best for the current situation: Armor-Pierce for a direct shot at low range, High-Explosive for maximizing splash damage at medium range when the target is on uneven terrain.

### Adaptive Difficulty

Rather than three fixed difficulty levels, the game could track the bot's win rate over a session and automatically adjust its noise parameters. If the bot has won the last three turns in a row, increase its noise slightly; if the player has won consistently, decrease it. This creates a dynamic difficulty that keeps the player in the "flow zone" — challenged but not defeated.
