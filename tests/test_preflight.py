"""Unit tests for the deploy preflight import guard (P0.1).

The guard exists so a MISSING runtime dependency (as ``firecrawl`` once was)
fails LOUDLY before deploy, instead of as a lazy 500 on the first /run call.

Run: ``uv run python -m pytest tests/test_preflight.py -q``
"""

import importlib

import pytest

from agents import _preflight


def test_check_imports_succeeds() -> None:
    """All runtime deps import and the full agent tree builds — must not raise."""
    _preflight.check_imports()


def test_check_imports_raises_when_a_dep_is_missing(monkeypatch) -> None:
    """If a guarded module can't be imported, the guard raises (the whole point)."""
    real_import = importlib.import_module

    def fake_import(name, *args, **kwargs):
        if name == "firecrawl":
            raise ModuleNotFoundError("No module named 'firecrawl'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    with pytest.raises(ModuleNotFoundError):
        _preflight.check_imports()
