# models/stats_snapshot.py
from typing import Optional


class StatsSnapshot:
    """
    Represents a snapshot of various stats for a user within a particular timeframe.
    """
    def __init__(
        self,
        total_goals_set: int,
        total_goals_finished: int,
        total_goals_failed: int,
        total_score_gained: float,
        total_penalties: float,
        avg_completion_rate: float,
        avg_daily_goals_set: float,
        avg_daily_goals_finished: float,
        period_name: str,  # e.g. 'week', 'month', 'quarter', 'year'
    ):
        self.total_goals_set = total_goals_set
        self.total_goals_finished = total_goals_finished
        self.total_goals_failed = total_goals_failed
        self.total_score_gained = total_score_gained
        self.total_penalties = total_penalties
        self.avg_completion_rate = avg_completion_rate
        self.avg_daily_goals_set = avg_daily_goals_set
        self.avg_daily_goals_finished = avg_daily_goals_finished
        self.period_name = period_name

    @property
    def success_rate(self) -> float:
        """Maybe a shorthand property for something specific you care about."""
        # For example:
        total_attempted = self.total_goals_finished + self.total_goals_failed
        return (self.total_goals_finished / total_attempted) * 100 if total_attempted else 0
