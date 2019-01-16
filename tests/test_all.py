from uuid import UUID

from .conftest import Foo, Point, Recursive, OpaqueData, ShoppingCart, Product, ProductList
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
        'e': {'type': 'string', 'minLength': 5, 'maxLength': 8},
        'h': {'$ref': '#/definitions/Point'}
    },
    'type': 'object',
    'required': ['a', 'c', 'd', 'f', 'g']
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

PRODUCT_SCHEMA = {
    'description': Product.__doc__,
    'properties': {'cost': {'type': 'number'},
                   'name': {'type': 'string'}},
    'required': ['name', 'cost'],
    'type': 'object'
}

SHOPPING_CART_SCHEMA = {
    'description': ShoppingCart.__doc__,
    'properties': {
        'items': {'items': {'$ref': '#/definitions/Product'}, 'type': 'array'},
    },
    'required': ['items'],
    'type': 'object'
}
PRODUCT_LIST_SCHEMA = {
    'description': ProductList.__doc__,
    'properties': {
        'products': {'additionalProperties': {'$ref': '#/definitions/Product'}, 'type': 'object'}
    },
    'type': 'object',
    'required': ['products']
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
                'Recursive': RECURSIVE_SCHEMA, 'OpaqueData': OPAQUE_DATA_SCHEMA,
                'Product': PRODUCT_SCHEMA, 'ShoppingCart': SHOPPING_CART_SCHEMA,
                'ProductList': PRODUCT_LIST_SCHEMA}
    assert expected == JsonSchemaMixin.json_schema()


def test_serialise_deserialise():
    data = {
        'a': '2018-06-03T12:00:00+00:00',
        'b': [{'z': 1.2, 'y': 1.5}],
        'c': {'Mon': 1, 'Tue': 2},
        'd': 'Wednesday',
        'e': 'testing',
        'f': ['xyz', 6],
        'g': ['abc'],
        'h': {'z': 0.5, 'y': 1.0}
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


def test_recursive_validation():
    # a valid shopping cart containing two items
    data = {"items": [{"name": "apple", "cost": 0.4}, {"name": "banana", "cost": 0.6}]}
    cart = ShoppingCart.from_dict(data, validate=True)
    assert len(cart.items) == 2
    assert {item.name for item in cart.items} == {"apple", "banana"}
    assert cart.cost == 0.4 + 0.6

    # a shopping cart containing an invalid item
    data = {"items": [{"name": 123}]}
    with pytest.raises(ValidationError):
        ShoppingCart.from_dict(data, validate=True)


def test_non_string_keys():
    p = ProductList(products={UUID('462b92e8-b3f7-4cb7-ae93-18e829c7e10d'): Product(name="hammer", cost=25.10)})
    expected_data = {"products": {"462b92e8-b3f7-4cb7-ae93-18e829c7e10d": {"name": "hammer", "cost": 25.10}}}
    assert p.to_dict() == expected_data
    assert ProductList.from_dict(expected_data) == p
