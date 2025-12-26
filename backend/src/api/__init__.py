"""API endpoints for Titan."""

from .locations import router as locations_router, set_dependencies as set_locations_deps
from .tracks import router as tracks_router, set_dependencies as set_tracks_deps
from .deck_editor import router as deck_editor_router, set_dependencies as set_editor_deps

__all__ = [
    "locations_router",
    "set_locations_deps",
    "tracks_router",
    "set_tracks_deps",
    "deck_editor_router",
    "set_editor_deps",
]
