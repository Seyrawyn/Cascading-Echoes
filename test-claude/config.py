"""
Configuration — every tunable parameter in one place.

Tweak these to change the visual style, speed, density,
color palette, and text behavior of the waterfall.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# ─── Type aliases ───────────────────────────────────────────
Color = Tuple[int, int, int]
Palette = List[Color]


@dataclass
class Config:
    """Master configuration for the waterfall artwork."""

    # ── Window ──────────────────────────────────────────────
    width: int = 1920
    height: int = 1080
    fullscreen: bool = False
    fps: int = 60
    title: str = "Waterfall Code"

    # ── Particle system (water drops) ───────────────────────
    max_particles: int = 3000          # total water drops alive at once
    spawn_rate: int = 12               # drops spawned per frame
    drop_min_speed: float = 2.0        # slowest fall speed (px/frame)
    drop_max_speed: float = 6.0        # fastest fall speed (px/frame)
    drop_min_size: float = 1.0         # smallest drop radius
    drop_max_size: float = 3.5         # largest drop radius
    drop_alpha_min: int = 40           # minimum opacity (0-255)
    drop_alpha_max: int = 200          # maximum opacity (0-255)
    wind_strength: float = 0.3         # horizontal drift amplitude
    wind_frequency: float = 0.01       # how fast wind oscillates

    # ── Turbulence near text ────────────────────────────────
    text_influence_radius: int = 60    # how far (px) text disturbs water
    turbulence_strength: float = 3.5   # lateral displacement near text
    ripple_amplitude: float = 2.0      # sine-wave ripple strength
    ripple_frequency: float = 0.15     # ripple wave frequency
    splash_probability: float = 0.02   # chance a drop spawns a splash near text
    speed_damping: float = 0.7         # drops slow down near text (multiplier)

    # ── Mist / spray layer ──────────────────────────────────
    mist_particles: int = 400          # ambient mist count
    mist_max_size: float = 5.0         # mist blob radius
    mist_alpha: int = 25               # mist opacity

    # ── Code text overlay ───────────────────────────────────
    font_size: int = 18                # monospace font size in pixels
    line_spacing: float = 1.5          # multiplier on font_size for line height
    text_alpha: int = 160              # base text opacity (0-255)
    text_glow_alpha: int = 40          # glow layer opacity
    text_glow_radius: int = 2          # glow offset in pixels
    scroll_speed: float = 0.6          # pixels per frame the text scrolls up
    scroll_speed_step: float = 0.1     # increment when pressing UP/DOWN
    text_margin_left: int = 80         # left padding for code text
    text_margin_right: int = 80        # right padding
    file_gap_lines: int = 8            # blank lines between files
    show_filename_header: bool = True  # show "── filename ──" separator

    # ── Color palettes ──────────────────────────────────────
    #   Each palette: (background, water_colors[], text_color, glow_color)
    #   water_colors is a list of 3+ colors the drops randomly pick from.
    active_palette: int = 0

    palettes: list = field(default_factory=lambda: [
        {   # 0 — Deep Ocean (default: dark bg, cyan/blue water)
            "name": "Deep Ocean",
            "bg": (6, 8, 18),
            "water": [(80, 200, 255), (40, 160, 230), (120, 220, 255),
                      (60, 180, 240), (20, 140, 210)],
            "text": (160, 210, 240),
            "glow": (80, 180, 255),
            "mist": (60, 160, 220),
        },
        {   # 1 — Moonlit Falls (silver/white on near-black)
            "name": "Moonlit Falls",
            "bg": (4, 4, 12),
            "water": [(200, 210, 230), (170, 180, 200), (230, 235, 245),
                      (150, 160, 180), (220, 225, 240)],
            "text": (200, 205, 215),
            "glow": (180, 190, 210),
            "mist": (160, 170, 190),
        },
        {   # 2 — Neon Cascade (cyberpunk magenta/cyan)
            "name": "Neon Cascade",
            "bg": (8, 2, 16),
            "water": [(255, 60, 180), (80, 220, 255), (200, 40, 255),
                      (60, 255, 200), (255, 100, 220)],
            "text": (220, 180, 255),
            "glow": (180, 60, 255),
            "mist": (140, 40, 200),
        },
        {   # 3 — Emerald Stream (forest greens)
            "name": "Emerald Stream",
            "bg": (4, 12, 8),
            "water": [(40, 220, 120), (60, 200, 100), (80, 240, 140),
                      (30, 180, 90), (100, 255, 160)],
            "text": (140, 230, 170),
            "glow": (60, 200, 120),
            "mist": (40, 160, 100),
        },
        {   # 4 — Warm Amber (golden/amber tones)
            "name": "Warm Amber",
            "bg": (16, 8, 2),
            "water": [(255, 180, 40), (240, 160, 60), (255, 200, 80),
                      (220, 140, 30), (255, 220, 100)],
            "text": (255, 210, 150),
            "glow": (255, 180, 60),
            "mist": (200, 140, 40),
        },
    ])

    # ── Derived helpers ─────────────────────────────────────
    @property
    def palette(self) -> dict:
        return self.palettes[self.active_palette % len(self.palettes)]

    @property
    def line_height(self) -> int:
        return int(self.font_size * self.line_spacing)

    # ── Code files to display ───────────────────────────────
    # Paths relative to project root, or absolute.
    # If empty, the program displays its own source files.
    code_files: list = field(default_factory=list)
