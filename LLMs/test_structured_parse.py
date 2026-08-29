# LLMs/test_structured_parse.py
import unittest

from pydantic import ValidationError

from LLMs.structured_output_schemas import CompactSchedule
from LLMs.structured_parse import (
    coerce_structured_payload,
    unpack_structured_result,
)


PARTIAL_WITHOUT_IMPACT = {
    "reasoning": "Checking if this is useful",
    "goal_description": "Meditate in the morning",
    "evaluation_deadline": "2026-08-29T22:22:00",
    "schedule_reminder": False,
    "reminder_time": None,
    "time_investment_value": 3.0,
    "difficulty_multiplier": 1.0,
    "failure_penalty": "no",
}


class StructuredParseTests(unittest.TestCase):
    def test_compact_schedule_rejects_missing_impact(self):
        with self.assertRaises(ValidationError) as ctx:
            CompactSchedule.model_validate(PARTIAL_WITHOUT_IMPACT)
        self.assertIn("impact_multiplier", str(ctx.exception))

    def test_coerce_fills_impact_multiplier(self):
        parsed, filled = coerce_structured_payload(CompactSchedule, PARTIAL_WITHOUT_IMPACT)
        self.assertIsNotNone(parsed)
        self.assertEqual(filled, ["impact_multiplier"])
        self.assertEqual(parsed.impact_multiplier, 1.0)
        self.assertEqual(parsed.failure_penalty, "no")

    def test_coerce_still_fails_without_description(self):
        payload = dict(PARTIAL_WITHOUT_IMPACT)
        del payload["goal_description"]
        parsed, filled = coerce_structured_payload(CompactSchedule, payload)
        self.assertIsNone(parsed)
        self.assertEqual(filled, ["impact_multiplier"])

    def test_unpack_successful_parsed_object(self):
        full = dict(PARTIAL_WITHOUT_IMPACT, impact_multiplier=1.2)
        model = CompactSchedule.model_validate(full)
        parsed, error, partial = unpack_structured_result(
            {"raw": object(), "parsed": model, "parsing_error": None}
        )
        self.assertIs(parsed, model)
        self.assertIsNone(error)
        self.assertIsNone(partial)

    def test_unpack_exposes_partial_from_validation_error(self):
        try:
            CompactSchedule.model_validate(PARTIAL_WITHOUT_IMPACT)
        except ValidationError as exc:
            parsed, error, partial = unpack_structured_result(
                {"raw": None, "parsed": None, "parsing_error": exc}
            )
        self.assertIsNone(parsed)
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(partial["failure_penalty"], "no")
        self.assertNotIn("impact_multiplier", partial)


if __name__ == "__main__":
    unittest.main()
