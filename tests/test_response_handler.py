import unittest
from unittest.mock import patch

from parsers.command_parser import ActivityConfig
from handlers.response_handler import (
    ParsedResponse,
    handle_realtime_event,
)


class TestResponseHandler(unittest.TestCase):
    """Tests for Plurk realtime event handling."""

    BOT_NAME = "AI_Anchor"

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _new_plurk(
        *,
        plurk_id=1001,
        user_id=2001,
        content_raw="@AI_Anchor 開始",
    ):
        return {
            "id": plurk_id,
            "plurk_id": plurk_id,
            "user_id": user_id,
            "owner_id": user_id,
            "content_raw": content_raw,
            "content": content_raw,
        }

    @staticmethod
    def _new_response(
        *,
        response_id=3001,
        plurk_id=1001,
        user_id=2001,
        content_raw="@AI_Anchor 開始",
    ):
        return {
            "plurk_id": plurk_id,
            "response": {
                "id": response_id,
                "user_id": user_id,
                "content_raw": content_raw,
                "content": content_raw,
            },
        }

    # --------------------------------------------------
    # new_plurk
    # --------------------------------------------------

    def test_new_plurk_with_bot_mention_is_parsed(
        self,
    ) -> None:
        event = {
            "new_offset": 1,
            "data": [
                self._new_plurk()
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        parsed = result[0]

        self.assertIsInstance(
            parsed,
            ParsedResponse,
        )

        self.assertEqual(
            parsed.user_id,
            2001,
        )

        self.assertEqual(
            parsed.plurk_id,
            1001,
        )

        self.assertIsNone(
            parsed.response_id,
        )

        self.assertEqual(
            parsed.content_raw,
            "@AI_Anchor 開始",
        )

        self.assertIsInstance(
            parsed.config,
            ActivityConfig,
        )

    def test_new_plurk_without_bot_mention_is_ignored(
        self,
    ) -> None:
        event = {
            "new_offset": 2,
            "data": [
                self._new_plurk(
                    content_raw="開始",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_new_plurk_with_wrong_bot_mention_is_ignored(
        self,
    ) -> None:
        event = {
            "new_offset": 3,
            "data": [
                self._new_plurk(
                    content_raw="@OtherBot 開始",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_new_plurk_with_custom_configuration_is_parsed(
        self,
    ) -> None:
        event = {
            "new_offset": 4,
            "data": [
                self._new_plurk(
                    plurk_id=1101,
                    user_id=2101,
                    content_raw=(
                        "@AI_Anchor 開始 20/5/3/5"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        config = result[0].config

        self.assertEqual(
            config.work_time,
            20,
        )

        self.assertEqual(
            config.break_time,
            5,
        )

        self.assertEqual(
            config.rounds,
            3,
        )

        self.assertEqual(
            config.prepare_time,
            5,
        )

    # --------------------------------------------------
    # new_response
    # --------------------------------------------------

    def test_new_response_with_bot_mention_is_parsed(
        self,
    ) -> None:
        event = {
            "new_offset": 5,
            "data": [
                self._new_response()
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        parsed = result[0]

        self.assertIsInstance(
            parsed,
            ParsedResponse,
        )

        self.assertEqual(
            parsed.user_id,
            2001,
        )

        self.assertEqual(
            parsed.plurk_id,
            1001,
        )

        self.assertEqual(
            parsed.response_id,
            3001,
        )

        self.assertEqual(
            parsed.content_raw,
            "@AI_Anchor 開始",
        )

    def test_new_response_without_bot_mention_is_ignored(
        self,
    ) -> None:
        event = {
            "new_offset": 6,
            "data": [
                self._new_response(
                    content_raw="開始",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_new_response_with_custom_configuration_is_parsed(
        self,
    ) -> None:
        event = {
            "new_offset": 7,
            "data": [
                self._new_response(
                    response_id=3007,
                    plurk_id=1007,
                    user_id=2007,
                    content_raw=(
                        "@AI_Anchor 開始 30/5/2/3"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        parsed = result[0]

        self.assertEqual(
            parsed.config.work_time,
            30,
        )

        self.assertEqual(
            parsed.config.break_time,
            5,
        )

        self.assertEqual(
            parsed.config.rounds,
            2,
        )

        self.assertEqual(
            parsed.config.prepare_time,
            3,
        )

    # --------------------------------------------------
    # Mixed events
    # --------------------------------------------------

    def test_valid_new_plurk_and_response_are_both_parsed(
        self,
    ) -> None:
        event = {
            "new_offset": 8,
            "data": [
                self._new_plurk(
                    plurk_id=1008,
                    user_id=2008,
                    content_raw="@AI_Anchor 開始",
                ),
                self._new_response(
                    response_id=3008,
                    plurk_id=1009,
                    user_id=2009,
                    content_raw="@AI_Anchor 開始",
                ),
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertIsNone(
            result[0].response_id
        )

        self.assertEqual(
            result[1].response_id,
            3008,
        )

    def test_valid_and_invalid_events_are_mixed(
        self,
    ) -> None:
        event = {
            "new_offset": 9,
            "data": [
                self._new_plurk(
                    plurk_id=1009,
                    user_id=2009,
                    content_raw="@AI_Anchor 開始",
                ),
                {
                    "type": "update_notification",
                    "count": 1,
                },
                {
                    "unexpected": True,
                },
                self._new_response(
                    response_id=3010,
                    plurk_id=1010,
                    user_id=2010,
                    content_raw="@AI_Anchor 開始",
                ),
                self._new_plurk(
                    plurk_id=1011,
                    user_id=2011,
                    content_raw="沒有提到機器人",
                ),
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0].plurk_id,
            1009,
        )

        self.assertEqual(
            result[1].response_id,
            3010,
        )

    # --------------------------------------------------
    # Invalid event payloads
    # --------------------------------------------------

    def test_non_dictionary_event_is_ignored(
        self,
    ) -> None:
        result = handle_realtime_event(
            "invalid",
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_missing_data_is_ignored(
        self,
    ) -> None:
        result = handle_realtime_event(
            {},
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_non_list_data_is_ignored(
        self,
    ) -> None:
        result = handle_realtime_event(
            {
                "data": {},
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_non_dictionary_item_is_ignored(
        self,
    ) -> None:
        result = handle_realtime_event(
            {
                "data": [
                    "invalid",
                    123,
                    None,
                ],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Unknown event types
    # --------------------------------------------------

    def test_unknown_event_type_is_ignored(
        self,
    ) -> None:
        event = {
            "new_offset": 10,
            "data": [
                {
                    "type": "some_future_event",
                }
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_update_notification_is_ignored(
        self,
    ) -> None:
        event = {
            "new_offset": 11,
            "data": [
                {
                    "type": "update_notification",
                    "count": 5,
                }
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Missing IDs
    # --------------------------------------------------

    def test_missing_user_id_is_ignored(
        self,
    ) -> None:
        item = self._new_plurk(
            plurk_id=1201,
            user_id=2201,
        )

        item.pop("user_id")
        item.pop("owner_id")

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_missing_plurk_id_is_ignored(
        self,
    ) -> None:
        item = self._new_plurk(
            plurk_id=1202,
            user_id=2202,
        )

        item.pop("id")
        item.pop("plurk_id")

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_missing_response_id_is_ignored(
        self,
    ) -> None:
        item = self._new_response(
            response_id=3201,
            plurk_id=1203,
            user_id=2203,
        )

        item["response"].pop("id")
        item["response"].pop(
            "response_id",
            None,
        )

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Missing content
    # --------------------------------------------------

    def test_missing_new_plurk_content_is_ignored(
        self,
    ) -> None:
        item = self._new_plurk()

        item.pop("content_raw")
        item.pop("content")

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_missing_response_content_is_ignored(
        self,
    ) -> None:
        item = self._new_response()

        item["response"].pop(
            "content_raw"
        )
        item["response"].pop(
            "content"
        )

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Invalid commands
    # --------------------------------------------------

    def test_invalid_command_is_ignored(
        self,
    ) -> None:
        event = {
            "data": [
                self._new_plurk(
                    content_raw=(
                        "@AI_Anchor "
                        "這不是有效指令"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_empty_command_after_mention_is_ignored(
        self,
    ) -> None:
        event = {
            "data": [
                self._new_plurk(
                    content_raw="@AI_Anchor",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Mention handling
    # --------------------------------------------------

    def test_mention_matching_is_case_sensitive(
        self,
    ) -> None:
        """
        command_parser currently matches @bot_name case-sensitively.
        """

        event = {
            "data": [
                self._new_plurk(
                    content_raw="@ai_anchor 開始",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_partial_bot_name_is_not_treated_as_mention(
        self,
    ) -> None:
        event = {
            "data": [
                self._new_plurk(
                    content_raw="@AI_AnchorBot 開始",
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # HTML content
    # --------------------------------------------------

    def test_html_new_plurk_mention_is_parsed(
        self,
    ) -> None:
        event = {
            "data": [
                self._new_plurk(
                    content_raw=(
                        '<a href="https://www.plurk.com/AI_Anchor">'
                        "@AI_Anchor"
                        "</a> 開始"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_html_response_mention_is_parsed(
        self,
    ) -> None:
        event = {
            "data": [
                self._new_response(
                    content_raw=(
                        '<a href="https://www.plurk.com/AI_Anchor">'
                        "@AI_Anchor"
                        "</a> 開始"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Alternate ID fields
    # --------------------------------------------------

    def test_new_plurk_can_use_owner_id(
        self,
    ) -> None:
        item = self._new_plurk()

        item.pop("user_id")

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0].user_id,
            2001,
        )

    def test_new_plurk_can_use_id_for_plurk_id(
        self,
    ) -> None:
        item = self._new_plurk()

        item.pop("plurk_id")

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0].plurk_id,
            1001,
        )

    def test_response_can_use_response_id_field(
        self,
    ) -> None:
        item = self._new_response()

        response = item["response"]

        response.pop("id")
        response["response_id"] = 3999

        result = handle_realtime_event(
            {
                "data": [item],
            },
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0].response_id,
            3999,
        )

    # --------------------------------------------------
    # Parser delegation
    # --------------------------------------------------

    @patch(
        "handlers.response_handler.parse_command"
    )
    def test_new_plurk_delegates_to_command_parser(
        self,
        mock_parse_command,
    ) -> None:
        expected_config = ActivityConfig(
            work_time=30,
            break_time=10,
            rounds=2,
            prepare_time=3,
        )

        mock_parse_command.return_value = (
            expected_config
        )

        event = {
            "data": [
                self._new_plurk(
                    content_raw=(
                        "@AI_Anchor "
                        "開始 30/10/2/3"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        mock_parse_command.assert_called_once_with(
            "@AI_Anchor 開始 30/10/2/3",
            bot_name="AI_Anchor",
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertIs(
            result[0].config,
            expected_config,
        )

    @patch(
        "handlers.response_handler.parse_command"
    )
    def test_new_response_delegates_to_command_parser(
        self,
        mock_parse_command,
    ) -> None:
        expected_config = ActivityConfig(
            work_time=30,
            break_time=10,
            rounds=2,
            prepare_time=3,
        )

        mock_parse_command.return_value = (
            expected_config
        )

        event = {
            "data": [
                self._new_response(
                    content_raw=(
                        "@AI_Anchor "
                        "開始 30/10/2/3"
                    ),
                )
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        mock_parse_command.assert_called_once_with(
            "@AI_Anchor 開始 30/10/2/3",
            bot_name="AI_Anchor",
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertIs(
            result[0].config,
            expected_config,
        )

    # --------------------------------------------------
    # Parser failure
    # --------------------------------------------------

    @patch(
        "handlers.response_handler.parse_command"
    )
    def test_parser_value_error_is_ignored(
        self,
        mock_parse_command,
    ) -> None:
        mock_parse_command.side_effect = (
            ValueError("invalid command")
        )

        event = {
            "data": [
                self._new_plurk(),
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )

    @patch(
        "handlers.response_handler.parse_command"
    )
    def test_parser_type_error_is_ignored(
        self,
        mock_parse_command,
    ) -> None:
        mock_parse_command.side_effect = (
            TypeError("invalid command")
        )

        event = {
            "data": [
                self._new_plurk(),
            ],
        }

        result = handle_realtime_event(
            event,
            bot_name=self.BOT_NAME,
        )

        self.assertEqual(
            result,
            [],
        )


if __name__ == "__main__":
    unittest.main()
