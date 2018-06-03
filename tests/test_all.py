from .conftest import Foo, Point
import pytest
from jsonschema import ValidationError

from dataclasses_jsonschema import JsonSchemaMixin


FOO_SCHEMA = {
    'description': 'A foo that foos',
    'properties': {
        'a': {'format': 'date-time', 'type': 'string'},
        'b': {'items': {'$ref': '#/definitions/Point', 'type': 'object'}, 'type': 'array'},
        'c': {'additionalProperties': {'format': 'integer', 'type': 'number'}, 'type': 'object'},
        'd': {'type': 'string'}},
    'type': 'object',
    'required': ['a', 'b', 'c']
}

POINT_SCHEMA = {
    'description': 'Point(x:float, y:float)',
    'type': 'object',
    'properties': {
        'x': {'format': 'float', 'type': 'number'},
        'y': {'format': 'float', 'type': 'number'}
    },
    'required': ['x', 'y']
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
    assert expected == JsonSchemaMixin.json_schema()


def test_serialise_deserialise():
    data = {
        'a': '2018-06-03T12:00:00',
        'b': [{'x': 1.2, 'y': 1.5}],
        'c': {'Mon': 1, 'Tue': 2},
        'd': 'test'
    }
    f = Foo.from_dict(data)
    assert data == f.to_dict()


def test_invalid_data():
    with pytest.raises(ValidationError):
        Point.from_dict({'x': 3.14, 'y': 'wrong'})
