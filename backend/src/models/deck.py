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


class LocationType(str, Enum):
    """Types of teach point locations (from xplanar-test LocationManager)."""

    WAYPOINT = "waypoint"  # Station entry/exit points
    DEVICE = "device"  # Actual device work positions
    PIVOT = "pivot"  # Rotation points within stations
    QUEUE = "queue"  # Traffic control checkpoints on tracks
    TRACK_SERVICE = "track_service_location"  # Track maintenance points


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


@dataclass(frozen=True)
class TrackPosition:
    """Position along a track (from xplanar-test).

    Used for locations that are defined by their position on a track
    rather than absolute cartesian coordinates.
    """

    track_id: int  # 1-indexed track ID (matches PLC convention)
    distance: float  # Distance in mm along the track from start

    def to_dict(self) -> dict[str, Any]:
        return {"track_id": self.track_id, "distance": self.distance}


@dataclass
class Track:
    """A track path for mover navigation.

    Tracks are linear paths that movers follow. They are defined in TwinCAT
    and extracted at runtime. Each track has start/end coordinates and
    can have queue points along its length.
    """

    track_id: int  # 1-indexed (matches PLC convention)
    name: str
    start_x: float  # Start point X in mm
    start_y: float  # Start point Y in mm
    end_x: float  # End point X in mm
    end_y: float  # End point Y in mm

    @property
    def length(self) -> float:
        """Calculate track length in mm."""
        import math
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.sqrt(dx * dx + dy * dy)

    def position_at_distance(self, distance: float) -> Position:
        """Get cartesian position at distance along track."""
        if self.length == 0:
            return Position(x=self.start_x, y=self.start_y)

        ratio = min(1.0, max(0.0, distance / self.length))
        x = self.start_x + (self.end_x - self.start_x) * ratio
        y = self.start_y + (self.end_y - self.start_y) * ratio
        return Position(x=x, y=y)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "name": self.name,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "length": self.length,
        }


@dataclass
class Location:
    """A teach point location with dual coordinate support.

    Locations can have both cartesian (x, y, c) and track-based
    (track_id, distance) coordinates. This allows flexible positioning
    for different use cases (free-space movement vs track-following).
    """

    location_id: str
    name: str
    location_type: LocationType

    # Cartesian coordinates
    x: float
    y: float
    c: float = 0.0  # Rotation in degrees

    # Track-based coordinates (optional)
    track_id: int | None = None
    track_distance: float | None = None

    # Parent station association
    station_id: str | None = None

    # Metadata for device type, priority, etc.
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def position(self) -> Position:
        """Get cartesian position."""
        return Position(x=self.x, y=self.y, c=self.c)

    @property
    def track_position(self) -> TrackPosition | None:
        """Get track position if defined."""
        if self.track_id is not None and self.track_distance is not None:
            return TrackPosition(track_id=self.track_id, distance=self.track_distance)
        return None

    @property
    def has_track_coordinates(self) -> bool:
        """Check if location has track-based coordinates."""
        return self.track_id is not None and self.track_distance is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "location_type": self.location_type.value,
            "x": self.x,
            "y": self.y,
            "c": self.c,
            "track_id": self.track_id,
            "track_distance": self.track_distance,
            "station_id": self.station_id,
            "metadata": self.metadata,
        }

    def to_xplanar_format(self) -> dict[str, Any]:
        """Convert to xplanar-test compatible JSON format."""
        return {
            "name": self.name,
            "type": self.location_type.value,
            "coordinates": {
                "cartesian": {"x": self.x, "y": self.y, "c": self.c},
                "track": (
                    {"track_id": self.track_id, "distance": self.track_distance}
                    if self.has_track_coordinates
                    else None
                ),
            },
            "parent": self.station_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_xplanar_format(cls, location_id: str, data: dict[str, Any]) -> Location:
        """Create Location from xplanar-test JSON format."""
        coords = data.get("coordinates", {})
        cartesian = coords.get("cartesian", {})
        track = coords.get("track")

        return cls(
            location_id=location_id,
            name=data.get("name", location_id),
            location_type=LocationType(data.get("type", "device")),
            x=cartesian.get("x", 0.0),
            y=cartesian.get("y", 0.0),
            c=cartesian.get("c", 0.0),
            track_id=track.get("track_id") if track else None,
            track_distance=track.get("distance") if track else None,
            station_id=data.get("parent"),
            metadata=data.get("metadata", {}),
        )


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
    - Tracks for mover navigation
    - Locations (teach points) for waypoints, devices, queues
    """

    name: str
    cols: int  # Number of tile columns
    rows: int  # Number of tile rows

    # Stator tiles (only need to list disabled ones; all others assumed enabled)
    disabled_tiles: list[GridPosition] = field(default_factory=list)

    # Stations on the deck
    stations: list[Station] = field(default_factory=list)

    # Tracks for mover navigation
    tracks: list[Track] = field(default_factory=list)

    # Locations (teach points)
    locations: list[Location] = field(default_factory=list)

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

    def get_track(self, track_id: int) -> Track | None:
        """Get track by ID."""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None

    def get_location(self, location_id: str) -> Location | None:
        """Get location by ID."""
        for location in self.locations:
            if location.location_id == location_id:
                return location
        return None

    def get_locations_by_type(self, location_type: LocationType) -> list[Location]:
        """Get all locations of a specific type."""
        return [loc for loc in self.locations if loc.location_type == location_type]

    def get_locations_by_station(self, station_id: str) -> list[Location]:
        """Get all locations belonging to a station."""
        return [loc for loc in self.locations if loc.station_id == station_id]

    def get_queue_points_on_track(self, track_id: int) -> list[Location]:
        """Get all queue point locations on a specific track."""
        return [
            loc
            for loc in self.locations
            if loc.location_type == LocationType.QUEUE and loc.track_id == track_id
        ]

    def get_quadrant_points(self) -> list[dict[str, Any]]:
        """Get all quadrant reference points for snap-to-grid.

        Quadrant points are at 60mm and 180mm intervals within each tile.
        This matches TrackDesigner's quadrant system.
        """
        quadrant_offsets = [60, 180]
        points = []

        for row in range(self.rows):
            for col in range(self.cols):
                # Skip disabled tiles
                if GridPosition(col, row) in self.disabled_tiles:
                    continue

                tile_x = col * TILE_SIZE_MM
                tile_y = row * TILE_SIZE_MM

                for qx in quadrant_offsets:
                    for qy in quadrant_offsets:
                        points.append(
                            {
                                "tile_col": col,
                                "tile_row": row,
                                "quadrant_x": 0 if qx == 60 else 1,
                                "quadrant_y": 0 if qy == 60 else 1,
                                "absolute_x": tile_x + qx,
                                "absolute_y": tile_y + qy,
                            }
                        )

        return points

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
            "tracks": [track.to_dict() for track in self.tracks],
            "locations": [location.to_dict() for location in self.locations],
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
