from typing import Optional, Type, Union, Any, Dict, cast, Tuple, List, TypeVar, get_type_hints, Callable
import re
from datetime import datetime
from dataclasses import fields, is_dataclass, Field, MISSING
from uuid import UUID
from enum import Enum
import warnings

from dateutil.parser import parse
try:
    import valico as validator
except ImportError:
    import jsonschema as validator

JSON_ENCODABLE_TYPES = {
    str: {'type': 'string'},
    int: {'type': 'integer'},
    bool: {'type': 'boolean'},
    float: {'type': 'number'}
}

JsonEncodable = Union[int, float, str, bool]
JsonDict = Dict[str, Any]


class ValidationError(Exception):
    pass


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
        raise NotImplementedError()


class DateTimeFieldEncoder(FieldEncoder):
    """Encodes datetimes to RFC3339 format"""

    def to_wire(self, value: datetime) -> str:
        out = value.isoformat()

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


class SchemaType(Enum):
    DRAFT_06 = "Draft6"
    DRAFT_04 = "Draft4"
    SWAGGER_V2 = "2.0"
    SWAGGER_V3 = "3.0"
    # Alias of SWAGGER_V2
    V2 = "2.0"
    # Alias of SWAGGER_V3
    V3 = "3.0"


# Retained for backwards compatibility
SwaggerSpecVersion = SchemaType


_ValueEncoder = Callable[[Any, Any, bool], Any]
_ValueDecoder = Callable[[str, Any, Any], Any]

T = TypeVar("T", bound='JsonSchemaMixin')


