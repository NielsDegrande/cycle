"""Automate the execution of a workflow with Computer Use."""

import base64
import json
import logging
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import tenacity
from anthropic import Anthropic, APIResponse
from anthropic._legacy_response import LegacyAPIResponse
from anthropic.types import (
    ToolResultBlockParam,
)
from anthropic.types.beta import (
    BetaContentBlock,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from box import Box

from cycle.tools.base import ToolResult
from cycle.tools.collection import ToolCollection
from cycle.tools.computer import ComputerTool
from cycle.utils.constants import PromptType
from cycle.utils.prompts import get_hydrated_prompt

log_ = logging.getLogger(__name__)


def output_callback(content_block: BetaContentBlock) -> None:
    """Handle the output callback.

    :param content_block: The content block to process.
    """
    if isinstance(content_block, dict) and content_block.get("type") == "text":
        log_.info("Assistant: %s", content_block.get("text"))


def tool_output_callback(
    screenshot_directory: Path,
    result: ToolResult,
    tool_use_id: str,
) -> None:
    """Handle the tool output callback.

    :param screenshot_directory: The directory to save the screenshot.
    :param result: The result from the tool.
    :param tool_use_id: The ID of the tool use.
    """
    if result.output:
        log_.info("> Tool Output [%s]: %s", tool_use_id, result.output)
    if result.error:
        log_.info("!!! Tool Error [%s]: %s", tool_use_id, result.error)
    if result.base64_image:
        screenshot_directory.mkdir(exist_ok=True)
        save_path = screenshot_directory / f"screenshot_{tool_use_id}.png"
        image_data = result.base64_image
        with save_path.open("wb") as file_:
            file_.write(base64.b64decode(image_data))
        log_.info("Took screenshot screenshot_%s.png", tool_use_id)


def api_response_callback(response: APIResponse[BetaMessage]) -> None:
    """Handle the API response callback.

    :param response: The API response to process.
    """
    log_.info(
        "\n---------------\nAPI Response:\n%s\n",
        json.dumps(
            json.loads(str(response.text))["content"],
            indent=4,
        ),
    )


def _filter_to_n_most_recent_images(
    messages: list[BetaMessageParam],
    images_to_keep: int,
) -> None:
    """Remove images from messages to keep only the most recent.

    :param messages: The messages to filter.
    :param images_to_keep: The number of images to keep.
    """
    tool_result_blocks = cast(
        list[ToolResultBlockParam],
        [
            item
            for message in messages
            for item in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ],
    )

    total_images = sum(
        1
        for tool_result in tool_result_blocks
        for content in tool_result.get("content", [])
        if isinstance(content, dict) and content.get("type") == "image"
    )
    images_to_remove = total_images - images_to_keep
    for tool_result in tool_result_blocks:
        if isinstance(tool_result.get("content"), list):
            new_content = []
            for content in tool_result.get("content", []):
                if (
                    isinstance(content, dict)
                    and content.get("type") == "image"
                    and images_to_remove > 0
                ):
                    images_to_remove -= 1
                    continue
                new_content.append(content)
            tool_result["content"] = new_content


def _prepend_system_tool_result(result: ToolResult, result_text: str) -> str:
    """Prepend the system to the tool result text.

    :param result: The tool result.
    :param result_text: The tool result text.
    :return: The tool result text with the system prepended.
    """
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text


def _make_api_tool_result(
    result: ToolResult,
    tool_use_id: str,
) -> BetaToolResultBlockParam:
    """Convert an agent ToolResult to an API ToolResultBlockParam.

    :param result: The tool result.
    :param tool_use_id: The ID of the tool use.
    :return: The API tool result block.
    """
    tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
    is_error = False
    if result.error:
        is_error = True
        tool_result_content = _prepend_system_tool_result(result, result.error)
    else:
        if result.output:
            tool_result_content.append(
                {
                    "type": "text",
                    "text": _prepend_system_tool_result(result, result.output),
                },
            )
        if result.base64_image:
            tool_result_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                },
            )
    return {
        "type": "tool_result",
        "content": tool_result_content,
        "tool_use_id": tool_use_id,
        "is_error": is_error,
    }


@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=8),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
def _create_with_retries(  # noqa: PLR0913
    client: Anthropic,
    max_tokens: int,
    messages: list[BetaMessageParam],
    model: str,
    system: str,
    tool_collection: ToolCollection,
) -> LegacyAPIResponse[BetaMessage]:
    """Create the Anthropic message with retries on internal errors.

    :param client: The Anthropic client.
    :param max_tokens: The maximum tokens to generate.
    :param messages: The list of message parameters.
    :param model: The model name.
    :param system: The system prompt.
    :param tool_collection: The tool collection.
    :return: The API response.
    """
    return client.beta.messages.with_raw_response.create(
        max_tokens=max_tokens,
        messages=messages,
        model=model,
        system=system,
        tools=tool_collection.to_params(),
        betas=["computer-use-2024-10-22"],
    )


async def automate_workflow(config: Box, transcript: str, instruction: str) -> None:
    """Automate the execution of a workflow with Computer Use.

    :param config: The configuration for the workflow automation.
    :param transcript: The transcript of the workflow to automate.
    :param instruction: The instruction for the workflow.
    """
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)
    images_to_keep = config.images_to_keep_in_history
    max_tokens = config.max_tokens
    model: str = config.models.computer_use
    tool_collection = ToolCollection(
        ComputerTool(),
    )

    messages: list[BetaMessageParam] = [
        {
            "role": "user",
            # TODO: Engineer this way more.
            "content": "Repeat the workflow considering the user instruction.",
        },
    ]

    while True:
        _filter_to_n_most_recent_images(
            messages,
            images_to_keep,
        )

        hydrated_system_prompt = get_hydrated_prompt(
            template_name="computer_use",
            prompt_type=PromptType.SYSTEM,
            template_kwargs={
                "architecture": platform.machine(),
                "datetime": datetime.now().strftime("%A, %B %-d, %Y"),  # noqa: DTZ005
                "workflow_instructions": transcript,
                "user_instruction": instruction,
            },
        )
        raw_response = _create_with_retries(
            client=client,
            max_tokens=max_tokens,
            messages=messages,
            model=model,
            system=hydrated_system_prompt,
            tool_collection=tool_collection,
        )
        api_response_callback(cast(APIResponse[BetaMessage], raw_response))
        response = raw_response.parse()
        if (
            response
            and response.content
            and response.content[-1].input  # type: ignore[attr-defined]
            and response.content[-1].input.get("action") != "screenshot"  # type: ignore[attr-defined]
        ):
            response.content.append(
                BetaToolUseBlock(
                    id=f"screenshot_{datetime.now().strftime('%Y%m%d%H%M%S')}",  # noqa: DTZ005
                    name="computer",
                    type="tool_use",
                    input={"action": "screenshot"},
                ),
            )

        messages.append(
            {
                "role": "assistant",
                "content": cast(list[BetaContentBlockParam], response.content),
            },
        )

        tool_result_content: list[BetaToolResultBlockParam] = []
        for content_block in cast(list[BetaContentBlock], response.content):
            output_callback(content_block)
            if content_block.type == "tool_use":
                result = await tool_collection.run(
                    name=content_block.name,
                    tool_input=cast(dict[str, Any], content_block.input),
                )
                tool_result_content.append(
                    _make_api_tool_result(result, content_block.id),
                )
                tool_output_callback(
                    Path(config.directories.screenshots),
                    result,
                    content_block.id,
                )

        # Terminate loop.
        if not tool_result_content:
            return

        messages.append(
            {
                "content": tool_result_content,
                "role": "user",
            },
        )
