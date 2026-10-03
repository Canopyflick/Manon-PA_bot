# LLMs/test_goal_upgrades.py
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from features.goals.cancel import cancellation_charge, charge_label, pick_charge_row
from features.goals.finder import mentioned_goal_ids
from features.goals.queries import collapse_goal_candidates
from utils.helpers import format_for_llm, format_when, parse_datetime_loose

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 10, 3, 16, 0, tzinfo=BERLIN)


def _row(goal_id, group_id=None, deadline=None, description="Goal", status="pending", recurrence="one-time"):
    return {
        "goal_id": goal_id,
        "group_id": group_id,
        "goal_description": description,
        "status": status,
        "deadline": deadline,
        "set_time": NOW,
        "recurrence_type": recurrence,
        "timeframe": "by_date",
    }


class DateFormatTests(unittest.TestCase):
    def test_parse_offset_without_colon(self):
        parsed = parse_datetime_loose("2026-10-05T22:22:00+0200")
        self.assertEqual(parsed, datetime(2026, 10, 5, 22, 22, tzinfo=BERLIN))

    def test_parse_strips_brackets_and_assumes_berlin_when_naive(self):
        parsed = parse_datetime_loose("[2026-10-05T22:22:00]")
        self.assertEqual(parsed, datetime(2026, 10, 5, 22, 22, tzinfo=BERLIN))

    def test_format_when_buckets(self):
        self.assertEqual(format_when("2026-10-03T22:22:00+0200", now=NOW), "today 22:22")
        self.assertEqual(format_when("2026-10-04T07:30:00+0200", now=NOW), "tomorrow 07:30")
        self.assertEqual(format_when("2026-10-02T11:11:00+0200", now=NOW), "yesterday 11:11")
        self.assertEqual(format_when("2026-10-08T22:22:00+0200", now=NOW), "Thu 22:22")
        self.assertEqual(format_when("2026-10-09T22:22:00+0200", now=NOW), "Fri 22:22")
        self.assertEqual(format_when("2026-10-10T22:22:00+0200", now=NOW), "Sat 10 Oct, 22:22")
        self.assertEqual(format_when("2027-01-12T09:00:00+0100", now=NOW), "Tue 12 Jan 2027, 09:00")

    def test_unparseable_value_is_cleaned_not_raised(self):
        self.assertEqual(format_when("[not a date]"), "not a date")

    def test_format_for_llm_is_absolute(self):
        self.assertEqual(format_for_llm("2026-10-05T22:22:00+0200"), "Mon 2026-10-05 22:22")


class CandidateCollapseTests(unittest.TestCase):
    def test_series_collapses_to_next_instance_and_recent_skips_it(self):
        upcoming = [
            _row(2, group_id=1, deadline=NOW + timedelta(days=1), description="Meditate", recurrence="recurring"),
            _row(3, group_id=1, deadline=NOW + timedelta(days=2), description="Meditate", recurrence="recurring"),
            _row(4, deadline=NOW + timedelta(days=3), description="Dentist"),
        ]
        recent = [
            _row(9, deadline=None, description="Learn woodworking", status="prepared"),
            _row(3, group_id=1, description="Meditate", recurrence="recurring"),
            _row(4, description="Dentist"),
        ]
        result = collapse_goal_candidates(
            upcoming, recent, series_counts={1: 5, 4: 1, 9: 1}
        )
        self.assertEqual([item["goal_id"] for item in result["upcoming"]], [2, 4])
        self.assertEqual(result["upcoming"][0]["remaining"], 5)
        self.assertEqual(result["upcoming"][0]["series_id"], 1)
        self.assertEqual([item["goal_id"] for item in result["recent"]], [9])

    def test_limits_and_no_duplicate_series_inside_a_list(self):
        upcoming = [
            _row(index, group_id=index, deadline=NOW + timedelta(days=index))
            for index in range(1, 12)
        ]
        result = collapse_goal_candidates(upcoming, upcoming, upcoming_limit=8, recent_limit=8)
        self.assertEqual([item["goal_id"] for item in result["upcoming"]], list(range(1, 9)))
        self.assertEqual([item["goal_id"] for item in result["recent"]], [9, 10, 11])


