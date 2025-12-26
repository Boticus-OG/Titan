"""Location manager service.

Manages teach point locations with CRUD operations
and dual coordinate support (cartesian + track-based).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ..models.deck import Location, LocationType

logger = logging.getLogger(__name__)


class LocationManager:
    """Manages teach point locations with dual coordinate support.

    Locations can have both cartesian (x, y, c) and track-based
    (track_id, distance) coordinates. This enables flexible positioning
    for different movement modes.
    """

    def __init__(self):
        self._locations: dict[str, Location] = {}

    def set_locations(self, locations: list[Location]) -> None:
        """Set all locations (used when loading from storage)."""
        self._locations = {loc.location_id: loc for loc in locations}
        logger.info(f"LocationManager: Loaded {len(self._locations)} locations")

    def get_all(self) -> list[Location]:
        """Get all locations."""
        return list(self._locations.values())

    def get(self, location_id: str) -> Location | None:
        """Get a location by ID."""
        return self._locations.get(location_id)

    def get_by_name(self, name: str) -> Location | None:
        """Get a location by name."""
        for loc in self._locations.values():
            if loc.name == name:
                return loc
        return None

    def get_by_type(self, location_type: LocationType) -> list[Location]:
        """Get all locations of a specific type."""
        return [
            loc for loc in self._locations.values() if loc.location_type == location_type
        ]

    def get_by_station(self, station_id: str) -> list[Location]:
        """Get all locations belonging to a station."""
        return [
            loc for loc in self._locations.values() if loc.station_id == station_id
        ]

    def get_queue_points_on_track(self, track_id: int) -> list[Location]:
        """Get all queue point locations on a specific track."""
        return [
            loc
            for loc in self._locations.values()
            if loc.location_type == LocationType.QUEUE and loc.track_id == track_id
        ]

    def get_waypoints_for_station(self, station_id: str) -> dict[str, Location | None]:
        """Get FREE and TRACK waypoint variants for a station.

        Returns dict with 'free' and 'track' keys.
        """
        station_locations = self.get_by_station(station_id)
        result: dict[str, Location | None] = {"free": None, "track": None}

        for loc in station_locations:
            if loc.location_type == LocationType.WAYPOINT:
                name_upper = loc.name.upper()
                if "FREE" in name_upper:
                    result["free"] = loc
                elif "TRACK" in name_upper:
                    result["track"] = loc

        return result

    def add(
        self,
        name: str,
        location_type: LocationType,
        x: float,
        y: float,
        c: float = 0.0,
        track_id: int | None = None,
        track_distance: float | None = None,
        station_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Location:
        """Add a new location."""
        location_id = str(uuid.uuid4())[:8]

        location = Location(
            location_id=location_id,
            name=name,
            location_type=location_type,
            x=x,
            y=y,
            c=c,
            track_id=track_id,
            track_distance=track_distance,
            station_id=station_id,
            metadata=metadata or {},
        )

        self._locations[location_id] = location
        logger.info(f"LocationManager: Added location {location_id} ({name})")
        return location

    def update(
        self,
        location_id: str,
        name: str | None = None,
        x: float | None = None,
        y: float | None = None,
        c: float | None = None,
        track_id: int | None = None,
        track_distance: float | None = None,
        station_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Location | None:
        """Update an existing location."""
        location = self._locations.get(location_id)
        if not location:
            return None

        # Create updated location (dataclass fields are not easily mutable)
        updated = Location(
            location_id=location_id,
            name=name if name is not None else location.name,
            location_type=location.location_type,
            x=x if x is not None else location.x,
            y=y if y is not None else location.y,
            c=c if c is not None else location.c,
            track_id=track_id if track_id is not None else location.track_id,
            track_distance=(
                track_distance if track_distance is not None else location.track_distance
            ),
            station_id=station_id if station_id is not None else location.station_id,
            metadata=metadata if metadata is not None else location.metadata,
        )

        self._locations[location_id] = updated
        logger.info(f"LocationManager: Updated location {location_id}")
        return updated

    def delete(self, location_id: str) -> bool:
        """Delete a location."""
        if location_id in self._locations:
            del self._locations[location_id]
            logger.info(f"LocationManager: Deleted location {location_id}")
            return True
        return False

    def exists(self, location_id: str) -> bool:
        """Check if a location exists."""
        return location_id in self._locations

    def is_queue_point(self, name: str) -> bool:
        """Check if a location name indicates a queue point."""
        return "QUEUE" in name.upper()

    def resolve_cartesian(self, name: str) -> tuple[float, float, float] | None:
        """Resolve a location name to cartesian coordinates (x, y, c)."""
        location = self.get_by_name(name)
        if location:
            return (location.x, location.y, location.c)
        return None

    def resolve_track(self, name: str) -> tuple[int, float] | None:
        """Resolve a location name to track coordinates (track_id, distance)."""
        location = self.get_by_name(name)
        if location and location.has_track_coordinates:
            return (location.track_id, location.track_distance)  # type: ignore
        return None
