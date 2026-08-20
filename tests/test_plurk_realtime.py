import unittest
from unittest.mock import Mock, patch

import requests

from services.plurk_realtime import (
    PlurkRealtime,
    PlurkRealtimeError,
)


class TestPlurkRealtime(unittest.TestCase):
    """Tests for the Plurk realtime listener."""

    def setUp(self) -> None:
        self.realtime = PlurkRealtime(
            comet_server=(
                "https://comet.example.com/comet"
                "?channel=old-channel&offset=99"
            ),
            channel_name="generic-test-channel",
        )

    # --------------------------------------------------
    # URL construction
    # --------------------------------------------------

    def test_build_url(self) -> None:
        url = self.realtime._build_url()

        self.assertEqual(
            url,
            "https://comet.example.com/comet"
            "?channel=generic-test-channel&offset=0",
        )

    def test_build_url_updates_existing_offset(self) -> None:
        self.realtime.offset = 42

        url = self.realtime._build_url()

        self.assertEqual(
            url,
            "https://comet.example.com/comet"
            "?channel=generic-test-channel&offset=42",
        )

    def test_build_url_preserves_other_query_parameters(self) -> None:
        self.realtime = PlurkRealtime(
            comet_server=(
                "https://comet.example.com/comet"
                "?channel=old-channel"
                "&offset=99"
                "&foo=bar"
            ),
            channel_name="generic-test-channel",
        )

        url = self.realtime._build_url()

        self.assertEqual(
            url,
            "https://comet.example.com/comet"
            "?channel=generic-test-channel"
            "&offset=0"
            "&foo=bar",
        )

    # --------------------------------------------------
    # JSONP parsing
    # --------------------------------------------------

    def test_parse_jsonp_response(self) -> None:
        raw_response = (
            "CometChannel.scriptCallback("
            '{"new_offset":21,"data":[]}'
            ");"
        )

        result = PlurkRealtime._parse_response(
            raw_response
        )

        self.assertEqual(
            result,
            {
                "new_offset": 21,
                "data": [],
            },
        )

    def test_parse_jsonp_response_with_event_data(self) -> None:
        raw_response = (
            "CometChannel.scriptCallback("
            "{"
            '"new_offset":21,'
            '"data":['
            "{"
            '"type":"new_response",'
            '"plurk_id":123,'
            '"response":{'
            '"content_raw":"@AI_Anchor 開始"'
            "}"
            "}"
            "]"
            "}"
            ");"
        )

        result = PlurkRealtime._parse_response(
            raw_response
        )

        self.assertEqual(
            result["new_offset"],
            21,
        )

        self.assertEqual(
            result["data"][0]["type"],
            "new_response",
        )

        self.assertEqual(
            result["data"][0]["plurk_id"],
            123,
        )

        self.assertEqual(
            result["data"][0]["response"]["content_raw"],
            "@AI_Anchor 開始",
        )

    def test_parse_empty_response_is_rejected(self) -> None:
        with self.assertRaises(PlurkRealtimeError):
            PlurkRealtime._parse_response("")

    def test_parse_non_jsonp_response_is_rejected(self) -> None:
        with self.assertRaises(PlurkRealtimeError):
            PlurkRealtime._parse_response(
                '{"new_offset":21,"data":[]}'
            )

    def test_parse_invalid_jsonp_is_rejected(self) -> None:
        raw_response = (
            "CometChannel.scriptCallback("
            '{"new_offset":INVALID}'
            ");"
        )

        with self.assertRaises(PlurkRealtimeError):
            PlurkRealtime._parse_response(
                raw_response
            )

    def test_parse_jsonp_with_non_object_json_is_rejected(self) -> None:
        raw_response = (
            "CometChannel.scriptCallback("
            '["not", "an", "object"]'
            ");"
        )

        with self.assertRaises(PlurkRealtimeError):
            PlurkRealtime._parse_response(
                raw_response
            )

    # --------------------------------------------------
    # Successful requests
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_wait_for_events_returns_response(
        self,
        mock_get: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":21,"data":[]}'
            ");"
        )

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result["new_offset"],
            21,
        )

        self.assertEqual(
            self.realtime.offset,
            21,
        )

        mock_get.assert_called_once_with(
            "https://comet.example.com/comet"
            "?channel=generic-test-channel&offset=0",
            timeout=70,
        )

    @patch("services.plurk_realtime.requests.get")
    def test_wait_for_events_updates_offset(
        self,
        mock_get: Mock,
    ) -> None:
        self.realtime.offset = 10

        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":25,"data":[]}'
            ");"
        )

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result["new_offset"],
            25,
        )

        self.assertEqual(
            self.realtime.offset,
            25,
        )

    # --------------------------------------------------
    # Offset handling
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_no_new_data_keeps_current_offset(
        self,
        mock_get: Mock,
    ) -> None:
        self.realtime.offset = 10

        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":-1}'
            ");"
        )

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result,
            {
                "new_offset": -1,
            },
        )

        self.assertEqual(
            self.realtime.offset,
            10,
        )

    @patch("services.plurk_realtime.requests.get")
    def test_resync_offset_keeps_current_offset(
        self,
        mock_get: Mock,
    ) -> None:
        self.realtime.offset = 25

        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":-3}'
            ");"
        )

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result,
            {
                "new_offset": -3,
            },
        )

        self.assertEqual(
            self.realtime.offset,
            25,
        )

    @patch("services.plurk_realtime.requests.get")
    def test_invalid_new_offset_does_not_change_offset(
        self,
        mock_get: Mock,
    ) -> None:
        self.realtime.offset = 15

        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":"invalid"}'
            ");"
        )

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result["new_offset"],
            "invalid",
        )

        self.assertEqual(
            self.realtime.offset,
            15,
        )

    # --------------------------------------------------
    # HTTP errors
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_http_error_raises_plurk_realtime_error(
        self,
        mock_get: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_get.return_value = mock_response

        with self.assertRaises(PlurkRealtimeError):
            self.realtime.wait_for_events()

    # --------------------------------------------------
    # Connection errors
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_connection_error_raises_plurk_realtime_error(
        self,
        mock_get: Mock,
    ) -> None:
        mock_get.side_effect = requests.RequestException(
            "connection failed"
        )

        with self.assertRaises(PlurkRealtimeError):
            self.realtime.wait_for_events()

    # --------------------------------------------------
    # Listen iterator
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_listen_yields_events(
        self,
        mock_get: Mock,
    ) -> None:
        first_response = Mock()
        first_response.ok = True
        first_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":1,'
            '"data":[{"type":"new_response","plurk_id":100}]}'
            ");"
        )

        second_response = Mock()
        second_response.ok = True
        second_response.text = (
            "CometChannel.scriptCallback("
            '{"new_offset":2,'
            '"data":[{"type":"new_response","plurk_id":200}]}'
            ");"
        )

        mock_get.side_effect = [
            first_response,
            second_response,
        ]

        event_stream = self.realtime.listen()

        first_event = next(event_stream)
        second_event = next(event_stream)

        self.assertEqual(
            first_event["new_offset"],
            1,
        )

        self.assertEqual(
            first_event["data"][0]["plurk_id"],
            100,
        )

        self.assertEqual(
            second_event["new_offset"],
            2,
        )

        self.assertEqual(
            second_event["data"][0]["plurk_id"],
            200,
        )

        self.assertEqual(
            self.realtime.offset,
            2,
        )

        self.assertEqual(
            mock_get.call_count,
            2,
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_initial_offset_is_zero(self) -> None:
        self.assertEqual(
            self.realtime.offset,
            0,
        )


if __name__ == "__main__":
    unittest.main()
