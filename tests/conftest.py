from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from dataclasses_jsonschema import JsonSchemaMixin


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
    e: Optional[str] = None
