"""Transcribe recordings to workflows using a multi-modal model."""

import json
import logging
import os
from time import sleep

from box import Box
from google import genai
from google.genai import types

from cycle.utils.constants import FIVE_SECONDS, Extension, PromptType
from cycle.utils.prompts import get_hydrated_prompt
from prompts import PROMPTS_DIRECTORY

log_ = logging.getLogger(__name__)


def transcribe_recording(config: Box, file_name: str) -> str:
    """Transcribe a recording to a workflow.

    :param config: Configuration settings.
    :param file_name: Filename of the recording.
    :return: Transcription of the recording.
    """
    log_.info("Started recording transcription for: %s.", file_name)
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
    )

    # Hydrate prompts.
    computer_use_specification_path = (
        PROMPTS_DIRECTORY / f"computer_use_specification.{Extension.JSON}"
    )
    computer_use_specification = json.load(computer_use_specification_path.open())
    hydrated_system_prompt = get_hydrated_prompt(
        template_name="transcribe_recording",
        prompt_type=PromptType.SYSTEM,
        template_kwargs={
            "computer_use_specification": json.dumps(computer_use_specification),
            "separator": config.separator,
        },
    )
    log_.info("Hydrated system prompt:\n%s.", hydrated_system_prompt)

    # Upload screen recording.
    screen_recording = client.files.upload(
        path=file_name,
    )
    if not (screen_recording.name and screen_recording.uri):
        upload_failed_message = "Screen recording upload failed."
        raise ValueError(upload_failed_message)

    is_active = False
    while not is_active:
        sleep(FIVE_SECONDS)
        is_active = client.files.get(name=screen_recording.name).state == "ACTIVE"

    # Call LLM and return results.
    response = client.models.generate_content(
        model=config.models.default,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=screen_recording.uri,
                        mime_type="video/mp4",
                    ),
                ],
            ),
            "Transcribe the recording to a workflow optimized for computer use.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=hydrated_system_prompt,
            temperature=0,
        ),
    )

    # Delete the uploaded file.
    client.files.delete(name=screen_recording.name)

    if not response.text:
        model_call_failed_message = f"Model response: {response}"
        raise ValueError(model_call_failed_message)

    log_.info("Finished recording transcription for: %s.", file_name)
    return response.text
