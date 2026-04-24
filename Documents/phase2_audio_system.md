# Phase 2 — Sound & Music System
## Development Guidelines

---

## Purpose of This Phase

Sound is the most underestimated dimension of game feel. Players will consciously notice bad graphics, but they often cannot articulate why a game without good audio feels hollow — they just feel it. Studies on game UX consistently show that adding sound effects to interactions increases perceived responsiveness, even when the underlying timing has not changed. Background music keeps players emotionally engaged during the quiet waiting periods between shots that define a turn-based game.

This phase adds a complete audio layer to the game: one-shot sound effects triggered by specific gameplay events, and looping background music that switches context between the main menu and the battle screen. It also establishes the volume control interface that the Settings screen (Phase 3) will expose to the player.

No new gameplay mechanics are introduced in this phase. If audio were removed entirely after this phase, the game would play identically. That constraint is intentional — audio should never gate game logic.

---

## Core Technology: pygame.mixer

Pygame's audio subsystem is the `pygame.mixer` module. It operates independently from the display and runs on a dedicated thread. Understanding its architecture is necessary to use it correctly.

### Initialization Parameters

`pygame.mixer` must be initialized with specific parameters before any sound can be played. The four key parameters are frequency (sample rate in Hz), bit depth (size), number of output channels (1 = mono, 2 = stereo), and buffer size. These values affect latency, quality, and compatibility.

A frequency of 44100 Hz is the CD-quality standard and is universally supported. Using 22050 Hz halves memory usage but sounds noticeably thin, especially for music. The bit depth should be -16 (signed 16-bit), which is the default for most audio editors. The buffer size is a tradeoff: larger buffers are more stable on slow computers but introduce latency between triggering a sound and hearing it. For a turn-based game where precise audio timing is not critical, a buffer of 512 samples is a safe choice.

Initialization must happen after `pygame.init()` but before any mixer calls. If initialization fails (which can happen on machines with no audio hardware), the game must continue to run without sound rather than crashing.

### The Channel System

Pygame mixer plays sounds through a fixed pool of **channels**. By default there are 8 channels. Each channel plays one sound at a time. When you call `sound.play()`, pygame finds the first free channel and uses it. If all channels are occupied, the new sound is dropped silently.

For this game, 16 channels is appropriate. In the worst case, you might have an explosion, a fire sound, a movement loop, and 3 simultaneous tank damage sounds all triggering at once. 16 channels provides headroom with room to spare.

The movement loop (tank engine sound while the player holds a movement key) requires a **dedicated channel**. This is because you need to be able to start and stop it precisely, and relying on `sound.play()` finding a channel automatically means you cannot selectively stop that specific instance. Allocate one channel for the movement loop at initialization and use it exclusively for that purpose.

### Music vs. Sound Effects

Pygame treats background music fundamentally differently from sound effects. Music is handled by `pygame.mixer.music`, a separate streaming subsystem that reads from disk continuously. This is important for large audio files — a 3-minute background music track is tens of megabytes; you do not want that fully loaded into memory. The streaming approach means only a small buffer of the music file is held in RAM at any time.

Sound effects (`pygame.mixer.Sound`) are fully pre-loaded into memory. This is correct for short clips (under a few seconds) because it eliminates disk I/O latency at playback time. A fire sound that takes 50 ms to load from disk before playing would feel noticeably delayed.

The practical rule: any audio under 5 seconds is a sound effect (pre-load to memory); anything longer is music (stream from disk).

---

## The AudioManager: Design Philosophy

### Why a Dedicated Manager

Without a central audio manager, sound playback calls get scattered across every class that produces sound. The Tank class plays the movement sound; the Bullet class plays the fire sound; the GameManager plays the explosion and game-over sounds. This creates coupling in two directions: every class depends on the mixer library, and there is no single place to adjust volume or mute the game.

An `AudioManager` class centralizes all mixer interactions. It owns the sound effect cache, manages the music track state, and provides the volume controls that the settings screen needs. Other classes express their intent ("a tank just fired") rather than directly manipulating the audio subsystem.

### Volume Architecture

The game needs two independent volume controls: SFX volume and music volume. These must be fully independent — a player who wants to hear game sounds but prefers to play their own music should be able to mute only the game music.

The SFX volume is applied by setting the `.volume` property on each pre-loaded `Sound` object. This is a property of the sound object itself, not of the channel, so it persists across all future plays of that sound. When the player changes SFX volume, iterate over all cached sound objects and update their volume property.

The music volume is controlled by `pygame.mixer.music.set_volume()`. This affects the currently-playing music track and all future tracks. It is a global setting for the music subsystem.

Store both volume values in the manager so they can be reapplied when assets are reloaded or when the settings are changed. The manager should also expose its current volumes to the settings screen for display.

### Graceful Degradation

Every mixer operation can fail. Hardware might not support audio, the operating system audio drivers might be in use by another application, or a sound file might be corrupted. The `AudioManager` must handle all failure modes without propagating exceptions to game logic.

The approach is to use try/except around every initialization and loading step. Failed sounds are simply absent from the cache — calling `play_sfx()` for a missing key quietly does nothing. The player experiences no sound for that event but the game continues functioning perfectly.

Log warnings to the console for missing files so the developer knows what to fix, but never let a missing `.wav` file become a crash.

---

## Sound Design Principles

### What Sounds Are Needed and Why

