import datetime
from _decimal import Decimal
from copy import deepcopy
from enum import Enum

from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv6Address
from typing import List, NewType, Optional, Union, Set, Any, cast
from typing_extensions import Final, Literal
from uuid import UUID

from dataclasses_jsonschema.type_defs import Nullable, NULL, JsonDict
from .conftest import Foo, Point, Recursive, OpaqueData, ShoppingCart, Product, ProductList, SubSchemas, Bar, Weekday, \
    JsonSchemaMixin, Zoo, Baz
import pytest

from dataclasses_jsonschema import SchemaType, ValidationError, DecimalField, JsonSchemaMeta, FieldEncoder

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


def test_field_with_default_dataclass():
    assert Baz(a=Point(0.0, 0.0)) == Baz.from_dict({})


def test_embeddable_json_schema():
    expected = {'Point': POINT_SCHEMA, 'Foo': FOO_SCHEMA}
    assert expected == Foo.json_schema(embeddable=True)
    expected = {'Point': POINT_SCHEMA, 'Foo': SWAGGER_V2_FOO_SCHEMA}
    assert expected == SubSchemas.all_json_schemas(schema_type=SchemaType.SWAGGER_V2)
    expected = {
        'Point': deepcopy(POINT_SCHEMA),
        'Foo': deepcopy(SWAGGER_V3_FOO_SCHEMA),
    }
    expected['Point']['x-module-name'] = 'tests.conftest'
    expected['Foo']['x-module-name'] = 'tests.conftest'
    expected['Foo']['properties']['d']['x-module-name'] = 'tests.conftest'
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


def test_from_json_to_json():
    data = """
{
  "a": "2018-06-03T12:00:00+00:00",
  "b": [
    {
      "z": 1.2,
      "y": 1.5
    }
  ],
  "c": {
    "Mon": 1,
    "Tue": 2
  },
  "d": "Wednesday",
  "f": [
    "xyz",
    6
  ],
  "g": [
    "abc"
  ],
  "e": "testing",
  "h": {
    "z": 0.5,
    "y": 1.0
  }
}
"""
    f = Foo.from_json(data)
    assert f.f == ('xyz', 6)
    assert f.g == ('abc',)
    assert data.strip() == f.to_json(indent=2)


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
        id: Optional[int] = field(metadata=JsonSchemaMeta(read_only=True), default=None)

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
    expected_schema['x-module-name'] = 'tests.test_core'
    assert Test.json_schema(schema_type=SchemaType.OPENAPI_3, embeddable=True) == {'Test': expected_schema}
    expected_schema['properties']['name']['example'] = 'foo'
    del expected_schema['properties']['name']['examples']
    del expected_schema['x-module-name']
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


def test_from_object():

    class Genre(Enum):
        HORROR = "horror"
        BIOGRAPHY = "biography"
        THRILLER = "thriller"

    class AuthorModel:

        def __init__(self, name, age, books):
            self.name = name
            self.age = age
            self.books = books

    class BookModel:

        def __init__(self, name, first_print, publisher, genre):
            self.name = name
            self.first_print = first_print
            self.publisher = publisher
            self.genre = genre

    @dataclass
    class Book(JsonSchemaMixin):
        name: str
        publisher: str
        genre: Optional[Genre]
        first_print: Optional[datetime.datetime] = None

    @dataclass
    class Author(JsonSchemaMixin):
        name: str
        age: Optional[int] = None
        books: Optional[List[Book]] = None

    sample_author = AuthorModel(
        "Joe Bloggs", 32, [BookModel("Hello World!", datetime.datetime.utcnow(), "ACME Corp", "biography")]
    )
    expected_author = Author("Joe Bloggs", books=[Book("Hello World!", "ACME Corp", Genre.BIOGRAPHY)])
    assert Author.from_object(sample_author, exclude=('age', ('books', ('first_print',)))) == expected_author

    sample_author_2 = AuthorModel(
        "Joe Bloggs", 32, [BookModel("Hello World!", datetime.datetime.utcnow(), "ACME Corp", None)]
    )
    expected_author_2 = Author("Joe Bloggs", books=[Book("Hello World!", "ACME Corp", None)])
    assert Author.from_object(sample_author_2, exclude=('age', ('books', ('first_print',)))) == expected_author_2

    with pytest.raises(ValueError):
        Author.from_object(sample_author, exclude=('age', ('books', ('publisher',))))


def test_serialise_deserialise_opaque_data():
    data = OpaqueData(a=["foo", 123], b={"foo": "bar", "baz": 123})
    dict_data = {"a": ["foo", 123], "b": {"foo": "bar", "baz": 123}}
    assert data.to_dict() == dict_data
    assert data == OpaqueData.from_dict(dict_data)


def test_inherited_schema():
    @dataclass
    class Pet(JsonSchemaMixin):
        """A generic pet"""
        name: str

    @dataclass
    class Cat(Pet):
        """A cat"""
        hunting_skill: str

    @dataclass
    class Dog(Pet):
        """A dog"""
        breed: str

    expected_cat_schema = compose_schema({
        "description": "A cat",
        "allOf": [
            {"$ref": "#/definitions/Pet"},
            {
                "type": "object",
                "properties": {"hunting_skill": {"type": "string"}},
                "required": ["hunting_skill"]
            },
        ]
    }, {
        "Pet": {
            "description": "A generic pet",
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    })
    expected_dog_schema = compose_schema({
        "description": "A dog",
        "allOf": [
            {"$ref": "#/definitions/Pet"},
            {
                "type": "object",
                "properties": {"breed": {"type": "string"}},
                "required": ["breed"]
            },
        ]
    }, {
        "Pet": {
            "description": "A generic pet",
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    })
    assert Cat.json_schema() == expected_cat_schema
    assert Dog.json_schema() == expected_dog_schema


def test_optional_union():
    @dataclass
    class Baz(JsonSchemaMixin):
        """Class with optional union"""
        a: Optional[Union[int, str]]

    expected_schema = compose_schema({
        "description": "Class with optional union",
        "type": "object",
        "properties": {
            "a": {"oneOf": [{"type": "integer"}, {"type": "string"}]}
        }
    })
    assert Baz.json_schema() == expected_schema


def test_nullable_field():
    @dataclass
    class Employee(JsonSchemaMixin):
        """An employee"""
        name: str
        manager: Nullable[Optional[str]] = None

    expected_openapi_3_schema = {
        "type": "object",
        "description": "An employee",
        "properties": {
            "name": {"type": "string"},
            "manager": {"type": "string", "nullable": True}
        },
        "required": ["name"],
        "x-module-name": "tests.test_core"
    }
    expected_json_schema = compose_schema({
        "type": "object",
        "description": "An employee",
        "properties": {
            "name": {"type": "string"},
            "manager": {"oneOf": [{"type": "string"}, {"type": "null"}]}
        },
        "required": ["name"]
    })
    assert Employee.json_schema() == expected_json_schema
    assert (
        Employee.json_schema(embeddable=True, schema_type=SchemaType.OPENAPI_3)["Employee"] == expected_openapi_3_schema
    )

    expected_obj = Employee(name="Joe Bloggs", manager=NULL)
    expected_dict = {"name": "Joe Bloggs", "manager": None}
    assert Employee.from_dict(expected_dict) == expected_obj
    assert expected_dict == expected_obj.to_dict()


def test_underscore_fields():
    @dataclass
    class Album(JsonSchemaMixin):
        """An album"""
        _id: int
        name: str

    expected_json_schema = compose_schema({
        "type": "object",
        "description": "An album",
        "properties": {
            "name": {"type": "string"},
            "_id": {"type": "integer"}
        },
        "required": ["_id", "name"]
    })
    assert Album.json_schema() == expected_json_schema
    expected_data = {"name": "Foo", "_id": 5}
    expected_obj = Album(_id=5, name="Foo")
    assert expected_data == expected_obj.to_dict()
    assert expected_obj == Album.from_dict(expected_data)


def test_discriminators():
    @dataclass
    class Pet(JsonSchemaMixin, discriminator=True):
        """A generic pet"""
        name: str

    @dataclass
    class Dog(Pet):
        """A dog"""
        breed: str

    expected_dog_schema = {
        "Dog": {
            "description": "A dog",
            "allOf": [
                {"$ref": "#/components/schemas/Pet"},
                {
                    "type": "object",
                    "properties": {"breed": {"type": "string"}},
                    "required": ["breed"],
                    "x-module-name": "tests.test_core",
                },
            ]
        },
        "Pet": {
            "description": "A generic pet",
            "type": "object",
            "properties": {
                "PetType": {"type": "string"},
                "name": {"type": "string"}
            },
            "required": ["name", "PetType"],
            "discriminator": {"propertyName": "PetType"},
            "x-module-name": "tests.test_core",
        }
    }

    assert Dog.json_schema(embeddable=True, schema_type=SchemaType.OPENAPI_3) == expected_dog_schema
    expected_dog = {
        "PetType": "Dog",
        "name": "Fido",
        "breed": "Dalmation"
    }
    assert Dog(name="Fido", breed="Dalmation").to_dict() == expected_dog
    assert Dog(name="Fido", breed="Dalmation") == Pet.from_dict(expected_dog)


def test_set_decode_encode():
    @dataclass
    class BlogArticle(JsonSchemaMixin):
        """A blog article"""
        content: str
        tags: Set[str]

    expected_schema = compose_schema({
        "type": "object",
        "description": "A blog article",
        "properties": {
            "content": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
        },
        "required": ["content", "tags"]
    })
    assert expected_schema == BlogArticle.json_schema()
    expected_blog_dict = {
        "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit...",
        "tags": ["foo", "bar"]
    }
    expected_blog = BlogArticle(
        content="Lorem ipsum dolor sit amet, consectetur adipiscing elit...",
        tags={"foo", "bar"}
    )
    assert isinstance(expected_blog.to_dict()["tags"], list)
    assert len(expected_blog.to_dict()["tags"]) == 2
    assert BlogArticle.from_dict(expected_blog_dict) == expected_blog


def test_any_type_schema():
    @dataclass
    class GraphNode(JsonSchemaMixin):
        """A graph node"""
        id: int
        data: Any

    expected_schema = compose_schema({
        "type": "object",
        "description": "A graph node",
        "properties": {
            "id": {"type": "integer"},
            "data": {}
        },
        "required": ["id", "data"]
    })
    assert GraphNode.json_schema() == expected_schema


def test_additional_properties_allowed():
    @dataclass
    class Scorpion(JsonSchemaMixin, allow_additional_props=False):
        """A scorpion"""
        species: str
        venom_rating: int

    expected_schema = compose_schema({
        "type": "object",
        "description": "A scorpion",
        "properties": {
            "species": {"type": "string"},
            "venom_rating": {"type": "integer"},
        },
        "required": ["species", "venom_rating"],
        "additionalProperties": False,
    })
    assert Scorpion.json_schema() == expected_schema


def test_property_serialisation():
    @dataclass
    class Rectangle(JsonSchemaMixin, serialise_properties=("area",)):
        """A rectangle"""
        width: float
        height: float

        @property
        def area(self) -> float:
            return self.width * self.height

        @property
        def perimeter(self) -> float:
            return 2 * self.width + 2 * self.height

    expected_schema = compose_schema({
        "type": "object",
        "description": "A rectangle",
        "properties": {
            "width": {"type": "number"},
            "height": {"type": "number"},
            "area": {"type": "number", "readOnly": True}
        },
        "required": ["width", "height"]
    })
    assert Rectangle.json_schema() == expected_schema
    rect = Rectangle(10, 20)
    assert rect.to_dict() == {"width": 10, "height": 20, "area": 200}
    assert Rectangle.from_dict({"width": 10, "height": 20}) == rect


def test_property_serialisation_all_properties():
    @dataclass
    class Rectangle(JsonSchemaMixin, serialise_properties=True):
        """A rectangle"""
        width: float
        height: float

        @property
        def area(self) -> float:
            return self.width * self.height

        @property
        def perimeter(self) -> float:
            return 2 * self.width + 2 * self.height

    expected_schema = compose_schema({
        "type": "object",
        "description": "A rectangle",
        "properties": {
            "width": {"type": "number"},
            "height": {"type": "number"},
            "area": {"type": "number", "readOnly": True},
            "perimeter": {"type": "number", "readOnly": True}
        },
        "required": ["width", "height"]
    })
    assert Rectangle.json_schema() == expected_schema


def test_inherited_field_narrowing():
    @dataclass
    class BaseObject(JsonSchemaMixin):
        """Base"""
        other: float
        field: str

    @dataclass
    class NarrowedObject(BaseObject, JsonSchemaMixin):
        """Narrowed"""
        field: Literal['staticstr']

    expected_schema = compose_schema({
      "allOf": [
        {
          "$ref": "#/definitions/BaseObject"
        },
        {
          "type": "object",
          "required": ["field"],
          "properties": {
            "field": {"enum": ["staticstr"]}
          }
        }
      ],
      "description": "Narrowed",
      "$schema": "http://json-schema.org/draft-06/schema#",
      "definitions": {
        "BaseObject": {
          "type": "object",
          "required": ["other", "field"],
          "properties": {
            "field": {"type": "string"},
            "other": {"type": "number"}
          },
          "description": "Base"
        }
      }
    })

    assert NarrowedObject.json_schema() == expected_schema


def test_unrecognized_enum_value():
    class PetType(Enum):
        CAT = "cat"
        DOG = "dog"

    class FoodType(Enum):
        KIBBLE = "kibble"
        FRESH = "fresh"

    @dataclass
    class Pet(JsonSchemaMixin):
        name: str
        type: PetType
        favourite_food: Optional[FoodType] = None

    p = Pet.from_dict({'name': 'snakey', 'type': 'python', 'favourite_food': 'mice'}, validate_enums=False)
    assert p.type == "python"
    assert p.favourite_food == "mice"

    with pytest.warns(UserWarning):
        assert p.to_dict() == {'name': 'snakey', 'type': 'python', 'favourite_food': 'mice'}


def test_inheritance_and_additional_properties_disallowed():
    @dataclass
    class Pet(JsonSchemaMixin):
        name: str

    # Currently this should raise an error until https://github.com/s-knibbs/dataclasses-jsonschema/issues/111
    # is implemented
    with pytest.raises(TypeError):
        @dataclass
        class Cat(Pet, allow_additional_props=False):
            hunting_skill: str


def test_newtype_decoding():
    StrippedString = NewType('StrippedString', str)

    class StrippedStringField(FieldEncoder[StrippedString, str]):

        def to_python(self, value: str) -> StrippedString:
            return cast(StrippedString, value.strip())

        @property
        def json_schema(self) -> JsonDict:
            return {'type': 'string'}

    JsonSchemaMixin.register_field_encoders({StrippedString: StrippedStringField()})

    @dataclass
    class Pet(JsonSchemaMixin):
        name: StrippedString
        type: str

    p = Pet.from_dict({'name': '  Fido ', 'type': 'dog'})
    assert p.name == 'Fido'


def test_module_name_extension():
    class PetType(Enum):
        DOG = "dog"
        CAT = "cat"

    @dataclass
    class Pet(JsonSchemaMixin):
        name: str
        type: PetType

    schema = Pet.json_schema(embeddable=True, schema_type=SchemaType.OPENAPI_3)
    assert schema['Pet']['x-module-name'] == 'tests.test_core'
    assert schema['Pet']['properties']['type']['x-module-name'] == 'tests.test_core'
