import unittest
from datetime import datetime

from core.activity import (
    Activity,
    ActivityStatus,
)
from parsers.command_parser import ActivityConfig


class TestActivity(unittest.TestCase):
    """Tests for the Activity data model."""

    def setUp(self) -> None:
        self.default_config = ActivityConfig()

        self.activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_activity_uses_default_config(self) -> None:
        self.assertEqual(
            self.activity.config,
            ActivityConfig(
                work_time=25,
                break_time=5,
                rounds=4,
                prepare_time=5,
            ),
        )

    def test_activity_identity(self) -> None:
        self.assertEqual(
            self.activity.owner_user_id,
            1001,
        )

        self.assertEqual(
            self.activity.source_plurk_id,
            2001,
        )

    def test_activity_plurk_id_is_optional(self) -> None:
        self.assertIsNone(
            self.activity.activity_plurk_id
        )

    def test_initial_status_is_preparing(self) -> None:
        self.assertEqual(
            self.activity.status,
            ActivityStatus.PREPARING,
        )

    def test_initial_round_is_zero(self) -> None:
        self.assertEqual(
            self.activity.current_round,
            0,
        )

    def test_initial_phase_times_are_none(self) -> None:
        self.assertIsNone(
            self.activity.phase_started_at
        )

        self.assertIsNone(
            self.activity.next_transition_at
        )

    def test_created_at_is_datetime(self) -> None:
        self.assertIsInstance(
            self.activity.created_at,
            datetime,
        )

    # --------------------------------------------------
    # Custom configuration
    # --------------------------------------------------

    def test_custom_config(self) -> None:
        config = ActivityConfig(
            work_time=20,
            break_time=10,
            rounds=6,
            prepare_time=3,
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=config,
        )

        self.assertEqual(
            activity.config,
            config,
        )

    # --------------------------------------------------
    # Status helpers
    # --------------------------------------------------

    def test_is_finished_for_preparing_activity(self) -> None:
        self.assertFalse(
            self.activity.is_finished
        )

    def test_is_finished_for_finished_activity(self) -> None:
        self.activity.status = ActivityStatus.FINISHED

        self.assertTrue(
            self.activity.is_finished
        )

    def test_is_working(self) -> None:
        self.activity.status = ActivityStatus.WORKING

        self.assertTrue(
            self.activity.is_working
        )

        self.assertFalse(
            self.activity.is_on_break
        )

    def test_is_on_break(self) -> None:
        self.activity.status = ActivityStatus.BREAK

        self.assertTrue(
            self.activity.is_on_break
        )

        self.assertFalse(
            self.activity.is_working
        )

    # --------------------------------------------------
    # Remaining rounds
    # --------------------------------------------------

    def test_remaining_rounds_during_preparing(self) -> None:
        self.assertEqual(
            self.activity.remaining_rounds,
            4,
        )

    def test_remaining_rounds_during_first_work_round(self) -> None:
        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 1

        self.assertEqual(
            self.activity.remaining_rounds,
            4,
        )

    def test_remaining_rounds_during_first_break(self) -> None:
        self.activity.status = ActivityStatus.BREAK
        self.activity.current_round = 1

        self.assertEqual(
            self.activity.remaining_rounds,
            4,
        )

    def test_remaining_rounds_during_second_work_round(self) -> None:
        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 2

        self.assertEqual(
            self.activity.remaining_rounds,
            3,
        )

    def test_remaining_rounds_during_second_break(self) -> None:
        self.activity.status = ActivityStatus.BREAK
        self.activity.current_round = 2

        self.assertEqual(
            self.activity.remaining_rounds,
            3,
        )

    def test_remaining_rounds_during_last_work_round(self) -> None:
        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 4

        self.assertEqual(
            self.activity.remaining_rounds,
            1,
        )

    def test_remaining_rounds_during_last_break(self) -> None:
        self.activity.status = ActivityStatus.BREAK
        self.activity.current_round = 4

        self.assertEqual(
            self.activity.remaining_rounds,
            1,
        )

    def test_remaining_rounds_when_finished(self) -> None:
        self.activity.status = ActivityStatus.FINISHED
        self.activity.current_round = 4

        self.assertEqual(
            self.activity.remaining_rounds,
            0,
        )

    # --------------------------------------------------
    # Different number of rounds
    # --------------------------------------------------

    def test_remaining_rounds_with_one_round(self) -> None:
        self.activity.config = ActivityConfig(
            work_time=25,
            break_time=5,
            rounds=1,
            prepare_time=5,
        )

        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 1

        self.assertEqual(
            self.activity.remaining_rounds,
            1,
        )

    def test_remaining_rounds_with_custom_round_count(self) -> None:
        self.activity.config = ActivityConfig(
            work_time=20,
            break_time=5,
            rounds=6,
            prepare_time=5,
        )

        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 4

        self.assertEqual(
            self.activity.remaining_rounds,
            3,
        )

    # --------------------------------------------------
    # Activity Plurk
    # --------------------------------------------------

    def test_activity_plurk_id_can_be_set(self) -> None:
        self.activity.activity_plurk_id = 9999

        self.assertEqual(
            self.activity.activity_plurk_id,
            9999,
        )


if __name__ == "__main__":
    unittest.main()
