from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any

from parsers.command_parser import (
    ActivityConfig,
    CommandParseError,
    parse_command,
)


@dataclass(frozen=True)
class ParsedResponse:
    """
    Normalized activity command extracted from a Plurk realtime event.

    response_id:
        - int for a command coming from a Plurk response.
        - None for a command coming from a new Plurk.

    owner_nick_name:
        Plurk nickname of the command owner.
    """

    user_id: int
    owner_nick_name: str
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
    owner_nick_name = _get_user_nick_name(
        item,
        user_id,
    )
    plurk_id = _get_plurk_id(item)

    if (
        user_id is None
        or plurk_id is None
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
        owner_nick_name=owner_nick_name,
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

    if user_id is None:
        return None

    owner_nick_name = _get_user_nick_name(
        response,
        user_id,
    )

    plurk_id = _get_plurk_id(item)
    response_id = _get_response_id(response)

    if (
        plurk_id is None
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
        owner_nick_name=owner_nick_name,
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
    Normalize Plurk content.

    Handles literal HTML, HTML entities, and repeatedly encoded
    HTML entities.
    """

    text = content

    for _ in range(3):
        decoded = unescape(text)

        stripped = re.sub(
            r"<[^>]*>",
            "",
            decoded,
        )

        if stripped == text:
            text = stripped
            break

        text = stripped

    return text


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
# User information
# ------------------------------------------------------


def _get_user_nick_name(
    item: dict[str, Any],
    user_id: int | None,
) -> str:
    """
    Extract the owner's Plurk nickname.

    Supported forms include:
        - item["nick_name"]
        - item["user"]["nick_name"]
        - item["plurk"]["user"]["nick_name"]
        - item["plurk_users"][str(user_id)]["nick_name"]

    A fallback value is returned when nickname information is not
    present in the realtime payload.
    """

    direct_nick_name = item.get(
        "nick_name"
    )

    if isinstance(
        direct_nick_name,
        str,
    ) and direct_nick_name.strip():
        return direct_nick_name.strip()

    user = item.get("user")

    if isinstance(
        user,
        dict,
    ):
        nick_name = user.get(
            "nick_name"
        )

        if (
            isinstance(
                nick_name,
                str,
            )
            and nick_name.strip()
        ):
            return nick_name.strip()

    plurk = item.get("plurk")

    if isinstance(
        plurk,
        dict,
    ):
        nick_name = _extract_nick_name_from_user(
            plurk.get("user")
        )

        if nick_name is not None:
            return nick_name

    plurk_users = item.get(
        "plurk_users"
    )

    if isinstance(
        plurk_users,
        dict,
    ):
        nick_name = _extract_nick_name_from_user_map(
            plurk_users,
            user_id,
        )

        if nick_name is not None:
            return nick_name

    return "Unknown"


def _extract_nick_name_from_user(
    user: Any,
) -> str | None:
    """Extract nick_name from one user dictionary."""

    if not isinstance(
        user,
        dict,
    ):
        return None

    nick_name = user.get(
        "nick_name"
    )

    if (
        isinstance(
            nick_name,
            str,
        )
        and nick_name.strip()
    ):
        return nick_name.strip()

    return None


def _extract_nick_name_from_user_map(
    users: dict[str, Any],
    user_id: int | None,
) -> str | None:
    """Extract nick_name from a Plurk user map."""

    if user_id is None:
        return None

    user = users.get(
        str(user_id)
    )

    return _extract_nick_name_from_user(
        user
    )


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
