"""Interactive Green's theorem visualizer built with pygame.

Launch this script with ``python greens_theorem_visualizer.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import pygame

WIDTH, HEIGHT = 960, 720
BACKGROUND_COLOR = (18, 18, 24)
AXIS_COLOR = (70, 70, 90)
AXIS_HIGHLIGHT = (120, 120, 160)
POLYGON_COLOR = (46, 150, 255, 70)
POLYGON_BORDER = (90, 190, 255)
POINT_COLOR = (255, 230, 120)
POINT_SELECTED = (255, 120, 120)
TEXT_COLOR = (230, 230, 240)
TEXT_ACCENT = (180, 240, 200)
FIELD_COLOR = (120, 120, 220)
FIELD_ARROW_HEAD = (190, 190, 255)
SEGMENT_COLOR = (140, 220, 150)
SEGMENT_ARROW = (90, 180, 110)
SEGMENT_HIGHLIGHT = (255, 200, 120)
SEGMENT_HIGHLIGHT_ARROW = (255, 160, 80)
EDGE_VECTOR_COLOR = (255, 120, 120)
EDGE_VECTOR_HEAD = (255, 190, 140)
EDGE_PROGRESS_COLOR = (255, 240, 180)
EDGE_PROGRESS_HEAD = (255, 220, 140)
TILE_COLOR_BASE = (80, 200, 180, 90)
TILE_COLOR_ALT = (60, 170, 150, 120)
TILE_COLOR_PROGRESS = (120, 240, 210, 160)
PANEL_COLOR = (15, 15, 24, 230)
PANEL_BORDER = (110, 110, 150)

SCALE = 80  # pixels per plane unit
ARROW_SCALE = 40
GRID_SPACING = 60
TILE_SPACING = 42
TILE_SIZE = TILE_SPACING - 6
CLOSE_DISTANCE = 18
DRAG_DISTANCE = 18

Vector = Tuple[float, float]
Point = Tuple[float, float]


@dataclass
class EdgeDetail:
    """Diagnostic information for a single polygon edge."""

    midpoint: Vector
    delta: Vector
    field: Vector
    contribution: float


@dataclass
class IntegralSnapshot:
    """Full set of quantities used to visualise Green's theorem."""

    area: float
    line_value: float
    double_integral: float
    details: List[EdgeDetail]
    cumulative: List[float]
    tile_centers: List[Point]
    tile_area: float

    @property
    def approximate_area(self) -> float:
        return self.tile_area * len(self.tile_centers)


@dataclass
class ToggleState:
    show_field: bool = True
    show_hints: bool = True
    show_tiles: bool = True


@dataclass
class SnapshotCache:
    snapshot: Optional[IntegralSnapshot] = None
    dirty: bool = True

    def invalidate(self) -> None:
        self.dirty = True


@dataclass
class EdgeAnimator:
    time: float = 0.0
    dwell: float = 1.1  # seconds spent on each edge

    def reset(self) -> None:
        self.time = 0.0

    def step(self, dt: float, count: int) -> Tuple[Optional[int], int, float, float]:
        """Advance the animation clock.

        Returns the highlighted edge index, the number of completed edges,
        the eased progress along the current edge (0–1), and the global
        traversal fraction across all edges.
        """

        if count <= 0:
            self.reset()
            return None, 0, 0.0, 0.0

        total_duration = self.dwell * count
        self.time = (self.time + dt) % total_duration
        raw = self.time / self.dwell
        index = int(raw)
        index = min(index, count - 1)
        linear_progress = raw - index
        eased_progress = ease_in_out_sine(linear_progress)
        active = index + 1
        global_fraction = (index + eased_progress) / max(count, 1)
        return index, active, eased_progress, global_fraction


@dataclass
class FontBundle:
    regular: pygame.font.Font
    small: pygame.font.Font
    large: pygame.font.Font


def screen_to_plane(point: Point) -> Vector:
    """Convert a screen point to plane coordinates."""
    x, y = point
    return ((x - WIDTH / 2) / SCALE, (HEIGHT / 2 - y) / SCALE)


def plane_to_screen(point: Vector) -> Point:
    """Convert a plane point to screen coordinates."""
    x, y = point
    return (int(WIDTH / 2 + x * SCALE), int(HEIGHT / 2 - y * SCALE))


def vector_field(point: Vector) -> Vector:
    """Simple vector field whose curl is constant and equal to 1.

    F(x, y) = (-y/2, x/2)
    curl(F) = dQ/dx - dP/dy = 1, so the double integral equals the area.
    """
    x, y = point
    return (-0.5 * y, 0.5 * x)


def polygon_area(points: Sequence[Vector]) -> float:
    """Signed area using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def line_integral(points: Sequence[Vector]) -> Tuple[float, List[EdgeDetail]]:
    """Midpoint approximation of the line integral of F · dr with diagnostics."""
    if len(points) < 2:
        return 0.0, []

    total = 0.0
    details: List[EdgeDetail] = []
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        delta = (x2 - x1, y2 - y1)
        mid = ((x1 + x2) / 2, (y1 + y2) / 2)
        fx, fy = vector_field(mid)
        contribution = fx * delta[0] + fy * delta[1]
        total += contribution
        details.append(EdgeDetail(mid, delta, (fx, fy), contribution))

    return total, details


def lerp(a: Vector, b: Vector, t: float) -> Vector:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ease_in_out_sine(t: float) -> float:
    """Smooth easing to keep the pacing gentle and intuitive."""
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def draw_axes(surface: pygame.Surface) -> None:
    pygame.draw.line(surface, AXIS_COLOR, (0, HEIGHT // 2), (WIDTH, HEIGHT // 2), 2)
    pygame.draw.line(surface, AXIS_COLOR, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

    for offset in range(GRID_SPACING, WIDTH // 2, GRID_SPACING):
        pygame.draw.line(surface, (40, 40, 55), (WIDTH // 2 + offset, 0), (WIDTH // 2 + offset, HEIGHT), 1)
        pygame.draw.line(surface, (40, 40, 55), (WIDTH // 2 - offset, 0), (WIDTH // 2 - offset, HEIGHT), 1)
    for offset in range(GRID_SPACING, HEIGHT // 2, GRID_SPACING):
        pygame.draw.line(surface, (40, 40, 55), (0, HEIGHT // 2 + offset), (WIDTH, HEIGHT // 2 + offset), 1)
        pygame.draw.line(surface, (40, 40, 55), (0, HEIGHT // 2 - offset), (WIDTH, HEIGHT // 2 - offset), 1)

    pygame.draw.circle(surface, AXIS_HIGHLIGHT, (WIDTH // 2, HEIGHT // 2), 4)


def draw_vector_field(surface: pygame.Surface) -> None:
    for sx in range(GRID_SPACING // 2, WIDTH, GRID_SPACING):
        for sy in range(GRID_SPACING // 2, HEIGHT, GRID_SPACING):
            plane_point = screen_to_plane((sx, sy))
            vx, vy = vector_field(plane_point)
            dx, dy = vx * ARROW_SCALE, -vy * ARROW_SCALE
            end = (sx + dx, sy + dy)
            pygame.draw.line(surface, FIELD_COLOR, (sx, sy), end, 2)
            draw_arrow_head(surface, end, (dx, dy), FIELD_ARROW_HEAD)


def draw_arrow_head(surface: pygame.Surface, tip: Point, direction: Vector, color: Tuple[int, int, int]) -> None:
    length = math.hypot(*direction)
    if length == 0:
        return
    ux, uy = direction[0] / length, direction[1] / length
    left = (tip[0] - ux * 8 + uy * 4, tip[1] - uy * 8 - ux * 4)
    right = (tip[0] - ux * 8 - uy * 4, tip[1] - uy * 8 + ux * 4)
    pygame.draw.polygon(surface, color, [tip, left, right])


def draw_edge_progress(
    surface: pygame.Surface,
    start: Point,
    end: Point,
    progress: float,
) -> None:
    if progress <= 0:
        return
    progress = max(0.0, min(1.0, progress))
    sx, sy = start
    ex, ey = end
    px = sx + (ex - sx) * progress
    py = sy + (ey - sy) * progress
    pygame.draw.line(surface, EDGE_PROGRESS_COLOR, start, (px, py), 6)
    direction = (ex - sx, ey - sy)
    tip = (px, py)
    draw_arrow_head(surface, tip, direction, EDGE_PROGRESS_HEAD)
    pygame.draw.circle(surface, EDGE_PROGRESS_HEAD, (int(px), int(py)), 8)


def draw_polygon(
    surface: pygame.Surface,
    points: Sequence[Point],
    closed: bool,
    highlight_edge: Optional[int] = None,
    edge_progress: float = 0.0,
) -> None:
    if len(points) >= 3 and closed:
        polygon_points = [tuple(map(int, p)) for p in points]
        gfxdraw = getattr(pygame, "gfxdraw", None)
        if gfxdraw:
            gfxdraw.filled_polygon(surface, polygon_points, POLYGON_COLOR)
            gfxdraw.aapolygon(surface, polygon_points, POLYGON_BORDER)
        else:
            polygon_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(polygon_surface, POLYGON_COLOR, polygon_points)
            surface.blit(polygon_surface, (0, 0))
            pygame.draw.polygon(surface, POLYGON_BORDER, polygon_points, 2)

        for i, start in enumerate(points):
            end = points[(i + 1) % len(points)]
            color = SEGMENT_HIGHLIGHT if i == highlight_edge else SEGMENT_COLOR
            arrow_color = SEGMENT_HIGHLIGHT_ARROW if i == highlight_edge else SEGMENT_ARROW
            width = 5 if i == highlight_edge else 3
            pygame.draw.line(surface, color, start, end, width)
            place = lerp(start, end, 0.85)
            direction = (end[0] - start[0], end[1] - start[1])
            draw_arrow_head(surface, place, direction, arrow_color)
            if i == highlight_edge:
                draw_edge_progress(surface, start, end, edge_progress)
    elif len(points) >= 2:
        pygame.draw.lines(surface, POLYGON_BORDER, False, points, 2)

    for idx, point in enumerate(points):
        color = POINT_SELECTED if idx == 0 and not closed else POINT_COLOR
        pygame.draw.circle(surface, color, point, 6)
        pygame.draw.circle(surface, BACKGROUND_COLOR, point, 2)


def draw_area_tiles(
    surface: pygame.Surface, tile_centers: Sequence[Point], fill_ratio: float
) -> None:
    if not tile_centers:
        return
    tile_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    total_tiles = len(tile_centers)
    clamped = max(0.0, min(1.0, fill_ratio))
    eased = ease_in_out_sine(clamped)
    fill_value = eased * total_tiles
    filled = int(fill_value)
    partial = fill_value - filled
    for idx, (sx, sy) in enumerate(tile_centers):
        rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        rect.center = (sx, sy)
        base_color = TILE_COLOR_BASE if idx % 2 == 0 else TILE_COLOR_ALT
        color = base_color
        if idx < filled:
            color = TILE_COLOR_PROGRESS
        elif idx == filled and partial > 0:
            alpha = int(TILE_COLOR_PROGRESS[3] * partial)
            color = TILE_COLOR_PROGRESS[:3] + (alpha,)
        pygame.draw.rect(tile_surface, color, rect, border_radius=6)
    surface.blit(tile_surface, (0, 0))


def draw_edge_vector(surface: pygame.Surface, detail: EdgeDetail, pulse: float) -> None:
    mid_screen = plane_to_screen(detail.midpoint)
    vx, vy = detail.field
    pulse = max(0.0, min(1.0, pulse))
    scale = SCALE * (0.6 + 0.25 * math.sin(math.pi * pulse))
    end = (mid_screen[0] + vx * scale, mid_screen[1] - vy * scale)
    pygame.draw.line(surface, EDGE_VECTOR_COLOR, mid_screen, end, 4)
    draw_arrow_head(surface, end, (vx * scale, -vy * scale), EDGE_VECTOR_HEAD)
    pygame.draw.circle(surface, EDGE_VECTOR_COLOR, mid_screen, 6)


def draw_orientation_label(surface: pygame.Surface, font: pygame.font.Font, points: Sequence[Point], area: float) -> None:
    if not points:
        return
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    text = "CCW (+)" if area >= 0 else "CW (−)"
    color = (140, 220, 150) if area >= 0 else (255, 140, 140)
    label = font.render(text, True, color)
    surface.blit(label, (cx - label.get_width() / 2, cy - label.get_height() / 2))


def render_story_caption(
    surface: pygame.Surface,
    fonts: FontBundle,
    closed: bool,
    points: Sequence[Point],
    snapshot: Optional[IntegralSnapshot],
    highlight_index: Optional[int],
    edge_progress: float,
    line_fraction: float,
) -> None:
    caption_surface = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
    y = 20
    pulse_target: Optional[Point] = None
    pulse_radius = 0

    def center_text(text: str, font: pygame.font.Font, color: Tuple[int, int, int]) -> None:
        nonlocal y
        rendered = font.render(text, True, color)
        caption_surface.blit(
            rendered, ((WIDTH - rendered.get_width()) / 2, y)
        )
        y += font.get_linesize() + 6

    if not closed:
        if len(points) < 2:
            center_text("Sketch a boundary to trap some area.", fonts.large, TEXT_ACCENT)
        elif len(points) == 2:
            center_text("Add one more vertex, then close the loop.", fonts.large, TEXT_ACCENT)
        else:
            center_text("Click the first point (or right click) to seal the curve.", fonts.large, TEXT_ACCENT)
    elif snapshot is None:
        center_text("Position the vertices to avoid self-intersections.", fonts.large, TEXT_ACCENT)
    else:
        line_percent = int(line_fraction * 100)
        if highlight_index is None or highlight_index >= len(snapshot.details):
            center_text("Full circulation measured! Tiles now mirror the area integral.", fonts.large, TEXT_ACCENT)
        else:
            detail = snapshot.details[highlight_index]
            orientation_text = "counter-clockwise" if snapshot.area >= 0 else "clockwise"
            center_text(
                f"Walking edge {highlight_index + 1} {orientation_text}: F(mid) · Δr builds circulation…",
                fonts.large,
                TEXT_ACCENT,
            )
            center_text(
                f"Progress: {line_percent}% of ∬ curl(F) dA matched by ∮ F · dr",
                fonts.regular,
                (200, 220, 255),
            )

            mid_screen = plane_to_screen(detail.midpoint)
            pulse = 12 + 8 * math.sin(edge_progress * math.pi)
            pulse_target = mid_screen
            pulse_radius = int(pulse)

    surface.blit(caption_surface, (0, 0))
    if pulse_target:
        pygame.draw.circle(surface, EDGE_PROGRESS_HEAD, pulse_target, pulse_radius, 2)


def nearest_point(points: Sequence[Point], target: Point) -> Optional[int]:
    for idx, point in enumerate(points):
        if math.dist(point, target) <= DRAG_DISTANCE:
            return idx
    return None


def generate_tile_centers(points: Sequence[Point]) -> List[Point]:
    mask_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(mask_surface, (255, 255, 255, 255), points)
    mask = pygame.mask.from_surface(mask_surface)
    centers: List[Point] = []
    for sx in range(TILE_SPACING // 2, WIDTH, TILE_SPACING):
        for sy in range(TILE_SPACING // 2, HEIGHT, TILE_SPACING):
            if mask.get_at((sx, sy)):
                centers.append((sx, sy))
    return centers


def compute_snapshot(points: Sequence[Point]) -> Optional[IntegralSnapshot]:
    if len(points) < 3:
        return None
    plane_points = [screen_to_plane(p) for p in points]
    area = polygon_area(plane_points)
    line_value, details = line_integral(plane_points)
    double_integral = area  # curl(F) = 1 everywhere

    cumulative: List[float] = []
    running = 0.0
    for detail in details:
        running += detail.contribution
        cumulative.append(running)

    tile_centers = generate_tile_centers(points)
    tile_area = (TILE_SPACING / SCALE) ** 2

    return IntegralSnapshot(area, line_value, double_integral, details, cumulative, tile_centers, tile_area)


def normalized_circulation(
    snapshot: Optional[IntegralSnapshot], highlight_index: Optional[int], edge_progress: float
) -> float:
    if snapshot is None or not snapshot.details:
        return 0.0
    total = snapshot.double_integral if snapshot.double_integral != 0 else snapshot.line_value
    if total == 0:
        return 0.0
    if highlight_index is None or highlight_index >= len(snapshot.details):
        return 1.0
    completed = snapshot.cumulative[highlight_index - 1] if highlight_index > 0 else 0.0
    contribution = snapshot.details[highlight_index].contribution * max(0.0, min(1.0, edge_progress))
    partial = completed + contribution
    return max(0.0, min(1.0, abs(partial) / max(abs(total), 1e-6)))

def render_overlay(
    surface: pygame.Surface,
    fonts: FontBundle,
    toggles: ToggleState,
    closed: bool,
    points: Sequence[Point],
    snapshot: Optional[IntegralSnapshot],
    highlight_index: Optional[int],
    active_edges: int,
    line_fraction: float,
) -> None:
    overlay_width = 430
    panel = pygame.Surface((overlay_width, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(panel, PANEL_COLOR, panel.get_rect(), border_radius=18)

    y = 20

    def write(text: str, font: pygame.font.Font = fonts.regular, color: Tuple[int, int, int] = TEXT_COLOR, spacing: int = 6) -> None:
        nonlocal y
        panel.blit(font.render(text, True, color), (24, y))
        y += font.get_linesize() + spacing

    write("Green's Theorem Visualizer", fonts.large, TEXT_ACCENT, spacing=10)
    write("Controls:", fonts.small, TEXT_ACCENT, spacing=2)
    write("  LMB add / drag vertices", fonts.small)
    write("  Close loop: right click or click start", fonts.small)
    write("  R reset   G field   H overlay   T tiles", fonts.small, spacing=12)

    if not closed or snapshot is None:
        if len(points) < 3:
            write("Sketch a closed loop to enclose a region.", fonts.regular)
            write("Add ≥3 vertices, then click near the first one to seal it.", fonts.small)
        else:
            write("Seal the loop to compare the integrals.", fonts.regular)
        surface.blit(panel, (0, 0))
        return

    orientation = "counter-clockwise" if snapshot.area >= 0 else "clockwise"
    sign_text = "positive" if snapshot.area >= 0 else "negative"
    write(f"Orientation: {orientation} ({sign_text})", fonts.small, TEXT_ACCENT, spacing=12)

    write("Equality spotlight", fonts.regular, TEXT_ACCENT, spacing=2)
    write(f"∮₍C₎ F · dr = {snapshot.line_value:+.4f}", fonts.regular)
    write(f"⊕ ∬₍R₎ curl(F) dA = {snapshot.double_integral:+.4f}", fonts.regular)
    difference = snapshot.line_value - snapshot.double_integral
    write(f"Difference = {difference:+.4e}", fonts.small, (200, 200, 220), spacing=12)

    bar_width = overlay_width - 80
    bar_x = 40
    bar_y = y
    scale = max(abs(snapshot.line_value), abs(snapshot.double_integral), 1.0)
    line_len = int(bar_width * abs(snapshot.line_value) / scale)
    area_len = int(bar_width * abs(snapshot.double_integral) / scale)
    pygame.draw.rect(panel, (35, 50, 35), pygame.Rect(bar_x, bar_y, bar_width, 32), border_radius=8)
    pygame.draw.rect(panel, (80, 200, 160), pygame.Rect(bar_x, bar_y + 4, line_len, 10), border_radius=4)
    pygame.draw.rect(panel, (120, 150, 240), pygame.Rect(bar_x, bar_y + 18, area_len, 10), border_radius=4)
    panel.blit(fonts.small.render("Line integral", True, (40, 40, 40)), (bar_x + 6, bar_y + 2))
    panel.blit(fonts.small.render("Area / curl integral", True, (40, 40, 40)), (bar_x + 6, bar_y + 16))
    y += 48

    progress_width = bar_width
    progress_rect = pygame.Rect(bar_x, y, progress_width, 16)
    pygame.draw.rect(panel, (40, 60, 40), progress_rect, border_radius=6)
    fill = int(progress_width * max(0.0, min(1.0, line_fraction)))
    pygame.draw.rect(
        panel,
        (150, 240, 200),
        pygame.Rect(bar_x, y, fill, 16),
        border_radius=6,
    )
    panel.blit(
        fonts.small.render(
            f"Walking progress: {int(line_fraction * 100):3d}%", True, (30, 30, 30)
        ),
        (bar_x + 6, y - 2),
    )
    y += 32

    write("Why they agree (drag to feel it):", fonts.regular, TEXT_ACCENT, spacing=8)
    write("1. Walk C edge by edge.", fonts.small)
    write("   Δr is the highlighted segment.", fonts.small, spacing=2)

    if highlight_index is not None and snapshot.details:
        detail = snapshot.details[highlight_index]
        running = snapshot.cumulative[highlight_index]
        fx, fy = detail.field
        dx, dy = detail.delta
        write(
            f"   Edge {highlight_index + 1}: F(mid) = ({fx:+.2f}, {fy:+.2f})", fonts.small
        )
        write(f"   Δr = ({dx:+.2f}, {dy:+.2f}) → dot = {detail.contribution:+.4f}", fonts.small)
        write(f"   Running circulation: {running:+.4f}", fonts.small, spacing=8)

    max_lines = min(len(snapshot.details), 5)
    for idx in range(max_lines):
        detail = snapshot.details[idx]
        symbol = "▶" if idx == highlight_index else ("✓" if idx < active_edges - 1 else "•")
        panel.blit(
            fonts.small.render(
                f"   {symbol} Edge {idx + 1}: ({detail.field[0]:+.2f},{detail.field[1]:+.2f}) · ({detail.delta[0]:+.2f},{detail.delta[1]:+.2f}) = {detail.contribution:+.4f}",
                True,
                (210, 210, 230),
            ),
            (24, y),
        )
        y += fonts.small.get_linesize() + 2
    if len(snapshot.details) > max_lines:
        write("   … more edges continue the same accumulation", fonts.small)

    write("2. Sum all dot products → circulation around C.", fonts.small, spacing=10)
    write("3. Fill R with tiles; curl(F)=1 so each contributes ΔA.", fonts.small)
    write(
        f"   {len(snapshot.tile_centers)} tiles × {snapshot.tile_area:.3f} ≈ {snapshot.approximate_area:.4f}",
        fonts.small,
    )
    write(
        "   Their total matches the green circulation sum!",
        fonts.small,
        TEXT_ACCENT,
        spacing=12,
    )

    if not toggles.show_tiles:
        write("(Press T to re-enable the area tiles.)", fonts.small, (200, 160, 160))

    surface.blit(panel, (0, 0))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Green's Theorem Visualizer")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    fonts = FontBundle(
        regular=pygame.font.SysFont("consolas", 18),
        small=pygame.font.SysFont("consolas", 16),
        large=pygame.font.SysFont("consolas", 24, bold=True),
    )

    points: List[Point] = []
    closed = False
    dragging: Optional[int] = None
    toggles = ToggleState()
    cache = SnapshotCache()
    animator = EdgeAnimator()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    points.clear()
                    closed = False
                    cache.invalidate()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_g:
                    toggles.show_field = not toggles.show_field
                elif event.key == pygame.K_h:
                    toggles.show_hints = not toggles.show_hints
                elif event.key == pygame.K_t:
                    toggles.show_tiles = not toggles.show_tiles
                elif event.key == pygame.K_SPACE and closed:
                    animator.reset()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if closed:
                        idx = nearest_point(points, event.pos)
                        if idx is not None:
                            dragging = idx
                    else:
                        if points and math.dist(points[0], event.pos) < CLOSE_DISTANCE and len(points) >= 3:
                            closed = True
                            cache.invalidate()
                        else:
                            points.append(event.pos)
                            cache.invalidate()
                elif event.button == 3 and not closed and len(points) >= 3:
                    closed = True
                    cache.invalidate()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = None
            elif event.type == pygame.MOUSEMOTION:
                if dragging is not None:
                    points[dragging] = event.pos
                    cache.invalidate()

        if not closed and cache.snapshot is not None:
            cache.snapshot = None
            cache.dirty = True

        snapshot: Optional[IntegralSnapshot] = None
        if closed and len(points) >= 3:
            if cache.dirty or cache.snapshot is None:
                cache.snapshot = compute_snapshot(points)
                cache.dirty = False
            snapshot = cache.snapshot
        else:
            snapshot = None

        if not snapshot:
            animator.reset()
            highlight_index: Optional[int] = None
            active_edges = 0
            edge_progress = 0.0
        else:
            highlight_index, active_edges, edge_progress, _ = animator.step(
                dt, len(snapshot.details)
            )

        screen.fill(BACKGROUND_COLOR)
        draw_axes(screen)
        if toggles.show_field:
            draw_vector_field(screen)

        if snapshot:
            line_fraction = normalized_circulation(snapshot, highlight_index, edge_progress)
        else:
            line_fraction = 0.0

        if snapshot and toggles.show_tiles:
            draw_area_tiles(screen, snapshot.tile_centers, line_fraction)

        draw_polygon(screen, points, closed, highlight_index, edge_progress if snapshot else 0.0)

        if snapshot:
            draw_orientation_label(screen, fonts.small, points, snapshot.area)
            if highlight_index is not None and 0 <= highlight_index < len(snapshot.details):
                draw_edge_vector(screen, snapshot.details[highlight_index], edge_progress)

        render_story_caption(screen, fonts, closed, points, snapshot, highlight_index, edge_progress, line_fraction)

        if toggles.show_hints:
            render_overlay(
                screen,
                fonts,
                toggles,
                closed,
                points,
                snapshot,
                highlight_index,
                active_edges,
                line_fraction,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
