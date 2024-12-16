"""Package entry point."""

import argparse
import logging

from dotenv import load_dotenv

from configs import CONFIGS_DIRECTORY
from cycle.utils import load_config
from cycle.utils.constants import Extension


def _parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments.

    :return: Parsed arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        help="""
        Global config to be loaded.
        Multiple values can be provided, separated by spaces.
        """,
        nargs="+",
        required=False,
        default=["config"],
    )
    # TODO: Add config override.
    return parser.parse_args()


def main() -> None:
    """Run a pipeline."""
    log_ = logging.getLogger(__name__)

    arguments = _parse_cli_args()

    log_.info("Load configuration.")
    load_dotenv()
    configs = [
        CONFIGS_DIRECTORY / f"{config}.{Extension.YAML}"
        for config in [*arguments.config]
    ]
    config = load_config(configs)
    # TODO: Do something.
    log_.info(config)


if __name__ == "__main__":
    main()
