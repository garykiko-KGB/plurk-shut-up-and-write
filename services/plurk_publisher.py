from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from core.activity import Activity
from core.activity_scheduler import ActivityTransition
from services.plurk_api import PlurkAPI


TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")
PLURK_BASE_URL = "https://www.plurk.com/p"


@dataclass(frozen=True)
class PublishedActivity:
    """Result of publishing an activity to Plurk."""

    activity_plurk_id: int
    activity_url: str
    activity_response: dict[str, Any]
    source_response: dict[str, Any]


class PlurkPublisher:
    """
    Publish writing activities to Plurk.

    Responsibilities:
        - Build activity Plurk content.
        - Create the activity Plurk.
        - Build the reply for the source Plurk.
        - Reply to the source Plurk with the activity URL.
        - Publish activity state transition announcements.

    This class does not:
        - manage Activity objects
        - advance activity state
        - manage timers
        - parse commands
        - perform OAuth directly
    """

    def __init__(
        self,
        api: PlurkAPI,
    ) -> None:
        self.api = api

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def publish_activity(
        self,
        activity: Activity,
    ) -> PublishedActivity:
        """
        Publish an activity Plurk and reply to the source Plurk.

        The activity Plurk is created first so its URL can be included
        in the response to the original command.

        If the activity Plurk is created successfully but the source
        response fails, the activity Plurk remains published and its
        ID is still stored in the Activity object.
        """

        activity_response = self.create_activity_plurk(
            activity
        )

        activity_plurk_id = self._extract_plurk_id(
            activity_response
        )

        activity.activity_plurk_id = activity_plurk_id

        activity_url = self.build_plurk_url(
            activity_plurk_id
        )

        source_response = self.reply_to_source_plurk(
            activity,
            activity_url,
        )

        return PublishedActivity(
            activity_plurk_id=activity_plurk_id,
            activity_url=activity_url,
            activity_response=activity_response,
            source_response=source_response,
        )

    def publish_transition(
        self,
        activity: Activity,
        transition: ActivityTransition,
    ) -> dict[str, Any]:
        """
        Publish one Activity transition as a response
        to the activity Plurk.

        The activity must already have an activity_plurk_id.
        """

        activity_plurk_id = (
            activity.activity_plurk_id
        )

        if activity_plurk_id is None:
            raise ValueError(
                "Activity 尚未建立活動噗，"
                "無法發布 transition。"
            )

        content = self.build_transition_content(
            activity,
            transition,
        )

        return self.api.add_response(
            plurk_id=activity_plurk_id,
            content=content,
            qualifier="says",
        )

    # --------------------------------------------------
    # Activity Plurk
    # --------------------------------------------------

    def create_activity_plurk(
        self,
        activity: Activity,
    ) -> dict[str, Any]:
        """Create the dedicated activity Plurk."""

        content = self.build_activity_content(
            activity
        )

        return self.api.add_plurk(
            content=content,
            qualifier="says",
            lang="tr_ch",
        )

    def build_activity_content(
        self,
        activity: Activity,
    ) -> str:
        """
        Build the initial activity Plurk content.

        The displayed start time is converted from UTC
        to Taiwan local time.
        """

        config = activity.config
        start_time = activity.next_transition_at

        start_text = "準備時間初始化中"

        if start_time is not None:
            start_text = self._format_taipei_datetime(
                start_time
            )

        return (
            "📝 Shut Up & Write! 寫作活動\n"
            "\n"
            f"👤 發起人 ID：{activity.owner_user_id}\n"
            f"⏱ 工作時間：{config.work_time} 分鐘\n"
            f"☕ 休息時間：{config.break_time} 分鐘\n"
            f"🔁 回合數：{config.rounds} 回合\n"
            f"⏳ 準備時間：{config.prepare_time} 分鐘\n"
            f"🕒 預計開始：{start_text}\n"
            "\n"
            "想一起寫的人可以加入；"
            "想安靜做事也完全沒問題。\n"
            "活動開始後會依照設定進行計時。"
        )

    # --------------------------------------------------
    # Source Plurk response
    # --------------------------------------------------

    def reply_to_source_plurk(
        self,
        activity: Activity,
        activity_url: str,
    ) -> dict[str, Any]:
        """Reply to the original Plurk with the activity URL."""

        content = self.build_source_response(
            activity,
            activity_url,
        )

        return self.api.add_response(
            plurk_id=activity.source_plurk_id,
            content=content,
            qualifier="says",
        )

    def build_source_response(
        self,
        activity: Activity,
        activity_url: str,
    ) -> str:
        """Build the response to the original command Plurk."""

        config = activity.config

        return (
            "活動已建立！\n"
            f"👤 發起人 ID：{activity.owner_user_id}\n"
            f"⏱ {config.work_time} 分鐘工作 / "
            f"{config.break_time} 分鐘休息\n"
            f"🔁 共 {config.rounds} 回合\n"
            f"⏳ 準備 {config.prepare_time} 分鐘\n"
            f"📌 活動噗：{activity_url}"
        )

    # --------------------------------------------------
    # Transition announcements
    # --------------------------------------------------

    def build_transition_content(
        self,
        activity: Activity,
        transition: ActivityTransition,
    ) -> str:
        """Build the announcement for an activity transition."""

        config = activity.config

        if transition == ActivityTransition.START_WORK:
            return self._build_start_work_content(
                activity
            )

        if transition == ActivityTransition.START_BREAK:
            return self._build_start_break_content(
                activity
            )

        if transition == ActivityTransition.FINISH:
            return self._build_finish_content(
                activity
            )

        raise ValueError(
            f"不支援的 ActivityTransition："
            f"{transition}"
        )

    def _build_start_work_content(
        self,
        activity: Activity,
    ) -> str:
        """Build the announcement for the start of a work round."""

        config = activity.config

        return (
            f"🟢 第 {activity.current_round} "
            f"回合開始！\n"
            f"現在開始寫作 {config.work_time} 分鐘。"
        )

    def _build_start_break_content(
        self,
        activity: Activity,
    ) -> str:
        """Build the announcement for the start of a break."""

        config = activity.config

        return (
            f"🔵 第 {activity.current_round} "
            f"回合結束。\n"
            f"休息 {config.break_time} 分鐘。"
        )

    def _build_finish_content(
        self,
        activity: Activity,
    ) -> str:
        """Build the final activity announcement."""

        return (
            "🏁 活動完成！\n"
            f"發起人 ID：{activity.owner_user_id}\n"
            f"共完成 {activity.config.rounds} 回合。"
        )

    # --------------------------------------------------
    # Plurk URL
    # --------------------------------------------------

    @classmethod
    def build_plurk_url(
        cls,
        plurk_id: int,
    ) -> str:
        """
        Build a web URL from the numeric Plurk ID.

        Plurk web URLs use the base-36 representation
        of plurk_id.
        """

        if not isinstance(plurk_id, int):
            raise TypeError(
                "plurk_id 必須是 int。"
            )

        if isinstance(plurk_id, bool):
            raise TypeError(
                "plurk_id 必須是整數，不接受 bool。"
            )

        if plurk_id <= 0:
            raise ValueError(
                "plurk_id 必須是正整數。"
            )

        return (
            f"{PLURK_BASE_URL}/"
            f"{cls._to_base36(plurk_id)}"
        )

    @staticmethod
    def _to_base36(
        value: int,
    ) -> str:
        """Convert a non-negative integer to lowercase base-36."""

        if value < 0:
            raise ValueError(
                "Base36 不接受負數。"
            )

        if value == 0:
            return "0"

        digits = (
            "0123456789"
            "abcdefghijklmnopqrstuvwxyz"
        )

        result: list[str] = []

        while value:
            value, remainder = divmod(
                value,
                36,
            )
            result.append(
                digits[remainder]
            )

        result.reverse()

        return "".join(result)

    # --------------------------------------------------
    # Response validation
    # --------------------------------------------------

    @staticmethod
    def _extract_plurk_id(
        response: dict[str, Any],
    ) -> int:
        """Extract and validate the new Plurk ID."""

        value = response.get("plurk_id")

        if isinstance(value, bool):
            raise ValueError(
                "Plurk API 回應的 plurk_id 無效。"
            )

        if isinstance(value, int):
            plurk_id = value

        elif (
            isinstance(value, str)
            and value.isdigit()
        ):
            plurk_id = int(value)

        else:
            raise ValueError(
                "Plurk API 回應缺少有效的 plurk_id。"
            )

        if plurk_id <= 0:
            raise ValueError(
                "Plurk API 回應的 plurk_id "
                "必須是正整數。"
            )

        return plurk_id

    # --------------------------------------------------
    # Date / time formatting
    # --------------------------------------------------

    @staticmethod
    def _format_taipei_datetime(
        value,
    ) -> str:
        """
        Convert an aware datetime to Taiwan local time.

        Internal Activity timestamps are stored as
        timezone-aware UTC datetimes.
        """

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "Activity 時間必須是 timezone-aware datetime。"
            )

        taipei_time = value.astimezone(
            TAIPEI_TIMEZONE
        )

        return taipei_time.strftime(
            "%Y-%m-%d %H:%M"
        )
