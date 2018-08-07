from typing import Optional, List, Dict, NewType, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from dataclasses_jsonschema import JsonSchemaMixin, FieldEncoder

Postcode = NewType('Postcode', str)


class PostcodeField(FieldEncoder):

    @property
    def json_schema(self):
        return {'type': 'string', 'minLength': 5, 'maxLength': 8}


JsonSchemaMixin.register_field_encoders({Postcode: PostcodeField()})


class Weekday(Enum):
    MON = 'Monday'
    TUE = 'Tuesday'
    WED = 'Wednesday'
    THU = 'Thursday'
    FRI = 'Friday'


@dataclass
class Point(JsonSchemaMixin):
    x: float
    y: float

    @classmethod
    def field_mapping(cls) -> Dict[str, str]:
        return {'x': 'z'}


@dataclass
class Foo(JsonSchemaMixin):
    """A foo that foos"""
    a: datetime
    b: List[Point]
    c: Dict[str, int]
    d: Weekday
    e: Optional[Postcode] = None


@dataclass
class Recursive(JsonSchemaMixin):
    """A recursive data-structure"""
    a: str
    b: Optional['Recursive'] = None


@dataclass
class OpaqueData(JsonSchemaMixin):
    """Structure with unknown types"""
    a: List[Any]
    b: Dict[str, Any]
