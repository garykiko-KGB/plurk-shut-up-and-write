from activity import Activity


class ActivityManager:
    """Manage currently active activities."""

    def __init__(self) -> None:
        self._activities: dict[int, Activity] = {}

    # --------------------------------------------------
    # Activity registration
    # --------------------------------------------------

    def add(self, activity: Activity) -> None:
        """
        Register an activity.

        The source Plurk ID is used as the unique key because each
        activity originates from one specific source Plurk.
        """

        key = activity.source_plurk_id

        if key in self._activities:
            raise ValueError(
                f"Activity already exists for Plurk {key}."
            )

        self._activities[key] = activity

    def remove(self, source_plurk_id: int) -> Activity | None:
        """
        Remove and return an activity.

        Returns None when the activity does not exist.
        """

        return self._activities.pop(
            source_plurk_id,
            None,
        )

    # --------------------------------------------------
    # Activity lookup
    # --------------------------------------------------

    def get(
        self,
        source_plurk_id: int,
    ) -> Activity | None:
        """Get an activity by its source Plurk ID."""

        return self._activities.get(
            source_plurk_id
        )

    def exists(
        self,
        source_plurk_id: int,
    ) -> bool:
        """Return True when an activity exists for the Plurk."""

        return source_plurk_id in self._activities

    def get_by_owner(
        self,
        owner_user_id: int,
    ) -> list[Activity]:
        """Return all activities owned by a Plurk user."""

        return [
            activity
            for activity in self._activities.values()
            if activity.owner_user_id == owner_user_id
        ]

    # --------------------------------------------------
    # Collection access
    # --------------------------------------------------

    def get_all(self) -> list[Activity]:
        """Return all currently managed activities."""

        return list(
            self._activities.values()
        )

    def count(self) -> int:
        """Return the number of managed activities."""

        return len(self._activities)

    def clear(self) -> None:
        """Remove all managed activities."""

        self._activities.clear()
