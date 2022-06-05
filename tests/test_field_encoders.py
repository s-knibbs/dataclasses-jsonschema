from dataclasses import dataclass
from typing import List
from dataclasses_jsonschema import JsonSchemaMixin
from dataclasses_jsonschema.field_types import FieldEncoder
from dataclasses_jsonschema.type_defs import JsonDict
import pytest

pytestmark = pytest.mark.filterwarnings("error:Unable to create schema")

class ExBar:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: "ExBar") -> bool:
        return self.name == other.name


class ExSubFoo:
    def __init__(self, number: int):
        self.number = number

    def __eq__(self, other: "ExSubFoo") -> bool:
        return self.number == other.number


class ExFoo:
    def __init__(self, ex_sub_foo: List[ExSubFoo]):
        self.ex_sub_foo = ex_sub_foo

    def __eq__(self, other: "ExFoo") -> bool:
        return self.ex_sub_foo == other.ex_sub_foo


class External:
    def __init__(self, ex_foo: ExFoo, ex_bar: ExBar):
        self.ex_foo = ex_foo
        self.ex_bar = ex_bar

    def __eq__(self, other: "External") -> bool:
        return self.ex_foo == other.ex_foo and self.ex_bar == other.ex_bar


class ExternalField(FieldEncoder):
    def to_python(self, value: dict) -> External:
        return External(
            ex_bar=ExBar(name=value["ex_bar"]["name"]),
            ex_foo=ExFoo(
                ex_sub_foo=[
                    ExSubFoo(number=ex_sub_foo["number"])
                    for ex_sub_foo in value["ex_foo"]["ex_sub_foo"]
                ]
            ),
        )

    def to_wire(self, value: External) -> dict:
        return {
            "ex_bar": {"name": value.ex_bar.name},
            "ex_foo": {
                "ex_sub_foo": [
                    {"number": ex_sub_foo.number}
                    for ex_sub_foo in value.ex_foo.ex_sub_foo
                ]
            },
        }

    @property
    def json_schema(self) -> JsonDict:
        return {
            "type": "object",
            "properties": {
                "ex_foo": {"$ref": "#/definitions/EX_FOO"},
                "ex_bar": {"$ref": "#/definitions/EX_BAR"},
            },
            "$schema": "http://json-schema.org/draft-06/schema#",
            "definitions": {
                "EX_FOO": {
                    "type": "object",
                    "properties": {
                        "ex_sub_foo": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/EX_SUB_FOO"},
                        }
                    },
                },
                "EX_BAR": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
                "EX_SUB_FOO": {
                    "type": "object",
                    "properties": {"number": {"type": "integer"}},
                },
            },
        }




def test_external_fields():
    JsonSchemaMixin.register_field_encoders({External: ExternalField()})

    @dataclass
    class Internal(JsonSchemaMixin):
        external: External

    internal_dict = {
        "external": {
            "ex_bar": {"name": "sample"},
            "ex_foo": {"ex_sub_foo": [{"number": number} for number in range(3)]},
        }
    }
    
    internal_obj = Internal(
        External(
            ex_bar=ExBar("sample"),
            ex_foo=ExFoo(ex_sub_foo=[ExSubFoo(number) for number in range(3)]),
        )
    )


    Internal._validate(internal_dict)

    # assert Internal.from_dict(internal_dict) == internal_obj
    # assert internal_obj.to_dict() == internal_dict
