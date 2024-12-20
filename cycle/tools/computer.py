"""Anthropic tool for interacting with the computer's screen, keyboard, and mouse."""

import asyncio
import base64
import io
import logging
from enum import StrEnum
from typing import Literal, Self, TypedDict

import pyautogui
from anthropic.types.beta import BetaToolComputerUse20241022Param

from cycle.utils.constants import COORDINATE_LENGTH, MAX_WIDTH, TYPING_DELAY_MS

from .base import BaseAnthropicTool, ToolError, ToolResult

log_ = logging.getLogger(__name__)

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]


class ScalingSource(StrEnum):
    """An enumeration of scaling sources for coordinates."""

    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    """A dictionary containing the options for the computer tool."""

    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    """Split a string into chunks of a specified size.

    :param s: The string to be split.
    :param chunk_size: The size of each chunk.
    :return: A list of string chunks.
    """
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class ComputerTool(BaseAnthropicTool):
    """Allow the agent to interact with the screen, keyboard, and mouse.

    The tool parameters are defined by Anthropic and are not editable.
    """

    name: Literal["computer"] = "computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int
    height: int
    display_num: int | None

    _screenshot_delay: float = 1.0
    _scaling_enabled: bool = True

    @property
    def options(self: Self) -> ComputerToolOptions:
        """Return the options for the computer tool.

        :return: A dictionary containing the display width, height, and number.
        """
        return {
            "display_width_px": self.target_width,
            "display_height_px": self.target_height,
            "display_number": self.display_num,
        }

    def to_params(self: Self) -> BetaToolComputerUse20241022Param:
        """Convert the tool options to parameters for the API.

        :return: A dictionary of parameters.
        """
        return {"name": self.name, "type": self.api_type, **self.options}

    def __init__(self: Self) -> None:
        """Initialize the ComputerTool instance."""
        super().__init__()

        self.width = int(pyautogui.size()[0])
        self.height = int(pyautogui.size()[1])

        self.display_num = None  # Not used on MacOS

        if self.width > MAX_WIDTH:
            self.scale_factor = MAX_WIDTH / self.width
            self.target_width = MAX_WIDTH
            self.target_height = int(self.height * self.scale_factor)
        else:
            self.scale_factor = 1.0
            self.target_width = self.width
            self.target_height = self.height

    async def __call__(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self: Self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: list[int] | None = None,
        **kwargs: dict,
    ) -> ToolResult:
        """Perform the specified action using the computer tool.

        :param action: The action to be performed.
        :param text: The text to be typed or the key combination to be pressed.
        :param coordinate: The coordinates for mouse actions.
        :return: The result of the action.
        :raises ToolError: If the action or parameters are invalid.
        """
        _ = kwargs  # Unused.
        log_.info(
            "### Performing action: %s%s%s",
            action,
            f", text: {text}" if text else "",
            f", coordinate: {coordinate}" if coordinate else "",
        )
        if action in ("mouse_move", "left_click_drag"):
            error_message: str
            if coordinate is None:
                error_message = f"Coordinate is required for {action}."
                raise ToolError(error_message)
            if text is not None:
                error_message = f"Text is not accepted for {action}."
                raise ToolError(error_message)
            if not isinstance(coordinate, list) or len(coordinate) != COORDINATE_LENGTH:
                error_message = "Coordinate must be a list of length 2."
                raise ToolError(error_message)
            if not all(isinstance(i, int) and i >= 0 for i in coordinate):
                error_message = "Coordinate must be a list of non-negative integers."
                raise ToolError(error_message)

            x, y = self._scale_coordinates(
                ScalingSource.API,
                coordinate[0],
                coordinate[1],
            )

            if action == "mouse_move":
                await asyncio.to_thread(pyautogui.moveTo, x, y)
                return ToolResult(output=f"Mouse moved successfully to X={x}, Y={y}")
            if action == "left_click_drag":
                await asyncio.to_thread(pyautogui.mouseDown)
                await asyncio.to_thread(pyautogui.moveTo, x, y)
                await asyncio.to_thread(pyautogui.mouseUp)
                return ToolResult(output="Mouse drag action completed.")

        if action in ("key", "type"):
            error_message: str
            if text is None:
                error_message = f"Text is required for {action}/"
                raise ToolError(error_message)
            if coordinate is not None:
                error_message = f"Coordinate is not accepted for {action}."
                raise ToolError(error_message)

            if action == "key":
                # Handle key combinations and modifiers.
                # Replace 'super' with 'command'.
                key_sequence = text.lower().replace("super", "command").split("+")
                key_sequence = [key.strip() for key in key_sequence]
                # Map 'cmd' to 'command' for MacOS.
                key_sequence = [
                    "command" if key == "cmd" else key for key in key_sequence
                ]
                # Handle special keys that pyautogui expects.
                special_keys = {
                    "ctrl": "ctrl",
                    "control": "ctrl",
                    "alt": "alt",
                    "option": "alt",
                    "shift": "shift",
                    "command": "command",
                    "tab": "tab",
                    "enter": "enter",
                    "return": "enter",
                    "esc": "esc",
                    "escape": "esc",
                    "space": "space",
                    "spacebar": "space",
                    "up": "up",
                    "down": "down",
                    "left": "left",
                    "right": "right",
                    # Add more special keys as needed.
                }
                key_sequence = [special_keys.get(key, key) for key in key_sequence]
                await asyncio.to_thread(pyautogui.hotkey, *key_sequence)
                return ToolResult(output=f"Key combination '{text}' pressed.")
            if action == "type":
                await asyncio.to_thread(
                    pyautogui.write,
                    text,
                    interval=TYPING_DELAY_MS / 1000.0,
                )
                return ToolResult(output=f"Typed text: {text}")

        if action in (
            "left_click",
            "right_click",
            "double_click",
            "screenshot",
            "cursor_position",
        ):
            error_message: str
            if text is not None:
                error_message = f"Text is not accepted for {action}."
                raise ToolError(error_message)
            if coordinate is not None:
                error_message = f"Coordinate is not accepted for {action}."
                raise ToolError(error_message)

            if action == "screenshot":
                return await self._screenshot()
            if action == "cursor_position":
                x, y = pyautogui.position()
                x, y = self._scale_coordinates(ScalingSource.COMPUTER, int(x), int(y))
                return ToolResult(output=f"X={x}, Y={y}")
            if action == "left_click":
                await asyncio.to_thread(pyautogui.click, button="left")
                return ToolResult(output="Left click performed.")
            if action == "right_click":
                await asyncio.to_thread(pyautogui.click, button="right")
                return ToolResult(output="Right click performed.")
            if action == "double_click":
                await asyncio.to_thread(pyautogui.doubleClick)
                return ToolResult(output="Double click performed.")

        error_message = f"Invalid action: {action}."
        raise ToolError(error_message)

    async def _screenshot(self: Self) -> ToolResult:
        """Take a screenshot of the current screen and return the base64 encoded image.

        :return: The result containing the base64 encoded screenshot.
        """
        # Capture screenshot using PyAutoGUI.
        screenshot = await asyncio.to_thread(pyautogui.screenshot)

        if self._scaling_enabled and self.scale_factor < 1.0:
            screenshot = screenshot.resize((self.target_width, self.target_height))

        img_buffer = io.BytesIO()
        # Save the image to an in-memory buffer.
        screenshot.save(img_buffer, format="PNG", optimize=True)
        img_buffer.seek(0)
        base64_image = base64.b64encode(img_buffer.read()).decode()

        return ToolResult(base64_image=base64_image)

    def _scale_coordinates(
        self: Self,
        source: ScalingSource,
        x: int,
        y: int,
    ) -> tuple[int, int]:
        """Scale coordinates from assistant's coordinate system to real screen.

        :param source: The source of the coordinates (API or COMPUTER).
        :param x: The x-coordinate.
        :param y: The y-coordinate.
        :return: The scaled coordinates.
        """
        if not self._scaling_enabled:
            return x, y
        x_scaling_factor = self.width / self.target_width
        y_scaling_factor = self.height / self.target_height
        if source == ScalingSource.API:
            # Assistant's coordinates -> real screen coordinates.
            return round(x * x_scaling_factor), round(y * y_scaling_factor)
        # Real screen coordinates -> assistant's coordinate system.
        return round(x / x_scaling_factor), round(y / y_scaling_factor)
