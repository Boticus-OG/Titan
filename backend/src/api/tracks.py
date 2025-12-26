"""Tracks API endpoints.

CRUD operations for track definitions.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.deck import Track

router = APIRouter(prefix="/api/deck/tracks", tags=["Tracks"])


# ============================================================================
# Request/Response Models
# ============================================================================


class TrackCreate(BaseModel):
    """Request body for creating a track."""

    name: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    track_id: int | None = None  # Optional, auto-assigned if not provided


class TrackUpdate(BaseModel):
    """Request body for updating a track."""

    name: str | None = None
    start_x: float | None = None
    start_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None


# ============================================================================
# Dependency Injection
# ============================================================================

_track_manager = None
_deck_storage = None
_location_manager = None


def set_dependencies(track_manager, deck_storage, location_manager):
    """Set service dependencies (called from main.py)."""
    global _track_manager, _deck_storage, _location_manager
    _track_manager = track_manager
    _deck_storage = deck_storage
    _location_manager = location_manager


# ============================================================================
# Endpoints
# ============================================================================


@router.get("")
async def list_tracks() -> list[dict]:
    """List all tracks."""
    if _track_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    tracks = _track_manager.get_all()
    return [track.to_dict() for track in tracks]


@router.get("/{track_id}")
async def get_track(track_id: int) -> dict:
    """Get a specific track."""
    if _track_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    track = _track_manager.get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    return track.to_dict()


@router.post("")
async def create_track(data: TrackCreate) -> dict:
    """Create a new track."""
    if _track_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    track = _track_manager.add(
        name=data.name,
        start_x=data.start_x,
        start_y=data.start_y,
        end_x=data.end_x,
        end_y=data.end_y,
        track_id=data.track_id,
    )

    # Persist to storage
    await _deck_storage.save_tracks(_track_manager.get_all())

    return track.to_dict()


@router.put("/{track_id}")
async def update_track(track_id: int, data: TrackUpdate) -> dict:
    """Update an existing track."""
    if _track_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    track = _track_manager.update(
        track_id=track_id,
        name=data.name,
        start_x=data.start_x,
        start_y=data.start_y,
        end_x=data.end_x,
        end_y=data.end_y,
    )

    if not track:
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    # Persist to storage
    await _deck_storage.save_tracks(_track_manager.get_all())

    return track.to_dict()


@router.delete("/{track_id}")
async def delete_track(track_id: int) -> dict:
    """Delete a track."""
    if _track_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    if not _track_manager.delete(track_id):
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    # Persist to storage
    await _deck_storage.save_tracks(_track_manager.get_all())

    return {"status": "deleted", "track_id": track_id}


@router.get("/{track_id}/queue-points")
async def get_queue_points(track_id: int) -> list[dict]:
    """Get all queue point locations on a specific track."""
    if _track_manager is None or _location_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    track = _track_manager.get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    queue_points = _location_manager.get_queue_points_on_track(track_id)
    return [loc.to_dict() for loc in queue_points]


@router.get("/{track_id}/connections")
async def get_track_connections(track_id: int, tolerance: float = 1.0) -> dict:
    """Get tracks connected to this track."""
    if _track_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    track = _track_manager.get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    connected_ids = _track_manager.find_connected_tracks(track_id, tolerance)
    return {
        "track_id": track_id,
        "connected_tracks": connected_ids,
    }


@router.get("/{track_id}/position")
async def get_position_on_track(track_id: int, distance: float) -> dict:
    """Get cartesian position at a distance along a track."""
    if _track_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    position = _track_manager.get_position_on_track(track_id, distance)
    if not position:
        raise HTTPException(status_code=404, detail=f"Track {track_id} not found")

    return {
        "track_id": track_id,
        "distance": distance,
        "position": position.to_dict(),
    }
