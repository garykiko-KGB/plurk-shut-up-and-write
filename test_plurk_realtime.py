import unittest
from unittest.mock import Mock, patch

import requests

from services.plurk_realtime import (
    PlurkRealtime,
    PlurkRealtimeError,
)


class TestPlurkRealtime(unittest.TestCase):
    """Tests for the Plurk realtime listener."""

    def setUp(self):
        self.realtime = PlurkRealtime(
            comet_server="https://comet.example.com/comet",
            channel_name="generic-test-channel",
        )

    # --------------------------------------------------
    # URL construction
    # --------------------------------------------------

    def test_build_url(self):
        url = self.realtime._build_url()

        self.assertEqual(
            url,
            "https://comet.example.com/comet"
            "?channel=generic-test-channel&offset=0",
        )

    def test_build_url_uses_updated_offset(self):
        self.realtime.offset = 42

        url = self.realtime._build_url()

        self.assertEqual(
            url,
            "https://comet.example.com/comet"
            "?channel=generic-test-channel&offset=42",
        )

    # --------------------------------------------------
    # Successful responses
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_wait_for_events_returns_response(self, mock_get):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "new_offset": 21,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 123,
                    "response": {
                        "content_raw": "@AI_Anchor 開始"
                    },
                }
            ],
        }

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result["new_offset"],
            21,
        )

        self.assertEqual(
            result["data"][0]["type"],
            "new_response",
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
    def test_wait_for_events_with_no_new_data_keeps_offset(self, mock_get):
        self.realtime.offset = 10

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "new_offset": -1,
        }

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result,
            {"new_offset": -1},
        )

        self.assertEqual(
            self.realtime.offset,
            10,
        )

    @patch("services.plurk_realtime.requests.get")
    def test_wait_for_events_with_negative_resync_offset_keeps_current_offset(
        self,
        mock_get,
    ):
        self.realtime.offset = 25

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "new_offset": -3,
        }

        mock_get.return_value = mock_response

        result = self.realtime.wait_for_events()

        self.assertEqual(
            result["new_offset"],
            -3,
        )

        self.assertEqual(
            self.realtime.offset,
            25,
        )

    # --------------------------------------------------
    # HTTP errors
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_http_error_raises_plurk_realtime_error(self, mock_get):
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
    def test_connection_error_raises_plurk_realtime_error(self, mock_get):
        mock_get.side_effect = requests.RequestException(
            "connection failed"
        )

        with self.assertRaises(PlurkRealtimeError):
            self.realtime.wait_for_events()

    # --------------------------------------------------
    # Invalid JSON
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_invalid_json_raises_plurk_realtime_error(self, mock_get):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.side_effect = ValueError(
            "invalid json"
        )

        mock_get.return_value = mock_response

        with self.assertRaises(PlurkRealtimeError):
            self.realtime.wait_for_events()

    # --------------------------------------------------
    # Listen iterator
    # --------------------------------------------------

    @patch("services.plurk_realtime.requests.get")
    def test_listen_yields_events(self, mock_get):
        first_response = Mock()
        first_response.ok = True
        first_response.json.return_value = {
            "new_offset": 1,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                }
            ],
        }

        second_response = Mock()
        second_response.ok = True
        second_response.json.return_value = {
            "new_offset": 2,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 200,
                }
            ],
        }

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
            second_event["new_offset"],
            2,
        )

        self.assertEqual(
            self.realtime.offset,
            2,
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_initial_offset_is_zero(self):
        self.assertEqual(
            self.realtime.offset,
            0,
        )


if __name__ == "__main__":
    unittest.main()
