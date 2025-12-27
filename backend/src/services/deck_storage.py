"""Deck configuration storage service.

Handles persistence of deck configuration to JSON files
in a format compatible with xplanar-test project.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..models.deck import (
    DeckConfig,
    GridPosition,
    Location,
    LocationType,
    Station,
    Track,
    DeviceType,
    Device,
    DeviceClass,
    Footprint,
    Overhang,
    Nest,
)

logger = logging.getLogger(__name__)


class DeckStorage:
    """Handles persistence of deck configuration files.

    Files are stored in xplanar-test compatible JSON format:
    - saved_locations.json: All teach point locations
    - station_config.json: Station definitions
    - tracks.json: Track definitions
    - deck_config.json: Base deck layout (grid, disabled tiles)
    """

    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def locations_file(self) -> Path:
        return self.data_dir / "saved_locations.json"

    @property
    def stations_file(self) -> Path:
        return self.data_dir / "station_config.json"

    @property
    def tracks_file(self) -> Path:
        return self.data_dir / "tracks.json"

    @property
    def deck_file(self) -> Path:
        return self.data_dir / "deck_config.json"

    @property
    def devices_file(self) -> Path:
        return self.data_dir / "devices.json"

    # =========================================================================
    # Devices
    # =========================================================================

    async def load_devices(self) -> list[Device]:
        """Load devices from devices.json."""
        if not self.devices_file.exists():
            return []

        try:
            with open(self.devices_file) as f:
                data = json.load(f)

            devices = []
            for dev_data in data.get("devices", []):
                devices.append(Device.from_dict(dev_data))

            logger.info(f"Loaded {len(devices)} devices from {self.devices_file}")
            return devices

        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            return []

    async def save_devices(self, devices: list[Device]) -> None:
        """Save devices to devices.json."""
        data = {"devices": [dev.to_dict() for dev in devices]}

        try:
            with open(self.devices_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(devices)} devices to {self.devices_file}")
        except Exception as e:
            logger.error(f"Failed to save devices: {e}")
            raise

    # =========================================================================
    # Locations
    # =========================================================================

    async def load_locations(self) -> list[Location]:
        """Load locations from saved_locations.json."""
        if not self.locations_file.exists():
            return []

        try:
            with open(self.locations_file) as f:
                data = json.load(f)

            locations = []
            # Handle xplanar-test format: {"locations": [...]}
            raw_locations = data.get("locations", [])
            if isinstance(raw_locations, list):
                for i, loc_data in enumerate(raw_locations):
                    location_id = loc_data.get("location_id", f"loc_{i}")
                    locations.append(Location.from_xplanar_format(location_id, loc_data))
            # Handle dict format: {"location_id": {...}}
            elif isinstance(raw_locations, dict):
                for location_id, loc_data in raw_locations.items():
                    locations.append(Location.from_xplanar_format(location_id, loc_data))

            logger.info(f"Loaded {len(locations)} locations from {self.locations_file}")
            return locations

        except Exception as e:
            logger.error(f"Failed to load locations: {e}")
            return []

    async def save_locations(self, locations: list[Location]) -> None:
        """Save locations to saved_locations.json in xplanar-test format."""
        data = {
            "locations": [loc.to_xplanar_format() for loc in locations]
        }

        try:
            with open(self.locations_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(locations)} locations to {self.locations_file}")
        except Exception as e:
            logger.error(f"Failed to save locations: {e}")
            raise

    # =========================================================================
    # Tracks
    # =========================================================================

    async def load_tracks(self) -> list[Track]:
        """Load tracks from tracks.json."""
        if not self.tracks_file.exists():
            return []

        try:
            with open(self.tracks_file) as f:
                data = json.load(f)

            tracks = []
            for track_data in data.get("tracks", []):
                tracks.append(
                    Track(
                        track_id=track_data["track_id"],
                        name=track_data.get("name", f"Track {track_data['track_id']}"),
                        start_x=track_data["start_x"],
                        start_y=track_data["start_y"],
                        end_x=track_data["end_x"],
                        end_y=track_data["end_y"],
                    )
                )

            logger.info(f"Loaded {len(tracks)} tracks from {self.tracks_file}")
            return tracks

        except Exception as e:
            logger.error(f"Failed to load tracks: {e}")
            return []

    async def save_tracks(self, tracks: list[Track]) -> None:
        """Save tracks to tracks.json."""
        data = {"tracks": [track.to_dict() for track in tracks]}

        try:
            with open(self.tracks_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(tracks)} tracks to {self.tracks_file}")
        except Exception as e:
            logger.error(f"Failed to save tracks: {e}")
            raise

    # =========================================================================
    # Stations (xplanar-test format)
    # =========================================================================

    async def load_stations(self) -> list[Station]:
        """Load stations from station_config.json (xplanar-test format)."""
        if not self.stations_file.exists():
            return []

        try:
            with open(self.stations_file) as f:
                data = json.load(f)

            stations = []
            for station_id, station_data in data.get("stations", {}).items():
                # Extract boundary to grid position (approximate)
                boundary = station_data.get("boundary", {})
                min_x = boundary.get("min_x", 0)
                min_y = boundary.get("min_y", 0)

                # Convert mm to grid position
                col = int(min_x // 240)
                row = int(min_y // 240)

                # Get first device type
                devices = station_data.get("devices", {})
                device_type = DeviceType.PIPETTER  # Default
                device_id = None
                if devices:
                    first_device_id = list(devices.keys())[0]
                    device_id = first_device_id
                    device_info = devices[first_device_id]
                    # Map device type string to enum
                    type_str = device_info.get("type", "").lower().replace(" ", "_")
                    try:
                        device_type = DeviceType(type_str)
                    except ValueError:
                        device_type = DeviceType.PIPETTER

                stations.append(
                    Station(
                        station_id=station_id,
                        name=station_id,
                        grid_pos=GridPosition(col=col, row=row),
                        device_type=device_type,
                        device_id=device_id,
                    )
                )

            logger.info(f"Loaded {len(stations)} stations from {self.stations_file}")
            return stations

        except Exception as e:
            logger.error(f"Failed to load stations: {e}")
            return []

    async def save_stations(self, stations: list[Station]) -> None:
        """Save stations to station_config.json in xplanar-test format."""
        data = {"stations": {}}

        for station in stations:
            boundary = {
                "min_x": station.grid_pos.col * 240,
                "max_x": (station.grid_pos.col + 1) * 240,
                "min_y": station.grid_pos.row * 240,
                "max_y": (station.grid_pos.row + 1) * 240,
            }

            station_data = {
                "devices": {},
                "shared_resources": {
                    "waypoint": {},
                    "pivot": {},
                    "queues": {},
                },
                "boundary": boundary,
            }

            if station.device_id:
                station_data["devices"][station.device_id] = {
                    "type": station.device_type.value.upper().replace("_", " ")
                }

            data["stations"][station.station_id] = station_data

        try:
            with open(self.stations_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(stations)} stations to {self.stations_file}")
        except Exception as e:
            logger.error(f"Failed to save stations: {e}")
            raise

    # =========================================================================
    # Deck Configuration
    # =========================================================================

    async def load_deck_config(self) -> dict[str, Any]:
        """Load base deck configuration (grid dimensions, disabled tiles)."""
        if not self.deck_file.exists():
            return {"name": "Default Deck", "cols": 4, "rows": 3, "disabled_tiles": []}

        try:
            with open(self.deck_file) as f:
                data = json.load(f)
            logger.info(f"Loaded deck config from {self.deck_file}")
            return data
        except Exception as e:
            logger.error(f"Failed to load deck config: {e}")
            return {"name": "Default Deck", "cols": 4, "rows": 3, "disabled_tiles": []}

    async def save_deck_config(
        self, name: str, cols: int, rows: int, disabled_tiles: list[GridPosition]
    ) -> None:
        """Save base deck configuration."""
        data = {
            "name": name,
            "cols": cols,
            "rows": rows,
            "disabled_tiles": [
                {"col": tile.col, "row": tile.row} for tile in disabled_tiles
            ],
        }

        try:
            with open(self.deck_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved deck config to {self.deck_file}")
        except Exception as e:
            logger.error(f"Failed to save deck config: {e}")
            raise

    # =========================================================================
    # Full Load/Save
    # =========================================================================

    async def load_full_config(self) -> DeckConfig:
        """Load complete deck configuration from all files."""
        deck_data = await self.load_deck_config()
        locations = await self.load_locations()
        tracks = await self.load_tracks()
        stations = await self.load_stations()
        devices = await self.load_devices()

        # Convert disabled tiles from dicts to GridPosition
        disabled_tiles = [
            GridPosition(col=t["col"], row=t["row"])
            for t in deck_data.get("disabled_tiles", [])
        ]

        return DeckConfig(
            name=deck_data.get("name", "Default Deck"),
            cols=deck_data.get("cols", 4),
            rows=deck_data.get("rows", 3),
            disabled_tiles=disabled_tiles,
            stations=stations,
            tracks=tracks,
            locations=locations,
            devices=devices,
        )

    async def save_full_config(self, config: DeckConfig) -> None:
        """Save complete deck configuration to all files."""
        await self.save_deck_config(
            config.name, config.cols, config.rows, config.disabled_tiles
        )
        await self.save_locations(config.locations)
        await self.save_tracks(config.tracks)
        await self.save_stations(config.stations)
        await self.save_devices(config.devices)
