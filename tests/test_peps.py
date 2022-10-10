from __future__ import annotations

from dataclasses import dataclass
from typing import List

from dataclasses_jsonschema import JsonSchemaMixin


def test_pep_604_types():
    @dataclass
    class Post(JsonSchemaMixin):
        body: str
        tags: str | List[str] | None
        metadata: List[str | int]

    schema = Post.json_schema()
    assert schema["properties"]["tags"] == {
        "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "string"}]
    }
    assert schema["properties"]["metadata"] == {
        "type": "array",
        "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
    }
    assert schema["required"] == ["body", "metadata"]


def test_pep_585_types():
    @dataclass
    class Collections(JsonSchemaMixin):
        a: list[str]
        b: dict[str, int]
        c: set[int]
        d: tuple[int, str]

    schema = Collections.json_schema()
    assert schema["properties"] == {
        "a": {"type": "array", "items": {"type": "string"}},
        "b": {"additionalProperties": {"type": "integer"}, "type": "object"},
        "c": {"type": "array", "items": {"type": "integer"}, "uniqueItems": True},
        "d": {"type": "array", "items": [{"type": "integer"}, {"type": "string"}], "maxItems": 2, "minItems": 2},
    }
    assert Collections(a=["foo"], b={"bar": 123}, c={4, 5}, d=(6, "baz")).to_dict() == {
        "a": ["foo"],
        "b": {"bar": 123},
        "c": [4, 5],
        "d": [6, "baz"],
    }
