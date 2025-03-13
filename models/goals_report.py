# models/goals_report.py
from typing import List
from models.goal import Goal

class GoalsReport:
    def __init__(self, goals, total_goal_value, total_penalty, goals_count):
        self.goals = List[Goal] = goals  # list of goal objects
        self.total_goal_value: float = total_goal_value
        self.total_penalty: float = total_penalty
        self.goals_count: int = goals_count

    @property
    def has_goals(self) -> bool:
        return self.goals_count > 0