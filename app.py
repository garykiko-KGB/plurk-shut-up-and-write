import logging
import threading
from typing import Any

from core.activity_manager import ActivityManager
from core.activity_scheduler import (
    ActivityScheduler,
    ActivityTransition,
)
from core.activity_service import ActivityService
from handlers.response_handler import handle_realtime_event
from services.plurk_api import PlurkAPI, PlurkAPIError
from services.plurk_publisher import PlurkPublisher
from services.plurk_realtime import (
    PlurkRealtime,
    PlurkRealtimeError,
)


BOT_NAME = "AI_Anchor"
SCHEDULER_INTERVAL_SECONDS = 1.0


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "[%(levelname)s] "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "shut-up-and-write"
)


class ShutUpAndWriteApp:
    """
    Application entry point for Shut Up & Write!.

    This class assembles the application components and coordinates
    their runtime execution.

    It does not contain command parsing, Activity state logic,
    Plurk API implementation, or publishing-format logic.
    """

    def __init__(
        self,
        bot_name: str = BOT_NAME,
        scheduler_interval: float = (
            SCHEDULER_INTERVAL_SECONDS
        ),
    ) -> None:
        self.bot_name = bot_name
        self.scheduler_interval = (
            scheduler_interval
        )

        # --------------------------------------------------
        # Infrastructure
        # --------------------------------------------------

        self.api = PlurkAPI()

        self.realtime_channel = (
            self.api.get_user_channel()
        )

        comet_server = (
            self.realtime_channel.get(
                "comet_server"
            )
        )

        channel_name = (
            self.realtime_channel.get(
                "channel_name"
            )
        )

        if not comet_server or not channel_name:
            raise RuntimeError(
                "Plurk 沒有回傳有效的 Realtime Channel。"
            )

        self.realtime = PlurkRealtime(
            comet_server=comet_server,
            channel_name=channel_name,
        )

        # --------------------------------------------------
        # Core components
        # --------------------------------------------------

        self.activity_manager = (
            ActivityManager()
        )

        self.activity_scheduler = (
            ActivityScheduler()
        )

        self.activity_service = (
            ActivityService(
                activity_manager=(
                    self.activity_manager
                ),
                scheduler=(
                    self.activity_scheduler
                ),
            )
        )

        self.publisher = PlurkPublisher(
            api=self.api
        )

        # --------------------------------------------------
        # Runtime control
        # --------------------------------------------------

        self._stop_event = threading.Event()

        self._realtime_thread = (
            threading.Thread(
                target=self._run_realtime,
                name="plurk-realtime",
                daemon=True,
            )
        )

        self._scheduler_thread = (
            threading.Thread(
                target=self._run_scheduler,
                name="activity-scheduler",
                daemon=True,
            )
        )

    # --------------------------------------------------
    # Application lifecycle
    # --------------------------------------------------

    def run(self) -> None:
        """Start the application and keep it running."""

        logger.info(
            "Shut Up & Write! 啟動。"
        )

        logger.info(
            "Bot：@%s",
            self.bot_name,
        )

        self._realtime_thread.start()
        self._scheduler_thread.start()

        try:
            while not self._stop_event.wait(
                timeout=1
            ):
                pass

        except KeyboardInterrupt:
            logger.info(
                "收到停止訊號。"
            )

        finally:
            self.stop()

    def stop(self) -> None:
        """Stop application threads."""

        if self._stop_event.is_set():
            return

        self._stop_event.set()

        logger.info(
            "Shut Up & Write! 已停止。"
        )

    # --------------------------------------------------
    # Realtime thread
    # --------------------------------------------------

    def _run_realtime(self) -> None:
        """Listen for Plurk realtime events."""

        logger.info(
            "開始監聽 Plurk Realtime。"
        )

        while not self._stop_event.is_set():
            try:
                for event in self.realtime.listen():
                    if self._stop_event.is_set():
                        break

                    self._handle_realtime_event(
                        event
                    )

            except PlurkRealtimeError as exc:
                logger.error(
                    "Plurk Realtime 錯誤：%s",
                    exc,
                )

                self._wait_before_retry()

            except Exception:
                logger.exception(
                    "Realtime thread 發生未預期錯誤。"
                )

                self._wait_before_retry()

    def _handle_realtime_event(
        self,
        event: dict[str, Any],
    ) -> None:
        """Process one realtime payload."""

        parsed_responses = (
            handle_realtime_event(
                event,
                bot_name=self.bot_name,
            )
        )

        if not parsed_responses:
            return

        for parsed_response in parsed_responses:
            self._handle_parsed_response(
                parsed_response
            )

    def _handle_parsed_response(
        self,
        parsed_response,
    ) -> None:
        """Create and publish an activity."""

        logger.info(
            "收到活動指令："
            "user=%s plurk=%s response=%s",
            parsed_response.user_id,
            parsed_response.plurk_id,
            parsed_response.response_id,
        )

        try:
            activity = (
                self.activity_service.create_activity(
                    parsed_response
                )
            )

        except ValueError as exc:
            logger.warning(
                "無法建立活動：%s",
                exc,
            )
            return

        try:
            published = (
                self.publisher.publish_activity(
                    activity
                )
            )

        except Exception:
            logger.exception(
                "活動建立成功，但發布到 Plurk 失敗："
                "plurk=%s",
                activity.source_plurk_id,
            )
            return

        logger.info(
            "活動已發布："
            "source_plurk=%s "
            "activity_plurk=%s "
            "url=%s",
            activity.source_plurk_id,
            published.activity_plurk_id,
            published.activity_url,
        )

    # --------------------------------------------------
    # Scheduler thread
    # --------------------------------------------------

    def _run_scheduler(self) -> None:
        """
        Periodically advance all active activities.

        Every transition is passed to PlurkPublisher so that the
        activity Plurk receives the corresponding announcement.
        """

        logger.info(
            "活動 Scheduler 已啟動。"
        )

        while not self._stop_event.wait(
            timeout=self.scheduler_interval
        ):
            self._advance_all_activities()

    def _advance_all_activities(self) -> None:
        """Advance every currently managed Activity."""

        activities = (
            self.activity_manager.get_all()
        )

        for activity in activities:
            try:
                transitions = (
                    self.activity_service.advance_activity(
                        activity.source_plurk_id
                    )
                )

            except KeyError:
                continue

            except Exception:
                logger.exception(
                    "Activity 推進失敗："
                    "plurk=%s",
                    activity.source_plurk_id,
                )
                continue

            for transition in transitions:
                self._handle_activity_transition(
                    activity,
                    transition,
                )

            if activity.is_finished:
                # Finished activities are intentionally kept for now.
                # Cleanup policy will be added together with final
                # activity result handling.
                pass

    def _handle_activity_transition(
        self,
        activity,
        transition: ActivityTransition,
    ) -> None:
        """
        Publish one activity transition to the activity Plurk.
        """

        try:
            response = (
                self.publisher.publish_transition(
                    activity,
                    transition,
                )
            )

        except ValueError as exc:
            logger.warning(
                "無法發布 Activity transition："
                "plurk=%s transition=%s error=%s",
                activity.source_plurk_id,
                transition.value,
                exc,
            )
            return

        except Exception:
            logger.exception(
                "Activity transition 發布失敗："
                "plurk=%s transition=%s",
                activity.source_plurk_id,
                transition.value,
            )
            return

        logger.info(
            "Activity transition 已發布："
            "plurk=%s "
            "activity_plurk=%s "
            "transition=%s "
            "response=%s",
            activity.source_plurk_id,
            activity.activity_plurk_id,
            transition.value,
            response,
        )

    # --------------------------------------------------
    # Retry handling
    # --------------------------------------------------

    def _wait_before_retry(
        self,
        seconds: float = 5.0,
    ) -> None:
        """Wait before reconnecting after a realtime failure."""

        self._stop_event.wait(
            timeout=seconds
        )


def main() -> None:
    """Application entry point."""

    try:
        app = ShutUpAndWriteApp()
        app.run()

    except PlurkAPIError as exc:
        logger.error(
            "Plurk API 初始化失敗：%s",
            exc,
        )

    except Exception:
        logger.exception(
            "應用程式啟動失敗。"
        )


if __name__ == "__main__":
    main()
