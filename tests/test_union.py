from dataclasses import dataclass
from typing import Union

from dataclasses_jsonschema import JsonSchemaMixin


@dataclass
class A(JsonSchemaMixin):
    a: str


@dataclass
class B(JsonSchemaMixin):
    b: str


@dataclass
class C(JsonSchemaMixin):
    c: Union[A, B]


def test_nested_union():
    a_variant = C(A("a"))
    b_variant = C(B("a"))

    print(C.from_json(a_variant.to_json()))
    print(C.from_json(b_variant.to_json()))

    assert a_variant == C.from_json(a_variant.to_json())
    assert b_variant == C.from_json(b_variant.to_json())
