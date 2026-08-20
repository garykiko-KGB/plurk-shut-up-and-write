import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from core.activity import Activity, ActivityConfig, ActivityStatus
from core.activity_scheduler import ActivityTransition
from handlers.response_handler import ParsedResponse


class TestShutUpAndWriteApp(unittest.TestCase):
    """Tests for the application entry point."""

    def setUp(self) -> None:
        self.channel = {
            "comet_server": "https://comet.example.com/comet",
            "channel_name": "generic-test-channel",
        }

        self.api_profile = {
            "id": 123456,
            "nick_name": "AI_Anchor",
        }

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_app_initializes_components(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp(
            bot_name="AI_Anchor",
            scheduler_interval=1.0,
        )

        mock_api.get_user_channel.assert_called_once_with()

        mock_realtime_class.assert_called_once_with(
            comet_server=self.channel[
                "comet_server"
            ],
            channel_name=self.channel[
                "channel_name"
            ],
        )

        mock_manager_class.assert_called_once_with()
        mock_scheduler_class.assert_called_once_with()

        mock_service_class.assert_called_once()

        mock_publisher_class.assert_called_once()

        self.assertEqual(
            app.bot_name,
            "AI_Anchor",
        )

        self.assertEqual(
            app.scheduler_interval,
            1.0,
        )

        self.assertIs(
            app.api,
            mock_api,
        )

    # --------------------------------------------------
    # Invalid realtime channel
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_invalid_realtime_channel_raises_error(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = {
            "channel_name": "generic-test-channel",
        }

        from app import ShutUpAndWriteApp

        with self.assertRaises(RuntimeError):
            ShutUpAndWriteApp()

        mock_realtime_class.assert_not_called()

    # --------------------------------------------------
    # Parsed response handling
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_parsed_response_creates_and_publishes_activity(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp
        from services.plurk_publisher import PublishedActivity

        app = ShutUpAndWriteApp()

        config = ActivityConfig(
            work_time=25,
            break_time=5,
            rounds=4,
            prepare_time=5,
        )

        parsed_response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始",
            config=config,
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            config=config,
            created_at=datetime(
                2026,
                8,
                20,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )

        mock_service = mock_service_class.return_value
        mock_service.create_activity.return_value = (
            activity
        )

        mock_publisher = (
            mock_publisher_class.return_value
        )

        published = PublishedActivity(
            activity_plurk_id=4001,
            activity_url=(
                "https://www.plurk.com/p/test"
            ),
            activity_response={
                "plurk_id": 4001,
            },
            source_response={
                "id": 5001,
            },
        )

        mock_publisher.publish_activity.return_value = (
            published
        )

        app._handle_parsed_response(
            parsed_response
        )

        mock_service.create_activity.assert_called_once_with(
            parsed_response
        )

        mock_publisher.publish_activity.assert_called_once_with(
            activity
        )

    # --------------------------------------------------
    # Activity creation failure
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_parsed_response_ignores_creation_failure(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        parsed_response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始",
            config=ActivityConfig(),
        )

        mock_service = mock_service_class.return_value
        mock_service.create_activity.side_effect = (
            ValueError("duplicate activity")
        )

        app._handle_parsed_response(
            parsed_response
        )

        mock_service.create_activity.assert_called_once_with(
            parsed_response
        )

        mock_publisher_class.return_value.publish_activity.assert_not_called()

    # --------------------------------------------------
    # Publishing failure
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_parsed_response_keeps_running_when_publish_fails(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        parsed_response = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始",
            config=ActivityConfig(),
        )

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
        )

        mock_service = mock_service_class.return_value
        mock_service.create_activity.return_value = (
            activity
        )

        mock_publisher = (
            mock_publisher_class.return_value
        )

        mock_publisher.publish_activity.side_effect = (
            RuntimeError("Plurk publish failed")
        )

        # The handler catches publish exceptions.
        app._handle_parsed_response(
            parsed_response
        )

        mock_service.create_activity.assert_called_once_with(
            parsed_response
        )

        mock_publisher.publish_activity.assert_called_once_with(
            activity
        )

    # --------------------------------------------------
    # Realtime event filtering
    # --------------------------------------------------

    @patch("app.handle_realtime_event")
    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_realtime_event_uses_handler(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
        mock_handler,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        event = {
            "new_offset": 10,
            "data": [],
        }

        mock_handler.return_value = []

        app._handle_realtime_event(
            event
        )

        mock_handler.assert_called_once_with(
            event,
            bot_name="AI_Anchor",
        )

    # --------------------------------------------------
    # Realtime event with parsed response
    # --------------------------------------------------

    @patch("app.handle_realtime_event")
    @patch("app.ShutUpAndWriteApp._handle_parsed_response")
    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_realtime_event_processes_all_parsed_responses(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
        mock_handle_response,
        mock_handler,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        first = ParsedResponse(
            user_id=1001,
            plurk_id=2001,
            response_id=3001,
            content_raw="@AI_Anchor 開始",
            config=ActivityConfig(),
        )

        second = ParsedResponse(
            user_id=1002,
            plurk_id=2002,
            response_id=3002,
            content_raw="@AI_Anchor 開始 20/5/3/5",
            config=ActivityConfig(
                work_time=20,
                break_time=5,
                rounds=3,
                prepare_time=5,
            ),
        )

        mock_handler.return_value = [
            first,
            second,
        ]

        app._handle_realtime_event(
            {
                "new_offset": 20,
                "data": [],
            }
        )

        self.assertEqual(
            mock_handle_response.call_count,
            2,
        )

        mock_handle_response.assert_any_call(
            first
        )

        mock_handle_response.assert_any_call(
            second
        )

    # --------------------------------------------------
    # Scheduler processing
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_advance_all_activities(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        first = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
        )

        second = Activity(
            owner_user_id=1002,
            source_plurk_id=2002,
        )

        mock_manager = (
            mock_manager_class.return_value
        )

        mock_manager.get_all.return_value = [
            first,
            second,
        ]

        mock_service = (
            mock_service_class.return_value
        )

        mock_service.advance_activity.side_effect = [
            [
                ActivityTransition.START_WORK
            ],
            [
                ActivityTransition.START_BREAK
            ],
        ]

        app._advance_all_activities()

        self.assertEqual(
            mock_service.advance_activity.call_count,
            2,
        )

        mock_service.advance_activity.assert_any_call(
            2001
        )

        mock_service.advance_activity.assert_any_call(
            2002
        )

    # --------------------------------------------------
    # Scheduler handles missing activity
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_advance_all_activities_ignores_missing_activity(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
        )

        mock_manager = (
            mock_manager_class.return_value
        )

        mock_manager.get_all.return_value = [
            activity,
        ]

        mock_service = (
            mock_service_class.return_value
        )

        mock_service.advance_activity.side_effect = (
            KeyError(2001)
        )

        # Should not raise.
        app._advance_all_activities()

    # --------------------------------------------------
    # Scheduler transition logging
    # --------------------------------------------------

    @patch("app.logger")
    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_handle_activity_transition_logs_transition(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
        mock_logger,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        app._handle_activity_transition(
            source_plurk_id=2001,
            transition=ActivityTransition.START_WORK,
        )

        mock_logger.info.assert_called_once()

        call_args = (
            mock_logger.info.call_args
        )

        self.assertIn(
            "Activity transition",
            call_args.args[0],
        )

    # --------------------------------------------------
    # Stop handling
    # --------------------------------------------------

    @patch("app.PlurkPublisher")
    @patch("app.ActivityService")
    @patch("app.ActivityScheduler")
    @patch("app.ActivityManager")
    @patch("app.PlurkRealtime")
    @patch("app.PlurkAPI")
    def test_stop_sets_stop_event(
        self,
        mock_api_class,
        mock_realtime_class,
        mock_manager_class,
        mock_scheduler_class,
        mock_service_class,
        mock_publisher_class,
    ) -> None:
        mock_api = mock_api_class.return_value
        mock_api.get_user_channel.return_value = (
            self.channel
        )

        from app import ShutUpAndWriteApp

        app = ShutUpAndWriteApp()

        self.assertFalse(
            app._stop_event.is_set()
        )

        app.stop()

        self.assertTrue(
            app._stop_event.is_set()
        )

    def test_activity_scheduler_status_helpers_are_consistent(
        self,
    ) -> None:
        activity = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
            status=ActivityStatus.PREPARING,
        )

        self.assertFalse(
            activity.is_working
        )

        self.assertFalse(
            activity.is_on_break
        )

        self.assertFalse(
            activity.is_finished
        )


if __name__ == "__main__":
    unittest.main()
