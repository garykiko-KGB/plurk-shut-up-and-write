import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from core.activity import Activity, ActivityConfig, ActivityStatus
from core.activity_scheduler import ActivityTransition
from services.plurk_publisher import (
    PlurkPublisher,
    PublishedActivity,
)


class TestPlurkPublisher(unittest.TestCase):
    """Tests for the PlurkPublisher."""

    def setUp(self) -> None:
        self.api = Mock()

        self.publisher = PlurkPublisher(
            api=self.api,
        )

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

        self.activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=self.config,
            created_at=self.base_time,
        )

        self.activity.phase_started_at = (
            self.base_time
        )

        self.activity.next_transition_at = (
            self.base_time
            + timedelta(minutes=5)
        )

    # --------------------------------------------------
    # Activity content
    # --------------------------------------------------

    def test_build_activity_content(self) -> None:
        content = (
            self.publisher.build_activity_content(
                self.activity
            )
        )

        self.assertIn(
            "Shut Up & Write!",
            content,
        )

        self.assertIn(
            "發起人 ID：1001",
            content,
        )

        self.assertIn(
            "工作時間：25 分鐘",
            content,
        )

        self.assertIn(
            "休息時間：5 分鐘",
            content,
        )

        self.assertIn(
            "回合數：4 回合",
            content,
        )

        self.assertIn(
            "準備時間：5 分鐘",
            content,
        )

        # 10:05 UTC == 18:05 GMT+8
        self.assertIn(
            "2026-08-20 18:05",
            content,
        )

    def test_build_activity_content_with_no_start_time(
        self,
    ) -> None:
        self.activity.next_transition_at = None

        content = (
            self.publisher.build_activity_content(
                self.activity
            )
        )

        self.assertIn(
            "準備時間初始化中",
            content,
        )

    # --------------------------------------------------
    # Source response
    # --------------------------------------------------

    def test_build_source_response(self) -> None:
        activity_url = (
            "https://www.plurk.com/p/test123"
        )

        content = (
            self.publisher.build_source_response(
                self.activity,
                activity_url,
            )
        )

        self.assertIn(
            "活動已建立！",
            content,
        )

        self.assertIn(
            "發起人 ID：1001",
            content,
        )

        self.assertIn(
            "25 分鐘工作 / 5 分鐘休息",
            content,
        )

        self.assertIn(
            "共 4 回合",
            content,
        )

        self.assertIn(
            "準備 5 分鐘",
            content,
        )

        self.assertIn(
            activity_url,
            content,
        )

    # --------------------------------------------------
    # Plurk URL
    # --------------------------------------------------

    def test_build_plurk_url_for_base36_values(self) -> None:
        self.assertEqual(
            self.publisher.build_plurk_url(1),
            "https://www.plurk.com/p/1",
        )

        self.assertEqual(
            self.publisher.build_plurk_url(35),
            "https://www.plurk.com/p/z",
        )

        self.assertEqual(
            self.publisher.build_plurk_url(36),
            "https://www.plurk.com/p/10",
        )

    def test_build_plurk_url_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            self.publisher.build_plurk_url("123")

    def test_build_plurk_url_rejects_bool(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            self.publisher.build_plurk_url(True)

    def test_build_plurk_url_rejects_zero(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher.build_plurk_url(0)

    def test_build_plurk_url_rejects_negative_value(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher.build_plurk_url(-1)

    # --------------------------------------------------
    # Base36 conversion
    # --------------------------------------------------

    def test_base36_conversion(self) -> None:
        self.assertEqual(
            self.publisher._to_base36(0),
            "0",
        )

        self.assertEqual(
            self.publisher._to_base36(1),
            "1",
        )

        self.assertEqual(
            self.publisher._to_base36(10),
            "a",
        )

        self.assertEqual(
            self.publisher._to_base36(35),
            "z",
        )

        self.assertEqual(
            self.publisher._to_base36(36),
            "10",
        )

        self.assertEqual(
            self.publisher._to_base36(71),
            "1z",
        )

    def test_base36_rejects_negative_value(self) -> None:
        with self.assertRaises(ValueError):
            self.publisher._to_base36(-1)

    # --------------------------------------------------
    # Response ID extraction
    # --------------------------------------------------

    def test_extract_plurk_id_from_integer(
        self,
    ) -> None:
        result = (
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": 123456,
                }
            )
        )

        self.assertEqual(
            result,
            123456,
        )

    def test_extract_plurk_id_from_numeric_string(
        self,
    ) -> None:
        result = (
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": "123456",
                }
            )
        )

        self.assertEqual(
            result,
            123456,
        )

    def test_extract_plurk_id_rejects_missing_value(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._extract_plurk_id({})

    def test_extract_plurk_id_rejects_zero(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": 0,
                }
            )

    def test_extract_plurk_id_rejects_negative_value(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": -123,
                }
            )

    def test_extract_plurk_id_rejects_bool(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": True,
                }
            )

    def test_extract_plurk_id_rejects_invalid_string(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._extract_plurk_id(
                {
                    "plurk_id": "abc",
                }
            )

    # --------------------------------------------------
    # Time formatting
    # --------------------------------------------------

    def test_format_taipei_datetime(
        self,
    ) -> None:
        result = (
            self.publisher._format_taipei_datetime(
                datetime(
                    2026,
                    8,
                    20,
                    10,
                    30,
                    tzinfo=timezone.utc,
                )
            )
        )

        self.assertEqual(
            result,
            "2026-08-20 18:30",
        )

    def test_format_taipei_datetime_rejects_naive_datetime(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher._format_taipei_datetime(
                datetime(
                    2026,
                    8,
                    20,
                    10,
                    30,
                )
            )

    # --------------------------------------------------
    # Create activity Plurk
    # --------------------------------------------------

    def test_create_activity_plurk(
        self,
    ) -> None:
        self.api.add_plurk.return_value = {
            "plurk_id": 3001,
            "content": "活動",
        }

        result = (
            self.publisher.create_activity_plurk(
                self.activity
            )
        )

        self.assertEqual(
            result,
            {
                "plurk_id": 3001,
                "content": "活動",
            },
        )

        self.api.add_plurk.assert_called_once()

        kwargs = (
            self.api.add_plurk.call_args.kwargs
        )

        self.assertEqual(
            kwargs["qualifier"],
            "says",
        )

        self.assertEqual(
            kwargs["lang"],
            "tr_ch",
        )

        self.assertIn(
            "發起人 ID：1001",
            kwargs["content"],
        )

    # --------------------------------------------------
    # Reply to source Plurk
    # --------------------------------------------------

    def test_reply_to_source_plurk(
        self,
    ) -> None:
        self.api.add_response.return_value = {
            "id": 4001,
        }

        activity_url = (
            "https://www.plurk.com/p/3001"
        )

        result = (
            self.publisher.reply_to_source_plurk(
                self.activity,
                activity_url,
            )
        )

        self.assertEqual(
            result,
            {
                "id": 4001,
            },
        )

        self.api.add_response.assert_called_once_with(
            plurk_id=2001,
            content=unittest.mock.ANY,
            qualifier="says",
        )

        response_content = (
            self.api.add_response.call_args.kwargs[
                "content"
            ]
        )

        self.assertIn(
            "發起人 ID：1001",
            response_content,
        )

        self.assertIn(
            activity_url,
            response_content,
        )

    # --------------------------------------------------
    # Transition content
    # --------------------------------------------------

    def test_build_start_work_content(
        self,
    ) -> None:
        self.activity.status = (
            ActivityStatus.WORKING
        )
        self.activity.current_round = 1

        content = (
            self.publisher.build_transition_content(
                self.activity,
                ActivityTransition.START_WORK,
            )
        )

        self.assertEqual(
            content,
            (
                "🟢 第 1 回合開始！\n"
                "現在開始寫作 25 分鐘。"
            ),
        )

    def test_build_start_break_content(
        self,
    ) -> None:
        self.activity.status = (
            ActivityStatus.BREAK
        )
        self.activity.current_round = 1

        content = (
            self.publisher.build_transition_content(
                self.activity,
                ActivityTransition.START_BREAK,
            )
        )

        self.assertEqual(
            content,
            (
                "🔵 第 1 回合結束。\n"
                "休息 5 分鐘。"
            ),
        )

    def test_build_finish_content(
        self,
    ) -> None:
        self.activity.status = (
            ActivityStatus.FINISHED
        )
        self.activity.current_round = 4

        content = (
            self.publisher.build_transition_content(
                self.activity,
                ActivityTransition.FINISH,
            )
        )

        self.assertEqual(
            content,
            (
                "🏁 活動完成！\n"
                "發起人 ID：1001\n"
                "共完成 4 回合。"
            ),
        )

    def test_build_transition_content_rejects_unknown_transition(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.publisher.build_transition_content(
                self.activity,
                "unknown-transition",
            )

    # --------------------------------------------------
    # Publish transition
    # --------------------------------------------------

    def test_publish_start_work_transition(
        self,
    ) -> None:
        self.activity.activity_plurk_id = 3001
        self.activity.status = (
            ActivityStatus.WORKING
        )
        self.activity.current_round = 1

        self.api.add_response.return_value = {
            "id": 5001,
            "plurk_id": 3001,
        }

        result = (
            self.publisher.publish_transition(
                self.activity,
                ActivityTransition.START_WORK,
            )
        )

        self.assertEqual(
            result,
            {
                "id": 5001,
                "plurk_id": 3001,
            },
        )

        self.api.add_response.assert_called_once_with(
            plurk_id=3001,
            content=(
                "🟢 第 1 回合開始！\n"
                "現在開始寫作 25 分鐘。"
            ),
            qualifier="says",
        )

    def test_publish_start_break_transition(
        self,
    ) -> None:
        self.activity.activity_plurk_id = 3001
        self.activity.status = (
            ActivityStatus.BREAK
        )
        self.activity.current_round = 1

        self.api.add_response.return_value = {
            "id": 5002,
            "plurk_id": 3001,
        }

        result = (
            self.publisher.publish_transition(
                self.activity,
                ActivityTransition.START_BREAK,
            )
        )

        self.assertEqual(
            result,
            {
                "id": 5002,
                "plurk_id": 3001,
            },
        )

        self.api.add_response.assert_called_once_with(
            plurk_id=3001,
            content=(
                "🔵 第 1 回合結束。\n"
                "休息 5 分鐘。"
            ),
            qualifier="says",
        )

    def test_publish_finish_transition(
        self,
    ) -> None:
        self.activity.activity_plurk_id = 3001
        self.activity.status = (
            ActivityStatus.FINISHED
        )
        self.activity.current_round = 4

        self.api.add_response.return_value = {
            "id": 5003,
            "plurk_id": 3001,
        }

        result = (
            self.publisher.publish_transition(
                self.activity,
                ActivityTransition.FINISH,
            )
        )

        self.assertEqual(
            result,
            {
                "id": 5003,
                "plurk_id": 3001,
            },
        )

        self.api.add_response.assert_called_once_with(
            plurk_id=3001,
            content=(
                "🏁 活動完成！\n"
                "發起人 ID：1001\n"
                "共完成 4 回合。"
            ),
            qualifier="says",
        )

    def test_publish_transition_requires_activity_plurk(
        self,
    ) -> None:
        self.activity.activity_plurk_id = None

        with self.assertRaises(ValueError):
            self.publisher.publish_transition(
                self.activity,
                ActivityTransition.START_WORK,
            )

        self.api.add_response.assert_not_called()

    # --------------------------------------------------
    # Publish full activity
    # --------------------------------------------------

    def test_publish_activity(
        self,
    ) -> None:
        self.api.add_plurk.return_value = {
            "plurk_id": 3001,
            "content": "活動",
        }

        self.api.add_response.return_value = {
            "id": 4001,
            "plurk_id": 2001,
        }

        result = self.publisher.publish_activity(
            self.activity
        )

        self.assertIsInstance(
            result,
            PublishedActivity,
        )

        self.assertEqual(
            result.activity_plurk_id,
            3001,
        )

        self.assertEqual(
            result.activity_response,
            {
                "plurk_id": 3001,
                "content": "活動",
            },
        )

        self.assertEqual(
            result.source_response,
            {
                "id": 4001,
                "plurk_id": 2001,
            },
        )

        self.assertEqual(
            self.activity.activity_plurk_id,
            3001,
        )

        self.assertEqual(
            result.activity_url,
            self.publisher.build_plurk_url(
                3001
            ),
        )

        self.api.add_plurk.assert_called_once()
        self.api.add_response.assert_called_once()

    def test_publish_activity_sets_activity_plurk_id_before_reply(
        self,
    ) -> None:
        self.api.add_plurk.return_value = {
            "plurk_id": 3001,
        }

        self.api.add_response.return_value = {
            "id": 4001,
        }

        self.publisher.publish_activity(
            self.activity
        )

        self.assertEqual(
            self.activity.activity_plurk_id,
            3001,
        )

        response_content = (
            self.api.add_response.call_args.kwargs[
                "content"
            ]
        )

        self.assertIn(
            self.publisher.build_plurk_url(
                3001
            ),
            response_content,
        )

    # --------------------------------------------------
    # Publish failure behavior
    # --------------------------------------------------

    def test_activity_plurk_failure_prevents_source_reply(
        self,
    ) -> None:
        self.api.add_plurk.side_effect = (
            RuntimeError(
                "plurk creation failed"
            )
        )

        with self.assertRaises(RuntimeError):
            self.publisher.publish_activity(
                self.activity
            )

        self.api.add_response.assert_not_called()

        self.assertIsNone(
            self.activity.activity_plurk_id
        )

    def test_source_reply_failure_keeps_activity_plurk_id(
        self,
    ) -> None:
        self.api.add_plurk.return_value = {
            "plurk_id": 3001,
        }

        self.api.add_response.side_effect = (
            RuntimeError(
                "response failed"
            )
        )

        with self.assertRaises(RuntimeError):
            self.publisher.publish_activity(
                self.activity
            )

        self.assertEqual(
            self.activity.activity_plurk_id,
            3001,
        )

    def test_transition_publish_failure_propagates(
        self,
    ) -> None:
        self.activity.activity_plurk_id = 3001
        self.activity.status = (
            ActivityStatus.WORKING
        )
        self.activity.current_round = 1

        self.api.add_response.side_effect = (
            RuntimeError(
                "transition publish failed"
            )
        )

        with self.assertRaises(RuntimeError):
            self.publisher.publish_transition(
                self.activity,
                ActivityTransition.START_WORK,
            )

        self.api.add_response.assert_called_once()

    # --------------------------------------------------
    # Full content consistency
    # --------------------------------------------------

    def test_activity_and_source_content_use_same_owner_id(
        self,
    ) -> None:
        activity_content = (
            self.publisher.build_activity_content(
                self.activity
            )
        )

        source_content = (
            self.publisher.build_source_response(
                self.activity,
                "https://www.plurk.com/p/test",
            )
        )

        self.assertIn(
            "發起人 ID：1001",
            activity_content,
        )

        self.assertIn(
            "發起人 ID：1001",
            source_content,
        )


if __name__ == "__main__":
    unittest.main()
