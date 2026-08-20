import unittest
from datetime import datetime, timedelta, timezone

from core.activity import ActivityConfig, ActivityStatus
from core.activity_manager import ActivityManager
from core.activity_scheduler import (
    ActivityScheduler,
    ActivityTransition,
)
from core.activity_service import ActivityService
from handlers.response_handler import ParsedResponse


class FailingScheduler:
    """Scheduler stub used to test rollback behavior."""

    def initialize(
        self,
        activity,
        now=None,
    ) -> None:
        raise RuntimeError(
            "scheduler initialization failed"
        )

    def advance(
        self,
        activity,
        now=None,
    ):
        raise RuntimeError(
            "scheduler advance failed"
        )


class TestActivityService(unittest.TestCase):
    """Tests for ActivityService."""

    def setUp(self) -> None:
        self.manager = ActivityManager()
        self.scheduler = ActivityScheduler()

        self.service = ActivityService(
            activity_manager=self.manager,
            scheduler=self.scheduler,
        )

        # UTC, timezone-aware test time.
        self.base_time = datetime(
            2026,
            8,
            20,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        )

        self.config = ActivityConfig(
            work_time=25,
            break_time=5,
            rounds=4,
            prepare_time=5,
        )

        self.parsed_response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始寫作 25/5/4/5",
            config=self.config,
        )

    # --------------------------------------------------
    # Activity creation
    # --------------------------------------------------

    def test_create_activity(self) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        self.assertEqual(
            activity.owner_user_id,
            1001,
        )

        self.assertEqual(
            activity.source_plurk_id,
            2001,
        )

        self.assertEqual(
            activity.config,
            self.config,
        )

        self.assertEqual(
            activity.created_at,
            self.base_time,
        )

    def test_create_activity_initializes_scheduler(self) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.PREPARING,
        )

        self.assertEqual(
            activity.current_round,
            0,
        )

        self.assertEqual(
            activity.phase_started_at,
            self.base_time,
        )

        self.assertEqual(
            activity.next_transition_at,
            self.base_time + timedelta(
                minutes=5
            ),
        )

    def test_create_activity_registers_with_manager(self) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        self.assertIs(
            self.manager.get(2001),
            activity,
        )

        self.assertEqual(
            self.manager.count(),
            1,
        )

    def test_create_activity_with_current_time(self) -> None:
        activity = self.service.create_activity(
            self.parsed_response
        )

        self.assertIsNotNone(
            activity.created_at
        )

        self.assertIsNotNone(
            activity.phase_started_at
        )

        self.assertEqual(
            activity.created_at,
            activity.phase_started_at,
        )

        self.assertIsNotNone(
            activity.created_at.tzinfo
        )

    # --------------------------------------------------
    # Duplicate activity
    # --------------------------------------------------

    def test_create_duplicate_activity_raises_error(self) -> None:
        self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        with self.assertRaises(ValueError):
            self.service.create_activity(
                self.parsed_response,
                now=self.base_time + timedelta(
                    minutes=1
                ),
            )

        self.assertEqual(
            self.manager.count(),
            1,
        )

    def test_duplicate_detection_uses_source_plurk_id(
        self,
    ) -> None:
        self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        different_response = ParsedResponse(
            user_id=9999,
            plurk_id=2001,
            response_id=9999,
            content_raw="@AI_Anchor 開始",
            config=ActivityConfig(),
        )

        with self.assertRaises(ValueError):
            self.service.create_activity(
                different_response,
                now=self.base_time,
            )

        self.assertEqual(
            self.manager.count(),
            1,
        )

    # --------------------------------------------------
    # Datetime validation
    # --------------------------------------------------

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
            self.service.create_activity(
                self.parsed_response,
                now=naive_time,
            )

        self.assertEqual(
            self.manager.count(),
            0,
        )

    # --------------------------------------------------
    # Rollback
    # --------------------------------------------------

    def test_creation_rolls_back_when_scheduler_fails(
        self,
    ) -> None:
        failing_service = ActivityService(
            activity_manager=self.manager,
            scheduler=FailingScheduler(),
        )

        with self.assertRaises(RuntimeError):
            failing_service.create_activity(
                self.parsed_response,
                now=self.base_time,
            )

        self.assertEqual(
            self.manager.count(),
            0,
        )

        self.assertIsNone(
            self.manager.get(2001)
        )

    # --------------------------------------------------
    # Lookup
    # --------------------------------------------------

    def test_get_activity(self) -> None:
        created = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        result = self.service.get_activity(
            2001
        )

        self.assertIs(
            result,
            created,
        )

    def test_get_missing_activity_returns_none(
        self,
    ) -> None:
        result = self.service.get_activity(
            9999
        )

        self.assertIsNone(
            result
        )

    def test_get_activities_by_owner(self) -> None:
        first = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        second_response = ParsedResponse(
            user_id=1001,
            plurk_id=2002,
            response_id=3002,
            content_raw="@AI_Anchor 開始 20/10/6/3",
            config=ActivityConfig(
                work_time=20,
                break_time=10,
                rounds=6,
                prepare_time=3,
            ),
        )

        second = self.service.create_activity(
            second_response,
            now=self.base_time,
        )

        result = self.service.get_activities_by_owner(
            1001
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertIn(
            first,
            result,
        )

        self.assertIn(
            second,
            result,
        )

    # --------------------------------------------------
    # Removal
    # --------------------------------------------------

    def test_remove_activity(self) -> None:
        created = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        removed = self.service.remove_activity(
            2001
        )

        self.assertIs(
            removed,
            created,
        )

        self.assertEqual(
            self.manager.count(),
            0,
        )

    def test_remove_missing_activity_returns_none(
        self,
    ) -> None:
        result = self.service.remove_activity(
            9999
        )

        self.assertIsNone(
            result
        )

    # --------------------------------------------------
    # Activity advancement
    # --------------------------------------------------

    def test_advance_activity_to_first_work_round(
        self,
    ) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        prepare_end = self.base_time + timedelta(
            minutes=5
        )

        transitions = self.service.advance_activity(
            2001,
            now=prepare_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
            ],
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.WORKING,
        )

        self.assertEqual(
            activity.current_round,
            1,
        )

    def test_advance_activity_to_break(
        self,
    ) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        work_end = self.base_time + timedelta(
            minutes=30
        )

        transitions = self.service.advance_activity(
            2001,
            now=work_end,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
                ActivityTransition.START_BREAK,
            ],
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.BREAK,
        )

        self.assertEqual(
            activity.current_round,
            1,
        )

    def test_advance_missing_activity_raises_key_error(
        self,
    ) -> None:
        with self.assertRaises(KeyError):
            self.service.advance_activity(
                9999,
                now=self.base_time,
            )

    def test_advance_rejects_naive_datetime(
        self,
    ) -> None:
        self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        naive_time = datetime(
            2026,
            8,
            20,
            10,
            5,
            0,
        )

        with self.assertRaises(ValueError):
            self.service.advance_activity(
                2001,
                now=naive_time,
            )

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    def test_cleanup_finished_activity_does_nothing_when_active(
        self,
    ) -> None:
        activity = self.service.create_activity(
            self.parsed_response,
            now=self.base_time,
        )

        result = self.service.cleanup_finished_activity(
            2001
        )

        self.assertIsNone(
            result
        )

        self.assertIs(
            self.manager.get(2001),
            activity,
        )

    def test_cleanup_finished_activity_removes_finished_activity(
        self,
    ) -> None:
        config = ActivityConfig(
            work_time=10,
            break_time=5,
            rounds=1,
            prepare_time=5,
        )

        response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始 10/5/1/5",
            config=config,
        )

        activity = self.service.create_activity(
            response,
            now=self.base_time,
        )

        finish_time = self.base_time + timedelta(
            minutes=15
        )

        transitions = self.service.advance_activity(
            2001,
            now=finish_time,
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
                ActivityTransition.FINISH,
            ],
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.FINISHED,
        )

        removed = (
            self.service.cleanup_finished_activity(
                2001
            )
        )

        self.assertIs(
            removed,
            activity,
        )

        self.assertIsNone(
            self.manager.get(2001)
        )

    def test_cleanup_missing_activity_returns_none(
        self,
    ) -> None:
        result = (
            self.service.cleanup_finished_activity(
                9999
            )
        )

        self.assertIsNone(
            result
        )

    # --------------------------------------------------
    # Full service flow
    # --------------------------------------------------

    def test_full_activity_lifecycle(self) -> None:
        config = ActivityConfig(
            work_time=10,
            break_time=5,
            rounds=2,
            prepare_time=5,
        )

        response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始 10/5/2/5",
            config=config,
        )

        activity = self.service.create_activity(
            response,
            now=self.base_time,
        )

        self.assertEqual(
            activity.status,
            ActivityStatus.PREPARING,
        )

        transitions = self.service.advance_activity(
            2001,
            now=self.base_time + timedelta(
                minutes=5
            ),
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
            ],
        )

        transitions = self.service.advance_activity(
            2001,
            now=self.base_time + timedelta(
                minutes=15
            ),
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_BREAK,
            ],
        )

        transitions = self.service.advance_activity(
            2001,
            now=self.base_time + timedelta(
                minutes=20
            ),
        )

        self.assertEqual(
            transitions,
            [
                ActivityTransition.START_WORK,
            ],
        )

        transitions = self.service.advance_activity(
            2001,
            now=self.base_time + timedelta(
                minutes=30
            ),
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

        removed = (
            self.service.cleanup_finished_activity(
                2001
            )
        )

        self.assertIs(
            removed,
            activity,
        )

        self.assertEqual(
            self.manager.count(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
