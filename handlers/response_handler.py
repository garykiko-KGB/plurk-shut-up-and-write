from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any

from core.activity import ActivityConfig
from core.command_parser import parse_command


@dataclass(frozen=True)
class ParsedResponse:
    """
    Normalized command extracted from a Plurk realtime event.

    response_id is None when the command came from a new Plurk
    instead of a response.
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
    Parse a Plurk realtime payload.

    Supported command sources:
        - new_plurk
        - new_response

    Ignored:
        - update_notification
        - unknown event types
        - malformed data
        - messages without the bot mention
        - messages whose command cannot be parsed
    """

    if not isinstance(event, dict):
        return []

    data = event.get("data")

    if not isinstance(data, list):
        return []

    parsed_responses: list[ParsedResponse] = []

    for item in data:
        parsed = _parse_event_item(
            item,
            bot_name=bot_name,
        )

        if parsed is not None:
            parsed_responses.append(parsed)

    return parsed_responses


# ------------------------------------------------------
# Event classification
# ------------------------------------------------------


def _parse_event_item(
    item: Any,
    bot_name: str,
) -> ParsedResponse | None:
    """Classify and parse one realtime data item."""

    if not isinstance(item, dict):
        return None

    # Plurk realtime events representing a response normally
    # contain a nested "response" object.
    if isinstance(item.get("response"), dict):
        return _parse_new_response(
            item,
            bot_name,
        )

    # New Plurks contain their own content/user/plurk data.
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
    Determine whether an event item looks like a new Plurk.

    update_notification and other event types do not normally carry
    content_raw/content together with a user_id and plurk_id.
    """

    has_content = (
        isinstance(item.get("content_raw"), str)
        or isinstance(item.get("content"), str)
    )

    has_user = (
        isinstance(item.get("user_id"), int)
        or isinstance(item.get("owner_id"), int)
    )

    has_plurk = (
        isinstance(item.get("plurk_id"), int)
        or isinstance(item.get("id"), int)
    )

    return (
        has_content
        and has_user
        and has_plurk
    )


# ------------------------------------------------------
# new_plurk
# ------------------------------------------------------


def _parse_new_plurk(
    item: dict[str, Any],
    bot_name: str,
) -> ParsedResponse | None:
    """Parse a command contained in a new Plurk."""

    content_raw = _get_content(item)

    if not content_raw:
        return None

    if not _mentions_bot(
        content_raw,
        bot_name,
    ):
        return None

    user_id = _get_user_id(item)
    plurk_id = _get_plurk_id(item)

    if user_id is None or plurk_id is None:
        return None

    config = _parse_command_content(
        content_raw,
        bot_name,
    )

    if config is None:
        return None

    return ParsedResponse(
        user_id=user_id,
        plurk_id=plurk_id,
        response_id=None,
        content_raw=content_raw,
        config=config,
    )


# ------------------------------------------------------
# new_response
# ------------------------------------------------------


def _parse_new_response(
    item: dict[str, Any],
    bot_name: str,
) -> ParsedResponse | None:
    """Parse a command contained in a Plurk response."""

    response = item.get("response")

    if not isinstance(response, dict):
        return None

    content_raw = _get_content(response)

    if not content_raw:
        return None

    if not _mentions_bot(
        content_raw,
        bot_name,
    ):
        return None

    user_id = _get_user_id(response)

    plurk_id = _get_plurk_id(item)

    response_id = _get_response_id(
        response
    )

    if (
        user_id is None
        or plurk_id is None
        or response_id is None
    ):
        return None

    config = _parse_command_content(
        content_raw,
        bot_name,
    )

    if config is None:
        return None

    return ParsedResponse(
        user_id=user_id,
        plurk_id=plurk_id,
        response_id=response_id,
        content_raw=content_raw,
        config=config,
    )


# ------------------------------------------------------
# Command parsing
# ------------------------------------------------------


def _parse_command_content(
    content_raw: str,
    bot_name: str,
) -> ActivityConfig | None:
    """
    Remove the bot mention and pass the remaining command
    to command_parser.
    """

    clean_content = _strip_html(
        content_raw
    )

    command_text = _remove_bot_mention(
        clean_content,
        bot_name,
    ).strip()

    if not command_text:
        return None

    try:
        return parse_command(
            command_text
        )

    except (ValueError, TypeError):
        return None


# ------------------------------------------------------
# Mention handling
# ------------------------------------------------------


def _mentions_bot(
    content: str,
    bot_name: str,
) -> bool:
    """
    Check whether the content mentions the bot.

    Supports normal text:
        @AI_Anchor 開始

    and HTML-containing Plurk content:
        <a ...>@AI_Anchor</a> 開始
    """

    clean_content = _strip_html(
        content
    )

    pattern = (
        r"@"
        + re.escape(bot_name)
        + r"\b"
    )

    return re.search(
        pattern,
        clean_content,
        flags=re.IGNORECASE,
    ) is not None


def _remove_bot_mention(
    content: str,
    bot_name: str,
) -> str:
    """Remove the bot mention from command text."""

    pattern = (
        r"@"
        + re.escape(bot_name)
        + r"\b"
    )

    return re.sub(
        pattern,
        "",
        content,
        count=1,
        flags=re.IGNORECASE,
    )


# ------------------------------------------------------
# Content normalization
# ------------------------------------------------------


def _strip_html(
    content: str,
) -> str:
    """
    Convert Plurk's HTML content into plain text.

    Only HTML tags are removed; character entities are unescaped.
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
    """Extract raw content from a Plurk event."""

    content_raw = item.get(
        "content_raw"
    )

    if isinstance(content_raw, str):
        return content_raw

    content = item.get("content")

    if isinstance(content, str):
        return content

    return None


# ------------------------------------------------------
# ID extraction
# ------------------------------------------------------


def _get_user_id(
    item: dict[str, Any],
) -> int | None:
    """Extract the user ID from an event."""

    value = item.get("user_id")

    if isinstance(value, int):
        return value

    value = item.get("owner_id")

    if isinstance(value, int):
        return value

    return None


def _get_plurk_id(
    item: dict[str, Any],
) -> int | None:
    """Extract the Plurk ID from an event."""

    value = item.get("plurk_id")

    if isinstance(value, int):
        return value

    value = item.get("id")

    if isinstance(value, int):
        return value

    return None


def _get_response_id(
    response: dict[str, Any],
) -> int | None:
    """Extract the response ID."""

    value = response.get("id")

    if isinstance(value, int):
        return value

    value = response.get("response_id")

    if isinstance(value, int):
        return value

    return None
