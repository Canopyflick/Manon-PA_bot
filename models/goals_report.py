# models/goals_report.py


class GoalsReport:
    def __init__(self, goals, total_goal_value, total_penalty, goals_count):
        self.goals = goals  # list of goal objects
        self.total_goal_value = total_goal_value
        self.total_penalty = total_penalty
        self.goals_count = goals_count

    @property
    def has_goals(self):
        return self.goals_count > 0