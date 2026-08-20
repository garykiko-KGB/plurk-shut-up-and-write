from dataclasses import dataclass
from typing import Any

from command_parser import (
    ActivityConfig,
    CommandParseError,
    parse_command,
)


@dataclass(frozen=True)
class ParsedResponse:
    """A successfully parsed Plurk command response."""

    user_id: int
    plurk_id: int
    response_id: int
    content_raw: str
    config: ActivityConfig


def handle_realtime_event(
    event: dict[str, Any],
    bot_name: str = "AI_Anchor",
) -> list[ParsedResponse]:
    """
    Process one Plurk realtime payload.

    Only new_response events are considered.

    Responses that are not valid commands for this bot are ignored.
    """

    if not isinstance(event, dict):
        return []

    data = event.get("data")

    if not isinstance(data, list):
        return []

    parsed_responses: list[ParsedResponse] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if item.get("type") != "new_response":
            continue

        response = item.get("response")

        if not isinstance(response, dict):
            continue

        content_raw = response.get("content_raw")

        if not isinstance(content_raw, str):
            continue

        try:
            config = parse_command(
                content_raw,
                bot_name=bot_name,
            )
        except CommandParseError:
            # Not a valid command for this bot.
            continue

        user_id = response.get("user_id")
        plurk_id = response.get("plurk_id")
        response_id = response.get("id")

        if not isinstance(user_id, int):
            continue

        if not isinstance(plurk_id, int):
            continue

        if not isinstance(response_id, int):
            continue

        parsed_responses.append(
            ParsedResponse(
                user_id=user_id,
                plurk_id=plurk_id,
                response_id=response_id,
                content_raw=content_raw,
                config=config,
            )
        )

    return parsed_responses
