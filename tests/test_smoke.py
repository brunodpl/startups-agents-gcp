"""Smoke test: the root agent imports and is wired correctly.

Run: ``uv run pytest``
"""

from agents.agent import root_agent


def test_root_agent_is_configured() -> None:
    assert root_agent.name == "startup_diagnostics_agent"
    # Routed to Gemini 2.5 Flash via Vertex AI (not the free tier).
    assert "flash" in root_agent.model
