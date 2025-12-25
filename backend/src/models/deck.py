"""Deck configuration models.

Defines the physical layout of the XPlanar deck per Constitution Article VIII.

Stator tiles are 240mm x 240mm, arranged in a perfect grid.
Movers can only traverse stator surfaces.
Devices share the same 240mm x 240mm footprint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Constitution Section 8.1: Stator tile size
TILE_SIZE_MM = 240


class DeviceType(str, Enum):
    """Types of devices that can be placed on the deck."""

    PIPETTER = "pipetter"
    DISPENSER = "dispenser"
    WASHER = "washer"
    INCUBATOR = "incubator"
    READER = "reader"
    LIDMATE = "lidmate"
    DECAPPER = "decapper"
    HOTEL = "hotel"
    NEST = "nest"
    BARCODE_READER = "barcode_reader"


@dataclass(frozen=True)
class Position:
    """Absolute position in millimeters.

    Origin (0,0) is top-left of the deck.
    X increases to the right, Y increases downward.
    """

    x: float
    y: float
    c: float = 0.0  # Rotation in degrees

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "c": self.c}

    @classmethod
    def from_grid(cls, grid_x: int, grid_y: int, c: float = 0.0) -> Position:
        """Convert grid coordinates to absolute position (tile center)."""
        return cls(
            x=(grid_x * TILE_SIZE_MM) + (TILE_SIZE_MM / 2),
            y=(grid_y * TILE_SIZE_MM) + (TILE_SIZE_MM / 2),
            c=c,
        )


@dataclass(frozen=True)
class GridPosition:
    """Position as grid tile indices (0-based)."""

    col: int  # X axis (column)
    row: int  # Y axis (row)

    def to_absolute(self) -> Position:
        """Convert to absolute mm position (tile center)."""
        return Position.from_grid(self.col, self.row)

    def to_dict(self) -> dict[str, int]:
        return {"col": self.col, "row": self.row}


@dataclass
class StatorTile:
    """A single XPlanar stator tile (240mm x 240mm).

    Stator tiles form the traversable surface for movers.
    """

    grid_pos: GridPosition
    enabled: bool = True  # Can be disabled for irregular deck shapes

    @property
    def position(self) -> Position:
        """Get center position in mm."""
        return self.grid_pos.to_absolute()

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Get bounding box (x_min, y_min, x_max, y_max) in mm."""
        x = self.grid_pos.col * TILE_SIZE_MM
        y = self.grid_pos.row * TILE_SIZE_MM
        return (x, y, x + TILE_SIZE_MM, y + TILE_SIZE_MM)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grid_pos": self.grid_pos.to_dict(),
            "enabled": self.enabled,
            "position": self.position.to_dict(),
            "bounds": self.bounds,
        }


@dataclass
class Station:
    """A device station on the deck.

    Stations are where plates stop for processing.
    Each station occupies one tile position (240mm x 240mm footprint).
    """

    station_id: str
    name: str
    grid_pos: GridPosition
    device_type: DeviceType
    device_id: str | None = None  # Actual device instance ID

    # Station can have multiple slots (e.g., hotel with multiple positions)
    slots: int = 1
    occupied_slots: int = 0

    # Queue point for plates waiting for this station
    queue_grid_pos: GridPosition | None = None

    @property
    def position(self) -> Position:
        """Get center position in mm."""
        return self.grid_pos.to_absolute()

    @property
    def is_available(self) -> bool:
        """Check if station has available slots."""
        return self.occupied_slots < self.slots

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_id": self.station_id,
            "name": self.name,
            "grid_pos": self.grid_pos.to_dict(),
            "position": self.position.to_dict(),
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "slots": self.slots,
            "occupied_slots": self.occupied_slots,
            "is_available": self.is_available,
            "queue_grid_pos": self.queue_grid_pos.to_dict() if self.queue_grid_pos else None,
        }


