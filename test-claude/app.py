"""
Application — the main loop that ties particles, text, and rendering together.

Handles window management, input, and the render pipeline.
"""

import sys
import pygame
from config import Config
from particles import ParticleSystem
from text_overlay import TextOverlay


class WaterfallApp:
    """Main application controller."""

    def __init__(self, config: Config):
        self.cfg = config
        self.running = False
        self.clock: pygame.time.Clock | None = None
        self.screen: pygame.Surface | None = None
        self.particles: ParticleSystem | None = None
        self.text: TextOverlay | None = None
        self.frame: int = 0

    # ── Setup ───────────────────────────────────────────────
    def _init_pygame(self):
        """Initialize pygame and create the window."""
        pygame.init()
        pygame.font.init()

        c = self.cfg
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        if c.fullscreen:
            flags |= pygame.FULLSCREEN
            info = pygame.display.Info()
            c.width = info.current_w
            c.height = info.current_h

        self.screen = pygame.display.set_mode((c.width, c.height), flags)
        pygame.display.set_caption(c.title)
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

    def _init_systems(self):
        """Create particle and text systems."""
        self.particles = ParticleSystem(self.cfg)
        self.text = TextOverlay(self.cfg)

    # ── Input handling ──────────────────────────────────────
    def _handle_events(self):
        """Process keyboard and window events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key: int):
        """Dispatch key presses."""
        c = self.cfg

        # Quit
        if key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False

        # Fullscreen toggle
        elif key in (pygame.K_f, pygame.K_F11):
            c.fullscreen = not c.fullscreen
            self._init_pygame()
            self._init_systems()

        # Restart
        elif key == pygame.K_r:
            self.frame = 0
            self._init_systems()

        # Next/prev file
        elif key == pygame.K_n:
            self.text.next_file()
        elif key == pygame.K_p:
            self.text.prev_file()

        # Pause scrolling
        elif key == pygame.K_SPACE:
            self.text.paused = not self.text.paused

        # Scroll speed
        elif key == pygame.K_UP:
            c.scroll_speed = min(5.0, c.scroll_speed + c.scroll_speed_step)
        elif key == pygame.K_DOWN:
            c.scroll_speed = max(0.0, c.scroll_speed - c.scroll_speed_step)

        # Palette switching (1-5)
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            idx = key - pygame.K_1
            if idx < len(c.palettes):
                c.active_palette = idx
                # Rebuild systems with new colors
                self._init_systems()

    # ── Render pipeline ─────────────────────────────────────
    def _render(self):
        """One frame of the render pipeline."""
        c = self.cfg
        pal = c.palette
        screen = self.screen

        # 1. Clear to background
        screen.fill(pal["bg"])

        # 2. Draw text and get the interaction mask
        text_mask = self.text.draw(screen, self.frame)

        # 3. Update and draw particles (water reacts to text mask)
        self.particles.spawn_drops()
        self.particles.update(text_mask)
        self.particles.draw(screen)

        # 4. Subtle vignette overlay for depth
        self._draw_vignette(screen)

        # 5. Flip
        pygame.display.flip()

    def _draw_vignette(self, surface: pygame.Surface):
        """Draw a soft dark vignette around the edges for cinematic depth."""
        c = self.cfg
        # We create a radial gradient once and cache it
        if not hasattr(self, "_vignette"):
            vig = pygame.Surface((c.width, c.height), pygame.SRCALPHA)
            cx, cy = c.width // 2, c.height // 2
            max_dist = (cx ** 2 + cy ** 2) ** 0.5
            # Draw concentric rectangles with increasing opacity at edges
            for i in range(0, max(c.width, c.height) // 2, 4):
                alpha = int(60 * (i / (max(c.width, c.height) / 2)) ** 2)
                alpha = min(alpha, 60)
                rect = pygame.Rect(0, 0, c.width - i * 2, c.height - i * 2)
                rect.center = (cx, cy)
                if rect.width > 0 and rect.height > 0:
                    border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    # Only draw the border, not fill
                    pygame.draw.rect(border_surf, (0, 0, 0, alpha),
                                     border_surf.get_rect(), width=4)
                    vig.blit(border_surf, rect.topleft)
            self._vignette = vig

        surface.blit(self._vignette, (0, 0))

    # ── Main loop ───────────────────────────────────────────
    def run(self):
        """Start the main application loop."""
        self._init_pygame()
        self._init_systems()
        self.running = True

        print(f"\n  ╔══════════════════════════════════════╗")
        print(f"  ║  Waterfall Code — running            ║")
        print(f"  ║  Palette: {self.cfg.palette['name']:<26s} ║")
        print(f"  ║  Resolution: {self.cfg.width}×{self.cfg.height:<18} ║")
        print(f"  ║  Press F for fullscreen, Q to quit   ║")
        print(f"  ╚══════════════════════════════════════╝\n")

        try:
            while self.running:
                self._handle_events()
                self.text.update()
                self._render()
                self.frame += 1
                self.clock.tick(self.cfg.fps)
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()
            sys.exit(0)
