"""Keep constant values separate from other code."""

from enum import StrEnum, auto


class Extension(StrEnum):
    """File extensions."""

    MP4 = auto()
    JINJA2 = auto()
    JSON = auto()
    TXT = auto()
    YAML = auto()


class PromptType(StrEnum):
    """Type of prompt."""

    SYSTEM = auto()
    USER = auto()


# TIME
FIVE_SECONDS = 5

# VIDEO
FRAMES_PER_SECOND = 30
