"""Unit tests for the anti-hallucination guard helper (P0.3).

When research fails (404 / Firecrawl error / empty), the pipeline must NOT let
the analysts + synthesizer fabricate a confident verdict. ``_research_failed``
is the detector that drives that guard.

Run: ``uv run python -m pytest tests/test_pipeline_guard.py -q``
"""

import pytest

from agents.pipeline import _research_failed


@pytest.mark.parametrize(
    "research",
    [
        None,
        "",
        "   \n  ",
        "Error: FIRECRAWL_API_KEY no está configurada.",
        "Error al descargar https://x.com: timeout",
        "Error: https://x.com no devolvió texto legible.",
        "RESEARCH_STATUS: SIN_DATOS\nLa web devolvió 404, sin datos públicos.",
    ],
)
def test_research_failed_true(research) -> None:
    assert _research_failed(research) is True


@pytest.mark.parametrize(
    "research",
    [
        "RESEARCH_STATUS: OK\n**Qué hace**: plataforma de pagos para pymes.",
        "**Qué hace**: SaaS de analítica. Propuesta de valor clara.",
    ],
)
def test_research_failed_false(research) -> None:
    assert _research_failed(research) is False
