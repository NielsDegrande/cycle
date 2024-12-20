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


# DIMENSIONS
COORDINATE_LENGTH = 2
MAX_WIDTH = 1280

# TIME
TWO_SECONDS = 2
FIVE_SECONDS = 5
TYPING_DELAY_MS = 12
TWO_MINUTES_IN_SECONDS = 120

# VIDEO
FRAMES_PER_SECOND = 30
