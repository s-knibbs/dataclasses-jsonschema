from typing import Optional, Type, Union, Any, List, Tuple, Dict
from datetime import datetime
from dataclasses import asdict
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


class FieldEncoder:
    """Base class for encoding fields to and from JSON encodable values"""

    def to_wire(self, value: Any) -> JsonEncodable:
        raise NotImplemented

    def to_python(self, value: JsonEncodable) -> Any:
        raise NotImplemented

    @property
    def json_schema(self) -> JsonDict:
        raise NotImplemented


class DateTimeFieldEncoder(FieldEncoder):
    """Encodes datetimes to isoformat"""

    def to_wire(self, value: datetime) -> str:
        return value.isoformat()

    def to_python(self, value: JsonEncodable) -> datetime:
        assert isinstance(value, str)
        return parse(value)

    @property
    def json_schema(self) -> JsonDict:
        return {"type": "string", "format": "date-time"}


class JsonSchemaMixin:
    """Mixin which adds methods to generate a JSON schema and
    convert to and from JSON encodable dicts with validation against the schema
    """
    field_encoders: Dict[Type, FieldEncoder] = {datetime: DateTimeFieldEncoder()}

    # Cache of the gernerated schema
    schema: Optional[JsonDict] = None
    definitions: Optional[JsonDict] = None

    @classmethod
    def register_field_encoders(cls, field_encoders: Dict[Type, FieldEncoder]):
        """Registers additional custom field encoders. If called on the base, these are added globally.

        The DateTimeFieldEncoder is included by default.
        """
        if cls is not JsonSchemaMixin:
            cls.field_encoders = {**cls.field_encoders, **field_encoders}
        else:
            cls.field_encoders.update(field_encoders)

    def to_dict(self, omit_none: bool = True, validate: bool = False) -> JsonDict:
        """Converts the dataclass instance to a JSON encodable dict, with optional JSON schema validation.
        Uses the asdict function internally to recursively convert all nested data structures.

        If omit_none (default True) is specified, any items with value None are removed
        """

        def _to_dict_inner(items: List[Tuple[str, Any]]) -> JsonDict:
            out = {}
            for key, value in items:
                if value is None and omit_none:
                    continue
                if type(value) in self.field_encoders:
                    out[key] = self.field_encoders[type(value)].to_wire(value)
                else:
                    out[key] = value
            return out

        data = asdict(self, dict_factory=_to_dict_inner)
        if validate:
            schema_validate(data, self.json_schema())
        return data

    @classmethod
    def _decode_field(cls, field: str, field_type: Any, value: Any):
        if type(value) in JSON_ENCODABLE_TYPES:
            return value

        # Replace any nested dictionaries with their targets
        if hasattr(field_type, 'from_dict'):
            return field_type.from_dict(value)
        if str(type(field_type)) == 'typing.Union' and issubclass(field_type.__args__[1], type(None)):
            return cls._decode_field(field, field_type.__args__[0], value)
        if field_type.__name__ in ('Mapping', 'Dict'):
            return {key: cls._decode_field(field, field_type.__args__[1], val) for key, val in value.items()}
        if field_type.__name__ in ('Sequence', 'List'):
            return [cls._decode_field(field, field_type.__args__[0], val) for val in value]

        if type(value) in cls.field_encoders:
            return cls.field_encoders[type(value)].to_python(value)

        warnings.warn(f"Unable to decode value for '{field}: {field_type.__name__}'")
        return value

    @classmethod
    def from_dict(cls: Any, data: JsonDict, validate=True) -> Any:
        """Returns a dataclass instance with all nested classes converted from the dict given"""
        decoded_data = {}
        if validate:
            schema_validate(data, cls.json_schema())
        for field, field_type in cls.__annotations__.items():
            decoded_data[field] = cls._decode_field(field, field_type, data.get(field))
        return cls(**decoded_data)

    @classmethod
    def _get_field_schema(cls, field_type):
        field_schema = {}
        required = True
        if hasattr(field_type, 'json_schema'):
            field_schema = {
                'type': 'object',
                '$ref': '#/definitions/{}'.format(field_type.__name__)
            }
        else:
            # If is optional[...]
            if str(type(field_type)) == 'typing.Union' and issubclass(field_type.__args__[1], type(None)):
                field_schema = cls._get_field_schema(field_type.__args__[0])[0]
                required = False
            elif field_type.__name__ in ('Dict', 'Mapping'):
                field_schema = {
                    'type': 'object',
                    'additionalProperties': cls._get_field_schema(field_type.__args__[1])[0]
                }
            elif field_type.__name__ in ('Sequence', 'List'):
                field_schema = {'type': 'array', 'items': cls._get_field_schema(field_type.__args__[0])[0]}
            elif field_type in JSON_ENCODABLE_TYPES:
                field_schema = JSON_ENCODABLE_TYPES[field_type]
            else:
                field_schema.update(cls.field_encoders[field_type].json_schema)
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
        schema: JsonDict = {}
        if cls is JsonSchemaMixin:
            for subclass in cls.__subclasses__():
                definitions.update(subclass.json_schema(embeddable=True))
            return definitions

        if cls.schema is not None and cls.definitions is not None:
            schema = cls.schema
            definitions = cls.definitions
        else:
            properties = {}
            required = []
            for field, field_type in cls.__annotations__.items():
                properties[field], is_required = cls._get_field_schema(field_type)
                item_type = field_type
                # Note Optional is represented by Union[Type, None]
                if str(type(field_type)) == 'typing.Union' and issubclass(field_type.__args__[1], type(None)):
                    item_type = field_type.__args__[0]
                elif field_type.__name__ in ('Dict', 'Mapping'):
                    item_type = field_type.__args__[1]
                elif field_type.__name__ in ('Sequence', 'List'):
                    item_type = field_type.__args__[0]
                if hasattr(item_type, 'json_schema'):
                    definitions.update(item_type.json_schema(embeddable=True))
                if is_required:
                    required.append(field)
            schema = {
                'type': 'object',
                'required': required,
                'properties': properties
            }
            if cls.__doc__:
                schema['description'] = cls.__doc__
            cls.schema = schema
            cls.definitions = definitions

        if embeddable:
            return {**definitions, cls.__name__: schema}
        else:
            return {**schema, **{
                'definitions': definitions,
                '$schema': 'http://json-schema.org/draft-04/schema#'
            }}
