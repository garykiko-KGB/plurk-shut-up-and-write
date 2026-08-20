import unittest

from parsers.command_parser import ActivityConfig
from handlers.response_handler import (
    ParsedResponse,
    handle_realtime_event,
)


class TestResponseHandler(unittest.TestCase):
    """Tests for realtime response handling."""

    # --------------------------------------------------
    # Valid response
    # --------------------------------------------------

    def test_valid_command_response_is_parsed(self):
        event = {
            "new_offset": 8,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 123456,
                    "response": {
                        "id": 987654,
                        "user_id": 111222,
                        "plurk_id": 123456,
                        "content_raw": (
                            "@AI_Anchor 開始寫作 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(len(result), 1)

        parsed = result[0]

        self.assertIsInstance(
            parsed,
            ParsedResponse,
        )

        self.assertEqual(
            parsed.user_id,
            111222,
        )

        self.assertEqual(
            parsed.plurk_id,
            123456,
        )

        self.assertEqual(
            parsed.response_id,
            987654,
        )

        self.assertEqual(
            parsed.content_raw,
            "@AI_Anchor 開始寫作 20/5/6/3",
        )

        self.assertEqual(
            parsed.config,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    # --------------------------------------------------
    # Default command
    # --------------------------------------------------

    def test_default_command_uses_default_config(self):
        event = {
            "new_offset": 1,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 200,
                        "user_id": 300,
                        "plurk_id": 100,
                        "content_raw": "@AI_Anchor 開始",
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(len(result), 1)

        self.assertEqual(
            result[0].config,
            ActivityConfig(
                work_time=25,
                break_time=5,
                rounds=4,
                prepare_time=5,
            ),
        )

    # --------------------------------------------------
    # Friendly syntax
    # --------------------------------------------------

    def test_friendly_command_is_parsed(self):
        event = {
            "new_offset": 2,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 201,
                        "user_id": 301,
                        "plurk_id": 100,
                        "content_raw": (
                            "@AI_Anchor 開始寫作，"
                            "工作20分鐘，"
                            "休息5分鐘，"
                            "6回合，"
                            "3分鐘後開始"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(len(result), 1)

        self.assertEqual(
            result[0].config,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    # --------------------------------------------------
    # Event filtering
    # --------------------------------------------------

    def test_new_plurk_event_is_ignored(self):
        event = {
            "new_offset": 3,
            "data": [
                {
                    "type": "new_plurk",
                    "plurk_id": 999,
                    "plurk": {
                        "content_raw": (
                            "@AI_Anchor 開始寫作 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_unknown_event_type_is_ignored(self):
        event = {
            "new_offset": 4,
            "data": [
                {
                    "type": "update_notification",
                    "counts": {
                        "noti": 1,
                        "req": 0,
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Invalid commands
    # --------------------------------------------------

    def test_non_command_response_is_ignored(self):
        event = {
            "new_offset": 5,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 202,
                        "user_id": 302,
                        "plurk_id": 100,
                        "content_raw": "今天晚餐吃什麼？",
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_wrong_bot_mention_is_ignored(self):
        event = {
            "new_offset": 6,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 203,
                        "user_id": 303,
                        "plurk_id": 100,
                        "content_raw": (
                            "@OtherBot 開始 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Missing response data
    # --------------------------------------------------

    def test_missing_data_is_ignored(self):
        event = {
            "new_offset": 7,
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_data_must_be_a_list(self):
        event = {
            "new_offset": 8,
            "data": {
                "type": "new_response",
            },
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_missing_response_is_ignored(self):
        event = {
            "new_offset": 9,
            "data": [
                {
                    "type": "new_response",
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_missing_content_raw_is_ignored(self):
        event = {
            "new_offset": 10,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 204,
                        "user_id": 304,
                        "plurk_id": 100,
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Missing identity fields
    # --------------------------------------------------

    def test_missing_user_id_is_ignored(self):
        event = {
            "new_offset": 11,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 205,
                        "plurk_id": 100,
                        "content_raw": (
                            "@AI_Anchor 開始 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_missing_plurk_id_is_ignored(self):
        event = {
            "new_offset": 12,
            "data": [
                {
                    "type": "new_response",
                    "response": {
                        "id": 206,
                        "user_id": 306,
                        "content_raw": (
                            "@AI_Anchor 開始 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    def test_missing_response_id_is_ignored(self):
        event = {
            "new_offset": 13,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "user_id": 307,
                        "plurk_id": 100,
                        "content_raw": (
                            "@AI_Anchor 開始 20/5/6/3"
                        ),
                    },
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Invalid event data types
    # --------------------------------------------------

    def test_non_dictionary_event_is_ignored(self):
        result = handle_realtime_event(
            None
        )

        self.assertEqual(
            result,
            [],
        )

    def test_non_dictionary_item_is_ignored(self):
        event = {
            "new_offset": 14,
            "data": [
                "invalid",
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 207,
                        "user_id": 308,
                        "plurk_id": 100,
                        "content_raw": (
                            "@AI_Anchor 開始 20/5/6/3"
                        ),
                    },
                },
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            len(result),
            1,
        )

    def test_non_dictionary_response_is_ignored(self):
        event = {
            "new_offset": 15,
            "data": [
                {
                    "type": "new_response",
                    "response": "invalid",
                }
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Multiple responses
    # --------------------------------------------------

    def test_multiple_valid_responses_are_parsed(self):
        event = {
            "new_offset": 16,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 301,
                        "user_id": 401,
                        "plurk_id": 100,
                        "content_raw": (
                            "@AI_Anchor 開始 20/5/4/5"
                        ),
                    },
                },
                {
                    "type": "new_response",
                    "plurk_id": 200,
                    "response": {
                        "id": 302,
                        "user_id": 402,
                        "plurk_id": 200,
                        "content_raw": (
                            "@AI_Anchor 開始 15/10/3/2"
                        ),
                    },
                },
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0].config,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=4,
                prepare_time=5,
            ),
        )

        self.assertEqual(
            result[1].config,
            ActivityConfig(
                work_time=15,
                break_time=10,
                rounds=3,
                prepare_time=2,
            ),
        )

    def test_valid_and_invalid_responses_are_mixed(self):
        event = {
            "new_offset": 17,
            "data": [
                {
                    "type": "new_response",
                    "plurk_id": 100,
                    "response": {
                        "id": 401,
                        "user_id": 501,
                        "plurk_id": 100,
                        "content_raw": "普通聊天",
                    },
                },
                {
                    "type": "new_plurk",
                    "plurk_id": 200,
                },
                {
                    "type": "new_response",
                    "plurk_id": 300,
                    "response": {
                        "id": 402,
                        "user_id": 502,
                        "plurk_id": 300,
                        "content_raw": (
                            "@AI_Anchor 開始 25/5/4/5"
                        ),
                    },
                },
            ],
        }

        result = handle_realtime_event(event)

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0].user_id,
            502,
        )

        self.assertEqual(
            result[0].plurk_id,
            300,
        )

        self.assertEqual(
            result[0].response_id,
            402,
        )


if __name__ == "__main__":
    unittest.main()
