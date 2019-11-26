from dataclasses import dataclass
from typing import Union

import pytest

from dataclasses_jsonschema import JsonSchemaMixin


@pytest.mark.last
def test_nested_union():
    @dataclass
    class A(JsonSchemaMixin):
        a: str

    @dataclass
    class B(JsonSchemaMixin):
        b: str

    @dataclass
    class C(JsonSchemaMixin):
        c: Union[A, B]

    a_variant = C(A("a"))
    b_variant = C(B("a"))

    assert a_variant == C.from_json(a_variant.to_json())
    assert b_variant == C.from_json(b_variant.to_json())
