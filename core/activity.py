from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from parsers.command_parser import ActivityConfig


class ActivityStatus(str, Enum):
    """Current status of a focus activity."""

    PREPARING = "preparing"
    WORKING = "working"
    BREAK = "break"
    FINISHED = "finished"


@dataclass
class Activity:
    """State of one focus activity."""

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    owner_user_id: int

    # Display name of the activity owner on Plurk.
    owner_nick_name: str

    source_plurk_id: int

    # The Plurk created by the bot for this activity.
    activity_plurk_id: int | None = None

    # --------------------------------------------------
    # Activity configuration
    # --------------------------------------------------

    config: ActivityConfig = field(
        default_factory=ActivityConfig
    )

    # --------------------------------------------------
    # Runtime state
    # --------------------------------------------------

    status: ActivityStatus = ActivityStatus.PREPARING

    # Current work round.
    # During PREPARING this remains 0.
    # During WORKING / BREAK it is 1..config.rounds.
    current_round: int = 0

    # When the current phase started.
    phase_started_at: datetime | None = None

    # When the current phase is expected to end.
    next_transition_at: datetime | None = None

    # When this activity was created.
    # Internal timestamps are always UTC and timezone-aware.
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # --------------------------------------------------
    # State helpers
    # --------------------------------------------------

    @property
    def is_finished(self) -> bool:
        """Return True when the activity has finished."""

        return self.status == ActivityStatus.FINISHED

    @property
    def remaining_rounds(self) -> int:
        """Return the number of work rounds still remaining."""

        if self.status == ActivityStatus.PREPARING:
            return self.config.rounds

        if self.status == ActivityStatus.FINISHED:
            return 0

        return max(
            self.config.rounds - self.current_round + 1,
            0,
        )

    @property
    def is_working(self) -> bool:
        """Return True when currently in a work phase."""

        return self.status == ActivityStatus.WORKING

    @property
    def is_on_break(self) -> bool:
        """Return True when currently in a break phase."""

        return self.status == ActivityStatus.BREAK
