from datetime import datetime, timedelta
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
    """

    @staticmethod
    def _now() -> datetime:
        """Return the current local time."""

        return datetime.now()

    @staticmethod
    def _get_start_time(
        activity: Activity,
        now: datetime,
    ) -> datetime:
        """
        Determine the activity's actual starting point.

        Normally, Activity.created_at is the source of truth.

        If a caller supplies a simulated time earlier than created_at,
        use the supplied time instead. This allows deterministic tests
        with historical or simulated timestamps.
        """

        if activity.created_at <= now:
            return activity.created_at

        return now

    def initialize(
        self,
        activity: Activity,
        now: datetime | None = None,
    ) -> None:
        """
        Initialize the activity's first transition time.

        A newly created activity starts in PREPARING.
        The preparation phase begins at the activity's creation time.
        """

        if activity.status != ActivityStatus.PREPARING:
            return

        if activity.phase_started_at is not None:
            return

        current_time = now or self._now()

        start_time = self._get_start_time(
            activity,
            current_time,
        )

        activity.phase_started_at = start_time

        activity.next_transition_at = (
            start_time
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

        current_time = now or self._now()

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

        start_time = activity.next_transition_at

        if start_time is None:
            raise RuntimeError(
                "Activity has no transition time."
            )

        activity.status = ActivityStatus.WORKING
        activity.current_round = 1
        activity.phase_started_at = start_time

        activity.next_transition_at = (
            start_time
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
