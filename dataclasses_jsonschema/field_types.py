import warnings
from datetime import date, datetime
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from typing import Generic, Optional, TypeVar, cast

# Note, iso8601 vs rfc3339 is subtle. rfc3339 is stricter, roughly a subset of iso8601.
# ciso8601 doesn’t support the entirety of the ISO 8601 spec, only a popular subset.
try:
    from ciso8601 import parse_datetime
except ImportError:
    from dateutil.parser import parse

    parse_datetime = parse  # type: ignore

try:
    from fastuuid import UUID
except ImportError:
    from uuid import UUID

from .type_defs import JsonDict, JsonEncodable

T = TypeVar("T")
OutType = TypeVar("OutType", bound=JsonEncodable)


class FieldEncoder(Generic[T, OutType]):
    """Base class for encoding fields to and from JSON encodable values"""

    def to_wire(self, value: T) -> OutType:
        # `cast` function call overhead adds up given how slow python is
        return value  # type: ignore

    def to_python(self, value: OutType) -> T:
        return value  # type: ignore

    @property
    def json_schema(self) -> JsonDict:
        raise NotImplementedError()


class DateFieldEncoder(FieldEncoder[date, str]):
    """Encodes dates to ISO8601 (compatible with RFC3339 subset) format"""

    def to_wire(self, value: date) -> str:
        return value.isoformat()

    def to_python(self, value: str) -> date:
        return value if isinstance(value, date) else parse_datetime(cast(str, value)).date()

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "date"}


class DateTimeFieldEncoder(FieldEncoder[datetime, str]):
    """Encodes datetimes to ISO8601 (compatible with RFC3339 subset) format"""

    def to_wire(self, value: datetime) -> str:
        out = value.isoformat()

        # Assume UTC if timezone is missing
        if value.tzinfo is None:
            warnings.warn("Naive datetime used, assuming utc")
            return out + "Z"
        return out

    def to_python(self, value: str) -> datetime:
        return value if isinstance(value, datetime) else parse_datetime(cast(str, value))

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "date-time"}


# Alias for backwards compat
DateTimeField = DateTimeFieldEncoder
UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class UuidField(FieldEncoder[UUID, str]):
    def to_wire(self, value: UUID) -> str:
        return str(value)

    def to_python(self, value: str) -> UUID:
        return UUID(value)

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "uuid", "pattern": UUID_REGEX}


class DecimalField(FieldEncoder[Decimal, float]):
    def __init__(self, precision: Optional[int] = None):
        self.precision = precision

    def to_wire(self, value: Decimal) -> float:
        return float(value)

    def to_python(self, value: float) -> Decimal:
        return Decimal(str(value))

    @property
    def json_schema(self) -> JsonDict:
        schema: JsonDict = {"type": "number"}
        if self.precision is not None and self.precision > 0:
            schema["multipleOf"] = float("0." + "0" * (self.precision - 1) + "1")
        return schema


class IPv4AddressField(FieldEncoder[IPv4Address, str]):
    def to_wire(self, value: IPv4Address) -> str:
        return str(value)

    def to_python(self, value: str) -> IPv4Address:
        return IPv4Address(value)

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "ipv4"}


class IPv6AddressField(FieldEncoder[IPv6Address, str]):
    def to_wire(self, value: IPv6Address) -> str:
        return str(value)

    def to_python(self, value: str) -> IPv6Address:
        return IPv6Address(value)

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "ipv6"}
