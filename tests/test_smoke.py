"""Smoke test: the root agent imports and is wired correctly.

Run: ``uv run python -m pytest -q``
"""

from agents.agent import root_agent


def test_root_agent_is_configured() -> None:
    # F2: the DiscoveryAgent is the root.
    assert root_agent.name == "discovery_agent"
    # Routed to Gemini 2.5 Flash via Vertex AI (not the free tier).
    assert "flash" in root_agent.model
    # Discovery must expose the search_startups tool and persist its shortlist.
    assert len(root_agent.tools) >= 1
    assert root_agent.output_key == "shortlist"
