import unittest
from datetime import datetime, timedelta, timezone

from core.activity import (
    Activity,
    ActivityConfig,
    ActivityStatus,
)
from core.activity_scheduler import (
    ActivityScheduler,
    ActivityTransition,
)


class TestActivityScheduler(unittest.TestCase):
    """Tests for the ActivityScheduler."""

    def setUp(self) -> None:
        self.scheduler = ActivityScheduler()

        # All test timestamps use timezone-aware UTC datetime.
        self.base_time = datetime(
            2026,
            8,
            20,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        )

        self.activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            created_at=self.base_time,
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_initialize_sets_first_transition(self) -> None:
        self.scheduler.initialize(
            self.activity,
            self.base_time,
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.PREPARING,
        )

        self.assertEqual(
            self.activity.current_round,
            0,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            self.base_time,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            self.base_time + timedelta(
                minutes=5
            ),
        )

    def test_initialize_uses_activity_created_at(
        self,
    ) -> None:
        check_time = self.base_time + timedelta(
            minutes=2
        )

        self.scheduler.initialize(
            self.activity,
            check_time,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            self.base_time,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            self.base_time + timedelta(
                minutes=5
            ),
        )

    def test_initialize_does_not_reinitialize_activity(
        self,
    ) -> None:
        self.scheduler.initialize(
            self.activity,
            self.base_time,
        )

        original_phase_started_at = (
            self.activity.phase_started_at
        )

        original_next_transition_at = (
            self.activity.next_transition_at
        )

        self.scheduler.initialize(
            self.activity,
            self.base_time + timedelta(
                minutes=10
            ),
        )

        self.assertEqual(
            self.activity.phase_started_at,
            original_phase_started_at,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            original_next_transition_at,
        )

    def test_initialize_does_not_change_non_preparing_activity(
        self,
    ) -> None:
        self.activity.status = ActivityStatus.WORKING
        self.activity.current_round = 2

        self.scheduler.initialize(
            self.activity,
            self.base_time,
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            self.activity.current_round,
            2,
        )

        self.assertIsNone(
            self.activity.phase_started_at,
        )

        self.assertIsNone(
            self.activity.next_transition_at,
        )

    def test_naive_datetime_is_rejected(self) -> None:
        naive_time = datetime(
            2026,
            8,
            20,
            10,
            0,
            0,
        )

        with self.assertRaises(ValueError):
            self.scheduler.advance(
                self.activity,
                naive_time,
            )

    # --------------------------------------------------
    # Preparing -> Working
    # --------------------------------------------------

    def test_preparing_activity_starts_first_work_round(
        self,
    ) -> None:
        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        transitions = self.scheduler.advance(
            self.activity,
            prepare_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
            ],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            self.activity.current_round,
            1,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            prepare_end,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            prepare_end + timedelta(
                minutes=25
            ),
        )

    def test_preparing_activity_does_not_start_before_time(
        self,
    ) -> None:
        check_time = self.base_time + timedelta(
            minutes=4
        )

        transitions = self.scheduler.advance(
            self.activity,
            check_time,
        )

        self.assertEqual(
            transitions,
            [],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.PREPARING,
        )

        self.assertEqual(
            self.activity.current_round,
            0,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            self.base_time,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            self.base_time + timedelta(
                minutes=5
            ),
        )

    # --------------------------------------------------
    # Working -> Break
    # --------------------------------------------------

    def test_working_round_enters_break_after_work_time(
        self,
    ) -> None:
        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        work_end = prepare_end + timedelta(
            minutes=25
        )

        self.scheduler.advance(
            self.activity,
            prepare_end,
        )

        transitions = self.scheduler.advance(
            self.activity,
            work_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_BREAK,
            ],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.BREAK,
        )

        self.assertEqual(
            self.activity.current_round,
            1,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            work_end,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            work_end + timedelta(
                minutes=5
            ),
        )

    # --------------------------------------------------
    # Break -> Next Working Round
    # --------------------------------------------------

    def test_break_starts_next_work_round(
        self,
    ) -> None:
        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        work_end = prepare_end + timedelta(
            minutes=25
        )

        break_end = work_end + timedelta(
            minutes=5
        )

        self.scheduler.advance(
            self.activity,
            prepare_end,
        )

        self.scheduler.advance(
            self.activity,
            work_end,
        )

        transitions = self.scheduler.advance(
            self.activity,
            break_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
            ],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            self.activity.current_round,
            2,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            break_end,
        )

        self.assertEqual(
            self.activity.next_transition_at,
            break_end + timedelta(
                minutes=25
            ),
        )

    # --------------------------------------------------
    # Final round -> Finished
    # --------------------------------------------------

    def test_final_work_round_finishes_activity(
        self,
    ) -> None:
        config = ActivityConfig(
            work_time=10,
            break_time=5,
            rounds=1,
            prepare_time=5,
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=config,
            created_at=self.base_time,
        )

        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        work_end = prepare_end + timedelta(
            minutes=10
        )

        self.scheduler.advance(
            activity,
            prepare_end,
        )

        transitions = self.scheduler.advance(
            activity,
            work_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.FINISH,
            ],
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.FINISHED,
        )

        self.assertEqual(
            activity.current_round,
            1,
        )

        self.assertEqual(
            activity.phase_started_at,
            work_end,
        )

        self.assertIsNone(
            activity.next_transition_at,
        )

    def test_final_round_does_not_enter_break(
        self,
    ) -> None:
        config = ActivityConfig(
            work_time=10,
            break_time=5,
            rounds=1,
            prepare_time=5,
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=config,
            created_at=self.base_time,
        )

        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        work_end = prepare_end + timedelta(
            minutes=10
        )

        self.scheduler.advance(
            activity,
            prepare_end,
        )

        self.scheduler.advance(
            activity,
            work_end,
        )

        self.assertNotEqual(
            activity.status,
            ActivityStatus.BREAK,
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.FINISHED,
        )

    # --------------------------------------------------
    # Multiple transitions in one advance()
    # --------------------------------------------------

    def test_advance_can_process_multiple_transitions(
        self,
    ) -> None:
        """
        If the scheduler is checked after several phase boundaries,
        it should advance through every elapsed transition.
        """

        # Timeline:
        #
        # 10:00 prepare
        # 10:05 work #1
        # 10:30 break
        # 10:35 work #2
        #
        # Check at 10:35.

        check_time = self.base_time + timedelta(
            minutes=35
        )

        transitions = self.scheduler.advance(
            self.activity,
            check_time,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
                ActivityTransition.START_BREAK,
                ActivityTransition.START_WORK,
            ],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            self.activity.current_round,
            2,
        )

        self.assertEqual(
            self.activity.phase_started_at,
            self.base_time + timedelta(
                minutes=35
            ),
        )

        self.assertEqual(
            self.activity.next_transition_at,
            self.base_time + timedelta(
                minutes=60
            ),
        )

    def test_advance_can_skip_to_finished(
        self,
    ) -> None:
        """
        A delayed scheduler check should be able to process the entire
        activity and reach FINISHED in one call.
        """

        config = ActivityConfig(
            work_time=10,
            break_time=5,
            rounds=2,
            prepare_time=5,
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=config,
            created_at=self.base_time,
        )

        # Timeline:
        #
        # 10:00 prepare
        # 10:05 work #1
        # 10:15 break
        # 10:20 work #2
        # 10:30 finished

        finish_time = self.base_time + timedelta(
            minutes=30
        )

        transitions = self.scheduler.advance(
            activity,
            finish_time,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
                ActivityTransition.START_BREAK,
                ActivityTransition.START_WORK,
                ActivityTransition.FINISH,
            ],
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.FINISHED,
        )

        self.assertEqual(
            activity.current_round,
            2,
        )

        self.assertEqual(
            activity.phase_started_at,
            self.base_time + timedelta(
                minutes=30
            ),
        )

        self.assertIsNone(
            activity.next_transition_at,
        )

    # --------------------------------------------------
    # Finished activity
    # --------------------------------------------------

    def test_finished_activity_does_not_advance(
        self,
    ) -> None:
        self.activity.status = ActivityStatus.FINISHED
        self.activity.current_round = (
            self.activity.config.rounds
        )

        self.activity.phase_started_at = (
            self.base_time
        )

        self.activity.next_transition_at = None

        transitions = self.scheduler.advance(
            self.activity,
            self.base_time + timedelta(
                minutes=60
            ),
        )

        self.assertEqual(
            transitions,
            [],
        )

        self.assertEqual(
            self.activity.status,
            ActivityStatus.FINISHED,
        )

    # --------------------------------------------------
    # Custom configuration
    # --------------------------------------------------

    def test_scheduler_uses_activity_configuration(
        self,
    ) -> None:
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
            created_at=self.base_time,
        )

        prepare_end = self.base_time + timedelta(
            minutes=3
        )

        self.scheduler.advance(
            activity,
            prepare_end,
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            activity.next_transition_at,
            prepare_end + timedelta(
                minutes=20
            ),
        )

        work_end = prepare_end + timedelta(
            minutes=20
        )

        self.scheduler.advance(
            activity,
            work_end,
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.BREAK,
        )

        self.assertEqual(
            activity.next_transition_at,
            work_end + timedelta(
                minutes=10
            ),
        )


if __name__ == "__main__":
    unittest.main()
