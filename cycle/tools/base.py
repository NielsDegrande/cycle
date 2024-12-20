"""Base classes for Anthropic-defined tools."""

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, fields, replace
from typing import Any, Self

from anthropic.types.beta import BetaToolUnionParam


class BaseAnthropicTool(metaclass=ABCMeta):
    """Abstract base class for Anthropic-defined tools."""

    @abstractmethod
    def __call__(self: Self, **kwargs: dict) -> Any:  # noqa: ANN401
        """Execute the tool with the given arguments."""
        ...

    @abstractmethod
    def to_params(
        self: Self,
    ) -> BetaToolUnionParam:
        """Return the parameters for the tool."""
        raise NotImplementedError


@dataclass(kw_only=True, frozen=True)
class ToolResult:
    """Represents the result of a tool execution."""

    output: str | None = None
    error: str | None = None
    base64_image: str | None = None
    system: str | None = None

    def __bool__(self: Self) -> bool:
        """Return True if the result is not empty."""
        return any(getattr(self, field.name) for field in fields(self))

    def __add__(self: Self, other: "ToolResult") -> "ToolResult":
        """Combine two ToolResults."""

        def combine_fields(
            field: str | None,
            other_field: str | None,
            *,
            concatenate: bool = True,
        ) -> str | None:
            if field and other_field:
                if concatenate:
                    return field + other_field
                error_message = "Cannot combine tool results."
                raise ValueError(error_message)
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(
                self.base64_image,
                other.base64_image,
                concatenate=False,
            ),
            system=combine_fields(self.system, other.system),
        )

    def replace(self: Self, **kwargs: dict) -> "ToolResult":
        """Return a new ToolResult with the given fields replaced."""
        return replace(self, **kwargs)


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self: Self, message: str) -> None:
        """Initialize the ToolError.

        :param message: The error message.
        """
        self.message = message
