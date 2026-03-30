"""
Particle system — water drops, mist blobs, and splash fragments.

Each particle is stored as a compact numpy-friendly struct for speed.
The system supports thousands of simultaneous particles at 60 fps.
"""

import math
import random
import pygame
import numpy as np
from config import Config


class Particle:
    """A single water drop."""
    __slots__ = ("x", "y", "vx", "vy", "size", "color", "alpha",
                 "base_vy", "age", "wobble_phase")

    def __init__(self, x, y, vx, vy, size, color, alpha):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.alpha = alpha
        self.base_vy = vy
        self.age = 0
        self.wobble_phase = random.uniform(0, math.tau)


class ParticleSystem:
    """
    Manages the full water simulation:
      - spawning drops from the top
      - ambient mist
      - text-interaction turbulence
      - rendering to a surface
    """

    def __init__(self, config: Config):
        self.cfg = config
        self.drops: list[Particle] = []
        self.mist: list[Particle] = []
        self.splashes: list[Particle] = []
        self.time = 0.0

        # Pre-create a small circle surface cache for each size bucket
        self._circle_cache: dict[tuple, pygame.Surface] = {}

        self._init_mist()

    # ── Initialization ──────────────────────────────────────
    def _init_mist(self):
        """Spawn ambient mist particles spread across the screen."""
        c = self.cfg
        pal = c.palette
        for _ in range(c.mist_particles):
            self.mist.append(Particle(
                x=random.uniform(0, c.width),
                y=random.uniform(0, c.height),
                vx=random.uniform(-0.3, 0.3),
                vy=random.uniform(-0.2, 0.2),
                size=random.uniform(2, c.mist_max_size),
                color=pal["mist"],
                alpha=random.randint(5, c.mist_alpha),
            ))

    # ── Spawning ────────────────────────────────────────────
    def spawn_drops(self):
        """Spawn new water drops from the top edge each frame."""
        c = self.cfg
        pal = c.palette
        for _ in range(c.spawn_rate):
            if len(self.drops) >= c.max_particles:
                break
            # Clustered spawn — denser in the center, sparser at edges
            cx = c.width / 2
            spread = c.width * 0.45
            x = random.gauss(cx, spread)
            x = max(0, min(c.width, x))

            self.drops.append(Particle(
                x=x,
                y=random.uniform(-20, 0),
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(c.drop_min_speed, c.drop_max_speed),
                size=random.uniform(c.drop_min_size, c.drop_max_size),
                color=random.choice(pal["water"]),
                alpha=random.randint(c.drop_alpha_min, c.drop_alpha_max),
            ))

    def spawn_splash(self, x: float, y: float):
        """Spawn a small burst of splash particles at (x, y)."""
        pal = self.cfg.palette
        for _ in range(random.randint(2, 5)):
            self.splashes.append(Particle(
                x=x + random.uniform(-4, 4),
                y=y + random.uniform(-2, 2),
                vx=random.uniform(-2.5, 2.5),
                vy=random.uniform(-3.0, -0.5),
                size=random.uniform(0.5, 1.5),
                color=random.choice(pal["water"]),
                alpha=random.randint(100, 220),
            ))

    # ── Update ──────────────────────────────────────────────
    def update(self, text_mask: np.ndarray | None = None):
        """
        Advance all particles by one frame.

        text_mask: a 2D numpy array (height x width) where nonzero values
                   indicate the presence of rendered text. Used to create
                   turbulence interactions.
        """
        c = self.cfg
        self.time += 1.0

        # Global wind (slow sine wave)
        wind = math.sin(self.time * c.wind_frequency) * c.wind_strength

        # ── Update drops ────────────────────────────────────
        alive = []
        for p in self.drops:
            p.age += 1

            # Base motion
            p.vy = p.base_vy
            p.vx = wind + math.sin(p.wobble_phase + self.time * 0.05) * 0.3

            # Text interaction: check if drop is near rendered text
            if text_mask is not None:
                ix = int(p.x)
                iy = int(p.y)
                if 0 <= ix < text_mask.shape[1] and 0 <= iy < text_mask.shape[0]:
                    # Sample a small area around the drop
                    r = c.text_influence_radius
                    y0 = max(0, iy - r)
                    y1 = min(text_mask.shape[0], iy + r)
                    x0 = max(0, ix - r)
                    x1 = min(text_mask.shape[1], ix + r)
                    region = text_mask[y0:y1, x0:x1]
                    density = np.mean(region) / 255.0 if region.size > 0 else 0.0

                    if density > 0.01:
                        # Turbulence — lateral displacement
                        turb = math.sin(p.y * c.ripple_frequency + self.time * 0.08)
                        p.vx += turb * c.turbulence_strength * density

                        # Ripple — vertical wave
                        ripple = math.cos(p.x * c.ripple_frequency * 0.7 + self.time * 0.1)
                        p.vy += ripple * c.ripple_amplitude * density

                        # Slow down near text (damping)
                        p.vy *= (1.0 - density * (1.0 - c.speed_damping))

                        # Occasional splash
                        if density > 0.05 and random.random() < c.splash_probability:
                            self.spawn_splash(p.x, p.y)

            # Apply velocity
            p.x += p.vx
            p.y += p.vy

            # Wrap horizontally
            if p.x < -10:
                p.x = c.width + 10
            elif p.x > c.width + 10:
                p.x = -10

            # Kill if off bottom
            if p.y < c.height + 20:
                alive.append(p)

        self.drops = alive

        # ── Update splashes ─────────────────────────────────
        splash_alive = []
        for p in self.splashes:
            p.age += 1
            p.vy += 0.15  # gravity
            p.x += p.vx
            p.y += p.vy
            p.alpha = max(0, p.alpha - 6)
            if p.alpha > 0 and p.age < 40:
                splash_alive.append(p)
        self.splashes = splash_alive

        # ── Update mist ─────────────────────────────────────
        for p in self.mist:
            p.x += p.vx + wind * 0.2
            p.y += p.vy
            p.wobble_phase += 0.01
            # Wrap
            if p.x < -20:
                p.x = c.width + 20
            elif p.x > c.width + 20:
                p.x = -20
            if p.y < -20:
                p.y = c.height + 20
            elif p.y > c.height + 20:
                p.y = -20

    # ── Rendering ───────────────────────────────────────────
    def _get_circle(self, radius: int, color: tuple, alpha: int) -> pygame.Surface:
        """Get (or create) a cached translucent circle surface."""
        key = (radius, color, alpha)
        if key not in self._circle_cache:
            size = radius * 2 + 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (radius + 1, radius + 1), radius)
            self._circle_cache[key] = surf
            # Limit cache size
            if len(self._circle_cache) > 2000:
                # Remove oldest quarter
                keys = list(self._circle_cache.keys())
                for k in keys[:500]:
                    del self._circle_cache[k]
        return self._circle_cache[key]

    def draw(self, surface: pygame.Surface):
        """Render all particles onto the given surface."""
        # Mist first (behind everything)
        for p in self.mist:
            r = max(1, int(p.size))
            circ = self._get_circle(r, p.color, p.alpha)
            surface.blit(circ, (int(p.x) - r - 1, int(p.y) - r - 1),
                         special_flags=pygame.BLEND_ADD)

        # Water drops
        for p in self.drops:
            r = max(1, int(p.size))
            alpha = max(0, min(255, p.alpha))
            circ = self._get_circle(r, p.color, alpha)
            surface.blit(circ, (int(p.x) - r - 1, int(p.y) - r - 1),
                         special_flags=pygame.BLEND_ADD)

        # Splashes on top
        for p in self.splashes:
            r = max(1, int(p.size))
            alpha = max(0, min(255, p.alpha))
            circ = self._get_circle(r, p.color, alpha)
            surface.blit(circ, (int(p.x) - r - 1, int(p.y) - r - 1),
                         special_flags=pygame.BLEND_ADD)
