import os
from typing import Any

import requests
from requests_oauthlib import OAuth1


PLURK_API_BASE = "https://www.plurk.com/APP"


class PlurkAPIError(RuntimeError):
    """Raised when a Plurk API request fails."""


class PlurkAPI:
    """Small wrapper around the Plurk API."""

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        token: str | None = None,
        token_secret: str | None = None,
    ) -> None:
        self.app_key = app_key or os.getenv("PLURK_APP_KEY")
        self.app_secret = app_secret or os.getenv("PLURK_APP_SECRET")
        self.token = token or os.getenv("PLURK_TOKEN")
        self.token_secret = token_secret or os.getenv("PLURK_TOKEN_SECRET")

        missing = [
            name
            for name, value in {
                "PLURK_APP_KEY": self.app_key,
                "PLURK_APP_SECRET": self.app_secret,
                "PLURK_TOKEN": self.token,
                "PLURK_TOKEN_SECRET": self.token_secret,
            }.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "缺少 Plurk API 環境變數："
                + ", ".join(missing)
            )

        self.auth = OAuth1(
            client_key=self.app_key,
            client_secret=self.app_secret,
            resource_owner_key=self.token,
            resource_owner_secret=self.token_secret,
            signature_method="HMAC-SHA1",
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a GET request to the Plurk API."""

        url = f"{PLURK_API_BASE}{endpoint}"

        try:
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise PlurkAPIError(
                f"Plurk API 連線失敗：{exc}"
            ) from exc

        if not response.ok:
            raise PlurkAPIError(
                f"Plurk API 回應錯誤 "
                f"({response.status_code})："
                f"{response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise PlurkAPIError(
                "Plurk API 回傳的內容不是有效 JSON。"
            ) from exc

        if isinstance(data, dict) and "error_text" in data:
            raise PlurkAPIError(
                f"Plurk API 錯誤：{data['error_text']}"
            )

        return data

    def get_own_profile(self) -> dict[str, Any]:
        """Get the current Plurk account profile."""

        return self.get("/Users/me")

    def get_user_channel(self) -> dict[str, Any]:
        """Get the realtime channel for the current account."""

        return self.get("/Realtime/getUserChannel")

    def get_responses(
        self,
        plurk_id: int,
        from_response: int = 0,
    ) -> dict[str, Any]:
        """Get responses for a Plurk."""

        return self.get(
            "/Responses/get",
            params={
                "plurk_id": plurk_id,
                "from_response": from_response,
            },
        )
