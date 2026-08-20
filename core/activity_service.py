from datetime import datetime, timezone

from activity import Activity
from activity_manager import ActivityManager
from activity_scheduler import ActivityScheduler
from response_handler import ParsedResponse


class ActivityService:
    """
    Application service for creating and managing writing activities.

    This service coordinates:
        - ParsedResponse
        - Activity
        - ActivityManager
        - ActivityScheduler

    It does not:
        - call Plurk APIs
        - publish Plurks
        - parse commands
        - run a timer loop
    """

    def __init__(
        self,
        activity_manager: ActivityManager,
        scheduler: ActivityScheduler,
    ) -> None:
        self.activity_manager = activity_manager
        self.scheduler = scheduler

    # --------------------------------------------------
    # Activity creation
    # --------------------------------------------------

    def create_activity(
        self,
        parsed_response: ParsedResponse,
        now: datetime | None = None,
    ) -> Activity:
        """
        Create an Activity from a successfully parsed command.

        The activity's source Plurk is used as its unique identity.

        Raises:
            ValueError:
                If an activity already exists for the source Plurk.
                If the supplied datetime is timezone-naive.
        """

        source_plurk_id = parsed_response.plurk_id

        if self.activity_manager.exists(
            source_plurk_id
        ):
            raise ValueError(
                "此 Plurk 已經存在一場活動："
                f"{source_plurk_id}"
            )

        created_at = (
            datetime.now(timezone.utc)
            if now is None
            else self._validate_datetime(now)
        )

        activity = Activity(
            owner_user_id=parsed_response.user_id,
            source_plurk_id=source_plurk_id,
            config=parsed_response.config,
            created_at=created_at,
        )

        # Register the activity before initializing the scheduler.
        self.activity_manager.add(activity)

        try:
            self.scheduler.initialize(
                activity,
                created_at,
            )
        except Exception:
            # Roll back registration if initialization fails.
            self.activity_manager.remove(
                source_plurk_id
            )
            raise

        return activity

    # --------------------------------------------------
    # Activity lookup
    # --------------------------------------------------

    def get_activity(
        self,
        source_plurk_id: int,
    ) -> Activity | None:
        """Return an activity by its source Plurk ID."""

        return self.activity_manager.get(
            source_plurk_id
        )

    def get_activities_by_owner(
        self,
        owner_user_id: int,
    ) -> list[Activity]:
        """Return all activities owned by a user."""

        return self.activity_manager.get_by_owner(
            owner_user_id
        )

    # --------------------------------------------------
    # Activity removal
    # --------------------------------------------------

    def remove_activity(
        self,
        source_plurk_id: int,
    ) -> Activity | None:
        """
        Remove an activity from the active activity manager.

        This does not modify the Activity's state.
        """

        return self.activity_manager.remove(
            source_plurk_id
        )

    # --------------------------------------------------
    # Activity advancement
    # --------------------------------------------------

    def advance_activity(
        self,
        source_plurk_id: int,
        now: datetime | None = None,
    ):
        """
        Advance one managed activity according to time.

        Returns the transitions produced by the scheduler.

        Raises:
            KeyError:
                If the requested activity does not exist.
        """

        activity = self.activity_manager.get(
            source_plurk_id
        )

        if activity is None:
            raise KeyError(
                f"找不到活動：{source_plurk_id}"
            )

        current_time = (
            datetime.now(timezone.utc)
            if now is None
            else self._validate_datetime(now)
        )

        return self.scheduler.advance(
            activity,
            current_time,
        )

    # --------------------------------------------------
    # Finished activities
    # --------------------------------------------------

    def cleanup_finished_activity(
        self,
        source_plurk_id: int,
    ) -> Activity | None:
        """
        Remove an activity if it has already finished.

        Returns the removed Activity when cleanup occurred.
        Returns None when the activity does not exist or is not finished.
        """

        activity = self.activity_manager.get(
            source_plurk_id
        )

        if activity is None:
            return None

        if not activity.is_finished:
            return None

        return self.activity_manager.remove(
            source_plurk_id
        )

    # --------------------------------------------------
    # Time validation
    # --------------------------------------------------

    @staticmethod
    def _validate_datetime(
        value: datetime,
    ) -> datetime:
        """
        Ensure a datetime is timezone-aware.

        Internal activity timestamps use timezone-aware UTC datetimes.
        """

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "ActivityService 需要 timezone-aware datetime。"
            )

        return value