class JsonSchemaMixin:
    """Mixin which adds methods to generate a JSON schema and
    convert to and from JSON encodable dicts with validation against the schema
    """
    _field_encoders: Dict[Type, FieldEncoder] = {datetime: DateTimeFieldEncoder(), UUID: UuidField()}

    # Cache of the generated schema
    _schema: Optional[Dict[SchemaType, JsonDict]] = None
    _definitions: Optional[Dict[SchemaType, JsonDict]] = None
    # Cache of field encode / decode functions
    _encode_cache: Optional[Dict[Any, _ValueEncoder]] = None
    _decode_cache: Optional[Dict[Any, _ValueDecoder]] = None
    _mapped_fields: Optional[List[Tuple[Field, str]]] = None

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

    @classmethod
    def _encode_field(cls, field_type: Any, value: Any, omit_none: bool) -> Any:
        if value is None:
            return value
        try:
            encoder = cls._encode_cache[field_type]  # type: ignore
        except (KeyError, TypeError):
            if cls._encode_cache is None:
                cls._encode_cache = {}

            field_type_name = cls._get_field_type_name(field_type)
            if field_type in cls._field_encoders:
                def encoder(ft, v, __): return cls._field_encoders[ft].to_wire(v)
            elif is_optional(field_type):
                def encoder(ft, val, o): return cls._encode_field(ft.__args__[0], val, o)
            elif is_enum(field_type):
                def encoder(_, v, __): return v.value
            elif field_type_name == 'Union':
                # Attempt to encode the field with each union variant.
                # TODO: Find a more reliable method than this since in the case 'Union[List[str], Dict[str, int]]' this
                # will just output the dict keys as a list
                encoded = None
                for variant in field_type.__args__:
                    try:
                        encoded = cls._encode_field(variant, value, omit_none)
                        break
                    except (TypeError, AttributeError):
                        continue
                if encoded is None:
                    raise TypeError("No variant of '{}' matched the type '{}'".format(field_type, type(value)))
                return encoded
            elif field_type_name in ('Mapping', 'Dict'):
                def encoder(ft, val, o):
                    return {
                        cls._encode_field(ft.__args__[0], k, o): cls._encode_field(ft.__args__[1], v, o)
                        for k, v in val.items()
                    }
            elif field_type_name in ('Sequence', 'List') or (field_type_name == "Tuple" and ... in field_type.__args__):
                def encoder(ft, val, o): return [cls._encode_field(ft.__args__[0], v, o) for v in val]
            elif field_type_name == 'Tuple':
                def encoder(ft, val, o):
                    return [cls._encode_field(ft.__args__[idx], v, o) for idx, v in enumerate(val)]
            elif cls._is_json_schema_subclass(field_type):
                # Only need to validate at the top level
                def encoder(_, v, o): return v.to_dict(omit_none=o, validate=False)
            elif hasattr(field_type, "__supertype__"):  # NewType field
                def encoder(ft, v, o):
                    return cls._encode_field(ft.__supertype__, v, o)
            else:
                def encoder(_, v, __): return v
            cls._encode_cache[field_type] = encoder  # type: ignore
        return encoder(field_type, value, omit_none)

    @classmethod
    def _get_fields(cls) -> List[Tuple[Field, str]]:
        if cls._mapped_fields is None:
            mapped_fields = []
            type_hints = get_type_hints(cls)
            for f in fields(cls):
                # Skip internal fields
                if f.name.startswith("_"):
                    continue
                # Note fields() doesn't resolve forward refs
                f.type = type_hints[f.name]
                mapped_fields.append((f, cls.field_mapping().get(f.name, f.name)))
            cls._mapped_fields = mapped_fields  # type: ignore
        return cls._mapped_fields  # type: ignore

    def to_dict(self, omit_none: bool = True, validate: bool = False) -> JsonDict:
        """Converts the dataclass instance to a JSON encodable dict, with optional JSON schema validation.

        If omit_none (default True) is specified, any items with value None are removed
        """
        data = {}
        for field, target_field in self._get_fields():
            value = self._encode_field(field.type, getattr(self, field.name), omit_none)
            if omit_none and value is None:
                continue
            data[target_field] = value
        if validate:
            try:
                validator.validate(data, self.json_schema())
            except validator.ValidationError as e:
                raise ValidationError(str(e)) from e
        return data

    @classmethod
    def _decode_field(cls, field: str, field_type: Any, value: Any) -> Any:
        if value is None:
            return None
        decoder = None
        try:
            decoder = cls._decode_cache[field_type]  # type: ignore
        except (KeyError, TypeError):
            if type(value) in JSON_ENCODABLE_TYPES and field_type in JSON_ENCODABLE_TYPES:
                return value
            if cls._decode_cache is None:
                cls._decode_cache = {}
            # Replace any nested dictionaries with their targets
            field_type_name = cls._get_field_type_name(field_type)
            if cls._is_json_schema_subclass(field_type):
                def decoder(_, ft, val): return ft.from_dict(val, validate=False)
            elif is_optional(field_type):
                def decoder(f, ft, val): return cls._decode_field(f, ft.__args__[0], val)
            elif field_type_name == 'Union':
                # Attempt to decode the value using each decoder in turn
                decoded = None
                for variant in field_type.__args__:
                    try:
                        decoded = cls._decode_field(field, variant, value)
                        break
                    except (AttributeError, TypeError, ValueError):
                        continue
                if decoded is not None:
                    return decoded
            elif field_type_name in ('Mapping', 'Dict'):
                def decoder(f, ft, val):
                    return {
                        cls._decode_field(f, ft.__args__[0], k): cls._decode_field(f, ft.__args__[1], v)
                        for k, v in val.items()
                    }
            elif field_type_name in ('Sequence', 'List') or (field_type_name == "Tuple" and ... in field_type.__args__):
                seq_type = tuple if field_type_name == "Tuple" else list

                def decoder(f, ft, val):
                    return seq_type(cls._decode_field(f, ft.__args__[0], v) for v in val)
            elif field_type_name == "Tuple":
                def decoder(f, ft, val):
                    return tuple(cls._decode_field(f, ft.__args__[idx], v) for idx, v in enumerate(val))
            elif hasattr(field_type, "__supertype__"):  # NewType field
                def decoder(f, ft, val):
                    return cls._decode_field(f, ft.__supertype__, val)
            elif is_enum(field_type):
                def decoder(_, ft, val): return ft(val)
            elif field_type in cls._field_encoders:
                def decoder(_, ft, val): return cls._field_encoders[ft].to_python(val)
            if decoder is None:
                warnings.warn(f"Unable to decode value for '{field}: {field_type_name}'")
                return value
            cls._decode_cache[field_type] = decoder
        return decoder(field, field_type, value)

    @classmethod
    def from_dict(cls: Type[T], data: JsonDict, validate=True) -> T:
        """Returns a dataclass instance with all nested classes converted from the dict given"""
        if cls is JsonSchemaMixin:
            raise NotImplementedError

        init_values: Dict[str, Any] = {}
        non_init_values: Dict[str, Any] = {}
        if validate:
            try:
                validator.validate(data, cls.json_schema())
            except validator.ValidationError as e:
                raise ValidationError(str(e)) from e

        for field, target_field in cls._get_fields():
            values = init_values if field.init else non_init_values
            if target_field in data or (field.default == MISSING and field.default_factory == MISSING):  # type: ignore
                values[field.name] = cls._decode_field(field.name, field.type, data.get(target_field))

        # Need to ignore the type error here, since mypy doesn't know that subclasses are dataclasses
        instance = cls(**init_values)  # type: ignore
        for field_name, value in non_init_values.items():
            setattr(instance, field_name, value)
        return instance

    @staticmethod
    def _is_json_schema_subclass(field_type) -> bool:
        return issubclass_safe(field_type, JsonSchemaMixin)

    @classmethod
    def _get_field_schema(cls, field: Union[Field, Type], schema_type: SchemaType) -> Tuple[JsonDict, bool]:
        field_schema: JsonDict = {'type': 'object'}
        required = True
        default = None
        description = None
        if isinstance(field, Field):
            field_type = field.type
            default_value = None
            if field.default is not MISSING and field.default is not None:
                # In case of default value given
                default_value = field.default
            elif field.default_factory is not MISSING and field.default_factory is not None:  # type: ignore
                # In case of a default factory given, we call it
                default_value = field.default_factory()  # type: ignore

            if default_value is not None:
                default = cls._encode_field(field.type, default_value, omit_none=False)
                required = False
            if field.metadata is not None and "description" in field.metadata:
                description = field.metadata["description"]
        else:
            field_type = field
        field_type_name = cls._get_field_type_name(field_type)
        ref_path = '#/components/schemas' if schema_type == SchemaType.SWAGGER_V3 else '#/definitions'
        if cls._is_json_schema_subclass(field_type):
            field_schema = {'$ref': '{}/{}'.format(ref_path, field_type_name)}
        else:
            # If is optional[...]
            if is_optional(field_type):
                field_schema = cls._get_field_schema(field_type.__args__[0], schema_type)[0]
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

                # If embedding into a swagger spec add the enum name as an extension.
                # Note: Unlike swagger, JSON schema does not support extensions
                if schema_type in (SchemaType.SWAGGER_V2, SchemaType.SWAGGER_V3):
                    field_schema['x-enum-name'] = field_type_name
            elif field_type_name == 'Union':
                if schema_type == SchemaType.SWAGGER_V2:
                    raise TypeError('Type unions unsupported in Swagger 2.0')
                field_schema = {
                    'oneOf': [cls._get_field_schema(variant, schema_type)[0] for variant in field_type.__args__]
                }
            elif field_type_name in ('Dict', 'Mapping'):
                field_schema = {'type': 'object'}
                if field_type.__args__[1] is not Any:
                    field_schema['additionalProperties'] = cls._get_field_schema(
                        field_type.__args__[1], schema_type
                    )[0]
            elif field_type_name in ('Sequence', 'List') or (field_type_name == "Tuple" and ... in field_type.__args__):
                field_schema = {'type': 'array'}
                if field_type.__args__[0] is not Any:
                    field_schema['items'] = cls._get_field_schema(field_type.__args__[0], schema_type)[0]
            elif field_type_name == "Tuple":
                tuple_len = len(field_type.__args__)
                # TODO: How do we handle Optional type within lists / tuples
                field_schema = {
                    'type': 'array', 'minItems': tuple_len, 'maxItems': tuple_len,
                    'items': [cls._get_field_schema(type_arg, schema_type)[0] for type_arg in field_type.__args__]
                }
            elif field_type in JSON_ENCODABLE_TYPES:
                field_schema.update(JSON_ENCODABLE_TYPES[field_type])
            elif field_type in cls._field_encoders:
                field_schema.update(cls._field_encoders[field_type].json_schema)
            elif hasattr(field_type, '__supertype__'):  # NewType fields
                field_schema, _ = cls._get_field_schema(field_type.__supertype__, schema_type)
            else:
                warnings.warn(f"Unable to create schema for '{field_type_name}'")

        if default is not None:
            field_schema['default'] = default
        if description is not None:
            field_schema['description'] = description

        return field_schema, required

    @classmethod
    def _get_field_definitions(cls, field_type: Any, definitions: JsonDict,
                               schema_type: SchemaType):
        field_type_name = cls._get_field_type_name(field_type)
        if is_optional(field_type) or field_type_name in ('Sequence', 'List', 'Tuple'):
            cls._get_field_definitions(field_type.__args__[0], definitions, schema_type)
        elif field_type_name in ('Dict', 'Mapping'):
            cls._get_field_definitions(field_type.__args__[1], definitions, schema_type)
        elif field_type_name == 'Union':
            for variant in field_type.__args__:
                cls._get_field_definitions(variant, definitions, schema_type)
        elif cls._is_json_schema_subclass(field_type):
            # Prevent recursion from forward refs & circular type dependencies
            if field_type.__name__ not in definitions:
                definitions[field_type.__name__] = None
                definitions.update(field_type.json_schema(embeddable=True, schema_type=schema_type))

    @classmethod
    def all_json_schemas(cls, schema_type: SchemaType = SchemaType.DRAFT_06) -> JsonDict:
        """Returns JSON schemas for all subclasses"""
        definitions = {}
        for subclass in cls.__subclasses__():
            if is_dataclass(subclass):
                definitions.update(subclass.json_schema(embeddable=True, schema_type=schema_type))
            else:
                definitions.update(subclass.all_json_schemas(schema_type=schema_type))
        return definitions

    @classmethod
    def json_schema(cls, embeddable: bool = False, schema_type: SchemaType = SchemaType.DRAFT_06, **kwargs) -> JsonDict:
        """Returns the JSON schema for the dataclass, along with the schema of any nested dataclasses
        within the 'definitions' field.

        Enable the embeddable flag to generate the schema in a format for embedding into other schemas
        or documents supporting JSON schema such as Swagger specs.

        If embedding the schema into a swagger api, specify 'swagger_version' to generate a spec compatible with that
        version.
        """
        if 'swagger_version' in kwargs and kwargs['swagger_version'] is not None:
            schema_type = kwargs['swagger_version']

        if cls is JsonSchemaMixin:
            warnings.warn(
                "Calling 'JsonSchemaMixin.json_schema' is deprecated. Use 'JsonSchemaMixin.all_json_schemas' instead",
                DeprecationWarning
            )
            return cls.all_json_schemas(schema_type)

        definitions: JsonDict = {}
        if cls._definitions is None:
            cls._definitions = {schema_type: definitions}
        elif schema_type not in cls._definitions:
            cls._definitions[schema_type] = definitions
        else:
            definitions = cls._definitions[schema_type]

        if schema_type in (SchemaType.SWAGGER_V3, SchemaType.SWAGGER_V2) and not embeddable:
            schema_type = SchemaType.DRAFT_06
            warnings.warn("'Swagger schema types unsupported when 'embeddable=False', using 'SchemaType.DRAFT_06'")

        if cls._schema is not None and schema_type in cls._schema:
            schema = cls._schema[schema_type]
        else:
            properties = {}
            required = []
            for field, target_field in cls._get_fields():
                properties[target_field], is_required = cls._get_field_schema(field, schema_type)
                cls._get_field_definitions(field.type, definitions, schema_type)
                if is_required:
                    required.append(target_field)
            schema = {
                'type': 'object',
                'required': required,
                'properties': properties
            }

            # Needed for Draft 04 backwards compatibility
            if len(required) == 0:
                del schema["required"]
            if cls.__doc__:
                schema['description'] = cls.__doc__

            if cls._schema is None:
                cls._schema = {}

            cls._schema[schema_type] = schema

        if embeddable:
            return {**definitions, cls.__name__: schema}
        else:
            schema_uri = 'http://json-schema.org/draft-06/schema#'
            if schema_type == SchemaType.DRAFT_04:
                schema_uri = 'http://json-shema.org/draft-04/schema#'

            return {**schema, **{'definitions': definitions, '$schema': schema_uri}}

    @staticmethod
    def _get_field_type_name(field_type: Any) -> str:
        try:
            return field_type.__name__
        except AttributeError:
            # The types in the 'typing' module lack the __name__ attribute
            match = re.match(r'typing\.([A-Za-z]+)', str(field_type))
            return str(field_type) if match is None else match.group(1)
