"""Collection classes for managing multiple tools."""

from typing import Any, Self

from anthropic.types.beta import BetaToolUnionParam

from .base import (
    BaseAnthropicTool,
    ToolError,
    ToolFailure,
    ToolResult,
)


class ToolCollection:
    """A collection of anthropic-defined tools."""

    def __init__(self: Self, *tools: BaseAnthropicTool) -> None:
        """Initialize the ToolCollection with a list of tools.

        :param tools: A variable number of BaseAnthropicTool instances.
        """
        self.tools = tools
        self.tool_map = {tool.to_params()["name"]: tool for tool in tools}

    def to_params(self: Self) -> list[BetaToolUnionParam]:
        """Convert the tools to their parameter representations.

        :return: A list of BetaToolUnionParam instances.
        """
        return [tool.to_params() for tool in self.tools]

    async def run(self: Self, *, name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Run a tool by name with the given input.

        :param name: The name of the tool to run.
        :param tool_input: A dictionary of input parameters for the tool.
        :return: A ToolResult instance.
        """
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            return await tool(**tool_input)
        except ToolError as e:
            return ToolFailure(error=e.message)
