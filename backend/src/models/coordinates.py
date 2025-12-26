"""Coordinate system utilities.

Handles conversion between different coordinate systems:
- UI coordinates: Top-left origin (Y increases downward)
- PLC coordinates: Bottom-left origin (Y increases upward)

TrackDesigner and PLC use bottom-left origin.
Standard SVG/canvas uses top-left origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class CoordinateOrigin(str, Enum):
    """Coordinate system origin location."""

    TOP_LEFT = "top_left"  # Standard SVG/canvas (Y increases down)
    BOTTOM_LEFT = "bottom_left"  # PLC/TrackDesigner (Y increases up)


@dataclass
class CoordinateSystem:
    """Coordinate system configuration and conversion utilities."""

    origin: CoordinateOrigin = CoordinateOrigin.BOTTOM_LEFT
    deck_height_mm: float = 720.0  # Total deck height for Y-axis flip

    def to_plc(self, x: float, y: float) -> Tuple[float, float]:
        """Convert UI coordinates to PLC coordinates (bottom-left origin).

        If current origin is top-left, flips the Y axis.
        If already bottom-left, returns unchanged.
        """
        if self.origin == CoordinateOrigin.TOP_LEFT:
            return (x, self.deck_height_mm - y)
        return (x, y)

    def from_plc(self, x: float, y: float) -> Tuple[float, float]:
        """Convert PLC coordinates (bottom-left origin) to UI coordinates.

        If current origin is top-left, flips the Y axis.
        If already bottom-left, returns unchanged.
        """
        if self.origin == CoordinateOrigin.TOP_LEFT:
            return (x, self.deck_height_mm - y)
        return (x, y)

    def to_svg(self, x: float, y: float) -> Tuple[float, float]:
        """Convert coordinates to SVG/canvas format (top-left origin).

        If current origin is bottom-left, flips the Y axis.
        If already top-left, returns unchanged.
        """
        if self.origin == CoordinateOrigin.BOTTOM_LEFT:
            return (x, self.deck_height_mm - y)
        return (x, y)

    def from_svg(self, x: float, y: float) -> Tuple[float, float]:
        """Convert SVG/canvas coordinates to internal format.

        If current origin is bottom-left, flips the Y axis.
        If already top-left, returns unchanged.
        """
        if self.origin == CoordinateOrigin.BOTTOM_LEFT:
            return (x, self.deck_height_mm - y)
        return (x, y)


# Default coordinate system (PLC-compatible, bottom-left origin)
default_coords = CoordinateSystem(
    origin=CoordinateOrigin.BOTTOM_LEFT,
    deck_height_mm=720.0,  # 3 rows x 240mm
)


def grid_to_mm(col: int, row: int, tile_size: float = 240.0) -> Tuple[float, float]:
    """Convert grid position to mm coordinates (tile center).

    Args:
        col: Column index (0-based, left to right)
        row: Row index (0-based, bottom to top for PLC origin)
        tile_size: Tile size in mm (default 240)

    Returns:
        (x, y) in mm at tile center
    """
    x = (col * tile_size) + (tile_size / 2)
    y = (row * tile_size) + (tile_size / 2)
    return (x, y)


def mm_to_grid(x: float, y: float, tile_size: float = 240.0) -> Tuple[int, int]:
    """Convert mm coordinates to grid position.

    Args:
        x: X coordinate in mm
        y: Y coordinate in mm
        tile_size: Tile size in mm (default 240)

    Returns:
        (col, row) grid indices
    """
    col = int(x // tile_size)
    row = int(y // tile_size)
    return (col, row)


def snap_to_grid(x: float, y: float, snap_distance: float = 5.0) -> Tuple[float, float]:
    """Snap coordinates to nearest grid point.

    Args:
        x: X coordinate in mm
        y: Y coordinate in mm
        snap_distance: Grid spacing in mm (default 5)

    Returns:
        Snapped (x, y) coordinates
    """
    snapped_x = round(x / snap_distance) * snap_distance
    snapped_y = round(y / snap_distance) * snap_distance
    return (snapped_x, snapped_y)


def snap_to_quadrant(
    x: float, y: float, tile_size: float = 240.0, tolerance: float = 10.0
) -> Tuple[float, float]:
    """Snap coordinates to nearest quadrant point within a tile.

    Quadrant points are at 60mm and 180mm within each tile (from TrackDesigner).

    Args:
        x: X coordinate in mm
        y: Y coordinate in mm
        tile_size: Tile size in mm (default 240)
        tolerance: Snap tolerance in mm (default 10)

    Returns:
        Snapped (x, y) coordinates if within tolerance, otherwise original
    """
    quadrant_offsets = [60.0, 180.0]

    # Find tile
    tile_x = int(x // tile_size) * tile_size
    tile_y = int(y // tile_size) * tile_size

    # Find nearest quadrant point
    best_x, best_y = x, y
    best_dist = float("inf")

    for qx in quadrant_offsets:
        for qy in quadrant_offsets:
            px = tile_x + qx
            py = tile_y + qy
            dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if dist < best_dist and dist <= tolerance:
                best_dist = dist
                best_x, best_y = px, py

    return (best_x, best_y)


def tile_bounds(col: int, row: int, tile_size: float = 240.0) -> Tuple[float, float, float, float]:
    """Get tile bounding box.

    Args:
        col: Column index
        row: Row index
        tile_size: Tile size in mm

    Returns:
        (x_min, y_min, x_max, y_max) in mm
    """
    x_min = col * tile_size
    y_min = row * tile_size
    x_max = x_min + tile_size
    y_max = y_min + tile_size
    return (x_min, y_min, x_max, y_max)
