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
        'd': {'type': 'string', 'enum': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']},
        'e': {'type': 'string', 'minLength': 5, 'maxLength': 8}},
    'type': 'object',
    'required': ['a', 'b', 'c', 'd']
}

# Fixme: Fields in description no longer match
POINT_SCHEMA = {
    'description': 'Point(x:float, y:float)',
    'type': 'object',
    'properties': {
        'z': {'format': 'float', 'type': 'number'},
        'y': {'format': 'float', 'type': 'number'}
    },
    'required': ['z', 'y']
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
        'a': '2018-06-03T12:00:00+00:00',
        'b': [{'z': 1.2, 'y': 1.5}],
        'c': {'Mon': 1, 'Tue': 2},
        'd': 'Wednesday',
        'e': 'testing'
    }
    f = Foo.from_dict(data)
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
            'e': 't'
        })
