"""
This script is used to test if mypy understands that the Nullable type is always False-y.
"""

from __future__ import annotations

from dataclasses import dataclass

from dataclasses_jsonschema.type_defs import Nullable


@dataclass
class Example:
    name: Nullable[str | None] = None


example = Example("sienna")

assert example.name  # If this assert passes we know `name` is a string (because it isn't None or Nullable)

name_upper = example.name.upper()
