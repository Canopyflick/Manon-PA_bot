# LLMs/structured_parse.py
"""Helpers for LangChain with_structured_output(include_raw=True) results."""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Neutral values from the valuation rubrics (1 = average effort/impact; no = low-stakes).
# Kept off the Pydantic models on purpose so the JSON schema still marks them required.
STRUCTURED_FIELD_DEFAULTS: dict[str, Any] = {
    "impact_multiplier": 1.0,
    "difficulty_multiplier": 1.0,
    "failure_penalty": "no",
}


def unpack_structured_result(result: Any) -> tuple[Any, Any, dict | None]:
    """Return (parsed, parsing_error, partial_payload).

    include_raw=True yields ``{"raw", "parsed", "parsing_error"}``. A successful
    parsed object is returned as-is; a parse failure exposes the incomplete dict
    so callers can retry or coerce defaults.
    """
    if not (
        isinstance(result, dict)
        and "parsed" in result
        and ("raw" in result or "parsing_error" in result)
    ):
        return result, None, None

    parsed = result.get("parsed")
    if parsed is not None:
        return parsed, None, None

    error = result.get("parsing_error")
    partial = extract_partial_payload(error, result.get("raw"))
    return None, error, partial


def extract_partial_payload(error: Any, raw: Any) -> dict | None:
    payload = _payload_from_validation_error(error)
    if payload is not None:
        return payload

    if raw is None:
        return None

    tool_calls = getattr(raw, "tool_calls", None) or []
    for tc in tool_calls:
        args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
        if isinstance(args, dict) and args:
            return args

    content = getattr(raw, "content", None)
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return None
            if isinstance(data, dict):
                return data
    return None


def coerce_structured_payload(
    schema: type[BaseModel], payload: dict
) -> tuple[BaseModel | None, list[str]]:
    """Fill known-safe valuation defaults for missing fields, then validate."""
    merged = dict(payload)
    filled: list[str] = []
    for key, default in STRUCTURED_FIELD_DEFAULTS.items():
        if key in schema.model_fields and (key not in merged or merged[key] is None):
            merged[key] = default
            filled.append(key)
    try:
        return schema.model_validate(merged), filled
    except ValidationError:
        return None, filled


def _payload_from_validation_error(error: Any) -> dict | None:
    if error is None or not hasattr(error, "errors"):
        return None
    try:
        for err in error.errors():
            inp = err.get("input")
            if isinstance(inp, dict):
                return inp
    except Exception:
        return None
    return None
