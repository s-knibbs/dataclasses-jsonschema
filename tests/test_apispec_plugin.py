from typing import Optional, List
from dataclasses import dataclass
import json

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask
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


# Optional Flask support
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
    pass


EXPECTED_API_SPEC = {
    "paths": {
        "/random": {
            "get": {
                "description": "Get a random pet",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "tags": [],
    "info": {
        "title": "Swagger Petstore",
        "version": "1.0.0"
    },
    "openapi": "3.0.2",
    "components": {
        "schemas": {
            "Category": {
                "x-module-name": "tests.test_apispec_plugin",
                "description": "Pet category",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "id": {
                        "type": "integer",
                    }
                },
                "required": [
                    "name"
                ]
            },
            "Pet": {
                "x-module-name": "tests.test_apispec_plugin",
                "description": "A pet",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/Category"
                        }
                    }
                },
                "required": ["categories", "name"]
            },
            "Cat": {
                "allOf": [
                    {
                        "$ref": "#/components/schemas/Pet"
                    },
                    {
                        "type": "object",
                        "required": [
                            "colour"
                        ],
                        "properties": {
                            "colour": {"type": "string"}
                        },
                        "x-module-name": "tests.test_apispec_plugin"
                    }
                ],
                "description": "A cat"
            },
            "Dog": {
                "allOf": [
                    {
                        "$ref": "#/components/schemas/Pet"
                    },
                    {
                        "type": "object",
                        "required": [
                            "favourite_food"
                        ],
                        "properties": {
                            "favourite_food": {"type": "string"}
                        },
                        "x-module-name": "tests.test_apispec_plugin"
                    }
                ],
                "description": "A dog"
            }

        }
    }
}


@pytest.mark.last
def test_api_spec_schema():
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

    @dataclass
    class Cat(Pet):
        """A cat"""
        colour: str

    @dataclass
    class Dog(Pet):
        """A dog"""
        favourite_food: str

    spec.components.schema("Cat", schema=Cat)
    spec.components.schema("Dog", schema=Dog)
    with app.test_request_context():
        spec.path(view=random_pet)
    spec_json = json.dumps(spec.to_dict(), indent=2)
    spec_dict = json.loads(spec_json)
    assert spec_dict["paths"] == EXPECTED_API_SPEC["paths"]
    assert spec_dict["components"] == EXPECTED_API_SPEC["components"]
