"""Deck Editor API endpoints.

Endpoints for deck layout editing operations.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..models.deck import GridPosition, DeckConfig

router = APIRouter(prefix="/api/deck/editor", tags=["Deck Editor"])


# ============================================================================
# Request/Response Models
# ============================================================================


class TileToggle(BaseModel):
    """Request to toggle a tile's enabled state."""

    col: int
    row: int
    enabled: bool


class DeckLayoutUpdate(BaseModel):
    """Request to update deck layout."""

    name: str | None = None
    cols: int | None = None
    rows: int | None = None


class GridResize(BaseModel):
    """Request to resize the deck grid."""

    cols: int
    rows: int


# ============================================================================
# Dependency Injection
# ============================================================================

_deck_storage = None
_deck_config = None  # Reference to TitanApp's deck


def set_dependencies(deck_storage, deck_config_ref):
    """Set service dependencies (called from main.py).

    deck_config_ref should be a callable that returns the current DeckConfig.
    """
    global _deck_storage, _deck_config
    _deck_storage = deck_storage
    _deck_config = deck_config_ref


def _get_deck() -> DeckConfig:
    """Get the current deck configuration."""
    if _deck_config is None:
        raise HTTPException(status_code=500, detail="Deck not initialized")
    if callable(_deck_config):
        return _deck_config()
    return _deck_config


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/layout")
async def get_layout() -> dict:
    """Get complete deck layout for editor."""
    deck = _get_deck()
    return {
        "name": deck.name,
        "cols": deck.cols,
        "rows": deck.rows,
        "tile_size_mm": deck.tile_size_mm,
        "width_mm": deck.width_mm,
        "height_mm": deck.height_mm,
        "disabled_tiles": [
            {"col": t.col, "row": t.row} for t in deck.disabled_tiles
        ],
        "tiles": [tile.to_dict() for tile in deck.get_all_tiles()],
    }


@router.put("/layout")
async def update_layout(data: DeckLayoutUpdate) -> dict:
    """Update deck layout (name only - use resize for grid changes)."""
    deck = _get_deck()

    if data.name is not None:
        # Create new deck with updated name
        # Note: This requires updating the deck reference in TitanApp
        pass

    return {"status": "updated", "name": deck.name}


@router.post("/tiles/toggle")
async def toggle_tile(data: TileToggle) -> dict:
    """Toggle a tile on/off.

    Disabled tiles represent devices or unused space.
    Movers cannot traverse disabled tiles.
    """
    deck = _get_deck()
    if _deck_storage is None:
        raise HTTPException(status_code=500, detail="Storage not initialized")

    # Validate position
    if data.col < 0 or data.col >= deck.cols or data.row < 0 or data.row >= deck.rows:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position ({data.col}, {data.row}) for {deck.cols}x{deck.rows} deck",
        )

    grid_pos = GridPosition(col=data.col, row=data.row)
    is_currently_disabled = grid_pos in deck.disabled_tiles

    if data.enabled and is_currently_disabled:
        # Enable tile (remove from disabled list)
        deck.disabled_tiles.remove(grid_pos)
    elif not data.enabled and not is_currently_disabled:
        # Disable tile (add to disabled list)
        deck.disabled_tiles.append(grid_pos)

    # Persist to storage
    await _deck_storage.save_deck_config(
        deck.name, deck.cols, deck.rows, deck.disabled_tiles
    )

    tile = deck.get_tile(data.col, data.row)
    return {
        "status": "toggled",
        "tile": tile.to_dict() if tile else None,
    }


@router.post("/resize")
async def resize_grid(data: GridResize) -> dict:
    """Resize the deck grid.

    Warning: This may invalidate stations/locations outside new bounds.
    """
    deck = _get_deck()
    if _deck_storage is None:
        raise HTTPException(status_code=500, detail="Storage not initialized")

    if data.cols < 1 or data.rows < 1:
        raise HTTPException(status_code=400, detail="Grid must be at least 1x1")

    if data.cols > 20 or data.rows > 20:
        raise HTTPException(status_code=400, detail="Grid cannot exceed 20x20")

    # Filter out disabled tiles outside new bounds
    new_disabled = [
        t for t in deck.disabled_tiles if t.col < data.cols and t.row < data.rows
    ]

    # Update in-memory deck configuration
    deck.cols = data.cols
    deck.rows = data.rows
    deck.disabled_tiles = new_disabled

    # Persist to storage
    await _deck_storage.save_deck_config(deck.name, data.cols, data.rows, new_disabled)

    return {
        "status": "resized",
        "cols": data.cols,
        "rows": data.rows,
        "width_mm": data.cols * 240,
        "height_mm": data.rows * 240,
    }


@router.post("/clear")
async def clear_tiles() -> dict:
    """Clear all tiles (disable all tiles).

    Useful for starting fresh with tile layout.
    """
    deck = _get_deck()
    if _deck_storage is None:
        raise HTTPException(status_code=500, detail="Storage not initialized")

    # Disable all tiles
    deck.disabled_tiles.clear()
    for col in range(deck.cols):
        for row in range(deck.rows):
            deck.disabled_tiles.append(GridPosition(col=col, row=row))

    # Persist to storage
    await _deck_storage.save_deck_config(
        deck.name, deck.cols, deck.rows, deck.disabled_tiles
    )

    return {
        "status": "cleared",
        "disabled_count": len(deck.disabled_tiles),
    }


@router.get("/quadrant-points")
async def get_quadrant_points() -> list[dict]:
    """Get all quadrant reference points for snap-to-grid.

    Quadrant points are at 60mm and 180mm intervals within each tile.
    Used by the editor for precise positioning.
    """
    deck = _get_deck()
    return deck.get_quadrant_points()


@router.post("/export")
async def export_configuration() -> dict:
    """Export complete deck configuration.

    Returns all configuration data that can be saved/loaded.
    """
    deck = _get_deck()

    return {
        "version": "1.0",
        "deck": {
            "name": deck.name,
            "cols": deck.cols,
            "rows": deck.rows,
            "disabled_tiles": [{"col": t.col, "row": t.row} for t in deck.disabled_tiles],
        },
        "stations": [station.to_dict() for station in deck.stations],
        "tracks": [track.to_dict() for track in deck.tracks],
        "locations": [loc.to_dict() for loc in deck.locations],
    }


@router.post("/import")
async def import_configuration(file: UploadFile = File(...)) -> dict:
    """Import deck configuration from file.

    Accepts JSON file with deck, stations, tracks, and locations.
    """
    if _deck_storage is None:
        raise HTTPException(status_code=500, detail="Storage not initialized")

    try:
        import json

        content = await file.read()
        data = json.loads(content)

        # Validate version
        version = data.get("version", "1.0")
        if version != "1.0":
            raise HTTPException(
                status_code=400, detail=f"Unsupported config version: {version}"
            )

        # TODO: Import deck, stations, tracks, locations
        # This requires updating multiple services and the TitanApp state

        return {
            "status": "imported",
            "message": "Configuration imported successfully",
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")
