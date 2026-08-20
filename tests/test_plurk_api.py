import unittest
from unittest.mock import Mock, patch

import requests

from services.plurk_api import (
    PLURK_API_BASE,
    PlurkAPI,
    PlurkAPIError,
)


class TestPlurkAPI(unittest.TestCase):
    """Tests for the Plurk API wrapper."""

    def setUp(self) -> None:
        self.api = PlurkAPI(
            app_key="test-app-key",
            app_secret="test-app-secret",
            token="test-token",
            token_secret="test-token-secret",
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_api_initialization(self) -> None:
        self.assertEqual(
            self.api.app_key,
            "test-app-key",
        )

        self.assertEqual(
            self.api.app_secret,
            "test-app-secret",
        )

        self.assertEqual(
            self.api.token,
            "test-token",
        )

        self.assertEqual(
            self.api.token_secret,
            "test-token-secret",
        )

        self.assertIsNotNone(
            self.api.auth
        )

    def test_missing_credentials_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            PlurkAPI(
                app_key="",
                app_secret="",
                token="",
                token_secret="",
            )

    # --------------------------------------------------
    # Low-level GET
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_get_request(self, mock_request: Mock) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": "ok",
        }

        mock_request.return_value = mock_response

        result = self.api.get(
            "/Users/me"
        )

        self.assertEqual(
            result,
            {
                "result": "ok",
            },
        )

        mock_request.assert_called_once_with(
            method="GET",
            url=f"{PLURK_API_BASE}/Users/me",
            params=None,
            data=None,
            auth=self.api.auth,
            timeout=30,
        )

    # --------------------------------------------------
    # Low-level POST
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_post_request(self, mock_request: Mock) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": "created",
        }

        mock_request.return_value = mock_response

        result = self.api.post(
            "/Timeline/plurkAdd",
            {
                "content": "Hello",
            },
        )

        self.assertEqual(
            result,
            {
                "result": "created",
            },
        )

        mock_request.assert_called_once_with(
            method="POST",
            url=f"{PLURK_API_BASE}/Timeline/plurkAdd",
            params=None,
            data={
                "content": "Hello",
            },
            auth=self.api.auth,
            timeout=30,
        )

    # --------------------------------------------------
    # HTTP errors
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_http_error_raises_plurk_api_error(
        self,
        mock_request: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = "Invalid data"

        mock_request.return_value = mock_response

        with self.assertRaises(PlurkAPIError) as context:
            self.api.get("/Users/me")

        self.assertIn(
            "400",
            str(context.exception),
        )

        self.assertIn(
            "Invalid data",
            str(context.exception),
        )

    # --------------------------------------------------
    # Connection errors
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_connection_error_raises_plurk_api_error(
        self,
        mock_request: Mock,
    ) -> None:
        mock_request.side_effect = requests.RequestException(
            "connection failed"
        )

        with self.assertRaises(PlurkAPIError) as context:
            self.api.get("/Users/me")

        self.assertIn(
            "連線失敗",
            str(context.exception),
        )

    # --------------------------------------------------
    # JSON errors
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_invalid_json_raises_plurk_api_error(
        self,
        mock_request: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.side_effect = ValueError(
            "invalid json"
        )

        mock_request.return_value = mock_response

        with self.assertRaises(PlurkAPIError) as context:
            self.api.get("/Users/me")

        self.assertIn(
            "不是有效 JSON",
            str(context.exception),
        )

    @patch("services.plurk_api.requests.request")
    def test_non_dict_json_raises_plurk_api_error(
        self,
        mock_request: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = [
            "unexpected",
            "list",
        ]

        mock_request.return_value = mock_response

        with self.assertRaises(PlurkAPIError):
            self.api.get("/Users/me")

    # --------------------------------------------------
    # API error payload
    # --------------------------------------------------

    @patch("services.plurk_api.requests.request")
    def test_error_text_raises_plurk_api_error(
        self,
        mock_request: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "error_text": "Content is empty",
        }

        mock_request.return_value = mock_response

        with self.assertRaises(PlurkAPIError) as context:
            self.api.post(
                "/Timeline/plurkAdd",
                {
                    "content": "",
                },
            )

        self.assertIn(
            "Content is empty",
            str(context.exception),
        )

    # --------------------------------------------------
    # Profile
    # --------------------------------------------------

    @patch.object(PlurkAPI, "get")
    def test_get_own_profile(
        self,
        mock_get: Mock,
    ) -> None:
        mock_get.return_value = {
            "id": 123,
            "nick_name": "AI_Anchor",
        }

        result = self.api.get_own_profile()

        self.assertEqual(
            result,
            {
                "id": 123,
                "nick_name": "AI_Anchor",
            },
        )

        mock_get.assert_called_once_with(
            "/Users/me"
        )

    # --------------------------------------------------
    # Realtime
    # --------------------------------------------------

    @patch.object(PlurkAPI, "get")
    def test_get_user_channel(
        self,
        mock_get: Mock,
    ) -> None:
        mock_get.return_value = {
            "comet_server": "https://comet.example.com",
            "channel_name": "generic-test",
        }

        result = self.api.get_user_channel()

        self.assertEqual(
            result,
            {
                "comet_server": "https://comet.example.com",
                "channel_name": "generic-test",
            },
        )

        mock_get.assert_called_once_with(
            "/Realtime/getUserChannel"
        )

    # --------------------------------------------------
    # Responses
    # --------------------------------------------------

    @patch.object(PlurkAPI, "get")
    def test_get_responses(
        self,
        mock_get: Mock,
    ) -> None:
        mock_get.return_value = {
            "responses": [],
            "response_count": 0,
        }

        result = self.api.get_responses(
            plurk_id=123456,
            from_response=5,
        )

        self.assertEqual(
            result,
            {
                "responses": [],
                "response_count": 0,
            },
        )

        mock_get.assert_called_once_with(
            "/Responses/get",
            params={
                "plurk_id": 123456,
                "from_response": 5,
            },
        )

    # --------------------------------------------------
    # Add response
    # --------------------------------------------------

    @patch.object(PlurkAPI, "post")
    def test_add_response(
        self,
        mock_post: Mock,
    ) -> None:
        mock_post.return_value = {
            "id": 999,
            "plurk_id": 123456,
            "content": "測試回覆",
        }

        result = self.api.add_response(
            plurk_id=123456,
            content="測試回覆",
        )

        self.assertEqual(
            result,
            {
                "id": 999,
                "plurk_id": 123456,
                "content": "測試回覆",
            },
        )

        mock_post.assert_called_once_with(
            "/Responses/responseAdd",
            data={
                "plurk_id": 123456,
                "content": "測試回覆",
                "qualifier": "says",
            },
        )

    def test_add_response_uses_custom_qualifier(
        self,
    ) -> None:
        with patch.object(
            PlurkAPI,
            "post",
            return_value={
                "id": 999,
            },
        ) as mock_post:
            self.api.add_response(
                plurk_id=123456,
                content="嗨！",
                qualifier="writes",
            )

        mock_post.assert_called_once_with(
            "/Responses/responseAdd",
            data={
                "plurk_id": 123456,
                "content": "嗨！",
                "qualifier": "writes",
            },
        )

    # --------------------------------------------------
    # Add Plurk
    # --------------------------------------------------

    @patch.object(PlurkAPI, "post")
    def test_add_plurk(
        self,
        mock_post: Mock,
    ) -> None:
        mock_post.return_value = {
            "plurk_id": 987654,
            "content": "活動開始！",
        }

        result = self.api.add_plurk(
            content="活動開始！",
        )

        self.assertEqual(
            result,
            {
                "plurk_id": 987654,
                "content": "活動開始！",
            },
        )

        mock_post.assert_called_once_with(
            "/Timeline/plurkAdd",
            data={
                "content": "活動開始！",
                "qualifier": "says",
                "lang": "tr_ch",
            },
        )

    def test_add_plurk_accepts_optional_parameters(
        self,
    ) -> None:
        with patch.object(
            PlurkAPI,
            "post",
            return_value={
                "plurk_id": 987654,
            },
        ) as mock_post:
            self.api.add_plurk(
                content="只有朋友看得到",
                qualifier="writes",
                lang="tr_ch",
                limited_to=[111, 222],
                no_comments=2,
            )

        mock_post.assert_called_once_with(
            "/Timeline/plurkAdd",
            data={
                "content": "只有朋友看得到",
                "qualifier": "writes",
                "lang": "tr_ch",
                "limited_to": [111, 222],
                "no_comments": 2,
            },
        )

    def test_add_plurk_does_not_send_unspecified_optional_parameters(
        self,
    ) -> None:
        with patch.object(
            PlurkAPI,
            "post",
            return_value={
                "plurk_id": 987654,
            },
        ) as mock_post:
            self.api.add_plurk(
                content="一般公開活動",
            )

        mock_post.assert_called_once_with(
            "/Timeline/plurkAdd",
            data={
                "content": "一般公開活動",
                "qualifier": "says",
                "lang": "tr_ch",
            },
        )


if __name__ == "__main__":
    unittest.main()
