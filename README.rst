Dataclasses JSON Schema
=======================

.. image:: https://travis-ci.org/s-knibbs/dataclasses-jsonschema.svg?branch=master
    :target: https://travis-ci.org/s-knibbs/dataclasses-jsonschema

.. image:: https://badge.fury.io/py/dataclasses-jsonschema.svg
    :target: https://badge.fury.io/py/dataclasses-jsonschema

JSON schema generation from python 3.7 dataclasses. Python 3.6 is supported through the dataclasses backport.
Also provides serialisation to and from JSON data with JSON schema validation.

Installation
------------

.. code:: bash

    ~$ pip install dataclasses-jsonschema

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


Deserialise data:

.. code:: python

    >>> Point.from_dict({'x': 3.14, 'y': 1.5})
    Point(x=3.14, y=1.5)
    >>> Point.from_dict({'x': 3.14, y: 'wrong'})
    dataclasses_jsonschema.ValidationError: 'wrong' is not of type 'number'

For more examples `see the tests <https://github.com/s-knibbs/dataclasses-jsonschema/blob/master/tests/conftest.py>`_

TODO
----
* Support field default values, currently only a default value of `None` will work
* Support fields with `init=False` (see https://docs.python.org/3/library/dataclasses.html#dataclasses.field). Currently this will result in an error when decoding data containing one of these fields.
