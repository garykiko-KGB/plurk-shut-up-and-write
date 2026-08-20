import json
import logging
import os
import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
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

# Render provides PORT for Web Services.
# 10000 is used as a local/default fallback.
HEALTH_HOST = "0.0.0.0"
HEALTH_PORT = int(
    os.getenv("PORT", "10000")
)


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


class HealthRequestHandler(
    BaseHTTPRequestHandler
):
    """Minimal HTTP health endpoint for Render/UptimeRobot."""

    def do_GET(self) -> None:
        """Handle GET requests."""

        if self.path != "/health":
            self._send_json(
                status_code=404,
                payload={
                    "status": "not_found",
                },
            )
            return

        self._send_json(
            status_code=200,
            payload={
                "status": "ok",
                "service": "plurk-shut-up-and-write",
            },
        )

    def do_HEAD(self) -> None:
        """Handle HEAD requests."""

        if self.path != "/health":
            self.send_response(404)
            self.send_header(
                "Content-Length",
                "0",
            )
            self.end_headers()
            return

        body = json.dumps(
            {
                "status": "ok",
                "service": "plurk-shut-up-and-write",
            },
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        """
        Disable BaseHTTPRequestHandler's default stdout logging.

        Application logging is handled by the project's logger instead.
        """

        logger.debug(
            "Health HTTP: " + format,
            *args,
        )

    def _send_json(
        self,
        status_code: int,
        payload: dict[str, Any],
    ) -> None:
        """Send a JSON response."""

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(body)


class ShutUpAndWriteApp:
    """
    Application entry point for Shut Up & Write!.

    This class assembles the application components and coordinates
    their runtime execution.

    It also exposes a minimal HTTP health endpoint so the application
    can run as a Render Web Service and be monitored by UptimeRobot.

    It does not contain command parsing, Activity state logic,
    Plurk API implementation, or publishing-format logic.
    """

    def __init__(
        self,
        bot_name: str = BOT_NAME,
        scheduler_interval: float = (
            SCHEDULER_INTERVAL_SECONDS
        ),
        health_host: str = HEALTH_HOST,
        health_port: int = HEALTH_PORT,
    ) -> None:
        self.bot_name = bot_name
        self.scheduler_interval = (
            scheduler_interval
        )

        self.health_host = health_host
        self.health_port = health_port

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

        self._health_server: (
            ThreadingHTTPServer | None
        ) = None

        self._health_thread = (
            threading.Thread(
                target=self._run_health_server,
                name="health-server",
                daemon=True,
            )
        )

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

        logger.info(
            "Health endpoint：http://%s:%s/health",
            self.health_host,
            self.health_port,
        )

        self._health_thread.start()
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
        """Stop all application threads and servers."""

        already_stopped = (
            self._stop_event.is_set()
        )

        self._stop_event.set()

        if self._health_server is not None:
            try:
                self._health_server.shutdown()
            except Exception:
                logger.exception(
                    "停止 Health HTTP server 失敗。"
                )

            self._health_server.server_close()
            self._health_server = None

        if not already_stopped:
            logger.info(
                "Shut Up & Write! 已停止。"
            )

    # --------------------------------------------------
    # Health server
    # --------------------------------------------------

    def _run_health_server(self) -> None:
        """Run the HTTP health endpoint."""

        try:
            server = ThreadingHTTPServer(
                (
                    self.health_host,
                    self.health_port,
                ),
                HealthRequestHandler,
            )

            self._health_server = server

            logger.info(
                "Health HTTP server 啟動："
                "0.0.0.0:%s",
                self.health_port,
            )

            while not self._stop_event.is_set():
                server.handle_request()

        except OSError:
            logger.exception(
                "Health HTTP server 啟動失敗："
                "host=%s port=%s",
                self.health_host,
                self.health_port,
            )

            self._stop_event.set()

        except Exception:
            logger.exception(
                "Health HTTP server 發生未預期錯誤。"
            )

            self._stop_event.set()

        finally:
            if self._health_server is not None:
                try:
                    self._health_server.server_close()
                except Exception:
                    logger.exception(
                        "關閉 Health HTTP server 失敗。"
                    )

                self._health_server = None

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
        """Publish one activity transition to the activity Plurk."""

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
