"""Track manager service.

Manages track definitions for mover navigation paths.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from ..models.deck import Track, Position

logger = logging.getLogger(__name__)


class TrackManager:
    """Manages track definitions and provides path utilities.

    Tracks are linear paths that movers follow. Each track has
    start/end coordinates and can have queue points along its length.
    """

    def __init__(self):
        self._tracks: dict[int, Track] = {}
        self._next_id: int = 1

    def set_tracks(self, tracks: list[Track]) -> None:
        """Set all tracks (used when loading from storage)."""
        self._tracks = {track.track_id: track for track in tracks}
        if tracks:
            self._next_id = max(t.track_id for t in tracks) + 1
        logger.info(f"TrackManager: Loaded {len(self._tracks)} tracks")

    def get_all(self) -> list[Track]:
        """Get all tracks."""
        return list(self._tracks.values())

    def get(self, track_id: int) -> Track | None:
        """Get a track by ID."""
        return self._tracks.get(track_id)

    def get_by_name(self, name: str) -> Track | None:
        """Get a track by name."""
        for track in self._tracks.values():
            if track.name == name:
                return track
        return None

    def add(
        self,
        name: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        track_id: int | None = None,
    ) -> Track:
        """Add a new track."""
        if track_id is None:
            track_id = self._next_id
            self._next_id += 1
        elif track_id >= self._next_id:
            self._next_id = track_id + 1

        track = Track(
            track_id=track_id,
            name=name,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )

        self._tracks[track_id] = track
        logger.info(f"TrackManager: Added track {track_id} ({name})")
        return track

    def update(
        self,
        track_id: int,
        name: str | None = None,
        start_x: float | None = None,
        start_y: float | None = None,
        end_x: float | None = None,
        end_y: float | None = None,
    ) -> Track | None:
        """Update an existing track."""
        track = self._tracks.get(track_id)
        if not track:
            return None

        updated = Track(
            track_id=track_id,
            name=name if name is not None else track.name,
            start_x=start_x if start_x is not None else track.start_x,
            start_y=start_y if start_y is not None else track.start_y,
            end_x=end_x if end_x is not None else track.end_x,
            end_y=end_y if end_y is not None else track.end_y,
        )

        self._tracks[track_id] = updated
        logger.info(f"TrackManager: Updated track {track_id}")
        return updated

    def delete(self, track_id: int) -> bool:
        """Delete a track."""
        if track_id in self._tracks:
            del self._tracks[track_id]
            logger.info(f"TrackManager: Deleted track {track_id}")
            return True
        return False

    def get_position_on_track(self, track_id: int, distance: float) -> Position | None:
        """Get cartesian position at distance along a track."""
        track = self._tracks.get(track_id)
        if not track:
            return None
        return track.position_at_distance(distance)

    def find_nearest_track_point(
        self, x: float, y: float
    ) -> tuple[int, float, float] | None:
        """Find the nearest point on any track.

        Returns (track_id, distance_along_track, distance_to_track) or None.
        """
        if not self._tracks:
            return None

        best_result: tuple[int, float, float] | None = None
        best_distance = float("inf")

        for track in self._tracks.values():
            distance_along, perpendicular_dist = self._point_to_line_distance(
                x, y, track.start_x, track.start_y, track.end_x, track.end_y
            )

            if perpendicular_dist < best_distance:
                best_distance = perpendicular_dist
                best_result = (track.track_id, distance_along, perpendicular_dist)

        return best_result

    def find_connected_tracks(self, track_id: int, tolerance: float = 1.0) -> list[int]:
        """Find tracks that connect to the given track (endpoints within tolerance)."""
        track = self._tracks.get(track_id)
        if not track:
            return []

        connected = []
        for other in self._tracks.values():
            if other.track_id == track_id:
                continue

            # Check if endpoints match within tolerance
            for my_point in [(track.start_x, track.start_y), (track.end_x, track.end_y)]:
                for other_point in [
                    (other.start_x, other.start_y),
                    (other.end_x, other.end_y),
                ]:
                    dist = math.sqrt(
                        (my_point[0] - other_point[0]) ** 2
                        + (my_point[1] - other_point[1]) ** 2
                    )
                    if dist <= tolerance:
                        connected.append(other.track_id)
                        break
                else:
                    continue
                break

        return connected

    def _point_to_line_distance(
        self,
        px: float,
        py: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> tuple[float, float]:
        """Calculate distance from point to line segment.

        Returns (distance_along_line, perpendicular_distance).
        """
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq == 0:
            # Line segment is actually a point
            dist = math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
            return (0.0, dist)

        # Calculate projection onto line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance from point to closest point
        dist = math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

        # Distance along line segment
        length = math.sqrt(length_sq)
        distance_along = t * length

        return (distance_along, dist)
