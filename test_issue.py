import json
from typing import Optional, List
from dataclasses import dataclass

from apispec import APISpec

from dataclasses_jsonschema.apispec import DataclassesPlugin
from dataclasses_jsonschema import JsonSchemaMixin

# Create an APISpec
spec = APISpec(
    title="Swagger Petstore",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[DataclassesPlugin()],
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


@dataclass
class Cat(Pet):
    """A cat"""
    color: str


# Dependant schemas (e.g. 'Category') are added automatically
spec.components.schema("Pet", schema=Pet)
spec.components.schema("Cat", schema=Cat)
print(json.dumps(spec.to_dict(), indent=2))
