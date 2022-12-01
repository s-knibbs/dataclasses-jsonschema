from __future__ import annotations

from typing import Any

try:
    from apispec import APISpec, BasePlugin
    from apispec.exceptions import DuplicateComponentNameError
except ImportError:
    raise ImportError("Missing the 'apispec' package. Try installing with 'dataclasses-jsonschema[apispec]'")

from . import JsonSchemaMixin, SchemaType


def _schema_reference(name: str, schema_type: SchemaType) -> str:
    if schema_type == SchemaType.SWAGGER_V2:
        return f"#/definitions/{name}"
    else:
        return f"#/components/schemas/{name}"


class DataclassesPlugin(BasePlugin):
    spec: APISpec

    def init_spec(self, spec: APISpec):
        super().init_spec(spec)
        self.spec = spec

    def resolve_schema_refs(self, data):

        if "schema" in data:

            if "$ref" in data["schema"]:
                data["schema"]["$ref"] = _schema_reference(data["schema"]["$ref"], self._schema_type)
            elif "items" in data["schema"] and "$ref" in data["schema"]["items"]:
                data["schema"]["items"]["$ref"] = _schema_reference(data["schema"]["items"]["$ref"], self._schema_type)
        else:
            for key in data:
                if isinstance(data[key], dict):
                    self.resolve_schema_refs(data[key])

    @property
    def _schema_type(self) -> SchemaType:
        return SchemaType.SWAGGER_V2 if self.spec.openapi_version.major == 2 else SchemaType.OPENAPI_3

    def schema_helper(self, name: str, definition: dict, **kwargs: Any) -> dict | None:
        schema: type[JsonSchemaMixin] | dict | None = kwargs.get("schema")
        if isinstance(schema, dict) or schema is None:
            return schema
        json_schemas = schema.json_schema(schema_type=self._schema_type, embeddable=True)
        for schema_name in json_schemas:
            if name == schema_name:
                continue
            try:
                self.spec.components.schema(schema_name, schema=json_schemas[schema_name])
            except DuplicateComponentNameError:
                # Catch duplicate schemas added due to multiple classes referencing the same dependent class
                pass
        return json_schemas[name]

    def parameter_helper(self, parameter, **kwargs):
        self.resolve_schema_refs(parameter)
        return parameter

    def response_helper(self, response, **kwargs):
        self.resolve_schema_refs(response)
        return response

    def operation_helper(self, path=None, operations=None, **kwargs):
        if operations is None:
            return None

        for operation in operations.values():
            if "parameters" in operation:
                for parameter in operation["parameters"]:
                    self.resolve_schema_refs(parameter)

            if self.spec.openapi_version.major >= 3:
                if "requestBody" in operation:
                    self.resolve_schema_refs(operation["requestBody"])

            for response in operation.get("responses", {}).values():
                self.resolve_schema_refs(response)
