"""Utility functions for working with strings."""

from cycle.utils.constants import Extension


def split_on_separator(text: str, separator: str) -> list[str]:
    """Split a string on a separator.

    :param text: Text to split.
    :param separator: Separator to split on.
    :return: List of parts.
    """
    # Remove empty parts.
    return [part for part in text.split(separator) if part]


def change_video_to_text_extension(file_name: str) -> str:
    """Change the extension of a video file to text.

    :param file_name: Filename of the video file.
    :return: Filename with the extension changed to text.
    """
    return file_name.replace(Extension.MP4, Extension.TXT)
