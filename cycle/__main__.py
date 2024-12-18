"""Package entry point."""

import logging

from dotenv import load_dotenv

from configs import CONFIGS_DIRECTORY
from cycle.app import CycleApp
from cycle.utils.config import load_config
from cycle.utils.constants import Extension


def main() -> None:
    """Run a pipeline."""
    log_ = logging.getLogger(__name__)

    log_.info("Load configuration.")
    load_dotenv()
    config = load_config([CONFIGS_DIRECTORY / f"config.{Extension.YAML}"])
    CycleApp(config)


if __name__ == "__main__":
    main()
