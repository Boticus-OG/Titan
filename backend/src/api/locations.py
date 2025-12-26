"""Locations API endpoints.

CRUD operations for teach point locations with dual coordinate support.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.deck import Location, LocationType

router = APIRouter(prefix="/api/deck/locations", tags=["Locations"])


# ============================================================================
# Request/Response Models
# ============================================================================


class LocationCreate(BaseModel):
    """Request body for creating a location."""

    name: str
    location_type: str  # LocationType value
    x: float
    y: float
    c: float = 0.0
    track_id: int | None = None
    track_distance: float | None = None
    station_id: str | None = None
    metadata: dict = {}


class LocationUpdate(BaseModel):
    """Request body for updating a location."""

    name: str | None = None
    x: float | None = None
    y: float | None = None
    c: float | None = None
    track_id: int | None = None
    track_distance: float | None = None
    station_id: str | None = None
    metadata: dict | None = None


class LocationResponse(BaseModel):
    """Response for a single location."""

    location_id: str
    name: str
    location_type: str
    x: float
    y: float
    c: float
    track_id: int | None
    track_distance: float | None
    station_id: str | None
    metadata: dict


# ============================================================================
# Dependency Injection
# ============================================================================

# These will be set by the main app
_location_manager = None
_deck_storage = None


def set_dependencies(location_manager, deck_storage):
    """Set service dependencies (called from main.py)."""
    global _location_manager, _deck_storage
    _location_manager = location_manager
    _deck_storage = deck_storage


# ============================================================================
# Endpoints
# ============================================================================


@router.get("")
async def list_locations(
    location_type: str | None = None, station_id: str | None = None
) -> list[dict]:
    """List all locations with optional filtering."""
    if _location_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    locations = _location_manager.get_all()

    # Apply filters
    if location_type:
        try:
            type_enum = LocationType(location_type)
            locations = [loc for loc in locations if loc.location_type == type_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid location_type: {location_type}")

    if station_id:
        locations = [loc for loc in locations if loc.station_id == station_id]

    return [loc.to_dict() for loc in locations]


@router.get("/{location_id}")
async def get_location(location_id: str) -> dict:
    """Get a specific location."""
    if _location_manager is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    location = _location_manager.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    return location.to_dict()


@router.post("")
async def create_location(data: LocationCreate) -> dict:
    """Create a new location."""
    if _location_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        location_type = LocationType(data.location_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid location_type: {data.location_type}")

    location = _location_manager.add(
        name=data.name,
        location_type=location_type,
        x=data.x,
        y=data.y,
        c=data.c,
        track_id=data.track_id,
        track_distance=data.track_distance,
        station_id=data.station_id,
        metadata=data.metadata,
    )

    # Persist to storage
    await _deck_storage.save_locations(_location_manager.get_all())

    return location.to_dict()


@router.put("/{location_id}")
async def update_location(location_id: str, data: LocationUpdate) -> dict:
    """Update an existing location."""
    if _location_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    location = _location_manager.update(
        location_id=location_id,
        name=data.name,
        x=data.x,
        y=data.y,
        c=data.c,
        track_id=data.track_id,
        track_distance=data.track_distance,
        station_id=data.station_id,
        metadata=data.metadata,
    )

    if not location:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    # Persist to storage
    await _deck_storage.save_locations(_location_manager.get_all())

    return location.to_dict()


@router.delete("/{location_id}")
async def delete_location(location_id: str) -> dict:
    """Delete a location."""
    if _location_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    if not _location_manager.delete(location_id):
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    # Persist to storage
    await _deck_storage.save_locations(_location_manager.get_all())

    return {"status": "deleted", "location_id": location_id}


@router.post("/{location_id}/teach")
async def teach_location(location_id: str, mover_id: str) -> dict:
    """Teach a location from current mover position.

    Updates the location's coordinates to match the mover's current position.
    """
    if _location_manager is None or _deck_storage is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    location = _location_manager.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    # TODO: Get mover position from mover actor
    # For now, return an error indicating this feature needs mover integration
    raise HTTPException(
        status_code=501, detail="Teach from mover not yet implemented - requires mover integration"
    )
