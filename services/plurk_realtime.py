import json
from typing import Any, Iterator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import requests


class PlurkRealtimeError(RuntimeError):
    """Raised when a Plurk realtime request fails."""


class PlurkRealtime:
    """Listen to Plurk's realtime Comet channel."""

    def __init__(
        self,
        comet_server: str,
        channel_name: str,
    ) -> None:
        self.comet_server = comet_server
        self.channel_name = channel_name
        self.offset = 0

    def _build_url(self) -> str:
        """
        Build the realtime request URL.

        Plurk's comet_server may already contain query parameters such as
        channel and offset, so update the existing query string instead of
        rebuilding the URL manually.
        """

        parts = urlsplit(self.comet_server)

        query = parse_qs(
            parts.query,
            keep_blank_values=True,
        )

        # Ensure the correct channel is present.
        query["channel"] = [self.channel_name]

        # Always use the current offset.
        query["offset"] = [str(self.offset)]

        new_query = urlencode(
            query,
            doseq=True,
        )

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                new_query,
                parts.fragment,
            )
        )

    @staticmethod
    def _parse_response(text: str) -> dict[str, Any]:
        """
        Parse Plurk's realtime response.

        Plurk's realtime endpoint returns JSON wrapped in a JavaScript
        callback, for example:

            CometChannel.scriptCallback({...});

        Extract the JSON object from the wrapper before decoding it.
        """

        text = text.strip().lstrip("\ufeff")

        if not text:
            raise PlurkRealtimeError(
                "Plurk Realtime 回傳內容是空的。"
            )

        # Find the first opening parenthesis and the last closing
        # parenthesis. This keeps the parser independent of the exact
        # callback name used by Plurk.
        first_paren = text.find("(")
        last_paren = text.rfind(")")

        if first_paren == -1 or last_paren == -1:
            raise PlurkRealtimeError(
                "Plurk Realtime 回傳的內容不是有效的 JSONP。"
            )

        json_text = text[first_paren + 1:last_paren].strip()

        if not json_text:
            raise PlurkRealtimeError(
                "Plurk Realtime JSONP 中沒有 JSON 資料。"
            )

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise PlurkRealtimeError(
                "Plurk Realtime JSONP 中的內容不是有效 JSON。"
            ) from exc

        if not isinstance(data, dict):
            raise PlurkRealtimeError(
                "Plurk Realtime 回傳的 JSON 不是物件。"
            )

        return data

    def wait_for_events(self) -> dict[str, Any]:
        """
        Wait for the next realtime response from Plurk.

        The request may remain open while waiting for new data.
        """

        url = self._build_url()

        try:
            response = requests.get(
                url,
                timeout=70,
            )
        except requests.RequestException as exc:
            raise PlurkRealtimeError(
                f"Plurk Realtime 連線失敗：{exc}"
            ) from exc

        if not response.ok:
            raise PlurkRealtimeError(
                f"Plurk Realtime 回應錯誤 "
                f"({response.status_code})："
                f"{response.text}"
            )

        data = self._parse_response(
            response.text
        )

        new_offset = data.get("new_offset")

        if isinstance(new_offset, int) and new_offset >= 0:
            self.offset = new_offset

        return data

    def listen(self) -> Iterator[dict[str, Any]]:
        """
        Continuously listen for realtime events.

        Yields one realtime payload at a time.
        """

        while True:
            yield self.wait_for_events()
