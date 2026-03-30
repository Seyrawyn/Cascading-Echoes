"""
Text overlay — loads code files, renders them as scrolling text,
and produces a binary mask so the particle system knows where text is.
"""

import os
import math
import pygame
import numpy as np
from config import Config


class TextOverlay:
    """
    Manages the scrolling code text:
      - Loads source files and concatenates them with headers
      - Renders lines with a monospace font
      - Produces a text_mask (numpy array) for particle interaction
      - Supports file navigation (next/prev)
    """

    def __init__(self, config: Config):
        self.cfg = config
        self.scroll_offset: float = 0.0
        self.paused = False

        # Load font
        self.font = self._load_font()

        # Pre-render cache: line_index -> (surface, glow_surface)
        self._render_cache: dict[int, tuple[pygame.Surface, pygame.Surface]] = {}

        # Load code files
        self.file_index = 0
        self.files = self._discover_files()
        self.lines: list[str] = []
        self.file_boundaries: list[tuple[int, str]] = []  # (line_index, filename)
        self._build_line_buffer()

        # The mask surface (grayscale, same size as screen)
        self.mask_surface = pygame.Surface(
            (config.width, config.height), pygame.SRCALPHA
        )
        self.text_mask: np.ndarray = np.zeros(
            (config.height, config.width), dtype=np.uint8
        )

    # ── Font loading ────────────────────────────────────────
    def _load_font(self) -> pygame.font.Font:
        """Try to find a good monospace font."""
        candidates = [
            "DejaVu Sans Mono", "Fira Code", "Source Code Pro",
            "Consolas", "Ubuntu Mono", "Liberation Mono",
            "Courier New", "monospace",
        ]
        for name in candidates:
            path = pygame.font.match_font(name)
            if path:
                try:
                    return pygame.font.Font(path, self.cfg.font_size)
                except Exception:
                    continue
        # Fallback to pygame default
        return pygame.font.SysFont("monospace", self.cfg.font_size)

    # ── File discovery ──────────────────────────────────────
    def _discover_files(self) -> list[str]:
        """Find code files to display."""
        c = self.cfg
        if c.code_files:
            return [f for f in c.code_files if os.path.isfile(f)]

        # Default: display our own source files
        project_dir = os.path.dirname(os.path.abspath(__file__))
        own_files = ["main.py", "config.py", "particles.py",
                     "text_overlay.py", "app.py"]
        result = []
        for fn in own_files:
            fp = os.path.join(project_dir, fn)
            if os.path.isfile(fp):
                result.append(fp)
        return result if result else [__file__]

    # ── Line buffer construction ────────────────────────────
    def _build_line_buffer(self):
        """Load all files into a single list of lines with separators."""
        self.lines = []
        self.file_boundaries = []
        gap = self.cfg.file_gap_lines

        for filepath in self.files:
            filename = os.path.basename(filepath)

            # Add separator header
            if self.cfg.show_filename_header:
                self.file_boundaries.append((len(self.lines), filename))
                header = f"─── {filename} ───"
                self.lines.append("")
                self.lines.append(header)
                self.lines.append("")

            # Read file content
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Replace tabs with spaces for consistent rendering
                content = content.replace("\t", "    ")
                for line in content.splitlines():
                    self.lines.append(line)
            except Exception as e:
                self.lines.append(f"# Error reading {filename}: {e}")

            # Gap between files
            for _ in range(gap):
                self.lines.append("")

        # Add padding at end so text scrolls fully off screen
        visible_lines = self.cfg.height // self.cfg.line_height + 2
        for _ in range(visible_lines):
            self.lines.append("")

        # Clear render cache when lines change
        self._render_cache.clear()

    # ── Navigation ──────────────────────────────────────────
    def next_file(self):
        """Jump scroll position to the next file header."""
        current_line = self.scroll_offset / self.cfg.line_height
        for line_idx, _name in self.file_boundaries:
            if line_idx > current_line + 2:
                self.scroll_offset = line_idx * self.cfg.line_height
                return
        # Wrap to beginning
        self.scroll_offset = 0.0

    def prev_file(self):
        """Jump scroll position to the previous file header."""
        current_line = self.scroll_offset / self.cfg.line_height
        for line_idx, _name in reversed(self.file_boundaries):
            if line_idx < current_line - 2:
                self.scroll_offset = line_idx * self.cfg.line_height
                return
        # Wrap to last file
        if self.file_boundaries:
            self.scroll_offset = self.file_boundaries[-1][0] * self.cfg.line_height

    def restart(self):
        """Reset scroll to top and reload files."""
        self.scroll_offset = 0.0
        self.files = self._discover_files()
        self._build_line_buffer()

    # ── Update ──────────────────────────────────────────────
    def update(self):
        """Advance the scroll position by one frame."""
        if not self.paused:
            self.scroll_offset += self.cfg.scroll_speed

        # Loop when all text has scrolled past
        total_height = len(self.lines) * self.cfg.line_height
        if self.scroll_offset > total_height:
            self.scroll_offset = 0.0

    # ── Rendering ───────────────────────────────────────────
    def _render_line(self, line_idx: int, time: float) -> tuple[pygame.Surface, pygame.Surface]:
        """Render a single line of text, returning (main_surface, glow_surface)."""
        if line_idx in self._render_cache:
            return self._render_cache[line_idx]

        c = self.cfg
        pal = c.palette
        text = self.lines[line_idx] if line_idx < len(self.lines) else ""

        if not text.strip():
            # Empty line — return tiny transparent surfaces
            empty = pygame.Surface((1, 1), pygame.SRCALPHA)
            self._render_cache[line_idx] = (empty, empty)
            return empty, empty

        # Check if this is a file header line
        is_header = text.startswith("───")

        text_color = pal["text"]
        glow_color = pal["glow"]

        # Render main text
        main_surf = self.font.render(text, True, text_color)

        # Render glow (same text, different color, will be blitted with offset)
        glow_surf = self.font.render(text, True, glow_color)

        # Cache it
        self._render_cache[line_idx] = (main_surf, glow_surf)
        return main_surf, glow_surf

    def draw(self, surface: pygame.Surface, time: float):
        """
        Render visible lines onto the surface and update the text_mask.
        Returns the updated text_mask numpy array.
        """
        c = self.cfg
        pal = c.palette
        lh = c.line_height

        # Clear mask
        self.mask_surface.fill((0, 0, 0, 0))

        # Determine visible line range
        first_line = int(self.scroll_offset / lh)
        y_offset = -(self.scroll_offset % lh)
        visible_count = c.height // lh + 2

        for i in range(visible_count):
            line_idx = first_line + i
            if line_idx < 0 or line_idx >= len(self.lines):
                continue

            y = y_offset + i * lh

            # Skip if completely off screen
            if y < -lh or y > c.height + lh:
                continue

            main_surf, glow_surf = self._render_line(line_idx, time)
            if main_surf.get_width() <= 1:
                continue

            x = c.text_margin_left

            # Subtle wave distortion on each line
            wave = math.sin(y * 0.01 + time * 0.03) * 3.0
            draw_x = int(x + wave)

            # Glow layer (slightly offset, lower alpha)
            glow_alpha_surf = glow_surf.copy()
            glow_alpha_surf.set_alpha(c.text_glow_alpha)
            gr = c.text_glow_radius
            surface.blit(glow_alpha_surf, (draw_x - gr, y - gr))
            surface.blit(glow_alpha_surf, (draw_x + gr, y + gr))

            # Main text
            main_alpha_surf = main_surf.copy()
            main_alpha_surf.set_alpha(c.text_alpha)
            surface.blit(main_alpha_surf, (draw_x, y))

            # Draw to mask (white text on black = interaction zones)
            mask_text = self.font.render(
                self.lines[line_idx], True, (255, 255, 255)
            )
            self.mask_surface.blit(mask_text, (draw_x, y))

        # Convert mask surface to numpy array
        # We only need one channel — take the red channel
        mask_pixels = pygame.surfarray.pixels3d(self.mask_surface)
        # surfarray gives (width, height, 3), we need (height, width)
        self.text_mask = np.ascontiguousarray(mask_pixels[:, :, 0].T)

        return self.text_mask
