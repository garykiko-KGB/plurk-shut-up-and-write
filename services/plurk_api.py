import logging
import os
from typing import Any

import requests
from requests_oauthlib import OAuth1


PLURK_API_BASE = "https://www.plurk.com/APP"

logger = logging.getLogger(__name__)


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

    # --------------------------------------------------
    # Low-level HTTP methods
    # --------------------------------------------------

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a GET request to the Plurk API."""

        return self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a POST request to the Plurk API."""

        return self._request(
            method="POST",
            endpoint=endpoint,
            data=data,
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send an authenticated request to the Plurk API.

        GET parameters are sent through ``params``.
        POST parameters are sent through form data.

        Temporary debug logging is enabled for
        ``/Timeline/plurkAdd`` so the actual content sent to
        Plurk and the response returned by Plurk can be inspected.
        """

        url = f"{PLURK_API_BASE}{endpoint}"

        debug_plurk_add = (
            method.upper() == "POST"
            and endpoint == "/Timeline/plurkAdd"
        )

        if debug_plurk_add:
            logger.info(
                "Plurk API Request: "
                "method=%s endpoint=%s data=%s",
                method,
                endpoint,
                data,
            )

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                data=data,
                auth=self.auth,
                timeout=30,
            )
        except requests.RequestException as exc:
            if debug_plurk_add:
                logger.error(
                    "Plurk API Request failed: "
                    "method=%s endpoint=%s error=%s",
                    method,
                    endpoint,
                    exc,
                )

            raise PlurkAPIError(
                f"Plurk API 連線失敗：{exc}"
            ) from exc

        if debug_plurk_add:
            logger.info(
                "Plurk API Response: "
                "status=%s body=%s",
                response.status_code,
                response.text,
            )

        if not response.ok:
            raise PlurkAPIError(
                f"Plurk API 回應錯誤 "
                f"({response.status_code})："
                f"{response.text}"
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise PlurkAPIError(
                "Plurk API 回傳的內容不是有效 JSON。"
            ) from exc

        if not isinstance(result, dict):
            raise PlurkAPIError(
                "Plurk API 回傳的 JSON 格式不是物件。"
            )

        if "error_text" in result:
            raise PlurkAPIError(
                f"Plurk API 錯誤：{result['error_text']}"
            )

        return result

    # --------------------------------------------------
    # Profile
    # --------------------------------------------------

    def get_own_profile(self) -> dict[str, Any]:
        """Get the current Plurk account profile."""

        return self.get("/Users/me")

    # --------------------------------------------------
    # Realtime
    # --------------------------------------------------

    def get_user_channel(self) -> dict[str, Any]:
        """Get the realtime channel for the current account."""

        return self.get("/Realtime/getUserChannel")

    # --------------------------------------------------
    # Responses
    # --------------------------------------------------

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

    def add_response(
        self,
        plurk_id: int,
        content: str,
        qualifier: str = "says",
    ) -> dict[str, Any]:
        """
        Add a response to a Plurk.

        Plurk API requires:
            - plurk_id
            - content
            - qualifier
        """

        return self.post(
            "/Responses/responseAdd",
            data={
                "plurk_id": plurk_id,
                "content": content,
                "qualifier": qualifier,
            },
        )

    # --------------------------------------------------
    # Plurk creation
    # --------------------------------------------------

    def add_plurk(
        self,
        content: str,
        qualifier: str = "says",
        lang: str = "tr_ch",
        limited_to: list[int] | None = None,
        no_comments: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Plurk.

        Defaults:
            qualifier = "says"
            lang = "tr_ch" (Traditional Chinese)

        Optional parameters are only sent when explicitly provided.
        """

        data: dict[str, Any] = {
            "content": content,
            "qualifier": qualifier,
            "lang": lang,
        }

        if limited_to is not None:
            data["limited_to"] = limited_to

        if no_comments is not None:
            data["no_comments"] = no_comments

        return self.post(
            "/Timeline/plurkAdd",
            data=data,
        )