class CancellationChargeTests(unittest.TestCase):
    def test_free_inside_twelve_hours_including_the_boundary(self):
        self.assertEqual(cancellation_charge(NOW - timedelta(hours=11), 10, NOW), 0.0)
        self.assertEqual(cancellation_charge(NOW - timedelta(hours=12), 10, NOW), 0.0)
        self.assertEqual(
            charge_label(0.0, NOW - timedelta(hours=1), NOW),
            "(free, set <12h ago)",
        )

    def test_charges_postpone_fraction_after_the_window(self):
        self.assertEqual(
            cancellation_charge(NOW - timedelta(hours=12, seconds=1), 10, NOW),
            6.5,
        )
        self.assertEqual(charge_label(6.5, NOW - timedelta(days=2), NOW), "(-6.5)")

    def test_no_penalty_is_free_even_when_old(self):
        self.assertEqual(cancellation_charge(NOW - timedelta(days=3), None, NOW), 0.0)
        self.assertEqual(cancellation_charge(NOW - timedelta(days=3), 0, NOW), 0.0)
        self.assertEqual(charge_label(0.0, NOW - timedelta(days=3), NOW), "(free)")

    def test_missing_set_time_is_not_treated_as_inside_the_window(self):
        self.assertEqual(cancellation_charge(None, 2, NOW), 1.3)

    def test_naive_set_time_is_read_as_berlin(self):
        naive = (NOW - timedelta(days=2)).replace(tzinfo=None)
        self.assertEqual(cancellation_charge(naive, 2, NOW), 1.3)

    def test_pick_charge_row_is_the_earliest_deadline(self):
        later = _row(2, deadline=NOW + timedelta(days=4))
        earlier = _row(1, deadline=NOW - timedelta(days=1))
        undated = _row(3, deadline=None)
        self.assertEqual(pick_charge_row([later, undated, earlier])["goal_id"], 1)
        self.assertIsNone(pick_charge_row([undated]))


class PromptRenderTests(unittest.TestCase):
    def test_classification_prompts_include_live_context(self):
        from LLMs.prompts_templates import (
            goal_classification_template,
            initial_classification_template,
            reminder_setting_template,
        )
        from LLMs.structured_output_schemas import GoalClassification, UpdatedGoalData
        from typing import get_args

        initial = initial_classification_template.format(
            bot_name="Manon", first_name="Ben", user_message="cancel my trial tomorrow"
        )
        self.assertIn("Manon", initial)
        self.assertNotIn("{bot_name}", initial)

        goal = goal_classification_template.format(
            bot_name="Manon",
            first_name="Ben",
            weekday="Saturday",
            now="2026-10-03 16:00:00",
            user_message="Tomorrow I wanna cancel subscription X",
        )
        self.assertIn("Saturday, 2026-10-03 16:00:00", goal)
        self.assertIn("cancel subscription X", goal)
        self.assertNotIn("{now}", goal)
        self.assertIn("actions", GoalClassification.model_fields)

        reminder = reminder_setting_template.format(
            weekday="Saturday",
            now="2026-10-03 16:00:00",
            first_name="Ben",
            user_id=1,
            user_message="remind me to call the dentist and pick up the parcel",
        )
        self.assertIn("Ben", reminder)
        self.assertNotIn("{reminder_text}", reminder)
        self.assertNotIn("{first_name}", reminder)

        statuses = get_args(UpdatedGoalData.model_fields["status"].annotation)
        self.assertIn("paused", statuses)
        self.assertIn("archived_done", statuses)
        self.assertNotIn("pausedarchived_done", statuses)


class MentionedGoalIdTests(unittest.TestCase):
    def test_plain_and_markdown_ids(self):
        self.assertEqual(
            mentioned_goal_ids("cancel #12", "reply to #_34_ and #12 again"),
            [12, 34],
        )


if __name__ == "__main__":
    unittest.main()
