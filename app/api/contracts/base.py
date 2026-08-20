from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
DeviceId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9._:-]*$',
    ),
]
RecordId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9._:-]*$',
    ),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True, use_enum_values=True)