**Cannon fire** — This is the most frequently heard sound in the game. It should be distinctive but not fatiguing. A short, sharp crack (around 0.2–0.4 seconds) works better than a prolonged rumble. Players will hear this dozens of times per session.

**Explosion** — The payoff sound after every shot lands. It should feel heavier and more impactful than the fire sound. A deep thump with a brief rumbling tail (0.8–1.5 seconds) communicates the destructive power of the blast. This sound justifies the entire shot sequence — a weak explosion sound makes victories feel anticlimactic.

**Tank movement** — A looping engine sound played while the player holds the movement keys. The loop must be seamless — there should be no click or gap at the loop point. A low-pitched engine rumble that fades in when movement starts and fades out when movement stops creates a much more satisfying movement feel than silence. This is one of the most impactful single audio additions in terms of game feel.

**UI click** — Every button press in the menu should produce a brief, soft click. Without this, the menu feels unresponsive — players cannot tell if their click registered. The sound should be short (under 0.15 seconds) and pleasant, not harsh. Think of the sound as confirming input, not announcing it.

**Game over** — A dramatic sting (2–3 seconds) that plays when the winner is determined. This should feel like a resolution — neither purely triumphant nor purely sad, since the sound plays for both winner and loser perspectives. A neutral fanfare works better than a victory jingle.

### Audio File Specifications

All sound effects must be WAV format with PCM encoding at 44100 Hz, 16-bit, stereo. This matches the mixer initialization parameters exactly, which means pygame does not need to do any format conversion at load time — it plays the file directly from memory.

Background music should be OGG Vorbis format. OGG is an open, patent-free format that pygame's music streaming subsystem handles natively. MP3 is more common but requires licensing in some jurisdictions and has slightly worse looping support in pygame. The music files can be encoded at a moderate bitrate (128 kbps) — in the context of a game where sound effects are also playing, the quality difference above 128 kbps is inaudible.

All sound effects should be **normalized** to approximately -3 dBFS peak level. If sound effects peak at different levels, some will feel much louder than others at the same volume setting. Normalization ensures that the volume slider controls the relative balance predictably.

### Looping Sound Files

The tank movement sound and background music both loop. For seamless looping, the audio file must be designed so the end of the file connects to the beginning without a click or a gap. In audio editing software (Audacity is free and excellent for this), use the "Loop" analysis tool to find a natural loop point where the waveform crosses zero going in the same direction. Trim the file to that length.

Test loops by exporting the file, loading it in a fresh Audacity project, and playing several repetitions. Any click or gap indicates a bad loop point.

---

## Integration Strategy

### Where to Hook Sound Events

Sound events should be triggered at the moment a **game state change** occurs, not at the moment the player presses a key. The distinction matters:

- The fire sound plays when the bullet object is created, not when Space is released (there might be a brief processing delay)
- The explosion sound plays when the crater is carved, not when the bullet goes off-screen
- The movement sound starts when the first movement input is detected and stops when no movement keys are held, checked every frame

Tying sounds to game state rather than input means the sound system naturally handles all cases — including bot AI firing (which produces no keyboard input at all but should still play the fire and explosion sounds).

### Music State Machine

The background music should follow the game's state machine: menu theme plays in the menu, battle theme plays during gameplay, and music stops (or fades out) on game over. Music transitions should use a short fade (0.5–1 second) rather than abrupt cuts — the ear finds hard cuts jarring.

The music manager should track which track is currently playing. Requesting a track that is already playing should be a no-op — this prevents the common bug where entering and exiting the settings screen triggers a music restart.

### The Movement Sound Detail

Movement sound requires special handling because it is continuous, not one-shot. The logic is: every frame, check if the player is currently holding a movement key. If yes and the movement sound is not playing, fade it in. If no and the movement sound is playing, fade it out. This check must happen in the game loop's update step, not in the event handler, because key-held state is not an event — it is a continuous condition.

The fade-in and fade-out prevent clicks that would occur if you started and stopped the loop abruptly. A 100 ms fade is imperceptible to the ear as a fade but eliminates any click artifact.

---

## Programming Approach for This Phase

### Build in Isolation First

Write and test `AudioManager` completely independently before connecting it to `GameManager`. Create a minimal test script that initializes pygame, creates an `AudioManager`, loads a single sound, plays it, and exits. Verify the sound plays correctly. Then test the looping movement sound. Then test music playback. Isolating the audio system from game logic means audio bugs are debugged in a simple environment rather than in the middle of a 600-line game manager.

### Handle the No-Audio Case

Test the game with the `sounds/` folder completely empty. This simulates the state where a developer has not yet added audio assets, and it should work without any errors or warnings breaking the game flow. Only console log messages should indicate that sounds were not found.

### Volume Testing

Test the volume controls by connecting them to the planned settings screen interface, even if that screen is not yet fully implemented. Temporarily add keyboard shortcuts in the main loop (for example, plus/minus keys to adjust SFX volume) to verify that volume changes take effect immediately and are applied to the correct subsystem.

### Latency Verification

After integrating the fire sound, verify that it plays with no perceptible delay when the shot fires. Measure this subjectively: fire ten shots while watching carefully. If the sound consistently feels late (even 50–80 ms of delay is noticeable in action games), the buffer size needs to be reduced. For a turn-based game this is rarely a problem, but it is worth verifying.
