from typing import Optional, Type, Union, Any, Dict, cast, Tuple, get_type_hints

from datetime import datetime
from dataclasses import fields
from uuid import UUID
from enum import Enum
import warnings

from dateutil.parser import parse
from jsonschema import validate as schema_validate

JSON_ENCODABLE_TYPES = {
    str: {'type': 'string'},
    int: {'type': 'number', 'format': 'integer'},
    bool: {'type': 'boolean'},
    float: {'type': 'number', 'format': 'float'}
}

JsonEncodable = Union[int, float, str, bool]
JsonDict = Dict[str, Any]


def is_enum(field_type: Any):
    return issubclass_safe(field_type, Enum)


def issubclass_safe(klass: Any, base: Type):
    try:
        return issubclass(klass, base)
    except TypeError:
        return False


def is_optional(field: Any) -> bool:
    return str(field).startswith('typing.Union') and issubclass(field.__args__[1], type(None))


class FieldEncoder:
    """Base class for encoding fields to and from JSON encodable values"""

    def to_wire(self, value: Any) -> JsonEncodable:
        return value

    def to_python(self, value: JsonEncodable) -> Any:
        return value

    @property
    def json_schema(self) -> JsonDict:
        raise NotImplemented


class DateTimeFieldEncoder(FieldEncoder):
    """Encodes datetimes to RFC3339 format"""

    def to_wire(self, value: datetime) -> str:
        out = value.isoformat(timespec='seconds')

        # Assume UTC if timezone is missing
        if value.tzinfo is None:
            return out + "Z"
        return out

    def to_python(self, value: JsonEncodable) -> datetime:
        return value if isinstance(value, datetime) else parse(cast(str, value))

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "date-time"}


class UuidField(FieldEncoder):

    def to_wire(self, value):
        return str(value)

    def to_python(self, value):
        return UUID(value)

    @property
    def json_schema(self):
        return {'type': 'string', 'format': 'uuid'}


