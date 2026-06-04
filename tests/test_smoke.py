"""Smoke test: the root agent imports and is wired correctly.

Run: ``uv run python -m pytest -q``
"""

from agents.agent import root_agent


def test_root_agent_is_the_pipeline() -> None:
    # F3: the root is the full SequentialAgent pipeline.
    assert root_agent.name == "startup_diagnostics_pipeline"
    names = [a.name for a in root_agent.sub_agents]
    # discovery first, then the per-candidate analysis stage.
    assert names[0] == "discovery_agent"
    assert "per_candidate_analysis" in names
