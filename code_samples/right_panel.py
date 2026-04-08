"""Right-side visual panel driven by JS sketch assets.

This module reads the JS and CSV assets from the Art2/Art3 folders and
renders complementary visuals on the RIGHT side of the waterfall piece.

Modes (art_mode in Config):
    1 — Art2 algorithms       → cellular / flow / growth variants
    2 — Unending Pressure     → code-as-dataset charts
"""

from __future__ import annotations

import os
import re
import math
import csv
import random
from dataclasses import dataclass
from typing import Optional

import pygame

from palettes import Palette


@dataclass
class Art2Params:
    cell_size: int = 20
    flow_particles: int = 15000

@dataclass
class Art2JCParams:
    target_loops: int = 1
    repulsion_radius: float = 20.0


class RightPanel:
    def __init__(self, width: int, height: int, project_root: Optional[str] = None):
        self.width = width
        self.height = height

        base_dir = project_root or os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, "assets")

        self.art2_path = os.path.join(assets_dir, "Art2_I", "sketch.js")
        self.art2_main_path = os.path.join(assets_dir, "Art2_M", "sketch.js")
        self.art2_jc_diff_path = os.path.join(assets_dir, "Art2_JC", "diffential_growth.js")

        self.art3_code_path = os.path.join(assets_dir, "Art3_I", "sketch.js")
        self.art3_jc_code_path = os.path.join(assets_dir, "Art3_JC", "sketch.js")
        self.art3_stats_path = os.path.join(assets_dir, "Art3_I", "data", "Stats.csv")
        self.art3_titanic_path = os.path.join(assets_dir, "Art3_M", "titanic.csv")

        self.art2_params = Art2Params()
        self.art2_jc_params = Art2JCParams()

        self.code_lines_art3: list[str] = []
        self.code_line_lengths_art3: list[int] = []
        self.code_max_length_art3: int = 1

        self.code_lines_art3_jc: list[str] = []
        self.code_line_lengths_art3_jc: list[int] = []
        self.code_max_length_art3_jc: int = 1

        # Aggregated scalar inspiration values for Art3 datasets
        self.art3_pressure: float = 0.0
        self.art3_survival_rate: float = 0.5

        # Simple per-mode variation counters so pieces shift when you switch
        self._last_mode: Optional[int] = None
        self._art2_variant: int = 0
        self._art3_variant: int = 0

        # Lightweight state for Art2's cellular automaton grid. The
        # resolution will be derived from Art2_I's cellSize once we've
        # loaded its parameters.
        self._art2_grid_w: int = 0
        self._art2_grid_h: int = 0
        self._art2_grid: list[list[int]] = []

        # Local timing for Art2 growth variant so trees can regrow
        # from scratch each time we land on that style.
        self._art2_growth_start_time: Optional[float] = None
        self._art2_current_style: int = 0
        # Number of trees for the Art2 growth style is chosen
        # randomly within a range derived from the JC asset each
        # time we land on that style, then kept stable.
        self._art2_num_trees: Optional[int] = None
        # Track which Art3 style is currently active (0,1,2) so the
        # app can sync the scrolling code overlay with the side art.
        self._art3_current_style: int = 0

        # Short-lived overlay text shown when switching variants or
        # modes: it slides in from the top-right of the panel and
        # then slowly fades out.
        self._overlay_text: Optional[str] = None
        self._overlay_start_frame: Optional[float] = None
        # Slightly larger, bold font so the overlay reads clearly
        # without overpowering the right-hand visuals.
        self._overlay_font = pygame.font.SysFont("DejaVu Sans", 24, bold=True)

        # Palette-driven colors; initialised to reasonable defaults
        # and updated via set_palette from the main scene.
        self._color_gol: tuple[int, int, int] = (60, 200, 140)
        self._color_flow: tuple[int, int, int] = (80, 190, 255)
        self._tree_dark: tuple[int, int, int] = (60, 140, 200)
        self._tree_light: tuple[int, int, int] = (200, 235, 255)
        self._column_struct: tuple[int, int, int] = (200, 235, 245)
        self._column_nonstruct: tuple[int, int, int] = (140, 170, 235)
        self._radial_color: tuple[int, int, int] = (80, 160, 200)
        self._wave_color: tuple[int, int, int] = (90, 130, 210)

        self._load_art2_params()
        self._load_art2_jc_params()
        self._init_art2_grid()
        self._load_art3_code()
        self._load_art3_jc_code()
        self._load_art3_csvs()

    def _ensure_art3_fallback(self) -> None:
        """If Art3 assets are missing, synthesise simple data so graphs render.

        This keeps the three data-driven mini pieces alive even when the
        original JS/CSV assets from the source project aren't present.
        """
        if self.code_line_lengths_art3 or self.code_line_lengths_art3_jc:
            return

        count = 160
        base = []
        for i in range(count):
            wave = math.sin(i * 0.18) * 0.6 + math.sin(i * 0.041 + 1.7) * 0.4
            val = 28 + wave * 18
            base.append(int(max(4, val)))

        self.code_line_lengths_art3_jc = base
        self.code_max_length_art3_jc = max(self.code_line_lengths_art3_jc or [1])

    # ── File helpers ───────────────────────────────────────
    def set_palette(self, palette: Palette) -> None:
        """Update internal colors to match the current waterfall palette."""
        self._color_gol = palette.code_low
        self._color_flow = palette.water_mid
        self._tree_dark = palette.water_dark
        self._tree_light = palette.water_bright
        self._column_struct = palette.code_high
        self._column_nonstruct = palette.code_low
        self._radial_color = palette.water_mid
        self._wave_color = palette.water_mid

    @staticmethod
    def _lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        return (
            int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t),
        )

    # ── File helpers ───────────────────────────────────────
    def _read_text_safe(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    # ── Art2: pull a few parameters from JS  ───────────────
    def _load_art2_params(self) -> None:
        text_algo = self._read_text_safe(self.art2_path)
        text_flow = self._read_text_safe(self.art2_main_path)

        if text_algo:
            m = re.search(r"let\s+cellSize\s*=\s*(\d+)", text_algo)
            if m:
                try:
                    self.art2_params.cell_size = int(m.group(1))
                except ValueError:
                    pass

        # Flow-field density driven by Art2_M's particle count N.
        if text_flow:
            m_n = re.search(r"\bN\s*=\s*(\d+)", text_flow)
            if m_n:
                try:
                    self.art2_params.flow_particles = int(m_n.group(1))
                except ValueError:
                    pass

    # ── Art2 JC: parameters from differential growth  ──────
    def _load_art2_jc_params(self) -> None:
        text = self._read_text_safe(self.art2_jc_diff_path)
        if not text:
            return

        m_loops = re.search(r"const\s+TARGET_LOOPS\s*=\s*([0-9.]+)", text)
        if m_loops:
            try:
                self.art2_jc_params.target_loops = int(float(m_loops.group(1)))
            except ValueError:
                pass

        m_rep = re.search(r"const\s+REPULSION_RADIUS\s*=\s*([0-9.]+)", text)
        if m_rep:
            try:
                self.art2_jc_params.repulsion_radius = float(m_rep.group(1))
            except ValueError:
                pass

    def _init_art2_grid(self) -> None:
        """Initialise the Art2_I-inspired Game-of-Life grid.

        We use Art2_I's cellSize as a guide for how fine the grid
        should be inside the right-hand panel.
        """
        rect = self.panel_rect
        cell = max(4, min(80, self.art2_params.cell_size or 20))

        # Compute grid resolution from panel dimensions and cell size,
        # but keep it within a sane range for performance.
        cols = max(14, min(70, int(rect.width / max(6.0, cell * 0.7))))
        rows = max(10, min(45, int(rect.height / max(6.0, cell * 0.7))))

        self._art2_grid_w = max(4, cols)
        self._art2_grid_h = max(4, rows)
        self._art2_grid = [
            [1 if random.random() < 0.16 else 0 for _ in range(self._art2_grid_w)]
            for _ in range(self._art2_grid_h)
        ]


    # ── Art3: use code as dataset  ─────────────────────────
    def _load_art3_code(self) -> None:
        text = self._read_text_safe(self.art3_code_path)
        if not text:
            return
        self.code_lines_art3 = text.splitlines()
        self.code_line_lengths_art3 = [len(line) for line in self.code_lines_art3]
        self.code_max_length_art3 = max(self.code_line_lengths_art3 or [1])
        if self.code_max_length_art3 == 0:
            self.code_max_length_art3 = 1

    def _load_art3_jc_code(self) -> None:
        text = self._read_text_safe(self.art3_jc_code_path)
        if not text:
            return
        self.code_lines_art3_jc = text.splitlines()
        self.code_line_lengths_art3_jc = [len(line) for line in self.code_lines_art3_jc]
        self.code_max_length_art3_jc = max(self.code_line_lengths_art3_jc or [1])
        if self.code_max_length_art3_jc == 0:
            self.code_max_length_art3_jc = 1

    def _load_art3_csvs(self) -> None:
        """Load aggregated pressure/survival scalars from CSV datasets.

        These values are only used to subtly modulate colors/shapes in Art3,
        not to add extra visible chart layers.
        """

        # Stats from Art3_I/data/Stats.csv
        stats_text = self._read_text_safe(self.art3_stats_path)
        if stats_text:
            try:
                reader = csv.DictReader(stats_text.splitlines())
                sums: dict[str, float] = {}
                count = 0
                for row in reader:
                    count += 1
                    for key in (
                        "anxiety_tension",
                        "academic_overload",
                        "peer_competition",
                    ):
                        if key in row and row[key] != "":
                            try:
                                val = float(row[key])
                            except ValueError:
                                continue
                            sums[key] = sums.get(key, 0.0) + val
                if count > 0 and sums:
                    # Map average pressure in [1,5] → [0,1]
                    avg_vals = [v / count for v in sums.values()]
                    avg_pressure_raw = sum(avg_vals) / len(avg_vals)
                    self.art3_pressure = max(0.0, min(1.0, (avg_pressure_raw - 1.0) / 4.0))
            except Exception:
                self.art3_pressure = 0.0

        # Simple survival rate from Titanic CSV
        titanic_text = self._read_text_safe(self.art3_titanic_path)
        if titanic_text:
            try:
                reader = csv.DictReader(titanic_text.splitlines())
                total = 0
                survived = 0
                for row in reader:
                    total += 1
                    if row.get("Survived") == "1":
                        survived += 1
                if total > 0:
                    self.art3_survival_rate = max(0.0, min(1.0, survived / float(total)))
            except Exception:
                self.art3_survival_rate = 0.5

    # ── Public API ─────────────────────────────────────────
    def draw(self, surface: pygame.Surface, mode: int, time: float = 0.0) -> None:
        # Bump a small variant counter whenever we switch back into a mode
        if mode != self._last_mode:
            self._last_mode = mode
            if mode == 1:
                self._art2_variant += 1
                # New visit into Art2: show an overlay for whichever
                # style this variant maps to.
                style = (self._art2_variant - 1) % 3
                self._start_overlay_for(mode, style, time)
            elif mode == 2:
                self._art3_variant += 1
                style = (self._art3_variant - 1) % 3
                self._start_overlay_for(mode, style, time)

        if mode == 1:
            self._draw_art2(surface, time)
        elif mode == 2:
            self._draw_art3(surface, time)

        # Draw any active overlay text on top of the current panel.
        self._draw_overlay(surface, time)

    # Small helpers so the app can explicitly advance variants
    # without needing to fake mode changes.
    def advance_art2_variant(self, time: float | None = None) -> None:
        self._art2_variant += 1
        if time is not None:
            style = (self._art2_variant - 1) % 3
            self._start_overlay_for(1, style, time)

    def advance_art3_variant(self, time: float | None = None) -> None:
        self._art3_variant += 1
        if time is not None:
            style = (self._art3_variant - 1) % 3
            self._start_overlay_for(2, style, time)

    # ── Common layout helpers ──────────────────────────────
    @property
    def panel_rect(self) -> pygame.Rect:
        # Reserve a band near the right, but pulled further left and
        # with a softer margin so it blends more into the waterfall.
        x = int(self.width * 0.58)
        y = int(self.height * 0.06)
        w = self.width - x - 90
        h = int(self.height * 0.88)
        return pygame.Rect(x, y, w, h)

    def _draw_panel_background(self, surface: pygame.Surface, alpha: int = 160) -> pygame.Surface:
        """Optional soft overlay; currently unused for Art2/Art3.

        Kept for future tweaks, but we don't draw a separate panel
        background anymore so the right visuals sit directly over the
        waterfall instead of inside a contrasting box.
        """
        return surface

    # ── Compact background cycle for main scene ────────────
    def draw_background_grid(
        self,
        surface: pygame.Surface,
        time: float,
        alpha: int = 80,
        width_fraction: float = 0.26,
        height_fraction: float = 0.28,
        cycle_seconds: float = 8.0,
    ) -> None:
        """Draw a single small mini-variant that cycles over time.

        One piece is shown at a time on the right side, switching
        between the six Art2/Art3 styles every few seconds. Alpha
        keeps it clearly in the background.
        """
        if alpha <= 0:
            return

        full = surface.get_rect()
        margin = int(min(full.width, full.height) * 0.02)

        # Single tile positioned near the centre, modest size.
        tile_w = int(full.width * max(0.05, min(0.95, width_fraction)))
        tile_h = int(full.height * max(0.05, min(0.95, height_fraction)))
        tile_w = max(24, tile_w)
        tile_h = max(24, tile_h)

        tile_x = full.centerx - tile_w // 2
        tile_y = full.centery - tile_h // 2

        styles: list[tuple[int, int]] = [
            (1, 0),  # Art2: Game of Life
            (1, 1),  # Art2: Flow fields
            (1, 2),  # Art2: Growth / trees
            (2, 0),  # Art3: column chart
            (2, 1),  # Art3: radial
            (2, 2),  # Art3: wave band
        ]

        # "time" is in seconds; use cycle_seconds per style.
        dur = cycle_seconds if cycle_seconds and cycle_seconds > 0.05 else 8.0
        index = int(max(0.0, time) // dur) % len(styles)
        mode, style = styles[index]

        tile_surface = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        tile_rect = pygame.Rect(0, 0, tile_w, tile_h)

        if mode == 1:
            self._draw_art2(tile_surface, time, rect=tile_rect, override_style=style)
        else:
            self._draw_art3(tile_surface, time, rect=tile_rect, override_style=style)

        tile_surface.set_alpha(alpha)
        surface.blit(tile_surface, (tile_x, tile_y))

    # ── Mode 2: algorithmic / recursive tree  ──────────────
    def _draw_art2(
        self,
        surface: pygame.Surface,
        time: float,
        rect: Optional[pygame.Rect] = None,
        override_style: Optional[int] = None,
    ) -> None:
        rect = rect or self.panel_rect
        # Choose which Art2 algorithm to show based on how many times
        # we've entered mode 2, similar to Art3's three styles.
        style = override_style if override_style is not None else (self._art2_variant - 1) % 3

        # Track when we enter/leave the growth style so we can
        # restart its growth animation each time.
        if style != self._art2_current_style:
            self._art2_current_style = style
            if style == 2:
                self._art2_growth_start_time = time
                # Force a fresh tree-count choice whenever we
                # newly enter the growth variant.
                self._art2_num_trees = None
            else:
                self._art2_growth_start_time = None

        if style == 0:
            self._draw_art2_gol(surface, rect, time)
        elif style == 1:
            self._draw_art2_flow(surface, rect, time)
        else:
            self._draw_art2_growth(surface, rect, time)

    # Top band: simple Game-of-Life-style grid echoing Art2_I
    def _step_art2_grid(self) -> None:
        w, h = self._art2_grid_w, self._art2_grid_h
        old = self._art2_grid
        new = [[0] * w for _ in range(h)]

        for y in range(h):
            for x in range(w):
                alive = old[y][x]
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= nx < w and 0 <= ny < h:
                            cnt += old[ny][nx]

                if alive:
                    new[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    new[y][x] = 1 if cnt == 3 else 0

                # A bit of random noise so the pattern never freezes fully
                if random.random() < 0.002:
                    new[y][x] = 1

        self._art2_grid = new

    def _draw_art2_gol(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        # Step the grid continuously for a faster, more lively pattern
        self._step_art2_grid()

        cell_w = rect.width / self._art2_grid_w
        cell_h = rect.height / self._art2_grid_h
        for y in range(self._art2_grid_h):
            for x in range(self._art2_grid_w):
                if self._art2_grid[y][x]:
                    rx = rect.left + x * cell_w
                    ry = rect.top + y * cell_h
                    r = pygame.Rect(int(rx), int(ry), int(cell_w) + 1, int(cell_h) + 1)
                    pygame.draw.rect(surface, self._color_gol, r)

    # Middle band: flowing vector field echoing Art2_M
    def _draw_art2_flow(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        cols = 14
        rows = 6
        base_len = rect.height * 0.22

        # Use particle count as a proxy for field density
        density = max(0.4, min(1.6, math.log10(self.art2_params.flow_particles + 10) / 5))
        scale = base_len * density

        for j in range(rows):
            for i in range(cols):
                u = (i + 0.5) / cols
                v = (j + 0.5) / rows
                x = rect.left + u * rect.width
                y = rect.top + v * rect.height

                # Simple pseudo-flow based on sines of position and time
                a = math.sin((u * 5.0 + time * 0.05))
                b = math.cos((v * 7.0 - time * 0.06))
                angle = (a + b) * math.pi * 0.35

                dx = math.cos(angle) * scale
                dy = math.sin(angle) * scale

                x2 = x + dx
                y2 = y + dy

                pygame.draw.line(surface, self._color_flow, (int(x), int(y)), (int(x2), int(y2)), 2)

    # Bottom band: recursive tree / growth echoing Art2_JC
    def _draw_art2_growth(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        # Multiple trees growing from the bottom edge
        base_y = rect.bottom - 6

        sway = math.sin(time * 0.09) * 8.0

        depth_base = 4
        loops = float(self.art2_jc_params.target_loops or 1)

        # Extra recursion depth is driven purely by TARGET_LOOPS so
        # the JC sketch is the only influence here.
        depth_extra = max(0, min(4, int(round(loops))))
        loop_factor = max(0.7, min(1.8, loops / 2.5))

        max_depth = int((depth_base + depth_extra) * loop_factor)

        rep = float(self.art2_jc_params.repulsion_radius or 20.0)
        rep_factor = max(0.7, min(1.6, rep / 20.0))

        # Overall growth strength, softly clamped so trees don't
        # explode in size for extreme parameter combinations.
        loops_norm = max(0.6, min(1.7, loops / 2.0))
        strength = (loops_norm + rep_factor) * 0.5
        strength = max(0.5, min(1.3, strength))
        root_length = rect.height * 0.4 * strength

        spread = 18 + (self._art2_variant % 5) * 4

        # Animate growth over time using a local start time so that
        # each time we land on this style it regrows from scratch.
        start_t = self._art2_growth_start_time if self._art2_growth_start_time is not None else time
        elapsed = max(0.0, time - start_t)
        # Grow much faster so the grove reaches full complexity
        # within just a few seconds.
        growth_phase = min(1.0, elapsed * 0.35)
        effective_depth = max(1, int(max_depth * growth_phase))

        # Number of trees: randomly chosen within a range derived
        # from TARGET_LOOPS and REPULSION_RADIUS so the grove feels
        # different each time we land on this style, but still
        # clearly shaped by the asset parameters.
        if self._art2_num_trees is None:
            loops = float(self.art2_jc_params.target_loops or 3)
            rep = float(self.art2_jc_params.repulsion_radius or 20.0)

            # Base tree count scales with loops, softly clamped and
            # biased a bit upward so even small loop counts don't
            # collapse the range to a single value.
            base_trees = 3 + loops * 2.0
            base_trees = max(4, min(12, int(round(base_trees))))

            # Repulsion radius nudges density a bit.
            rep_factor = max(0.7, min(1.5, rep / 22.0))
            mean_trees = max(4.0, min(14.0, base_trees * rep_factor))

            # Build a range around the mean and pick a random
            # integer within it. Ensure we always have at least a
            # couple of possible values so it doesn't get stuck.
            center = int(round(mean_trees))
            half_span = max(2, int(round(mean_trees * 0.35)))
            min_t = max(3, center - half_span)
            max_t = min(16, center + half_span)
            if max_t <= min_t:
                max_t = min_t + 2
            self._art2_num_trees = random.randint(min_t, max_t)

        num_trees = self._art2_num_trees

        for i in range(num_trees):
            t = (i + 0.5) / num_trees
            base_x = rect.left + t * rect.width

            # Small per-tree variation in length and angle; keep length stable
            # so trees don't visually shrink, only sway.
            angle_offset = math.sin(time * 0.08 + i * 1.3) * 6.0
            length_scale = 0.85 + 0.15 * math.sin(i * 0.7)
            this_length = root_length * length_scale

            self._draw_branch(
                surface,
                base_x,
                base_y,
                -90 + sway + angle_offset,
                this_length,
                effective_depth,
                spread,
            )

    def _draw_branch(self, surface: pygame.Surface, x: float, y: float,
                     angle_deg: float, length: float, depth: int, spread: float) -> None:
        if depth <= 0 or length < 6:
            return

        angle_rad = math.radians(angle_deg)
        x2 = x + math.cos(angle_rad) * length
        y2 = y + math.sin(angle_rad) * length

        # Color and thickness vary with depth, interpolated between
        # darker and lighter tree tones from the current palette.
        t_depth = max(0.0, min(1.0, depth / 6.0))
        color = self._lerp_color(self._tree_light, self._tree_dark, t_depth)
        thickness = max(1, int(3 * (1.0 - t_depth)))
        pygame.draw.line(surface, color, (int(x), int(y)), (int(x2), int(y2)), thickness)

        # Slightly shorter segments so we can afford a bit more
        # branching without the trees exploding off-screen.
        next_len = length * 0.7

        # Main split: classic left/right branches.
        self._draw_branch(surface, x2, y2, angle_deg - spread, next_len, depth - 1, spread)
        self._draw_branch(surface, x2, y2, angle_deg + spread, next_len, depth - 1, spread)

        # Extra side shoot for richness. We only add this when there
        # is still enough depth/length left so complexity stays under
        # control but the silhouette feels more lush.
        if depth > 2 and length > 8:
            side_len = length * 0.55
            # Alternate the offset direction with depth so the
            # additional branches weave slightly instead of all
            # leaning to one side.
            sign = -1 if depth % 2 else 1
            side_angle = angle_deg + sign * spread * 0.18
            self._draw_branch(surface, x2, y2, side_angle, side_len, depth - 2, spread * 0.9)

    # ── Mode 3: code-as-dataset, three diagram styles  ────
    def _draw_art3(
        self,
        surface: pygame.Surface,
        time: float,
        rect: Optional[pygame.Rect] = None,
        override_style: Optional[int] = None,
    ) -> None:
        rect = rect or self.panel_rect

        # Choose diagram style based on how many times we've entered mode 3.
        # Subtract 1 so the *first* visit to C shows the column chart (style 0).
        style = override_style if override_style is not None else (self._art3_variant - 1) % 3
        # Expose current style so the app can keep the scrolling
        # code overlay in sync with whichever Art3 variant is active.
        self._art3_current_style = style
        if style == 0:
            self._draw_art3_columns(surface, rect, time)
        elif style == 1:
            self._draw_art3_radial(surface, rect, time)
        else:
            self._draw_art3_wave(surface, rect, time)

    # ── Overlay text helpers ──────────────────────────────
    def _start_overlay_for(self, mode: int, style: int, time: float) -> None:
        """Start a short-lived overlay label for the given variant.

        mode: 1 = Art2, 2 = Art3
        style: 0,1,2 within that mode
        """
        labels = {
            (1, 0): "Game of Life",
            (1, 1): "Flow Fields",
            (1, 2): "Trees and Differential growth",
            (2, 0): "Data!",
            (2, 1): "Data?",
            (2, 2): "Data",
        }

        text = labels.get((mode, style))
        if not text:
            return

        self._overlay_text = text
        self._overlay_start_frame = time

    def _draw_overlay(self, surface: pygame.Surface, time: float) -> None:
        if not self._overlay_text or self._overlay_start_frame is None:
            return

        rect = self.panel_rect
        elapsed = float(time - self._overlay_start_frame)
        if elapsed < 0:
            return

        # Durations in frames (time is the global frame counter).
        slide_in = 40.0   # frames to slide in from top-right
        hold = 40.0       # frames fully visible
        fade = 140.0      # frames to fade out
        total = slide_in + hold + fade

        if elapsed > total:
            # Overlay lifetime over — clear state.
            self._overlay_text = None
            self._overlay_start_frame = None
            return

        # Render text once to measure it.
        text_surf = self._overlay_font.render(self._overlay_text, True, (230, 235, 245))
        tw, th = text_surf.get_width(), text_surf.get_height()

        margin_x = 16
        margin_y = 12

        # Final position: near the top-left inside the panel.
        dest_x = rect.left + margin_x
        dest_y = rect.top + margin_y

        # Start position: off-screen to the left, same vertical
        # position as the final spot so it only slides horizontally.
        start_x = rect.left - tw * 1.5
        start_y = dest_y

        if elapsed < slide_in:
            t = elapsed / slide_in
            # Slide purely horizontally from left → right, keeping
            # Y fixed so the label doesn't move up/down.
            x = start_x + (dest_x - start_x) * t
            y = dest_y
            # Fade in while sliding.
            alpha = int(230 * max(0.0, min(1.0, t)))
        elif elapsed < slide_in + hold:
            x = dest_x
            y = dest_y
            alpha = 230
        else:
            x = dest_x
            y = dest_y
            t = (elapsed - slide_in - hold) / fade
            alpha = int(230 * max(0.0, 1.0 - t))

        overlay = text_surf.copy()
        overlay.set_alpha(alpha)
        surface.blit(overlay, (int(x), int(y)))

    def _draw_art3_columns(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        """Column chart, mainly driven by Art3_I code + Stats.

        If Art3_I couldn't be read for some reason, we gracefully fall back
        to the JC code lengths so the diagram never goes completely blank.
        """
        self._ensure_art3_fallback()
        if not self.code_line_lengths_art3 and not self.code_line_lengths_art3_jc:
            return

        top = rect.top
        bottom = rect.bottom
        left = rect.left
        width = rect.width
        height = rect.height

        # Prefer Art3_I lengths, but fall back to JC if needed
        if self.code_line_lengths_art3:
            lengths = self.code_line_lengths_art3
            lines_ref = self.code_lines_art3
            max_len = max(self.code_max_length_art3, 1)
            label_source = "art3_I: column chart"
        else:
            lengths = self.code_line_lengths_art3_jc
            lines_ref = self.code_lines_art3_jc
            max_len = max(self.code_max_length_art3_jc, 1)
            label_source = "art3_JC: column chart"

        # Fewer, thicker bars so the chart reads clearly
        max_bars = max(1, width // 8)
        n = len(lengths)
        step = max(1, n // max_bars)
        bar_count = (n + step - 1) // step
        bar_width = max(1, int(width / max(1, bar_count)))

        for i in range(0, n, step):
            idx = i // step
            length_val = lengths[i]
            norm = length_val / float(max_len)
            bar_h = max(3, int(norm * height * 0.8))
            x = left + idx * bar_width
            y = bottom - bar_h

            line_text = lines_ref[i] if i < len(lines_ref) else ""
            is_structural = any(token in line_text for token in ("class ", "function ", "let ", "const ", "=>"))

            # Color uses pressure to warm/cool the bars, but keep high contrast
            p = self.art3_pressure
            if is_structural:
                base = self._column_struct
            else:
                base = self._column_nonstruct
            r_c = base[0] + int(30 * p)
            g_c = base[1] - int(25 * p)
            b_c = base[2] - int(15 * p)

            color = (
                max(0, min(255, r_c)),
                max(0, min(255, g_c)),
                max(0, min(255, b_c)),
            )

            # Faster breathing animation for bar heights
            phase = time * 0.18 + idx * 0.35
            wobble = 0.85 + 0.12 * math.sin(phase)
            animated_h = max(2, int(bar_h * wobble))
            animated_y = bottom - animated_h

            pygame.draw.rect(surface, color, pygame.Rect(x, animated_y, bar_width - 1, animated_h))

    def _draw_art3_radial(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        """Radial bar chart, mixing Art3 code and Titanic survival."""
        self._ensure_art3_fallback()
        # Use combined code lengths so we have enough segments
        values: list[int] = []
        values.extend(self.code_line_lengths_art3)
        values.extend(self.code_line_lengths_art3_jc)
        if not values:
            return

        max_len = max(max(values), 1)

        cx = rect.centerx
        cy = rect.centery
        radius_min = min(rect.width, rect.height) * (0.16 + 0.18 * self.art3_survival_rate)
        radius_max = min(rect.width, rect.height) * 0.46

        n = len(values)
        max_segments = 80
        step = max(1, n // max_segments)

        # Slight twist based on pressure
        p = self.art3_pressure

        for i in range(0, n, step):
            idx = i // step
            v = values[i] / float(max_len)

            base_angle = 2 * math.pi * idx / (n // step + 1)
            # Faster global rotation plus slight pressure twist
            angle = base_angle + time * 0.01 + p * 0.6

            # Bar length also breathes faster over time so bars
            # themselves move in and out, not only the ring rotating.
            phase = time * 0.14 + idx * 0.4
            wobble = 0.85 + 0.15 * math.sin(phase)
            r0 = radius_min
            r1 = radius_min + v * (radius_max - radius_min) * wobble

            x0 = cx + math.cos(angle) * r0
            y0 = cy + math.sin(angle) * r0
            x1 = cx + math.cos(angle) * r1
            y1 = cy + math.sin(angle) * r1

            # Color derived from the palette, lightly modulated by
            # survival/pressure rather than using fixed hues.
            base = self._radial_color
            s = self.art3_survival_rate
            r_c = int(base[0] * (0.8 + 0.4 * s))
            g_c = int(base[1] * (0.8 + 0.4 * s))
            b_c = int(base[2] * (0.9 - 0.3 * p))
            color = (
                max(0, min(255, r_c)),
                max(0, min(255, g_c)),
                max(0, min(255, b_c)),
            )

            pygame.draw.line(surface, color, (int(x0), int(y0)), (int(x1), int(y1)), 2)


    def _draw_art3_wave(self, surface: pygame.Surface, rect: pygame.Rect, time: float) -> None:
        """Wavy band, mainly using Art3_JC code lengths."""
        self._ensure_art3_fallback()
        if not self.code_line_lengths_art3_jc:
            return

        left = rect.left
        right = rect.right
        top = rect.top
        height = rect.height

        lengths = self.code_line_lengths_art3_jc
        max_len = max(self.code_max_length_art3_jc, 1)

        n = len(lengths)
        max_points = max(20, rect.width // 6)
        step = max(1, n // max_points)

        points_top = []
        points_bottom = []

        for i in range(0, n, step):
            idx = i // step
            t = idx / max(1, (n // step))
            x = left + t * (right - left)
            norm = lengths[i] / float(max_len)
            wave = math.sin((t + time * 0.01) * 6 * math.pi) * 0.12
            y_center = top + height * (0.5 + wave * (0.3 + 0.4 * self.art3_pressure))
            band_h = height * (0.18 + 0.12 * self.art3_survival_rate)
            y_top = y_center - norm * band_h
            y_bottom = y_center + norm * band_h
            points_top.append((int(x), int(y_top)))
            points_bottom.append((int(x), int(y_bottom)))

        if len(points_top) < 2:
            return

        polygon = points_top + points_bottom[::-1]

        # Color based on the current palette's water tone, keeping
        # it softly in the same family as the waterfall.
        base = self._wave_color
        color = (base[0], base[1], base[2], 200)

        wave_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(wave_surface, color, [(x - rect.left, y - rect.top) for x, y in polygon])
        surface.blit(wave_surface, (rect.left, rect.top))