class JsonSchemaMixin:
    """Mixin which adds methods to generate a JSON schema and
    convert to and from JSON encodable dicts with validation against the schema
    """
    _field_encoders: Dict[Type, FieldEncoder] = {datetime: DateTimeFieldEncoder(), UUID: UuidField()}

    # Cache of the generated schema
    _schema: Optional[JsonDict] = None
    _definitions: Optional[JsonDict] = None

    @classmethod
    def field_mapping(cls) -> Dict[str, str]:
        """Defines the mapping of python field names to JSON field names.

        The main use-case is to allow JSON field names which are Python keywords
        """
        return {}

    @classmethod
    def register_field_encoders(cls, field_encoders: Dict[Type, FieldEncoder]):
        """Registers additional custom field encoders. If called on the base, these are added globally.

        The DateTimeFieldEncoder is included by default.
        """
        if cls is not JsonSchemaMixin:
            cls._field_encoders = {**cls._field_encoders, **field_encoders}
        else:
            cls._field_encoders.update(field_encoders)

    def _encode_field(self, value: Any, omit_none: bool) -> Any:
        if type(value) in self._field_encoders:
            return self._field_encoders[type(value)].to_wire(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, dict):
            return {self._encode_field(k, omit_none): self._encode_field(v, omit_none) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(self._encode_field(v, omit_none) for v in value)
        elif isinstance(value, JsonSchemaMixin):
            # Only need to validate at the top level
            return value.to_dict(omit_none=omit_none, validate=False)
        else:
            # TODO: Copy value?
            return value

    def to_dict(self, omit_none: bool = True, validate: bool = False) -> JsonDict:
        """Converts the dataclass instance to a JSON encodable dict, with optional JSON schema validation.

        If omit_none (default True) is specified, any items with value None are removed
        """
        data = {}
        for f in fields(self):
            if f.name.startswith("_"):
                continue
            value = self._encode_field(getattr(self, f.name), omit_none)
            if omit_none and value is None:
                continue
            data[self.field_mapping().get(f.name, f.name)] = value
        if validate:
            schema_validate(data, self.json_schema())
        return data

    @classmethod
    def _decode_field(cls, field: str, field_type: Any, value: Any, validate: bool):
        if (type(value) in JSON_ENCODABLE_TYPES and field_type in JSON_ENCODABLE_TYPES) or value is None:
            return value

        # Replace any nested dictionaries with their targets
        field_type_name = cls._get_field_type_name(field_type)
        if cls._is_json_schema_subclass(field_type):
            return field_type.from_dict(value, validate)
        if is_optional(field_type):
            return cls._decode_field(field, field_type.__args__[0], value, validate)
        if field_type_name in ('Mapping', 'Dict'):
            return {key: cls._decode_field(field, field_type.__args__[1], val, validate) for key, val in value.items()}
        if field_type_name in ('Sequence', 'List'):
            return [cls._decode_field(field, field_type.__args__[0], val, validate) for val in value]
        if hasattr(field_type, "__supertype__"):  # NewType field
            return cls._decode_field(field, field_type.__supertype__, value, validate)
        if is_enum(field_type):
            try:
                decoded = field_type(value)
            except ValueError:
                if validate:
                    raise
                warnings.warn(f"Invalid enum value: {value}")
                decoded = value
            return decoded
        if field_type in cls._field_encoders:
            return cls._field_encoders[field_type].to_python(value)
        warnings.warn(f"Unable to decode value for '{field}: {field_type_name}'")
        return value

    @classmethod
    def from_dict(cls: Any, data: JsonDict, validate=True) -> Any:
        """Returns a dataclass instance with all nested classes converted from the dict given"""
        decoded_data = {}
        if validate:
            schema_validate(data, cls.json_schema())
        for field, field_type in get_type_hints(cls).items():
            if not field.startswith("_"):
                mapped_field = cls.field_mapping().get(field, field)
                decoded_data[field] = cls._decode_field(field, field_type, data.get(mapped_field), validate)
        return cls(**decoded_data)

    @staticmethod
    def _is_json_schema_subclass(field_type) -> bool:
        return issubclass_safe(field_type, JsonSchemaMixin)

    @classmethod
    def _get_field_schema(cls, field_type: Any) -> Tuple[JsonDict, bool]:
        field_schema: JsonDict = {'type': 'object'}
        required = True
        field_type_name = cls._get_field_type_name(field_type)
        if cls._is_json_schema_subclass(field_type):
            field_schema = {
                'type': 'object',
                '$ref': '#/definitions/{}'.format(field_type_name)
            }
        else:
            # If is optional[...]
            if is_optional(field_type):
                field_schema = cls._get_field_schema(field_type.__args__[0])[0]
                required = False
            elif is_enum(field_type):
                member_types = set()
                values = []
                for member in field_type:
                    member_types.add(type(member.value))
                    values.append(member.value)
                if len(member_types) == 1:
                    member_type = member_types.pop()
                    if member_type in JSON_ENCODABLE_TYPES:
                        field_schema.update(JSON_ENCODABLE_TYPES[member_type])
                    else:
                        field_schema.update(cls._field_encoders[member_types.pop()].json_schema)
                field_schema['enum'] = values
            elif field_type_name in ('Dict', 'Mapping'):
                field_schema = {'type': 'object'}
                if field_type.__args__[1] is not Any:
                    field_schema['additionalProperties'] = cls._get_field_schema(field_type.__args__[1])[0]
            elif field_type_name in ('Sequence', 'List'):
                field_schema = {'type': 'array'}
                if field_type.__args__[0] is not Any:
                    field_schema['items'] = cls._get_field_schema(field_type.__args__[0])[0]
            elif field_type in JSON_ENCODABLE_TYPES:
                field_schema = JSON_ENCODABLE_TYPES[field_type]
            elif field_type in cls._field_encoders:
                field_schema.update(cls._field_encoders[field_type].json_schema)
            elif hasattr(field_type, '__supertype__'):  # NewType fields
                field_schema, _ = cls._get_field_schema(field_type.__supertype__)
            else:
                warnings.warn(f"Unable to create schema for '{field_type_name}'")
        return field_schema, required

    @classmethod
    def json_schema(cls, embeddable=False) -> JsonDict:
        """Returns the JSON schema for the dataclass, along with the schema of any nested dataclasses
        within the 'definitions' field.

        Enable the embeddable flag to generate the schema in a format for embedding into other schemas
        or documents supporting JSON schema such as Swagger specs

        If called on the base class, this returns the JSON schema of all subclasses.
        """
        definitions: JsonDict = {}

        if cls._definitions is None:
            cls._definitions = definitions
        else:
            definitions = cls._definitions

        if cls is JsonSchemaMixin:
            for subclass in cls.__subclasses__():
                definitions.update(subclass.json_schema(embeddable=True))
            return definitions

        if cls._schema is not None:
            schema = cls._schema
        else:
            properties = {}
            required = []
            for field, field_type in get_type_hints(cls).items():
                # Internal field
                if field.startswith("_"):
                    continue
                mapped_field = cls.field_mapping().get(field, field)
                properties[mapped_field], is_required = cls._get_field_schema(field_type)
                item_type = field_type
                field_type_name = cls._get_field_type_name(field_type)
                if is_optional(field_type):
                    item_type = field_type.__args__[0]
                elif field_type_name in ('Dict', 'Mapping'):
                    item_type = field_type.__args__[1]
                elif field_type_name in ('Sequence', 'List'):
                    item_type = field_type.__args__[0]
                if cls._is_json_schema_subclass(item_type):
                    # Prevent recursion from forward refs & circular type dependencies
                    if item_type.__name__ not in definitions:
                        definitions[item_type.__name__] = None
                        definitions.update(item_type.json_schema(embeddable=True))
                if is_required:
                    required.append(mapped_field)
            schema = {
                'type': 'object',
                'required': required,
                'properties': properties
            }
            if len(required) == 0:
                del schema["required"]
            if cls.__doc__:
                schema['description'] = cls.__doc__
            cls._schema = schema

        if embeddable:
            return {**definitions, cls.__name__: schema}
        else:
            return {**schema, **{
                'definitions': definitions,
                '$schema': 'http://json-schema.org/draft-04/schema#'
            }}

    @staticmethod
    def _get_field_type_name(field_type: Any) -> Optional[str]:
        try:
            return field_type.__name__
        except AttributeError:
            try:
                return field_type._name
            except AttributeError:
                return None
