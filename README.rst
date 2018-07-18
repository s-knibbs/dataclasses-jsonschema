Dataclasses JSON Schema
=======================

.. image:: https://travis-ci.org/s-knibbs/dataclasses-jsonschema.svg?branch=master
    :target: https://travis-ci.org/s-knibbs/dataclasses-jsonschema

.. image:: https://badge.fury.io/py/dataclasses-jsonschema.svg
    :target: https://badge.fury.io/py/dataclasses-jsonschema

JSON schema generation from python 3.7 dataclasses. Python 3.6 is supported through the dataclasses backport.
Also provides serialisation to and from JSON data with JSON schema validation.

Examples
--------

.. code:: python

    from dataclasses import dataclass

    from dataclasses_jsonschema import JsonSchemaMixin


    @dataclass
    class Point(JsonSchemaMixin):
        x: float
        y: float


Generate the schema:

.. code:: python

    >>> pprint(Point.json_schema())
    {
        'description': 'Point(x:float, y:float)',
        'type': 'object',
        'properties': {
            'x': {'format': 'float', 'type': 'number'},
            'y': {'format': 'float', 'type': 'number'}
        },
        'required': ['x', 'y']
    }


Deserialise data:

.. code:: python

    >>> Point.from_dict({'x': 3.14, 'y': 1.5})
    Point(x=3.14, y=1.5)
    >>> Point.from_dict({'x': 3.14, y: 'wrong'})
    jsonschema.exceptions.ValidationError: 'wrong' is not of type 'number'


TODO
----

* Support type Union using 'oneOf'
