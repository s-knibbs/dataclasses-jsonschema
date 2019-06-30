from _decimal import Decimal
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv6Address
from typing import List, NewType
from typing_extensions import Final, Literal
from uuid import UUID

from .conftest import Foo, Point, Recursive, OpaqueData, ShoppingCart, Product, ProductList, SubSchemas, Bar, Weekday, \
    JsonSchemaMixin, Zoo, Baz
import pytest

from dataclasses_jsonschema import SchemaType, ValidationError, DecimalField, JsonSchemaMeta

try:
    import valico as _

    have_valico = True
except ImportError:
    have_valico = False

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

SWAGGER_V2_FOO_SCHEMA = {
    'description': 'A foo that foos',
    'properties': {
        'a': {'format': 'date-time', 'type': 'string'},
        'b': {'items': {'$ref': '#/definitions/Point'}, 'type': 'array'},
        'c': {'additionalProperties': {'type': 'integer'}, 'type': 'object'},
        'd': {
            'type': 'string',
            'enum': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'x-enum-name': 'Weekday'
        },
        'f': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': [{'type': 'string'}, {'type': 'integer'}]},
        'g': {'type': 'array', 'items': {'type': 'string'}},
        'e': {'type': 'string', 'minLength': 5, 'maxLength': 8},
        'h': {'$ref': '#/definitions/Point'}
    },
    'type': 'object',
    'required': ['a', 'c', 'd', 'f', 'g']
}

SWAGGER_V3_FOO_SCHEMA = {
    'description': 'A foo that foos',
    'properties': {
        'a': {'format': 'date-time', 'type': 'string'},
        'b': {'items': {'$ref': '#/components/schemas/Point'}, 'type': 'array'},
        'c': {'additionalProperties': {'type': 'integer'}, 'type': 'object'},
        'd': {
            'type': 'string',
            'enum': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'x-enum-name': 'Weekday'
        },
        'f': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': [{'type': 'string'}, {'type': 'integer'}]},
        'g': {'type': 'array', 'items': {'type': 'string'}},
        'e': {'type': 'string', 'minLength': 5, 'maxLength': 8},
        'h': {'$ref': '#/components/schemas/Point'}
    },
    'type': 'object',
    'required': ['a', 'c', 'd', 'f', 'g']
}

