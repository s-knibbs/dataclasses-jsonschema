Dataclasses JSON Schema
=======================

.. image:: https://github.com/s-knibbs/dataclasses-jsonschema/workflows/Tox%20tests/badge.svg?branch=master
    :target: https://github.com/s-knibbs/dataclasses-jsonschema/actions

.. image:: https://badge.fury.io/py/dataclasses-jsonschema.svg
    :target: https://badge.fury.io/py/dataclasses-jsonschema

.. image:: https://img.shields.io/lgtm/grade/python/g/s-knibbs/dataclasses-jsonschema.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/s-knibbs/dataclasses-jsonschema/context:python
    :alt:    Language grade: Python

**Please Note:** This project is in maintenance mode. I'm currently only making urgent bugfixes.

A library to generate JSON Schema from python 3.7 dataclasses. Python 3.6 is supported through the `dataclasses backport <https://github.com/ericvsmith/dataclasses>`_. Aims to be a more lightweight alternative to similar projects such as `marshmallow <https://github.com/marshmallow-code/marshmallow>`_ & `pydantic <https://github.com/samuelcolvin/pydantic>`_.

Feature Overview
----------------

* Support for draft-04, draft-06, Swagger 2.0 & OpenAPI 3 schema types
* Serialisation and deserialisation
* Data validation against the generated schema
* `APISpec <https://github.com/marshmallow-code/apispec>`_ support. Example below_:

Installation
------------

.. code:: bash

    ~$ pip install dataclasses-jsonschema

For improved validation performance using `fastjsonschema <https://github.com/horejsek/python-fastjsonschema>`_, install with:

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


Schema Generation
^^^^^^^^^^^^^^^^^

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

Data Serialisation
^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> Point(x=3.5, y=10.1).to_dict()
    {'x': 3.5, 'y': 10.1}

Deserialisation
^^^^^^^^^^^^^^^

.. code:: python

    >>> Point.from_dict({'x': 3.14, 'y': 1.5})
    Point(x=3.14, y=1.5)
    >>> Point.from_dict({'x': 3.14, y: 'wrong'})
    dataclasses_jsonschema.ValidationError: 'wrong' is not of type 'number'

Generating multiple schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
        

Custom validation using `NewType <https://docs.python.org/3/library/typing.html#newtype>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

.. _below:

APISpec Plugin
--------------
**New in v2.5.0**

OpenAPI & Swagger specs can be generated using the apispec plugin:

.. code:: python

    from typing import Optional, List
    from dataclasses import dataclass

    from apispec import APISpec
    from apispec_webframeworks.flask import FlaskPlugin
    from flask import Flask, jsonify
    import pytest

    from dataclasses_jsonschema.apispec import DataclassesPlugin
    from dataclasses_jsonschema import JsonSchemaMixin


    # Create an APISpec
    spec = APISpec(
        title="Swagger Petstore",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[FlaskPlugin(), DataclassesPlugin()],
    )
    
    
    @dataclass
    class Category(JsonSchemaMixin):
        """Pet category"""
        name: str
        id: Optional[int]

    @dataclass
    class Pet(JsonSchemaMixin):
        """A pet"""
        categories: List[Category]
        name: str


    app = Flask(__name__)


    @app.route("/random")
    def random_pet():
        """A cute furry animal endpoint.
        ---
        get:
          description: Get a random pet
          responses:
            200:
              content:
                application/json:
                  schema: Pet
        """
        pet = get_random_pet()
        return jsonify(pet.to_dict())
 
    # Dependant schemas (e.g. 'Category') are added automatically
    spec.components.schema("Pet", schema=Pet)
    with app.test_request_context():
        spec.path(view=random_pet)

TODO
----

* Add benchmarks against alternatives such as `pydantic <https://github.com/samuelcolvin/pydantic>`_ and `marshmallow <https://github.com/marshmallow-code/marshmallow>`_
