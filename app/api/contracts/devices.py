from typing import Any

from pydantic import BaseModel


class DeviceSnapshotOut(BaseModel):
    device_id: str
    telemetry: dict[str, Any] | None = None
    command: dict[str, Any] | None = None