# Fixme: Fields in description no longer match
POINT_SCHEMA = {
    'description': Point.__doc__,
    'type': 'object',
    'properties': {
        'z': {'type': 'number', 'description': 'Point x coordinate'},
        'y': {'type': 'number', 'description': 'Point y coordinate'}
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
    'properties': {'cost': {'type': 'number', 'default': 20.0},
                   'name': {'type': 'string'}},
    'required': ['name'],
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
BAR_SCHEMA = {
    'type': 'object',
    'description': "Type with union field",
    'properties': {
        'a': {
            'oneOf': [
                {'type': 'string', 'enum': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']},
                {'$ref': '#/definitions/Point'}
            ]
        }
    },
    'required': ['a']
}
ZOO_SCHEMA = {
    'type': 'object',
    'description': "A zoo",
    'properties': {
        'animal_types': {'additionalProperties': {'type': 'string'}, 'type': 'object', 'default': {}}
    }
}
BAZ_SCHEMA = {
    'description': 'Type with nested default value',
    'properties': {'a': {'$ref': '#/definitions/Point', 'default': {'z': 0.0, 'y': 0.0}}},
    'type': 'object'
}


def compose_schema(schema, definitions=None):
    full_schema = {**schema, **{
        '$schema': 'http://json-schema.org/draft-06/schema#'
    }}
    if definitions is not None:
        full_schema['definitions'] = definitions
    return full_schema


def test_field_with_default_factory():
    assert Zoo(animal_types={}) == Zoo.from_dict({})
    assert Zoo(animal_types={"snake": "reptile", "dog": "mammal"}) == Zoo.from_dict(
        {"animal_types": {"snake": "reptile", "dog": "mammal"}}
    )


# TODO: Investigate this / raise an issue on https://github.com/rustless/valico
@pytest.mark.skipif(have_valico, reason="Skipped due to valico bug")
def test_field_with_default_dataclass():
    assert Baz(a=Point(0.0, 0.0)) == Baz.from_dict({})


def test_embeddable_json_schema():
    expected = {'Point': POINT_SCHEMA, 'Foo': FOO_SCHEMA}
    assert expected == Foo.json_schema(embeddable=True)
    expected = {'Point': POINT_SCHEMA, 'Foo': SWAGGER_V2_FOO_SCHEMA}
    assert expected == SubSchemas.all_json_schemas(schema_type=SchemaType.SWAGGER_V2)
    expected = {'Point': POINT_SCHEMA, 'Foo': SWAGGER_V3_FOO_SCHEMA}
    assert expected == SubSchemas.all_json_schemas(schema_type=SchemaType.SWAGGER_V3)
    expected = {
        'Point': POINT_SCHEMA,
        'Foo': FOO_SCHEMA,
        'Recursive': RECURSIVE_SCHEMA,
        'Product': PRODUCT_SCHEMA,
        'ProductList': PRODUCT_LIST_SCHEMA,
        'Bar': BAR_SCHEMA,
        'ShoppingCart': SHOPPING_CART_SCHEMA,
        'OpaqueData': OPAQUE_DATA_SCHEMA,
        'Zoo': ZOO_SCHEMA,
        'Baz': BAZ_SCHEMA
    }
    assert expected == JsonSchemaMixin.all_json_schemas()
    with pytest.warns(DeprecationWarning):
        assert expected == JsonSchemaMixin.json_schema()


def test_json_schema():
    definitions = {'Point': POINT_SCHEMA}
    assert compose_schema(FOO_SCHEMA, definitions) == Foo.json_schema()


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


def test_type_union_schema():
    expected_schema = {
        **BAR_SCHEMA,
        'definitions': {'Point': POINT_SCHEMA},
        '$schema': 'http://json-schema.org/draft-06/schema#'
    }
    assert expected_schema == Bar.json_schema()

    # Should throw an error with SchemaType.SWAGGER_V2
    with pytest.raises(TypeError):
        Bar.json_schema(embeddable=True, schema_type=SchemaType.SWAGGER_V2)


def test_type_union_serialise():
    assert Bar(a=Weekday.MON).to_dict() == {'a': 'Monday'}
    assert Bar(a=Point(x=1.25, y=3.5)).to_dict() == {'a': {'z': 1.25, 'y': 3.5}}


def test_type_union_deserialise():
    assert Bar.from_dict({'a': 'Friday'}) == Bar(a=Weekday.FRI)
    assert Bar.from_dict({'a': {'z': 3.6, 'y': 10.1}}) == Bar(a=Point(x=3.6, y=10.1))


def test_default_values():
    assert Product(name="hammer", cost=20.0) == Product.from_dict({"name": "hammer"})


def test_default_factory():
    @dataclass
    class ClassTest(JsonSchemaMixin):
        attri: List[str] = field(default_factory=lambda: ['val'])

    assert 'required' not in ClassTest.json_schema().keys()

    assert ClassTest().attri == ['val']
    assert ClassTest().to_dict() == {'attri': ['val']}
    assert ClassTest.from_dict({}).attri == ['val']


def test_read_only_field():
    @dataclass
    class Employee(JsonSchemaMixin):
        name: str
        department: str
        id: int = field(metadata=dict(read_only=True), default=-1)

    schema = Employee.json_schema(schema_type=SchemaType.OPENAPI_3, embeddable=True)
    assert schema['Employee']['properties']['id']['readOnly']
    assert 'readOnly' not in Employee.json_schema(schema_type=SchemaType.DRAFT_06)['properties']['id']


def test_read_only_field_no_default():
    @dataclass
    class Employee(JsonSchemaMixin):
        name: str
        department: str
        id: int = field(metadata=JsonSchemaMeta(read_only=True))

    with pytest.warns(UserWarning):
        Employee.json_schema(schema_type=SchemaType.OPENAPI_3, embeddable=True)


def test_field_types():
    Currency = NewType('Currency', Decimal)
    JsonSchemaMixin.register_field_encoders({
        Currency: DecimalField(precision=2)
    })

    @dataclass
    class AllFieldTypes(JsonSchemaMixin):
        """All field types used"""
        ip_address: IPv4Address
        ipv6_address: IPv6Address
        cost: Currency
        uuid: UUID

    expected_schema = compose_schema({
        'description': 'All field types used',
        'type': 'object',
        'properties': {
            'ip_address': {'type': 'string', 'format': 'ipv4'},
            'ipv6_address': {'type': 'string', 'format': 'ipv6'},
            'cost': {'type': 'number', 'multipleOf': 0.01},
            'uuid': {
                'type': 'string',
                'format': 'uuid',
                'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            }
        },
        'required': ['ip_address', 'ipv6_address', 'cost', 'uuid']
    })

    assert AllFieldTypes.json_schema() == expected_schema
    expected_uuid = UUID('032bbcad-9ca2-4f36-9a63-43a036bc5755')
    expected_obj = AllFieldTypes(
        ip_address=IPv4Address('127.0.0.1'),
        ipv6_address=IPv6Address('::1'),
        cost=Currency(Decimal('49.99')),
        uuid=expected_uuid
    )
    expected_dict = {
        "ip_address": "127.0.0.1",
        "ipv6_address": "::1",
        "cost": 49.99,
        "uuid": str(expected_uuid)
    }
    assert expected_obj == AllFieldTypes.from_dict(expected_dict)
    assert expected_obj.to_dict() == expected_dict


def test_field_metadata():
    @dataclass
    class Test(JsonSchemaMixin):
        """Dataclass with field metadata"""
        name: str = field(
            metadata=JsonSchemaMeta(
                title="Title of the field",
                description="Description of the field",
                examples=["foo", "bar"],
                extensions={
                    'field-group': 1
                }
            )
        )

    expected_schema = {
        'type': 'object',
        'description': 'Dataclass with field metadata',
        'properties': {
            'name': {
                'type': 'string',
                'examples': ['foo', 'bar'],
                'title': 'Title of the field',
                'description': 'Description of the field'
            }
        },
        'required': ['name']
    }
    expected_full_schema = compose_schema(expected_schema)
    assert Test.json_schema() == expected_full_schema
    expected_schema['properties']['name']['x-field-group'] = 1
    assert Test.json_schema(schema_type=SchemaType.OPENAPI_3, embeddable=True) == {'Test': expected_schema}
    expected_schema['properties']['name']['example'] = 'foo'
    del expected_schema['properties']['name']['examples']
    assert Test.json_schema(schema_type=SchemaType.SWAGGER_V2, embeddable=True) == {'Test': expected_schema}


def test_final_field():

    @dataclass
    class TestWithFinal(JsonSchemaMixin):
        """Dataclass with final field"""
        name: Final[str]

    expected_schema = {
        'type': 'object',
        'description': 'Dataclass with final field',
        'properties': {
            'name': {'type': 'string'}
        },
        'required': ['name']
    }

    assert TestWithFinal.json_schema() == compose_schema(expected_schema)
    assert TestWithFinal.from_dict({'name': 'foo'}) == TestWithFinal(name='foo')
    assert TestWithFinal(name='foo').to_dict() == {'name': 'foo'}


def test_literal_types():

    @dataclass
    class ImageMeta(JsonSchemaMixin):
        """Image metadata"""
        bits_per_pixel: Literal[8, 16, 24, "true-color", None]

    expected_schema = {
        'type': 'object',
        'description': 'Image metadata',
        'properties': {
            'bits_per_pixel': {'enum': [8, 16, 24, 'true-color', None]}
        },
        'required': ['bits_per_pixel']
    }
    assert ImageMeta.json_schema() == compose_schema(expected_schema)
    assert ImageMeta(bits_per_pixel=16).to_dict() == {"bits_per_pixel": 16}
    assert ImageMeta.from_dict({"bits_per_pixel": 16}) == ImageMeta(bits_per_pixel=16)
