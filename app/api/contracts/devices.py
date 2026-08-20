from app.api.contracts.base import ApiModel, DeviceId
from app.api.contracts.commands import CommandSnapshotOut
from app.api.contracts.telemetry import TelemetryOut


class DeviceSnapshotOut(ApiModel):
    device_id: DeviceId
    telemetry: TelemetryOut | None = None
    command: CommandSnapshotOut | None = None
