from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime

from dataclasses_jsonschema import JsonSchemaMixin


@dataclass
class Point(JsonSchemaMixin):
    x: float
    y: float


@dataclass
class Foo(JsonSchemaMixin):
    """A foo that foos"""
    a: datetime
    b: List[Point]
    c: Dict[str, int]
    d: Optional[str] = None
