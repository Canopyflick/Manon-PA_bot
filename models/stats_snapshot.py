# models/stats_snapshot.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class StatsSnapshot:
    """
    Represents a snapshot of various stats for a user within a particular timeframe.
    """
    total_goals_set: int
    total_goals_finished: int
    total_goals_failed: int
    total_score_gained: float
    total_penalties: float
    avg_completion_rate: float
    avg_daily_goals_set: float
    avg_daily_goals_finished: float
    period_name: str  # e.g. 'week', 'month', 'quarter', 'year'

    @property
    def success_rate(self) -> float:
        """Maybe a shorthand property for something specific you care about."""
        # For example:
        total_attempted = self.total_goals_finished + self.total_goals_failed
        return (self.total_goals_finished / total_attempted) * 100 if total_attempted else 0
