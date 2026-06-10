"""Shared JSON parsing helpers for LLM-backed discovery sources."""

from __future__ import annotations

import json
import re


def parse_json_array(text: str) -> list[dict]:
    """Parse a JSON array that may be wrapped in a ```json fence or prose."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: grab the outermost [...] array.
        i, j = text.find("["), text.rfind("]")
        if not (0 <= i < j):
            return []
        try:
            data = json.loads(text[i : j + 1])
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []
