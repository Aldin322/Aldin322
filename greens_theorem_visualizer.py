"""Interactive Green's theorem visualizer built with pygame.

Launch this script with ``python greens_theorem_visualizer.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import pygame

WIDTH, HEIGHT = 960, 720
BACKGROUND_COLOR = (18, 18, 24)
AXIS_COLOR = (70, 70, 90)
AXIS_HIGHLIGHT = (120, 120, 160)
POLYGON_COLOR = (46, 150, 255, 80)
POLYGON_BORDER = (90, 190, 255)
POINT_COLOR = (255, 230, 120)
POINT_SELECTED = (255, 120, 120)
TEXT_COLOR = (230, 230, 240)
FIELD_COLOR = (120, 120, 220)
FIELD_ARROW_HEAD = (190, 190, 255)
SEGMENT_COLOR = (140, 220, 150)
SEGMENT_ARROW = (90, 180, 110)

SCALE = 80  # pixels per plane unit
ARROW_SCALE = 40
GRID_SPACING = 60
CLOSE_DISTANCE = 18
DRAG_DISTANCE = 18

Vector = Tuple[float, float]
Point = Tuple[float, float]


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


def line_integral(points: Sequence[Vector]) -> float:
    """Midpoint approximation of the line integral of F · dr."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        mid = ((x1 + x2) / 2, (y1 + y2) / 2)
        fx, fy = vector_field(mid)
        total += fx * (x2 - x1) + fy * (y2 - y1)
    return total


def lerp(a: Vector, b: Vector, t: float) -> Vector:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


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


def draw_polygon(surface: pygame.Surface, points: Sequence[Point], closed: bool) -> None:
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
            pygame.draw.line(surface, SEGMENT_COLOR, start, end, 3)
            place = lerp(start, end, 0.85)
            direction = (end[0] - start[0], end[1] - start[1])
            draw_arrow_head(surface, place, direction, SEGMENT_ARROW)
    elif len(points) >= 2:
        pygame.draw.lines(surface, POLYGON_BORDER, False, points, 2)

    for idx, point in enumerate(points):
        color = POINT_SELECTED if idx == 0 and not closed else POINT_COLOR
        pygame.draw.circle(surface, color, point, 6)
        pygame.draw.circle(surface, BACKGROUND_COLOR, point, 2)


def compute_values(points: Sequence[Point], closed: bool) -> Tuple[float, float, float]:
    if len(points) < 3 or not closed:
        return 0.0, 0.0, 0.0
    plane_points = [screen_to_plane(p) for p in points]
    area = polygon_area(plane_points)
    line_value = line_integral(plane_points)
    double_integral = area  # curl(F) = 1 everywhere
    return area, line_value, double_integral


def nearest_point(points: Sequence[Point], target: Point) -> int | None:
    for idx, point in enumerate(points):
        if math.dist(point, target) <= DRAG_DISTANCE:
            return idx
    return None


def render_text(surface: pygame.Surface, font: pygame.font.Font, closed: bool, area: float,
                line_value: float, double_integral: float, points: Sequence[Point]) -> None:
    lines: List[str] = [
        "Green's Theorem Visualizer",
        "Left click: add vertex / drag vertex",
        "Right click: close polygon",
        "R: reset   H: toggle hints   G: toggle vector field",
    ]
    if len(points) >= 3 and not closed:
        lines.append("Close the loop to compute the integrals (click near the first vertex).")
    elif len(points) < 3:
        lines.append("Add at least three vertices to form a region.")

    if closed and len(points) >= 3:
        orientation = "counter-clockwise" if area > 0 else "clockwise"
        lines.extend([
            f"Signed area (double integral of curl): {double_integral:.4f}",
            f"Line integral of F · dr:              {line_value:.4f}",
            f"Orientation: {orientation}  (difference = {line_value - double_integral:+.4e})",
        ])
        lines.append("Drag vertices to deform the region and watch the equality persist!")
    else:
        lines.append("Green's theorem relates the line integral around the closed curve")
        lines.append("to the double integral of the curl inside the region.")

    padding = 12
    y = padding
    for line in lines:
        surface.blit(font.render(line, True, TEXT_COLOR), (padding, y))
        y += font.get_linesize() + 2


@dataclass
class ToggleState:
    show_field: bool = True
    show_hints: bool = True


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Green's Theorem Visualizer")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    points: List[Point] = []
    closed = False
    dragging: int | None = None
    toggles = ToggleState()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    points.clear()
                    closed = False
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_g:
                    toggles.show_field = not toggles.show_field
                elif event.key == pygame.K_h:
                    toggles.show_hints = not toggles.show_hints
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if closed:
                        idx = nearest_point(points, event.pos)
                        if idx is not None:
                            dragging = idx
                    else:
                        if points and math.dist(points[0], event.pos) < CLOSE_DISTANCE and len(points) >= 3:
                            closed = True
                        else:
                            points.append(event.pos)
                elif event.button == 3 and not closed and len(points) >= 3:
                    closed = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = None
            elif event.type == pygame.MOUSEMOTION:
                if dragging is not None:
                    points[dragging] = event.pos

        screen.fill(BACKGROUND_COLOR)
        draw_axes(screen)
        if toggles.show_field:
            draw_vector_field(screen)

        draw_polygon(screen, points, closed)
        area, line_value, double_integral = compute_values(points, closed)
        if toggles.show_hints:
            render_text(screen, font, closed, area, line_value, double_integral, points)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
