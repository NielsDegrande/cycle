"""Utility functions for working with prompts."""

from pathlib import Path

from jinja2 import Environment, StrictUndefined

from cycle.utils.constants import Extension, PromptType
from prompts import PROMPTS_DIRECTORY


def get_hydrated_prompt(
    template_name: str,
    prompt_type: PromptType,
    template_kwargs: dict | None = None,
) -> str:
    """Hydrate prompt with provided kwargs.

    :param template_name: Reference to the template name.
    :param prompt_type: Type of prompt to hydrate.
    :param template_kwargs: Key-value pairs to hydrate the prompt with.
    :return: Hydrated prompt.
    """
    template_path = (
        PROMPTS_DIRECTORY / f"{template_name}_{prompt_type.value}.{Extension.JINJA2}"
    )
    with Path.open(template_path) as file:
        template = file.read()

    # Initialize the Jinja2 environment.
    # Raise error upon undefined characters and do NOT escape special characters.
    environment = Environment(undefined=StrictUndefined, autoescape=False)  # noqa: S701

    # Render the Jinja2 template.
    jinja_template = environment.from_string(template)
    return jinja_template.render(**(template_kwargs or {}))
