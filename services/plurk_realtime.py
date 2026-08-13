from typing import Any, Iterator

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
        """Build the realtime channel URL."""

        return (
            f"{self.comet_server}"
            f"?channel={self.channel_name}"
            f"&offset={self.offset}"
        )

    def wait_for_events(self) -> dict[str, Any]:
        """
        Wait for the next realtime response from Plurk.

        The request may remain open for a while when there is no
        new data. The returned payload contains a new_offset and,
        when available, event data.
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

        try:
            data = response.json()
        except ValueError as exc:
            raise PlurkRealtimeError(
                "Plurk Realtime 回傳的內容不是有效 JSON。"
            ) from exc

        new_offset = data.get("new_offset")

        if isinstance(new_offset, int) and new_offset >= 0:
            self.offset = new_offset

        return data

    def listen(self) -> Iterator[dict[str, Any]]:
        """
        Continuously listen for realtime events.

        Yields one API payload at a time.
        """

        while True:
            yield self.wait_for_events()
