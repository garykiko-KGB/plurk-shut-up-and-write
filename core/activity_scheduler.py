from datetime import datetime, timedelta, timezone
from enum import Enum

from activity import Activity, ActivityStatus


class ActivityTransition(str, Enum):
    """Description of an activity state transition."""

    START_WORK = "start_work"
    START_BREAK = "start_break"
    FINISH = "finish"


class ActivityScheduler:
    """
    Advance Activity state according to time.

    The scheduler does not:
        - create activities
        - store activities
        - send Plurk API requests
        - sleep or block

    All internal timestamps are expected to be timezone-aware.
    """

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC time."""

        return datetime.now(timezone.utc)

    @staticmethod
    def _validate_datetime(value: datetime) -> datetime:
        """
        Validate that a datetime is timezone-aware.

        Naive datetimes are rejected to prevent accidental mixing of
        UTC and local time.
        """

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "ActivityScheduler 需要 timezone-aware datetime。"
            )

        return value

    def initialize(
        self,
        activity: Activity,
        now: datetime | None = None,
    ) -> None:
        """
        Initialize the activity's first transition time.

        A newly created activity starts in PREPARING.

        The preparation phase always begins at activity.created_at.
        """

        if activity.status != ActivityStatus.PREPARING:
            return

        if activity.phase_started_at is not None:
            return

        current_time = (
            self._now()
            if now is None
            else self._validate_datetime(now)
        )

        created_at = self._validate_datetime(
            activity.created_at
        )

        # current_time is intentionally not used as the activity's
        # starting point. The activity timeline begins at created_at.
        #
        # current_time is evaluated here so callers still get immediate
        # validation of the supplied timestamp.
        _ = current_time

        activity.phase_started_at = created_at

        activity.next_transition_at = (
            created_at
            + timedelta(
                minutes=activity.config.prepare_time
            )
        )

    def advance(
        self,
        activity: Activity,
        now: datetime | None = None,
    ) -> list[ActivityTransition]:
        """
        Advance an activity according to the current time.

        Returns every transition that occurred during this check.

        The returned list may contain multiple transitions when the
        scheduler has not been checked for a while.
        """

        current_time = (
            self._now()
            if now is None
            else self._validate_datetime(now)
        )

        self.initialize(
            activity,
            current_time,
        )

        transitions: list[ActivityTransition] = []

        while (
            activity.status != ActivityStatus.FINISHED
            and activity.next_transition_at is not None
            and current_time >= activity.next_transition_at
        ):
            transition = self._advance_once(
                activity
            )

            if transition is None:
                break

            transitions.append(transition)

        return transitions

    def _advance_once(
        self,
        activity: Activity,
    ) -> ActivityTransition | None:
        """
        Advance one activity phase.

        Returns the transition that occurred.
        """

        if activity.status == ActivityStatus.PREPARING:
            return self._start_first_work_round(
                activity
            )

        if activity.status == ActivityStatus.WORKING:
            return self._handle_work_finished(
                activity
            )

        if activity.status == ActivityStatus.BREAK:
            return self._start_next_work_round(
                activity
            )

        return None

    def _start_first_work_round(
        self,
        activity: Activity,
    ) -> ActivityTransition:
        """Move from PREPARING to the first WORKING round."""

        transition_time = activity.next_transition_at

        if transition_time is None:
            raise RuntimeError(
                "Activity has no transition time."
            )

        activity.status = ActivityStatus.WORKING
        activity.current_round = 1
        activity.phase_started_at = transition_time

        activity.next_transition_at = (
            transition_time
            + timedelta(
                minutes=activity.config.work_time
            )
        )

        return ActivityTransition.START_WORK

    def _handle_work_finished(
        self,
        activity: Activity,
    ) -> ActivityTransition:
        """
        Handle the end of a work phase.

        The final work round ends the entire activity.
        Earlier rounds transition into BREAK.
        """

        transition_time = activity.next_transition_at

        if transition_time is None:
            raise RuntimeError(
                "Activity has no transition time."
            )

        if activity.current_round >= activity.config.rounds:
            activity.status = ActivityStatus.FINISHED
            activity.phase_started_at = transition_time
            activity.next_transition_at = None

            return ActivityTransition.FINISH

        activity.status = ActivityStatus.BREAK
        activity.phase_started_at = transition_time

        activity.next_transition_at = (
            transition_time
            + timedelta(
                minutes=activity.config.break_time
            )
        )

        return ActivityTransition.START_BREAK

    def _start_next_work_round(
        self,
        activity: Activity,
    ) -> ActivityTransition:
        """Move from BREAK to the next WORKING round."""

        transition_time = activity.next_transition_at

        if transition_time is None:
            raise RuntimeError(
                "Activity has no transition time."
            )

        activity.current_round += 1
        activity.status = ActivityStatus.WORKING
        activity.phase_started_at = transition_time

        activity.next_transition_at = (
            transition_time
            + timedelta(
                minutes=activity.config.work_time
            )
        )

        return ActivityTransition.START_WORK
