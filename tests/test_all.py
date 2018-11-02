from .conftest import Foo, Point, Recursive, OpaqueData
import pytest
try:
    from valico import ValidationError
except ImportError:
    from jsonschema import ValidationError

from dataclasses_jsonschema import JsonSchemaMixin


FOO_SCHEMA = {
    'description': 'A foo that foos',
    'properties': {
        'a': {'format': 'date-time', 'type': 'string'},
        'b': {'items': {'$ref': '#/definitions/Point'}, 'type': 'array'},
        'c': {'additionalProperties': {'type': 'integer'}, 'type': 'object'},
        'd': {'type': 'string', 'enum': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']},
        'f': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': [{'type': 'string'}, {'type': 'integer'}]},
        'g': {'type': 'array', 'items': {'type': 'string'}},
        'e': {'type': 'string', 'minLength': 5, 'maxLength': 8}},
    'type': 'object',
    'required': ['a', 'b', 'c', 'd', 'f', 'g']
}

# Fixme: Fields in description no longer match
POINT_SCHEMA = {
    'description': Point.__doc__,
    'type': 'object',
    'properties': {
        'z': {'type': 'number'},
        'y': {'type': 'number'}
    },
    'required': ['z', 'y']
}

RECURSIVE_SCHEMA = {
    "description": Recursive.__doc__,
    "properties": {
        'a': {'type': 'string'},
        'b': {'$ref': '#/definitions/Recursive'}
    },
    'type': 'object',
    'required': ['a']
}

OPAQUE_DATA_SCHEMA = {
    "description": OpaqueData.__doc__,
    "properties": {
        'a': {'type': 'array'},
        'b': {'type': 'object'}
    },
    'type': 'object',
    'required': ['a', 'b']
}


def test_json_schema():
    definitions = {'Point': POINT_SCHEMA}
    schema = {**FOO_SCHEMA, **{
            'definitions': definitions,
            '$schema': 'http://json-schema.org/draft-04/schema#'
        }
    }
    assert schema == Foo.json_schema()


def test_embeddable_json_schema():
    expected = {'Point': POINT_SCHEMA, 'Foo': FOO_SCHEMA}
    assert expected == Foo.json_schema(embeddable=True)
    expected = {'Point': POINT_SCHEMA, 'Foo': FOO_SCHEMA,
                'Recursive': RECURSIVE_SCHEMA, 'OpaqueData': OPAQUE_DATA_SCHEMA}
    assert expected == JsonSchemaMixin.json_schema()


def test_serialise_deserialise():
    data = {
        'a': '2018-06-03T12:00:00+00:00',
        'b': [{'z': 1.2, 'y': 1.5}],
        'c': {'Mon': 1, 'Tue': 2},
        'd': 'Wednesday',
        'e': 'testing',
        'f': ['xyz', 6],
        'g': ['abc']
    }
    f = Foo.from_dict(data)
    assert f.f == ('xyz', 6)
    assert f.g == ('abc',)
    assert data == f.to_dict()


def test_invalid_data():
    with pytest.raises(ValidationError):
        Point.from_dict({'z': 3.14, 'y': 'wrong'})


def test_newtype_field_validation():
    with pytest.raises(ValidationError):
        Foo.from_dict({
            'a': '2018-06-03T12:00:00+00:00',
            'b': [{'z': 1.2, 'y': 1.5}],
            'c': {'Mon': 1, 'Tue': 2},
            'd': 'Wednesday',
            'e': 't',
            'f': ['xyz', 6],
            'g': ['abc']
        })


def test_recursive_data():
    data = {"a": "test", "b": {"a": "test2"}}
    r = Recursive.from_dict(data)
    assert r.a == "test"
    assert r.to_dict() == data