@dataclass
class DeckConfig:
    """Complete deck configuration.

    Defines the physical layout of the XPlanar system:
    - Grid dimensions (number of stator tiles)
    - Which tiles are active (for irregular shapes)
    - Station positions and types
    """

    name: str
    cols: int  # Number of tile columns
    rows: int  # Number of tile rows

    # Stator tiles (only need to list disabled ones; all others assumed enabled)
    disabled_tiles: list[GridPosition] = field(default_factory=list)

    # Stations on the deck
    stations: list[Station] = field(default_factory=list)

    @property
    def tile_size_mm(self) -> int:
        return TILE_SIZE_MM

    @property
    def width_mm(self) -> float:
        return self.cols * TILE_SIZE_MM

    @property
    def height_mm(self) -> float:
        return self.rows * TILE_SIZE_MM

    def get_tile(self, col: int, row: int) -> StatorTile | None:
        """Get stator tile at grid position."""
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return None

        grid_pos = GridPosition(col, row)
        enabled = grid_pos not in self.disabled_tiles
        return StatorTile(grid_pos=grid_pos, enabled=enabled)

    def get_all_tiles(self) -> list[StatorTile]:
        """Get all stator tiles."""
        tiles = []
        for row in range(self.rows):
            for col in range(self.cols):
                grid_pos = GridPosition(col, row)
                enabled = grid_pos not in self.disabled_tiles
                tiles.append(StatorTile(grid_pos=grid_pos, enabled=enabled))
        return tiles

    def get_station(self, station_id: str) -> Station | None:
        """Get station by ID."""
        for station in self.stations:
            if station.station_id == station_id:
                return station
        return None

    def get_station_at(self, col: int, row: int) -> Station | None:
        """Get station at grid position."""
        for station in self.stations:
            if station.grid_pos.col == col and station.grid_pos.row == row:
                return station
        return None

    def is_traversable(self, x: float, y: float) -> bool:
        """Check if a position (in mm) is on an enabled stator tile."""
        col = int(x // TILE_SIZE_MM)
        row = int(y // TILE_SIZE_MM)

        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return False

        return GridPosition(col, row) not in self.disabled_tiles

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cols": self.cols,
            "rows": self.rows,
            "tile_size_mm": self.tile_size_mm,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "tiles": [tile.to_dict() for tile in self.get_all_tiles()],
            "stations": [station.to_dict() for station in self.stations],
        }


# Default demo deck configuration
def create_demo_deck() -> DeckConfig:
    """Create a demo deck configuration for testing.

    Layout (4x3 grid = 960mm x 720mm):

    +-------+-------+-------+-------+
    |       | Delid | Pipet |       |  Row 0
    +-------+-------+-------+-------+
    |       |       |       | Disp  |  Row 1
    +-------+-------+-------+-------+
    |       |       | Incub |       |  Row 2
    +-------+-------+-------+-------+
      Col 0   Col 1   Col 2   Col 3
    """
    return DeckConfig(
        name="Demo Deck",
        cols=4,
        rows=3,
        stations=[
            Station(
                station_id="STATION_1",
                name="Delid/Pipette Station",
                grid_pos=GridPosition(col=1, row=0),
                device_type=DeviceType.LIDMATE,
                device_id="lidmate-1",
            ),
            Station(
                station_id="STATION_1",  # Same station, different device
                name="Pipette Station",
                grid_pos=GridPosition(col=2, row=0),
                device_type=DeviceType.PIPETTER,
                device_id="pipetter-1",
            ),
            Station(
                station_id="STATION_2",
                name="Dispense Station",
                grid_pos=GridPosition(col=3, row=1),
                device_type=DeviceType.DISPENSER,
                device_id="dispenser-1",
            ),
            Station(
                station_id="STATION_3",
                name="Incubator",
                grid_pos=GridPosition(col=2, row=2),
                device_type=DeviceType.INCUBATOR,
                device_id="incubator-1",
                slots=4,  # Can hold 4 plates
            ),
        ],
    )
