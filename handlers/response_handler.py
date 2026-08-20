from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any

from parsers.command_parser import (
    CommandParseError,
    parse_command,
)
from parsers.command_parser import (
    ActivityConfig,
)


@dataclass(frozen=True)
class ParsedResponse:
    """
    Normalized activity command extracted from a Plurk realtime event.

    response_id:
        - int for a command coming from a Plurk response.
        - None for a command coming from a new Plurk.
    """

    user_id: int
    plurk_id: int
    response_id: int | None
    content_raw: str
    config: ActivityConfig


# ------------------------------------------------------
# Public entry point
# ------------------------------------------------------


def handle_realtime_event(
    event: dict[str, Any],
    bot_name: str = "AI_Anchor",
) -> list[ParsedResponse]:
    """
    Parse one Plurk realtime payload.

    Supported command sources:
        - new_plurk
        - new_response

    Other realtime events are ignored.

    The command parser remains responsible for:
        - validating the @bot mention
        - removing the mention
        - parsing the actual command
        - validating activity parameters
    """

    if not isinstance(event, dict):
        return []

    data = event.get("data")

    if not isinstance(data, list):
        return []

    results: list[ParsedResponse] = []

    for item in data:
        parsed = _parse_event_item(
            item,
            bot_name=bot_name,
        )

        if parsed is not None:
            results.append(parsed)

    return results


# ------------------------------------------------------
# Event classification
# ------------------------------------------------------


def _parse_event_item(
    item: Any,
    bot_name: str,
) -> ParsedResponse | None:
    """
    Classify and parse one realtime data item.

    new_response is checked first because it contains a nested
    "response" object.
    """

    if not isinstance(item, dict):
        return None

    if isinstance(item.get("response"), dict):
        return _parse_new_response(
            item,
            bot_name,
        )

    if _looks_like_new_plurk(item):
        return _parse_new_plurk(
            item,
            bot_name,
        )

    return None


def _looks_like_new_plurk(
    item: dict[str, Any],
) -> bool:
    """
    Identify a new Plurk payload without relying on an explicit
    event-type field.

    A normal new Plurk carries content plus user and Plurk IDs.
    """

    has_content = (
        isinstance(
            item.get("content_raw"),
            str,
        )
        or isinstance(
            item.get("content"),
            str,
        )
    )

    has_user_id = (
        isinstance(
            item.get("user_id"),
            int,
        )
        or isinstance(
            item.get("owner_id"),
            int,
        )
    )

    has_plurk_id = (
        isinstance(
            item.get("plurk_id"),
            int,
        )
        or isinstance(
            item.get("id"),
            int,
        )
    )

    return (
        has_content
        and has_user_id
        and has_plurk_id
    )


# ------------------------------------------------------
# New Plurk
# ------------------------------------------------------


def _parse_new_plurk(
    item: dict[str, Any],
    bot_name: str,
) -> ParsedResponse | None:
    """Parse a command from a newly-created Plurk."""

    content_raw = _get_content(item)

    if not content_raw:
        return None

    normalized_content = _strip_html(
        content_raw
    ).strip()

    if not _has_expected_bot_mention(
        normalized_content,
        bot_name,
    ):
        return None

    user_id = _get_user_id(item)
    plurk_id = _get_plurk_id(item)

    if user_id is None or plurk_id is None:
        return None

    config = _parse_command_content(
        normalized_content,
        bot_name,
    )

    if config is None:
        return None

    return ParsedResponse(
        user_id=user_id,
        plurk_id=plurk_id,
        response_id=None,
        content_raw=normalized_content,
        config=config,
    )


# ------------------------------------------------------
# New Response
# ------------------------------------------------------


def _parse_new_response(
    item: dict[str, Any],
    bot_name: str,
) -> ParsedResponse | None:
    """Parse a command from a newly-created response."""

    response = item.get("response")

    if not isinstance(response, dict):
        return None

    content_raw = _get_content(response)

    if not content_raw:
        return None

    normalized_content = _strip_html(
        content_raw
    ).strip()

    if not _has_expected_bot_mention(
        normalized_content,
        bot_name,
    ):
        return None

    user_id = _get_user_id(response)
    plurk_id = _get_plurk_id(item)
    response_id = _get_response_id(response)

    if (
        user_id is None
        or plurk_id is None
        or response_id is None
    ):
        return None

    config = _parse_command_content(
        normalized_content,
        bot_name,
    )

    if config is None:
        return None

    return ParsedResponse(
        user_id=user_id,
        plurk_id=plurk_id,
        response_id=response_id,
        content_raw=normalized_content,
        config=config,
    )


# ------------------------------------------------------
# Command parser bridge
# ------------------------------------------------------


def _parse_command_content(
    content_raw: str,
    bot_name: str,
) -> ActivityConfig | None:
    """
    Pass the COMPLETE command text to command_parser.

    Example:
        @AI_Anchor 開始

    command_parser itself removes @AI_Anchor and parses the
    remaining command.
    """

    try:
        return parse_command(
            content_raw,
            bot_name=bot_name,
        )

    except (
        CommandParseError,
        ValueError,
        TypeError,
    ):
        return None


# ------------------------------------------------------
# Mention handling
# ------------------------------------------------------


def _has_expected_bot_mention(
    content: str,
    bot_name: str,
) -> bool:
    """
    Check whether the command starts with the bot mention.

    This deliberately follows command_parser's contract:
        ^@<bot_name>\\s*

    The actual parsing is still delegated to command_parser.
    """

    pattern = (
        rf"^@{re.escape(bot_name)}\s*"
    )

    return (
        re.match(
            pattern,
            content,
        )
        is not None
    )


# ------------------------------------------------------
# Content normalization
# ------------------------------------------------------


def _strip_html(
    content: str,
) -> str:
    """
    Remove simple HTML tags and decode HTML entities.

    Plurk may expose HTML in content fields. The parser receives
    normalized text rather than HTML markup.
    """

    text = re.sub(
        r"<[^>]*>",
        "",
        content,
    )

    return unescape(text)


def _get_content(
    item: dict[str, Any],
) -> str | None:
    """Get raw content from a Plurk event object."""

    content_raw = item.get(
        "content_raw"
    )

    if isinstance(
        content_raw,
        str,
    ):
        return content_raw

    content = item.get("content")

    if isinstance(
        content,
        str,
    ):
        return content

    return None


# ------------------------------------------------------
# ID extraction
# ------------------------------------------------------


def _get_user_id(
    item: dict[str, Any],
) -> int | None:
    """
    Extract the user ID.

    Supported fields:
        - user_id
        - owner_id
    """

    value = item.get("user_id")

    if isinstance(
        value,
        int,
    ):
        return value

    value = item.get("owner_id")

    if isinstance(
        value,
        int,
    ):
        return value

    return None


def _get_plurk_id(
    item: dict[str, Any],
) -> int | None:
    """
    Extract the Plurk ID.

    Supported fields:
        - plurk_id
        - id
    """

    value = item.get("plurk_id")

    if isinstance(
        value,
        int,
    ):
        return value

    value = item.get("id")

    if isinstance(
        value,
        int,
    ):
        return value

    return None


def _get_response_id(
    response: dict[str, Any],
) -> int | None:
    """
    Extract the response ID.

    Supported fields:
        - id
        - response_id
    """

    value = response.get("id")

    if isinstance(
        value,
        int,
    ):
        return value

    value = response.get(
        "response_id"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    return None
