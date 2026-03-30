# Waterfall Code — Generative Art for Live Projection

An animated waterfall of particles with embedded scrolling source code.
The water reacts to the text with ripples, turbulence, and splashes,
creating a hypnotic visual piece suitable for projection during presentations.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.5+-green)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run
python main.py

# 3. Press F for fullscreen, Q to quit
```

---

## Controls

| Key         | Action                        |
|-------------|-------------------------------|
| `F` / `F11` | Toggle fullscreen             |
| `ESC` / `Q` | Quit                          |
| `R`         | Restart animation             |
| `N`         | Jump to next code file        |
| `P`         | Jump to previous code file    |
| `SPACE`     | Pause / resume scrolling      |
| `UP`        | Increase scroll speed         |
| `DOWN`      | Decrease scroll speed         |
| `1`–`5`     | Switch color palette          |

---

## File Structure

```
waterfall_art/
├── main.py            Entry point — starts the application
├── config.py          All tunable parameters in one place
├── particles.py       Particle system (drops, mist, splashes)
├── text_overlay.py    Code file loading, scrolling, mask generation
├── app.py             Main loop, input handling, render pipeline
├── requirements.txt   Python dependencies
└── README.md          This file
```

---

## How It Works

### Render Pipeline (each frame)

1. **Clear** the screen to the background color.
2. **Text overlay** renders visible code lines with a glow effect and produces
   a **text mask** — a grayscale numpy array where white pixels = text location.
3. **Particle system** spawns new water drops from the top edge, then updates
   every particle. During the update, each drop samples the text mask near its
   position:
   - If text is nearby, the drop gets **lateral turbulence** (a sine wave pushes
     it sideways), **vertical ripple** (wave motion), and **speed damping**
     (it slows down as if hitting an obstacle).
   - Occasionally a drop **splashes** — spawning tiny burst particles.
4. **Mist layer** drifts slowly across the scene for ambient atmosphere.
5. **Vignette** darkens the edges for cinematic depth.
6. **Flip** the double buffer to display the frame.

### Text–Water Interaction

The interaction is driven by a **density field**: at each drop's position, we
sample the text mask in a radius (`text_influence_radius`). The mean brightness
gives a 0–1 "density" value. Higher density = stronger turbulence. This creates
a convincing effect where water appears to *flow around* and *react to* the
code without needing a full fluid simulation.

---

## Color Palettes

| Key | Name           | Character                           |
|-----|----------------|-------------------------------------|
| `1` | Deep Ocean     | Dark navy bg, cyan/blue water       |
| `2` | Moonlit Falls  | Near-black bg, silver/white water   |
| `3` | Neon Cascade   | Dark purple bg, magenta/cyan water  |
| `4` | Emerald Stream | Dark green bg, green water          |
| `5` | Warm Amber     | Dark brown bg, golden/amber water   |

---

## Tweaking the Visual Style

All parameters live in `config.py`. Here are the most impactful ones:

### Particle Density & Speed
```python
max_particles = 3000     # More = denser waterfall (costs performance)
spawn_rate = 12          # Drops per frame — higher = heavier rain
drop_min_speed = 2.0     # Slow drops feel like mist
drop_max_speed = 6.0     # Fast drops feel like a torrent
```

### Text–Water Interaction
```python
text_influence_radius = 60      # Bigger = water reacts from farther away
turbulence_strength = 3.5       # Higher = more lateral displacement
ripple_amplitude = 2.0          # Higher = more vertical waviness
splash_probability = 0.02       # Higher = more splash bursts near text
speed_damping = 0.7             # Lower = drops slow more near text
```

### Text Appearance
```python
font_size = 18           # Larger for big screens
text_alpha = 160         # Lower = more transparent text
text_glow_alpha = 40     # Glow intensity
scroll_speed = 0.6       # Pixels per frame (0.3 = slow, 2.0 = fast)
```

### Mood Adjustments
- **Calm / meditative**: Low `spawn_rate` (5), high `speed_damping` (0.9), low `turbulence_strength` (1.5)
- **Intense / dramatic**: High `spawn_rate` (20), high `turbulence_strength` (5.0), high `splash_probability` (0.05)
- **Minimal**: Low `max_particles` (1000), low `mist_particles` (100), high `text_alpha` (200)

---

## Displaying Your Own Code

Edit `config.py` and set the `code_files` list:

```python
code_files: list = field(default_factory=lambda: [
    "/path/to/your/project/main.py",
    "/path/to/your/project/utils.py",
    "/path/to/your/project/models.py",
])
```

If left empty (the default), the artwork displays its own source code.

---

## Environment Variable Overrides

```bash
# Start in fullscreen
WATERFALL_FULLSCREEN=1 python main.py

# Start with palette 3 (Neon Cascade)
WATERFALL_PALETTE=2 python main.py
```

---

## Performance Notes

- Targets 60 fps at 1920×1080 with 3000 particles.
- If performance is low, reduce `max_particles` and `mist_particles`.
- The text mask uses numpy for fast array operations.
- Circle surfaces are cached to avoid re-rendering each frame.
- On projector setups, windowed mode may perform better than fullscreen
  depending on the GPU driver.

---

## Requirements

- Python 3.10+
- pygame >= 2.5.0
- numpy >= 1.24.0

Both are pure `pip install` — no system dependencies beyond what pygame needs
(SDL2, which pygame bundles on most platforms).
