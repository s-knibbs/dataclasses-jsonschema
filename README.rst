Dataclasses JSON Schema
=======================

.. image:: https://travis-ci.org/s-knibbs/dataclasses-jsonschema.svg?branch=master
    :target: https://travis-ci.org/s-knibbs/dataclasses-jsonschema

.. image:: https://badge.fury.io/py/dataclasses-jsonschema.svg
    :target: https://badge.fury.io/py/dataclasses-jsonschema

.. image:: https://img.shields.io/lgtm/grade/python/g/s-knibbs/dataclasses-jsonschema.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/s-knibbs/dataclasses-jsonschema/context:python
    :alt:    Language grade: Python

A lightweight library to generate JSON Schema from python 3.7 dataclasses. Python 3.6 is supported through the `dataclasses backport <https://github.com/ericvsmith/dataclasses>`_. Also supports the following features:

* Generate schemas that can be embedded into Swagger / OpenAPI 2.0 and 3.0 specs
* Serialisation and deserialisation
* Data validation against the generated schema

Installation
------------

.. code:: bash

    ~$ pip install dataclasses-jsonschema

For improved validation performance using `PyValico <https://github.com/s-knibbs/pyvalico>`_, install with:

.. code:: bash

    ~$ pip install dataclasses-jsonschema[fast-validation]

Examples
--------

.. code:: python

    from dataclasses import dataclass

    from dataclasses_jsonschema import JsonSchemaMixin


    @dataclass
    class Point(JsonSchemaMixin):
        "A 2D point"
        x: float
        y: float


Generate the schema:

.. code:: python

    >>> pprint(Point.json_schema())
    {
        'description': 'A 2D point',
        'type': 'object',
        'properties': {
            'x': {'format': 'float', 'type': 'number'},
            'y': {'format': 'float', 'type': 'number'}
        },
        'required': ['x', 'y']
    }

Serialise data:

.. code:: python

    >>> Point(x=3.5, y=10.1).to_dict()
    {'x': 3.5, 'y': 10.1}

Deserialise data:

.. code:: python

    >>> Point.from_dict({'x': 3.14, 'y': 1.5})
    Point(x=3.14, y=1.5)
    >>> Point.from_dict({'x': 3.14, y: 'wrong'})
    dataclasses_jsonschema.ValidationError: 'wrong' is not of type 'number'

Generate a schema for embedding into an API spec:

.. code:: python

    from dataclasses_jsonschema import JsonSchemaMixin, SchemaType
    
    @dataclass
    class Address(JsonSchemaMixin):
        """Postal Address"""
        building: str
        street: str
        city: str
    
    @dataclass
    class Company(JsonSchemaMixin):
        """Company Details"""
        name: str
        address: Address
    
    >>> pprint(JsonSchemaMixin.all_json_schemas(schema_type=SchemaType.SWAGGER_V3))
    {'Address': {'description': 'Postal Address',
                 'properties': {'building': {'type': 'string'},
                                'city': {'type': 'string'},
                                'street': {'type': 'string'}},
                 'required': ['building', 'street', 'city'],
                 'type': 'object'},
     'Company': {'description': 'Company Details',
                 'properties': {'address': {'$ref': '#/components/schemas/Address'},
                                'name': {'type': 'string'}},
                 'required': ['name', 'address'],
                 'type': 'object'}}
        

Custom validation rules can be added using `NewType <https://docs.python.org/3/library/typing.html#newtype>`_:

.. code:: python

    from dataclasses_jsonschema import JsonSchemaMixin, FieldEncoder

    PhoneNumber = NewType('PhoneNumber', str)
    
    class PhoneNumberField(FieldEncoder):
    
        @property
        def json_schema(self):
            return {'type': 'string', 'pattern': r'^(\([0-9]{3}\))?[0-9]{3}-[0-9]{4}$'}
    
    JsonSchemaMixin.register_field_encoders({PhoneNumber: PhoneNumberField()})
    
    @dataclass
    class Person(JsonSchemaMixin):
        name: str
        phone_number: PhoneNumber

For more examples `see the tests <https://github.com/s-knibbs/dataclasses-jsonschema/blob/master/tests/conftest.py>`_

TODO
----

* Add benchmarks against alternatives such as `pydantic <https://github.com/samuelcolvin/pydantic>`_ and `marshmallow <https://github.com/marshmallow-code/marshmallow>`_


KNOWN ISSUES
------------

The following will currently fail when installed alongside ``pyvalico==0.0.2``

.. code:: python

    @dataclass
    class Baz(JsonSchemaMixin):
        """Type with nested default value"""
        a: Point = field(default=Point(0.0, 0.0))

    Baz.from_dict({})

The workaround is to pin pyvalico to v0.0.1
