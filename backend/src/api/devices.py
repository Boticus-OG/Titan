"""Device configuration API endpoints.

Provides CRUD operations for device placement in the workcell.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.deck import Device, DeviceClass, DeviceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config/devices", tags=["Device Configuration"])

# Storage path for device configuration (unified with deck data)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DEVICES_FILE = DATA_DIR / "devices.json"


# Pydantic models for API
class FootprintModel(BaseModel):
    width: float
    height: float


class OverhangModel(BaseModel):
    width: float
    depth: float
    offset_x: float
    offset_y: float


class NestModel(BaseModel):
    x: float
    y: float
    expected_plate_orientation: int = 0


class PositionModel(BaseModel):
    x: float
    y: float


class GridPosModel(BaseModel):
    col: int
    row: int


class DeviceModel(BaseModel):
    device_id: str
    name: str
    device_type: str
    device_class: str
    footprint: FootprintModel
    position: PositionModel
    orientation: int = 0
    grid_pos: GridPosModel | None = None
    nest: NestModel
    overhang: OverhangModel | None = None
    device_hub_id: str | None = None


class DeviceCreateModel(BaseModel):
    """Model for creating a new device (device_id is optional)."""

    device_id: str | None = None
    name: str
    device_type: str
    device_class: str
    footprint: FootprintModel
    position: PositionModel
    orientation: int = 0
    grid_pos: GridPosModel | None = None
    nest: NestModel
    overhang: OverhangModel | None = None
    device_hub_id: str | None = None


def _load_devices() -> list[dict[str, Any]]:
    """Load devices from JSON file."""
    if not DEVICES_FILE.exists():
        return []

    try:
        with open(DEVICES_FILE) as f:
            data = json.load(f)
            return data.get("devices", [])
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load devices: {e}")
        return []


def _save_devices(devices: list[dict[str, Any]]) -> None:
    """Save devices to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {"devices": devices}
    with open(DEVICES_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.get("")
async def list_devices() -> list[dict[str, Any]]:
    """List all configured devices."""
    return _load_devices()


@router.get("/{device_id}")
async def get_device(device_id: str) -> dict[str, Any]:
    """Get a specific device by ID."""
    devices = _load_devices()
    for device in devices:
        if device.get("device_id") == device_id:
            return device
    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@router.post("")
async def create_device(device: DeviceCreateModel) -> dict[str, Any]:
    """Create a new device."""
    devices = _load_devices()

    # Generate ID if not provided
    device_id = device.device_id
    if not device_id:
        import time
        import random
        device_id = f"dev_{int(time.time())}_{random.randint(1000, 9999)}"

    # Check for duplicate ID
    for existing in devices:
        if existing.get("device_id") == device_id:
            raise HTTPException(
                status_code=400, detail=f"Device {device_id} already exists"
            )

    # Validate device type and class
    try:
        DeviceType(device.device_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid device type: {device.device_type}"
        )

    try:
        DeviceClass(device.device_class)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid device class: {device.device_class}"
        )

    # Build device dict
    device_dict = {
        "device_id": device_id,
        "name": device.name,
        "device_type": device.device_type,
        "device_class": device.device_class,
        "footprint": device.footprint.model_dump(),
        "position": device.position.model_dump(),
        "orientation": device.orientation,
        "nest": device.nest.model_dump(),
    }

    if device.grid_pos:
        device_dict["grid_pos"] = device.grid_pos.model_dump()

    if device.overhang:
        device_dict["overhang"] = device.overhang.model_dump()

    if device.device_hub_id:
        device_dict["device_hub_id"] = device.device_hub_id

    devices.append(device_dict)
    _save_devices(devices)

    logger.info(f"Created device: {device_id}")
    return device_dict


@router.put("/{device_id}")
async def update_device(device_id: str, device: DeviceModel) -> dict[str, Any]:
    """Update an existing device."""
    devices = _load_devices()

    for i, existing in enumerate(devices):
        if existing.get("device_id") == device_id:
            # Update device
            device_dict = {
                "device_id": device_id,
                "name": device.name,
                "device_type": device.device_type,
                "device_class": device.device_class,
                "footprint": device.footprint.model_dump(),
                "position": device.position.model_dump(),
                "orientation": device.orientation,
                "nest": device.nest.model_dump(),
            }

            if device.grid_pos:
                device_dict["grid_pos"] = device.grid_pos.model_dump()

            if device.overhang:
                device_dict["overhang"] = device.overhang.model_dump()

            if device.device_hub_id:
                device_dict["device_hub_id"] = device.device_hub_id

            devices[i] = device_dict
            _save_devices(devices)

            logger.info(f"Updated device: {device_id}")
            return device_dict

    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@router.put("")
async def update_all_devices(devices_list: list[DeviceModel]) -> list[dict[str, Any]]:
    """Replace all devices (bulk update)."""
    devices = []

    for device in devices_list:
        device_dict = {
            "device_id": device.device_id,
            "name": device.name,
            "device_type": device.device_type,
            "device_class": device.device_class,
            "footprint": device.footprint.model_dump(),
            "position": device.position.model_dump(),
            "orientation": device.orientation,
            "nest": device.nest.model_dump(),
        }

        if device.grid_pos:
            device_dict["grid_pos"] = device.grid_pos.model_dump()

        if device.overhang:
            device_dict["overhang"] = device.overhang.model_dump()

        if device.device_hub_id:
            device_dict["device_hub_id"] = device.device_hub_id

        devices.append(device_dict)

    _save_devices(devices)
    logger.info(f"Saved {len(devices)} devices")
    return devices


@router.delete("/{device_id}")
async def delete_device(device_id: str) -> dict[str, str]:
    """Delete a device."""
    devices = _load_devices()

    for i, existing in enumerate(devices):
        if existing.get("device_id") == device_id:
            devices.pop(i)
            _save_devices(devices)
            logger.info(f"Deleted device: {device_id}")
            return {"status": "deleted", "device_id": device_id}

    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
