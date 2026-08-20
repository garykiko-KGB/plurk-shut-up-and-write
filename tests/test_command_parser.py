import unittest

from command_parser import (
    ActivityConfig,
    CommandParseError,
    parse_command,
)


class TestParseCommand(unittest.TestCase):
    """Tests for the Shut Up & Write! command parser."""

    # --------------------------------------------------
    # Default commands
    # --------------------------------------------------

    def test_start_command_uses_defaults(self):
        result = parse_command("@AI_Anchor 開始")

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=25,
                break_time=5,
                rounds=4,
                prepare_time=5,
            ),
        )

    def test_start_writing_command_uses_defaults(self):
        result = parse_command("@AI_Anchor 開始寫作")

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=25,
                break_time=5,
                rounds=4,
                prepare_time=5,
            ),
        )

    # --------------------------------------------------
    # Compact syntax
    # --------------------------------------------------

    def test_compact_syntax(self):
        result = parse_command(
            "@AI_Anchor 開始 20/5/6/3"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    def test_compact_syntax_with_writing(self):
        result = parse_command(
            "@AI_Anchor 開始寫作 20/5/6/3"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    def test_compact_syntax_all_maximum_values(self):
        result = parse_command(
            "@AI_Anchor 開始 30/30/30/30"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=30,
                break_time=30,
                rounds=30,
                prepare_time=30,
            ),
        )

    def test_compact_syntax_all_minimum_values(self):
        result = parse_command(
            "@AI_Anchor 開始 1/1/1/1"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=1,
                break_time=1,
                rounds=1,
                prepare_time=1,
            ),
        )

    # --------------------------------------------------
    # Friendly syntax
    # --------------------------------------------------

    def test_friendly_syntax(self):
        result = parse_command(
            "@AI_Anchor 開始寫作，工作20分鐘，"
            "休息5分鐘，6回合，3分鐘後開始"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    def test_friendly_syntax_without_writing_keyword(self):
        result = parse_command(
            "@AI_Anchor 開始，工作20分鐘，"
            "休息5分鐘，6回合，3分鐘後開始"
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )

    # --------------------------------------------------
    # Invalid values
    # --------------------------------------------------

    def test_zero_work_time_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 0/5/4/5")

    def test_zero_break_time_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/0/4/5")

    def test_zero_rounds_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/0/5")

    def test_zero_prepare_time_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/4/0")

    def test_work_time_above_maximum_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 31/5/4/5")

    def test_break_time_above_maximum_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/31/4/5")

    def test_rounds_above_maximum_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/31/5")

    def test_prepare_time_above_maximum_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/4/31")

    # --------------------------------------------------
    # Invalid compact syntax
    # --------------------------------------------------

    def test_missing_parameter_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/4")

    def test_too_many_parameters_are_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25/5/4/5/3")

    def test_decimal_parameter_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 25.5/5/4/5")

    def test_negative_parameter_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 -5/5/4/5")

    # --------------------------------------------------
    # Unsupported commands
    # --------------------------------------------------

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 今天想寫小說")

    def test_unknown_start_parameter_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@AI_Anchor 開始 隨便")

    def test_missing_bot_mention_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("開始 25/5/4/5")

    def test_wrong_bot_name_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command("@OtherBot 開始 25/5/4/5")

    # --------------------------------------------------
    # Input type
    # --------------------------------------------------

    def test_non_string_input_is_rejected(self):
        with self.assertRaises(CommandParseError):
            parse_command(None)

    # --------------------------------------------------
    # Whitespace
    # --------------------------------------------------

    def test_leading_and_trailing_whitespace(self):
        result = parse_command(
            "  @AI_Anchor 開始 20/5/6/3  "
        )

        self.assertEqual(
            result,
            ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=6,
                prepare_time=3,
            ),
        )


if __name__ == "__main__":
    unittest.main()
