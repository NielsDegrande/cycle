"""Package init file.

Logging is configured here to ensure global scope.
"""

from configs import CONFIGS_DIRECTORY
from cycle.utils import configure_logging
from cycle.utils.constants import Extension

LOG_CONFIG_PATH = CONFIGS_DIRECTORY / f"log.{Extension.YAML}"
configure_logging(LOG_CONFIG_PATH)
