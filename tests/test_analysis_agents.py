"""Wiring smoke for the F3 analysis sub-agents.

Run: ``uv run python -m pytest tests/test_analysis_agents.py -q``
"""

from agents.sub_agents.business_model import business_model_agent
from agents.sub_agents.market import market_agent
from agents.sub_agents.metrics import metrics_agent


def test_analysts_have_distinct_output_keys() -> None:
    keys = {
        business_model_agent.output_key,
        metrics_agent.output_key,
        market_agent.output_key,
    }
    assert keys == {"business", "metrics", "market"}


def test_analysts_have_no_tools() -> None:
    # Analysts reason over session state, they do not call tools.
    for a in (business_model_agent, metrics_agent, market_agent):
        assert not a.tools
        assert "flash" in a.model
