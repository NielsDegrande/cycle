"""Keep constant values separate from other code."""

from enum import StrEnum, auto


class Extension(StrEnum):
    """File extensions."""

    YAML = auto()
